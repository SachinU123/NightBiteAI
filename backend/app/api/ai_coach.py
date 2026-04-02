"""
NightBite AI — AI Coach Endpoints (Claude-powered)

All AI Coach functionality uses Anthropic Claude exclusively.

Endpoints:
  POST /ai-coach/chat              — Personalized AI coach chat
  POST /ai-coach/chat/public       — Public chat (no auth required)
  POST /ai-coach/explain           — Explain a food event or pattern
  POST /ai-coach/smart-swap        — Get healthier swap with AI reasoning
  GET  /ai-coach/weekly-summary    — AI-generated weekly behavior summary
  GET  /ai-coach/monthly-summary   — AI-generated monthly behavior summary
  POST /ai-coach/item-insight      — Item-specific late-night trend explanation
"""
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.food_event import FoodEvent, RiskScore
from app.schemas.food import (
    AIChatRequest,
    AIChatResponse,
    AIExplainRequest,
    AICoachResponse,
    SmartSwapRequest,
    SmartSwapResponse,
)
from app.services.claude_service import call_claude_text, call_claude_structured
from app.services.late_night_utils import (
    is_late_night,
    normalize_food_name,
    current_late_night_context,
    hour_to_time_label,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-coach", tags=["ai-coach"])

# ── System prompts ─────────────────────────────────────────────────────────────

_COACH_SYSTEM = """You are NightBite Coach — a warm, knowledgeable, and supportive health and nutrition coach
specializing in late-night eating habits for Indian users. The NightBite app tracks food orders
placed between 10 PM and 4 AM to help users understand their NCD (non-communicable disease) risk patterns.

Your personality:
- Warm, encouraging, never preachy or scolding
- Culturally aware of Indian food (biryani, samosa, chai, makhana, dosa, etc.)
- Evidence-informed but conversational
- You use "you" informally and speak like a supportive friend, not a doctor
- Never use: "you should", "you must", "avoid", "stop eating"
- Brief and actionable, not overwhelming

Your focus is specifically: late-night (10 PM – 4 AM) food ordering behavior and NCD risk."""

_STRUCTURED_COACH_SYSTEM = """You are NightBite Coach, an AI health advisor for late-night food habits.
Return ONLY valid JSON — no markdown, no explanations outside the JSON.
Focus on late-night (10 PM – 4 AM) food ordering patterns and NCD risk for Indian users."""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_recent_history_block(user_id: int, db: Session, days: int = 14, limit: int = 15) -> tuple[str, bool]:
    """Fetch and format recent history for AI prompt context. Returns (block_text, has_history)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(FoodEvent, RiskScore)
        .outerjoin(RiskScore, RiskScore.event_id == FoodEvent.id)
        .filter(FoodEvent.user_id == user_id)
        .filter(FoodEvent.event_timestamp >= since)
        .filter(FoodEvent.is_processed == True)
        .order_by(FoodEvent.event_timestamp.desc())
        .limit(limit)
        .all()
    )

    if not rows:
        return "No recent food orders logged yet.", False

    lines = []
    for event, risk in rows:
        food_name = event.normalized_food_text or event.raw_food_text or "Unknown food"
        food_name = normalize_food_name(food_name)
        score = f"{risk.final_risk_score:.1f}/10" if risk else "?"
        band = (risk.risk_band or "unknown").upper() if risk else "UNKNOWN"
        hour = event.event_timestamp.hour
        time_str = hour_to_time_label(hour)
        late = "🌙" if is_late_night(event.event_timestamp) else ""
        lines.append(f"• {food_name} at {time_str} {late} → Risk {score} ({band})")

    return "\n".join(lines), True


def _fallback_reply(context_source: str = "chat") -> str:
    """Fallback reply when Claude is unavailable."""
    if context_source in ("home", "profile"):
        return "Your late-night patterns are being tracked. Keep logging to see personalized insights!"
    return (
        "Hey! I'm here to help you make better late-night choices. "
        "Try asking me what to eat right now, or how to reduce late-night cravings!"
    )


# ── Chat Endpoints ─────────────────────────────────────────────────────────────

@router.post("/chat", response_model=AIChatResponse)
def ai_coach_chat(
    payload: AIChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Personalized AI Coach chat using Claude.
    Pulls the user's recent late-night order history for context.
    """
    history_block, has_history = _get_recent_history_block(current_user.id, db)
    time_ctx = current_late_night_context()

    prompt = f"""Current time context: {time_ctx['context_text']} (It is {time_ctx['label']})

User's recent food history from NightBite app (last 14 days):
{history_block}

User's message: "{payload.message.strip()}"

Instructions:
- Reply in 2-4 short sentences (under 90 words total)
- Be warm and encouraging, not preachy
- Reference their actual history ONLY if it's genuinely relevant and helpful
- Give practical Indian-friendly food suggestions when asked
- If past midnight, gently acknowledge the late hour
- Return plain text only, no markdown, no bullet points"""

    reply = call_claude_text(
        prompt=prompt,
        system=_COACH_SYSTEM,
        max_tokens=300,
        timeout_seconds=25.0,
    )

    if not reply:
        reply = _fallback_reply(payload.context_source or "chat")

    return AIChatResponse(
        reply=reply.strip(),
        used_history=has_history,
        context_source=payload.context_source or "chat",
    )


@router.post("/chat/public", response_model=AIChatResponse)
def ai_coach_chat_public(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
):
    """
    Public AI Coach endpoint — no auth required.
    Used as fallback for unauthenticated or token-expired states.
    """
    time_ctx = current_late_night_context()

    prompt = f"""Current time context: {time_ctx['context_text']} (It is {time_ctx['label']})

User message: "{payload.message.strip()}"

Instructions:
- Reply in 2-4 short sentences (under 90 words total)
- Be warm and encouraging
- Give practical Indian-friendly food suggestions when asked
- Return plain text only, no markdown, no bullet points"""

    reply = call_claude_text(
        prompt=prompt,
        system=_COACH_SYSTEM,
        max_tokens=300,
        timeout_seconds=25.0,
    )

    if not reply:
        reply = _fallback_reply("chat")

    return AIChatResponse(
        reply=reply.strip(),
        used_history=False,
        context_source="public",
    )


# ── Explain Endpoint ───────────────────────────────────────────────────────────

@router.post("/explain", response_model=AICoachResponse)
def ai_explain(
    payload: AIExplainRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get an AI explanation of a food event, pattern, or recent behavior.
    Can take an event_id or food_name or free-form context.
    Returns a structured Flutter-friendly response.
    """
    # Resolve context
    context_parts = []
    food_label = "food order"
    risk_band = "moderate"
    healthier_swap = None

    if payload.event_id:
        event = db.query(FoodEvent).filter(
            FoodEvent.id == payload.event_id,
            FoodEvent.user_id == current_user.id,
        ).first()
        if event:
            food_label = normalize_food_name(event.normalized_food_text)
            hour = event.event_timestamp.hour
            time_label = hour_to_time_label(hour)
            is_ln = is_late_night(event.event_timestamp)
            context_parts.append(f"Food ordered: {food_label}")
            context_parts.append(f"Time: {time_label}")
            context_parts.append(f"Late-night window: {'Yes' if is_ln else 'No'}")
            if event.risk_score:
                band = event.risk_score.risk_band
                context_parts.append(f"Risk score: {event.risk_score.final_risk_score:.1f}/10 ({band.upper()})")
                risk_band = band
            if event.nudge and event.nudge.healthier_swap:
                healthier_swap = event.nudge.healthier_swap

    if payload.food_name:
        food_label = payload.food_name
        context_parts.append(f"Food item: {payload.food_name}")

    if payload.context:
        context_parts.append(f"Additional context: {payload.context}")

    # Also add recent history
    history_block, has_history = _get_recent_history_block(current_user.id, db, days=7, limit=8)

    is_detailed = payload.mode == "detailed"
    max_tokens = 700 if is_detailed else 400

    user_message = f"""Context:
{chr(10).join(context_parts) if context_parts else "General late-night food behavior inquiry"}

User's recent 7-day history:
{history_block}

Generate a structured explanation for the NightBite app.

Return ONLY this JSON:
{{
  "title": "Short engaging title (max 8 words)",
  "short_summary": "1-2 sentence summary of the risk or insight (max 50 words)",
  "detailed_explanation": {"'2-3 sentences with more detail about the late-night risk and pattern. Reference Indian food culture where relevant. Max 100 words.'" if is_detailed else "null"},
  "suggestions": ["Practical suggestion 1", "Practical suggestion 2", "Practical suggestion 3"],
  "follow_up_prompts": ["Follow-up question 1", "Follow-up question 2"],
  "healthier_swap": {"f'Specific healthier swap for {food_label}'" if food_label != "food order" else "null"},
  "risk_tag": "{risk_band}"
}}"""

    result = call_claude_structured(
        system=_STRUCTURED_COACH_SYSTEM,
        user_message=user_message,
        expected_keys=["title", "short_summary", "suggestions"],
        max_tokens=max_tokens,
        timeout_seconds=30.0,
    )

    if result:
        suggestions = result.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = []
        follow_ups = result.get("follow_up_prompts", [])
        if not isinstance(follow_ups, list):
            follow_ups = []

        swap = result.get("healthier_swap") or healthier_swap
        if swap and str(swap).lower() in ("null", "none", ""):
            swap = healthier_swap

        return AICoachResponse(
            title=str(result.get("title", "Late-Night Food Insight")),
            short_summary=str(result.get("short_summary", "")),
            detailed_explanation=result.get("detailed_explanation") if is_detailed else None,
            suggestions=[str(s) for s in suggestions[:3]],
            follow_up_prompts=[str(f) for f in follow_ups[:2]],
            healthier_swap=swap,
            risk_tag=str(result.get("risk_tag", risk_band)),
            ai_powered=True,
        )

    # Fallback
    return AICoachResponse(
        title=f"About Your {food_label} Order",
        short_summary=(
            "Late-night food orders can increase NCD risk due to slower metabolism at night. "
            "Small swaps and timing adjustments make a big difference."
        ),
        suggestions=[
            "Try ordering before 10 PM when your body processes food better.",
            "Consider a lighter version of your favorite item.",
            "Drink a glass of water before ordering to check if you're truly hungry.",
        ],
        follow_up_prompts=[
            "What's a healthier option I can order right now?",
            "How does late-night eating affect my health?",
        ],
        healthier_swap=healthier_swap,
        risk_tag=risk_band,
        ai_powered=False,
    )


# ── Smart Swap Endpoint ────────────────────────────────────────────────────────

@router.post("/smart-swap", response_model=SmartSwapResponse)
def smart_swap(
    payload: SmartSwapRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a Claude-generated healthier swap recommendation for a specific food item.
    Returns structured swap reasoning suitable for Flutter's smart swap UI.
    """
    time_ctx = current_late_night_context()

    user_message = f"""A user is ordering {payload.food_name} at {time_ctx['label']} (late-night window).

Additional context: {payload.context or 'None provided'}

Generate a healthier swap recommendation for the NightBite app.

Return ONLY this JSON:
{{
  "swap_suggestion": "Specific healthier Indian food alternative (max 8 words)",
  "short_reason": "Why this swap helps (1 sentence, max 20 words)",
  "detailed_reason": "2 sentences with nutritional and timing context. Mention late-night metabolism. Max 60 words.",
  "risk_reduction_label": "Approximate risk improvement label like 'Reduces risk by ~30%' or 'Significantly lighter'"
}}"""

    result = call_claude_structured(
        system=_STRUCTURED_COACH_SYSTEM,
        user_message=user_message,
        expected_keys=["swap_suggestion", "short_reason"],
        max_tokens=400,
        timeout_seconds=25.0,
    )

    if result:
        return SmartSwapResponse(
            food_name=payload.food_name,
            swap_suggestion=str(result.get("swap_suggestion", "A lighter home-cooked option")),
            short_reason=str(result.get("short_reason", "Lighter options are processed better at night.")),
            detailed_reason=result.get("detailed_reason"),
            risk_reduction_label=result.get("risk_reduction_label"),
            ai_powered=True,
        )

    return SmartSwapResponse(
        food_name=payload.food_name,
        swap_suggestion="Grilled or baked version",
        short_reason="Heavy fried foods slow down your night-time metabolism.",
        detailed_reason=(
            "Your body's metabolism slows significantly after 10 PM. "
            "Lighter, grilled, or high-protein options are processed much more efficiently at night."
        ),
        risk_reduction_label="Generally ~25–35% lighter",
        ai_powered=False,
    )


# ── Weekly Summary ─────────────────────────────────────────────────────────────

@router.get("/weekly-summary", response_model=AICoachResponse)
def get_weekly_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a Claude-generated summary of the user's weekly late-night ordering behavior.
    """
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    week_events = (
        db.query(FoodEvent)
        .filter(
            FoodEvent.user_id == current_user.id,
            FoodEvent.event_timestamp >= week_ago,
            FoodEvent.is_processed == True,
        )
        .order_by(FoodEvent.event_timestamp.desc())
        .all()
    )

    if not week_events:
        return AICoachResponse(
            title="Start Your Late-Night Journey",
            short_summary="No orders logged this week yet. Start capturing your late-night food choices to unlock personalized insights!",
            suggestions=[
                "Enable notification capture to automatically log food delivery orders.",
                "Or manually log a food item using the + button.",
            ],
            ai_powered=False,
        )

    ln_events = [ev for ev in week_events if is_late_night(ev.event_timestamp)]
    risk_scores = [ev.risk_score.final_risk_score for ev in week_events if ev.risk_score]
    food_names = [normalize_food_name(ev.normalized_food_text) for ev in week_events if ev.normalized_food_text]
    top_food = Counter(food_names).most_common(1)[0][0] if food_names else "Unknown"
    avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
    high_risk = sum(1 for ev in week_events if ev.risk_score and ev.risk_score.risk_band in ("high", "critical"))

    weeks_data = (
        f"Total orders this week: {len(week_events)}\n"
        f"Late-night orders: {len(ln_events)}\n"
        f"Average risk score: {avg_risk}/10\n"
        f"High-risk orders: {high_risk}\n"
        f"Most ordered: {top_food}"
    )

    user_message = f"""Weekly late-night food behavior summary for NightBite app:

{weeks_data}

Generate a weekly summary response. Return ONLY this JSON:
{{
  "title": "Weekly summary title (max 8 words, engaging)",
  "short_summary": "2-sentence summary of the week's pattern (max 60 words). Be specific, reference the data.",
  "detailed_explanation": "2-3 sentences of behavioral insight and encouragement. Reference late-night risk patterns. Max 80 words.",
  "suggestions": ["Actionable suggestion 1", "Actionable suggestion 2", "Actionable suggestion 3"],
  "follow_up_prompts": ["Question 1", "Question 2"],
  "risk_tag": "{('critical' if avg_risk >= 8 else 'high' if avg_risk >= 5.5 else 'moderate' if avg_risk >= 3 else 'low')}"
}}"""

    result = call_claude_structured(
        system=_STRUCTURED_COACH_SYSTEM,
        user_message=user_message,
        expected_keys=["title", "short_summary"],
        max_tokens=600,
        timeout_seconds=30.0,
    )

    if result:
        suggestions = result.get("suggestions", [])
        follow_ups = result.get("follow_up_prompts", [])
        return AICoachResponse(
            title=str(result.get("title", "Your Weekly Recap")),
            short_summary=str(result.get("short_summary", "")),
            detailed_explanation=result.get("detailed_explanation"),
            suggestions=[str(s) for s in (suggestions if isinstance(suggestions, list) else [])[:3]],
            follow_up_prompts=[str(f) for f in (follow_ups if isinstance(follow_ups, list) else [])[:2]],
            risk_tag=str(result.get("risk_tag", "moderate")),
            ai_powered=True,
        )

    return AICoachResponse(
        title="Your Week in Review",
        short_summary=f"You made {len(week_events)} food orders this week, {len(ln_events)} during the late-night window.",
        suggestions=[
            "Try shifting dinner earlier to reduce late-night cravings.",
            "Keep a glass of water by the bed — thirst is often mistaken for hunger.",
            "Check your repeat items to find easier, healthier swaps.",
        ],
        risk_tag="moderate",
        ai_powered=False,
    )


# ── Monthly Summary ────────────────────────────────────────────────────────────

@router.get("/monthly-summary", response_model=AICoachResponse)
def get_monthly_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a Claude-generated monthly late-night behavior summary.
    """
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)

    month_events = (
        db.query(FoodEvent)
        .filter(
            FoodEvent.user_id == current_user.id,
            FoodEvent.event_timestamp >= month_ago,
            FoodEvent.is_processed == True,
        )
        .order_by(FoodEvent.event_timestamp.desc())
        .all()
    )

    if not month_events:
        return AICoachResponse(
            title="No Orders This Month Yet",
            short_summary="Start logging your late-night food orders to build a monthly trend.",
            ai_powered=False,
        )

    ln_events = [ev for ev in month_events if is_late_night(ev.event_timestamp)]
    risk_scores = [ev.risk_score.final_risk_score for ev in month_events if ev.risk_score]
    food_names = [normalize_food_name(ev.normalized_food_text) for ev in month_events if ev.normalized_food_text]
    top_foods = Counter(food_names).most_common(3)
    avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
    ln_pct = round(len(ln_events) / max(len(month_events), 1) * 100)

    monthly_data = (
        f"Total orders this month: {len(month_events)}\n"
        f"Late-night orders: {len(ln_events)} ({ln_pct}%)\n"
        f"Average risk score: {avg_risk}/10\n"
        f"Top foods: {', '.join(f[0] for f in top_foods)}"
    )

    user_message = f"""Monthly late-night food behavior for NightBite app:

{monthly_data}

Generate a monthly summary. Return ONLY this JSON:
{{
  "title": "Monthly insight title (max 8 words)",
  "short_summary": "2-sentence monthly pattern summary (max 60 words). Mention late-night specific patterns.",
  "detailed_explanation": "3 sentences on monthly trends, NCD risk context, and encouragement. Max 100 words.",
  "suggestions": ["Monthly improvement tip 1", "Monthly improvement tip 2", "Monthly improvement tip 3"],
  "follow_up_prompts": ["Follow-up 1", "Follow-up 2"],
  "risk_tag": "{('critical' if avg_risk >= 8 else 'high' if avg_risk >= 5.5 else 'moderate' if avg_risk >= 3 else 'low')}"
}}"""

    result = call_claude_structured(
        system=_STRUCTURED_COACH_SYSTEM,
        user_message=user_message,
        expected_keys=["title", "short_summary"],
        max_tokens=700,
        timeout_seconds=30.0,
    )

    if result:
        suggestions = result.get("suggestions", [])
        follow_ups = result.get("follow_up_prompts", [])
        return AICoachResponse(
            title=str(result.get("title", "Your Monthly Overview")),
            short_summary=str(result.get("short_summary", "")),
            detailed_explanation=result.get("detailed_explanation"),
            suggestions=[str(s) for s in (suggestions if isinstance(suggestions, list) else [])[:3]],
            follow_up_prompts=[str(f) for f in (follow_ups if isinstance(follow_ups, list) else [])[:2]],
            risk_tag=str(result.get("risk_tag", "moderate")),
            ai_powered=True,
        )

    return AICoachResponse(
        title="Your Month at a Glance",
        short_summary=f"You had {len(month_events)} food orders this month, {len(ln_events)} happening late at night.",
        suggestions=[
            "Try implementing a 10 PM cutoff for heavy food delivery.",
            "Look for pattern clusters — certain days tend to drive late-night ordering.",
            "Use the AI Coach when cravings hit to find lighter alternatives.",
        ],
        risk_tag="moderate",
        ai_powered=False,
    )


# ── Item Insight ───────────────────────────────────────────────────────────────

@router.post("/item-insight", response_model=AICoachResponse)
def get_item_insight(
    payload: AIExplainRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get an AI-generated insight for a specific food item's late-night pattern.
    Designed for the item detail drill-down screen in Flutter.
    """
    food_name = payload.food_name or "this food item"

    # Pull all history for this item
    events = (
        db.query(FoodEvent)
        .filter(
            FoodEvent.user_id == current_user.id,
            FoodEvent.is_processed == True,
            FoodEvent.normalized_food_text.ilike(f"%{food_name}%"),
        )
        .order_by(FoodEvent.event_timestamp.desc())
        .limit(20)
        .all()
    )

    total = len(events)
    ln_evs = [ev for ev in events if is_late_night(ev.event_timestamp)]
    risk_scores = [ev.risk_score.final_risk_score for ev in events if ev.risk_score]
    avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
    hours = [ev.event_timestamp.hour for ev in events]
    common_hour = Counter(hours).most_common(1)[0][0] if hours else 0
    time_label = hour_to_time_label(common_hour)

    healthier_swap = None
    for ev in events:
        if ev.nudge and ev.nudge.healthier_swap:
            healthier_swap = ev.nudge.healthier_swap
            break

    item_data = (
        f"Food item: {food_name}\n"
        f"Total orders in history: {total}\n"
        f"Late-night orders: {len(ln_evs)}\n"
        f"Average risk score: {avg_risk}/10\n"
        f"Most common ordering time: {time_label}"
    )

    user_message = f"""Late-night ordering pattern analysis for a specific food item:

{item_data}

Generate an item-specific insight for the NightBite app detail screen.

Return ONLY this JSON:
{{
  "title": "Insight title about this food (max 8 words)",
  "short_summary": "1-2 sentence item-specific insight referencing ordering frequency and risk (max 50 words)",
  "detailed_explanation": "2-3 sentences about why this food is particularly relevant late at night, any NCD risk factors, and what makes it worth watching. Max 80 words.",
  "suggestions": ["Specific to this food item — healthier way to enjoy it", "Timing suggestion", "Portion suggestion"],
  "follow_up_prompts": ["What's a good swap?", "When is the best time to order this?"],
  "healthier_swap": {"f'Swap suggestion for {food_name}'" if food_name != 'this food item' else "null"},
  "risk_tag": "{('critical' if avg_risk >= 8 else 'high' if avg_risk >= 5.5 else 'moderate' if avg_risk >= 3 else 'low')}"
}}"""

    result = call_claude_structured(
        system=_STRUCTURED_COACH_SYSTEM,
        user_message=user_message,
        expected_keys=["title", "short_summary"],
        max_tokens=600,
        timeout_seconds=30.0,
    )

    if result:
        suggestions = result.get("suggestions", [])
        follow_ups = result.get("follow_up_prompts", [])
        swap = result.get("healthier_swap") or healthier_swap
        if swap and str(swap).lower() in ("null", "none", ""):
            swap = healthier_swap
        return AICoachResponse(
            title=str(result.get("title", f"About Your {food_name}")),
            short_summary=str(result.get("short_summary", "")),
            detailed_explanation=result.get("detailed_explanation"),
            suggestions=[str(s) for s in (suggestions if isinstance(suggestions, list) else [])[:3]],
            follow_up_prompts=[str(f) for f in (follow_ups if isinstance(follow_ups, list) else [])[:2]],
            healthier_swap=swap,
            risk_tag=str(result.get("risk_tag", "moderate")),
            ai_powered=True,
        )

    return AICoachResponse(
        title=f"Your {food_name.title()} Pattern",
        short_summary=f"You've ordered {food_name} {total} times, with {len(ln_evs)} late-night orders.",
        suggestions=[
            f"Try a lighter version of {food_name} for late-night cravings.",
            "Consider scheduling this as a lunch or dinner choice instead.",
            "Reduce the portion size when ordering after 10 PM.",
        ],
        healthier_swap=healthier_swap,
        risk_tag="moderate",
        ai_powered=False,
    )
