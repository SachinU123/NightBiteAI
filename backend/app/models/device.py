from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, default="android")
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fcm_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notification_listener_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="devices")
