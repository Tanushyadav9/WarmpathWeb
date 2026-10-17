"""
backend/app/core/db.py - Async & Sync dual-compatible SQLAlchemy engine and session factory.
Supports PostgreSQL (with pgvector in Docker/production) and SQLite (for lightning-fast tests/demo).
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker

from app.core.base import Base
from app.core.config import settings

db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
if not db_url:
    db_url = "sqlite:///warmpath.db"

is_sqlite = "sqlite" in db_url

if not is_sqlite:
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
else:
    # Use standard synchronous sqlite engine with thread-safe connect args
    sqlite_sync_url = db_url.replace("+aiosqlite", "")
    engine = create_engine(
        sqlite_sync_url,
        connect_args={"check_same_thread": False},
        future=True,
    )
    sync_session_factory = sessionmaker(
        engine,
        expire_on_commit=False,
    )
    async_session_factory = sync_session_factory

async_session_maker = async_session_factory


class AsyncSessionWrapper:
    """Async facade over synchronous SQLAlchemy session for SQLite."""

    def __init__(self, sync_session):
        self._s = sync_session

    async def execute(self, statement, *args, **kwargs):
        return self._s.execute(statement, *args, **kwargs)

    async def commit(self):
        self._s.commit()

    async def rollback(self):
        self._s.rollback()

    async def flush(self):
        self._s.flush()

    async def refresh(self, instance):
        self._s.refresh(instance)

    def add(self, instance):
        self._s.add(instance)

    def add_all(self, instances):
        self._s.add_all(instances)

    async def close(self):
        self._s.close()


# Core platform infrastructure models
class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic = Column(String(100), index=True, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(20), default="pending", index=True, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    response_code = Column(Integer, nullable=False)
    response_body = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


# Import all normalized domain models so Base.metadata is fully populated
from app.core.models import (  # noqa: E402, F401
    Institution,
    User,
    StudentProfile,
    GiverProfile,
    Skill,
    UserSkill,
    Resume,
    GitHubProof,
    Availability,
    Capacity,
    Request,
    RequestMessage,
    Session,
    Rating,
    Vouch,
    CreditWallet,
    CreditLedger,
    Subscription,
    SponsoredSeat,
    Opportunity,
    Report,
    ScamRule,
    Notification,
    AuditLog,
    Embedding,
)


async def get_db() -> AsyncGenerator[Any, None]:
    """Dependency yielding an async session (or wrapped session on SQLite)."""
    if is_sqlite:
        sync_session = sync_session_factory()
        wrapper = AsyncSessionWrapper(sync_session)
        try:
            yield wrapper
        finally:
            await wrapper.close()
    else:
        async with async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()


def get_db_session_context():
    """Context manager for standalone scripts and background tasks."""
    if is_sqlite:
        sync_session = sync_session_factory()
        return AsyncSessionWrapper(sync_session)
    else:
        return async_session_factory()


async def init_db() -> None:
    """Create all tables if they do not exist."""
    if is_sqlite:
        Base.metadata.create_all(engine)
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
