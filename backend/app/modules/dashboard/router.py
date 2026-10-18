"""
backend/app/modules/dashboard/router.py - Role-Based Dashboard Views with RBAC Enforcement.
Ensures each role sees strictly the data relevant to their permission scope.
Unauthorized calls return HTTP 403 Forbidden.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.models import (
    Availability,
    Capacity,
    CreditWallet,
    GiverProfile,
    Institution,
    Opportunity,
    Rating,
    Report,
    Request,
    Resume,
    Session,
    Skill,
    StudentProfile,
    User,
    UserSkill,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# --- 1. Student Seeker Dashboard ---
@router.get("/student", summary="Student seeker dashboard")
async def get_student_dashboard(
    current_user: User = Depends(require_roles("student")),
    db: AsyncSession = Depends(get_db),
):
    # Student profile
    sp = (await db.execute(select(StudentProfile).where(StudentProfile.user_id == current_user.id))).scalar_one_or_none()
    
    # Institution
    inst = None
    if current_user.institution_id:
        inst = (await db.execute(select(Institution).where(Institution.id == current_user.institution_id))).scalar_one_or_none()

    # Wallet
    wallet = (await db.execute(select(CreditWallet).where(CreditWallet.user_id == current_user.id))).scalar_one_or_none()

    # Skills count
    skill_count_res = await db.execute(select(func.count(UserSkill.id)).where(UserSkill.user_id == current_user.id))
    skills_count = skill_count_res.scalar() or 0

    # Resume status
    resume = (await db.execute(select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()))).scalar_one_or_none()

    # Active requests
    req_stmt = (
        select(Request, User)
        .join(User, Request.giver_id == User.id)
        .where(Request.seeker_id == current_user.id)
        .order_by(Request.created_at.desc())
        .limit(5)
    )
    req_rows = (await db.execute(req_stmt)).all()

    # Recommended mentors (same college preferred)
    mentor_stmt = (
        select(User, GiverProfile)
        .join(GiverProfile, User.id == GiverProfile.user_id)
        .where(User.role.in_(["alumni", "faculty"]), User.institution_id == current_user.institution_id)
        .order_by(GiverProfile.rating_avg.desc())
        .limit(6)
    )
    mentors = (await db.execute(mentor_stmt)).all()

    # Upcoming opportunities
    opp_stmt = select(Opportunity).where(Opportunity.is_verified.is_(True)).order_by(Opportunity.created_at.desc()).limit(4)
    opps = (await db.execute(opp_stmt)).scalars().all()

    return {
        "view": "student_dashboard",
        "user": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "email": current_user.email,
            "role": current_user.role,
            "verification_level": current_user.verification_level,
            "trust_score": current_user.trust_score,
            "college": inst.name if inst else "Unknown Institution",
        },
        "profile": {
            "headline": sp.headline if sp else "Student",
            "target_role": sp.target_role if sp else "Software Engineer",
            "target_domain": sp.target_domain if sp else "Tech",
            "intent_ask": sp.intent_ask if sp else "Seeking general guidance",
            "skills_count": skills_count,
            "has_resume": resume is not None and resume.is_committed,
        },
        "wallet": {
            "balance": wallet.balance if wallet else 0,
            "escrow_held": wallet.escrow_held if wallet else 0,
        },
        "active_requests": [
            {
                "id": str(r.id),
                "giver_name": u.full_name,
                "status": r.status,
                "intent_category": r.intent_category,
                "ask_details": r.ask_details,
                "created_at": r.created_at.isoformat(),
            }
            for r, u in req_rows
        ],
        "recommended_mentors": [
            {
                "id": str(u.id),
                "full_name": u.full_name,
                "company": gp.company,
                "role_title": gp.role_title,
                "band": gp.band,
                "rating_avg": gp.rating_avg,
                "rating_count": gp.rating_count,
                "topics": gp.topics or [],
            }
            for u, gp in mentors
        ],
        "curated_opportunities": [
            {
                "id": str(o.id),
                "title": o.title,
                "company": o.company,
                "type": o.type,
                "location": o.location,
            }
            for o in opps
        ],
    }


# --- 2. Alumni Giver Dashboard ---
@router.get("/alumni", summary="Alumni mentor dashboard")
async def get_alumni_dashboard(
    current_user: User = Depends(require_roles("alumni", "faculty")),
    db: AsyncSession = Depends(get_db),
):
    gp = (await db.execute(select(GiverProfile).where(GiverProfile.user_id == current_user.id))).scalar_one_or_none()
    avail = (await db.execute(select(Availability).where(Availability.user_id == current_user.id))).scalar_one_or_none()
    cap = (await db.execute(select(Capacity).where(Capacity.user_id == current_user.id))).scalar_one_or_none()
    wallet = (await db.execute(select(CreditWallet).where(CreditWallet.user_id == current_user.id))).scalar_one_or_none()

    # Incoming pending requests
    pending_stmt = (
        select(Request, User)
        .join(User, Request.seeker_id == User.id)
        .where(Request.giver_id == current_user.id, Request.status == "pending")
        .order_by(Request.created_at.desc())
    )
    pending_rows = (await db.execute(pending_stmt)).all()

    # Upcoming sessions
    sess_stmt = (
        select(Session, User)
        .join(User, Session.seeker_id == User.id)
        .where(Session.giver_id == current_user.id, Session.status == "scheduled")
        .order_by(Session.scheduled_at.asc())
    )
    sess_rows = (await db.execute(sess_stmt)).all()

    # Recent ratings
    ratings_stmt = (
        select(Rating, User)
        .join(User, Rating.reviewer_id == User.id)
        .where(Rating.reviewee_id == current_user.id)
        .order_by(Rating.created_at.desc())
        .limit(5)
    )
    ratings_rows = (await db.execute(ratings_stmt)).all()

    return {
        "view": "alumni_dashboard",
        "user": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "role": current_user.role,
            "verification_level": current_user.verification_level,
            "trust_score": current_user.trust_score,
        },
        "stats": {
            "band": gp.band if gp else "rising",
            "rating_avg": gp.rating_avg if gp else 4.0,
            "rating_count": gp.rating_count if gp else 0,
            "completion_rate": gp.completion_rate if gp else 1.0,
            "weekly_capacity": cap.weekly_cap if cap else 2,
            "current_week_booked": cap.current_week_booked if cap else 0,
            "free_monthly_cap": cap.free_monthly_cap if cap else 4,
            "availability_status": avail.status if avail else "active_now",
            "avg_reply_minutes": avail.avg_reply_minutes if avail else 45,
            "response_rate": avail.response_rate if avail else 0.95,
        },
        "wallet": {
            "balance": wallet.balance if wallet else 0,
            "escrow_held": wallet.escrow_held if wallet else 0,
        },
        "incoming_requests": [
            {
                "id": str(r.id),
                "seeker_name": u.full_name,
                "intent_category": r.intent_category,
                "ask_details": r.ask_details,
                "is_cross_college": r.is_cross_college,
                "credits_locked": r.credits_locked,
                "created_at": r.created_at.isoformat(),
            }
            for r, u in pending_rows
        ],
        "upcoming_sessions": [
            {
                "id": str(s.id),
                "seeker_name": u.full_name,
                "scheduled_at": s.scheduled_at.isoformat(),
                "duration_minutes": s.duration_minutes,
                "meeting_link": s.meeting_link,
            }
            for s, u in sess_rows
        ],
        "recent_reviews": [
            {
                "id": str(r.id),
                "reviewer_name": u.full_name,
                "score": r.score,
                "tags": r.tags,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
            }
            for r, u in ratings_rows
        ],
    }


# --- 3. Faculty Dashboard ---
@router.get("/faculty", summary="Faculty mentor dashboard")
async def get_faculty_dashboard(
    current_user: User = Depends(require_roles("faculty")),
    db: AsyncSession = Depends(get_db),
):
    gp = (await db.execute(select(GiverProfile).where(GiverProfile.user_id == current_user.id))).scalar_one_or_none()
    inst = (await db.execute(select(Institution).where(Institution.id == current_user.institution_id))).scalar_one_or_none()
    wallet = (await db.execute(select(CreditWallet).where(CreditWallet.user_id == current_user.id))).scalar_one_or_none()

    # Completed academic consultations
    consult_count_res = await db.execute(
        select(func.count(Session.id)).where(Session.giver_id == current_user.id, Session.status == "completed")
    )
    consult_count = consult_count_res.scalar() or 0

    return {
        "view": "faculty_dashboard",
        "user": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "department": gp.domain if gp else "Computer Science",
            "institution": inst.name if inst else "University",
            "verification_level": current_user.verification_level,
            "verified_faculty_badge": True,
        },
        "academic_metrics": {
            "total_consultations_held": consult_count,
            "rating_avg": gp.rating_avg if gp else 4.8,
            "honorarium_credits": wallet.balance if wallet else 0,
            "office_hour_slots": ["Mon 15:00-17:00", "Thu 16:00-18:00"],
        },
        "guidance_areas": gp.topics if gp else ["Research Advising", "Thesis Review", "Higher Studies"],
    }


# --- 4. Recruiter Dashboard ---
@router.get("/recruiter", summary="Recruiter hiring dashboard")
async def get_recruiter_dashboard(
    current_user: User = Depends(require_roles("recruiter", "founder")),
    db: AsyncSession = Depends(get_db),
):
    gp = (await db.execute(select(GiverProfile).where(GiverProfile.user_id == current_user.id))).scalar_one_or_none()
    company_name = gp.company if gp else "Tech Corp"

    # Posted referrals/jobs
    opps = (
        await db.execute(
            select(Opportunity).where(Opportunity.creator_id == current_user.id).order_by(Opportunity.created_at.desc())
        )
    ).scalars().all()

    # Pre-matched candidate pool count
    candidate_count_res = await db.execute(select(func.count(StudentProfile.user_id)))
    candidate_count = candidate_count_res.scalar() or 0

    return {
        "view": "recruiter_dashboard",
        "user": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "company": company_name,
            "verification_level": current_user.verification_level,
            "verified_employer_badge": current_user.verification_level == "verified_employer",
        },
        "hiring_pipeline": {
            "active_postings_count": len(opps),
            "pre_matched_candidates_available": candidate_count,
            "hiring_chats_active": 3,
        },
        "posted_opportunities": [
            {
                "id": str(o.id),
                "title": o.title,
                "type": o.type,
                "location": o.location,
                "created_at": o.created_at.isoformat(),
            }
            for o in opps
        ],
    }


# --- 5. Founder Dashboard ---
@router.get("/founder", summary="Founder startup & hiring dashboard")
async def get_founder_dashboard(
    current_user: User = Depends(require_roles("founder")),
    db: AsyncSession = Depends(get_db),
):
    gp = (await db.execute(select(GiverProfile).where(GiverProfile.user_id == current_user.id))).scalar_one_or_none()
    company_name = gp.company if gp else "Startup"

    return {
        "view": "founder_dashboard",
        "user": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "startup": company_name,
            "verified_employer_badge": True,
            "trust_score": current_user.trust_score,
        },
        "founder_activities": {
            "office_hours_status": "Open for AMA and early founding engineer chats",
            "startup_talks_hosted": 2,
            "candidates_screened": 12,
            "open_referral_roles": ["Founding Full-Stack Engineer", "AI/ML Intern"],
        },
    }


# --- 6. Institution Admin Dashboard ---
@router.get("/admin", summary="Institution administration dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    # Total counts
    student_count = (await db.execute(select(func.count(User.id)).where(User.role == "student"))).scalar() or 0
    alumni_count = (await db.execute(select(func.count(User.id)).where(User.role == "alumni"))).scalar() or 0
    faculty_count = (await db.execute(select(func.count(User.id)).where(User.role == "faculty"))).scalar() or 0
    session_count = (await db.execute(select(func.count(Session.id)).where(Session.status == "completed"))).scalar() or 0
    request_total = (await db.execute(select(func.count(Request.id)))).scalar() or 1
    request_accepted = (await db.execute(select(func.count(Request.id)).where(Request.status.in_(["accepted", "completed"])))).scalar() or 0

    fulfillment_rate = round((request_accepted / request_total) * 100, 1)

    # Verification queue (pending users)
    pending_users = (
        await db.execute(
            select(User)
            .where(User.verification_level == "pending")
            .order_by(User.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    # Moderation reports queue
    pending_reports = (
        await db.execute(
            select(Report)
            .where(Report.status == "pending")
            .order_by(Report.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    return {
        "view": "admin_dashboard",
        "user": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "role": "admin",
            "institution": "Indraprastha Institute of Information Technology Delhi (IIITD)",
        },
        "kpis": {
            "total_students": student_count,
            "verified_alumni": alumni_count,
            "faculty_mentors": faculty_count,
            "completed_sessions": session_count,
            "fulfillment_rate_percent": fulfillment_rate,
            "median_reply_time_hours": 3.2,
        },
        "pilot_target_status": {
            "verified_givers_target": 50,
            "verified_givers_current": alumni_count + faculty_count,
            "fulfillment_target_rate": 60.0,
            "fulfillment_current_rate": fulfillment_rate,
            "closed_launch_gate_cleared": (alumni_count + faculty_count) >= 50 and fulfillment_rate >= 60.0,
        },
        "verification_queue": [
            {
                "id": str(u.id),
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "created_at": u.created_at.isoformat(),
            }
            for u in pending_users
        ],
        "moderation_reports": [
            {
                "id": str(r.id),
                "reason": r.reason,
                "description": r.description,
                "context_type": r.context_type,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in pending_reports
        ],
        "skill_gaps": [
            {"skill": "System Design", "student_demand": 42, "alumni_supply": 14, "gap_severity": "High"},
            {"skill": "MLOps / PyTorch", "student_demand": 38, "alumni_supply": 11, "gap_severity": "High"},
            {"skill": "Kubernetes", "student_demand": 26, "alumni_supply": 15, "gap_severity": "Medium"},
            {"skill": "Product Management", "student_demand": 19, "alumni_supply": 8, "gap_severity": "Medium"},
        ],
    }
