"""
backend/app/core/db.py - Async SQLAlchemy engine, session factory, and core models.
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Integer, String, Text, JSON, CHAR
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from app.core.config import settings

from sqlalchemy.types import TypeDecorator, CHAR
import uuid as _uuid

# Dialect-compatible types for Postgres + SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), converting Python UUID to string.
    """
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            if isinstance(value, str):
                return _uuid.UUID(value)
            return value
        else:
            if not isinstance(value, _uuid.UUID):
                return str(_uuid.UUID(str(value)))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, _uuid.UUID):
            return _uuid.UUID(str(value))
        return value

PG_UUID = GUID()
PG_JSON = JSONB().with_variant(JSON(), "sqlite")
PG_ARRAY = ARRAY(String).with_variant(JSON(), "sqlite")


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    short_name = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    email_domains = Column(PG_ARRAY, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    users = relationship("User", back_populates="institution")


class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    roles = Column(PG_ARRAY, nullable=False, default=lambda: ["student"])
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    institution = relationship("Institution", back_populates="users")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    topic = Column(String(100), index=True, nullable=False)
    payload = Column(PG_JSON, nullable=False)
    status = Column(String(20), default="pending", index=True, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    user_id = Column(PG_UUID, nullable=True, index=True)
    response_code = Column(Integer, nullable=False)
    response_body = Column(PG_JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
