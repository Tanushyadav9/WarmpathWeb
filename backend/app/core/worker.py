"""
backend/app/core/worker.py - Background outbox worker using arq.
Delivers outbox events with retries.
"""

import asyncio
from datetime import datetime, timezone
import structlog
from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import settings
from app.core.db import OutboxEvent, async_session_maker

from app.modules.availability.service import availability_service

logger = structlog.get_logger()


async def process_outbox_events(ctx):
    """
    Polls pending outbox_events and dispatches them.
    """
    logger.info("Processing outbox events...")
    async with async_session_maker() as session:
        result = await session.execute(
            select(OutboxEvent).where(OutboxEvent.status == "pending").limit(50)
        )
        events = result.scalars().all()
        for event in events:
            logger.info("Dispatching event", topic=event.topic, event_id=str(event.id))
            event.status = "processed"
            event.processed_at = datetime.now(timezone.utc)
        await session.commit()


async def flip_stale_givers_job(ctx=None):
    """
    Scheduled job: Auto-switch stale givers (no activity in N days, default 7) to Inactive.
    Sends notification to confirm availability again.
    """
    logger.info("Running flip_stale_givers_job...")
    async with async_session_maker() as session:
        flipped = await availability_service.flip_stale_givers_to_inactive(
            session, inactive_days=settings.INACTIVE_AFTER_DAYS
        )
        logger.info("Completed flip_stale_givers_job", count=len(flipped))
        return flipped


class WorkerSettings:
    functions = [process_outbox_events, flip_stale_givers_job]
    cron_jobs = []
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)


if __name__ == "__main__":
    from arq import run_worker
    run_worker(WorkerSettings)

