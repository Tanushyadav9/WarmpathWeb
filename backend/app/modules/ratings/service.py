"""Business logic service and RatingsPort implementation for ratings."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker, OutboxEvent
from app.core.errors import AppError
from app.core.ports import ports, RatingsPort
from app.modules.ratings.models import SessionRating
from app.modules.ratings.schemas import RatingCreateInput, RatingResponse


class RatingsService:
    async def submit_rating(
        self, db: AsyncSession, session_id: uuid.UUID, rater_id: uuid.UUID, req: RatingCreateInput, giver_id: Optional[uuid.UUID] = None
    ) -> RatingResponse:
        session_info = await ports.sessions.get_session(str(session_id))
        if not session_info:
            raise AppError(code="session_not_found", message="Session not found", status_code=404)
        if session_info.get("status") != "completed":
            raise AppError(
                code="session_not_completed",
                message="A session cannot be rated before completion.",
                status_code=400,
            )
        gid = giver_id or uuid.UUID(session_info["giver_id"])
        rating_obj = SessionRating(
            session_id=session_id,
            rater_id=rater_id,
            giver_id=gid,
            score=req.score,
            comment=req.comment,
            created_at=datetime.now(timezone.utc),
        )
        db.add(rating_obj)

        outbox = OutboxEvent(
            topic="rating.submitted",
            payload={
                "rating_id": str(rating_obj.id),
                "session_id": str(session_id),
                "rater_id": str(rater_id),
                "score": req.score,
            },
        )
        db.add(outbox)

        await db.commit()
        await db.refresh(rating_obj)

        # Notify sessions module via synchronous port that session was rated
        try:
            await ports.sessions.mark_session_rated(str(session_id))
        except Exception:
            pass

        # Escrow release to giver (80%) and platform fee (20%), and karma reward
        try:
            await ports.credits.release(str(session_id))
            await ports.credits.reward_karma(str(session_id), str(gid))
        except Exception:
            pass

        return RatingResponse(
            id=str(rating_obj.id),
            session_id=str(rating_obj.session_id),
            rater_id=str(rating_obj.rater_id),
            giver_id=str(rating_obj.giver_id),
            score=rating_obj.score,
            comment=rating_obj.comment,
            created_at=rating_obj.created_at.isoformat(),
        )


class RatingsPortImpl(RatingsPort):
    def __init__(self, service: RatingsService):
        self.service = service

    async def get_band(self, giver_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            gid = uuid.UUID(giver_id)
            result = await db.execute(
                select(SessionRating).where(SessionRating.giver_id == gid)
            )
            ratings = result.scalars().all()

            n = len(ratings)
            sum_ratings = sum(r.score for r in ratings)

            prior_mean = settings.PRIOR_MEAN
            prior_weight = settings.PRIOR_WEIGHT
            smoothed_avg = (prior_mean * prior_weight + sum_ratings) / (prior_weight + n)
            completion_rate = 1.0

            band = "Rising"
            if n >= settings.TRUSTED_MIN_SESSIONS and smoothed_avg >= settings.TRUSTED_RATING_THRESHOLD:
                band = "Trusted"
            if (
                n >= settings.TOP_RATED_MIN_SESSIONS
                and smoothed_avg >= settings.TOP_RATED_THRESHOLD
                and completion_rate >= settings.TOP_RATED_MIN_COMPLETION_RATE
            ):
                band = "Top Rated"

            return {
                "band": band,
                "smoothed_avg": round(smoothed_avg, 2),
                "n": n,
                "completion_rate": completion_rate,
            }


ratings_service = RatingsService()
ratings_port_instance = RatingsPortImpl(ratings_service)
