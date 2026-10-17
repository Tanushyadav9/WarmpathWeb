"""Business logic service and SessionsPort implementation for sessions."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker, OutboxEvent
from app.core.errors import AppError
from app.core.ports import ports, SessionsPort
from app.core.rate_limit import check_rate_limit
from app.modules.sessions.models import MentorshipRequest
from app.modules.sessions.schemas import CreateRequestInput, RequestResponse


def to_utc_datetime(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val)
        except Exception:
            return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    return None


def format_reply_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return "N/A"
    if seconds < 3600:
        mins = max(1, int(seconds // 60))
        return f"{mins}m"
    elif seconds < 86400:
        hours = max(1, int(round(seconds / 3600)))
        return f"{hours}h"
    else:
        days = max(1, int(round(seconds / 86400)))
        return f"{days}d"



class SessionsService:
    def _to_response(self, r: MentorshipRequest) -> RequestResponse:
        return RequestResponse(
            id=str(r.id),
            student_id=str(r.student_id),
            giver_id=str(r.giver_id),
            intent=r.intent,
            notes=r.notes,
            status=r.status,
            is_free=r.is_free,
            created_at=r.created_at.isoformat(),
            responded_at=r.responded_at.isoformat() if r.responded_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            rated=r.rated,
        )

    async def create_request(
        self, db: AsyncSession, student_id: uuid.UUID, req: CreateRequestInput
    ) -> RequestResponse:
        student_id_str = str(student_id)
        giver_id_str = req.giver_id

        # 1. Rate limiting on requests per day
        trust_level = "new"
        try:
            trust_level = await ports.trust.get_level(student_id_str)
        except Exception:
            pass
        await check_rate_limit(student_id_str, trust_level=trust_level, action="request")

        # 2. Check graduated trust limits (max open requests, unrated completed sessions)
        try:
            can_res = await ports.trust.can(student_id_str, "create_request")
            if not can_res.get("allowed", True):
                raise AppError(
                    code=can_res.get("code", "request_blocked"),
                    message=can_res.get("reason", "Request creation is currently blocked."),
                    status_code=400,
                )
        except AppError:
            raise
        except Exception:
            pass

        # 3. Check giver status and capacity via PresencePort
        try:
            presence_map = await ports.presence.status([giver_id_str])
            giver_presence = presence_map.get(giver_id_str, {})
            if giver_presence.get("capacity_reached", False):
                raise AppError(
                    code="capacity_reached",
                    message="This giver has reached their session capacity cap.",
                    status_code=400,
                )
            if giver_presence.get("status") == "inactive":
                raise AppError(
                    code="giver_inactive",
                    message="This giver is currently inactive and not accepting new requests.",
                    status_code=400,
                )
        except AppError:
            raise
        except Exception:
            pass

        # 4. Create request
        req_obj = MentorshipRequest(
            student_id=student_id,
            giver_id=uuid.UUID(giver_id_str),
            intent=req.intent,
            notes=req.notes,
            is_free=req.is_free,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(req_obj)

        outbox = OutboxEvent(
            topic="request.created",
            payload={
                "request_id": str(req_obj.id),
                "student_id": student_id_str,
                "giver_id": giver_id_str,
            },
        )
        db.add(outbox)

        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj)

    async def accept_request(
        self, db: AsyncSession, giver_id: uuid.UUID, request_id: uuid.UUID
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)
        if req_obj.giver_id != giver_id:
            raise AppError(code="unauthorized", message="Not authorized to accept this request", status_code=403)

        req_obj.status = "accepted"
        req_obj.responded_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj)

    async def decline_request(
        self, db: AsyncSession, giver_id: uuid.UUID, request_id: uuid.UUID
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)
        if req_obj.giver_id != giver_id:
            raise AppError(code="unauthorized", message="Not authorized to decline this request", status_code=403)

        req_obj.status = "declined"
        req_obj.responded_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj)

    async def complete_session(
        self, db: AsyncSession, request_id: uuid.UUID
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)

        req_obj.status = "completed"
        req_obj.completed_at = datetime.now(timezone.utc)
        req_obj.rated = False
        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj)

    async def mark_rated(
        self, db: AsyncSession, request_id: uuid.UUID
    ) -> None:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if req_obj:
            req_obj.rated = True
            await db.commit()

    async def list_requests(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> List[RequestResponse]:
        result = await db.execute(
            select(MentorshipRequest).where(
                (MentorshipRequest.student_id == user_id) | (MentorshipRequest.giver_id == user_id)
            ).order_by(MentorshipRequest.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._to_response(r) for r in rows]

    async def get_request(
        self, db: AsyncSession, request_id: uuid.UUID
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)
        return self._to_response(req_obj)


class SessionsPortImpl(SessionsPort):
    def __init__(self, service: SessionsService):
        self.service = service

    async def get_giver_stats(self, giver_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            gid = uuid.UUID(giver_id)
            result = await db.execute(
                select(MentorshipRequest).where(MentorshipRequest.giver_id == gid)
            )
            reqs = result.scalars().all()

            total = len(reqs)
            responded = [
                r for r in reqs
                if r.responded_at is not None or r.status in ("accepted", "declined", "completed")
            ]
            response_rate = round((len(responded) / total) * 100, 1) if total > 0 else 100.0

            reply_diffs = []
            for r in responded:
                resp_dt = to_utc_datetime(r.responded_at)
                creat_dt = to_utc_datetime(r.created_at)
                if resp_dt and creat_dt:
                    diff = (resp_dt - creat_dt).total_seconds()
                    if diff >= 0:
                        reply_diffs.append(diff)

            avg_reply_seconds = (sum(reply_diffs) / len(reply_diffs)) if reply_diffs else None
            avg_reply_display = format_reply_time(avg_reply_seconds)

            now = datetime.now(timezone.utc)
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            weekly_sessions = 0
            monthly_free_sessions = 0
            for r in reqs:
                cdt = to_utc_datetime(r.created_at)
                if not cdt:
                    continue
                if r.status in ("accepted", "completed"):
                    if cdt >= start_of_week:
                        weekly_sessions += 1
                    if r.is_free and cdt >= start_of_month:
                        monthly_free_sessions += 1

            return {
                "total_requests": total,
                "responded_requests": len(responded),
                "response_rate": response_rate,
                "avg_reply_time_seconds": avg_reply_seconds,
                "avg_reply_time_display": avg_reply_display,
                "weekly_sessions_count": weekly_sessions,
                "monthly_free_sessions_count": monthly_free_sessions,
            }


    async def get_student_session_stats(self, student_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            sid = uuid.UUID(student_id)
            result = await db.execute(
                select(MentorshipRequest).where(MentorshipRequest.student_id == sid)
            )
            reqs = result.scalars().all()

            open_count = sum(1 for r in reqs if r.status == "pending")
            completed_count = sum(1 for r in reqs if r.status == "completed")
            unrated_count = sum(1 for r in reqs if r.status == "completed" and not r.rated)

            return {
                "open_requests_count": open_count,
                "completed_sessions_count": completed_count,
                "unrated_completed_count": unrated_count,
            }

    async def mark_session_rated(self, session_id: str) -> None:
        async with async_session_maker() as db:
            sid = uuid.UUID(session_id)
            await self.service.mark_rated(db, sid)



sessions_service = SessionsService()
sessions_port_instance = SessionsPortImpl(sessions_service)
