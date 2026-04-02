"""
NightBite AI — NLP Service
Handles food text normalization, keyword extraction, and classification.
Uses spaCy for tokenization + PhraseMatcher.
Falls back to regex-based matching if spaCy model not available.
"""
from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# ── Curated Lexicons ──────────────────────────────────────────────────────────

UNHEALTHY_KEYWORDS = [
    "fried", "deep fried", "crispy", "butter", "cheese burst", "extra cheese",
    "loaded", "masala", "spicy", "oil", "ghee", "cream", "mayo", "mayonnaise",
    "bacon", "sausage", "hot dog", "nuggets", "wings", "pizza", "burger",
    "biryani", "mutton", "pork", "beef", "lamb", "kebab", "shawarma",
    "noodles", "maggi", "instant", "chips", "fries", "french fries",
    "samosa", "pakora", "bhajiya", "puri", "kachori", "vada",
    "chocolate", "ice cream", "cake", "brownie", "donut", "waffle",
    "sugar", "soda", "cola", "pepsi", "fanta", "sprite", "energy drink",
    "milkshake", "shake", "cold drink", "sweetened",
]

HEALTHY_MODIFIERS = [
    "grilled", "baked", "steamed", "boiled", "low fat", "low calorie",
    "sugar free", "sugar-free", "whole grain", "multigrain", "salad",
    "vegetables", "veggies", "green", "lean", "protein", "tofu",
    "dal", "lentil", "soup", "broth", "tandoori", "roasted",
    "oats", "quinoa", "brown rice",
]

FOOD_CATEGORIES: Dict[str, List[str]] = {
    "fast_food": [
        "burger", "pizza", "sandwich", "wrap", "hot dog", "nuggets",
        "kfc", "mcdonalds", "subway", "dominos", "fries",
    ],
    "indian_fried": [
        "samosa", "pakora", "bhajiya", "puri", "kachori", "vada",
        "dahi vada", "aloo tikki",
    ],
    "rice_dish": [
        "biryani", "fried rice", "pulao", "rice", "khichdi",
    ],
    "noodles_pasta": [
        "noodles", "pasta", "maggi", "spaghetti", "ramen",
    ],
    "kebab_grill": [
        "kebab", "seekh kebab", "tikka", "tandoori", "shawarma",
    ],
    "dessert": [
        "ice cream", "cake", "brownie", "donut", "waffle", "kheer",
        "gulab jamun", "halwa", "rabri", "jalebi", "rasgulla",
    ],
    "beverage_unhealthy": [
        "cola", "pepsi", "fanta", "sprite", "soda", "energy drink",
        "milkshake", "shake", "cold drink", "juice box",
    ],
    "beverage_healthy": [
        "water", "coconut water", "green tea", "black coffee",
        "lemon water", "nimbu pani",
    ],
    "healthy_food": [
        "salad", "dal", "idli", "dosa", "upma", "poha", "oats",
        "fruit", "curd", "yogurt", "soup",
    ],
    "snack": [
        "chips", "nachos", "popcorn", "biscuit", "cookie", "cracker",
    ],
    "meat": [
        "chicken", "mutton", "pork", "beef", "lamb", "fish", "prawn",
        "paneer",
    ],
}

# Flat unhealthy category keywords (except healthy_food + beverage_healthy)
UNHEALTHY_CATEGORIES = {
    "fast_food", "indian_fried", "dessert", "beverage_unhealthy",
    "noodles_pasta", "snack",
}

BASE_RISK_BY_CATEGORY: Dict[str, float] = {
    "fast_food": 7.5,
    "indian_fried": 7.0,
    "rice_dish": 5.0,
    "noodles_pasta": 6.5,
    "kebab_grill": 5.5,
    "dessert": 8.0,
    "beverage_unhealthy": 7.0,
    "beverage_healthy": 1.5,
    "healthy_food": 2.0,
    "snack": 6.0,
    "meat": 5.0,
    "unknown": 4.5,
}


# ── NLP Result Dataclass ──────────────────────────────────────────────────────

@dataclass
class NLPResult:
    normalized_text: str
    food_category: Optional[str]
    risk_tags: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    healthy_modifiers_found: List[str] = field(default_factory=list)
    confidence: float = 0.0
    parse_quality: str = "complete"  # complete | partial | failed
    base_food_risk: float = 4.5


# ── NLP Service ───────────────────────────────────────────────────────────────

class NLPService:
    """
    Food text normalizer + classifier.
    
    Architecture: adapter-ready — can be plugged into ManualEntryAdapter
    or NotificationCaptureAdapter transparently. The `.analyze()` method
    is the single stable entry point.
    """

    def __init__(self):
        self._nlp = None
        self._matcher = None
        self._try_load_spacy()

    def _try_load_spacy(self):
        """Attempt to load spaCy. Falls back gracefully if not available."""
        try:
            import spacy
            from spacy.matcher import PhraseMatcher

            self._nlp = spacy.load("en_core_web_sm")
            self._matcher = PhraseMatcher(self._nlp.vocab, attr="LOWER")

            # Register all keyword patterns
            all_keywords = (
                UNHEALTHY_KEYWORDS
                + HEALTHY_MODIFIERS
                + [kw for cat_list in FOOD_CATEGORIES.values() for kw in cat_list]
            )
            patterns = [self._nlp.make_doc(text) for text in all_keywords]
            self._matcher.add("FOOD_TERMS", patterns)
            logger.info("spaCy NLP loaded successfully")

        except Exception as e:
            logger.warning(f"spaCy not available, using regex fallback: {e}")
            self._nlp = None
            self._matcher = None

    def normalize(self, text: str) -> str:
        """Lowercase, collapse whitespace, strip noise."""
        if not text:
            return ""
        text = text.lower().strip()
        # Remove order IDs, prices, numeric noise
        text = re.sub(r"\border\s*#?\s*\w+\b", "", text)
        text = re.sub(r"₹[\d,]+(\.\d+)?", "", text)
        text = re.sub(r"\brs\.?\s*[\d,]+\b", "", text)
        text = re.sub(r"\d{10,}", "", text)        # phone numbers
        text = re.sub(r"https?://\S+", "", text)   # URLs
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def extract_keywords_spacy(self, text: str) -> List[str]:
        """Extract food keywords using spaCy PhraseMatcher."""
        doc = self._nlp(text)
        matches = self._matcher(doc)
        found = set()
        for _, start, end in matches:
            found.add(doc[start:end].text.lower())
        return list(found)

    def extract_keywords_regex(self, text: str) -> List[str]:
        """Fallback regex-based keyword extraction."""
        found = set()
        all_terms = (
            UNHEALTHY_KEYWORDS
            + HEALTHY_MODIFIERS
            + [kw for cat_list in FOOD_CATEGORIES.values() for kw in cat_list]
        )
        for term in all_terms:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                found.add(term.lower())
        return list(found)

    def classify_category(self, keywords: List[str]) -> Optional[str]:
        """
        Map extracted keywords to the most prominent food category.
        Returns the first strong match, else None.
        """
        hits: Dict[str, int] = {}
        for cat, terms in FOOD_CATEGORIES.items():
            count = sum(1 for t in terms if t in keywords)
            if count > 0:
                hits[cat] = count

        if not hits:
            return None

        # Return category with most keyword hits
        return max(hits, key=lambda c: hits[c])

    def extract_risk_tags(self, keywords: List[str], category: Optional[str]) -> List[str]:
        """Generate meaningful risk tags from matched keywords."""
        tags = []
        unhealthy_hits = [k for k in keywords if k in UNHEALTHY_KEYWORDS]
        healthy_hits = [k for k in keywords if k in HEALTHY_MODIFIERS]

        if "fried" in unhealthy_hits or "deep fried" in unhealthy_hits:
            tags.append("deep_fried")
        if any(k in ["cheese burst", "extra cheese", "loaded"] for k in unhealthy_hits):
            tags.append("high_cheese")
        if any(k in ["soda", "cola", "energy drink", "milkshake", "shake"] for k in unhealthy_hits):
            tags.append("sugary_drink")
        if any(k in ["chocolate", "ice cream", "cake", "brownie", "donut", "gulab jamun", "jalebi"] for k in unhealthy_hits):
            tags.append("high_sugar_dessert")
        if category in UNHEALTHY_CATEGORIES:
            tags.append(f"category_{category}")
        if healthy_hits:
            tags.append("has_healthy_modifier")
        if not tags and category == "healthy_food":
            tags.append("low_risk_food")

        return list(set(tags)) if tags else ["unclassified"]

    def analyze(self, text: str, is_partial: bool = False) -> NLPResult:
        """
        Main entry point for food text analysis.
        Returns a structured NLPResult regardless of input quality.
        """
        if not text or len(text.strip()) < 3:
            return NLPResult(
                normalized_text=text or "",
                food_category=None,
                parse_quality="failed",
                confidence=0.0,
                base_food_risk=4.5,
            )

        normalized = self.normalize(text)

        # Extract keywords via spaCy or regex fallback
        if self._nlp is not None:
            keywords = self.extract_keywords_spacy(normalized)
        else:
            keywords = self.extract_keywords_regex(normalized)

        category = self.classify_category(keywords)
        risk_tags = self.extract_risk_tags(keywords, category)
        healthy_mods = [k for k in keywords if k in HEALTHY_MODIFIERS]

        base_risk = BASE_RISK_BY_CATEGORY.get(category or "unknown", 4.5)

        # Apply healthy modifier discount
        if healthy_mods:
            base_risk = max(1.5, base_risk * 0.75)

        # Confidence: keyword hit rate
        total_terms = len(UNHEALTHY_KEYWORDS) + len(HEALTHY_MODIFIERS)
        confidence = min(1.0, len(keywords) / max(1, len(normalized.split()) * 0.5))

        parse_quality = "partial" if is_partial else ("complete" if keywords else "failed")
        if not keywords and not is_partial:
            parse_quality = "partial"

        return NLPResult(
            normalized_text=normalized,
            food_category=category,
            risk_tags=risk_tags,
            matched_keywords=keywords,
            healthy_modifiers_found=healthy_mods,
            confidence=round(confidence, 2),
            parse_quality=parse_quality,
            base_food_risk=round(base_risk, 2),
        )


# Singleton instance — shared across the app
nlp_service = NLPService()
