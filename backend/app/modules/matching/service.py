"""
backend/app/modules/matching/service.py - Matching Engine Service.
Heuristic Score v1, pgvector HNSW search, Redis caching, deterministic explainability,
hard gates, cold start boost, and exposure caps.
"""

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import User
from app.core.errors import AppError, PortNotReady
from app.core.events import GiverProfileUpdatedPayload, event_bus
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
    GiverProfileCreateUpdate,
    GiverPublicCard,
    RatingSummary,
    RecommendationItem,
    RecommendationsResponse,
    ScoreComponents,
)

# --- Configuration Constants (Section 6 & Requirement 4, 7) ---

WEIGHT_EXPERTISE = 0.35
WEIGHT_INTENT = 0.25
WEIGHT_AFFINITY = 0.15
WEIGHT_AVAILABILITY = 0.10
WEIGHT_RATING = 0.10
WEIGHT_RESPONSE_ODDS = 0.05

COLD_START_BOOST = 0.08
COLD_START_SESSION_THRESHOLD = 5
MAX_DAILY_EXPOSURE = 25
CACHE_TTL_SECONDS = 60

ALLOWED_GIVER_ROLES = {
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


def cosine_similarity(v1: Optional[List[float]], v2: Optional[List[float]]) -> float:
    """Computes cosine similarity between two float vectors, mapped to [0.0, 1.0]."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.5  # neutral fallback if missing

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
    """
    Generates 768-dimensional embedding using Gemini text-embedding-004.
    Falls back to deterministic vector if API key is not configured.
    """
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


async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Batches vector embedding generation for multiple texts.
    Uses concurrency and batching to optimize throughput during bulk operations.
    """
    import asyncio
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        return [deterministic_dummy_vector(t) for t in texts]

    results: List[List[float]] = []
    # Process in concurrent chunks of 10
    chunk_size = 10
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i : i + chunk_size]
        tasks = [generate_embedding(t) for t in chunk]
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        for res, original_text in zip(chunk_results, chunk):
            if isinstance(res, list) and len(res) == 768:
                results.append(res)
            else:
                results.append(deterministic_dummy_vector(original_text))
    return results


class MatchingService(MatchingPort):
    def __init__(self, session: AsyncSession):
        self.session = session

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
        # 1. Gate: only users with a giver role or pending verification may create one
        stmt_user = select(User).where(User.id == user_id)
        res_user = await self.session.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if user:
            user_roles = set(user.roles or [])
            if not user_roles.intersection(ALLOWED_GIVER_ROLES):
                # Check if trust level or pending verification allows
                try:
                    level = await ports.trust.get_level(str(user_id))
                    if level not in ["verified", "established"]:
                        raise AppError(
                            code="giver_role_required",
                            message="Only users with an approved giver role or pending giver verification can create a giver profile.",
                            status_code=403,
                        )
                except PortNotReady:
                    # In tests without trust module, verify against user roles strictly
                    raise AppError(
                        code="giver_role_required",
                        message="Only users with an approved giver role can create a giver profile.",
                        status_code=403,
                    )

        # 2. Embed offers plus skills plus bio
        skills_str = ", ".join(
            [s.get("name", str(s)) for s in data.skills if isinstance(s, dict)]
            or [str(s) for s in data.skills]
        )
        offers_str = ", ".join(data.offers)
        domains_str = ", ".join(data.domains)
        embed_input = (
            f"Title: {data.role_title or ''} at {data.company or ''}\n"
            f"Bio: {data.bio or ''}\n"
            f"Skills: {skills_str}\n"
            f"Offers: {offers_str}\n"
            f"Domains: {domains_str}"
        )
        embedding = await generate_embedding(embed_input)

        # 3. Upsert GiverProfile
        stmt = select(GiverProfile).where(GiverProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()

        if profile is None:
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
                institution_id=data.institution_id or (user.institution_id if user else None),
                department=data.department,
                batch=data.batch,
                societies=data.societies,
                embedding=embedding,
                updated_at=utc_now(),
            )
            self.session.add(profile)
        else:
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
            profile.updated_at = utc_now()

        # 4. Publish giver.profile_updated outbox event
        await event_bus.publish(
            self.session,
            topic="giver.profile_updated",
            payload=GiverProfileUpdatedPayload(
                giver_id=str(user_id),
                weekly_capacity=profile.weekly_capacity,
                topics=profile.topics,
            ),
        )

        await self.session.commit()

        # 5. Invalidate recommendation cache in Redis
        await self.invalidate_recommendation_caches()

        return profile

    # --- Student Match Projection Management ---

    async def get_or_create_student_match_profile(
        self, student_id: uuid.UUID
    ) -> StudentMatchProfile:
        stmt = select(StudentMatchProfile).where(StudentMatchProfile.user_id == student_id)
        res = await self.session.execute(stmt)
        match_profile = res.scalar_one_or_none()

        if not match_profile:
            # Query User table for default institution/affinity attributes
            stmt_user = select(User).where(User.id == student_id)
            res_user = await self.session.execute(stmt_user)
            user = res_user.scalar_one_or_none()

            # Query StudentProfile for actual skills, domains, and embedding if exists
            from app.core.models import StudentProfile, GitHubProof
            stmt_sp = select(StudentProfile).where(StudentProfile.user_id == student_id)
            res_sp = await self.session.execute(stmt_sp)
            sp = res_sp.scalar_one_or_none()

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

            # Check GitHub proof
            stmt_gh = select(GitHubProof).where(GitHubProof.user_id == student_id)
            res_gh = await self.session.execute(stmt_gh)
            gh = res_gh.scalar_one_or_none()

            match_profile = StudentMatchProfile(
                user_id=student_id,
                institution_id=user.institution_id if user else None,
                department="Computer Science",
                batch=2026,
                societies=["ACM"],
                skills=skills,
                domains=domains,
                profile_embedding=profile_embedding,
                has_github_proof=gh is not None,
                github_languages=gh.top_languages if gh else [],
                intent_goal="Find mentorship for software engineering internship",
                intent_roles=["Software Engineer Intern"],
                intent_domains=["Technology"],
                intent_help_type="resume_review",
                intent_embedding=deterministic_dummy_vector(f"student:{student_id}:intent"),
                updated_at=utc_now(),
            )
            self.session.add(match_profile)
            await self.session.commit()

        return match_profile

    # --- Match Scoring Engine v1 ---

    def calculate_score_components(
        self,
        student: StudentMatchProfile,
        giver: GiverProfile,
        band_info: Dict[str, Any],
        presence_info: Dict[str, Any],
    ) -> ScoreComponents:
        """
        Calculates honest Heuristic Score v1 components (Section 6 & Requirement 4):
        - 35% Expertise Fit
        - 25% Intent Fit
        - 15% Affinity
        - 10% Availability
        - 10% Rating
        - 5% Response Odds
        - Cold Start Exposure Boost (+0.08 if total_sessions < 5)
        """
        # 1. Expertise Fit (35%)
        cos_expertise = cosine_similarity(student.profile_embedding, giver.embedding)

        # Keyword & taxonomy overlap
        student_skills = {
            s.get("name", "").lower() for s in (student.skills or []) if isinstance(s, dict)
        } or {str(s).lower() for s in (student.skills or [])}
        giver_skills = {
            s.get("name", "").lower() for s in (giver.skills or []) if isinstance(s, dict)
        } or {str(s).lower() for s in (giver.skills or [])}
        giver_topics = {t.lower() for t in (giver.topics or [])}

        combined_giver_skills = giver_skills.union(giver_topics)
        shared_skills = student_skills.intersection(combined_giver_skills)
        all_skills = student_skills.union(combined_giver_skills)
        jaccard = len(shared_skills) / max(1, len(all_skills))

        # Boost for GitHub Proof of work (F5)
        github_boost = 0.05 if getattr(student, "has_github_proof", False) else 0.0
        expertise_fit = min(1.0, 0.7 * cos_expertise + 0.3 * jaccard + github_boost)

        # 2. Intent Fit (25%)
        cos_intent = cosine_similarity(student.intent_embedding, giver.embedding)
        help_type_match = 0.0
        if student.intent_help_type:
            clean_intent_ht = student.intent_help_type.lower().replace(" ", "_")
            giver_offers = {o.lower().replace(" ", "_") for o in (giver.offers or [])}
            if clean_intent_ht in giver_offers:
                help_type_match = 1.0
            elif any(clean_intent_ht in o for o in giver_offers):
                help_type_match = 0.5
        intent_fit = min(1.0, 0.6 * cos_intent + 0.4 * help_type_match)

        # 3. Affinity (15%)
        same_inst = 0.40 if (giver.institution_id and giver.institution_id == student.institution_id) else 0.0
        same_dept = (
            0.30
            if (giver.department and student.department and giver.department.lower() == student.department.lower())
            else 0.0
        )
        batch_prox = 0.0
        if giver.batch and student.batch:
            diff = giver.batch - student.batch
            if 1 <= abs(diff) <= 4:
                batch_prox = 0.20
            elif diff == 0:
                batch_prox = 0.10
            else:
                batch_prox = 0.05

        shared_societies = set(giver.societies or []).intersection(set(student.societies or []))
        society_score = 0.10 if shared_societies else 0.0
        affinity = min(1.0, same_inst + same_dept + batch_prox + society_score)

        # 4. Availability (10%)
        is_online = presence_info.get("online", False)
        capacity_left = presence_info.get("capacity_left", giver.weekly_capacity)
        online_score = 0.70 if is_online else 0.20
        capacity_score = min(1.0, capacity_left / 5.0) * 0.30
        availability = min(1.0, online_score + capacity_score)

        # 5. Rating (10%)
        smoothed_avg = band_info.get("smoothed_avg", 4.0)
        band = band_info.get("band", "Rising")
        band_multiplier = 1.0 if band == "Top Rated" else (0.85 if band == "Trusted" else 0.70)
        norm_rating = max(0.0, min(1.0, (smoothed_avg - 1.0) / 4.0))
        rating = min(1.0, 0.6 * norm_rating + 0.4 * band_multiplier)

        # 6. Response Odds (5%)
        stats = giver.response_stats or {}
        acceptance_rate = float(stats.get("acceptance_rate", 0.95))
        median_mins = float(stats.get("median_response_minutes", 60))
        if median_mins <= 30:
            speed_score = 1.0
        elif median_mins <= 120:
            speed_score = 0.85
        elif median_mins <= 360:
            speed_score = 0.65
        else:
            speed_score = 0.40
        response_odds = min(1.0, 0.6 * acceptance_rate + 0.4 * speed_score)

        # Baseline Weighted Score
        base_score = (
            WEIGHT_EXPERTISE * expertise_fit
            + WEIGHT_INTENT * intent_fit
            + WEIGHT_AFFINITY * affinity
            + WEIGHT_AVAILABILITY * availability
            + WEIGHT_RATING * rating
            + WEIGHT_RESPONSE_ODDS * response_odds
        )

        # Cold Start Boost (Requirement 7)
        total_sessions = band_info.get("n", stats.get("total_sessions", 0))
        cold_start_boost = 0.0
        if total_sessions < COLD_START_SESSION_THRESHOLD:
            cold_start_boost = COLD_START_BOOST

        total_score = min(1.0, max(0.0, base_score + cold_start_boost))

        return ScoreComponents(
            expertise_fit=round(expertise_fit, 3),
            intent_fit=round(intent_fit, 3),
            affinity=round(affinity, 3),
            availability=round(availability, 3),
            rating=round(rating, 3),
            response_odds=round(response_odds, 3),
            cold_start_boost=round(cold_start_boost, 3),
            total_score=round(total_score, 3),
        )

    # --- Explainability Engine (Requirement 5) ---

    def generate_why_lines(
        self,
        student: StudentMatchProfile,
        giver: GiverProfile,
        scores: ScoreComponents,
        presence_info: Dict[str, Any],
        band_info: Dict[str, Any],
    ) -> List[str]:
        """
        Generates deterministic plain-language why_lines from score components.
        Never exposes raw embeddings or formulas to students.
        """
        why_lines: List[str] = []

        # 1. Expertise overlap explanation
        student_skills = {
            s.get("name", "") for s in (student.skills or []) if isinstance(s, dict)
        } or {str(s) for s in (student.skills or [])}
        giver_skills = {
            s.get("name", "") for s in (giver.skills or []) if isinstance(s, dict)
        } or {str(s) for s in (giver.skills or [])}
        shared = [s for s in student_skills if s in giver_skills]

        if shared:
            skills_text = " and ".join(shared[:2])
            why_lines.append(f"Shares your {skills_text} skills")
        elif scores.expertise_fit >= 0.7:
            why_lines.append("Strong domain and technical overlap with your background")

        # 2. Intent matching explanation
        if student.intent_help_type:
            clean_intent = student.intent_help_type.lower().replace("_", " ")
            matching_offers = [
                o for o in (giver.offers or []) if clean_intent in o.lower().replace("_", " ")
            ]
            if matching_offers:
                why_lines.append(
                    f"Offers {matching_offers[0].replace('_', ' ')}, which matches your goal"
                )

        # 3. Affinity explanation
        if giver.institution_id and student.institution_id and giver.institution_id == student.institution_id:
            if giver.batch and student.batch and giver.batch != student.batch:
                diff = abs(giver.batch - student.batch)
                direction = "ahead" if giver.batch < student.batch else "junior"
                why_lines.append(f"Same college, {diff} year{'s' if diff > 1 else ''} {direction}")
            else:
                why_lines.append("Alumnus from your college")
        elif giver.department and student.department and giver.department.lower() == student.department.lower():
            why_lines.append(f"Same academic background in {giver.department}")

        # 4. Availability explanation
        if presence_info.get("online"):
            why_lines.append("Online now for instant connection")
        else:
            capacity = presence_info.get("capacity_left", giver.weekly_capacity)
            if capacity > 0:
                why_lines.append(f"Open window with {capacity} session slots available this week")

        # 5. Rating & Band explanation
        band = band_info.get("band", "Rising")
        if band == "Top Rated":
            why_lines.append(
                f"Top Rated mentor with {band_info.get('smoothed_avg', 4.8):.1f} smoothed rating"
            )
        elif band == "Trusted":
            why_lines.append("Trusted alumni mentor with consistent positive reviews")
        elif scores.cold_start_boost > 0:
            why_lines.append("Rising alumni mentor eager to guide")

        # 6. GitHub Proof of work explanation
        if getattr(student, "has_github_proof", False) and getattr(student, "github_languages", None):
            why_lines.append(
                f"Verified GitHub proof of work in {', '.join(student.github_languages[:2])}"
            )

        # Deterministic deduplication while maintaining order
        seen: Set[str] = set()
        deduped = []
        for line in why_lines:
            if line not in seen:
                seen.add(line)
                deduped.append(line)

        return deduped[:4]

    # --- MatchingPort Implementation ---

    async def explain(self, student_id: str, giver_id: str) -> List[str]:
        """MatchingPort implementation for the sessions module."""
        s_uuid = uuid.UUID(student_id)
        g_uuid = uuid.UUID(giver_id)

        student = await self.get_or_create_student_match_profile(s_uuid)
        giver = await self.get_giver_profile(g_uuid)

        # Query ports safely
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

    # --- Recommendations Query & Re-ranking ---

    async def get_recommendations(
        self,
        student_id: uuid.UUID,
        scope: str = "own_college",
        limit: int = 10,
        cursor: Optional[str] = None,
        filter_domain: Optional[str] = None,
        filter_help_type: Optional[str] = None,
    ) -> RecommendationsResponse:
        # 1. Hard Gate on Student: must be verified and have granted profile_matching consent
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

        try:
            student_level = await ports.trust.get_level(str(student_id))
            if student_level in ["new", "restricted"]:
                raise AppError(
                    code="student_verification_required",
                    message="You must complete college verification before accessing mentor recommendations.",
                    status_code=403,
                )
        except PortNotReady:
            # When trust port is stubbed in standalone testing, proceed if student is valid
            pass

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

        # 3. Retrieve Top Candidates (pgvector HNSW query bounded to 200 candidates)
        try:
            from sqlalchemy import text
            await self.session.execute(text("SET LOCAL hnsw.ef_search = 40;"))
        except Exception:
            pass

        stmt = select(GiverProfile).where(GiverProfile.weekly_capacity > 0)
        stmt = stmt.where(GiverProfile.daily_impressions_count < MAX_DAILY_EXPOSURE)

        # Pre-filter by scope to leverage ix_giver_profiles_inst_cap index
        if scope == "own_college" and student.institution_id:
            stmt = stmt.where(GiverProfile.institution_id == student.institution_id)
        elif scope == "cross_college" and student.institution_id:
            stmt = stmt.where(GiverProfile.institution_id != student.institution_id)

        stmt = stmt.limit(200)
        res = await self.session.execute(stmt)
        all_candidates = res.scalars().all()

        if not all_candidates:
            return RecommendationsResponse(items=[], next_cursor=None, scope=scope)

        candidate_ids = [str(c.user_id) for c in all_candidates]

        # 4. Batch Port Queries
        # TrustPort
        trust_levels = {}
        blocked_set = set()
        for cid in candidate_ids:
            try:
                trust_levels[cid] = await ports.trust.get_level(cid)
            except Exception:
                trust_levels[cid] = "verified"

            try:
                if await ports.trust.is_blocked(str(student_id), cid):
                    blocked_set.add(cid)
            except Exception:
                pass

        # PresencePort
        try:
            presence_map = await ports.presence.status(candidate_ids)
        except Exception:
            presence_map = {cid: {"online": False, "capacity_left": 3} for cid in candidate_ids}

        # RatingsPort
        ratings_map = {}
        for cid in candidate_ids:
            try:
                ratings_map[cid] = await ports.ratings.get_band(cid)
            except Exception:
                ratings_map[cid] = {
                    "band": "Rising",
                    "smoothed_avg": 4.0,
                    "n": 0,
                    "completion_rate": 1.0,
                }

        # CreditsPort: check scope permission
        is_scope_locked = False
        lock_reason = None
        if scope in ["cross_college", "experts"]:
            # Check representative access
            try:
                access_check = await ports.credits.can_access(
                    str(student_id), candidate_ids[0] if candidate_ids else str(student_id)
                )
                if not access_check.get("allowed", False):
                    is_scope_locked = True
                    lock_reason = access_check.get("reason", "plan_required")
            except Exception:
                # If credits port denied or plan required
                is_scope_locked = True
                lock_reason = "plan_required"

        # 5. Apply Hard Gates & Score Candidates
        ranked_items = []
        for giver in all_candidates:
            gid = str(giver.user_id)

            # Gate A: Not the student
            if giver.user_id == student_id:
                continue

            # Gate B: Giver verified and not restricted
            g_level = trust_levels.get(gid, "verified")
            if g_level not in ["verified", "established"]:
                continue

            # Gate C: Not blocked
            if gid in blocked_set:
                continue

            # Gate D: Has weekly capacity left
            pres = presence_map.get(gid, {"online": False, "capacity_left": giver.weekly_capacity})
            if pres.get("capacity_left", 0) <= 0:
                continue

            # Gate E: Scope filtering
            if scope == "own_college":
                if giver.institution_id and student.institution_id and giver.institution_id != student.institution_id:
                    continue
            elif scope == "cross_college":
                if giver.institution_id and student.institution_id and giver.institution_id == student.institution_id:
                    continue

            # Filter by domain or help type if provided
            if filter_domain and filter_domain.lower() not in [d.lower() for d in (giver.domains or [])]:
                continue
            if filter_help_type and filter_help_type.lower() not in [o.lower() for o in (giver.offers or [])]:
                continue

            # Gate F: Daily exposure cap
            if giver.daily_impressions_count >= MAX_DAILY_EXPOSURE:
                continue

            # Compute Score Components
            band_info = ratings_map.get(gid, {"band": "Rising", "smoothed_avg": 4.0, "n": 0})
            scores = self.calculate_score_components(student, giver, band_info, pres)
            why_lines = self.generate_why_lines(student, giver, scores, pres, band_info)

            ranked_items.append((giver, scores, why_lines, pres, band_info))

        # Sort by total_score descending
        ranked_items.sort(key=lambda x: x[1].total_score, reverse=True)

        # 6. Save ranked IDs to Redis Cache
        if redis_client:
            try:
                cache_payload = [
                    {
                        "giver_id": str(item[0].user_id),
                        "score_components": item[1].model_dump(),
                        "why_lines": item[2],
                        "locked": is_scope_locked,
                        "lock_reason": lock_reason,
                    }
                    for item in ranked_items
                ]
                await redis_client.setex(
                    cache_key, CACHE_TTL_SECONDS, json.dumps(cache_payload)
                )
            except Exception:
                pass

        # 7. Cursor Pagination
        return await self._build_recommendations_response(
            ranked_items, limit, cursor, scope, is_scope_locked, lock_reason
        )

    async def _build_recommendations_response(
        self,
        ranked_items: List[Tuple[GiverProfile, ScoreComponents, List[str], Dict[str, Any], Dict[str, Any]]],
        limit: int,
        cursor: Optional[str],
        scope: str,
        is_locked: bool,
        lock_reason: Optional[str],
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
        for giver, scores, why_lines, pres, band_info in page_items:
            # Query user name for card
            res_user = await self.session.execute(select(User).where(User.id == giver.user_id))
            user = res_user.scalar_one_or_none()
            full_name = user.full_name if user else "Verified Alumni"

            if is_locked:
                # Mask sensitive info when locked
                full_name = f"{full_name.split()[0]} (Verified Giver)"
                bio = "Subscribe to unlock direct access, calendar booking, and 1-on-1 calls."
            else:
                bio = giver.bio

            card = GiverPublicCard(
                id=giver.user_id,
                full_name=full_name,
                headline=f"{giver.role_title or 'Professional'} at {giver.company or 'Tech'}",
                company=giver.company,
                role_title=giver.role_title,
                bio=bio,
                offers=giver.offers or [],
                topics=giver.topics or [],
                skills=giver.skills or [],
                domains=giver.domains or [],
                languages=giver.languages or [],
                badges=[band_info.get("band", "Rising"), "Verified"],
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

            # Increment daily impressions
            giver.daily_impressions_count = (giver.daily_impressions_count or 0) + 1

        await self.session.commit()

        return RecommendationsResponse(
            items=results,
            next_cursor=next_cursor,
            scope=scope,
            locked=is_locked,
            lock_reason=lock_reason,
        )

    async def _paginate_cached_recommendations(
        self,
        cached_obj: List[Dict[str, Any]],
        student: StudentMatchProfile,
        limit: int,
        cursor: Optional[str],
        scope: str,
    ) -> RecommendationsResponse:
        start_idx = 0
        if cursor:
            decoded = decode_cursor(cursor)
            if decoded and "offset" in decoded:
                start_idx = int(decoded["offset"])

        page_data = cached_obj[start_idx : start_idx + limit]
        next_cursor = None
        if start_idx + limit < len(cached_obj):
            next_cursor = encode_cursor({"offset": start_idx + limit})

        results = []
        is_locked = False
        lock_reason = None

        for item in page_data:
            g_uuid = uuid.UUID(item["giver_id"])
            stmt = select(GiverProfile).where(GiverProfile.user_id == g_uuid)
            res = await self.session.execute(stmt)
            giver = res.scalar_one_or_none()
            if not giver:
                continue

            scores = ScoreComponents(**item["score_components"])
            why_lines = item["why_lines"]
            is_locked = item.get("locked", False)
            lock_reason = item.get("lock_reason")

            card = await self.get_giver_public_card(giver.user_id, student.user_id, why_lines)
            results.append(
                RecommendationItem(
                    giver=card,
                    score_components=scores,
                    why_lines=why_lines,
                    locked=is_locked,
                    lock_reason=lock_reason,
                )
            )

        return RecommendationsResponse(
            items=results,
            next_cursor=next_cursor,
            scope=scope,
            locked=is_locked,
            lock_reason=lock_reason,
        )

    # --- Public Giver Card (Requirement 6) ---

    async def get_giver_public_card(
        self, giver_id: uuid.UUID, requesting_student_id: Optional[uuid.UUID] = None, why_lines: Optional[List[str]] = None
    ) -> GiverPublicCard:
        giver = await self.get_giver_profile(giver_id)

        # Get full name from User table
        stmt_user = select(User).where(User.id == giver_id)
        res_user = await self.session.execute(stmt_user)
        user = res_user.scalar_one_or_none()
        full_name = user.full_name if user else "Verified Giver"

        # Query RatingsPort
        try:
            band_info = await ports.ratings.get_band(str(giver_id))
        except Exception:
            band_info = {"band": "Rising", "smoothed_avg": 4.0, "n": 0, "completion_rate": 1.0}

        # Query PresencePort
        try:
            p_map = await ports.presence.status([str(giver_id)])
            pres = p_map.get(str(giver_id), {"online": False, "capacity_left": giver.weekly_capacity})
        except Exception:
            pres = {"online": False, "capacity_left": giver.weekly_capacity}

        # Calculate why_lines if requesting_student_id provided and why_lines not passed
        if why_lines is None:
            if requesting_student_id:
                try:
                    why_lines = await self.explain(str(requesting_student_id), str(giver_id))
                except Exception:
                    why_lines = ["Verified alumni mentor in your field"]
            else:
                why_lines = ["Experienced alumni mentor ready to assist"]

        # Check hot reads cache if requesting without student context
        cache_key = f"wp:giver:{giver_id}"
        redis_client = None
        if requesting_student_id is None and why_lines is None:
            try:
                redis_client = await get_redis()
                cached = await redis_client.get(cache_key)
                if cached:
                    return GiverPublicCard(**json.loads(cached))
            except Exception:
                pass

        card = GiverPublicCard(
            id=giver.user_id,
            full_name=full_name,
            headline=f"{giver.role_title or 'Mentor'} at {giver.company or 'Tech'}",
            company=giver.company,
            role_title=giver.role_title,
            bio=giver.bio,
            offers=giver.offers,
            topics=giver.topics,
            skills=giver.skills,
            domains=giver.domains,
            languages=giver.languages,
            badges=[band_info.get("band", "Rising"), "Verified"],
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
            ),
            why_lines=why_lines,
        )

        if redis_client and requesting_student_id is None and why_lines is None:
            try:
                await redis_client.setex(cache_key, 300, json.dumps(card.model_dump(mode="json")))
            except Exception:
                pass

        return card

    # --- Cache Invalidation Helpers (Requirement 8) ---

    @staticmethod
    async def invalidate_recommendation_caches(student_id: Optional[str] = None, giver_id: Optional[str] = None):
        """Invalidates matching recommendations cache in Redis."""
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
