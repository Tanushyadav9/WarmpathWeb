"""SQLAlchemy models for trust and safety."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.core.db import Base, PG_UUID, PG_ARRAY


class UserTrust(Base):
    __tablename__ = "user_trust"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    reports_count = Column(Integer, default=0, nullable=False)
    manual_level = Column(String(20), nullable=True)  # Override: new, verified, established, restricted
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ScamRule(Base):
    __tablename__ = "scam_rules"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    pattern = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # phone_number, email, url, social_handle, payment_request, scam_phrase, off_platform
    action = Column(String(20), default="block", nullable=False)  # block, warn
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class SafetyFlag(Base):
    __tablename__ = "safety_flags"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    sender_id = Column(PG_UUID, index=True, nullable=False)
    context = Column(String(50), nullable=True)
    message_text = Column(Text, nullable=False)
    flags = Column(PG_ARRAY, nullable=False, default=list)
    action = Column(String(20), nullable=False)  # block, warn
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
