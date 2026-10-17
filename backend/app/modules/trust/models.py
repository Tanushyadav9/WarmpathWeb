"""SQLAlchemy models for trust."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.core.db import Base, PG_UUID


class UserTrust(Base):
    __tablename__ = "user_trust"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    reports_count = Column(Integer, default=0, nullable=False)
    manual_level = Column(String(20), nullable=True)  # Override: new, verified, established, restricted
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
