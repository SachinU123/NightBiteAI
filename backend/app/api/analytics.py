"""
Analytics endpoints — heatmap, dashboard summary.
Uses pandas for grouping and aggregation.
"""
from datetime import datetime, timedelta, timezone
from collections import Counter
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.food_event import FoodEvent, RiskScore, FoodClassification
from app.schemas.analytics import HeatmapResponse, HeatmapCell, DashboardSummaryResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/heatmap", response_model=HeatmapResponse)
def get_heatmap(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """
    Returns heatmap matrix data: each cell = (day_of_week, time_slot, avg_risk, order_count).
    Time slots are the late-night windows: 10PM, 11PM, 12AM, 1AM, 2AM, 3AM, 4AM.
    Locations are grouped by pincode for the sidebar summary cards.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            FoodEvent.pincode,
            FoodEvent.latitude,
            FoodEvent.longitude,
            FoodEvent.event_timestamp,
            RiskScore.final_risk_score,
            RiskScore.risk_band,
        )
        .outerjoin(RiskScore, RiskScore.event_id == FoodEvent.id)
        .filter(FoodEvent.event_timestamp >= since)
        .filter(FoodEvent.is_processed == True)
        .all()
    )

    if not rows:
        return HeatmapResponse(cells=[], total_cells=0)

    df = pd.DataFrame(rows, columns=[
        "pincode", "latitude", "longitude", "event_timestamp",
        "final_risk_score", "risk_band"
    ])

    # Convert to IST
    df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], utc=True)
    df["event_timestamp_ist"] = df["event_timestamp"].dt.tz_convert("Asia/Kolkata")
    df["hour"] = df["event_timestamp_ist"].dt.hour
    df["day_of_week"] = df["event_timestamp_ist"].dt.day_name().str[:3]  # Mon, Tue ...

    # Location key
    def make_location_key(row):
        if row["pincode"]:
            return str(row["pincode"])
        if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
            return f"{round(row['latitude'], 2)},{round(row['longitude'], 2)}"
        return None

    df["location_key"] = df.apply(make_location_key, axis=1)
    df = df[df["location_key"].notna()]

    # Time slot assigned to each row
    LATE_HOURS = {22, 23, 0, 1, 2, 3, 4}
    def hour_to_slot(h):
        if h == 22: return "10p"
        if h == 23: return "11p"
        if h == 0:  return "12a"
        if h == 1:  return "1a"
        if h == 2:  return "2a"
        if h == 3:  return "3a"
        if h == 4:  return "4a"
        return "day"

    df["time_slot"] = df["hour"].apply(hour_to_slot)
    df["final_risk_score"] = pd.to_numeric(df["final_risk_score"], errors="coerce").fillna(4.5)
    df["is_high_risk"] = df["risk_band"].isin(["high", "critical"])

    # Group by location + day + time_slot for the matrix
    grouped = df.groupby(["location_key", "day_of_week", "time_slot"]).agg(
        order_count=("final_risk_score", "count"),
        avg_risk=("final_risk_score", "mean"),
        high_risk_count=("is_high_risk", "sum"),
        lat_bin=("latitude", "first"),
        lon_bin=("longitude", "first"),
    ).reset_index()

    grouped["high_risk_density"] = grouped["high_risk_count"] / grouped["order_count"].clip(lower=1)
    grouped["hotspot_intensity"] = grouped["avg_risk"] * grouped["high_risk_density"]

    cells = []
    for _, row in grouped.iterrows():
        cells.append(HeatmapCell(
            location_key=row["location_key"],
            time_bucket=row["time_slot"],
            day_of_week=row["day_of_week"],
            lat_bin=float(row["lat_bin"]) if pd.notna(row["lat_bin"]) else None,
            lon_bin=float(row["lon_bin"]) if pd.notna(row["lon_bin"]) else None,
            order_count=int(row["order_count"]),
            avg_risk=round(float(row["avg_risk"]), 2),
            high_risk_count=int(row["high_risk_count"]),
            hotspot_intensity=round(float(row["hotspot_intensity"]), 2),
        ))

    return HeatmapResponse(cells=cells, total_cells=len(cells))


@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin/analytics dashboard summary stats."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total_today = (
        db.query(FoodEvent)
        .filter(FoodEvent.event_timestamp >= today_start, FoodEvent.is_processed == True)
        .count()
    )

    total_week = (
        db.query(FoodEvent)
        .filter(FoodEvent.event_timestamp >= week_ago, FoodEvent.is_processed == True)
        .count()
    )

    week_scores = (
        db.query(RiskScore.final_risk_score)
        .join(FoodEvent, RiskScore.event_id == FoodEvent.id)
        .filter(FoodEvent.event_timestamp >= week_ago)
        .all()
    )
    avg_risk_week = None
    if week_scores:
        avg_risk_week = round(sum(s[0] for s in week_scores) / len(week_scores), 2)

    high_risk_today = (
        db.query(RiskScore)
        .join(FoodEvent, RiskScore.event_id == FoodEvent.id)
        .filter(
            FoodEvent.event_timestamp >= today_start,
            RiskScore.risk_band.in_(["high", "critical"]),
        )
        .count()
    )

    # Top source app this week
    source_apps = [
        ev.source_app for ev in
        db.query(FoodEvent.source_app)
        .filter(FoodEvent.event_timestamp >= week_ago, FoodEvent.source_app.isnot(None))
        .all()
    ]
    top_app = Counter(source_apps).most_common(1)[0][0] if source_apps else None

    # Top food category this week
    categories = [
        cls.food_category for cls in
        db.query(FoodClassification.food_category)
        .join(FoodEvent, FoodClassification.event_id == FoodEvent.id)
        .filter(
            FoodEvent.event_timestamp >= week_ago,
            FoodClassification.food_category.isnot(None),
        )
        .all()
    ]
    top_category = Counter(categories).most_common(1)[0][0] if categories else None

    hotspot_count = len(set(
        ev.pincode for ev in
        db.query(FoodEvent.pincode)
        .filter(FoodEvent.event_timestamp >= week_ago, FoodEvent.pincode.isnot(None))
        .all()
    ))

    return DashboardSummaryResponse(
        total_events_today=total_today,
        total_events_this_week=total_week,
        avg_risk_this_week=avg_risk_week,
        high_risk_events_today=high_risk_today,
        top_source_app=top_app,
        top_food_category=top_category,
        hotspot_count=hotspot_count,
    )
