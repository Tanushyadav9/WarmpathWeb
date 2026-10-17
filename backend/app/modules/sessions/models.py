"""SQLAlchemy models for sessions."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, String, Text
from app.core.db import Base, PG_UUID


class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    student_id = Column(PG_UUID, index=True, nullable=False)
    giver_id = Column(PG_UUID, index=True, nullable=False)
    intent = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(30), default="pending", index=True, nullable=False)  # pending, accepted, declined, cancelled, completed
    is_free = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    rated = Column(Boolean, default=False, nullable=False)


class SessionBooking(Base):
    __tablename__ = "session_bookings"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    request_id = Column(PG_UUID, index=True, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    room_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
