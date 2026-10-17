"""SQLAlchemy models for availability."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.core.db import Base, PG_UUID


class GiverAvailability(Base):
    __tablename__ = "giver_availabilities"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    status = Column(String(30), default="inactive", nullable=False)  # active_now, available_today, inactive
    today_window = Column(String(100), nullable=True)  # e.g., "8 to 10 pm"
    weekly_capacity_cap = Column(Integer, default=5, nullable=False)
    monthly_free_session_cap = Column(Integer, default=10, nullable=False)
    last_active_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class AvailabilityNotification(Base):
    __tablename__ = "availability_notifications"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, index=True, nullable=False)
    type = Column(String(50), nullable=False)  # confirm_availability, capacity_reached
    message = Column(Text, nullable=False)
    confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
