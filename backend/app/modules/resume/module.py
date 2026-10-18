"""
Module descriptor for 'resume'
Owner: M2
"""

import uuid
from app.modules.resume.router import router as ROUTER
from app.core.events import EventBus
from app.core.ports import PortRegistry


def register_events(bus: EventBus) -> None:
    """Register outbox event handlers for resume module."""
    async def handle_user_deleted(payload: dict) -> None:
        user_id_raw = payload.get("user_id") if isinstance(payload, dict) else getattr(payload, "user_id", None)
        if user_id_raw:
            try:
                target_uid = uuid.UUID(str(user_id_raw))
                from app.core.db import async_session_maker
                from app.modules.resume.service import ResumeService
                async with async_session_maker() as session:
                    service = ResumeService(session)
                    await service.purge_all_user_data(target_uid)
            except Exception:
                pass

    bus.subscribe("user.deleted", handle_user_deleted)


def register_ports(registry: PortRegistry) -> None:
    """Register synchronous ports implemented by resume."""
    pass
