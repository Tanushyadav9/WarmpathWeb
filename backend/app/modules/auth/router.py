"""
backend/app/modules/auth/router.py - Authentication, Registration, and User Profile.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.models import (
    CreditWallet,
    Institution,
    StudentProfile,
    GiverProfile,
    Availability,
    Capacity,
    User,
)
from app.core.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


# --- Schemas ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    role: str = Field(default="student")  # student, alumni, faculty, recruiter, founder, admin
    institution_id: Optional[int] = None
    headline: Optional[str] = None
    company: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    target_role: Optional[str] = None
    target_domain: Optional[str] = None
    consent_flags: Optional[Dict[str, Any]] = None


# --- Endpoints ---

@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with role and institution."""
    # Check if user already exists
    stmt = select(User).where(User.email == payload.email.lower().strip())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Validate role
    valid_roles = ["student", "alumni", "faculty", "recruiter", "founder", "admin"]
    role = payload.role.lower().strip()
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {valid_roles}",
        )

    # Initial verification level
    if role == "student":
        ver_level = "verified_alumnus" if payload.institution_id else "pending"
    elif role in ["alumni", "faculty"]:
        ver_level = "pending"
    elif role in ["recruiter", "founder"]:
        ver_level = "pending"
    else:
        ver_level = "trusted"

    # Create user
    user = User(
        id=uuid.uuid4(),
        email=payload.email.lower().strip(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=role,
        roles=[role],
        institution_id=payload.institution_id,
        verification_level=ver_level,
        trust_score=60.0 if role == "student" else 50.0,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Create default associated profiles
    if role == "student":
        profile = StudentProfile(
            user_id=user.id,
            headline=payload.headline or "Student",
            target_role="Software Engineer",
            intent_ask="General career mentorship",
        )
        db.add(profile)
    elif role in ["alumni", "faculty", "founder", "recruiter"]:
        giver = GiverProfile(
            user_id=user.id,
            headline=payload.headline or f"{role.capitalize()} at {payload.company or 'Tech'}",
            company=payload.company or "Tech",
            role_title=payload.headline or "Professional",
            weekly_capacity=2,
            band="rising",
            rating_avg=4.0,
        )
        avail = Availability(user_id=user.id, status="active_now")
        cap = Capacity(user_id=user.id, weekly_cap=2, free_monthly_cap=4)
        db.add_all([giver, avail, cap])

    # Create wallet with initial credits
    wallet = CreditWallet(
        user_id=user.id,
        balance=3 if role == "student" else 0,
        escrow_held=0,
    )
    db.add(wallet)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        str(user.id),
        claims={"role": user.role, "email": user.email, "name": user.full_name},
    )

    return AuthResponse(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "roles": user.roles,
            "institution_id": user.institution_id,
            "verification_level": user.verification_level,
            "trust_score": user.trust_score,
        },
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password."""
    stmt = select(User).where(User.email == payload.email.lower().strip())
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or deactivated",
        )

    token = create_access_token(
        str(user.id),
        claims={"role": user.role, "email": user.email, "name": user.full_name},
    )

    return AuthResponse(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "roles": user.roles,
            "institution_id": user.institution_id,
            "verification_level": user.verification_level,
            "trust_score": user.trust_score,
        },
    )


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full profile of current authenticated user."""
    # Fetch institution details
    institution_data = None
    if current_user.institution_id:
        inst = (await db.execute(select(Institution).where(Institution.id == current_user.institution_id))).scalar_one_or_none()
        if inst:
            institution_data = {
                "id": inst.id,
                "name": inst.name,
                "short_name": inst.short_name,
                "city": inst.city,
            }

    # Fetch wallet
    wallet = (await db.execute(select(CreditWallet).where(CreditWallet.user_id == current_user.id))).scalar_one_or_none()

    profile_data = {}
    if current_user.role == "student":
        sp = (await db.execute(select(StudentProfile).where(StudentProfile.user_id == current_user.id))).scalar_one_or_none()
        if sp:
            profile_data = {
                "headline": sp.headline,
                "bio": sp.bio,
                "batch": sp.batch,
                "department": sp.department,
                "target_role": sp.target_role,
                "target_domain": sp.target_domain,
                "intent_ask": sp.intent_ask,
            }
    elif current_user.role in ["alumni", "faculty", "recruiter", "founder"]:
        gp = (await db.execute(select(GiverProfile).where(GiverProfile.user_id == current_user.id))).scalar_one_or_none()
        if gp:
            profile_data = {
                "headline": gp.headline,
                "bio": gp.bio,
                "company": gp.company,
                "role_title": gp.role_title,
                "domain": gp.domain,
                "band": gp.band,
                "rating_avg": gp.rating_avg,
                "rating_count": gp.rating_count,
                "weekly_capacity": gp.weekly_capacity,
            }

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "roles": current_user.roles,
        "institution": institution_data,
        "verification_level": current_user.verification_level,
        "trust_score": current_user.trust_score,
        "consent_flags": current_user.consent_flags,
        "wallet": {
            "balance": wallet.balance if wallet else 0,
            "escrow_held": wallet.escrow_held if wallet else 0,
        },
        "profile": profile_data,
    }


@router.patch("/me")
async def patch_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update personal profile fields and consent flags."""
    if payload.full_name:
        current_user.full_name = payload.full_name
    if payload.consent_flags:
        current_user.consent_flags = {**current_user.consent_flags, **payload.consent_flags}

    if current_user.role == "student":
        sp = (await db.execute(select(StudentProfile).where(StudentProfile.user_id == current_user.id))).scalar_one_or_none()
        if sp:
            if payload.headline:
                sp.headline = payload.headline
            if payload.bio:
                sp.bio = payload.bio
            if payload.target_role:
                sp.target_role = payload.target_role
            if payload.target_domain:
                sp.target_domain = payload.target_domain
    elif current_user.role in ["alumni", "faculty", "recruiter", "founder"]:
        gp = (await db.execute(select(GiverProfile).where(GiverProfile.user_id == current_user.id))).scalar_one_or_none()
        if gp:
            if payload.headline:
                gp.headline = payload.headline
            if payload.bio:
                gp.bio = payload.bio
            if payload.company:
                gp.company = payload.company

    await db.commit()
    return {"status": "success", "message": "Profile updated successfully"}


@router.get("/institutions")
async def list_institutions(db: AsyncSession = Depends(get_db)):
    """List all supported institutions for registration and discovery."""
    stmt = select(Institution).order_by(Institution.name)
    institutions = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": inst.id,
            "name": inst.name,
            "short_name": inst.short_name,
            "city": inst.city,
            "email_domains": inst.email_domains,
        }
        for inst in institutions
    ]
