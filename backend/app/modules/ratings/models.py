"""SQLAlchemy models for ratings, reviews, anti-gaming review queue, and vouches."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.core.db import Base, PG_UUID, PG_JSON


class SessionRating(Base):
    __tablename__ = "session_ratings"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    session_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    rater_id = Column(PG_UUID, index=True, nullable=False)
    giver_id = Column(PG_UUID, index=True, nullable=False)
    score = Column(Integer, nullable=False)  # 1 to 5
    tags = Column(PG_JSON, default=list, nullable=False)  # Helpful, On time, Clear feedback, etc.
    comment = Column(Text, nullable=True)
    is_flagged = Column(Boolean, default=False, nullable=False)
    flag_reason = Column(String(255), nullable=True)
    review_status = Column(String(20), default="approved", nullable=False)  # approved, pending, rejected
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Vouch(Base):
    __tablename__ = "vouches"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    session_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    giver_id = Column(PG_UUID, index=True, nullable=False)
    student_id = Column(PG_UUID, index=True, nullable=False)
    giver_name = Column(String(255), nullable=False)
    giver_company = Column(String(255), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
