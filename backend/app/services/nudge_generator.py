"""
NightBite AI — Nudge Generator (Claude-powered)

Generates contextual smart nudges and healthier swaps.
Uses claude_service.py as the AI backend (centralized, no duplicate init).
Falls back gracefully to deterministic templates if Claude fails.
AI provider: Anthropic Claude only.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Optional

from app.services.nlp_service import NLPResult
from app.services.risk_engine import RiskResult
from app.services.claude_service import call_claude_json_with_retry
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Fallback Templates ────────────────────────────────────────────────────────

HEALTHIER_SWAPS: dict[str, Optional[str]] = {
    "fast_food": "Try a grilled option or a whole-grain wrap instead.",
    "indian_fried": "Baked or air-fried snacks have the same crunch with fewer calories.",
    "rice_dish": "Swap to brown rice or cut the portion in half — your body will thank you.",
    "noodles_pasta": "Zucchini noodles or whole-grain pasta are great swaps.",
    "kebab_grill": "Tandoori options are typically lower in fat — solid late-night choice!",
    "dessert": "A small portion of dark chocolate or fresh fruit satisfies the craving.",
    "beverage_unhealthy": "Try lemon water, coconut water, or a zero-sugar version.",
    "beverage_healthy": None,
    "healthy_food": None,
    "snack": "Roasted makhana, nuts, or a small fruit are satisfying and lighter.",
    "meat": "Consider a lean protein like grilled chicken or fish.",
    "unknown": "A light homemade option is often the best bet at this hour.",
}

LOW_RISK_NUDGES = [
    "Looks like a lighter choice — great call for this hour! 🙂",
    "Low risk food choice — your body will appreciate it.",
    "Smart pick for late night. Keep it up!",
    "That's a thoughtful food choice — enjoy it!",
]

MODERATE_NUDGES = [
    "Not bad, but keep the portion in check at this hour.",
    "Moderate risk — a smaller serving makes this much better.",
    "Balance it with plenty of water before sleep.",
    "Decent choice — just watch the serving size tonight.",
]

HIGH_RISK_NUDGES = [
    "Heavy choices at night are processed slowly — even a smaller portion helps a lot.",
    "Your body metabolizes heavy foods slowly past midnight.",
    "Fried food at this hour is tough on digestion — grilled tastes just as good.",
    "High-calorie choice late at night — consider the lighter version next time.",
]

CRITICAL_NUDGES = [
    "This combo at {time_label} is one of the highest-risk patterns — you've still got this though!",
    "High sugar + late night = tough on your metabolism. A lighter option will still satisfy.",
    "Critical risk at this hour. Even skipping one item from the order helps a lot.",
    "Your night-time metabolism slows down significantly — this one is worth swapping next time.",
]


# ── Claude Nudge Generation ───────────────────────────────────────────────────

_NUDGE_PROMPT_TEMPLATE = """You are NightBite AI, a supportive late-night food health advisor for an Indian audience.
The app tracks late-night food orders (10 PM – 4 AM) for NCD risk awareness.

A user just logged this food item:
- Food: "{food_text}"
- Category: {category}
- Risk Score: {risk_score:.1f} / 10
- Risk Band: {risk_band}
- Time of day: {time_label}
- Risk tags: {tags}

Return ONLY a JSON object with exactly these keys:

{{"nudge": "One supportive, non-preachy sentence (max 20 words). Be warm, not moralizing. If low risk, be positive. If high risk, be realistic but encouraging.", "swap": "One specific healthier food alternative for Indian context (max 15 words). Write null if food is already healthy or low risk."}}

Rules:
- Never use "you should", "you must", "avoid", "stop eating"
- Be culturally aware of Indian food (biryani, samosa, chai, makhana, etc.)
- Keep tone friendly — like a supportive friend, not a doctor
- If {time_label} contains "am" (midnight or later), gently acknowledge the late hour
- If category is beverage_healthy or healthy_food, swap must be null
- Return valid JSON only, no markdown, no extra text"""

_NUDGE_STRICT_PROMPT = """Return ONLY this JSON (no other text, no markdown):
{{"nudge": "short supportive message max 20 words", "swap": "healthier alternative or null"}}
Context: {food_text} | Risk: {risk_band} | Time: {time_label}"""


def _claude_nudge(
    food_text: str,
    category: Optional[str],
    risk_score: float,
    risk_band: str,
    time_label: str,
    tags: list[str],
) -> Optional[tuple[str, Optional[str]]]:
    """Use Claude via centralized service to generate nudge + swap."""
    if not settings.ENABLE_LLM_ENHANCEMENT or not settings.CLAUDE_API_KEY:
        return None

    prompt = _NUDGE_PROMPT_TEMPLATE.format(
        food_text=food_text[:200],
        category=category or "unknown",
        risk_score=risk_score,
        risk_band=risk_band,
        time_label=time_label,
        tags=", ".join(tags) if tags else "none",
    )

    strict = _NUDGE_STRICT_PROMPT.format(
        food_text=food_text[:100],
        risk_band=risk_band,
        time_label=time_label,
    )

    result = call_claude_json_with_retry(
        prompt=prompt,
        strict_prompt=strict,
        expected_keys=["nudge"],
        timeout_seconds=settings.AI_TIMEOUT_SECONDS,
    )

    if result is None:
        return None

    nudge_text = str(result.get("nudge", "")).strip()
    swap_raw = result.get("swap")
    swap = None if (swap_raw is None or str(swap_raw).lower() in ("null", "none", "")) else str(swap_raw).strip()

    if not nudge_text:
        return None

    return nudge_text, swap


# ── Fallback Logic ────────────────────────────────────────────────────────────

def _template_nudge(
    category: Optional[str],
    risk_band: str,
    time_label: str,
    tags: list[str],
) -> tuple[str, Optional[str]]:
    """Deterministic template-based fallback."""
    if risk_band == "low":
        nudge_text = random.choice(LOW_RISK_NUDGES)
    elif risk_band == "moderate":
        nudge_text = random.choice(MODERATE_NUDGES)
    elif risk_band == "high":
        nudge_text = random.choice(HIGH_RISK_NUDGES)
    else:  # critical
        nudge_text = random.choice(CRITICAL_NUDGES).replace("{time_label}", time_label)

    return nudge_text, HEALTHIER_SWAPS.get(category or "unknown")


# ── Output Dataclass ──────────────────────────────────────────────────────────

@dataclass
class NudgeOutput:
    nudge_text: str
    healthier_swap: Optional[str]
    nudge_type: str  # ai_generated | risk_warning | positive


# ── Public Generator ──────────────────────────────────────────────────────────

class NudgeGenerator:
    """
    Claude-powered nudge engine with deterministic fallback.
    Uses the centralized claude_service.py — no duplicate AI client init.
    """

    def generate(
        self,
        nlp_result: NLPResult,
        risk_result: RiskResult,
        behavior_label: str,
    ) -> NudgeOutput:
        band = risk_result.risk_band
        category = nlp_result.food_category
        tags = nlp_result.risk_tags
        time_label = risk_result.time_label
        food_text = nlp_result.normalized_text
        risk_score = risk_result.final_risk_score

        # Try Claude first
        claude_result = _claude_nudge(
            food_text=food_text,
            category=category,
            risk_score=risk_score,
            risk_band=band,
            time_label=time_label,
            tags=tags,
        )

        if claude_result:
            nudge_text, healthier_swap = claude_result
            nudge_type = "ai_generated"
            logger.info(f"Claude nudge OK for: {food_text[:40]!r}")
        else:
            nudge_text, healthier_swap = _template_nudge(category, band, time_label, tags)
            nudge_type = "positive" if band == "low" else "risk_warning"
            logger.info(f"Template nudge used for: {food_text[:40]!r}")

        return NudgeOutput(
            nudge_text=nudge_text.strip(),
            healthier_swap=healthier_swap,
            nudge_type=nudge_type,
        )


nudge_generator = NudgeGenerator()
