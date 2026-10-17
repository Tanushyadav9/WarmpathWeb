import uuid
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.errors import ModuleNotImplemented
from app.core.security import get_current_user_id
from app.modules.trust.schemas import TrustScoreResponse
from app.modules.trust.service import trust_service

router = APIRouter(tags=["trust"])

@router.post("/reports", summary="Submit a report against a user, message, or session")
async def post_reports():
    raise ModuleNotImplemented("/reports")

@router.post("/blocks", summary="Block a user from contacting or booking")
async def post_blocks():
    raise ModuleNotImplemented("/blocks")

@router.delete("/blocks/{user_id}", summary="Unblock a previously blocked user")
async def delete_blocks_user_id():
    raise ModuleNotImplemented("/blocks/{user_id}")

@router.get("/me/trust", response_model=TrustScoreResponse, summary="Retrieve current private trust score and safety limits")
async def get_me_trust(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(get_current_user_id(request))
    details = await trust_service.get_trust_details(db, user_id)
    return TrustScoreResponse(**details)


@router.get("/admin/moderation/queue", summary="List pending moderation reports")
async def get_admin_moderation_queue():
    raise ModuleNotImplemented("/admin/moderation/queue")

@router.post("/admin/moderation/{id}/resolve", summary="Resolve a moderation report")
async def post_admin_moderation_id_resolve():
    raise ModuleNotImplemented("/admin/moderation/{id}/resolve")

@router.get("/admin/verification/queue", summary="List pending verification submissions")
async def get_admin_verification_queue():
    raise ModuleNotImplemented("/admin/verification/queue")

@router.post("/admin/verification/{id}/decide", summary="Approve or reject a verification request")
async def post_admin_verification_id_decide():
    raise ModuleNotImplemented("/admin/verification/{id}/decide")

@router.post("/admin/approved-members/upload", summary="Upload institutional roster CSV")
async def post_admin_approved_members_upload():
    raise ModuleNotImplemented("/admin/approved-members/upload")

@router.get("/admin/audit-log", summary="Retrieve security audit trail")
async def get_admin_audit_log():
    raise ModuleNotImplemented("/admin/audit-log")
