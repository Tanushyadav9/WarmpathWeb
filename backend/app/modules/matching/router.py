import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_token
from app.modules.matching.schemas import (
    CandidateRankingExplanation,
    ExplainRankingResponse,
    GiverProfileCreateUpdate,
    GiverProfileResponse,
    GiverPublicCard,
    IntentQualityCheckRequest,
    IntentQualityCheckResponse,
    RecommendationsResponse,
    SaveIntentRequest,
    SaveIntentResponse,
    StructuredIntentData,
)
from app.modules.matching.service import MatchingService
from app.modules.matching.intent import analyze_intent_quality, structure_intent

router = APIRouter(tags=["matching"])


async def get_current_user_id(request: Request) -> uuid.UUID:
    """Extracts authenticated user UUID from Authorization Bearer token or X-User-Id/X-User-ID."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
            return uuid.UUID(payload.get("sub"))
        except Exception:
            raise AppError(code="unauthorized", message="Invalid or expired token", status_code=401)

    x_user_id = request.headers.get("X-User-Id") or request.headers.get("X-User-ID")
    if x_user_id:
        try:
            return uuid.UUID(x_user_id)
        except ValueError:
            raise AppError(code="invalid_user_id", message="Invalid X-User-Id header", status_code=400)

    raise AppError(code="unauthorized", message="Authentication required", status_code=401)


async def get_optional_user_id(request: Request) -> Optional[uuid.UUID]:
    """Extracts optional authenticated user UUID if present."""
    try:
        return await get_current_user_id(request)
    except Exception:
        return None


# --- Giver Profile Endpoints ---

@router.put(
    "/me/giver-profile",
    summary="Create or update giver mentorship profile",
    response_model=GiverProfileResponse,
)
async def update_me_giver_profile(
    data: GiverProfileCreateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = await get_current_user_id(request)
    service = MatchingService(db)
    profile = await service.update_giver_profile(user_id, data)

    return GiverProfileResponse(
        user_id=profile.user_id,
        offers=profile.offers or [],
        topics=profile.topics or [],
        skills=profile.skills or [],
        domains=profile.domains or [],
        company=profile.company,
        role_title=profile.role_title,
        bio=profile.bio,
        languages=profile.languages or ["English"],
        weekly_capacity=profile.weekly_capacity,
        institution_id=profile.institution_id,
        department=profile.department,
        batch=profile.batch,
        societies=profile.societies or [],
        has_embedding=profile.embedding is not None,
        response_stats=profile.response_stats or {},
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "/me/giver-profile",
    summary="Retrieve own giver mentorship profile",
    response_model=GiverProfileResponse,
)
async def get_me_giver_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = await get_current_user_id(request)
    service = MatchingService(db)
    profile = await service.get_giver_profile(user_id)

    return GiverProfileResponse(
        user_id=profile.user_id,
        offers=profile.offers or [],
        topics=profile.topics or [],
        skills=profile.skills or [],
        domains=profile.domains or [],
        company=profile.company,
        role_title=profile.role_title,
        bio=profile.bio,
        languages=profile.languages or ["English"],
        weekly_capacity=profile.weekly_capacity,
        institution_id=profile.institution_id,
        department=profile.department,
        batch=profile.batch,
        societies=profile.societies or [],
        has_embedding=profile.embedding is not None,
        response_stats=profile.response_stats or {},
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# --- Intent & Request Quality Endpoints (F6 & F7) ---

@router.post(
    "/intent/quality-check",
    summary="Pre-flight analysis on student intent ask quality",
    response_model=IntentQualityCheckResponse,
)
@router.post("/api/v1/intent/quality-check", response_model=IntentQualityCheckResponse, include_in_schema=False)
async def quality_check_intent(req: IntentQualityCheckRequest):
    return analyze_intent_quality(req.text)


@router.post(
    "/intent/structure",
    summary="Convert unstructured ask to clean structured intent",
    response_model=StructuredIntentData,
)
@router.post("/api/v1/intent/structure", response_model=StructuredIntentData, include_in_schema=False)
async def structure_intent_endpoint(req: IntentQualityCheckRequest):
    return structure_intent(req.text)


@router.post(
    "/intent",
    summary="Save structured intent and update matching embedding",
    response_model=SaveIntentResponse,
)
@router.post("/api/v1/intent", response_model=SaveIntentResponse, include_in_schema=False)
@router.put("/intent", response_model=SaveIntentResponse, include_in_schema=False)
@router.put("/api/v1/intent", response_model=SaveIntentResponse, include_in_schema=False)
async def save_intent_endpoint(
    req: SaveIntentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = await get_current_user_id(request)
    service = MatchingService(db)
    return await service.save_intent(
        user_id=user_id,
        text=req.text,
        goal_type=req.goal_type,
        target_role=req.target_role,
        target_company_type=req.target_company_type,
        required_skills=req.required_skills,
    )


# --- Recommendations Endpoints (F8, F9, F10) ---

@router.get(
    "/recommendations",
    summary="Get ranked mentor recommendations for student",
    response_model=RecommendationsResponse,
)
@router.get("/api/v1/recommendations", response_model=RecommendationsResponse, include_in_schema=False)
async def get_recommendations(
    request: Request,
    scope: str = Query("own_college", pattern="^(own_college|cross_college|experts)$"),
    limit: int = Query(10, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    filter_domain: Optional[str] = Query(None),
    filter_help_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    student_id = await get_current_user_id(request)
    service = MatchingService(db)
    return await service.get_recommendations(
        student_id=student_id,
        scope=scope,
        limit=limit,
        cursor=cursor,
        filter_domain=filter_domain,
        filter_help_type=filter_help_type,
    )


@router.get(
    "/recommendations/explain-ranking",
    summary="Explain ranking engine factor breakdown for admin / jury panel",
    response_model=ExplainRankingResponse,
)
@router.get("/api/v1/recommendations/explain-ranking", response_model=ExplainRankingResponse, include_in_schema=False)
async def explain_ranking_endpoint(
    request: Request,
    scope: str = Query("own_college", pattern="^(own_college|cross_college|experts)$"),
    db: AsyncSession = Depends(get_db),
):
    student_id = await get_current_user_id(request)
    service = MatchingService(db)
    return await service.explain_ranking(student_id=student_id, scope=scope)


@router.get(
    "/givers/{id}",
    summary="View giver mentorship profile",
    response_model=GiverPublicCard,
)
@router.get("/api/v1/givers/{id}", response_model=GiverPublicCard, include_in_schema=False)
async def get_givers_id(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    requesting_student_id = await get_optional_user_id(request)
    service = MatchingService(db)
    return await service.get_giver_public_card(
        giver_id=id, requesting_student_id=requesting_student_id
    )
