"""
backend/app/core/ports.py - Inter-module synchronous Protocol interfaces & registry.
All default stubs FAIL CLOSED by raising PortNotReady (HTTP 503, port_not_ready).
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from app.core.errors import PortNotReady


@runtime_checkable
class SafetyPort(Protocol):
    async def scan_text(self, text: str, sender_id: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Returns {flags: [...], action: 'allow'|'warn'|'block'|'review'}"""
        ...


@runtime_checkable
class TrustPort(Protocol):
    async def get_level(self, user_id: str) -> str:
        """Returns trust level: new|verified|established|restricted"""
        ...

    async def can(self, user_id: str, action: str) -> Dict[str, Any]:
        """Returns {allowed: bool, reason: str}"""
        ...

    async def is_blocked(self, user_a: str, user_b: str) -> bool:
        """Returns True if communication between user_a and user_b is blocked"""
        ...

    async def get_score(self, user_id: str) -> Dict[str, Any]:
        """Returns {score: int, level: str, max_open_requests: int, breakdown: Dict[str, Any]}"""
        ...


@runtime_checkable
class SessionsPort(Protocol):
    async def get_giver_stats(self, giver_id: str) -> Dict[str, Any]:
        """Returns {total_requests: int, responded_requests: int, response_rate: float, avg_reply_time_seconds: Optional[float], avg_reply_time_display: str, weekly_sessions_count: int, monthly_free_sessions_count: int}"""
        ...

    async def get_student_session_stats(self, student_id: str) -> Dict[str, Any]:
        """Returns {open_requests_count: int, completed_sessions_count: int, unrated_completed_count: int}"""
        ...

    async def mark_session_rated(self, session_id: str) -> None:
        """Marks a session request as rated by student"""
        ...



@runtime_checkable
class CreditsPort(Protocol):

    async def can_access(self, student_id: str, giver_id: str) -> Dict[str, Any]:
        """Returns {allowed: bool, reason: str, plan: str, cost: int}"""
        ...

    async def reserve(self, student_id: str, request_id: str, giver_id: str) -> None:
        """Reserves credit for session request"""
        ...

    async def release(self, request_id: str) -> None:
        """Releases reserved credit to giver"""
        ...

    async def refund(self, request_id: str, reason: str) -> None:
        """Refunds reserved credit to student"""
        ...


@runtime_checkable
class RatingsPort(Protocol):
    async def get_band(self, giver_id: str) -> Dict[str, Any]:
        """Returns {band: str, smoothed_avg: float, n: int, completion_rate: float}"""
        ...


@runtime_checkable
class PresencePort(Protocol):
    async def status(self, user_ids: List[str]) -> Dict[str, Any]:
        """Returns {online: bool, capacity_left: int} mapping per user_id"""
        ...


@runtime_checkable
class MatchingPort(Protocol):
    async def explain(self, student_id: str, giver_id: str) -> List[str]:
        """Returns list of explainable match reasons"""
        ...


# --- Default Fail-Closed Stub Implementations ---

class DefaultSafetyPort(SafetyPort):
    async def scan_text(self, text: str, sender_id: str, context: Optional[str] = None) -> Dict[str, Any]:
        raise PortNotReady("SafetyPort")


class DefaultTrustPort(TrustPort):
    async def get_level(self, user_id: str) -> str:
        raise PortNotReady("TrustPort")

    async def can(self, user_id: str, action: str) -> Dict[str, Any]:
        raise PortNotReady("TrustPort")

    async def is_blocked(self, user_a: str, user_b: str) -> bool:
        raise PortNotReady("TrustPort")

    async def get_score(self, user_id: str) -> Dict[str, Any]:
        raise PortNotReady("TrustPort")


class DefaultSessionsPort(SessionsPort):
    async def get_giver_stats(self, giver_id: str) -> Dict[str, Any]:
        raise PortNotReady("SessionsPort")

    async def get_student_session_stats(self, student_id: str) -> Dict[str, Any]:
        raise PortNotReady("SessionsPort")

    async def mark_session_rated(self, session_id: str) -> None:
        raise PortNotReady("SessionsPort")



class DefaultCreditsPort(CreditsPort):
    async def can_access(self, student_id: str, giver_id: str) -> Dict[str, Any]:
        raise PortNotReady("CreditsPort")

    async def reserve(self, student_id: str, request_id: str, giver_id: str) -> None:
        raise PortNotReady("CreditsPort")

    async def release(self, request_id: str) -> None:
        raise PortNotReady("CreditsPort")

    async def refund(self, request_id: str, reason: str) -> None:
        raise PortNotReady("CreditsPort")


class DefaultRatingsPort(RatingsPort):
    async def get_band(self, giver_id: str) -> Dict[str, Any]:
        raise PortNotReady("RatingsPort")


class DefaultPresencePort(PresencePort):
    async def status(self, user_ids: List[str]) -> Dict[str, Any]:
        raise PortNotReady("PresencePort")


class DefaultMatchingPort(MatchingPort):
    async def explain(self, student_id: str, giver_id: str) -> List[str]:
        raise PortNotReady("MatchingPort")


# --- Central Port Registry ---

class PortRegistry:
    def __init__(self):
        self.safety: SafetyPort = DefaultSafetyPort()
        self.trust: TrustPort = DefaultTrustPort()
        self.sessions: SessionsPort = DefaultSessionsPort()
        self.credits: CreditsPort = DefaultCreditsPort()
        self.ratings: RatingsPort = DefaultRatingsPort()
        self.presence: PresencePort = DefaultPresencePort()
        self.matching: MatchingPort = DefaultMatchingPort()


ports = PortRegistry()

