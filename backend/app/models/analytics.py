from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Nudge(Base):
    """Smart nudge generated for a food event."""
    __tablename__ = "nudges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_events.id"), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    nudge_text: Mapped[str] = mapped_column(Text, nullable=False)
    healthier_swap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nudge_type: Mapped[str] = mapped_column(String(50), default="risk_warning")  # risk_warning | pattern_alert | timing

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    event: Mapped["FoodEvent"] = relationship("FoodEvent", back_populates="nudge")
    user: Mapped["User"] = relationship("User", back_populates="nudges")


class UserAggregate(Base):
    """Periodic aggregate stats per user (for insights screen)."""
    __tablename__ = "user_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_label: Mapped[str] = mapped_column(String(20), default="weekly")  # weekly | monthly

    avg_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_risk_count: Mapped[int] = mapped_column(Integer, default=0)
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    common_food_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="user_aggregates")


class HeatmapAggregate(Base):
    """Aggregated heatmap data by location + time bucket."""
    __tablename__ = "heatmap_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Location
    location_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # pincode or geo cell
    pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    lat_bin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon_bin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Time bucket
    time_bucket: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # YYYY-MM-DD HH
    hour_of_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Aggregates
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_risk: Mapped[float] = mapped_column(Float, default=0.0)
    high_risk_count: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_density: Mapped[float] = mapped_column(Float, default=0.0)
    hotspot_intensity: Mapped[float] = mapped_column(Float, default=0.0)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
