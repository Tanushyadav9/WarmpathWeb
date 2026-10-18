"""Business logic service and RatingsPort implementation for ratings and reputation."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker, OutboxEvent
from app.core.errors import AppError
from app.core.ports import ports, RatingsPort
from app.modules.ratings.models import SessionRating, Vouch
from app.modules.ratings.schemas import (
    RatingCreateInput,
    RatingResponse,
    GiverPublicRatingSummaryResponse,
    GiverBandResponse,
    LeaderboardEntryResponse,
    VouchCreateInput,
    VouchResponse,
    RatingReviewResolveInput,
)
from app.modules.matching.models import GiverProfile


class RatingsService:
    async def submit_rating(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        rater_id: uuid.UUID,
        req: RatingCreateInput,
        giver_id: Optional[uuid.UUID] = None,
    ) -> RatingResponse:
        session_info = await ports.sessions.get_session(str(session_id))
        if not session_info:
            raise AppError(code="session_not_found", message="Session not found", status_code=404)

        # 1. One rating per session check
        existing_res = await db.execute(
            select(SessionRating).where(SessionRating.session_id == session_id)
        )
        if existing_res.scalar_one_or_none():
            raise AppError(
                code="already_rated",
                message="This session has already been rated.",
                status_code=400,
            )

        if session_info.get("status") not in ("completed", "rated"):
            raise AppError(
                code="session_not_completed",
                message="A session cannot be rated before completion.",
                status_code=400,
            )

        gid = giver_id or uuid.UUID(session_info["giver_id"])

        # 2. Anti-gaming check: Block self-ratings
        if rater_id == gid:
            raise AppError(
                code="self_rating_blocked",
                message="Self-ratings are not allowed.",
                status_code=400,
            )

        # 3. Anti-gaming check: Mutual rating rings detection
        # Check how many times rater and giver have reciprocally rated each other in past sessions
        reciprocal_ratings_res = await db.execute(
            select(SessionRating).where(
                SessionRating.rater_id == gid,
                SessionRating.giver_id == rater_id,
            )
        )
        reciprocal_count = len(reciprocal_ratings_res.scalars().all())

        is_flagged = False
        flag_reason = None
        review_status = "approved"

        if reciprocal_count >= 2:
            is_flagged = True
            flag_reason = "mutual_rating_ring"
            review_status = "pending"

        # 4. Anti-gaming check: Outlier rating detection
        # When giver has >= 3 approved ratings, flag if |score - history_avg| >= 2.0
        if not is_flagged:
            history_ratings_res = await db.execute(
                select(SessionRating).where(
                    SessionRating.giver_id == gid,
                    SessionRating.is_flagged == False,
                    SessionRating.review_status == "approved",
                )
            )
            history_ratings = history_ratings_res.scalars().all()
            if len(history_ratings) >= 3:
                history_avg = sum(r.score for r in history_ratings) / len(history_ratings)
                if abs(req.score - history_avg) >= 2.0:
                    is_flagged = True
                    flag_reason = "outlier_rating"
                    review_status = "pending"

        rating_obj = SessionRating(
            session_id=session_id,
            rater_id=rater_id,
            giver_id=gid,
            score=req.score,
            tags=req.tags or [],
            comment=req.comment,
            is_flagged=is_flagged,
            flag_reason=flag_reason,
            review_status=review_status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(rating_obj)

        outbox = OutboxEvent(
            topic="rating.flagged_for_review" if is_flagged else "rating.submitted",
            payload={
                "rating_id": str(rating_obj.id),
                "session_id": str(session_id),
                "rater_id": str(rater_id),
                "giver_id": str(gid),
                "score": req.score,
                "is_flagged": is_flagged,
                "flag_reason": flag_reason,
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
            tags=rating_obj.tags or [],
            comment=rating_obj.comment,
            is_flagged=rating_obj.is_flagged,
            flag_reason=rating_obj.flag_reason,
            review_status=rating_obj.review_status,
            created_at=rating_obj.created_at.isoformat(),
        )

    async def get_band_info(self, db: AsyncSession, giver_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calculates giver rating band with Bayesian smoothing.
        Flagged ratings are strictly excluded from calculation.
        """
        result = await db.execute(
            select(SessionRating).where(
                SessionRating.giver_id == giver_id,
                SessionRating.is_flagged == False,
                SessionRating.review_status == "approved",
            )
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

        # Fair-start boost for new givers (n < 5) so they aren't buried
        fair_start_boost = max(0.0, round((5 - n) * 0.05, 2)) if n < 5 else 0.0
        ranking_score = round(smoothed_avg + fair_start_boost, 2)

        if band == "Rising":
            next_threshold_message = f"Complete {max(0, settings.TRUSTED_MIN_SESSIONS - n)} more sessions with rating >= {settings.TRUSTED_RATING_THRESHOLD} to reach Trusted."
        elif band == "Trusted":
            next_threshold_message = f"Complete {max(0, settings.TOP_RATED_MIN_SESSIONS - n)} more sessions with rating >= {settings.TOP_RATED_THRESHOLD} to reach Top Rated."
        else:
            next_threshold_message = "You have achieved Top Rated status! Keep up the outstanding mentorship."

        return {
            "giver_id": str(giver_id),
            "band": band,
            "smoothed_avg": round(smoothed_avg, 2),
            "n": n,
            "completion_rate": completion_rate,
            "ranking_score": ranking_score,
            "next_threshold_message": next_threshold_message,
        }

    async def get_public_summary(self, db: AsyncSession, giver_id: uuid.UUID) -> GiverPublicRatingSummaryResponse:
        """
        Student-facing giver rating summary.
        Do NOT show tier labels to students as a judgment; show rating, session count and tags.
        """
        result = await db.execute(
            select(SessionRating).where(
                SessionRating.giver_id == giver_id,
                SessionRating.is_flagged == False,
                SessionRating.review_status == "approved",
            ).order_by(SessionRating.created_at.desc())
        )
        ratings = result.scalars().all()

        n = len(ratings)
        if n == 0:
            rating = settings.PRIOR_MEAN
        else:
            sum_ratings = sum(r.score for r in ratings)
            smoothed_avg = (settings.PRIOR_MEAN * settings.PRIOR_WEIGHT + sum_ratings) / (settings.PRIOR_WEIGHT + n)
            rating = round(smoothed_avg, 2)

        tag_counts: Dict[str, int] = {}
        for r in ratings:
            for t in (r.tags or []):
                tag_counts[t] = tag_counts.get(t, 0) + 1

        sorted_tags = sorted(tag_counts.keys(), key=lambda t: tag_counts[t], reverse=True)
        top_tags = sorted_tags[:5]

        recent_reviews = [
            RatingResponse(
                id=str(r.id),
                session_id=str(r.session_id),
                rater_id=str(r.rater_id),
                giver_id=str(r.giver_id),
                score=r.score,
                tags=r.tags or [],
                comment=r.comment,
                is_flagged=r.is_flagged,
                flag_reason=r.flag_reason,
                review_status=r.review_status,
                created_at=r.created_at.isoformat(),
            )
            for r in ratings[:5]
        ]

        return GiverPublicRatingSummaryResponse(
            giver_id=str(giver_id),
            rating=rating,
            session_count=n,
            top_tags=top_tags,
            recent_reviews=recent_reviews,
        )

    async def create_vouch(
        self, db: AsyncSession, session_id: uuid.UUID, giver_id: uuid.UUID, req: VouchCreateInput
    ) -> VouchResponse:
        """Allows giver to vouch for student after a session with rating >= 4."""
        session_info = await ports.sessions.get_session(str(session_id))
        if not session_info:
            raise AppError(code="session_not_found", message="Session not found", status_code=404)

        if session_info.get("giver_id") != str(giver_id):
            raise AppError(code="forbidden", message="Only the session giver can vouch for the student.", status_code=403)

        # Check rating on the session
        rating_res = await db.execute(
            select(SessionRating).where(SessionRating.session_id == session_id)
        )
        rating = rating_res.scalar_one_or_none()
        if not rating:
            raise AppError(code="session_not_rated", message="Session must be rated before vouching.", status_code=400)

        if rating.score < 4:
            raise AppError(
                code="vouch_score_too_low",
                message="Vouching is only allowed after a rating of 4 or higher.",
                status_code=400,
            )

        # Check existing vouch
        existing = await db.execute(select(Vouch).where(Vouch.session_id == session_id))
        if existing.scalar_one_or_none():
            raise AppError(
                code="already_vouched",
                message="This student has already been vouched for this session.",
                status_code=400,
            )

        # Lookup giver profile
        prof_res = await db.execute(select(GiverProfile).where(GiverProfile.user_id == giver_id))
        prof = prof_res.scalar_one_or_none()
        giver_name = prof.full_name if prof else "Verified Mentor"
        headline = (prof.headline or "").strip() if prof else ""
        giver_company = "Tech Industry"
        if " at " in headline:
            giver_company = headline.split(" at ")[-1].strip()
        elif headline:
            giver_company = headline

        student_id = uuid.UUID(session_info["student_id"])
        vouch_obj = Vouch(
            session_id=session_id,
            giver_id=giver_id,
            student_id=student_id,
            giver_name=giver_name,
            giver_company=giver_company,
            note=req.note,
            created_at=datetime.now(timezone.utc),
        )
        db.add(vouch_obj)
        await db.commit()
        await db.refresh(vouch_obj)

        return VouchResponse(
            id=str(vouch_obj.id),
            session_id=str(vouch_obj.session_id),
            giver_id=str(vouch_obj.giver_id),
            student_id=str(vouch_obj.student_id),
            giver_name=vouch_obj.giver_name,
            giver_company=vouch_obj.giver_company,
            display_text=f"Vouched by {vouch_obj.giver_name} at {vouch_obj.giver_company}",
            note=vouch_obj.note,
            created_at=vouch_obj.created_at.isoformat(),
        )

    async def get_student_vouches(self, db: AsyncSession, student_id: uuid.UUID) -> List[VouchResponse]:
        """Returns all vouches for a student profile and recruiter views."""
        result = await db.execute(
            select(Vouch).where(Vouch.student_id == student_id).order_by(Vouch.created_at.desc())
        )
        vouches = result.scalars().all()
        return [
            VouchResponse(
                id=str(v.id),
                session_id=str(v.session_id),
                giver_id=str(v.giver_id),
                student_id=str(v.student_id),
                giver_name=v.giver_name,
                giver_company=v.giver_company,
                display_text=f"Vouched by {v.giver_name} at {v.giver_company}",
                note=v.note,
                created_at=v.created_at.isoformat(),
            )
            for v in vouches
        ]

    async def get_leaderboard(
        self,
        db: AsyncSession,
        college: Optional[str] = None,
        month: Optional[str] = None,
        limit: int = 20,
    ) -> List[LeaderboardEntryResponse]:
        """Top Giver leaderboard per institution and per month."""
        query = select(GiverProfile)
        if college:
            query = query.where(GiverProfile.college.ilike(f"%{college}%"))

        profiles_res = await db.execute(query)
        profiles = profiles_res.scalars().all()

        entries = []
        for prof in profiles:
            rating_query = select(SessionRating).where(
                SessionRating.giver_id == prof.user_id,
                SessionRating.is_flagged == False,
                SessionRating.review_status == "approved",
            )
            if month:
                try:
                    parts = month.split("-")
                    year = int(parts[0])
                    m = int(parts[1])
                    start_date = datetime(year, m, 1, tzinfo=timezone.utc)
                    end_date = datetime(year + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1, tzinfo=timezone.utc)
                    rating_query = rating_query.where(
                        SessionRating.created_at >= start_date,
                        SessionRating.created_at < end_date,
                    )
                except Exception:
                    pass

            r_res = await db.execute(rating_query)
            ratings = r_res.scalars().all()

            n = len(ratings)
            if n == 0:
                smoothed_avg = settings.PRIOR_MEAN
                raw_avg = 0.0
            else:
                sum_ratings = sum(r.score for r in ratings)
                smoothed_avg = (settings.PRIOR_MEAN * settings.PRIOR_WEIGHT + sum_ratings) / (settings.PRIOR_WEIGHT + n)
                raw_avg = sum_ratings / n

            tag_counts: Dict[str, int] = {}
            for r in ratings:
                for t in (r.tags or []):
                    tag_counts[t] = tag_counts.get(t, 0) + 1
            sorted_tags = sorted(tag_counts.keys(), key=lambda t: tag_counts[t], reverse=True)[:3]

            fair_start_boost = max(0.0, round((5 - n) * 0.05, 2)) if n < 5 else 0.0
            ranking_score = round(smoothed_avg + fair_start_boost, 2)
            karma_points = n * 10

            entries.append({
                "giver_id": str(prof.user_id),
                "full_name": prof.full_name,
                "headline": prof.headline,
                "college": prof.college,
                "session_count": n,
                "average_rating": round(raw_avg if n > 0 else smoothed_avg, 2),
                "ranking_score": ranking_score,
                "top_tags": sorted_tags,
                "karma_points": karma_points,
            })

        entries.sort(key=lambda x: (x["ranking_score"], x["session_count"]), reverse=True)

        leaderboard = []
        for idx, item in enumerate(entries[:limit], start=1):
            leaderboard.append(
                LeaderboardEntryResponse(
                    rank=idx,
                    giver_id=item["giver_id"],
                    full_name=item["full_name"],
                    headline=item["headline"],
                    college=item["college"],
                    session_count=item["session_count"],
                    average_rating=item["average_rating"],
                    ranking_score=item["ranking_score"],
                    top_tags=item["top_tags"],
                    karma_points=item["karma_points"],
                )
            )

        return leaderboard

    async def list_reviews(self, db: AsyncSession, status: str = "pending") -> List[RatingResponse]:
        """Admin review queue for outlier and mutual ring flagged ratings."""
        query = select(SessionRating)
        if status:
            query = query.where(SessionRating.review_status == status)
        else:
            query = query.where(SessionRating.is_flagged == True)

        result = await db.execute(query.order_by(SessionRating.created_at.desc()))
        ratings = result.scalars().all()
        return [
            RatingResponse(
                id=str(r.id),
                session_id=str(r.session_id),
                rater_id=str(r.rater_id),
                giver_id=str(r.giver_id),
                score=r.score,
                tags=r.tags or [],
                comment=r.comment,
                is_flagged=r.is_flagged,
                flag_reason=r.flag_reason,
                review_status=r.review_status,
                created_at=r.created_at.isoformat(),
            )
            for r in ratings
        ]

    async def resolve_review(
        self, db: AsyncSession, rating_id: uuid.UUID, req: RatingReviewResolveInput
    ) -> RatingResponse:
        """Admin resolves a flagged rating by either approving or rejecting it."""
        res = await db.execute(select(SessionRating).where(SessionRating.id == rating_id))
        rating = res.scalar_one_or_none()
        if not rating:
            raise AppError(code="rating_not_found", message="Rating not found", status_code=404)

        if req.decision.lower() == "approve":
            rating.is_flagged = False
            rating.review_status = "approved"
        elif req.decision.lower() == "reject":
            rating.is_flagged = True
            rating.review_status = "rejected"
        else:
            raise AppError(code="invalid_decision", message="Decision must be 'approve' or 'reject'", status_code=400)

        await db.commit()
        await db.refresh(rating)
        return RatingResponse(
            id=str(rating.id),
            session_id=str(rating.session_id),
            rater_id=str(rating.rater_id),
            giver_id=str(rating.giver_id),
            score=rating.score,
            tags=rating.tags or [],
            comment=rating.comment,
            is_flagged=rating.is_flagged,
            flag_reason=rating.flag_reason,
            review_status=rating.review_status,
            created_at=rating.created_at.isoformat(),
        )


class RatingsPortImpl(RatingsPort):
    def __init__(self, service: RatingsService):
        self.service = service

    async def get_band(self, giver_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            gid = uuid.UUID(giver_id)
            return await self.service.get_band_info(db, gid)


ratings_service = RatingsService()
ratings_port_instance = RatingsPortImpl(ratings_service)
