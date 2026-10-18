"""Business logic service and SessionsPort implementation for sessions."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker, OutboxEvent
from app.core.errors import AppError
from app.core.ports import ports, SessionsPort
from app.core.rate_limit import check_rate_limit
from app.modules.sessions.calendar_adapter import calendar_adapter
from app.modules.sessions.models import (
    MentorshipMessage,
    MentorshipRequest,
    SessionBooking,
    SessionNotification,
)
from app.modules.sessions.schemas import (
    BookingResponse,
    CreateRequestInput,
    MessageResponse,
    NotificationResponse,
    RequestResponse,
    StudentProfileRoleView,
)


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
    def _to_response(
        self, r: MentorshipRequest, viewer_id: Optional[uuid.UUID] = None
    ) -> RequestResponse:
        student_profile = None
        # Role-based student profile for giver view (contact details strictly omitted)
        if viewer_id and viewer_id == r.giver_id:
            student_profile = StudentProfileRoleView(
                student_id=str(r.student_id),
                display_name=f"Student {str(r.student_id)[:8]}",
                college="Verified Partner College",
                headline="Student Mentee",
                intent=r.intent,
                notes=r.notes,
            )

        return RequestResponse(
            id=str(r.id),
            student_id=str(r.student_id),
            giver_id=str(r.giver_id),
            intent=r.intent,
            notes=r.notes,
            status=r.status,
            decline_reason=r.decline_reason,
            is_free=r.is_free,
            proposed_slots=r.proposed_slots,
            confirmed_slot=r.confirmed_slot.isoformat() if r.confirmed_slot else None,
            meeting_link=r.meeting_link,
            no_show_party=r.no_show_party,
            created_at=r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
            responded_at=r.responded_at.isoformat() if r.responded_at else None,
            scheduled_at=r.scheduled_at.isoformat() if r.scheduled_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            rated=r.rated,
            student_profile=student_profile,
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
        req_id = uuid.uuid4()
        req_obj = MentorshipRequest(
            id=req_id,
            student_id=student_id,
            giver_id=uuid.UUID(giver_id_str),
            intent=req.intent,
            notes=req.notes,
            is_free=req.is_free,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(req_obj)

        # Giver notification
        notif = SessionNotification(
            id=uuid.uuid4(),
            user_id=uuid.UUID(giver_id_str),
            request_id=req_id,
            type="request_received",
            message=f"New mentorship request received: {req.intent}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)

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

        # Escrow: on request acceptance credits move to Held (free if same-college)
        try:
            await ports.credits.reserve(
                student_id=str(req_obj.student_id),
                request_id=str(req_obj.id),
                giver_id=str(req_obj.giver_id),
            )
        except AppError:
            raise
        except Exception:
            pass

        # Notify student
        notif = SessionNotification(
            id=uuid.uuid4(),
            user_id=req_obj.student_id,
            request_id=req_obj.id,
            type="request_accepted",
            message="Your mentorship request was accepted! Giver can now propose slots.",
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)

        db.add(
            OutboxEvent(
                topic="request.accepted",
                payload={"request_id": str(req_obj.id), "student_id": str(req_obj.student_id), "giver_id": str(giver_id)},
            )
        )

        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj, viewer_id=giver_id)

    async def decline_request(
        self, db: AsyncSession, giver_id: uuid.UUID, request_id: uuid.UUID, reason: Optional[str] = None
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)
        if req_obj.giver_id != giver_id:
            raise AppError(code="unauthorized", message="Not authorized to decline this request", status_code=403)

        decline_reason = reason or "Giver is currently unavailable"
        req_obj.status = "declined"
        req_obj.decline_reason = decline_reason
        req_obj.responded_at = datetime.now(timezone.utc)

        # Escrow: full refund on decline
        try:
            await ports.credits.refund(str(req_obj.id), reason=decline_reason)
        except Exception:
            pass

        # Notify student with decline reason
        notif = SessionNotification(
            id=uuid.uuid4(),
            user_id=req_obj.student_id,
            request_id=req_obj.id,
            type="request_declined",
            message=f"Your mentorship request was declined. Reason: {decline_reason}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)

        db.add(
            OutboxEvent(
                topic="request.declined",
                payload={
                    "request_id": str(req_obj.id),
                    "student_id": str(req_obj.student_id),
                    "giver_id": str(giver_id),
                    "reason": decline_reason,
                },
            )
        )

        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj, viewer_id=giver_id)

    async def propose_slots(
        self, db: AsyncSession, giver_id: uuid.UUID, request_id: uuid.UUID, slots: List[str]
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)
        if req_obj.giver_id != giver_id:
            raise AppError(code="unauthorized", message="Not authorized to propose slots", status_code=403)
        if req_obj.status not in ("accepted", "scheduled"):
            raise AppError(
                code="invalid_request_state",
                message=f"Cannot propose slots for request in '{req_obj.status}' status",
                status_code=400,
            )

        req_obj.proposed_slots = slots

        # Notify student of proposed slots
        notif = SessionNotification(
            id=uuid.uuid4(),
            user_id=req_obj.student_id,
            request_id=req_obj.id,
            type="slots_proposed",
            message=f"Giver has proposed {len(slots)} session slot(s). Please confirm your preferred slot.",
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)

        db.add(
            OutboxEvent(
                topic="slots.proposed",
                payload={"request_id": str(req_obj.id), "slots": slots},
            )
        )

        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj, viewer_id=giver_id)

    async def confirm_slot(
        self, db: AsyncSession, user_id: uuid.UUID, request_id: uuid.UUID, slot: str
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)
        if user_id not in (req_obj.student_id, req_obj.giver_id):
            raise AppError(code="unauthorized", message="Not authorized to confirm this slot", status_code=403)

        slot_dt = to_utc_datetime(slot)
        if not slot_dt:
            raise AppError(code="invalid_slot_format", message="Invalid slot datetime format", status_code=400)

        # Call Calendar Adapter to create calendar event and Jitsi meeting link
        calendar_res = await calendar_adapter.create_event(
            request_id=str(req_obj.id),
            title=f"WarmPath Mentorship: {req_obj.intent}",
            start_time=slot_dt,
            end_time=slot_dt + timedelta(minutes=45),
            attendees=[str(req_obj.student_id), str(req_obj.giver_id)],
            description=req_obj.notes,
        )

        meeting_link = calendar_res["meeting_link"]
        event_id = calendar_res.get("event_id")

        booking = SessionBooking(
            id=uuid.uuid4(),
            request_id=req_obj.id,
            scheduled_at=slot_dt,
            room_id=f"warmpath-{req_obj.id}",
            meeting_link=meeting_link,
            calendar_event_id=event_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(booking)

        req_obj.status = "scheduled"
        req_obj.confirmed_slot = slot_dt
        req_obj.meeting_link = meeting_link
        req_obj.scheduled_at = datetime.now(timezone.utc)

        # Send calendar and meeting reminders to both student and giver
        student_notif = SessionNotification(
            id=uuid.uuid4(),
            user_id=req_obj.student_id,
            request_id=req_obj.id,
            type="session_scheduled",
            message=f"Mentorship session confirmed for {slot}. Meeting link: {meeting_link}",
            created_at=datetime.now(timezone.utc),
        )
        giver_notif = SessionNotification(
            id=uuid.uuid4(),
            user_id=req_obj.giver_id,
            request_id=req_obj.id,
            type="session_scheduled",
            message=f"Mentorship session confirmed for {slot}. Meeting link: {meeting_link}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(student_notif)
        db.add(giver_notif)

        db.add(
            OutboxEvent(
                topic="session.scheduled",
                payload={
                    "request_id": str(req_obj.id),
                    "slot": slot_dt.isoformat(),
                    "meeting_link": meeting_link,
                    "calendar_event_id": event_id,
                },
            )
        )

        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj, viewer_id=user_id)

    async def complete_session(
        self, db: AsyncSession, request_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)

        if user_id and user_id not in (req_obj.student_id, req_obj.giver_id):
            raise AppError(code="unauthorized", message="Not authorized to complete this session", status_code=403)

        req_obj.status = "completed"
        req_obj.completed_at = datetime.now(timezone.utc)
        req_obj.rated = False

        # Release credit to giver if this was a paid credit session
        if not req_obj.is_free:
            try:
                await ports.credits.release(str(req_obj.id))
            except Exception:
                pass

        # Send rating reminder to student
        student_notif = SessionNotification(
            id=uuid.uuid4(),
            user_id=req_obj.student_id,
            request_id=req_obj.id,
            type="session_completed",
            message="Your mentorship session is completed! Please take a moment to rate the session.",
            created_at=datetime.now(timezone.utc),
        )
        db.add(student_notif)

        db.add(
            OutboxEvent(
                topic="session.completed",
                payload={"request_id": str(req_obj.id), "completed_at": req_obj.completed_at.isoformat()},
            )
        )

        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj, viewer_id=user_id)

    async def report_no_show(
        self, db: AsyncSession, reporter_id: uuid.UUID, request_id: uuid.UUID, party: str, reason: Optional[str] = None
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)

        if reporter_id not in (req_obj.student_id, req_obj.giver_id):
            raise AppError(code="unauthorized", message="Not authorized to report no-show", status_code=403)

        party_clean = party.lower().strip()
        if party_clean not in ("giver", "student"):
            raise AppError(code="invalid_party", message="No-show party must be 'giver' or 'student'", status_code=400)

        req_obj.status = "no_show"
        req_obj.no_show_party = party_clean

        # If giver no-show: trigger refund to student
        if party_clean == "giver":
            try:
                await ports.credits.refund(str(req_obj.id), reason=f"Giver no-show: {reason or 'Did not attend'}")
            except Exception:
                pass

            notif = SessionNotification(
                id=uuid.uuid4(),
                user_id=req_obj.student_id,
                request_id=req_obj.id,
                type="refund_issued",
                message=f"Full refund issued due to giver no-show: {reason or 'Giver did not attend.'}",
                created_at=datetime.now(timezone.utc),
            )
            db.add(notif)

        db.add(
            OutboxEvent(
                topic="session.no_show",
                payload={
                    "request_id": str(req_obj.id),
                    "party": party_clean,
                    "reported_by": str(reporter_id),
                    "reason": reason,
                },
            )
        )

        await db.commit()
        await db.refresh(req_obj)
        return self._to_response(req_obj, viewer_id=reporter_id)

    async def send_message(
        self, db: AsyncSession, sender_id: uuid.UUID, request_id: uuid.UUID, body: str
    ) -> MessageResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)

        if sender_id not in (req_obj.student_id, req_obj.giver_id):
            raise AppError(code="unauthorized", message="Not authorized to message on this request", status_code=403)

        recipient_id = req_obj.giver_id if sender_id == req_obj.student_id else req_obj.student_id

        # Run scam detection middleware via SafetyPort
        scan_result = await ports.safety.scan_text(
            text=body, sender_id=str(sender_id), context=f"request:{request_id}"
        )

        action = scan_result.get("action", "allow")
        flags = scan_result.get("flags", [])
        warning = scan_result.get("warning")

        if action == "block":
            raise AppError(
                code="safety_violation_blocked",
                message=warning or "Message blocked due to safety violations (phone numbers, contact details, or payment requests).",
                status_code=400,
                details={"flags": flags},
            )

        msg = MentorshipMessage(
            id=uuid.uuid4(),
            request_id=req_obj.id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            body=body,
            flags=flags,
            safety_action=action,
            safety_warning=warning if action == "warn" else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)

        db.add(
            OutboxEvent(
                topic="message.created",
                payload={
                    "message_id": str(msg.id),
                    "request_id": str(req_obj.id),
                    "sender_id": str(sender_id),
                    "recipient_id": str(recipient_id),
                },
            )
        )

        await db.commit()
        await db.refresh(msg)

        return MessageResponse(
            id=str(msg.id),
            request_id=str(msg.request_id),
            sender_id=str(msg.sender_id),
            recipient_id=str(msg.recipient_id),
            body=msg.body,
            flags=msg.flags,
            safety_action=msg.safety_action,
            safety_warning=msg.safety_warning,
            created_at=msg.created_at.isoformat(),
        )

    async def list_messages(
        self, db: AsyncSession, user_id: uuid.UUID, request_id: uuid.UUID
    ) -> List[MessageResponse]:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)

        if user_id not in (req_obj.student_id, req_obj.giver_id):
            raise AppError(code="unauthorized", message="Not authorized to view messages", status_code=403)

        msg_result = await db.execute(
            select(MentorshipMessage)
            .where(MentorshipMessage.request_id == request_id)
            .order_by(MentorshipMessage.created_at.asc())
        )
        messages = msg_result.scalars().all()

        return [
            MessageResponse(
                id=str(m.id),
                request_id=str(m.request_id),
                sender_id=str(m.sender_id),
                recipient_id=str(m.recipient_id),
                body=m.body,
                flags=m.flags,
                safety_action=m.safety_action,
                safety_warning=m.safety_warning,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ]

    async def list_notifications(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> List[NotificationResponse]:
        result = await db.execute(
            select(SessionNotification)
            .where(SessionNotification.user_id == user_id)
            .order_by(SessionNotification.created_at.desc())
        )
        notifications = result.scalars().all()
        return [
            NotificationResponse(
                id=str(n.id),
                user_id=str(n.user_id),
                request_id=str(n.request_id),
                type=n.type,
                message=n.message,
                created_at=n.created_at.isoformat(),
            )
            for n in notifications
        ]

    async def mark_rated(
        self, db: AsyncSession, request_id: uuid.UUID
    ) -> None:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if req_obj:
            req_obj.rated = True
            req_obj.status = "rated"
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
        return [self._to_response(r, viewer_id=user_id) for r in rows]

    async def get_request(
        self, db: AsyncSession, request_id: uuid.UUID, viewer_id: Optional[uuid.UUID] = None
    ) -> RequestResponse:
        result = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.id == request_id)
        )
        req_obj = result.scalar_one_or_none()
        if not req_obj:
            raise AppError(code="request_not_found", message="Request not found", status_code=404)
        return self._to_response(req_obj, viewer_id=viewer_id)


class SessionsPortImpl(SessionsPort):
    def __init__(self, service: SessionsService):
        self.service = service

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as db:
            sid = uuid.UUID(session_id)
            result = await db.execute(
                select(MentorshipRequest).where(MentorshipRequest.id == sid)
            )
            req_obj = result.scalar_one_or_none()
            if not req_obj:
                return None
            return {
                "id": str(req_obj.id),
                "status": req_obj.status,
                "student_id": str(req_obj.student_id),
                "giver_id": str(req_obj.giver_id),
                "intent": req_obj.intent,
                "meeting_link": req_obj.meeting_link,
                "confirmed_slot": req_obj.confirmed_slot.isoformat() if req_obj.confirmed_slot else None,
                "rated": req_obj.rated,
            }

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
                if r.responded_at is not None or r.status in ("accepted", "declined", "completed", "scheduled", "rated")
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
                if r.status in ("accepted", "completed", "scheduled", "rated"):
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

            open_count = sum(1 for r in reqs if r.status in ("pending", "accepted", "scheduled"))
            completed_count = sum(1 for r in reqs if r.status in ("completed", "rated"))
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
