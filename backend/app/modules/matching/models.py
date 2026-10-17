import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType

    class Vector(UserDefinedType):
        """Fallback for environments without pgvector installed."""
        def __init__(self, dim: int = 768):
            self.dim = dim

        def get_col_spec(self, **kw) -> str:
            return f"vector({self.dim})"

from app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


from app.core.models import GiverProfile


class StudentMatchProfile(Base):
    """
    Local matching projection populated from profile.updated outbox events.
    Enforces privacy by storing only non-raw shared matching signals.
    """
    __tablename__ = "student_match_profiles"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(Integer, nullable=True)
    department = Column(String(100), nullable=True)
    batch = Column(Integer, nullable=True)
    societies = Column(ARRAY(String), nullable=False, default=list)
    skills = Column(JSONB, nullable=False, default=list)
    domains = Column(ARRAY(String), nullable=False, default=list)
    profile_embedding = Column(Vector(768), nullable=True)
    intent_goal = Column(Text, nullable=True)
    intent_roles = Column(ARRAY(String), nullable=False, default=list)
    intent_domains = Column(ARRAY(String), nullable=False, default=list)
    intent_help_type = Column(String(100), nullable=True)
    intent_embedding = Column(Vector(768), nullable=True)
    profile_version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_student_match_institution_id", "institution_id"),
        {"extend_existing": True},
    )
