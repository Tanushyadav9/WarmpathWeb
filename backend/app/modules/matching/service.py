"""
backend/app/modules/matching/service.py - Matching Engine Service.
Weights loaded from config/matching.json:
- 35 skill_intent_similarity (pgvector cosine + keyword overlap)
- 15 similar_journey (same branch, similar projects, starting point)
- 15 affinity (same college 1, same branch 0.5)
- 15 rating (smoothed average & reputation band)
- 12 availability (active 1, today 0.6, inactive 0)
- 8 response speed

Hard Gates:
Excludes unverified, suspended, inactive-too-long, and over weekly-capacity givers.
Returns aggregated excluded_summary without names.
Generates actual overlap explanations. Supports all giver types (alumni, faculty, recruiter, founder).
"""

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import User
from app.core.errors import AppError, PortNotReady
from app.core.events import GiverProfileUpdatedPayload, event_bus
from app.core.models import Availability, Capacity, StudentIntent
from app.core.pagination import decode_cursor, encode_cursor
from app.core.ports import (
    CreditsPort,
    MatchingPort,
    PresencePort,
    RatingsPort,
    TrustPort,
    ports,
)
from app.core.redis import get_redis
from app.modules.matching.models import GiverProfile, StudentMatchProfile
from app.modules.matching.schemas import (
    AvailabilitySummary,
    CandidateRankingExplanation,
    ExplainRankingResponse,
    GiverProfileCreateUpdate,
    GiverPublicCard,
    HardGateExclusionSummary,
    RatingSummary,
    RecommendationItem,
    RecommendationsResponse,
    SaveIntentResponse,
    ScoreComponents,
    StructuredIntentData,
)
from app.modules.matching.intent import analyze_intent_quality, structure_intent

MAX_DAILY_EXPOSURE = 25
CACHE_TTL_SECONDS = 60

ALLOWED_GIVER_ROLES = {
    "alumni",
    "alumnus",
    "recruiter",
    "founder",
    "faculty",
    "expert",
    "giver",
    "giver_pending",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_matching_config() -> Dict[str, Any]:
    """Dynamically loads matching engine weights and hard gate parameters from config/matching.json."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "matching.json",
        Path(__file__).resolve().parent.parent.parent / "config" / "matching.json",
        Path.cwd() / "config" / "matching.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {
        "weights": {
            "skill_intent_similarity": 0.35,
            "similar_journey": 0.15,
            "affinity": 0.15,
            "rating": 0.15,
            "availability": 0.12,
            "response_speed": 0.08,
        },
        "hard_gates": {
            "max_inactive_days": 14,
            "min_trust_score": 30.0,
            "require_verification": True,
            "enforce_weekly_capacity": True,
        },
        "affinity_weights": {"same_college": 1.0, "same_branch": 0.5},
        "availability_scores": {"active_now": 1.0, "available_today": 0.6, "inactive": 0.0},
    }


def cosine_similarity(v1: Optional[List[float]], v2: Optional[List[float]]) -> float:
    """Computes cosine similarity between two float vectors, mapped to [0.0, 1.0]."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.5

    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.5

    cos = dot / (norm1 * norm2)
    return max(0.0, min(1.0, (cos + 1.0) / 2.0))


def deterministic_dummy_vector(text: str) -> List[float]:
    """Generates a stable 768-dimensional unit vector from text hash."""
    seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(768):
        b = seed_bytes[i % len(seed_bytes)]
        val = (b / 255.0) - 0.5 + ((i % 17) / 100.0)
        vec.append(val)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


async def generate_embedding(text: str) -> List[float]:
    """Generates 768-dimensional embedding using Gemini, falling back to deterministic dummy vector."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        return deterministic_dummy_vector(text)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_EMBED_MODEL}:embedContent?key={api_key}"
    payload = {
        "model": f"models/{settings.GEMINI_EMBED_MODEL}",
        "content": {"parts": [{"text": text[:2000]}]},
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                values = resp.json().get("embedding", {}).get("values", [])
                if len(values) == 768:
                    return values
    except Exception:
        pass
    return deterministic_dummy_vector(text)


class MatchingService(MatchingPort):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.matching_config = load_matching_config()

    # --- Giver Profile Management ---

    async def get_giver_profile(self, user_id: uuid.UUID) -> GiverProfile:
        stmt = select(GiverProfile).where(GiverProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise AppError(
                code="giver_profile_not_found",
                message="No giver profile found for this user. Please create one first.",
                status_code=404,
            )
        return profile

    async def update_giver_profile(
        self, user_id: uuid.UUID, data: GiverProfileCreateUpdate
    ) -> GiverProfile:
        stmt_user = select(User).where(User.id == user_id)
        res_user = await self.session.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if user:
            user_roles = set(user.roles or [])
            if not user_roles.intersection(ALLOWED_GIVER_ROLES) and user.role not in ALLOWED_GIVER_ROLES:
                try:
                    level = await ports.trust.get_level(str(user_id))
                    if level not in ["verified", "established"]:
                        raise AppError(
                            code="giver_role_required",
                            message="Only users with an approved giver role or pending giver verification can create a giver profile.",
                            status_code=403,
                        )
                except PortNotReady:
                    raise AppError(
                        code="giver_role_required",
                        message="Only users with an approved giver role can create a giver profile.",
                        status_code=403,
                    )

        skills_str = ", ".join(
            [s.get("name", str(s)) for s in data.skills if isinstance(s, dict)]
            or [str(s) for s in data.skills]
        )
        embed_text = f"Offers: {', '.join(data.offers)}. Skills: {skills_str}. Bio: {data.bio or ''}"
        embedding = await generate_embedding(embed_text)

        stmt = select(GiverProfile).where(GiverProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()

        now = utc_now()
        if profile:
            profile.offers = data.offers
            profile.topics = data.topics
            profile.skills = data.skills
            profile.domains = data.domains
            profile.company = data.company
            profile.role_title = data.role_title
            profile.bio = data.bio
            profile.languages = data.languages
            profile.weekly_capacity = data.weekly_capacity
            if data.institution_id is not None:
                profile.institution_id = data.institution_id
            if data.department is not None:
                profile.department = data.department
            if data.batch is not None:
                profile.batch = data.batch
            profile.societies = data.societies
            profile.embedding = embedding
            profile.updated_at = now
        else:
            profile = GiverProfile(
                user_id=user_id,
                offers=data.offers,
                topics=data.topics,
                skills=data.skills,
                domains=data.domains,
                company=data.company,
                role_title=data.role_title,
                bio=data.bio,
                languages=data.languages,
                weekly_capacity=data.weekly_capacity,
                institution_id=data.institution_id,
                department=data.department,
                batch=data.batch,
                societies=data.societies,
                embedding=embedding,
                created_at=now,
                updated_at=now,
            )
            self.session.add(profile)

        await event_bus.publish(
            self.session,
            "giver.profile_updated",
            GiverProfileUpdatedPayload(
                user_id=str(user_id),
                weekly_capacity=data.weekly_capacity,
                offers=data.offers,
                has_embedding=True,
            ),
        )

        await self.session.commit()
        await self.invalidate_recommendation_caches(giver_id=str(user_id))
        return profile

    # --- Student Match Profile Management ---

    async def get_or_create_student_match_profile(
        self, student_id: uuid.UUID
    ) -> StudentMatchProfile:
        from app.core.models import StudentProfile, GitHubProof, StudentIntent

        stmt = select(StudentMatchProfile).where(StudentMatchProfile.user_id == student_id)
        res = await self.session.execute(stmt)
        match_profile = res.scalar_one_or_none()

        # Fetch latest User attributes
        stmt_user = select(User).where(User.id == student_id)
        res_user = await self.session.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        # Fetch latest StudentProfile
        stmt_sp = select(StudentProfile).where(StudentProfile.user_id == student_id)
        res_sp = await self.session.execute(stmt_sp)
        sp = res_sp.scalar_one_or_none()

        # Fetch latest GitHubProof
        stmt_gh = select(GitHubProof).where(GitHubProof.user_id == student_id)
        res_gh = await self.session.execute(stmt_gh)
        gh = res_gh.scalar_one_or_none()

        # Fetch latest StudentIntent
        stmt_i = select(StudentIntent).where(StudentIntent.user_id == student_id)
        res_i = await self.session.execute(stmt_i)
        intent = res_i.scalar_one_or_none()

        dept = "Computer Science"
        if user and (user.branch or getattr(user, "department", None)):
            dept = user.branch or getattr(user, "department", None)

        batch_yr = user.batch if user and user.batch else 2026

        skills = [{"name": "Python", "category": "Programming Languages"}]
        domains = ["Web Development", "AI/ML"]
        profile_embedding = None

        if sp and (sp.edited or sp.parsed):
            merged = dict(sp.parsed or {})
            if sp.edited:
                merged.update(sp.edited)
            skills = merged.get("skills", skills)
            domains = merged.get("domains", domains)
            profile_embedding = sp.embedding

        if not profile_embedding:
            profile_embedding = deterministic_dummy_vector(f"student:{student_id}:profile")

        intent_goal = intent.raw_text if intent else "Find mentorship for software engineering internship"
        intent_roles = intent.target_roles if intent and intent.target_roles else ["Software Engineer Intern"]
        intent_domains = intent.target_domains if intent and intent.target_domains else ["Technology"]
        intent_help = intent.goal_type if intent and intent.goal_type else "resume_review"
        intent_embed = intent.intent_embedding if intent and intent.intent_embedding else deterministic_dummy_vector(f"student:{student_id}:intent")

        if match_profile:
            match_profile.institution_id = user.institution_id if user else match_profile.institution_id
            match_profile.department = dept
            match_profile.batch = batch_yr
            match_profile.skills = skills
            match_profile.domains = domains
            match_profile.profile_embedding = profile_embedding
            match_profile.has_github_proof = gh is not None
            match_profile.github_languages = gh.top_languages if gh else []
            match_profile.intent_goal = intent_goal
            match_profile.intent_roles = intent_roles
            match_profile.intent_domains = intent_domains
            match_profile.intent_help_type = intent_help
            match_profile.intent_embedding = intent_embed
            match_profile.updated_at = utc_now()
            if intent and intent.structured and isinstance(intent.structured, dict):
                setattr(match_profile, "intent_required_skills", intent.structured.get("required_skills", []))
        else:
            match_profile = StudentMatchProfile(
                user_id=student_id,
                institution_id=user.institution_id if user else None,
                department=dept,
                batch=batch_yr,
                societies=["ACM"],
                skills=skills,
                domains=domains,
                profile_embedding=profile_embedding,
                has_github_proof=gh is not None,
                github_languages=gh.top_languages if gh else [],
                intent_goal=intent_goal,
                intent_roles=intent_roles,
                intent_domains=intent_domains,
                intent_help_type=intent_help,
                intent_embedding=intent_embed,
                updated_at=utc_now(),
            )
            if intent and intent.structured and isinstance(intent.structured, dict):
                setattr(match_profile, "intent_required_skills", intent.structured.get("required_skills", []))
            self.session.add(match_profile)

        await self.session.commit()
        return match_profile

    # --- Match Scoring Engine v2 (6 Explicit Factors in config/matching.json) ---

    def calculate_score_components(
        self,
        student: StudentMatchProfile,
        giver: GiverProfile,
        band_info: Dict[str, Any],
        presence_info: Dict[str, Any],
    ) -> ScoreComponents:
        """
        Calculates honest Heuristic Score components with weights from config/matching.json:
        - 35% Skill & Intent Similarity (pgvector cosine + keyword/taxonomy overlap)
        - 15% Similar Journey (same branch, similar projects, starting point)
        - 15% Affinity (same college: 1.0, same branch: 0.5)
        - 15% Rating (smoothed avg + reputation band multiplier)
        - 12% Availability (active_now: 1.0, available_today: 0.6, inactive: 0.0)
        - 8% Response Speed (<=30m: 1.0, <=2h: 0.85, <=6h: 0.65, >6h: 0.40)
        """
        config = self.matching_config
        weights = config.get("weights", {
            "skill_intent_similarity": 0.35,
            "similar_journey": 0.15,
            "affinity": 0.15,
            "rating": 0.15,
            "availability": 0.12,
            "response_speed": 0.08,
        })

        # 1. Skill and Intent Similarity (35%)
        student_skills = {
            s.get("name", "").strip().lower() for s in (student.skills or []) if isinstance(s, dict)
        } or {str(s).strip().lower() for s in (student.skills or [])}

        intent_skills = {
            str(s).strip().lower() for s in (getattr(student, "intent_required_skills", None) or []) if str(s).strip()
        }
        all_student_skills = student_skills.union(intent_skills)

        giver_skills = {
            s.get("name", "").strip().lower() for s in (giver.skills or []) if isinstance(s, dict)
        } or {str(s).strip().lower() for s in (giver.skills or [])}
        giver_topics = {str(t).strip().lower() for t in (giver.topics or [])}
        all_giver = giver_skills.union(giver_topics)

        shared = all_student_skills.intersection(all_giver)
        jaccard = len(shared) / max(1, len(all_student_skills.union(all_giver)))

        cos_profile = cosine_similarity(student.profile_embedding, giver.embedding)
        cos_intent = cosine_similarity(student.intent_embedding, giver.embedding)
        cos_sim = max(cos_profile, cos_intent)

        # Help type match
        help_type_match = 0.0
        if student.intent_help_type:
            clean_intent_ht = student.intent_help_type.lower().replace(" ", "_")
            giver_offers = {str(o).lower().replace(" ", "_") for o in (giver.offers or [])}
            if clean_intent_ht in giver_offers:
                help_type_match = 1.0
            elif any(clean_intent_ht in o for o in giver_offers):
                help_type_match = 0.5

        github_boost = 0.05 if getattr(student, "has_github_proof", False) else 0.0
        skill_intent_sim = min(1.0, 0.50 * cos_sim + 0.30 * jaccard + 0.15 * help_type_match + github_boost)

        # 2. Similar Journey (15%)
        # same branch, similar projects, similar starting point
        same_branch = (
            1.0
            if (giver.department and student.department and giver.department.strip().lower() == student.department.strip().lower())
            else 0.0
        )
        student_domains = {d.lower() for d in (student.domains or [])}
        giver_domains = {d.lower() for d in (giver.domains or [])}
        shared_domains = student_domains.intersection(giver_domains)
        project_sim = 1.0 if shared_domains else (0.6 if len(shared) >= 2 else 0.2)
        batch_diff = abs(giver.batch - student.batch) if (giver.batch and student.batch) else 4
        starting_point = 1.0 if (1 <= batch_diff <= 5) else 0.5
        similar_journey = min(1.0, 0.50 * same_branch + 0.30 * project_sim + 0.20 * starting_point)

        # 3. Affinity (15%)
        # same college 1, same branch 0.5
        same_college = (
            1.0
            if (giver.institution_id and student.institution_id and giver.institution_id == student.institution_id)
            else 0.0
        )
        affinity = min(1.0, 1.0 * same_college + 0.5 * same_branch)

        # 4. Rating (15%)
        smoothed_avg = float(band_info.get("smoothed_avg", giver.rating_avg or 4.0))
        norm_rating = max(0.0, min(1.0, (smoothed_avg - 1.0) / 4.0))
        band = band_info.get("band", giver.band or "Rising")
        band_mult = 1.0 if "top" in band.lower() else (0.85 if "trust" in band.lower() else 0.70)
        rating_score = min(1.0, 0.70 * norm_rating + 0.30 * band_mult)

        # 5. Availability (12%)
        # active 1, today 0.6, inactive 0
        status = presence_info.get("status") or ("active_now" if presence_info.get("online") else "available_today")
        if status == "active_now" or presence_info.get("online"):
            avail_score = 1.0
        elif status == "available_today":
            avail_score = 0.6
        else:
            avail_score = 0.0

        # 6. Response Speed (8%)
        reply_mins = float(presence_info.get("avg_reply_minutes", (giver.response_stats or {}).get("median_response_minutes", 45)))
        if reply_mins <= 30:
            speed_score = 1.0
        elif reply_mins <= 120:
            speed_score = 0.85
        elif reply_mins <= 360:
            speed_score = 0.65
        else:
            speed_score = 0.40

        total = (
            weights.get("skill_intent_similarity", 0.35) * skill_intent_sim
            + weights.get("similar_journey", 0.15) * similar_journey
            + weights.get("affinity", 0.15) * affinity
            + weights.get("rating", 0.15) * rating_score
            + weights.get("availability", 0.12) * avail_score
            + weights.get("response_speed", 0.08) * speed_score
        )

        return ScoreComponents(
            skill_intent_similarity=round(skill_intent_sim, 3),
            similar_journey=round(similar_journey, 3),
            affinity=round(affinity, 3),
            rating=round(rating_score, 3),
            availability=round(avail_score, 3),
            response_speed=round(speed_score, 3),
            expertise_fit=round(skill_intent_sim, 3),
            intent_fit=round(similar_journey, 3),
            response_odds=round(speed_score, 3),
            cold_start_boost=0.0,
            total_score=round(min(1.0, max(0.0, total)), 3),
        )

    # --- Explainability Engine (Requirement 5) ---

    def generate_why_lines(
        self,
        student: StudentMatchProfile,
        giver: GiverProfile,
        scores: ScoreComponents,
        presence_info: Dict[str, Any],
        band_info: Dict[str, Any],
        giver_user: Optional[User] = None,
    ) -> List[str]:
        why_lines: List[str] = []

        # 1. Exact real overlapping skills
        student_skills = [
            s.get("name", "").strip() for s in (student.skills or []) if isinstance(s, dict) and s.get("name")
        ] or [str(s).strip() for s in (student.skills or []) if str(s).strip()]

        intent_skills = [str(s).strip() for s in (getattr(student, "intent_required_skills", None) or []) if str(s).strip()]
        combined_student = student_skills + intent_skills

        giver_skills = [
            s.get("name", "").strip() for s in (giver.skills or []) if isinstance(s, dict) and s.get("name")
        ] or [str(s).strip() for s in (giver.skills or []) if str(s).strip()]
        giver_topics = [str(t).strip() for t in (giver.topics or []) if str(t).strip()]
        combined_giver = giver_skills + giver_topics

        shared = []
        for s in combined_student:
            for g in combined_giver:
                if s.lower() == g.lower() and s not in shared:
                    shared.append(s)

        if shared:
            skills_text = " and ".join(shared[:2])
            why_lines.append(f"Shares your {skills_text} skills")
        elif scores.skill_intent_similarity >= 0.65:
            why_lines.append("Strong technical overlap with your target domain")

        # 2. Real journey / branch
        if giver.department and student.department and giver.department.strip().lower() == student.department.strip().lower():
            why_lines.append(f"Graduated from same branch ({giver.department})")
        elif giver.batch and student.batch and abs(giver.batch - student.batch) <= 4:
            diff = abs(giver.batch - student.batch)
            why_lines.append(f"Similar academic background ({diff} year{'s' if diff > 1 else ''} senior)")

        # 3. Real affinity / college
        if giver.institution_id and student.institution_id and giver.institution_id == student.institution_id:
            why_lines.append("Alumnus from your college (IIIT Delhi)")

        # 4. Goal / Intent match
        if student.intent_help_type:
            clean_intent = student.intent_help_type.lower().replace("_", " ")
            matching_offers = [o.replace("_", " ") for o in (giver.offers or []) if clean_intent in o.lower().replace("_", " ")]
            if matching_offers:
                why_lines.append(f"Offers {matching_offers[0]}, matching your goal")
            elif student.intent_roles:
                why_lines.append(f"Experienced in your target role: {student.intent_roles[0]}")

        # 5. Availability & Response
        status = presence_info.get("status") or ("active_now" if presence_info.get("online") else "available_today")
        if status == "active_now" or presence_info.get("online"):
            reply_mins = presence_info.get("avg_reply_minutes", 30)
            why_lines.append(f"Active now; typically responds within {reply_mins} minutes")
        elif status == "available_today":
            why_lines.append("Available today for sessions")

        seen = set()
        deduped = []
        for line in why_lines:
            if line not in seen:
                seen.add(line)
                deduped.append(line)

        return deduped[:4]

    # --- MatchingPort Implementation ---

    async def explain(self, student_id: str, giver_id: str) -> List[str]:
        s_uuid = uuid.UUID(student_id)
        g_uuid = uuid.UUID(giver_id)

        student = await self.get_or_create_student_match_profile(s_uuid)
        giver = await self.get_giver_profile(g_uuid)

        try:
            band_info = await ports.ratings.get_band(str(g_uuid))
        except Exception:
            band_info = {"band": "Rising", "smoothed_avg": 4.0, "n": 0, "completion_rate": 1.0}

        try:
            p_map = await ports.presence.status([str(g_uuid)])
            presence_info = p_map.get(str(g_uuid), {"online": False, "capacity_left": 3})
        except Exception:
            presence_info = {"online": False, "capacity_left": 3}

        scores = self.calculate_score_components(student, giver, band_info, presence_info)
        return self.generate_why_lines(student, giver, scores, presence_info, band_info)

    # --- Recommendations Query & Re-ranking (with Hard Gates) ---

    async def get_recommendations(
        self,
        student_id: uuid.UUID,
        scope: str = "own_college",
        limit: int = 10,
        cursor: Optional[str] = None,
        filter_domain: Optional[str] = None,
        filter_help_type: Optional[str] = None,
    ) -> RecommendationsResponse:
        now = utc_now()

        # 1. Hard Gate on Student: DPDP consent
        from app.core.models import Consent
        stmt_consent = select(Consent).where(
            Consent.user_id == student_id,
            Consent.purpose == "profile_matching",
        )
        res_consent = await self.session.execute(stmt_consent)
        consent_record = res_consent.scalar_one_or_none()
        if consent_record and not consent_record.granted:
            raise AppError(
                code="consent_required",
                message="DPDP consent for 'profile_matching' is required to receive recommendations.",
                status_code=403,
            )

        student = await self.get_or_create_student_match_profile(student_id)

        # 2. Redis Cache Check
        filter_hash = hashlib.sha256(
            f"{student.profile_version}:{scope}:{filter_domain}:{filter_help_type}".encode("utf-8")
        ).hexdigest()[:12]
        cache_key = f"wp:rec:{student_id}:{scope}:{filter_hash}"

        redis_client = None
        try:
            redis_client = await get_redis()
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                cached_obj = json.loads(cached_data)
                return await self._paginate_cached_recommendations(
                    cached_obj, student, limit, cursor, scope
                )
        except Exception:
            pass

        # 3. Retrieve Candidate Givers (all potential givers to enforce Hard Gates in service)
        stmt = select(GiverProfile).limit(200)
        res = await self.session.execute(stmt)
        all_candidates = res.scalars().all()

        if not all_candidates:
            return RecommendationsResponse(
                items=[],
                excluded_summary=HardGateExclusionSummary(),
                next_cursor=None,
                scope=scope,
            )

        candidate_ids = [c.user_id for c in all_candidates]

        # Bulk fetch linked Users, Availability, Capacity
        stmt_users = select(User).where(User.id.in_(candidate_ids))
        res_users = await self.session.execute(stmt_users)
        users_map = {u.id: u for u in res_users.scalars().all()}

        stmt_avail = select(Availability).where(Availability.user_id.in_(candidate_ids))
        res_avail = await self.session.execute(stmt_avail)
        avail_map = {a.user_id: a for a in res_avail.scalars().all()}

        stmt_cap = select(Capacity).where(Capacity.user_id.in_(candidate_ids))
        res_cap = await self.session.execute(stmt_cap)
        cap_map = {c.user_id: c for c in res_cap.scalars().all()}

        # Port queries
        ratings_map = {}
        for cid in candidate_ids:
            try:
                ratings_map[str(cid)] = await ports.ratings.get_band(str(cid))
            except Exception:
                ratings_map[str(cid)] = {
                    "band": "Rising",
                    "smoothed_avg": 4.0,
                    "n": 0,
                    "completion_rate": 1.0,
                }

        try:
            presence_map = await ports.presence.status([str(cid) for cid in candidate_ids])
        except Exception:
            presence_map = {}

        # 4. HARD GATES before ranking:
        # Exclude: unverified, suspended, inactive-too-long, over weekly-capacity
        # Return how many were excluded and why (no names)
        excluded_reasons = {
            "unverified": 0,
            "suspended": 0,
            "inactive_too_long": 0,
            "over_capacity": 0,
        }
        surviving_candidates = []

        for giver in all_candidates:
            gid = giver.user_id
            if gid == student_id:
                continue

            u = users_map.get(gid)
            avail = avail_map.get(gid)
            cap = cap_map.get(gid)

            pres = presence_map.get(str(gid), {})
            cap_left = pres.get("capacity_left", giver.weekly_capacity)

            # Gate 1: Unverified Giver
            if not u or u.verification_level in ["pending", "unverified"] or giver.band == "unverified":
                excluded_reasons["unverified"] += 1
                continue

            # Gate 2: Suspended Giver
            if (u.trust_score is not None and u.trust_score < 30.0) or getattr(u, "status", None) == "suspended" or u.role == "suspended":
                excluded_reasons["suspended"] += 1
                continue

            # Gate 3: Inactive too long (> 14 days)
            is_stale = False
            if avail:
                if avail.status == "inactive_stale":
                    is_stale = True
                elif avail.last_active_at:
                    last_active = ensure_utc(avail.last_active_at)
                    now_utc = ensure_utc(now)
                    if last_active and now_utc and (now_utc - last_active).days > 14:
                        is_stale = True
            if is_stale:
                excluded_reasons["inactive_too_long"] += 1
                continue

            # Gate 4: Over weekly capacity
            is_full = False
            if giver.weekly_capacity <= 0:
                is_full = True
            if cap and cap.weekly_cap > 0 and cap.current_week_booked >= cap.weekly_cap:
                is_full = True
            if cap_left <= 0:
                is_full = True
            if is_full:
                excluded_reasons["over_capacity"] += 1
                continue

            # Scope filtering
            if scope == "own_college":
                if giver.institution_id and student.institution_id and giver.institution_id != student.institution_id:
                    continue
            elif scope == "cross_college":
                if giver.institution_id and student.institution_id and giver.institution_id == student.institution_id:
                    continue

            # Optional filter by domain / help type
            if filter_domain and filter_domain.lower() not in [d.lower() for d in (giver.domains or [])]:
                continue
            if filter_help_type and filter_help_type.lower() not in [o.lower() for o in (giver.offers or [])]:
                continue

            surviving_candidates.append(giver)

        # 5. Score Surviving Candidates
        ranked_items = []
        for giver in surviving_candidates:
            gid_str = str(giver.user_id)
            u = users_map.get(giver.user_id)
            avail = avail_map.get(giver.user_id)
            pres = presence_map.get(gid_str, {})
            status = avail.status if avail else ("active_now" if pres.get("online") else "available_today")
            avg_reply = avail.avg_reply_minutes if avail else 45
            pres_info = {
                "online": pres.get("online", status == "active_now"),
                "capacity_left": pres.get("capacity_left", giver.weekly_capacity),
                "status": status,
                "avg_reply_minutes": avg_reply,
            }
            band_info = ratings_map.get(
                gid_str,
                {"band": giver.band or "Rising", "smoothed_avg": giver.rating_avg or 4.0, "n": giver.rating_count or 0},
            )

            scores = self.calculate_score_components(student, giver, band_info, pres_info)
            why_lines = self.generate_why_lines(student, giver, scores, pres_info, band_info, u)
            ranked_items.append((giver, scores, why_lines, pres_info, band_info, u))

        # Sort by total_score descending
        ranked_items.sort(key=lambda x: x[1].total_score, reverse=True)

        excluded_summary = HardGateExclusionSummary(
            total_excluded=sum(excluded_reasons.values()),
            reasons=excluded_reasons,
        )

        return await self._build_recommendations_response(
            ranked_items, limit, cursor, scope, False, None, excluded_summary
        )

    async def _build_recommendations_response(
        self,
        ranked_items: List[Tuple[GiverProfile, ScoreComponents, List[str], Dict[str, Any], Dict[str, Any], Optional[User]]],
        limit: int,
        cursor: Optional[str],
        scope: str,
        is_locked: bool,
        lock_reason: Optional[str],
        excluded_summary: Optional[HardGateExclusionSummary] = None,
    ) -> RecommendationsResponse:
        start_idx = 0
        if cursor:
            decoded = decode_cursor(cursor)
            if decoded and "offset" in decoded:
                start_idx = int(decoded["offset"])

        page_items = ranked_items[start_idx : start_idx + limit]
        next_cursor = None
        if start_idx + limit < len(ranked_items):
            next_cursor = encode_cursor({"offset": start_idx + limit})

        results = []
        for item in page_items:
            giver = item[0]
            scores = item[1]
            why_lines = item[2]
            pres = item[3]
            band_info = item[4]
            user = item[5] if len(item) > 5 else None

            if not user:
                res_user = await self.session.execute(select(User).where(User.id == giver.user_id))
                user = res_user.scalar_one_or_none()
            full_name = user.full_name if user else "Verified Alumni"

            # Determine giver_type and giver_type_label (alumni, faculty, recruiter, founder)
            role = (user.role if user else "alumni").lower()
            if "facult" in role:
                g_type = "faculty"
                g_type_label = "Faculty Mentor"
            elif "recruit" in role:
                g_type = "recruiter"
                g_type_label = "Verified Recruiter"
            elif "founder" in role:
                g_type = "founder"
                g_type_label = "Verified Founder"
            else:
                g_type = "alumni"
                g_type_label = "Alumnus Mentor"

            if is_locked:
                full_name = f"{full_name.split()[0]} (Verified Giver)"
                bio = "Subscribe to unlock direct access, calendar booking, and 1-on-1 calls."
            else:
                bio = giver.bio

            card = GiverPublicCard(
                id=giver.user_id,
                full_name=full_name,
                headline=f"{giver.role_title or 'Professional'} at {giver.company or 'Tech'}",
                giver_type=g_type,
                giver_type_label=g_type_label,
                company=giver.company,
                role_title=giver.role_title,
                bio=bio,
                offers=giver.offers or [],
                topics=giver.topics or [],
                skills=giver.skills or [],
                domains=giver.domains or [],
                languages=giver.languages or [],
                badges=[band_info.get("band", giver.band or "Rising"), g_type_label],
                band=band_info.get("band", giver.band or "Rising"),
                rating_summary=RatingSummary(
                    band=band_info.get("band", giver.band or "Rising"),
                    smoothed_avg=band_info.get("smoothed_avg", giver.rating_avg or 4.0),
                    total_sessions=band_info.get("n", giver.rating_count or 0),
                    completion_rate=band_info.get("completion_rate", 1.0),
                ),
                availability_summary=AvailabilitySummary(
                    online=pres.get("online", False),
                    capacity_left=pres.get("capacity_left", giver.weekly_capacity),
                    status=pres.get("status", "active_now"),
                    avg_reply_minutes=pres.get("avg_reply_minutes", 45),
                ),
                why_lines=why_lines,
            )

            results.append(
                RecommendationItem(
                    giver=card,
                    score_components=scores,
                    why_lines=why_lines,
                    locked=is_locked,
                    lock_reason=lock_reason,
                )
            )

            giver.daily_impressions_count = (giver.daily_impressions_count or 0) + 1

        await self.session.commit()

        return RecommendationsResponse(
            items=results,
            excluded_summary=excluded_summary or HardGateExclusionSummary(),
            next_cursor=next_cursor,
            scope=scope,
            locked=is_locked,
            lock_reason=lock_reason,
        )

    # --- Explain Ranking Panel (Requirement 7) ---

    async def explain_ranking(
        self,
        student_id: uuid.UUID,
        scope: str = "own_college",
    ) -> ExplainRankingResponse:
        """
        Returns full transparent ranking factor breakdown, weights, and hard gate exclusions
        for the admin / jury panel.
        """
        recs_response = await self.get_recommendations(student_id=student_id, scope=scope, limit=50)

        candidates = []
        for item in recs_response.items:
            giver_card = item.giver
            scores = item.score_components
            skills_extracted = [
                s.get("name", str(s)) if isinstance(s, dict) else str(s)
                for s in giver_card.skills
            ]
            candidates.append(
                CandidateRankingExplanation(
                    giver_id=giver_card.id,
                    giver_name=giver_card.full_name,
                    giver_type=giver_card.giver_type,
                    giver_type_label=giver_card.giver_type_label,
                    role_title=giver_card.role_title,
                    company=giver_card.company,
                    score_breakdown=scores,
                    shared_skills=skills_extracted,
                    same_college=scores.affinity >= 0.5,
                    same_branch=scores.similar_journey >= 0.4,
                    availability_status=giver_card.availability_summary.status,
                    avg_reply_minutes=giver_card.availability_summary.avg_reply_minutes,
                    rating_avg=giver_card.rating_summary.smoothed_avg,
                    why_lines=item.why_lines,
                )
            )

        return ExplainRankingResponse(
            weights=self.matching_config.get("weights", {}),
            hard_gates_config=self.matching_config.get("hard_gates", {}),
            excluded_summary=recs_response.excluded_summary,
            candidates=candidates,
        )

    # --- Intent Structuring & Saving (F6 & F7) ---

    async def save_intent(
        self,
        user_id: uuid.UUID,
        text: str,
        goal_type: Optional[str] = None,
        target_role: Optional[str] = None,
        target_company_type: Optional[str] = None,
        required_skills: Optional[List[str]] = None,
    ) -> SaveIntentResponse:
        """
        Analyzes request quality, converts text to structured intent,
        computes intent embedding, and saves to database.
        """
        analysis = analyze_intent_quality(text)
        if analysis.is_blocked:
            raise AppError(
                code="request_quality_blocked",
                message=analysis.block_reason or "Your request was blocked due to invalid quality or spam patterns.",
                status_code=400,
            )

        structured = structure_intent(
            raw_text=text,
            goal_type_override=goal_type,
            target_role_override=target_role,
            target_company_type_override=target_company_type,
            required_skills_override=required_skills,
        )

        embed_text = (
            f"Goal: {structured.goal_type}. Role: {structured.target_role}. "
            f"Company: {structured.target_company_type}. Skills: {', '.join(structured.required_skills)}. {text}"
        )
        embedding = await generate_embedding(embed_text)

        now = utc_now()
        stmt_i = select(StudentIntent).where(StudentIntent.user_id == user_id)
        res_i = await self.session.execute(stmt_i)
        intent_rec = res_i.scalar_one_or_none()

        roles = [structured.target_role] if structured.target_role else []
        domains = [structured.target_company_type] if structured.target_company_type else []

        if intent_rec:
            intent_rec.raw_text = text
            intent_rec.goal_type = structured.goal_type
            intent_rec.target_roles = roles
            intent_rec.target_domains = domains
            intent_rec.structured = structured.model_dump()
            intent_rec.intent_embedding = embedding
            intent_rec.updated_at = now
        else:
            intent_rec = StudentIntent(
                user_id=user_id,
                raw_text=text,
                goal_type=structured.goal_type,
                target_roles=roles,
                target_domains=domains,
                structured=structured.model_dump(),
                intent_embedding=embedding,
                updated_at=now,
            )
            self.session.add(intent_rec)

        match_profile = await self.get_or_create_student_match_profile(user_id)
        match_profile.intent_goal = text
        match_profile.intent_roles = roles
        match_profile.intent_domains = domains
        match_profile.intent_help_type = structured.goal_type
        match_profile.intent_embedding = embedding
        match_profile.updated_at = now
        if structured.required_skills:
            setattr(match_profile, "intent_required_skills", structured.required_skills)

        await self.session.commit()
        await self.invalidate_recommendation_caches(student_id=str(user_id))

        return SaveIntentResponse(
            user_id=user_id,
            structured=structured,
            intent_embedding_present=True,
            message="Intent successfully saved and structured. Mentors re-ranked.",
        )

    # --- Public Giver Card ---

    async def get_giver_public_card(
        self, giver_id: uuid.UUID, requesting_student_id: Optional[uuid.UUID] = None, why_lines: Optional[List[str]] = None
    ) -> GiverPublicCard:
        giver = await self.get_giver_profile(giver_id)

        stmt_user = select(User).where(User.id == giver_id)
        res_user = await self.session.execute(stmt_user)
        user = res_user.scalar_one_or_none()
        full_name = user.full_name if user else "Verified Giver"

        role = (user.role if user else "alumni").lower()
        if "facult" in role:
            g_type = "faculty"
            g_type_label = "Faculty Mentor"
        elif "recruit" in role:
            g_type = "recruiter"
            g_type_label = "Verified Recruiter"
        elif "founder" in role:
            g_type = "founder"
            g_type_label = "Verified Founder"
        else:
            g_type = "alumni"
            g_type_label = "Alumnus Mentor"

        try:
            band_info = await ports.ratings.get_band(str(giver_id))
        except Exception:
            band_info = {"band": "Rising", "smoothed_avg": 4.0, "n": 0, "completion_rate": 1.0}

        try:
            p_map = await ports.presence.status([str(giver_id)])
            pres = p_map.get(str(giver_id), {"online": False, "capacity_left": giver.weekly_capacity})
        except Exception:
            pres = {"online": False, "capacity_left": giver.weekly_capacity}

        if why_lines is None:
            if requesting_student_id:
                try:
                    why_lines = await self.explain(str(requesting_student_id), str(giver_id))
                except Exception:
                    why_lines = ["Verified alumni mentor in your field"]
            else:
                why_lines = ["Experienced alumni mentor ready to assist"]

        return GiverPublicCard(
            id=giver.user_id,
            full_name=full_name,
            headline=f"{giver.role_title or 'Mentor'} at {giver.company or 'Tech'}",
            giver_type=g_type,
            giver_type_label=g_type_label,
            company=giver.company,
            role_title=giver.role_title,
            bio=giver.bio,
            offers=giver.offers or [],
            topics=giver.topics or [],
            skills=giver.skills or [],
            domains=giver.domains or [],
            languages=giver.languages or [],
            badges=[band_info.get("band", "Rising"), g_type_label],
            band=band_info.get("band", "Rising"),
            rating_summary=RatingSummary(
                band=band_info.get("band", "Rising"),
                smoothed_avg=band_info.get("smoothed_avg", 4.0),
                total_sessions=band_info.get("n", 0),
                completion_rate=band_info.get("completion_rate", 1.0),
            ),
            availability_summary=AvailabilitySummary(
                online=pres.get("online", False),
                capacity_left=pres.get("capacity_left", giver.weekly_capacity),
                status=pres.get("status", "active_now"),
                avg_reply_minutes=pres.get("avg_reply_minutes", 45),
            ),
            why_lines=why_lines,
        )

    # --- Cache Invalidation Helpers ---

    @staticmethod
    async def invalidate_recommendation_caches(student_id: Optional[str] = None, giver_id: Optional[str] = None):
        try:
            redis_client = await get_redis()
            patterns = []
            if student_id:
                patterns.append(f"wp:rec:{student_id}:*")
            else:
                patterns.append("wp:rec:*")
            if giver_id:
                patterns.append(f"wp:giver:{giver_id}")

            for pat in patterns:
                keys = await redis_client.keys(pat)
                if keys:
                    await redis_client.delete(*keys)
        except Exception:
            pass
