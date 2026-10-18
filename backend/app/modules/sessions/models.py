"""SQLAlchemy models for sessions, mentorship requests, bookings, and messages."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, String, Text
from app.core.db import Base, PG_UUID, PG_JSON


class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    student_id = Column(PG_UUID, index=True, nullable=False)
    giver_id = Column(PG_UUID, index=True, nullable=False)
    intent = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(
        String(30),
        default="pending",
        index=True,
        nullable=False,
    )  # pending, accepted, declined, scheduled, completed, rated, no_show, cancelled
    decline_reason = Column(Text, nullable=True)
    is_free = Column(Boolean, default=True, nullable=False)
    proposed_slots = Column(PG_JSON, nullable=True)
    confirmed_slot = Column(DateTime(timezone=True), nullable=True)
    meeting_link = Column(String(255), nullable=True)
    no_show_party = Column(String(20), nullable=True)  # giver, student
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    rated = Column(Boolean, default=False, nullable=False)


class SessionBooking(Base):
    __tablename__ = "session_bookings"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    request_id = Column(PG_UUID, index=True, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    room_id = Column(String(100), nullable=False)
    meeting_link = Column(String(255), nullable=False)
    calendar_event_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class MentorshipMessage(Base):
    __tablename__ = "mentorship_messages"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    request_id = Column(PG_UUID, index=True, nullable=False)
    sender_id = Column(PG_UUID, index=True, nullable=False)
    recipient_id = Column(PG_UUID, index=True, nullable=False)
    body = Column(Text, nullable=False)
    flags = Column(PG_JSON, nullable=False, default=list)
    safety_action = Column(String(20), default="allow", nullable=False)  # allow, warn, block
    safety_warning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class SessionNotification(Base):
    __tablename__ = "session_notifications"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, index=True, nullable=False)
    request_id = Column(PG_UUID, index=True, nullable=False)
    type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
