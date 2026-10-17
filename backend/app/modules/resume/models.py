import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector
from app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Consent(Base):
    __tablename__ = "consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(50), nullable=False)
    granted = Column(Boolean, default=False, nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    text_version = Column(String(20), default="v1.0", nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "purpose", name="uq_user_purpose_consent"),
    )


class SkillTaxonomy(Base):
    __tablename__ = "skills_taxonomy"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    aliases = Column(ARRAY(String), default=list, nullable=False)


from app.core.models import StudentProfile


class StudentIntent(Base):
    __tablename__ = "student_intents"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    raw_text = Column(Text, nullable=False)
    goal_type = Column(String(50), nullable=True)
    target_roles = Column(ARRAY(String), default=list, nullable=False)
    target_domains = Column(ARRAY(String), default=list, nullable=False)
    structured = Column(JSONB, nullable=True)
    intent_embedding = Column(Vector(768), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
