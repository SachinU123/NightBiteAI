"""
NightBite AI — Raw Notification Ingestion API

This is the core endpoint — it receives raw notification payloads
from the Android NotificationListenerService, runs the full AI pipeline,
and returns a structured risk analysis.

Endpoint: POST /api/v1/notifications/ingest

Expected from Android:
{
  "app_package": "in.swiggy.android",
  "app_name": "Swiggy",
  "title": "Order placed!",
  "text": "Your Butter Chicken is on its way",
  "subtext": null,
  "posted_at": "2025-03-31T00:15:00Z",
  "device_id": "optional-android-id"
}

Returns full FoodAnalysisResponse with risk score, nudge, etc.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.food_event import FoodEvent, FoodClassification, RiskScore
from app.models.analytics import Nudge
from app.schemas.food import FoodAnalysisResponse
from app.services.ai_classifier_service import classify_notification
from app.services.nlp_service import nlp_service
from app.services.risk_engine import risk_engine
from app.services.nudge_generator import nudge_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Request schema ─────────────────────────────────────────────────────────────

class NotificationIngestRequest(BaseModel):
    """
    Payload sent by Android NotificationListenerService.
    All fields except posted_at are optional to handle partial captures gracefully.
    """
    app_package: Optional[str] = None       # e.g. "in.swiggy.android"
    app_name: Optional[str] = None          # e.g. "Swiggy"
    title: Optional[str] = None             # notification title
    text: Optional[str] = None              # notification body
    subtext: Optional[str] = None           # notification subtext/summary
    posted_at: Optional[datetime] = None    # when notification was posted on device
    device_id: Optional[str] = None         # android installation ID (for audit)

    # Optional geo fields (if app sends them)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pincode: Optional[str] = None


class NotificationIngestResponse(BaseModel):
    """Extended response for notification ingestion — includes classification details."""
    success: bool
    notification_id: int
    is_food_related: bool
    is_order: bool
    is_promo: bool
    platform_name: Optional[str]
    vendor_name: Optional[str]
    probable_items: list[str]
    health_risk_score: Optional[float]
    late_night_score: Optional[float]
    combined_risk_score: Optional[float]
    risk_band: Optional[str]
    explanation: str
    smart_nudge: Optional[str]
    healthier_swap: Optional[str]
    confidence: float
    used_claude: bool
    analysis: Optional[FoodAnalysisResponse] = None


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/ingest",
    response_model=NotificationIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest raw Android notification",
    description=(
        "Accept a raw notification captured by the Android NotificationListenerService. "
        "Runs the full AI classification + risk scoring pipeline. "
        "Always returns a result — never crashes due to classification failure."
    ),
)
def ingest_notification(
    payload: NotificationIngestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    event_dt = payload.posted_at or datetime.now(timezone.utc)
    full_text = " ".join(filter(None, [payload.title, payload.text, payload.subtext]))

    # ── Step 1: AI Classification (hybrid: rules + Claude) ────────────────────
    classification = classify_notification(
        app_package=payload.app_package,
        app_name=payload.app_name,
        title=payload.title,
        text=payload.text,
    )

    logger.info(
        f"Notification classified: food={classification.is_food_related}, "
        f"order={classification.is_order}, platform={classification.platform_name}, "
        f"claude={classification.used_claude}"
    )

    # ── Step 2: Always store raw event in DB ──────────────────────────────────
    raw_notification_text = full_text or None
    food_text_for_analysis = (
        " ".join(classification.probable_items) if classification.probable_items
        else full_text or "unknown food"
    )

    event = FoodEvent(
        user_id=current_user.id,
        source_type="notification",
        source_app=classification.platform_name or payload.app_name or payload.app_package,
        raw_food_text=food_text_for_analysis,
        raw_notification_text=raw_notification_text,
        event_timestamp=event_dt,
        latitude=payload.latitude,
        longitude=payload.longitude,
        pincode=payload.pincode,
        meal_type=classification.meal_type,
        is_processed=False,  # will set True after pipeline
    )
    db.add(event)
    db.flush()

    # ── Step 3: If not food-related, save minimal record and return ───────────
    if not classification.is_food_related or classification.is_promo:
        event.is_processed = True
        db.commit()
        return NotificationIngestResponse(
            success=True,
            notification_id=event.id,
            is_food_related=classification.is_food_related,
            is_order=False,
            is_promo=classification.is_promo,
            platform_name=classification.platform_name,
            vendor_name=classification.vendor_name,
            probable_items=classification.probable_items,
            health_risk_score=None,
            late_night_score=None,
            combined_risk_score=None,
            risk_band=None,
            explanation=classification.explanation,
            smart_nudge=None,
            healthier_swap=None,
            confidence=classification.confidence,
            used_claude=classification.used_claude,
        )

    # ── Step 4: Run NLP + risk pipeline for food orders ───────────────────────
    try:
        nlp_result = nlp_service.analyze(food_text_for_analysis, is_partial=False)
        event.normalized_food_text = nlp_result.normalized_text
        event.is_processed = True
        db.flush()

        # Persist classification
        cls_row = FoodClassification(
            event_id=event.id,
            food_category=nlp_result.food_category,
            risk_tags=json.dumps(nlp_result.risk_tags),
            matched_keywords=json.dumps(nlp_result.matched_keywords),
            confidence=nlp_result.confidence,
            parse_quality=nlp_result.parse_quality,
        )
        db.add(cls_row)
        db.flush()

        # Risk score
        risk_result = risk_engine.score(
            nlp_result=nlp_result,
            event_dt=event_dt,
            user_id=current_user.id,
            db=db,
        )

        score_row = RiskScore(
            event_id=event.id,
            base_food_risk=risk_result.base_food_risk,
            time_multiplier=risk_result.time_multiplier,
            behavior_multiplier=risk_result.behavior_multiplier,
            final_risk_score=risk_result.final_risk_score,
            risk_band=risk_result.risk_band,
        )
        db.add(score_row)
        db.flush()

        # Nudge
        nudge_output = nudge_generator.generate(
            nlp_result=nlp_result,
            risk_result=risk_result,
            behavior_label=risk_result.behavior_label,
        )

        nudge_row = Nudge(
            event_id=event.id,
            user_id=current_user.id,
            nudge_text=nudge_output.nudge_text,
            healthier_swap=nudge_output.healthier_swap,
            nudge_type=nudge_output.nudge_type,
        )
        db.add(nudge_row)
        db.commit()
        db.refresh(event)

        # Build full analysis response
        analysis = FoodAnalysisResponse(
            event_id=event.id,
            source_type=event.source_type,
            source_app=event.source_app,
            normalized_food_text=nlp_result.normalized_text,
            food_category=nlp_result.food_category,
            risk_tags=nlp_result.risk_tags,
            risk_score=risk_result.final_risk_score,
            risk_band=risk_result.risk_band,
            smart_nudge=nudge_output.nudge_text,
            healthier_swap=nudge_output.healthier_swap,
            event_timestamp=event_dt,
        )

        # Late night score = time_multiplier mapped to 0-10
        late_night_score = round((risk_result.time_multiplier - 1.0) * 10.0, 2)
        late_night_score = max(0.0, min(10.0, late_night_score * 2.5))

        return NotificationIngestResponse(
            success=True,
            notification_id=event.id,
            is_food_related=True,
            is_order=classification.is_order,
            is_promo=False,
            platform_name=classification.platform_name,
            vendor_name=classification.vendor_name,
            probable_items=classification.probable_items,
            health_risk_score=risk_result.base_food_risk,
            late_night_score=late_night_score,
            combined_risk_score=risk_result.final_risk_score,
            risk_band=risk_result.risk_band,
            explanation=classification.explanation,
            smart_nudge=nudge_output.nudge_text,
            healthier_swap=nudge_output.healthier_swap,
            confidence=classification.confidence,
            used_claude=classification.used_claude,
            analysis=analysis,
        )

    except Exception as e:
        logger.error(f"Pipeline failed for notification {event.id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis pipeline failed: {str(e)}",
        )
