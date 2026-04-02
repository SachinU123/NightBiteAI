"""
NightBite AI — User Insights API

GET /user-insights          — Legacy simple insights (backward compat)
GET /user-insights/profile  — Rich profile dashboard insights (new)
"""
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.food_event import FoodEvent, FoodClassification, RiskScore
from app.schemas.food import (
    UserInsightsResponse,
    ProfileInsightsResponse,
    TopFoodItem,
    LateNightWindow,
    WeeklyOrderStat,
)
from app.services.late_night_utils import (
    is_late_night,
    normalize_food_name,
    hour_to_time_label,
    late_night_hours,
    get_late_night_window_label,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user-insights", tags=["insights"])


# ── Legacy simple insights (backward compat) ───────────────────────────────────

@router.get("", response_model=UserInsightsResponse)
def get_user_insights(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return simple weekly insights for the current user. Preserved for backward compatibility."""
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)

    this_week_events = (
        db.query(FoodEvent)
        .filter(
            FoodEvent.user_id == current_user.id,
            FoodEvent.event_timestamp >= week_ago,
            FoodEvent.is_processed == True,
        )
        .all()
    )

    this_week_scores = [
        ev.risk_score.final_risk_score
        for ev in this_week_events
        if ev.risk_score is not None
    ]

    high_risk_count = sum(
        1 for ev in this_week_events
        if ev.risk_score and ev.risk_score.risk_band in ("high", "critical")
    )

    categories = [
        ev.classification.food_category
        for ev in this_week_events
        if ev.classification and ev.classification.food_category
    ]
    common_category = Counter(categories).most_common(1)[0][0] if categories else None
    weekly_avg = round(sum(this_week_scores) / len(this_week_scores), 2) if this_week_scores else None

    prev_week_events = (
        db.query(FoodEvent)
        .filter(
            FoodEvent.user_id == current_user.id,
            FoodEvent.event_timestamp >= two_weeks_ago,
            FoodEvent.event_timestamp < week_ago,
            FoodEvent.is_processed == True,
        )
        .all()
    )

    prev_scores = [ev.risk_score.final_risk_score for ev in prev_week_events if ev.risk_score]
    prev_avg = sum(prev_scores) / len(prev_scores) if prev_scores else None

    if weekly_avg is None or prev_avg is None:
        trend = "stable"
    elif weekly_avg < prev_avg - 0.5:
        trend = "improving"
    elif weekly_avg > prev_avg + 0.5:
        trend = "worsening"
    else:
        trend = "stable"

    return UserInsightsResponse(
        weekly_avg_risk=weekly_avg,
        high_risk_count_this_week=high_risk_count,
        total_events_this_week=len(this_week_events),
        common_food_category=common_category,
        risk_trend=trend,
    )


# ── Rich Profile Insights ──────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileInsightsResponse)
def get_profile_insights(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return rich, chart-ready behavioral insights for the profile dashboard.
    All data is structured for direct Flutter consumption.
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    two_weeks_ago = now - timedelta(days=14)

    # ── All processed events ───────────────────────────────────────────────────
    all_events = (
        db.query(FoodEvent)
        .filter(
            FoodEvent.user_id == current_user.id,
            FoodEvent.is_processed == True,
        )
        .order_by(FoodEvent.event_timestamp.desc())
        .all()
    )

    # ── Late-night events ──────────────────────────────────────────────────────
    late_night_events = [ev for ev in all_events if is_late_night(ev.event_timestamp)]
    week_events = [ev for ev in all_events if ev.event_timestamp >= week_ago]
    month_events = [ev for ev in all_events if ev.event_timestamp >= month_ago]
    week_ln = [ev for ev in week_events if is_late_night(ev.event_timestamp)]
    month_ln = [ev for ev in month_events if is_late_night(ev.event_timestamp)]

    total = len(all_events)
    ln_total = len(late_night_events)
    ln_pct = round((ln_total / total * 100), 1) if total > 0 else 0.0

    # ── Risk summary ───────────────────────────────────────────────────────────
    all_scores = [ev.risk_score.final_risk_score for ev in all_events if ev.risk_score]
    week_scores = [ev.risk_score.final_risk_score for ev in week_events if ev.risk_score]
    prev_week_events = [ev for ev in all_events if two_weeks_ago <= ev.event_timestamp < week_ago]
    prev_scores = [ev.risk_score.final_risk_score for ev in prev_week_events if ev.risk_score]

    avg_risk = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    week_avg = sum(week_scores) / len(week_scores) if week_scores else None
    prev_avg = sum(prev_scores) / len(prev_scores) if prev_scores else None

    if week_avg is not None and prev_avg is not None:
        delta = round(week_avg - prev_avg, 2)
        if delta < -0.5:
            trend = "improving"
        elif delta > 0.5:
            trend = "worsening"
        else:
            trend = "stable"
    else:
        trend = "stable"
        delta = None

    high_risk_week = sum(
        1 for ev in week_events
        if ev.risk_score and ev.risk_score.risk_band in ("high", "critical")
    )
    high_risk_month = sum(
        1 for ev in month_events
        if ev.risk_score and ev.risk_score.risk_band in ("high", "critical")
    )

    # ── Top foods (all) ────────────────────────────────────────────────────────
    food_groups: dict[str, list[FoodEvent]] = {}
    for ev in all_events:
        canonical = normalize_food_name(ev.normalized_food_text)
        food_groups.setdefault(canonical, []).append(ev)

    def _build_top_food_item(name: str, evs: list) -> TopFoodItem:
        scores = [e.risk_score.final_risk_score for e in evs if e.risk_score]
        bands = [e.risk_score.risk_band for e in evs if e.risk_score]
        return TopFoodItem(
            canonical_name=name,
            order_count=len(evs),
            last_ordered_at=max(e.event_timestamp for e in evs),
            avg_risk_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
            risk_band=Counter(bands).most_common(1)[0][0] if bands else "unknown",
        )

    top_foods = sorted(food_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    top_food_items = [_build_top_food_item(name, evs) for name, evs in top_foods]

    # ── Top late-night foods ───────────────────────────────────────────────────
    ln_food_groups: dict[str, list[FoodEvent]] = {}
    for ev in late_night_events:
        canonical = normalize_food_name(ev.normalized_food_text)
        ln_food_groups.setdefault(canonical, []).append(ev)

    top_ln_foods = sorted(ln_food_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    top_ln_items = [_build_top_food_item(name, evs) for name, evs in top_ln_foods]

    # ── Unique / repeat food counts ────────────────────────────────────────────
    unique_food_count = len(food_groups)
    repeat_food_count = sum(1 for evs in food_groups.values() if len(evs) >= 2)

    # ── Late-night hour distribution ───────────────────────────────────────────
    hour_counter = Counter(ev.event_timestamp.hour for ev in late_night_events)
    ln_total_for_pct = max(ln_total, 1)
    ln_windows: list[LateNightWindow] = []
    for h in late_night_hours():
        count = hour_counter.get(h, 0)
        ln_windows.append(LateNightWindow(
            hour=h,
            label=hour_to_time_label(h),
            order_count=count,
            pct=round(count / ln_total_for_pct * 100, 1),
        ))

    # Dominant late-night window
    dominant_window = None
    if late_night_events:
        peak_hour = hour_counter.most_common(1)[0][0]
        dominant_window = get_late_night_window_label(peak_hour)

    # ── Weekly trend (last 4 weeks) ────────────────────────────────────────────
    weekly_trend: list[WeeklyOrderStat] = []
    for weeks_ago in range(3, -1, -1):
        w_start = now - timedelta(days=(weeks_ago + 1) * 7)
        w_end = now - timedelta(days=weeks_ago * 7)
        w_evs = [ev for ev in all_events if w_start <= ev.event_timestamp < w_end]
        w_ln = [ev for ev in w_evs if is_late_night(ev.event_timestamp)]
        w_scores = [ev.risk_score.final_risk_score for ev in w_evs if ev.risk_score]
        weekly_trend.append(WeeklyOrderStat(
            week_label="This Week" if weeks_ago == 0 else f"{weeks_ago}w ago",
            total_orders=len(w_evs),
            late_night_orders=len(w_ln),
            avg_risk=round(sum(w_scores)/len(w_scores), 2) if w_scores else None,
        ))

    # ── Streak calculation ─────────────────────────────────────────────────────
    streak = 0
    if late_night_events:
        check_date = now.date()
        event_dates = {ev.event_timestamp.date() for ev in late_night_events}
        while check_date in event_dates:
            streak += 1
            check_date = check_date - timedelta(days=1)

    last_ln = late_night_events[0].event_timestamp if late_night_events else None

    # ── Behavior summary text ──────────────────────────────────────────────────
    behavior_summary = _generate_behavior_summary(
        total=total,
        ln_total=ln_total,
        ln_pct=ln_pct,
        trend=trend,
        week_ln=len(week_ln),
        top_food=top_food_items[0].canonical_name if top_food_items else None,
        streak=streak,
    )

    return ProfileInsightsResponse(
        total_orders_all_time=total,
        total_late_night_orders=ln_total,
        late_night_pct=ln_pct,
        weekly_late_night_count=len(week_ln),
        monthly_late_night_count=len(month_ln),
        avg_risk_score=avg_risk,
        risk_trend=trend,
        risk_trend_delta=delta,
        high_risk_count_week=high_risk_week,
        high_risk_count_month=high_risk_month,
        top_foods=top_food_items,
        top_late_night_foods=top_ln_items,
        unique_food_count=unique_food_count,
        repeat_food_count=repeat_food_count,
        dominant_late_night_window=dominant_window,
        late_night_windows=ln_windows,
        weekly_trend=weekly_trend,
        behavior_summary=behavior_summary,
        streak_days=streak,
        last_late_night_order=last_ln,
    )


def _generate_behavior_summary(
    total: int,
    ln_total: int,
    ln_pct: float,
    trend: str,
    week_ln: int,
    top_food: Optional[str],
    streak: int,
) -> str:
    """Generate a user-specific, human-readable behavioral summary."""
    if total == 0:
        return "No food orders logged yet. Start by logging your first late-night order!"

    if ln_total == 0:
        return "No late-night orders recorded yet. Your tracking begins at 10 PM."

    trend_phrase = ""
    if trend == "improving":
        trend_phrase = " Your pattern is improving this week — great work!"
    elif trend == "worsening":
        trend_phrase = " Late-night ordering has picked up this week — worth watching."

    streak_phrase = ""
    if streak >= 3:
        streak_phrase = f" You've had late-night orders {streak} nights in a row."
    elif streak == 2:
        streak_phrase = " You've had late-night orders 2 nights running."

    food_phrase = f" {top_food} is your most ordered item." if top_food else ""

    if ln_pct >= 80:
        base = f"Most of your {total} tracked orders ({ln_pct}%) happen late at night."
    elif ln_pct >= 50:
        base = f"You've logged {ln_total} late-night orders out of {total} total."
    else:
        base = f"You've made {ln_total} late-night food choices across {total} total orders."

    return (base + food_phrase + trend_phrase + streak_phrase).strip()
