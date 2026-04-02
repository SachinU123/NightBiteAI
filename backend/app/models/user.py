from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    food_events: Mapped[List["FoodEvent"]] = relationship("FoodEvent", back_populates="user", cascade="all, delete-orphan")
    nudges: Mapped[List["Nudge"]] = relationship("Nudge", back_populates="user", cascade="all, delete-orphan")
    user_aggregates: Mapped[List["UserAggregate"]] = relationship("UserAggregate", back_populates="user", cascade="all, delete-orphan")
