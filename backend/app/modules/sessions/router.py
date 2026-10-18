"""API Router for sessions, mentorship requests, in-app chat, and scheduling."""
import json
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, async_session_maker
from app.core.security import get_current_user_id
from app.modules.sessions.schemas import (
    ConfirmSlotInput,
    CreateRequestInput,
    DeclineRequestInput,
    MessageCreateInput,
    MessageResponse,
    NoShowReportInput,
    NotificationResponse,
    ProposeSlotsInput,
    RequestResponse,
)
from app.modules.sessions.service import sessions_service

router = APIRouter(tags=["sessions"])


# In-memory WebSocket connection manager for real-time chat updates
class ChatConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, request_id: str, websocket: WebSocket):
        await websocket.accept()
        if request_id not in self.active_connections:
            self.active_connections[request_id] = []
        self.active_connections[request_id].append(websocket)

    def disconnect(self, request_id: str, websocket: WebSocket):
        if request_id in self.active_connections:
            if websocket in self.active_connections[request_id]:
                self.active_connections[request_id].remove(websocket)
            if not self.active_connections[request_id]:
                del self.active_connections[request_id]

    async def broadcast(self, request_id: str, message: dict):
        if request_id in self.active_connections:
            for connection in self.active_connections[request_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


chat_manager = ChatConnectionManager()


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


@router.get("/requests/{id}", response_model=RequestResponse, summary="Get request details and agenda (role-based view)")
async def get_requests_id(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.get_request(db, req_id, viewer_id=viewer_id)


@router.post("/requests/{id}/accept", response_model=RequestResponse, summary="Accept a mentorship request")
async def post_requests_id_accept(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    giver_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.accept_request(db, giver_id, req_id)


@router.post("/requests/{id}/decline", response_model=RequestResponse, summary="Decline a mentorship request with a reason")
async def post_requests_id_decline(
    id: str,
    request: Request,
    body: Optional[DeclineRequestInput] = None,
    db: AsyncSession = Depends(get_db),
):
    giver_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    reason = body.reason if body else "Giver is currently unavailable"
    return await sessions_service.decline_request(db, giver_id, req_id, reason=reason)


@router.post("/requests/{id}/propose-slots", response_model=RequestResponse, summary="Giver proposes session slots")
async def post_requests_id_propose_slots(
    id: str,
    body: ProposeSlotsInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    giver_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.propose_slots(db, giver_id, req_id, body.slots)


@router.post("/requests/{id}/confirm-slot", response_model=RequestResponse, summary="Confirm session slot and generate meeting link")
async def post_requests_id_confirm_slot(
    id: str,
    body: ConfirmSlotInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.confirm_slot(db, user_id, req_id, body.slot)


@router.post("/sessions/{id}/complete", response_model=RequestResponse, summary="Mark session completed")
async def post_sessions_id_complete(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.complete_session(db, req_id, user_id=user_id)


@router.post("/requests/{id}/complete", response_model=RequestResponse, summary="Mark session completed (alias)")
async def post_requests_id_complete(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.complete_session(db, req_id, user_id=user_id)


@router.post("/sessions/{id}/no-show", response_model=RequestResponse, summary="Report no-show for a session")
async def post_sessions_id_no_show(
    id: str,
    body: NoShowReportInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.report_no_show(db, user_id, req_id, party=body.party, reason=body.reason)


@router.post("/requests/{id}/messages", response_model=MessageResponse, summary="Send in-app chat message with safety check")
async def post_requests_id_messages(
    id: str,
    body: MessageCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sender_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    msg = await sessions_service.send_message(db, sender_id, req_id, body.body)
    await chat_manager.broadcast(str(req_id), msg.model_dump())
    return msg


@router.get("/requests/{id}/messages", response_model=List[MessageResponse], summary="List in-app chat messages (polling)")
async def get_requests_id_messages(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    req_id = uuid.UUID(id)
    return await sessions_service.list_messages(db, user_id, req_id)


@router.websocket("/ws/requests/{id}/chat")
async def websocket_chat(
    websocket: WebSocket,
    id: str,
    user_id: Optional[str] = Query(None),
):
    await chat_manager.connect(id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                body_text = payload.get("body", "")
                sender_str = payload.get("sender_id") or user_id
                if body_text and sender_str:
                    async with async_session_maker() as db:
                        msg = await sessions_service.send_message(
                            db, uuid.UUID(sender_str), uuid.UUID(id), body_text
                        )
                        await chat_manager.broadcast(id, msg.model_dump())
            except Exception as e:
                await websocket.send_json({"error": str(e)})
    except WebSocketDisconnect:
        chat_manager.disconnect(id, websocket)


@router.get("/me/notifications", response_model=List[NotificationResponse], summary="Get session lifecycle notifications")
async def get_me_notifications(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await sessions_service.list_notifications(db, user_id)


@router.get("/me/sessions", response_model=List[RequestResponse], summary="List past and upcoming sessions")
async def get_me_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await sessions_service.list_requests(db, user_id)
