"""SQLAlchemy models for matching."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, String
from app.core.db import Base, PG_UUID


class GiverProfile(Base):
    __tablename__ = "giver_profiles"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    headline = Column(String(255), nullable=True)
    college = Column(String(255), nullable=True)
    skills = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
