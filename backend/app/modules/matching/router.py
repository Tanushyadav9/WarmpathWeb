import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import get_current_user_id
from app.modules.matching.schemas import (
    RecommendationsResponse,
    FacultyProfileInput,
    FacultyProfileResponse,
    EmployerProfileInput,
    EmployerProfileResponse,
    OpportunityCreateInput,
    OpportunityItemResponse,
    OpportunitiesFeedResponse,
    StudentProfileInput,
    StudentProfileResponse,
    OpportunityInterestInput,
    OpportunityInterestResponse,
    CandidateProfileResponse,
)
from app.modules.matching.service import matching_service

router = APIRouter(tags=["matching"])


# --- Giver Recommendations & Matching ---

@router.get("/recommendations", response_model=RecommendationsResponse, summary="Get ranked mentor recommendations for student")
async def get_recommendations(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    student_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.get_recommendations(db, student_id)


@router.put("/me/giver-profile", summary="Update own giver mentorship profile and topics")
async def put_me_giver_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    prof = await matching_service.get_or_create_profile(db, user_id)
    return {"message": "Profile updated", "id": str(prof.id)}


@router.get("/me/giver-profile", summary="Retrieve own giver mentorship profile")
async def get_me_giver_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    prof = await matching_service.get_or_create_profile(db, user_id)
    return {
        "id": str(prof.id),
        "user_id": str(prof.user_id),
        "full_name": prof.full_name,
        "headline": prof.headline,
        "college": prof.college,
        "skills": prof.skills,
        "is_verified": prof.is_verified,
    }


# --- 1. Faculty Domain Mentor Endpoints ---

@router.post("/faculty/profile", response_model=FacultyProfileResponse, summary="Create or update faculty domain mentor profile")
@router.put("/faculty/profile", response_model=FacultyProfileResponse, summary="Update faculty domain mentor profile")
async def post_faculty_profile(
    req: FacultyProfileInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.create_or_update_faculty_profile(db, user_id, req)


@router.get("/faculty/profile", response_model=Optional[FacultyProfileResponse], summary="Retrieve current faculty profile")
async def get_faculty_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    prof = await matching_service.get_faculty_profile(db, user_id)
    if not prof:
        raise AppError(code="faculty_not_found", message="Faculty profile not found", status_code=404)
    return prof


@router.get("/faculty/{id}", response_model=FacultyProfileResponse, summary="Retrieve public faculty domain mentor profile")
async def get_faculty_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    fac_user_id = uuid.UUID(id)
    prof = await matching_service.get_faculty_profile(db, fac_user_id)
    if not prof:
        raise AppError(code="faculty_not_found", message="Faculty profile not found", status_code=404)
    return prof


@router.get("/faculty", response_model=List[FacultyProfileResponse], summary="List and search faculty domain mentors")
async def list_faculty(
    department: Optional[str] = Query(None, description="Filter by academic department"),
    expertise: Optional[str] = Query(None, description="Filter by domain expertise"),
    db: AsyncSession = Depends(get_db),
):
    return await matching_service.list_faculty(db, department=department, expertise=expertise)


# --- 2. Recruiter & Founder Employer Profiles ---

@router.post("/recruiters/profile", response_model=EmployerProfileResponse, summary="Create or update employer profile")
@router.put("/recruiters/profile", response_model=EmployerProfileResponse, summary="Update employer profile")
async def post_employer_profile(
    req: EmployerProfileInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.create_or_update_employer_profile(db, user_id, req)


@router.get("/recruiters/profile", response_model=EmployerProfileResponse, summary="Retrieve current employer profile")
async def get_employer_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    prof = await matching_service.get_employer_profile(db, user_id)
    if not prof:
        raise AppError(code="employer_not_found", message="Employer profile not found", status_code=404)
    return prof


@router.post("/recruiters/verify", response_model=EmployerProfileResponse, summary="Verify recruiter business credentials")
async def post_verify_employer(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.verify_employer(db, user_id)


# --- 3. Opportunity Posting & Feed ---

@router.post("/opportunities", response_model=OpportunityItemResponse, summary="Post an opportunity (verified employers only)")
async def post_opportunity(
    req: OpportunityCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    creator_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.create_opportunity(db, creator_id, req)


@router.get("/opportunities", response_model=OpportunitiesFeedResponse, summary="Feed of jobs, hackathons, talks, and meetups")
@router.get("/opportunities/feed", response_model=OpportunitiesFeedResponse, summary="Ranked opportunities feed")
async def get_opportunities_feed(
    request: Request,
    skills: Optional[List[str]] = Query(None, description="Optional skills list to rank by"),
    city: Optional[str] = Query(None, description="Optional city filter"),
    opportunity_type: Optional[str] = Query(None, description="Filter by type (job, hackathon, meetup, etc.)"),
    college: Optional[str] = Query(None, description="Student's institution for linked alumni count"),
    db: AsyncSession = Depends(get_db),
):
    student_id = None
    try:
        student_id = uuid.UUID(get_current_user_id(request))
    except Exception:
        pass

    return await matching_service.get_opportunities_feed(
        db,
        student_id=student_id,
        skills=skills,
        city=city,
        opportunity_type=opportunity_type,
        college=college,
    )


# --- 4. Student Opt-In & Candidate Views ---

@router.post("/students/profile", response_model=StudentProfileResponse, summary="Update student confirmed skills and proof of work")
async def post_student_profile(
    req: StudentProfileInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.create_or_update_student_profile(db, user_id, req)


@router.post("/opportunities/{id}/express-interest", response_model=OpportunityInterestResponse, summary="Student expresses interest / opts in")
async def post_express_interest(
    id: str,
    req: OpportunityInterestInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    opportunity_id = uuid.UUID(id)
    student_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.express_interest(db, opportunity_id, student_id, req)


@router.get("/opportunities/{id}/candidates", response_model=List[CandidateProfileResponse], summary="Recruiter views opted-in interested candidates")
async def get_opportunity_candidates(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    opportunity_id = uuid.UUID(id)
    requester_id = uuid.UUID(get_current_user_id(request))
    return await matching_service.get_opportunity_candidates(db, opportunity_id, requester_id)
