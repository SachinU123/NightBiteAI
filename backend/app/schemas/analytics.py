from typing import List, Optional
from pydantic import BaseModel


class HeatmapCell(BaseModel):
    location_key: str
    time_bucket: Optional[str] = None
    day_of_week: Optional[str] = None
    lat_bin: Optional[float] = None
    lon_bin: Optional[float] = None
    order_count: int
    avg_risk: float
    high_risk_count: int
    hotspot_intensity: float


class HeatmapResponse(BaseModel):
    cells: List[HeatmapCell]
    total_cells: int


class DashboardSummaryResponse(BaseModel):
    total_events_today: int
    total_events_this_week: int
    avg_risk_this_week: Optional[float]
    high_risk_events_today: int
    top_source_app: Optional[str]
    top_food_category: Optional[str]
    hotspot_count: int
