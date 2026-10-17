"""Business logic service and TrustPort implementation for trust."""
import uuid
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.ports import ports, TrustPort
from app.modules.trust.models import UserTrust


class TrustService:
    async def get_or_create_trust(self, db: AsyncSession, user_id: uuid.UUID) -> UserTrust:
        result = await db.execute(select(UserTrust).where(UserTrust.user_id == user_id))
        ut = result.scalar_one_or_none()
        if not ut:
            ut = UserTrust(user_id=user_id, is_verified=False, reports_count=0)
            db.add(ut)
            await db.commit()
            await db.refresh(ut)
        return ut

    def get_max_open_requests(self, level: str) -> int:
        lvl = (level or "").lower()
        if lvl == "established":
            return settings.MAX_OPEN_REQUESTS_ESTABLISHED
        elif lvl == "verified":
            return settings.MAX_OPEN_REQUESTS_VERIFIED
        elif lvl == "restricted":
            return settings.MAX_OPEN_REQUESTS_RESTRICTED
        return settings.MAX_OPEN_REQUESTS_NEW

    async def get_trust_details(self, db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
        ut = await self.get_or_create_trust(db, user_id)

        # Base starting score
        score = 20
        verification_pts = 30 if ut.is_verified else 0
        score += verification_pts

        # Completed sessions from SessionsPort
        completed_sessions = 0
        open_requests = 0
        unrated_completed = 0
        try:
            stats = await ports.sessions.get_student_session_stats(str(user_id))
            completed_sessions = stats.get("completed_sessions_count", 0)
            open_requests = stats.get("open_requests_count", 0)
            unrated_completed = stats.get("unrated_completed_count", 0)
        except Exception:
            pass

        sessions_pts = min(30, completed_sessions * 10)
        score += sessions_pts

        # Ratings from RatingsPort
        rating_pts = 0
        try:
            band_info = await ports.ratings.get_band(str(user_id))
            smoothed_avg = band_info.get("smoothed_avg", 4.0)
            rating_pts = int(round((smoothed_avg - 3.0) * 10))
            rating_pts = max(-20, min(20, rating_pts))
        except Exception:
            pass
        score += rating_pts

        # Reports penalty
        reports_pts = ut.reports_count * -25
        score += reports_pts

        score = max(0, min(100, score))

        if ut.manual_level:
            level = ut.manual_level
        elif ut.reports_count >= 2:
            level = "restricted"
        elif score >= 70:
            level = "established"
        elif score >= 40:
            level = "verified"
        else:
            level = "new"

        max_open = self.get_max_open_requests(level)

        # Graduated limits check
        can_request = True
        blocked_code = None
        blocked_reason = ""

        if level == "restricted":
            can_request = False
            blocked_code = "account_restricted"
            blocked_reason = "Account is restricted. You cannot create new requests."
        elif unrated_completed > 0:
            can_request = False
            blocked_code = "unrated_sessions_pending"
            blocked_reason = "Students must rate completed sessions before sending more."
        elif open_requests >= max_open:
            can_request = False
            blocked_code = "open_requests_limit_exceeded"
            if level == "new":
                blocked_reason = f"New students may have at most {max_open} open requests."
            else:
                blocked_reason = f"You have reached your limit of {max_open} open requests for trust level '{level}'."

        return {
            "user_id": str(user_id),
            "trust_score": score,
            "trust_level": level,
            "is_verified": ut.is_verified,
            "reports_count": ut.reports_count,
            "max_open_requests": max_open,
            "open_requests_count": open_requests,
            "unrated_completed_count": unrated_completed,
            "can_request": can_request,
            "blocked_code": blocked_code,
            "blocked_reason": blocked_reason,
            "breakdown": {
                "base": 20,
                "verification": verification_pts,
                "completed_sessions": sessions_pts,
                "ratings": rating_pts,
                "reports_penalty": reports_pts,
            },
        }


class TrustPortImpl(TrustPort):
    def __init__(self, service: TrustService):
        self.service = service

    async def get_level(self, user_id: str) -> str:
        async with async_session_maker() as db:
            uid = uuid.UUID(user_id)
            details = await self.service.get_trust_details(db, uid)
            return details["trust_level"]

    async def can(self, user_id: str, action: str) -> Dict[str, Any]:
        if action in ("request", "create_request"):
            async with async_session_maker() as db:
                uid = uuid.UUID(user_id)
                details = await self.service.get_trust_details(db, uid)
                if not details["can_request"]:
                    return {
                        "allowed": False,
                        "code": details["blocked_code"],
                        "reason": details["blocked_reason"],
                    }
                return {"allowed": True, "reason": ""}
        return {"allowed": True, "reason": ""}

    async def is_blocked(self, user_a: str, user_b: str) -> bool:
        return False

    async def get_score(self, user_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            uid = uuid.UUID(user_id)
            return await self.service.get_trust_details(db, uid)


trust_service = TrustService()
trust_port_instance = TrustPortImpl(trust_service)
