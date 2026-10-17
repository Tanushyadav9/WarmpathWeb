import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, UploadFile, Request, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.security import decode_token
from app.core.errors import AppError
from app.modules.resume.service import ResumeService
from app.modules.resume.schemas import (
    ConsentUpdateItem,
    UpdateConsentsRequest,
    ConsentsListResponse,
    ResumeUploadResponse,
    StudentProfileUpdateRequest,
    StudentProfileResponse,
    StudentIntentUpdateRequest,
    StudentIntentResponse,
    GitHubProofRequest,
    GitHubProofResponse,
    ProfileVisibilityUpdateRequest,
    WithdrawConsentRequest,
    DataExportResponse,
)

router = APIRouter(tags=["resume"])


async def get_current_user_id(request: Request) -> uuid.UUID:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = decode_token(token)
            return uuid.UUID(payload["sub"])
        except Exception:
            raise AppError(code="unauthorized", message="Invalid or expired token", status_code=401)

    x_user_id = request.headers.get("X-User-ID") or request.headers.get("X-User-Id")
    if x_user_id:
        try:
            return uuid.UUID(x_user_id)
        except Exception:
            raise AppError(code="invalid_user_id", message="Invalid X-User-ID header", status_code=400)

    # Default dev test user
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


# --- DPDP Consents Endpoints (F33) ---

@router.get("/me/consents", response_model=ConsentsListResponse, summary="Retrieve DPDP consent records")
@router.get("/api/v1/me/consents", response_model=ConsentsListResponse, include_in_schema=False)
@router.get("/api/v1/privacy/consent", response_model=ConsentsListResponse, include_in_schema=False)
async def get_consents(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.get_consents(user_id)


@router.put("/me/consents", response_model=ConsentsListResponse, summary="Update DPDP consent preferences")
@router.put("/api/v1/me/consents", response_model=ConsentsListResponse, include_in_schema=False)
@router.put("/api/v1/privacy/consent", response_model=ConsentsListResponse, include_in_schema=False)
async def update_consents(
    req: UpdateConsentsRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.update_consents(user_id, req.consents, req.text_version or "v1.0")


@router.post("/api/v1/privacy/withdraw-consent", response_model=ConsentsListResponse, summary="Withdraw a specific consent")
async def withdraw_consent(
    req: WithdrawConsentRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.update_consents(
        user_id,
        [ConsentUpdateItem(purpose=req.purpose, granted=False)],
    )


# --- Resume Upload and Profile Endpoints (F4) ---

@router.post("/resume", response_model=ResumeUploadResponse, status_code=status.HTTP_202_ACCEPTED, summary="Upload resume PDF/DOCX for AI extraction")
@router.post("/api/v1/resume", response_model=ResumeUploadResponse, status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    content = await file.read()
    service = ResumeService(session)
    resume_id = await service.process_resume_upload(user_id, content, file.filename or "resume.pdf")
    return ResumeUploadResponse(resume_id=resume_id, status="processing")


@router.get("/resume/profile", response_model=StudentProfileResponse, summary="Retrieve parsed and edited resume profile")
@router.get("/api/v1/resume/profile", response_model=StudentProfileResponse, include_in_schema=False)
@router.get("/api/v1/profile/student", response_model=StudentProfileResponse, include_in_schema=False)
async def get_resume_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.get_profile(user_id)


@router.put("/resume/profile", response_model=StudentProfileResponse, summary="Update student profile edits and re-embed")
@router.put("/api/v1/resume/profile", response_model=StudentProfileResponse, include_in_schema=False)
async def update_resume_profile(
    req: StudentProfileUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    updates = req.model_dump(exclude_unset=True)
    return await service.update_profile(user_id, updates)


@router.put("/resume/confirm", response_model=StudentProfileResponse, summary="Explicit student confirmation of extracted profile data")
@router.put("/api/v1/resume/confirm", response_model=StudentProfileResponse, include_in_schema=False)
async def confirm_resume_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.confirm_profile(user_id)


@router.delete("/resume", status_code=status.HTTP_204_NO_CONTENT, summary="Delete uploaded resume, parsed data and embeddings")
@router.delete("/api/v1/resume", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_resume(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    await service.delete_resume_data(user_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- GitHub Proof of Work Endpoints (F5) ---

@router.post("/api/v1/profile/github-proof", response_model=GitHubProofResponse, summary="Link GitHub profile as proof of work")
@router.post("/api/v1/me/github-proof", response_model=GitHubProofResponse, include_in_schema=False)
async def create_github_proof(
    req: GitHubProofRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    identifier = req.repo_url or req.username
    if not identifier:
        raise AppError(code="missing_github_input", message="Please provide a GitHub repo URL or username", status_code=400)
    service = ResumeService(session)
    return await service.add_or_update_github_proof(user_id, identifier)


@router.get("/api/v1/profile/github-proof", response_model=GitHubProofResponse, summary="Get verified GitHub proof of work")
@router.get("/api/v1/me/github-proof", response_model=GitHubProofResponse, include_in_schema=False)
async def get_github_proof(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.get_github_proof(user_id)


# --- Privacy, Profile Visibility & Account Deletion (F33) ---

@router.put("/api/v1/privacy/profile-visibility", summary="Update profile visibility settings")
async def update_profile_visibility(
    req: ProfileVisibilityUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.update_profile_visibility(user_id, hide_cgpa=req.hide_cgpa)


@router.get("/api/v1/privacy/export-data", response_model=DataExportResponse, summary="Export all personal data as JSON")
@router.get("/api/v1/me/export-data", response_model=DataExportResponse, include_in_schema=False)
async def export_data(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.export_user_data(user_id)


@router.delete("/api/v1/privacy/delete-account", status_code=status.HTTP_204_NO_CONTENT, summary="Permanent Right to be Forgotten account deletion")
@router.delete("/api/v1/me", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_account(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    await service.purge_all_user_data(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Intent Endpoints (F6) ---

@router.get("/me/intent", response_model=StudentIntentResponse, summary="Retrieve structured intent and goal")
@router.get("/api/v1/me/intent", response_model=StudentIntentResponse, include_in_schema=False)
async def get_intent(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.get_intent(user_id)


@router.put("/me/intent", response_model=StudentIntentResponse, summary="Save and structure 'what do you want next' intent")
@router.put("/api/v1/me/intent", response_model=StudentIntentResponse, include_in_schema=False)
async def update_intent(
    req: StudentIntentUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = ResumeService(session)
    return await service.update_intent(
        user_id=user_id,
        raw_text=req.text,
        goal_type=req.goal_type,
        target_roles=req.target_roles,
        target_domains=req.target_domains,
    )
