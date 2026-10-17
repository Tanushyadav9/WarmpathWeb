"""Business logic service for availability."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker, OutboxEvent
from app.core.errors import AppError
from app.core.ports import ports, PresencePort
from app.modules.availability.models import AvailabilityNotification, GiverAvailability
from app.modules.availability.schemas import (
    AvailabilityResponse,
    AvailabilityUpdateRequest,
    get_status_color,
    get_status_label,
)


class AvailabilityService:
    async def get_or_create(self, db: AsyncSession, user_id: uuid.UUID) -> GiverAvailability:
        result = await db.execute(
            select(GiverAvailability).where(GiverAvailability.user_id == user_id)
        )
        avail = result.scalar_one_or_none()
        if not avail:
            avail = GiverAvailability(
                user_id=user_id,
                status="inactive",
                weekly_capacity_cap=settings.DEFAULT_WEEKLY_CAPACITY_CAP,
                monthly_free_session_cap=settings.DEFAULT_MONTHLY_FREE_SESSION_CAP,
                last_active_at=datetime.now(timezone.utc),
            )
            db.add(avail)
            await db.commit()
            await db.refresh(avail)
        return avail

    async def get_availability_details(self, db: AsyncSession, user_id: uuid.UUID) -> AvailabilityResponse:
        avail = await self.get_or_create(db, user_id)

        # Query session statistics through synchronous ports
        weekly_used = 0
        monthly_free_used = 0
        response_rate = 100.0
        avg_reply_time_seconds = None
        avg_reply_time_display = "N/A"

        try:
            stats = await ports.sessions.get_giver_stats(str(user_id))
            weekly_used = stats.get("weekly_sessions_count", 0)
            monthly_free_used = stats.get("monthly_free_sessions_count", 0)
            response_rate = stats.get("response_rate", 100.0)
            avg_reply_time_seconds = stats.get("avg_reply_time_seconds")
            avg_reply_time_display = stats.get("avg_reply_time_display", "N/A")
        except Exception:
            # Fall back to zero usage if SessionsPort is unavailable
            pass

        capacity_left = max(0, avail.weekly_capacity_cap - weekly_used)
        capacity_reached = (capacity_left <= 0) or (monthly_free_used >= avail.monthly_free_session_cap)
        capacity_banner = None
        if capacity_reached:
            capacity_banner = (
                "Capacity reached: You have reached your session limit for this period. "
                "You are temporarily hidden from matching until capacity resets."
            )

        return AvailabilityResponse(
            user_id=str(avail.user_id),
            status=avail.status,
            today_window=avail.today_window,
            status_color=get_status_color(avail.status),
            status_label=get_status_label(avail.status, avail.today_window),
            weekly_capacity_cap=avail.weekly_capacity_cap,
            weekly_sessions_used=weekly_used,
            monthly_free_session_cap=avail.monthly_free_session_cap,
            monthly_free_sessions_used=monthly_free_used,
            capacity_left=capacity_left,
            capacity_reached=capacity_reached,
            capacity_banner=capacity_banner,
            response_rate=response_rate,
            avg_reply_time_seconds=avg_reply_time_seconds,
            avg_reply_time_display=avg_reply_time_display,
            last_active_at=avail.last_active_at.isoformat() if avail.last_active_at else None,
        )

    async def update_availability(
        self, db: AsyncSession, user_id: uuid.UUID, req: AvailabilityUpdateRequest
    ) -> AvailabilityResponse:
        avail = await self.get_or_create(db, user_id)

        if req.status is not None:
            valid_statuses = ["active_now", "available_today", "inactive"]
            status_val = req.status.lower()
            if status_val not in valid_statuses:
                raise AppError(
                    code="invalid_status",
                    message=f"Status must be one of {valid_statuses}.",
                    status_code=400,
                )
            avail.status = status_val

        if req.today_window is not None:
            avail.today_window = req.today_window

        if req.weekly_capacity_cap is not None:
            avail.weekly_capacity_cap = req.weekly_capacity_cap

        if req.monthly_free_session_cap is not None:
            avail.monthly_free_session_cap = req.monthly_free_session_cap

        avail.last_active_at = datetime.now(timezone.utc)
        avail.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(avail)

        return await self.get_availability_details(db, user_id)

    async def set_online(self, db: AsyncSession, user_id: uuid.UUID) -> AvailabilityResponse:
        avail = await self.get_or_create(db, user_id)
        avail.status = "active_now"
        avail.last_active_at = datetime.now(timezone.utc)
        avail.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(avail)
        return await self.get_availability_details(db, user_id)

    async def set_offline(self, db: AsyncSession, user_id: uuid.UUID) -> AvailabilityResponse:
        avail = await self.get_or_create(db, user_id)
        avail.status = "inactive"
        avail.last_active_at = datetime.now(timezone.utc)
        avail.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(avail)
        return await self.get_availability_details(db, user_id)

    async def flip_stale_givers_to_inactive(
        self, db: AsyncSession, inactive_days: Optional[int] = None
    ) -> List[uuid.UUID]:
        days = inactive_days if inactive_days is not None else settings.INACTIVE_AFTER_DAYS
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(GiverAvailability).where(
                GiverAvailability.status != "inactive",
                GiverAvailability.last_active_at < cutoff,
            )
        )
        stale_givers = result.scalars().all()
        flipped_ids: List[uuid.UUID] = []

        for giver in stale_givers:
            giver.status = "inactive"
            giver.updated_at = datetime.now(timezone.utc)
            flipped_ids.append(giver.user_id)

            # Notification to confirm availability again
            notification = AvailabilityNotification(
                user_id=giver.user_id,
                type="confirm_availability",
                message=(
                    f"You have been switched to Inactive due to {days} days of inactivity. "
                    "Please confirm your availability to receive mentorship requests again."
                ),
            )
            db.add(notification)

            # Outbox event
            outbox = OutboxEvent(
                topic="availability.stale_deactivated",
                payload={
                    "user_id": str(giver.user_id),
                    "inactive_days": days,
                    "action": "confirm_availability",
                },
            )
            db.add(outbox)

        await db.commit()
        return flipped_ids


class AvailabilityPresencePort(PresencePort):
    def __init__(self, service: AvailabilityService):
        self.service = service

    async def status(self, user_ids: List[str]) -> Dict[str, Any]:
        """Returns {online: bool, capacity_left: int, ...} mapping per user_id"""
        result_map: Dict[str, Any] = {}
        async with async_session_maker() as db:
            for uid_str in user_ids:
                try:
                    uid = uuid.UUID(uid_str)
                    details = await self.service.get_availability_details(db, uid)
                    result_map[uid_str] = {
                        "online": details.status == "active_now",
                        "status": details.status,
                        "status_color": details.status_color,
                        "status_label": details.status_label,
                        "today_window": details.today_window,
                        "capacity_left": details.capacity_left,
                        "capacity_reached": details.capacity_reached,
                        "weekly_capacity_cap": details.weekly_capacity_cap,
                        "weekly_sessions_used": details.weekly_sessions_used,
                        "monthly_free_session_cap": details.monthly_free_session_cap,
                        "monthly_free_sessions_used": details.monthly_free_sessions_used,
                        "response_rate": details.response_rate,
                        "avg_reply_time_seconds": details.avg_reply_time_seconds,
                        "avg_reply_time_display": details.avg_reply_time_display,
                    }
                except Exception:
                    result_map[uid_str] = {
                        "online": False,
                        "status": "inactive",
                        "status_color": "#64748B",
                        "status_label": "Inactive",
                        "today_window": None,
                        "capacity_left": 0,
                        "capacity_reached": True,
                        "response_rate": 100.0,
                        "avg_reply_time_display": "N/A",
                    }
        return result_map


availability_service = AvailabilityService()
presence_port_instance = AvailabilityPresencePort(availability_service)
