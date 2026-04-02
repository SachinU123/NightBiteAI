"""
NightBite AI — Order State Classifier (v2)
==========================================

Deterministic (rule-based) NLP pipeline for classifying notifications
from supported food-delivery apps (Zomato, Swiggy).

Pipeline:
  1. package whitelist check        — only allowed apps proceed
  2. text normalization             — lower, trim noise, merge fields
  3. reject-first classification   — rejection signals checked FIRST
  4. accept classification         — confirmed/update/delivered signals
  5. acceptance gate               — only real orders become food events
  6. diagnostics                   — fully auditable

Event States (exhaustive):
  - confirmed_order              → ACCEPT
  - order_update                 → ACCEPT
  - delivered_order              → ACCEPT
  - cancelled_order              → REJECT
  - failed_order                 → REJECT
  - promo_or_marketing           → REJECT
  - irrelevant_supported_app     → REJECT

KEY DESIGN DECISIONS:
  - Rejection signals are checked BEFORE acceptance signals.
  - Broad/ambiguous terms like "offer", "cancel" are NOT in the signal lists.
  - Each signal is as specific as possible to avoid false positives.
  - "order id" was removed (appears in promos referencing previous orders).
  - "confirmation" was removed (too generic — matches "subscription confirmation").
  - Promo signals must be >= 1 match to be classified as promo (was already 1).
  - "order_update" requires NO promo signals to avoid "track + save" combos.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Supported app packages ────────────────────────────────────────────────────

STRICTLY_SUPPORTED_PACKAGES = {
    "com.application.zomato",
    "in.swiggy.android",
    "com.zomato.android",
    "com.swiggy.android",
}

PACKAGE_TO_PLATFORM = {
    "com.application.zomato": "Zomato",
    "com.zomato.android": "Zomato",
    "in.swiggy.android": "Swiggy",
    "com.swiggy.android": "Swiggy",
}

# ── REJECT signal sets (checked first, so they cannot be overridden) ──────────

# Failed / payment issues
_FAILED_ORDER_SIGNALS = [
    "order could not be",
    "could not be fulfilled",
    "unfulfilled",
    "payment failed",
    "payment unsuccessful",
    "transaction failed",
    "could not process your",
    "order failed",
    "unable to process",
    "payment declined",
    "order could not be placed",
]

# Cancellation
_CANCELLED_ORDER_SIGNALS = [
    "order cancelled",
    "order has been cancelled",
    "your order was cancelled",
    "cancelled by restaurant",
    "we have cancelled your",
    "request to cancel",
    "cancellation confirmed",
]

# Promotions / marketing — every signal here must be SPECIFIC (no single generic words)
_PROMO_SIGNALS = [
    "% off",
    "flat off",
    "flat discount",
    "use code",
    "use coupon",
    "promo code",
    "referral code",
    "refer and earn",
    "cashback on your next",
    "free delivery on",
    "limited time",
    "today only",
    "this weekend",
    "flash sale",
    "grab now",
    "exclusive offer",
    "zomato gold",
    "swiggy one",
    "pro membership",
    "club membership",
    "special price",
    "happy hours",
    "midnight madness",
    "order now and get",
    "get flat",
    "minimum order",
    "don't miss out",
    "have you tried",
    "missing you",
    "it's been a while",
    "based on your taste",
    "recommended for you",
    "back in stock",
    "new on zomato",
    "new on swiggy",
    "trending near you",
    "popular near you",
    "only on zomato",
    "only on swiggy",
    "limited seats",
    "table booking",
    "up to 50%",
    "up to 40%",
    "up to 30%",
    "save up to",
    "earn extra",
    "click here to",
    "tap to order",
    "renew now",
    "upgrade now",
    "subscription renewed",
    "subscription reminder",
    "explore now",
    "check out",
    "new restaurant",
]

# ── ACCEPT signal sets ─────────────────────────────────────────────────────────

# Confirmed — restaurant accepted and is going to prepare
_CONFIRMED_ORDER_SIGNALS = [
    "order placed",
    "order confirmed",
    "order accepted",
    "your order has been placed",
    "order has been confirmed",
    "placed successfully",
    "restaurant accepted your",
    "your order is confirmed",
    "you ordered",
    "we have received your order",
    "your order is placed",
]

# Order in progress — being prepared or on the way
_ORDER_UPDATE_SIGNALS = [
    "arriving in",
    "on its way",
    "out for delivery",
    "delivery partner",
    "preparing your order",
    "restaurant is preparing",
    "rider picked",
    "almost there",
    "heading your way",
    "your order will arrive",
    "delivery partner is heading",
    "partner is nearby",
    "partner has picked",
    "being prepared",
    "order is being prepared",
    "order is ready",
    "leaving for your",
]

# Delivered
_DELIVERED_ORDER_SIGNALS = [
    "order delivered",
    "your order has been delivered",
    "delivered successfully",
    "enjoy your meal",
    "delivered to your",
    "has been delivered",
    "successfully delivered",
]


# ── Diagnostics dataclass ──────────────────────────────────────────────────────

@dataclass
class OrderStateResult:
    """Fully auditable result of the order-state classification."""
    package_name: str
    platform_name: Optional[str]
    normalized_text: str
    event_state: str            # one of 7 state strings
    accepted: bool              # True → becomes a food event
    rejection_reason: Optional[str] = None
    matched_signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    extracted_food_text: Optional[str] = None  # best-effort food extraction

    @property
    def is_real_order(self) -> bool:
        return self.accepted

    def log_diagnostic(self):
        status = "✅ ACCEPTED" if self.accepted else f"⛔ REJECTED ({self.rejection_reason})"
        logger.info(
            f"[OrderState] {status} | pkg={self.package_name} "
            f"| state={self.event_state} | signals={self.matched_signals[:3]} "
            f"| preview={self.normalized_text[:80]!r}"
        )


# ── Classifier ────────────────────────────────────────────────────────────────

class OrderStateClassifier:
    """
    Deterministic, inspectable order-state classifier.

    Design principle: REJECT-FIRST.
    Rejection signals are always checked before acceptance signals.
    This prevents marketing text like "order now and get..."
    from matching the "order" acceptance keywords.
    """

    def classify(
        self,
        app_package: Optional[str],
        title: Optional[str],
        text: Optional[str],
    ) -> OrderStateResult:
        """Main classification entry point. Never raises."""
        package = (app_package or "").lower().strip()
        platform = PACKAGE_TO_PLATFORM.get(package)

        # ── GATE 1: Package whitelist ─────────────────────────────────────────
        if package not in STRICTLY_SUPPORTED_PACKAGES:
            return OrderStateResult(
                package_name=package,
                platform_name=None,
                normalized_text="",
                event_state="irrelevant_supported_app",
                accepted=False,
                rejection_reason="package_not_whitelisted",
                confidence=1.0,
            )

        # ── GATE 2: Normalize combined text ──────────────────────────────────
        combined_raw = " ".join(filter(None, [title, text]))
        normalized = self._normalize(combined_raw)

        if not normalized:
            return OrderStateResult(
                package_name=package,
                platform_name=platform,
                normalized_text="",
                event_state="irrelevant_supported_app",
                accepted=False,
                rejection_reason="empty_notification_text",
                confidence=0.9,
            )

        # ── GATE 3: Event-state classification (REJECT-FIRST) ─────────────────
        event_state, matched_signals, confidence = self._classify_state(normalized)

        # ── GATE 4: Acceptance decision ───────────────────────────────────────
        accepted = event_state in ("confirmed_order", "delivered_order", "order_update")
        rejection_reason = None if accepted else self._rejection_reason(event_state)

        # ── GATE 5: Best-effort food text extraction (for accepted orders) ────
        food_text = None
        if accepted:
            food_text = self._extract_food_text(normalized, platform or "")

        result = OrderStateResult(
            package_name=package,
            platform_name=platform,
            normalized_text=normalized,
            event_state=event_state,
            accepted=accepted,
            rejection_reason=rejection_reason,
            matched_signals=matched_signals,
            confidence=confidence,
            extracted_food_text=food_text,
        )
        result.log_diagnostic()
        return result

    # ── Internal methods ──────────────────────────────────────────────────────

    def _normalize(self, text: str) -> str:
        """Lowercase, strip noise, normalize separators."""
        if not text:
            return ""
        t = text.lower()
        # Remove prices
        t = re.sub(r"₹[\d,]+(\.\d+)?", "", t)
        t = re.sub(r"\brs\.?\s*[\d,]+\b", "", t)
        # Remove phone numbers
        t = re.sub(r"\b\d{10,}\b", "", t)
        # Remove URLs
        t = re.sub(r"https?://\S+", "", t)
        # Normalize repeated punctuation
        t = re.sub(r"[!?.,:;]{2,}", ". ", t)
        # Collapse whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _classify_state(self, text: str) -> tuple[str, list[str], float]:
        """
        REJECT-FIRST classification.
        Rejection signals are always checked before acceptance signals.
        """

        # 1. Failed order (payment/fulfillment issues) — highest priority reject
        failed_hits = [s for s in _FAILED_ORDER_SIGNALS if s in text]
        if failed_hits:
            return "failed_order", failed_hits, self._conf(failed_hits)

        # 2. Cancelled order
        cancelled_hits = [s for s in _CANCELLED_ORDER_SIGNALS if s in text]
        if cancelled_hits:
            return "cancelled_order", cancelled_hits, self._conf(cancelled_hits)

        # 3. Promo / marketing — check BEFORE acceptance to prevent
        #    marketing texts like "order now and earn" from being accepted
        promo_hits = [s for s in _PROMO_SIGNALS if s in text]
        promo_count = len(promo_hits)

        # If 2+ promo signals → definitely promo, no further checks needed
        if promo_count >= 2:
            return "promo_or_marketing", promo_hits, self._conf(promo_hits)

        # 4. Delivered — strong, specific signals
        delivered_hits = [s for s in _DELIVERED_ORDER_SIGNALS if s in text]
        if delivered_hits:
            return "delivered_order", delivered_hits, self._conf(delivered_hits)

        # 5. Confirmed order
        confirmed_hits = [s for s in _CONFIRMED_ORDER_SIGNALS if s in text]
        if confirmed_hits:
            # Even 1 promo signal alongside confirmed → promo wins IF it's a known strong promo phrase
            if promo_count >= 1 and any(s in text for s in ["order now and get", "% off", "use code", "cashback"]):
                return "promo_or_marketing", promo_hits, self._conf(promo_hits)
            return "confirmed_order", confirmed_hits, self._conf(confirmed_hits)

        # 6. Order update / tracking
        update_hits = [s for s in _ORDER_UPDATE_SIGNALS if s in text]
        if update_hits:
            # Promo wins if mixed
            if promo_count >= 1:
                return "promo_or_marketing", promo_hits, self._conf(promo_hits)
            return "order_update", update_hits, self._conf(update_hits)

        # 7. Single promo signal → still promo
        if promo_count >= 1:
            return "promo_or_marketing", promo_hits, self._conf(promo_hits)

        # 8. Nothing recognizable
        return "irrelevant_supported_app", [], 0.5

    def _extract_food_text(self, normalized_text: str, platform: str) -> Optional[str]:
        """
        Best-effort food item extraction from an accepted notification.
        Returns None if nothing useful found.
        """
        patterns = [
            # "you ordered butter chicken"
            r"you ordered\s+(.+?)(?:\.|from|for|at|\n|$)",
            # "butter chicken from paradise"
            r"(.+?)\s+(?:from|by)\s+\w+",
            # "order confirmed: butter chicken, naan"
            r"order confirmed[:：]?\s*(.+?)(?:\.|from|at|\n|$)",
            # "preparing your <food>"
            r"preparing your\s+(.+?)(?:\.|from|at|\n|$)",
            # "order placed for <food>"
            r"order placed for\s+(.+?)(?:\.|from|at|\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Only return if it looks like food text (not too short, not too long)
                if 3 <= len(extracted) <= 100:
                    return extracted
        return None

    def _conf(self, hits: list[str]) -> float:
        return min(1.0, 0.65 + 0.15 * len(hits))

    def _rejection_reason(self, state: str) -> str:
        reasons = {
            "cancelled_order": "order_was_cancelled",
            "failed_order": "payment_or_fulfillment_failed",
            "promo_or_marketing": "promotional_notification",
            "irrelevant_supported_app": "no_order_state_signals_found",
        }
        return reasons.get(state, "rejected_by_classifier")


# Singleton — shared across all ingestion paths
order_state_classifier = OrderStateClassifier()
