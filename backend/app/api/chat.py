"""
NightBite AI — Legacy Chat Endpoint (Claude-powered)

Preserved for backward compatibility with the existing Flutter /chat endpoint.
New frontend should use /ai-coach endpoints for richer interactions.
AI Provider: Anthropic Claude only.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.food_event import FoodEvent, RiskScore
from app.services.claude_service import call_claude_text
from app.services.late_night_utils import (
    current_late_night_context, is_late_night, normalize_food_name, hour_to_time_label
)

router = APIRouter(prefix="/chat", tags=["chat"])

_COACH_SYSTEM = """You are NightBite Coach — a warm, supportive, non-preachy health and nutrition coach
specialising in late-night eating habits for Indian users. The app tracks food orders between
10 PM and 4 AM for NCD risk awareness.
- Reply in 2-4 short sentences (under 90 words total)
- Be warm and encouraging, not preachy
- Give practical Indian-friendly food suggestions when asked
- Never say "you should", "you must", "avoid" — keep it supportive
- Return plain text only, no markdown, no bullet points"""


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    used_history: bool = False


@router.post("", response_model=ChatResponse)
def ai_coach_chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """AI Coach Chat — personalised using user's late-night order history."""

    # Pull recent history (last 14 days)
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    rows = (
        db.query(FoodEvent, RiskScore)
        .outerjoin(RiskScore, RiskScore.event_id == FoodEvent.id)
        .filter(FoodEvent.user_id == current_user.id)
        .filter(FoodEvent.event_timestamp >= two_weeks_ago)
        .filter(FoodEvent.is_processed == True)
        .order_by(FoodEvent.event_timestamp.desc())
        .limit(15)
        .all()
    )

    has_history = len(rows) > 0
    if has_history:
        lines = []
        for event, risk in rows:
            food_name = normalize_food_name(event.normalized_food_text or event.raw_food_text or "Unknown food")
            score = f"{risk.final_risk_score:.1f}/10" if risk else "?"
            band = (risk.risk_band or "unknown").upper() if risk else "UNKNOWN"
            time_str = hour_to_time_label(event.event_timestamp.hour)
            late = "🌙" if is_late_night(event.event_timestamp) else ""
            lines.append(f"• {food_name} at {time_str} {late} → Risk {score} ({band})")
        history_block = "\n".join(lines)
    else:
        history_block = "No recent logs yet. Encourage the user to start logging food."

    time_ctx = current_late_night_context()

    prompt = f"""Current time context: {time_ctx['context_text']} (It is {time_ctx['label']})

User's recent food history from NightBite app (last 14 days):
{history_block}

User message: "{payload.message.strip()}"

Answer the user's message directly. Reference their history only if genuinely relevant."""

    reply = call_claude_text(prompt=prompt, system=_COACH_SYSTEM, max_tokens=300, timeout_seconds=25.0)

    if not reply:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Coach is temporarily unavailable. Claude did not return a response. Please try again.",
        )

    return ChatResponse(reply=reply.strip(), used_history=has_history)


@router.post("/public", response_model=ChatResponse)
def ai_coach_chat_public(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Public AI Coach endpoint — no auth required.
    General coaching without user-specific history.
    """
    time_ctx = current_late_night_context()

    prompt = f"""Current time context: {time_ctx['context_text']} (It is {time_ctx['label']})

User message: "{payload.message.strip()}"

Answer the user's message with general late-night food coaching advice for Indian users."""

    reply = call_claude_text(prompt=prompt, system=_COACH_SYSTEM, max_tokens=300, timeout_seconds=25.0)

    if not reply:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Coach is temporarily unavailable. Claude did not return a response.",
        )

    return ChatResponse(reply=reply.strip(), used_history=False)
