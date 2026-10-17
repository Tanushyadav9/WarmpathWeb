import uuid
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.errors import ModuleNotImplemented
from app.core.security import get_current_user_id
from app.modules.matching.schemas import RecommendationsResponse
from app.modules.matching.service import matching_service

router = APIRouter(tags=["matching"])

@router.get("/recommendations", response_model=RecommendationsResponse, summary="Get ranked mentor recommendations for student")
async def get_recommendations(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    student_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.get_recommendations(db, student_id)


@router.put("/me/giver-profile", summary="Update own giver mentorship profile and topics")
async def put_me_giver_profile():
    raise ModuleNotImplemented("/me/giver-profile")

@router.get("/me/giver-profile", summary="Retrieve own giver mentorship profile")
async def get_me_giver_profile():
    raise ModuleNotImplemented("/me/giver-profile")
