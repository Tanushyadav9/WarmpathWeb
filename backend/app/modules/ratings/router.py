import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import ModuleNotImplemented
from app.core.security import get_current_user_id
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
from app.modules.ratings.service import ratings_service

router = APIRouter(tags=["ratings"])


@router.post("/sessions/{id}/rating", response_model=RatingResponse, summary="Student rates session quality (1-5 + feedback)")
async def post_sessions_id_rating(
    id: str,
    req: RatingCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = uuid.UUID(id)
    rater_id = uuid.UUID(get_current_user_id(request))
    return await ratings_service.submit_rating(db, session_id, rater_id, req)


@router.get("/givers/{id}/rating-summary", response_model=GiverPublicRatingSummaryResponse, summary="Get student-facing public rating summary for giver")
async def get_givers_id_rating_summary(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    giver_id = uuid.UUID(id)
    return await ratings_service.get_public_summary(db, giver_id)


@router.get("/me/band", response_model=GiverBandResponse, summary="Get current giver rating band (Rising, Trusted, Top Rated)")
async def get_me_band(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    band_info = await ratings_service.get_band_info(db, user_id)
    return GiverBandResponse(**band_info)


@router.post("/sessions/{id}/vouch", response_model=VouchResponse, summary="Giver vouches for student after high-rated session")
async def post_sessions_id_vouch(
    id: str,
    req: VouchCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = uuid.UUID(id)
    giver_id = uuid.UUID(get_current_user_id(request))
    return await ratings_service.create_vouch(db, session_id, giver_id, req)


@router.get("/students/{id}/vouches", response_model=List[VouchResponse], summary="List all endorsements and vouches for a student")
async def get_students_id_vouches(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    student_id = uuid.UUID(id)
    return await ratings_service.get_student_vouches(db, student_id)


@router.get("/leaderboard", response_model=List[LeaderboardEntryResponse], summary="Top Giver leaderboard per institution and month")
async def get_leaderboard(
    college: Optional[str] = Query(None, description="Filter by college / institution name"),
    month: Optional[str] = Query(None, description="Filter by month in YYYY-MM format"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await ratings_service.get_leaderboard(db, college=college, month=month, limit=limit)


@router.get("/admin/ratings/reviews", response_model=List[RatingResponse], summary="Admin queue for flagged ratings")
async def get_admin_ratings_reviews(
    status: str = Query("pending", description="Filter review status ('pending', 'approved', 'rejected')"),
    db: AsyncSession = Depends(get_db),
):
    return await ratings_service.list_reviews(db, status=status)


@router.post("/admin/ratings/{id}/resolve", response_model=RatingResponse, summary="Admin resolves a flagged rating")
async def post_admin_ratings_id_resolve(
    id: str,
    req: RatingReviewResolveInput,
    db: AsyncSession = Depends(get_db),
):
    rating_id = uuid.UUID(id)
    return await ratings_service.resolve_review(db, rating_id, req)


@router.post("/sessions/{id}/request-quality", summary="Giver rates student preparation and request clarity")
async def post_sessions_id_request_quality():
    raise ModuleNotImplemented("/sessions/{id}/request-quality")


@router.post("/sessions/{id}/dispute", summary="Open dispute for abusive or low-effort session")
async def post_sessions_id_dispute():
    raise ModuleNotImplemented("/sessions/{id}/dispute")


@router.get("/admin/disputes", summary="List pending session disputes")
async def get_admin_disputes():
    raise ModuleNotImplemented("/admin/disputes")


@router.post("/admin/disputes/{id}/resolve", summary="Resolve a session dispute")
async def post_admin_disputes_id_resolve():
    raise ModuleNotImplemented("/admin/disputes/{id}/resolve")
