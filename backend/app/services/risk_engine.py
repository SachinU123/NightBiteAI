"""
NightBite AI — Risk Scoring Engine

Implements the deterministic formula:
  FinalRisk = BaseFoodRisk × TimeMultiplier × BehaviorMultiplier

All decisions are explainable — no opaque models.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.services.nlp_service import NLPResult

logger = logging.getLogger(__name__)


# ── Time Multiplier Config ─────────────────────────────────────────────────────

TIME_MULTIPLIERS = {
    # (start_hour_inclusive, end_hour_exclusive): multiplier
    (0, 10): 1.0,    # before 10pm (next day 10am is capped same as before 22)
    (10, 22): 1.0,   # 10am–10pm: baseline
    (22, 24): 1.2,   # 10pm–midnight: elevated
}

LATE_NIGHT_BANDS = [
    (0, 2, 1.4),    # midnight–2am
    (2, 4, 1.6),    # 2am–4am
]


def get_time_multiplier(event_dt: datetime) -> tuple[float, str]:
    """
    Returns (multiplier, explanation_label) based on event local hour.
    Uses UTC hour as fallback when no timezone info.
    """
    if event_dt.tzinfo is not None:
        hour = event_dt.hour
    else:
        hour = event_dt.hour

    for start, end, mult in LATE_NIGHT_BANDS:
        if start <= hour < end:
            return mult, f"{start}am–{end}am"

    if 22 <= hour < 24:
        return 1.2, "10pm–midnight"

    return 1.0, "daytime"


# ── Behavior Multiplier ────────────────────────────────────────────────────────

def get_behavior_multiplier(
    user_id: int,
    db: Session,
) -> tuple[float, str]:
    """
    Derives multiplier from recent user behavior.
    If user has had ≥3 high-risk events in past 7 days → 1.15.
    If user has had ≥5 high-risk events in past 7 days → 1.25.
    Otherwise → 1.0 (neutral).
    """
    from datetime import timedelta
    from app.models.food_event import RiskScore, FoodEvent

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    try:
        recent_high_risk = (
            db.query(RiskScore)
            .join(FoodEvent, RiskScore.event_id == FoodEvent.id)
            .filter(
                FoodEvent.user_id == user_id,
                FoodEvent.event_timestamp >= seven_days_ago,
                RiskScore.risk_band.in_(["high", "critical"]),
            )
            .count()
        )

        if recent_high_risk >= 5:
            return 1.25, "frequent_high_risk_pattern"
        if recent_high_risk >= 3:
            return 1.15, "elevated_risk_pattern"
        return 1.0, "normal_behavior"

    except Exception as e:
        logger.warning(f"Could not compute behavior multiplier: {e}")
        return 1.0, "normal_behavior"


# ── Risk Band ─────────────────────────────────────────────────────────────────

def score_to_band(score: float) -> str:
    """Map final risk score to a human-readable band."""
    if score < 3.0:
        return "low"
    if score < 5.5:
        return "moderate"
    if score < 8.0:
        return "high"
    return "critical"


# ── Result Dataclass ──────────────────────────────────────────────────────────

@dataclass
class RiskResult:
    base_food_risk: float
    time_multiplier: float
    behavior_multiplier: float
    final_risk_score: float
    risk_band: str
    time_label: str
    behavior_label: str


# ── Main Entry Point ──────────────────────────────────────────────────────────

class RiskEngine:
    """
    Deterministic risk scoring engine.
    
    Formula:
        FinalRisk = BaseFoodRisk × TimeMultiplier × BehaviorMultiplier
    
    All factors are explainable and traceable.
    """

    def score(
        self,
        nlp_result: NLPResult,
        event_dt: datetime,
        user_id: int,
        db: Session,
    ) -> RiskResult:
        base = nlp_result.base_food_risk
        time_mult, time_label = get_time_multiplier(event_dt)
        behavior_mult, behavior_label = get_behavior_multiplier(user_id, db)

        final = round(base * time_mult * behavior_mult, 2)
        final = min(final, 10.0)  # cap at 10
        band = score_to_band(final)

        return RiskResult(
            base_food_risk=base,
            time_multiplier=time_mult,
            behavior_multiplier=behavior_mult,
            final_risk_score=final,
            risk_band=band,
            time_label=time_label,
            behavior_label=behavior_label,
        )


risk_engine = RiskEngine()
