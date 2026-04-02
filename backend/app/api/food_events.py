"""
NightBite AI — Food Events API

Endpoints:
  POST /food-events/manual-entry       — Manual food log
  POST /food-events/notification-capture — Notification-based capture
  GET  /food-events/latest             — Most recent event
  GET  /food-events/history            — Flat paginated history (search/filter/sort)
  GET  /food-events/grouped            — Grouped/deduplicated history
  GET  /food-events/item/{name}        — Item detail analytics
"""
import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.food_event import FoodEvent, FoodClassification, RiskScore
from app.models.analytics import Nudge
from app.schemas.food import (
    ManualEntryRequest,
    NotificationCaptureRequest,
    FoodAnalysisResponse,
    HistoryResponse,
    HistoryEventItem,
    GroupedFoodItem,
    GroupedHistoryResponse,
    ItemDetailResponse,
    ItemOrderInstance,
    TimeDistributionBucket,
    WeeklyTrendPoint,
    MonthlyTrendPoint,
)
from app.services.ingestion_adapters import manual_entry_adapter, notification_capture_adapter
from app.services.late_night_utils import (
    is_late_night, normalize_food_name, hour_to_time_label, late_night_hours
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/food-events", tags=["food-events"])


# ── Manual Entry ───────────────────────────────────────────────────────────────

@router.post("/manual-entry", response_model=FoodAnalysisResponse, status_code=status.HTTP_201_CREATED)
def manual_entry(
    payload: ManualEntryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Submit a manually entered food item for analysis."""
    if not payload.food_text or len(payload.food_text.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="food_text must not be empty.",
        )

    return manual_entry_adapter.ingest(payload=payload, user_id=current_user.id, db=db)


# ── Notification Capture ───────────────────────────────────────────────────────

@router.post("/notification-capture", response_model=FoodAnalysisResponse, status_code=status.HTTP_201_CREATED)
def notification_capture(
    payload: NotificationCaptureRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Submit a captured food notification for analysis."""
    if not payload.raw_notification_text and not payload.raw_food_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either raw_notification_text or raw_food_text must be provided.",
        )

    return notification_capture_adapter.ingest(payload=payload, user_id=current_user.id, db=db)


# ── Latest Event ───────────────────────────────────────────────────────────────

@router.get("/latest", response_model=Optional[FoodAnalysisResponse])
def get_latest_event(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return the most recent analyzed food event for the current user."""
    event = (
        db.query(FoodEvent)
        .filter(FoodEvent.user_id == current_user.id, FoodEvent.is_processed == True)
        .order_by(FoodEvent.event_timestamp.desc())
        .first()
    )

    if not event:
        return None

    return _event_to_response(event)


# ── Flat History (search / filter / sort) ─────────────────────────────────────

@router.get("/history", response_model=HistoryResponse)
def get_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, description="Search by food name"),
    source_app: Optional[str] = Query(default=None, description="Filter by source app (e.g. Zomato)"),
    late_night_only: bool = Query(default=False, description="Only show late-night orders"),
    sort_by: str = Query(default="most_recent", description="most_recent | highest_risk | lowest_risk"),
    days: Optional[int] = Query(default=None, ge=1, le=365, description="Limit to last N days"),
):
    """
    Return paginated food event history for the current user.
    Supports search, filter by source app, late-night filter, and sorting.
    """
    query = db.query(FoodEvent).filter(
        FoodEvent.user_id == current_user.id,
        FoodEvent.is_processed == True,
    )

    # Apply days filter
    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(FoodEvent.event_timestamp >= since)

    # Apply search (normalized or raw food text)
    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(
            FoodEvent.normalized_food_text.ilike(search_term) |
            FoodEvent.raw_food_text.ilike(search_term)
        )

    # Apply source app filter
    if source_app and source_app.strip():
        query = query.filter(FoodEvent.source_app.ilike(f"%{source_app.strip()}%"))

    # Apply late-night filter (hours 22, 23, 0, 1, 2, 3, 4)
    if late_night_only:
        from sqlalchemy import extract
        query = query.filter(
            (extract("hour", FoodEvent.event_timestamp) >= 22) |
            (extract("hour", FoodEvent.event_timestamp) < 4)
        )

    # Count before pagination
    total = query.count()

    # Apply sorting
    if sort_by == "highest_risk":
        query = query.join(RiskScore, RiskScore.event_id == FoodEvent.id, isouter=True)
        query = query.order_by(RiskScore.final_risk_score.desc().nulls_last())
    elif sort_by == "lowest_risk":
        query = query.join(RiskScore, RiskScore.event_id == FoodEvent.id, isouter=True)
        query = query.order_by(RiskScore.final_risk_score.asc().nulls_last())
    else:
        query = query.order_by(FoodEvent.event_timestamp.desc())

    events = query.offset((page - 1) * page_size).limit(page_size).all()

    # Count late-night total
    late_night_total = sum(1 for ev in events if is_late_night(ev.event_timestamp))

    items = []
    for ev in events:
        score_row = ev.risk_score
        cls_row = ev.classification
        nudge_row = ev.nudge
        items.append(
            HistoryEventItem(
                event_id=ev.id,
                source_type=ev.source_type,
                source_app=ev.source_app,
                normalized_food_text=ev.normalized_food_text,
                risk_score=score_row.final_risk_score if score_row else 0.0,
                risk_band=score_row.risk_band if score_row else "unknown",
                event_timestamp=ev.event_timestamp,
                food_category=cls_row.food_category if cls_row else None,
                is_late_night=is_late_night(ev.event_timestamp),
                smart_nudge=nudge_row.nudge_text if nudge_row else None,
                healthier_swap=nudge_row.healthier_swap if nudge_row else None,
            )
        )

    return HistoryResponse(
        total=total,
        late_night_total=late_night_total,
        page=page,
        page_size=page_size,
        events=items,
    )


# ── Grouped / Deduplicated History ─────────────────────────────────────────────

@router.get("/grouped", response_model=GroupedHistoryResponse)
def get_grouped_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(default=None, description="Search by food name"),
    source_app: Optional[str] = Query(default=None, description="Filter by source app"),
    late_night_only: bool = Query(default=False, description="Only include late-night orders"),
    sort_by: str = Query(
        default="most_ordered",
        description="most_ordered | most_recent | highest_risk | highest_frequency",
    ),
    days: Optional[int] = Query(default=None, ge=1, le=365),
    min_orders: int = Query(default=1, ge=1, description="Minimum orders to include"),
):
    """
    Return grouped/deduplicated food history.
    Groups food events by canonical food name, providing aggregated stats.
    Ideal for the Flutter history grouped view.
    """
    query = db.query(FoodEvent).filter(
        FoodEvent.user_id == current_user.id,
        FoodEvent.is_processed == True,
        FoodEvent.normalized_food_text.isnot(None),
    )

    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(FoodEvent.event_timestamp >= since)

    if source_app and source_app.strip():
        query = query.filter(FoodEvent.source_app.ilike(f"%{source_app.strip()}%"))

    if late_night_only:
        from sqlalchemy import extract
        query = query.filter(
            (extract("hour", FoodEvent.event_timestamp) >= 22) |
            (extract("hour", FoodEvent.event_timestamp) < 4)
        )

    events = query.order_by(FoodEvent.event_timestamp.desc()).all()

    # Group by canonical food name
    groups: dict[str, list[FoodEvent]] = {}
    for ev in events:
        canonical = normalize_food_name(ev.normalized_food_text)

        # Apply search filter after normalization
        if search and search.strip():
            if search.strip().lower() not in canonical.lower():
                continue

        groups.setdefault(canonical, []).append(ev)

    # Build grouped items
    grouped_items: list[GroupedFoodItem] = []
    total_orders_all = sum(len(evs) for evs in groups.values())
    late_night_all = 0

    for canonical_name, evs in groups.items():
        if len(evs) < min_orders:
            continue

        timestamps = [ev.event_timestamp for ev in evs]
        risk_scores = [ev.risk_score.final_risk_score for ev in evs if ev.risk_score]
        risk_bands = [ev.risk_score.risk_band for ev in evs if ev.risk_score]
        source_apps_raw = list(set(ev.source_app for ev in evs if ev.source_app))
        late_night_evs = [ev for ev in evs if is_late_night(ev.event_timestamp)]
        late_night_all += len(late_night_evs)

        # Food category from first classification
        category = None
        for ev in evs:
            if ev.classification and ev.classification.food_category:
                category = ev.classification.food_category
                break

        # Risk stats
        avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
        max_risk = round(max(risk_scores), 2) if risk_scores else 0.0
        dominant_band = Counter(risk_bands).most_common(1)[0][0] if risk_bands else "unknown"

        # Common order hour
        hours = [ev.event_timestamp.hour for ev in evs]
        common_hour = Counter(hours).most_common(1)[0][0] if hours else None
        time_label = hour_to_time_label(common_hour) if common_hour is not None else None

        # Recurrence
        recurrence_days = None
        if len(timestamps) >= 2:
            sorted_ts = sorted(timestamps)
            gaps = [(sorted_ts[i+1] - sorted_ts[i]).days for i in range(len(sorted_ts)-1) if sorted_ts[i+1] > sorted_ts[i]]
            if gaps:
                recurrence_days = round(sum(gaps) / len(gaps), 1)

        # Healthier swap (pick from nudges)
        swap = None
        for ev in evs:
            if ev.nudge and ev.nudge.healthier_swap:
                swap = ev.nudge.healthier_swap
                break

        grouped_items.append(GroupedFoodItem(
            canonical_name=canonical_name,
            food_category=category,
            total_orders=len(evs),
            late_night_orders=len(late_night_evs),
            first_ordered_at=min(timestamps),
            last_ordered_at=max(timestamps),
            avg_risk_score=avg_risk,
            max_risk_score=max_risk,
            dominant_risk_band=dominant_band,
            common_order_hour=common_hour,
            common_order_time_label=time_label,
            source_apps=source_apps_raw,
            has_healthier_swap=swap is not None,
            healthier_swap=swap,
            recurrence_days=recurrence_days,
            event_ids=[ev.id for ev in evs],
        ))

    # Sort
    if sort_by == "most_ordered":
        grouped_items.sort(key=lambda x: x.total_orders, reverse=True)
    elif sort_by == "most_recent":
        grouped_items.sort(key=lambda x: x.last_ordered_at, reverse=True)
    elif sort_by == "highest_risk":
        grouped_items.sort(key=lambda x: x.avg_risk_score, reverse=True)
    elif sort_by == "highest_frequency":
        grouped_items.sort(key=lambda x: x.recurrence_days or 9999)

    return GroupedHistoryResponse(
        total_unique_foods=len(grouped_items),
        total_orders=total_orders_all,
        late_night_orders=late_night_all,
        search_query=search,
        sort_by=sort_by,
        items=grouped_items,
    )


# ── Item Detail Analytics ──────────────────────────────────────────────────────

@router.get("/item/{food_name}", response_model=ItemDetailResponse)
def get_item_detail(
    food_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: Optional[int] = Query(default=90, ge=7, le=365),
):
    """
    Return full analytics for a specific food item.
    Used by the Flutter item detail drill-down screen.
    Searches by normalized food name (case-insensitive partial match).
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    events = (
        db.query(FoodEvent)
        .filter(
            FoodEvent.user_id == current_user.id,
            FoodEvent.is_processed == True,
            FoodEvent.normalized_food_text.ilike(f"%{food_name}%"),
            FoodEvent.event_timestamp >= since,
        )
        .order_by(FoodEvent.event_timestamp.desc())
        .all()
    )

    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No orders found for food item: {food_name}",
        )

    timestamps = [ev.event_timestamp for ev in events]
    risk_scores = [ev.risk_score.final_risk_score for ev in events if ev.risk_score]
    risk_bands = [ev.risk_score.risk_band for ev in events if ev.risk_score]
    late_night_evs = [ev for ev in events if is_late_night(ev.event_timestamp)]

    # Basic stats
    avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
    max_risk = round(max(risk_scores), 2) if risk_scores else 0.0
    dominant_band = Counter(risk_bands).most_common(1)[0][0] if risk_bands else "unknown"

    # Category and tags
    category = None
    risk_tags: list[str] = []
    swap = None
    for ev in events:
        if ev.classification:
            if not category and ev.classification.food_category:
                category = ev.classification.food_category
            if not risk_tags and ev.classification.risk_tags:
                try:
                    risk_tags = json.loads(ev.classification.risk_tags) or []
                except Exception:
                    pass
        if ev.nudge and ev.nudge.healthier_swap and not swap:
            swap = ev.nudge.healthier_swap

    # Common order hour
    hours = [ev.event_timestamp.hour for ev in events]
    hour_counter = Counter(hours)
    common_hour = hour_counter.most_common(1)[0][0] if hours else None
    time_label = hour_to_time_label(common_hour) if common_hour is not None else None

    # Recurrence
    recurrence_days = None
    recurrence_label = None
    if len(timestamps) >= 2:
        sorted_ts = sorted(timestamps)
        gaps = [(sorted_ts[i+1] - sorted_ts[i]).days for i in range(len(sorted_ts)-1) if sorted_ts[i+1] > sorted_ts[i]]
        if gaps:
            recurrence_days = round(sum(gaps) / len(gaps), 1)
            if recurrence_days <= 1:
                recurrence_label = "Almost daily"
            elif recurrence_days <= 3:
                recurrence_label = f"Every ~{int(recurrence_days)} days"
            elif recurrence_days <= 7:
                recurrence_label = "Weekly"
            elif recurrence_days <= 14:
                recurrence_label = "Bi-weekly"
            else:
                recurrence_label = f"Every ~{int(recurrence_days)} days"

    # Time distribution (hours)
    time_dist = []
    for hour in late_night_hours():
        count = hour_counter.get(hour, 0)
        evs_this_hour = [ev for ev in events if ev.event_timestamp.hour == hour]
        h_scores = [ev.risk_score.final_risk_score for ev in evs_this_hour if ev.risk_score]
        h_avg = round(sum(h_scores) / len(h_scores), 2) if h_scores else 0.0
        if count > 0:
            time_dist.append(TimeDistributionBucket(
                hour=hour,
                label=hour_to_time_label(hour),
                count=count,
                avg_risk=h_avg,
            ))

    # Weekly trend (last 4 weeks)
    weekly_trend = []
    now = datetime.now(timezone.utc)
    for weeks_ago in range(3, -1, -1):
        week_start = now - timedelta(days=(weeks_ago + 1) * 7)
        week_end = now - timedelta(days=weeks_ago * 7)
        week_evs = [ev for ev in events if week_start <= ev.event_timestamp < week_end]
        week_scores = [ev.risk_score.final_risk_score for ev in week_evs if ev.risk_score]
        weekly_trend.append(WeeklyTrendPoint(
            week_label="This Week" if weeks_ago == 0 else f"{weeks_ago}w ago",
            order_count=len(week_evs),
            avg_risk=round(sum(week_scores) / len(week_scores), 2) if week_scores else 0.0,
        ))

    # Monthly trend (last 3 months)
    monthly_trend = []
    for months_ago in range(2, -1, -1):
        month_dt = now - timedelta(days=months_ago * 30)
        label = month_dt.strftime("%b %Y")
        month_start = month_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        month_evs = [ev for ev in events if month_start <= ev.event_timestamp < month_end]
        month_scores = [ev.risk_score.final_risk_score for ev in month_evs if ev.risk_score]
        monthly_trend.append(MonthlyTrendPoint(
            month_label=label,
            order_count=len(month_evs),
            avg_risk=round(sum(month_scores) / len(month_scores), 2) if month_scores else 0.0,
        ))

    # Per-order instances
    order_instances = []
    for ev in events[:30]:  # Cap at 30 for response size
        nudge_text = ev.nudge.nudge_text if ev.nudge else None
        order_instances.append(ItemOrderInstance(
            event_id=ev.id,
            ordered_at=ev.event_timestamp,
            source_app=ev.source_app,
            risk_score=ev.risk_score.final_risk_score if ev.risk_score else 0.0,
            risk_band=ev.risk_score.risk_band if ev.risk_score else "unknown",
            is_late_night=is_late_night(ev.event_timestamp),
            nudge_text=nudge_text,
        ))

    canonical = normalize_food_name(events[0].normalized_food_text)

    return ItemDetailResponse(
        canonical_name=canonical,
        food_category=category,
        total_orders=len(events),
        late_night_orders=len(late_night_evs),
        first_ordered_at=min(timestamps),
        last_ordered_at=max(timestamps),
        avg_risk_score=avg_risk,
        max_risk_score=max_risk,
        dominant_risk_band=dominant_band,
        common_order_hour=common_hour,
        common_order_time_label=time_label,
        recurrence_days=recurrence_days,
        recurrence_label=recurrence_label,
        time_distribution=time_dist,
        weekly_trend=weekly_trend,
        monthly_trend=monthly_trend,
        has_healthier_swap=swap is not None,
        healthier_swap=swap,
        risk_tags=risk_tags,
        orders=order_instances,
    )


# ── Helper ─────────────────────────────────────────────────────────────────────

def _event_to_response(event: FoodEvent) -> FoodAnalysisResponse:
    """Convert a persisted FoodEvent (with joins) to the API response model."""
    score = event.risk_score
    cls = event.classification
    nudge = event.nudge

    risk_tags = []
    if cls and cls.risk_tags:
        try:
            risk_tags = json.loads(cls.risk_tags)
        except Exception:
            pass

    return FoodAnalysisResponse(
        event_id=event.id,
        source_type=event.source_type,
        source_app=event.source_app,
        normalized_food_text=event.normalized_food_text,
        food_category=cls.food_category if cls else None,
        risk_tags=risk_tags,
        risk_score=score.final_risk_score if score else 0.0,
        risk_band=score.risk_band if score else "unknown",
        smart_nudge=nudge.nudge_text if nudge else "No nudge available.",
        healthier_swap=nudge.healthier_swap if nudge else None,
        event_timestamp=event.event_timestamp,
        is_late_night=is_late_night(event.event_timestamp),
    )
