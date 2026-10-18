"""API Router for authentication, secure login, OTPs, CSRF token, and DPDP Act rights."""
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.core.security_middleware import generate_csrf_token
from app.modules.auth.schemas import (
    ConsentResponse,
    ConsentUpdateInput,
    DataExportResponse,
    OTPRequestInput,
    OTPVerifyInput,
    TokenResponse,
    UserLoginInput,
    UserRegisterInput,
    UserResponse,
)
from app.modules.auth.service import auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=Dict[str, Any], summary="Register user with Argon2 password hashing and DPDP consent")
async def post_auth_register(
    req: UserRegisterInput,
    db: AsyncSession = Depends(get_db),
):
    user, tokens = await auth_service.register_user(db, req)
    return {
        "user": user.model_dump(),
        "tokens": tokens.model_dump(),
        "message": "User registered successfully",
    }


@router.post("/auth/login", response_model=Dict[str, Any], summary="Login with email and password via Argon2 verification")
async def post_auth_login(
    req: UserLoginInput,
    db: AsyncSession = Depends(get_db),
):
    user, tokens = await auth_service.authenticate_user(db, req)
    return {
        "user": user.model_dump(),
        "tokens": tokens.model_dump(),
        "message": "Login successful",
    }


@router.post("/auth/request-otp", summary="Request one-time password for email")
async def post_auth_request_otp(
    req: OTPRequestInput,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.request_otp(db, req)


@router.post("/auth/verify-otp", response_model=TokenResponse, summary="Verify one-time password and receive session tokens")
async def post_auth_verify_otp(
    req: OTPVerifyInput,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.verify_otp(db, req)


@router.get("/auth/csrf-token", summary="Generate HMAC signed CSRF token for state-changing requests")
async def get_csrf_token(request: Request):
    user_id = get_current_user_id(request)
    csrf_tok = generate_csrf_token(user_id)
    return {"csrf_token": csrf_tok, "header_name": "X-CSRF-Token"}


@router.get("/me", response_model=UserResponse, summary="Retrieve current authenticated user profile")
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await auth_service.get_user_profile(db, user_id)


@router.get("/me/consents", response_model=ConsentResponse, summary="Retrieve DPDP consent records")
async def get_me_consents(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await auth_service.update_consents(
        db, user_id, ConsentUpdateInput(terms_of_service=True, privacy_policy=True, data_processing=True)
    )


@router.put("/me/consents", response_model=ConsentResponse, summary="Update DPDP consent preferences")
async def put_me_consents(
    req: ConsentUpdateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await auth_service.update_consents(db, user_id, req)


@router.get("/me/data-export", response_model=DataExportResponse, summary="Download personal data export under DPDP Act / GDPR")
async def get_me_data_export(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await auth_service.export_user_data(db, user_id)


@router.delete("/me", summary="Request account and data deletion under DPDP Act")
async def delete_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await auth_service.delete_user_account(db, user_id)
