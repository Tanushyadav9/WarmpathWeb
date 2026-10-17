"""API Router for sessions and mentorship requests."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.modules.sessions.schemas import CreateRequestInput, RequestResponse
from app.modules.sessions.service import sessions_service

router = APIRouter(tags=["sessions"])


@router.post("/requests", response_model=RequestResponse, summary="Submit mentorship request to a giver")
async def post_requests(
    req: CreateRequestInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    student_id = uuid.UUID(get_current_user_id(request))
    return await sessions_service.create_request(db, student_id, req)


@router.get("/requests", response_model=List[RequestResponse], summary="List incoming or outgoing mentorship requests")
async def get_requests(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await sessions_service.list_requests(db, user_id)


@router.get("/requests/{id}", response_model=RequestResponse, summary="Get request details and agenda")
async def get_requests_id(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    req_id = uuid.UUID(id)
    return await sessions_service.get_request(db, req_id)


@router.post("/requests/{id}/accept", response_model=RequestResponse, summary="Accept a mentorship request")
async def post_requests_id_accept(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    giver_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.accept_request(db, giver_id, req_id)


@router.post("/requests/{id}/decline", response_model=RequestResponse, summary="Decline a mentorship request")
async def post_requests_id_decline(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    giver_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.decline_request(db, giver_id, req_id)


@router.get("/me/sessions", response_model=List[RequestResponse], summary="List past and upcoming sessions")
async def get_me_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await sessions_service.list_requests(db, user_id)
