"""
backend/app/modules/demo/router.py - Demo Mode Sandbox, Persona Switcher & Database Reset.
Active in DEMO_MODE for jury evaluations and testing.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.models import User
from app.core.security import create_access_token
import sys
from pathlib import Path

# Ensure repo root is in sys.path for scripts import
curr = Path(__file__).resolve()
repo_root = curr.parents[4] if len(curr.parents) >= 5 else Path.cwd()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.seed_all import run_seed

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


class LoginAsRequest(BaseModel):
    role: str  # student, alumni, faculty, recruiter, founder, admin


DEMO_PERSONAS = [
    {
        "role": "student",
        "email": "aarav.sharma@iiitd.ac.in",
        "name": "Aarav Sharma",
        "title": "3rd Year B.Tech CSE (Seeker)",
        "organization": "IIIT Delhi",
        "avatar_badge": "Student Seeker",
        "description": "Uploads resume, sets target domain, discovers mentors, books sessions.",
    },
    {
        "role": "alumni",
        "email": "vikram.malhotra@alumni.iiitd.ac.in",
        "name": "Vikram Malhotra",
        "title": "Staff Software Engineer (Top Rated Giver)",
        "organization": "Google",
        "avatar_badge": "Top Rated Alumnus",
        "description": "Sets weekly capacity, accepts mentorship requests, holds 1:1 sessions.",
    },
    {
        "role": "faculty",
        "email": "dr.pankaj@iiitd.ac.in",
        "name": "Dr. Pankaj Jalote",
        "title": "Distinguished Professor (Domain Mentor)",
        "organization": "IIIT Delhi",
        "avatar_badge": "Verified Faculty",
        "description": "Academic research advisor, thesis reviewer, office hours consultations.",
    },
    {
        "role": "recruiter",
        "email": "priya.recruiter@razorpay.com",
        "name": "Priya Menon",
        "title": "Tech Recruiting Lead (Giver of Opportunities)",
        "organization": "Razorpay",
        "avatar_badge": "Verified Employer",
        "description": "Posts verified job referrals, candidate talent pipeline, hiring chats.",
    },
    {
        "role": "founder",
        "email": "kunal.founder@postman.com",
        "name": "Kunal Shah",
        "title": "Co-Founder & CTO (Giver of Opportunities)",
        "organization": "Postman",
        "avatar_badge": "Verified Founder",
        "description": "Hosts startup AMA office hours, pre-screened candidate discovery.",
    },
    {
        "role": "admin",
        "email": "admin@iiitd.ac.in",
        "name": "Dean Alumni Affairs",
        "title": "Institution Network Administrator",
        "organization": "IIIT Delhi",
        "avatar_badge": "Admin",
        "description": "Oversees verification queue, dispute reports, fulfillment rates, skill gaps.",
    },
]


@router.get("/personas", summary="List available demo personas for 1-click switcher")
async def get_personas():
    return {
        "demo_mode": True,
        "default_password": "demo1234",
        "personas": DEMO_PERSONAS,
    }


@router.post("/login-as", summary="Instant 1-click login as demo persona")
async def login_as(payload: LoginAsRequest, db: AsyncSession = Depends(get_db)):
    role = payload.role.lower().strip()
    persona_info = next((p for p in DEMO_PERSONAS if p["role"] == role), None)
    if not persona_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid demo persona role: {role}",
        )

    # Find the persona in DB
    stmt = select(User).where(User.email == persona_info["email"])
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        # Fallback to any user with that role
        stmt_fallback = select(User).where(User.role == role).limit(1)
        user = (await db.execute(stmt_fallback)).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona for role '{role}' not found in database. Run reset first.",
        )

    token = create_access_token(
        str(user.id),
        claims={"role": user.role, "email": user.email, "name": user.full_name},
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "roles": user.roles,
            "institution_id": user.institution_id,
            "verification_level": user.verification_level,
            "trust_score": user.trust_score,
        },
    }


@router.post("/reset", summary="Reset database to clean benchmark seed state")
async def reset_database(db: AsyncSession = Depends(get_db)):
    await run_seed(db)
    return {
        "status": "success",
        "message": "Demo database successfully reset to clean benchmark state with 60 students, 50 alumni, 6 faculty, 5 recruiters, and 5 founders.",
    }
