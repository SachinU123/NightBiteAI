"""
NightBite AI — Food Event Ingestion Adapters

Adapter-pattern design for extensibility:
  - ManualEntryAdapter
  - NotificationCaptureAdapter
  - (Future) FuturePartnerApiAdapter

Each adapter:
  1. Validates and normalizes input
  2. Persists the raw event
  3. Runs NLP analysis
  4. Runs risk scoring
  5. Generates nudge
  6. Persists processed results
  7. Returns FoodAnalysisResponse

This design allows future delivery platform API webhooks to be plugged in
by creating a new adapter without touching core business logic.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.food_event import FoodEvent, FoodClassification, RiskScore
from app.models.analytics import Nudge
from app.schemas.food import (
    FoodAnalysisResponse,
    ClassificationResult,
    RiskScoreResult,
    NudgeResult,
    ManualEntryRequest,
    NotificationCaptureRequest,
)
from app.services.nlp_service import nlp_service, NLPResult
from app.services.risk_engine import risk_engine, RiskResult
from app.services.nudge_generator import nudge_generator

logger = logging.getLogger(__name__)


class BaseIngestionAdapter:
    """Shared persistence + pipeline logic for all adapters."""

    def _run_pipeline(
        self,
        event: FoodEvent,
        food_text: str,
        db: Session,
        is_partial: bool = False,
    ) -> tuple[NLPResult, RiskResult]:
        """Run NLP → scoring pipeline and persist results."""

        # 1. NLP
        nlp_result = nlp_service.analyze(food_text, is_partial=is_partial)

        # 2. Persist normalized text back to event
        event.normalized_food_text = nlp_result.normalized_text
        event.is_processed = True
        db.flush()

        # 3. Persist Classification
        classification = FoodClassification(
            event_id=event.id,
            food_category=nlp_result.food_category,
            risk_tags=json.dumps(nlp_result.risk_tags),
            matched_keywords=json.dumps(nlp_result.matched_keywords),
            confidence=nlp_result.confidence,
            parse_quality=nlp_result.parse_quality,
        )
        db.add(classification)
        db.flush()

        # 4. Risk Score
        risk_result = risk_engine.score(
            nlp_result=nlp_result,
            event_dt=event.event_timestamp,
            user_id=event.user_id,
            db=db,
        )

        # 5. Persist Risk Score
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

        # 6. Generate nudge
        nudge_output = nudge_generator.generate(
            nlp_result=nlp_result,
            risk_result=risk_result,
            behavior_label=risk_result.behavior_label,
        )

        # 7. Persist Nudge
        nudge_row = Nudge(
            event_id=event.id,
            user_id=event.user_id,
            nudge_text=nudge_output.nudge_text,
            healthier_swap=nudge_output.healthier_swap,
            nudge_type=nudge_output.nudge_type,
        )
        db.add(nudge_row)
        db.commit()
        db.refresh(event)

        return nlp_result, risk_result, nudge_output

    def _build_response(
        self,
        event: FoodEvent,
        nlp_result: NLPResult,
        risk_result: RiskResult,
        nudge_output,
    ) -> FoodAnalysisResponse:
        return FoodAnalysisResponse(
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
            event_timestamp=event.event_timestamp,
            classification=ClassificationResult(
                food_category=nlp_result.food_category,
                risk_tags=nlp_result.risk_tags,
                matched_keywords=nlp_result.matched_keywords,
                confidence=nlp_result.confidence,
                parse_quality=nlp_result.parse_quality,
            ),
            score_detail=RiskScoreResult(
                base_food_risk=risk_result.base_food_risk,
                time_multiplier=risk_result.time_multiplier,
                behavior_multiplier=risk_result.behavior_multiplier,
                final_risk_score=risk_result.final_risk_score,
                risk_band=risk_result.risk_band,
            ),
        )


class ManualEntryAdapter(BaseIngestionAdapter):
    """
    Handles manually entered food text from the mobile app.
    Text is assumed reasonably clean but still goes through full NLP pipeline.
    """

    def ingest(
        self,
        payload: ManualEntryRequest,
        user_id: int,
        db: Session,
    ) -> FoodAnalysisResponse:
        event_dt = payload.event_timestamp or datetime.now(timezone.utc)

        # 1. Persist raw event
        event = FoodEvent(
            user_id=user_id,
            source_type="manual",
            source_app=None,
            raw_food_text=payload.food_text,
            raw_notification_text=None,
            event_timestamp=event_dt,
            latitude=payload.latitude,
            longitude=payload.longitude,
            pincode=payload.pincode,
            meal_type=payload.meal_type,
        )
        db.add(event)
        db.flush()

        # 2. Run pipeline
        nlp_result, risk_result, nudge_output = self._run_pipeline(
            event=event,
            food_text=payload.food_text,
            db=db,
            is_partial=False,
        )

        return self._build_response(event, nlp_result, risk_result, nudge_output)


class NotificationCaptureAdapter(BaseIngestionAdapter):
    """
    Handles food events captured from Android notification listener.
    
    IMPORTANT: Notification text is noisy and incomplete.
    - Store the raw notification text always (audit trail)
    - Extract food text best-effort
    - Mark parse_quality appropriately
    - Never fail the response — return best-effort partial analysis
    - Future: plug in per-app parsers (ZomatoParser, SwiggyParser)
    """

    SUPPORTED_APPS = {"zomato", "swiggy", "blinkit", "zepto", "dunzo"}

    def _extract_food_text_from_notification(
        self, raw_text: str, source_app: str
    ) -> tuple[str, bool]:
        """
        Best-effort food text extraction from notification text.
        Returns (extracted_text, is_partial).
        
        Future: plug in per-app structured parsers here.
        """
        if not raw_text:
            return "", True

        import re

        # Common order confirmation patterns
        patterns = [
            r"(?:you ordered|order confirmed|items?[:：]\s*)(.+?)(?:\.|from|for ₹|at|\n|$)",
            r"(.+?)(?:has been placed|is confirmed|is on its way)",
            r"(?:delivering|preparing)\s+(.+?)(?:\.|from|for|\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) > 3:
                    return extracted, False

        # Fallback: use the whole text but mark as partial
        cleaned = re.sub(r"[^\w\s,]", " ", raw_text)
        cleaned = " ".join(cleaned.split())
        return cleaned[:300], True  # cap length; mark partial

    def ingest(
        self,
        payload: NotificationCaptureRequest,
        user_id: int,
        db: Session,
    ) -> FoodAnalysisResponse:
        event_dt = payload.event_timestamp or datetime.now(timezone.utc)
        source_app = payload.source_app.lower().strip()

        # Determine food text: use explicitly provided or extract from raw
        if payload.raw_food_text and len(payload.raw_food_text.strip()) > 3:
            food_text = payload.raw_food_text
            is_partial = False
        else:
            food_text, is_partial = self._extract_food_text_from_notification(
                payload.raw_notification_text, source_app
            )

        # 1. Persist raw event (always — even if extraction fails)
        event = FoodEvent(
            user_id=user_id,
            source_type="notification",
            source_app=source_app,
            raw_food_text=food_text or None,
            raw_notification_text=payload.raw_notification_text,
            event_timestamp=event_dt,
            latitude=payload.latitude,
            longitude=payload.longitude,
            pincode=payload.pincode,
        )
        db.add(event)
        db.flush()

        # 2. Run pipeline (graceful even if text is partial)
        nlp_result, risk_result, nudge_output = self._run_pipeline(
            event=event,
            food_text=food_text or payload.raw_notification_text or "unknown food",
            db=db,
            is_partial=is_partial,
        )

        return self._build_response(event, nlp_result, risk_result, nudge_output)


# Singleton adapter instances
manual_entry_adapter = ManualEntryAdapter()
notification_capture_adapter = NotificationCaptureAdapter()
