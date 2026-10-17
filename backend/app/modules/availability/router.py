"""API Router for availability."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.ports import ports
from app.core.security import get_current_user_id
from app.modules.availability.schemas import (
    AvailabilityResponse,
    AvailabilityUpdateRequest,
    PresenceResponse,
    PresenceStatusItem,
)
from app.modules.availability.service import availability_service

router = APIRouter(tags=["availability"])


@router.put("/me/availability", response_model=AvailabilityResponse, summary="Set weekly schedule and session capacity limit")
async def put_me_availability(
    req: AvailabilityUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await availability_service.update_availability(db, user_id, req)


@router.get("/me/availability", response_model=AvailabilityResponse, summary="Retrieve current availability schedule")
async def get_me_availability(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await availability_service.get_availability_details(db, user_id)


@router.post("/me/online", response_model=AvailabilityResponse, summary="Open 30-minute instant connect window")
async def post_me_online(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await availability_service.set_online(db, user_id)


@router.delete("/me/online", response_model=AvailabilityResponse, summary="Close instant connect window")
async def delete_me_online(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await availability_service.set_offline(db, user_id)


@router.get("/presence", summary="Check online and capacity status for givers")
async def get_presence(
    user_ids: Optional[str] = Query(None, description="Comma-separated user IDs"),
):
    ids: List[str] = []
    if user_ids:
        ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    status_map = await ports.presence.status(ids)
    return {"users": status_map}


@router.websocket("/ws")
async def ws_ws(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "Presence WebSocket active"})
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "data": data})
    except Exception:
        await websocket.close()
