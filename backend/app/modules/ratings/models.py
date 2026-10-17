"""SQLAlchemy models for ratings."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, Text
from app.core.db import Base, PG_UUID


class SessionRating(Base):
    __tablename__ = "session_ratings"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    session_id = Column(PG_UUID, index=True, nullable=False)
    rater_id = Column(PG_UUID, index=True, nullable=False)
    giver_id = Column(PG_UUID, index=True, nullable=False)
    score = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
