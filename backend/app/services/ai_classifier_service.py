"""
NightBite AI — AI Classifier Service

Hybrid classifier pipeline:
  1. Deterministic rules (always runs, always produces a result)
  2. Claude enhancement (optional, runs if ENABLE_LLM_ENHANCEMENT=True)
  3. Merge results — Claude enriches, never replaces, deterministic baseline

Responsibilities:
  - Classify if notification is food-related
  - Detect if it's an actual order vs promo/irrelevant
  - Infer vendor/platform
  - Extract probable food items
  - Determine meal/snack type
  - Estimate health risk category
  - Generate short explanation
  - Output confidence score

Never blocks ingestion if Claude fails.
AI provider: Anthropic Claude only.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, List

from app.core.config import settings
from app.services.claude_service import call_claude_json_with_retry

logger = logging.getLogger(__name__)


# ── Known food-delivery app packages / names ──────────────────────────────────

FOOD_APP_PACKAGES = {
    "com.application.zomato": "Zomato",
    "in.swiggy.android": "Swiggy",
    "com.blinkit.consumer": "Blinkit",
    "com.grofers.customerapp": "Blinkit",
    "com.zeptoconsumer": "Zepto",
    "com.dunzo.user": "Dunzo",
    "com.ubercab.eats": "Uber Eats",
    "com.magicpin.partner": "Magicpin",
    "com.eatclub.app": "EatClub",
    "com.faasos.android": "Faasos",
    "com.freshmenu.android": "Freshmenu",
    "com.swiggy.android": "Swiggy",
    "com.zomato.android": "Zomato",
}

FOOD_APP_NAMES = {
    name.lower(): name for name in FOOD_APP_PACKAGES.values()
}

# Keyword signals
ORDER_POSITIVE_KEYWORDS = [
    "order placed", "order confirmed", "order accepted", "your order",
    "arriving", "delivered", "on its way", "out for delivery",
    "preparing", "heading your way", "delivery partner",
    "placed successfully", "restaurant accepted", "picked up",
    "delivery expected", "delivery boy", "arriving soon",
]

PROMO_KEYWORDS = [
    "offer", "discount", "% off", "free delivery", "coupon", "deal",
    "save", "cashback", "today only", "limited time", "use code",
    "flat", "extra off", "referral", "refer", "earn",
    "hurry", "grab", "exclusive", "flash sale", "this weekend",
]

FOOD_KEYWORDS = [
    "pizza", "burger", "biryani", "noodles", "pasta", "sandwich",
    "salad", "chicken", "mutton", "paneer", "roti", "rice",
    "dosa", "idli", "wrap", "roll", "fries", "shake", "combo",
    "meal", "thali", "curry", "kebab", "tikka", "shawarma",
    "momos", "sushi", "dessert", "cake", "ice cream", "coffee",
    "paratha", "dal", "sabzi", "veg", "non-veg", "manchurian",
    "chowmein", "fried rice", "spring roll", "samosa", "pakora",
    "pav bhaji", "chole", "rajma", "upma", "poha", "maggi",
    "pizza", "submarine", "sub", "hot dog", "taco", "quesadilla",
    "chai", "tea", "juice", "smoothie", "lassi", "milkshake",
]

HEALTH_RISK_CATEGORIES = {
    "low_risk": ["salad", "soup", "idli", "dosa", "oats", "fruit", "yogurt", "dal", "poha", "upma", "chai"],
    "medium_risk": ["sandwich", "wrap", "pasta", "rice", "roti", "paneer", "coffee", "paratha", "rajma", "chole"],
    "high_risk": ["pizza", "burger", "biryani", "fried", "fries", "shake", "ice cream", "manchurian", "maggi", "samosa"],
    "very_high_risk": ["deep fried", "cheese burst", "loaded", "extra cheese", "triple", "large", "double patty", "stuffed"],
}

MEAL_TYPE_HOURS = {
    "breakfast": (5, 10),
    "lunch": (11, 15),
    "snack": (15, 19),
    "dinner": (19, 22),
    "late_night": (22, 4),  # wraps around midnight
}


# ── Output Dataclass ──────────────────────────────────────────────────────────

@dataclass
class ClassificationOutput:
    is_food_related: bool
    is_order: bool
    is_promo: bool
    platform_name: Optional[str]
    vendor_name: Optional[str]
    probable_items: List[str]
    meal_type: Optional[str]
    health_risk_category: str   # low_risk | medium_risk | high_risk | very_high_risk | unknown
    explanation: str
    confidence: float           # 0.0–1.0
    used_claude: bool = False


# ── Deterministic Classifier ──────────────────────────────────────────────────

class DeterministicClassifier:
    """
    Rule-based food notification classifier.
    Always produces a result. Used as baseline and fallback.
    """

    def classify(
        self,
        app_package: Optional[str],
        app_name: Optional[str],
        title: Optional[str],
        text: Optional[str],
    ) -> ClassificationOutput:
        full_text = " ".join(filter(None, [title, text])).lower()
        pkg_lower = (app_package or "").lower()
        app_lower = (app_name or "").lower()

        # ── Platform detection ────────────────────────────────────────────────
        platform_name = None
        for pkg, name in FOOD_APP_PACKAGES.items():
            if pkg in pkg_lower:
                platform_name = name
                break
        if not platform_name:
            for pkg, name in FOOD_APP_PACKAGES.items():
                last_segment = pkg.split(".")[-1]
                if last_segment in pkg_lower or last_segment in app_lower:
                    platform_name = name
                    break

        if not platform_name:
            for known_name in FOOD_APP_NAMES:
                if known_name in app_lower or known_name in full_text:
                    platform_name = FOOD_APP_NAMES[known_name]
                    break

        # ── Is food related? ──────────────────────────────────────────────────
        is_food_app = platform_name is not None
        has_food_keywords = any(kw in full_text for kw in FOOD_KEYWORDS)
        is_food_related = is_food_app or has_food_keywords

        if not is_food_related:
            return ClassificationOutput(
                is_food_related=False,
                is_order=False,
                is_promo=False,
                platform_name=None,
                vendor_name=None,
                probable_items=[],
                meal_type=None,
                health_risk_category="unknown",
                explanation="Notification does not appear food-related.",
                confidence=0.85,
            )

        # ── Order vs promo detection ──────────────────────────────────────────
        order_signals = sum(1 for kw in ORDER_POSITIVE_KEYWORDS if kw in full_text)
        promo_signals = sum(1 for kw in PROMO_KEYWORDS if kw in full_text)
        is_promo = promo_signals > order_signals and order_signals == 0
        is_order = order_signals > 0

        # ── Probable items ────────────────────────────────────────────────────
        probable_items = [kw.title() for kw in FOOD_KEYWORDS if kw in full_text][:5]

        # ── Vendor name (simple extraction from title) ────────────────────────
        vendor_name = None
        vendor_patterns = [
            r"from (.+?)(?:\s+is|\s+has|\.|,|$)",
            r"your (.+?) order",
            r"(.+?) has accepted",
            r"(.+?) is preparing",
        ]
        for pattern in vendor_patterns:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                if 2 < len(candidate) < 60 and candidate.lower() not in ["your", "the", "a", "an"]:
                    vendor_name = candidate.title()
                    break

        # ── Health risk category ──────────────────────────────────────────────
        health_risk = "unknown"
        for category in ["very_high_risk", "high_risk", "medium_risk", "low_risk"]:
            if any(kw in full_text for kw in HEALTH_RISK_CATEGORIES[category]):
                health_risk = category
                break

        # ── Confidence ────────────────────────────────────────────────────────
        confidence_score = 0.5
        if is_food_app:
            confidence_score += 0.25
        if order_signals > 0:
            confidence_score += 0.15
        if probable_items:
            confidence_score += 0.1
        confidence_score = min(0.9, confidence_score)

        # ── Explanation ───────────────────────────────────────────────────────
        if is_promo:
            explanation = f"Promotional notification from {platform_name or 'a food app'}, not an actual order."
        elif is_order:
            explanation = (
                f"Food order detected via {platform_name or 'food delivery app'}"
                + (f" — {', '.join(probable_items[:2])}" if probable_items else "")
            )
        else:
            explanation = f"Possibly food-related notification from {platform_name or 'unknown app'}."

        return ClassificationOutput(
            is_food_related=is_food_related,
            is_order=is_order,
            is_promo=is_promo,
            platform_name=platform_name,
            vendor_name=vendor_name,
            probable_items=probable_items,
            meal_type=None,  # determined later
            health_risk_category=health_risk,
            explanation=explanation,
            confidence=confidence_score,
        )


# ── Claude Enhancement ────────────────────────────────────────────────────────

_CLAUDE_REQUIRED_KEYS = [
    "is_food_related", "is_order", "is_promo",
    "platform_name", "vendor_name", "probable_items",
    "meal_type", "health_risk_category", "explanation", "confidence"
]

_CLAUDE_PROMPT_TEMPLATE = """You are a food notification classifier for a health app called NightBite AI.
The app tracks late-night food ordering behavior (10 PM to 4 AM) for health analysis.

Analyze this Android notification and return ONLY a valid JSON object.

App Package: {app_package}
App Name: {app_name}
Notification Title: {title}
Notification Text: {text}

Return a JSON object with EXACTLY these keys (no extra text, no markdown, no explanation outside JSON):

{{
  "is_food_related": true or false,
  "is_order": true or false,
  "is_promo": true or false,
  "platform_name": "Swiggy" or "Zomato" or "Blinkit" or "Zepto" or null,
  "vendor_name": "Restaurant Name" or null,
  "probable_items": ["item1", "item2"] or [],
  "meal_type": "breakfast" or "lunch" or "dinner" or "snack" or "late_night" or null,
  "health_risk_category": "low_risk" or "medium_risk" or "high_risk" or "very_high_risk" or "unknown",
  "explanation": "One sentence explanation (max 20 words)",
  "confidence": 0.0 to 1.0
}}

Rules:
- is_food_related = true only if this is about food/beverage ordering
- is_order = true only if an actual purchase/order was placed or is in progress
- is_promo = true if it's a promotional offer/discount, false for actual orders
- Classify Indian food accurately (biryani, samosa, etc are high_risk at night)
- meal_type: late_night if it's between 10 PM and 4 AM, otherwise infer from context"""

_CLAUDE_STRICT_PROMPT = """Return ONLY this raw JSON (no other text, no markdown):
{{"is_food_related": boolean, "is_order": boolean, "is_promo": boolean, "platform_name": string_or_null, "vendor_name": string_or_null, "probable_items": [], "meal_type": string_or_null, "health_risk_category": "unknown", "explanation": "short explanation", "confidence": 0.7}}

Classify: App={app_name}, Notification="{title} {text}" """


def _enhance_with_claude(
    app_package: str,
    app_name: str,
    title: str,
    text: str,
    deterministic: ClassificationOutput,
) -> Optional[ClassificationOutput]:
    """
    Call Claude to enhance the deterministic classification.
    Returns enriched ClassificationOutput or None if Claude fails.
    """
    if not settings.ENABLE_LLM_ENHANCEMENT:
        return None

    if not settings.CLAUDE_API_KEY:
        return None

    prompt = _CLAUDE_PROMPT_TEMPLATE.format(
        app_package=app_package or "unknown",
        app_name=app_name or "unknown",
        title=title or "",
        text=text or "",
    )

    strict_prompt = _CLAUDE_STRICT_PROMPT.format(
        app_name=app_name or "unknown",
        title=title or "",
        text=text or "",
    )

    result = call_claude_json_with_retry(
        prompt=prompt,
        strict_prompt=strict_prompt,
        expected_keys=_CLAUDE_REQUIRED_KEYS,
        timeout_seconds=settings.AI_TIMEOUT_SECONDS,
    )

    if result is None:
        logger.warning("Claude enhancement failed — using deterministic result only.")
        return None

    try:
        probable_items = result.get("probable_items", [])
        if not isinstance(probable_items, list):
            probable_items = []

        return ClassificationOutput(
            is_food_related=bool(result["is_food_related"]),
            is_order=bool(result["is_order"]),
            is_promo=bool(result["is_promo"]),
            platform_name=result.get("platform_name") or deterministic.platform_name,
            vendor_name=result.get("vendor_name") or deterministic.vendor_name,
            probable_items=[str(i) for i in probable_items],
            meal_type=result.get("meal_type"),
            health_risk_category=result.get("health_risk_category", "unknown"),
            explanation=str(result.get("explanation", deterministic.explanation)),
            confidence=float(result.get("confidence", deterministic.confidence)),
            used_claude=True,
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse Claude result into ClassificationOutput: {e}")
        return None


# ── Public Classifier ──────────────────────────────────────────────────────────

_deterministic = DeterministicClassifier()


def classify_notification(
    app_package: Optional[str] = None,
    app_name: Optional[str] = None,
    title: Optional[str] = None,
    text: Optional[str] = None,
) -> ClassificationOutput:
    """
    Main entry point. Always returns a ClassificationOutput.
    Uses deterministic rules as baseline, optionally enhanced by Claude.
    Never raises exceptions.
    """
    # 1. Deterministic baseline (always runs)
    try:
        det_result = _deterministic.classify(app_package, app_name, title, text)
    except Exception as e:
        logger.error(f"Deterministic classifier crashed: {e}")
        det_result = ClassificationOutput(
            is_food_related=False, is_order=False, is_promo=False,
            platform_name=None, vendor_name=None, probable_items=[],
            meal_type=None, health_risk_category="unknown",
            explanation="Classification failed.", confidence=0.0,
        )

    # 2. Claude enhancement (optional, graceful)
    if settings.ENABLE_LLM_ENHANCEMENT and settings.CLAUDE_API_KEY:
        try:
            claude_result = _enhance_with_claude(
                app_package=app_package or "",
                app_name=app_name or "",
                title=title or "",
                text=text or "",
                deterministic=det_result,
            )
            if claude_result is not None:
                return claude_result
        except Exception as e:
            logger.error(f"Claude enhancement crashed unexpectedly: {e}")

    return det_result
