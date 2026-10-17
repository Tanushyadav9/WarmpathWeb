import uuid
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.errors import ModuleNotImplemented
from app.core.security import get_current_user_id
from app.modules.ratings.schemas import RatingCreateInput, RatingResponse
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


@router.post("/sessions/{id}/request-quality", summary="Giver rates student preparation and request clarity")
async def post_sessions_id_request_quality():
    raise ModuleNotImplemented("/sessions/{id}/request-quality")

@router.post("/sessions/{id}/dispute", summary="Open dispute for abusive or low-effort session")
async def post_sessions_id_dispute():
    raise ModuleNotImplemented("/sessions/{id}/dispute")

@router.get("/givers/{id}/rating-summary", summary="Get public rating aggregate for giver")
async def get_givers_id_rating_summary():
    raise ModuleNotImplemented("/givers/{id}/rating-summary")

@router.get("/me/band", summary="Get current rating band (Rising, Trusted, Top Rated)")
async def get_me_band():
    raise ModuleNotImplemented("/me/band")

@router.get("/admin/disputes", summary="List pending session disputes")
async def get_admin_disputes():
    raise ModuleNotImplemented("/admin/disputes")

@router.post("/admin/disputes/{id}/resolve", summary="Resolve a session dispute")
async def post_admin_disputes_id_resolve():
    raise ModuleNotImplemented("/admin/disputes/{id}/resolve")
