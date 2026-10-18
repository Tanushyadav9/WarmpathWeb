"""
Module descriptor for 'matching'
Owner: M2
"""

from typing import List
from app.core.db import async_session_maker
from app.core.ports import MatchingPort
from app.modules.matching.router import router as ROUTER
from app.modules.matching.service import MatchingService


class MatchingPortAdapter(MatchingPort):
    """Adapter bridging the central MatchingPort interface to the matching service."""

    async def explain(self, student_id: str, giver_id: str) -> List[str]:
        async with async_session_maker() as session:
            service = MatchingService(session)
            return await service.explain(student_id, giver_id)


def register_events(bus):
    """Register outbox event handlers for matching cache invalidation."""

    async def on_profile_updated(payload):
        user_id = getattr(payload, "user_id", None)
        await MatchingService.invalidate_recommendation_caches(student_id=str(user_id) if user_id else None)

    async def on_giver_profile_updated(payload):
        await MatchingService.invalidate_recommendation_caches()

    async def on_band_changed(payload):
        await MatchingService.invalidate_recommendation_caches()

    async def on_rating_submitted(payload):
        await MatchingService.invalidate_recommendation_caches()

    bus.subscribe("profile.updated", on_profile_updated)
    bus.subscribe("giver.profile_updated", on_giver_profile_updated)
    bus.subscribe("band.changed", on_band_changed)
    bus.subscribe("rating.submitted", on_rating_submitted)


def register_ports(registry):
    """Register synchronous ports implemented by matching."""
    registry.matching = MatchingPortAdapter()
