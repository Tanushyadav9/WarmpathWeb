"""Business logic service for matching and recommendations."""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import ports
from app.modules.matching.models import GiverProfile
from app.modules.matching.schemas import GiverRecommendationItem, RecommendationsResponse


class MatchingService:
    async def get_or_create_profile(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        full_name: str = "Alex Mercer",
        headline: str = "Senior Engineer at CloudCorp",
        college: str = "VIPS-TC",
        skills: str = "Python, FastAPI, Architecture",
    ) -> GiverProfile:
        result = await db.execute(
            select(GiverProfile).where(GiverProfile.user_id == user_id)
        )
        prof = result.scalar_one_or_none()
        if not prof:
            prof = GiverProfile(
                user_id=user_id,
                full_name=full_name,
                headline=headline,
                college=college,
                skills=skills,
                is_verified=True,
            )
            db.add(prof)
            await db.commit()
            await db.refresh(prof)
        return prof

    async def get_recommendations(
        self, db: AsyncSession, student_id: uuid.UUID
    ) -> RecommendationsResponse:
        result = await db.execute(select(GiverProfile))
        profiles = result.scalars().all()

        if not profiles:
            return RecommendationsResponse(items=[])

        user_ids = [str(p.user_id) for p in profiles]

        try:
            presence_map = await ports.presence.status(user_ids)
        except Exception:
            presence_map = {}

        items: List[GiverRecommendationItem] = []
        for prof in profiles:
            uid_str = str(prof.user_id)
            pres = presence_map.get(uid_str, {})

            status = pres.get("status", "inactive")
            capacity_reached = pres.get("capacity_reached", False)
            capacity_left = pres.get("capacity_left", 0)

            # Rule: Giver disappears from matching if capacity is reached OR status is inactive
            if capacity_reached or status == "inactive":
                continue

            skills_list = [s.strip() for s in (prof.skills or "").split(",") if s.strip()]

            items.append(
                GiverRecommendationItem(
                    giver_id=uid_str,
                    full_name=prof.full_name,
                    headline=prof.headline or "Alumni Mentor",
                    college=prof.college or "Same College",
                    skills=skills_list,
                    status=status,
                    status_color=pres.get("status_color", "#15803D"),
                    status_label=pres.get("status_label", "Active now"),
                    today_window=pres.get("today_window"),
                    response_rate=pres.get("response_rate", 100.0),
                    avg_reply_time_display=pres.get("avg_reply_time_display", "N/A"),
                    capacity_left=capacity_left,
                    why_matched=f"Verified alumni • {pres.get('status_label', 'Available')}",
                )
            )

        return RecommendationsResponse(items=items)


matching_service = MatchingService()
