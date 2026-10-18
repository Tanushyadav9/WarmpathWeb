"""Business logic service, TrustPort, and SafetyPort implementation for trust."""
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker, OutboxEvent
from app.core.ports import ports, TrustPort, SafetyPort
from app.modules.trust.models import UserTrust, ScamRule, SafetyFlag

# Regular expression detectors for contact details, payments, and scam phrases
PHONE_REGEX = re.compile(
    r'(?:(?:\+?91[\-\s]?)?[6-9]\d{9})|'           # 10 digits starting with 6-9 (Indian standard)
    r'(?:\b\d{5}[\s\-]\d{5}\b)|'                  # 5-5 split digits
    r'(?:\b\d{3}[\s\-]\d{3}[\s\-]\d{4}\b)|'       # standard 3-3-4
    r'(?:\b\d{10}\b)',                             # 10 consecutive digits
    re.IGNORECASE
)
EMAIL_REGEX = re.compile(
    r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b',
    re.IGNORECASE
)
URL_REGEX = re.compile(
    r'(?:https?://[^\s]+)|(?:www\.[^\s]+)|(?:\b[a-zA-Z0-9.-]+\.(?:com|org|in|io|net|co|me|xyz|app)\b)',
    re.IGNORECASE
)
SOCIAL_REGEX = re.compile(
    r'(?:@[a-zA-Z0-9_]{3,})|'
    r'(?:\b(?:telegram|whatsapp|wa\.me|t\.me|instagram|insta|linkedin|discord|snapchat)\b)',
    re.IGNORECASE
)
PAYMENT_REGEX = re.compile(
    r'(?:\b(?:send\s+money|upi|gpay|google\s*pay|phonepe|paytm|pay\s+me|transfer\s+money|crypto|bitcoin|advance\s+fee|processing\s+fee)\b)|'
    r'(?:[\w.\-]+@(okhdfcbank|okaxis|oksbi|okicici|ybl|paytm|upi))',
    re.IGNORECASE
)
OFF_PLATFORM_REGEX = re.compile(
    r'\b(?:talk\s+outside|call\s+me\s+on|chat\s+on\s+whatsapp|dm\s+me|contact\s+me\s+at|reach\s+out\s+on)\b',
    re.IGNORECASE
)
SCAM_PHRASES_REGEX = re.compile(
    r'\b(?:guaranteed\s+job|pay\s+for\s+referral|fake\s+certificate|interview\s+proxy|direct\s+offer\s+without\s+interview|100%\s+placement)\b',
    re.IGNORECASE
)


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


class SafetyService:
    async def scan_text(
        self, db: AsyncSession, text: str, sender_id: uuid.UUID, context: Optional[str] = None
    ) -> Dict[str, Any]:
        flags: List[str] = []
        action = "allow"

        # Regex detections
        if PHONE_REGEX.search(text):
            flags.append("phone_number")
        if EMAIL_REGEX.search(text):
            flags.append("email")
        if URL_REGEX.search(text):
            flags.append("url")
        if SOCIAL_REGEX.search(text):
            flags.append("social_handle")
        if PAYMENT_REGEX.search(text):
            flags.append("payment_request")
        if SCAM_PHRASES_REGEX.search(text):
            flags.append("scam_phrase")
        if OFF_PLATFORM_REGEX.search(text):
            flags.append("off_platform")

        # Database scam rules
        try:
            result = await db.execute(select(ScamRule))
            rules = result.scalars().all()
            for rule in rules:
                if re.search(rule.pattern, text, re.IGNORECASE):
                    flags.append(rule.category)
                    if rule.action == "block":
                        action = "block"
        except Exception:
            pass

        # Determine final action
        blocking_categories = {"phone_number", "email", "url", "social_handle", "payment_request", "scam_phrase"}
        has_block = any(f in blocking_categories for f in flags)

        if has_block:
            action = "block"
        elif "off_platform" in flags:
            action = "warn"

        warning_message = None
        if action == "block":
            # Store the safety flag in database
            flag_entry = SafetyFlag(
                id=uuid.uuid4(),
                sender_id=sender_id,
                context=context,
                message_text=text,
                flags=flags,
                action="block",
                created_at=datetime.now(timezone.utc),
            )
            db.add(flag_entry)

            # Check repeated flags
            res = await db.execute(
                select(SafetyFlag).where(
                    SafetyFlag.sender_id == sender_id,
                    SafetyFlag.action == "block",
                )
            )
            prior_flags = res.scalars().all()
            violations_count = len(prior_flags) + 1

            # Repeated violations penalize trust score
            ut = await trust_service.get_or_create_trust(db, sender_id)
            ut.reports_count += 1

            if violations_count >= 2:
                # Notify admins of repeated safety violations
                outbox = OutboxEvent(
                    topic="admin.safety_alert",
                    payload={
                        "sender_id": str(sender_id),
                        "violations_count": violations_count,
                        "flags": flags,
                        "text": text,
                        "action": "trust_score_penalized",
                    },
                )
                db.add(outbox)

            await db.commit()
            warning_message = (
                f"Safety alert: {', '.join(flags)} detected. "
                "Contact details, payments, and off-platform communication are blocked."
            )
        elif action == "warn":
            warning_message = "Safety notice: Never share personal contact info or transact outside WarmPath."

        return {
            "flags": flags,
            "action": action,
            "warning": warning_message,
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


class SafetyPortImpl(SafetyPort):
    def __init__(self, service: SafetyService):
        self.service = service

    async def scan_text(self, text: str, sender_id: str, context: Optional[str] = None) -> Dict[str, Any]:
        async with async_session_maker() as db:
            sid = uuid.UUID(sender_id)
            return await self.service.scan_text(db, text, sid, context)


trust_service = TrustService()
trust_port_instance = TrustPortImpl(trust_service)

safety_service = SafetyService()
safety_port_instance = SafetyPortImpl(safety_service)
