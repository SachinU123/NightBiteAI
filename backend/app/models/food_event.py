from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FoodEvent(Base):
    """Raw food event — stores exactly what was captured, before any processing."""
    __tablename__ = "food_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Source
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)   # 'manual' | 'notification'
    source_app: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 'zomato' | 'swiggy' | None

    # Raw content
    raw_food_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_food_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_notification_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Geo (optional)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Meal context
    meal_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # breakfast/lunch/dinner/snack

    # Processing status
    is_processed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="food_events")
    classification: Mapped[Optional["FoodClassification"]] = relationship(
        "FoodClassification", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )
    risk_score: Mapped[Optional["RiskScore"]] = relationship(
        "RiskScore", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )
    nudge: Mapped[Optional["Nudge"]] = relationship(
        "Nudge", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )


class FoodClassification(Base):
    """NLP/AI output — what was classified from the raw event."""
    __tablename__ = "food_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_events.id"), nullable=False, unique=True, index=True)

    food_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    risk_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string list
    matched_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string list
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parse_quality: Mapped[str] = mapped_column(String(20), default="complete")  # complete|partial|failed

    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationship
    event: Mapped["FoodEvent"] = relationship("FoodEvent", back_populates="classification")


class RiskScore(Base):
    """Deterministic risk scoring output."""
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_events.id"), nullable=False, unique=True, index=True)

    base_food_risk: Mapped[float] = mapped_column(Float, nullable=False)
    time_multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    behavior_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    final_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False)  # low|moderate|high|critical

    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationship
    event: Mapped["FoodEvent"] = relationship("FoodEvent", back_populates="risk_score")
