"""
NightBite AI — Food Schemas (Request/Response Contracts)

All schemas are frontend-friendly and Flutter-ready.
Includes: history, grouped history, item details, insights, AI coach responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────────────────────────────

class ManualEntryRequest(BaseModel):
    food_text: str
    meal_type: Optional[str] = None       # breakfast | lunch | dinner | snack | late_night
    event_timestamp: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pincode: Optional[str] = None


class NotificationCaptureRequest(BaseModel):
    source_app: str                         # zomato | swiggy | other
    raw_notification_text: str
    raw_food_text: Optional[str] = None     # pre-extracted if available
    event_timestamp: Optional[datetime] = None
    captured_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pincode: Optional[str] = None


# ── Sub-response models ────────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    food_category: Optional[str]
    risk_tags: List[str]
    matched_keywords: List[str]
    confidence: Optional[float]
    parse_quality: str  # complete | partial | failed


class RiskScoreResult(BaseModel):
    base_food_risk: float
    time_multiplier: float
    behavior_multiplier: float
    final_risk_score: float
    risk_band: str  # low | moderate | high | critical


class NudgeResult(BaseModel):
    nudge_text: str
    healthier_swap: Optional[str]
    nudge_type: str


# ── Main food analysis response ────────────────────────────────────────────────

class FoodAnalysisResponse(BaseModel):
    """The stable API contract returned after any food event analysis."""
    event_id: int
    source_type: str
    source_app: Optional[str]
    normalized_food_text: Optional[str]
    food_category: Optional[str]
    risk_tags: List[str]
    risk_score: float
    risk_band: str
    smart_nudge: str
    healthier_swap: Optional[str]
    event_timestamp: datetime
    is_late_night: bool = False

    # Detail sub-objects (optional for richer consumers)
    classification: Optional[ClassificationResult] = None
    score_detail: Optional[RiskScoreResult] = None


# ── History / list contracts ───────────────────────────────────────────────────

class HistoryEventItem(BaseModel):
    """Single item in the flat history list."""
    event_id: int
    source_type: str
    source_app: Optional[str]
    normalized_food_text: Optional[str]
    risk_score: float
    risk_band: str
    event_timestamp: datetime
    food_category: Optional[str]
    is_late_night: bool = False
    smart_nudge: Optional[str] = None
    healthier_swap: Optional[str] = None


class HistoryResponse(BaseModel):
    total: int
    late_night_total: int = 0
    page: int = 1
    page_size: int = 20
    events: List[HistoryEventItem]


# ── Grouped food history (deduplicated) ───────────────────────────────────────

class GroupedFoodItem(BaseModel):
    """
    A canonical food item with aggregated ordering stats.
    Used for the grouped/deduplicated history view in Flutter.
    """
    canonical_name: str               # Normalized display name, e.g. "Biryani"
    food_category: Optional[str]      # e.g. "rice_dish"
    total_orders: int                  # How many times ordered
    late_night_orders: int             # How many were in late-night window
    first_ordered_at: datetime         # Earliest order
    last_ordered_at: datetime          # Most recent order
    avg_risk_score: float              # Average risk across all orders
    max_risk_score: float              # Worst risk seen
    dominant_risk_band: str            # Most common risk band
    common_order_hour: Optional[int]   # Most common hour (0–23)
    common_order_time_label: Optional[str]  # Human-readable: "1 AM", "10 PM", etc.
    source_apps: List[str]             # Unique source apps used
    has_healthier_swap: bool           # Whether a swap suggestion exists
    healthier_swap: Optional[str]      # Best swap text from any order
    recurrence_days: Optional[float]   # Avg days between orders (if ≥2 orders)
    event_ids: List[int]               # All event IDs for drill-down


class GroupedHistoryResponse(BaseModel):
    total_unique_foods: int
    total_orders: int
    late_night_orders: int
    search_query: Optional[str] = None
    sort_by: str = "most_ordered"
    items: List[GroupedFoodItem]


# ── Item detail analytics ─────────────────────────────────────────────────────

class TimeDistributionBucket(BaseModel):
    hour: int               # 0–23
    label: str              # "12 AM", "1 AM" etc.
    count: int
    avg_risk: float


class WeeklyTrendPoint(BaseModel):
    week_label: str         # "Week 1", "This Week", etc.
    order_count: int
    avg_risk: float


class MonthlyTrendPoint(BaseModel):
    month_label: str        # "Jan 2025", "Feb 2025"
    order_count: int
    avg_risk: float


class ItemOrderInstance(BaseModel):
    """Single order instance for the item detail drill-down."""
    event_id: int
    ordered_at: datetime
    source_app: Optional[str]
    risk_score: float
    risk_band: str
    is_late_night: bool
    nudge_text: Optional[str]


class ItemDetailResponse(BaseModel):
    """
    Full analytics for a single canonical food item.
    Designed for the Flutter item detail drill-down page.
    """
    canonical_name: str
    food_category: Optional[str]

    # Core stats
    total_orders: int
    late_night_orders: int
    first_ordered_at: datetime
    last_ordered_at: datetime
    avg_risk_score: float
    max_risk_score: float
    dominant_risk_band: str

    # Ordering pattern
    common_order_hour: Optional[int]
    common_order_time_label: Optional[str]
    recurrence_days: Optional[float]
    recurrence_label: Optional[str]   # "Every ~3 days", "Weekly", etc.

    # Chart-ready data
    time_distribution: List[TimeDistributionBucket]
    weekly_trend: List[WeeklyTrendPoint]
    monthly_trend: List[MonthlyTrendPoint]

    # Swap / nudge context
    has_healthier_swap: bool
    healthier_swap: Optional[str]
    risk_tags: List[str]

    # Order history
    orders: List[ItemOrderInstance]


# ── Insights / Profile APIs ───────────────────────────────────────────────────

class UserInsightsResponse(BaseModel):
    """Legacy simple insights — preserved for backward compatibility."""
    weekly_avg_risk: Optional[float]
    high_risk_count_this_week: int
    total_events_this_week: int
    common_food_category: Optional[str]
    risk_trend: str  # improving | stable | worsening


class WeeklyOrderStat(BaseModel):
    week_label: str
    total_orders: int
    late_night_orders: int
    avg_risk: Optional[float]


class TopFoodItem(BaseModel):
    canonical_name: str
    order_count: int
    last_ordered_at: datetime
    avg_risk_score: float
    risk_band: str


class LateNightWindow(BaseModel):
    hour: int
    label: str     # "10 PM", "11 PM", "12 AM" etc.
    order_count: int
    pct: float     # % of total late-night orders


class ProfileInsightsResponse(BaseModel):
    """
    Rich profile insights for the Flutter profile/dashboard page.
    All data is chart-ready, label-ready, and Flutter-friendly.
    """
    # Summary stats
    total_orders_all_time: int
    total_late_night_orders: int
    late_night_pct: float              # % of all orders that are late-night
    weekly_late_night_count: int       # Last 7 days
    monthly_late_night_count: int      # Last 30 days

    # Risk summary
    avg_risk_score: Optional[float]
    risk_trend: str                    # improving | stable | worsening
    risk_trend_delta: Optional[float]  # Change from prev period (positive = higher risk)
    high_risk_count_week: int
    high_risk_count_month: int

    # Food patterns
    top_foods: List[TopFoodItem]       # Top 5 most ordered foods
    top_late_night_foods: List[TopFoodItem]   # Top 5 specifically late-night
    unique_food_count: int
    repeat_food_count: int             # Foods ordered 2+ times

    # Ordering windows
    dominant_late_night_window: Optional[str]   # "12 AM – 2 AM", etc.
    late_night_windows: List[LateNightWindow]   # Hour-by-hour breakdown

    # Weekly trend (last 4 weeks)
    weekly_trend: List[WeeklyOrderStat]

    # Behavior summary
    behavior_summary: str              # 1-2 sentence human-readable summary
    streak_days: int                   # Consecutive days with late-night orders
    last_late_night_order: Optional[datetime]


# ── AI Coach Schemas ──────────────────────────────────────────────────────────

class AIChatRequest(BaseModel):
    message: str
    context_source: Optional[str] = "chat"   # chat | home | history | profile | swap


class AIChatResponse(BaseModel):
    reply: str
    used_history: bool = False
    context_source: str = "chat"


class AIExplainRequest(BaseModel):
    """Request for AI explanation of a food event or pattern."""
    event_id: Optional[int] = None
    food_name: Optional[str] = None
    context: Optional[str] = None     # Free-form context override
    mode: str = "short"               # short | detailed


class AICoachResponse(BaseModel):
    """
    Structured AI Coach response for polished Flutter display.
    """
    title: str
    short_summary: str
    detailed_explanation: Optional[str] = None
    suggestions: List[str] = []
    follow_up_prompts: List[str] = []
    healthier_swap: Optional[str] = None
    risk_tag: Optional[str] = None        # Used for color-coding in Flutter
    ai_powered: bool = True


class SmartSwapRequest(BaseModel):
    """Request for a healthier swap recommendation."""
    food_name: str
    context: Optional[str] = None      # Additional context, e.g. "ordering at 2 AM"
    event_id: Optional[int] = None


class SmartSwapResponse(BaseModel):
    """Healthier swap response with AI reasoning."""
    food_name: str
    swap_suggestion: str
    short_reason: str
    detailed_reason: Optional[str] = None
    risk_reduction_label: Optional[str] = None   # "Reduces risk by ~30%"
    ai_powered: bool = True
