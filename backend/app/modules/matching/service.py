"""Business logic service for matching, recommendations, faculty mentors, employers, and opportunities."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.ports import ports
from app.modules.matching.models import (
    GiverProfile,
    FacultyProfile,
    EmployerProfile,
    Opportunity,
    StudentProfile,
    OpportunityInterest,
)
from app.modules.matching.schemas import (
    GiverRecommendationItem,
    RecommendationsResponse,
    FacultyProfileInput,
    FacultyProfileResponse,
    EmployerProfileInput,
    EmployerProfileResponse,
    OpportunityCreateInput,
    LinkedAlumnus,
    OpportunityItemResponse,
    OpportunitiesFeedResponse,
    StudentProfileInput,
    StudentProfileResponse,
    OpportunityInterestInput,
    OpportunityInterestResponse,
    CandidateProfileResponse,
)
from app.modules.ratings.models import Vouch


class MatchingService:
    # --- Giver Recommendations (Existing) ---

    async def get_or_create_profile(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        full_name: str = "Alex Mercer",
        headline: str = "Senior Engineer at CloudCorp",
        college: str = "VIPS-TC",
        skills: str = "Python, FastAPI, Architecture",
    ) -> GiverProfile:
        result = await db.execute(
            select(GiverProfile).where(GiverProfile.user_id == user_id)
        )
        prof = result.scalar_one_or_none()
        if not prof:
            prof = GiverProfile(
                user_id=user_id,
                full_name=full_name,
                headline=headline,
                college=college,
                skills=skills,
                is_verified=True,
            )
            db.add(prof)
            await db.commit()
            await db.refresh(prof)
        return prof

    async def get_recommendations(
        self, db: AsyncSession, student_id: uuid.UUID
    ) -> RecommendationsResponse:
        result = await db.execute(select(GiverProfile))
        profiles = result.scalars().all()

        if not profiles:
            return RecommendationsResponse(items=[])

        user_ids = [str(p.user_id) for p in profiles]

        try:
            presence_map = await ports.presence.status(user_ids)
        except Exception:
            presence_map = {}

        items: List[GiverRecommendationItem] = []
        for prof in profiles:
            uid_str = str(prof.user_id)
            pres = presence_map.get(uid_str, {})

            status = pres.get("status", "inactive")
            capacity_reached = pres.get("capacity_reached", False)
            capacity_left = pres.get("capacity_left", 0)

            # Rule: Giver disappears from matching if capacity is reached, status is inactive, or giver is unverified/suspended
            if not prof.is_verified or capacity_reached or status == "inactive":
                continue

            skills_list = [s.strip() for s in (prof.skills or "").split(",") if s.strip()]

            items.append(
                GiverRecommendationItem(
                    giver_id=uid_str,
                    full_name=prof.full_name,
                    headline=prof.headline or "Alumni Mentor",
                    college=prof.college or "Same College",
                    skills=skills_list,
                    status=status,
                    status_color=pres.get("status_color", "#15803D"),
                    status_label=pres.get("status_label", "Active now"),
                    today_window=pres.get("today_window"),
                    response_rate=pres.get("response_rate", 100.0),
                    avg_reply_time_display=pres.get("avg_reply_time_display", "N/A"),
                    capacity_left=capacity_left,
                    why_matched=f"Verified alumni • {pres.get('status_label', 'Available')}",
                )
            )

        return RecommendationsResponse(items=items)

    # --- 1. Faculty Domain Mentor Profile ---

    async def create_or_update_faculty_profile(
        self, db: AsyncSession, user_id: uuid.UUID, req: FacultyProfileInput
    ) -> FacultyProfileResponse:
        result = await db.execute(
            select(FacultyProfile).where(FacultyProfile.user_id == user_id)
        )
        fac = result.scalar_one_or_none()
        if not fac:
            fac = FacultyProfile(
                user_id=user_id,
                full_name=req.full_name,
                department=req.department,
                institution=req.institution,
                expertise=req.expertise or [],
                bio=req.bio,
                rate_credits=req.rate_credits,
                is_verified=True,
                verified_expert_badge=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(fac)
        else:
            fac.full_name = req.full_name
            fac.department = req.department
            fac.institution = req.institution
            fac.expertise = req.expertise or []
            fac.bio = req.bio
            fac.rate_credits = req.rate_credits
            fac.verified_expert_badge = True

        await db.commit()
        await db.refresh(fac)

        return FacultyProfileResponse(
            id=str(fac.id),
            user_id=str(fac.user_id),
            full_name=fac.full_name,
            department=fac.department,
            institution=fac.institution,
            expertise=fac.expertise or [],
            bio=fac.bio,
            rate_credits=fac.rate_credits,
            is_verified=fac.is_verified,
            verified_expert_badge=fac.verified_expert_badge,
            created_at=fac.created_at.isoformat(),
        )

    async def get_faculty_profile(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Optional[FacultyProfileResponse]:
        result = await db.execute(
            select(FacultyProfile).where(FacultyProfile.user_id == user_id)
        )
        fac = result.scalar_one_or_none()
        if not fac:
            return None
        return FacultyProfileResponse(
            id=str(fac.id),
            user_id=str(fac.user_id),
            full_name=fac.full_name,
            department=fac.department,
            institution=fac.institution,
            expertise=fac.expertise or [],
            bio=fac.bio,
            rate_credits=fac.rate_credits,
            is_verified=fac.is_verified,
            verified_expert_badge=fac.verified_expert_badge,
            created_at=fac.created_at.isoformat(),
        )

    async def list_faculty(
        self,
        db: AsyncSession,
        department: Optional[str] = None,
        expertise: Optional[str] = None,
    ) -> List[FacultyProfileResponse]:
        query = select(FacultyProfile)
        if department:
            query = query.where(FacultyProfile.department.ilike(f"%{department}%"))
        result = await db.execute(query)
        facs = result.scalars().all()

        output = []
        for fac in facs:
            if expertise:
                fac_exp_lower = [e.lower() for e in (fac.expertise or [])]
                if not any(expertise.lower() in e for e in fac_exp_lower):
                    continue
            output.append(
                FacultyProfileResponse(
                    id=str(fac.id),
                    user_id=str(fac.user_id),
                    full_name=fac.full_name,
                    department=fac.department,
                    institution=fac.institution,
                    expertise=fac.expertise or [],
                    bio=fac.bio,
                    rate_credits=fac.rate_credits,
                    is_verified=fac.is_verified,
                    verified_expert_badge=fac.verified_expert_badge,
                    created_at=fac.created_at.isoformat(),
                )
            )
        return output

    # --- 2. Recruiter & Founder Employer Profiles ---

    async def create_or_update_employer_profile(
        self, db: AsyncSession, user_id: uuid.UUID, req: EmployerProfileInput
    ) -> EmployerProfileResponse:
        result = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == user_id)
        )
        emp = result.scalar_one_or_none()
        if not emp:
            emp = EmployerProfile(
                user_id=user_id,
                full_name=req.full_name,
                company_name=req.company_name,
                company_domain=req.company_domain,
                designation=req.designation or "Recruiter",
                cin_or_gst=req.cin_or_gst,
                is_verified=req.is_verified,
                verified_employer_badge=req.is_verified,
                created_at=datetime.now(timezone.utc),
            )
            db.add(emp)
        else:
            emp.full_name = req.full_name
            emp.company_name = req.company_name
            emp.company_domain = req.company_domain
            emp.designation = req.designation or emp.designation
            emp.cin_or_gst = req.cin_or_gst
            if req.is_verified:
                emp.is_verified = True
                emp.verified_employer_badge = True

        await db.commit()
        await db.refresh(emp)

        return EmployerProfileResponse(
            id=str(emp.id),
            user_id=str(emp.user_id),
            full_name=emp.full_name,
            company_name=emp.company_name,
            company_domain=emp.company_domain,
            designation=emp.designation,
            cin_or_gst=emp.cin_or_gst,
            is_verified=emp.is_verified,
            verified_employer_badge=emp.verified_employer_badge,
            created_at=emp.created_at.isoformat(),
        )

    async def get_employer_profile(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Optional[EmployerProfileResponse]:
        result = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == user_id)
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return None
        return EmployerProfileResponse(
            id=str(emp.id),
            user_id=str(emp.user_id),
            full_name=emp.full_name,
            company_name=emp.company_name,
            company_domain=emp.company_domain,
            designation=emp.designation,
            cin_or_gst=emp.cin_or_gst,
            is_verified=emp.is_verified,
            verified_employer_badge=emp.verified_employer_badge,
            created_at=emp.created_at.isoformat(),
        )

    async def verify_employer(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> EmployerProfileResponse:
        result = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == user_id)
        )
        emp = result.scalar_one_or_none()
        if not emp:
            raise AppError(code="employer_not_found", message="Employer profile not found", status_code=404)

        emp.is_verified = True
        emp.verified_employer_badge = True
        await db.commit()
        await db.refresh(emp)
        return EmployerProfileResponse(
            id=str(emp.id),
            user_id=str(emp.user_id),
            full_name=emp.full_name,
            company_name=emp.company_name,
            company_domain=emp.company_domain,
            designation=emp.designation,
            cin_or_gst=emp.cin_or_gst,
            is_verified=emp.is_verified,
            verified_employer_badge=emp.verified_employer_badge,
            created_at=emp.created_at.isoformat(),
        )

    # --- 3. Opportunity Posting & Feed ---

    async def create_opportunity(
        self, db: AsyncSession, creator_id: uuid.UUID, req: OpportunityCreateInput
    ) -> OpportunityItemResponse:
        """
        Only verified employers/recruiters can post opportunities.
        Unverified employers cannot post.
        """
        emp_res = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == creator_id)
        )
        emp = emp_res.scalar_one_or_none()

        if not emp or not emp.is_verified:
            raise AppError(
                code="unverified_employer_cannot_post",
                message="Unverified employers cannot post opportunities. Please verify your company domain and registration credentials.",
                status_code=403,
            )

        deadline_dt = None
        if req.deadline:
            try:
                deadline_dt = datetime.fromisoformat(req.deadline)
            except Exception:
                pass

        opp = Opportunity(
            creator_id=creator_id,
            company_name=req.company_name or emp.company_name,
            title=req.title,
            opportunity_type=req.opportunity_type.lower(),
            description=req.description,
            required_skills=req.required_skills or [],
            city=req.city or "Remote",
            deadline=deadline_dt,
            external_link=req.external_link,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(opp)
        await db.commit()
        await db.refresh(opp)

        return OpportunityItemResponse(
            id=str(opp.id),
            creator_id=str(opp.creator_id),
            company_name=opp.company_name,
            title=opp.title,
            opportunity_type=opp.opportunity_type,
            description=opp.description,
            required_skills=opp.required_skills or [],
            city=opp.city,
            deadline=opp.deadline.isoformat() if opp.deadline else None,
            external_link=opp.external_link,
            is_active=opp.is_active,
            verified_employer_badge=True,
            skill_overlap_count=len(opp.required_skills or []),
            skill_overlap_ratio=1.0,
            linked_alumni_summary=f"Connect with alumni at {opp.company_name}",
            linked_alumni=[],
            has_student_opted_in=False,
            created_at=opp.created_at.isoformat(),
        )

    async def get_opportunities_feed(
        self,
        db: AsyncSession,
        student_id: Optional[uuid.UUID] = None,
        skills: Optional[List[str]] = None,
        city: Optional[str] = None,
        opportunity_type: Optional[str] = None,
        college: Optional[str] = None,
    ) -> OpportunitiesFeedResponse:
        """
        Opportunities feed (jobs, hackathons, events, meetups):
        - Filtered by student's skills and city.
        - Ranks by skill overlap.
        - Shows linked alumni at the sponsoring/hiring company ("3 IIIT Delhi alumni work here") from real records.
        """
        student_skills = [s.strip().lower() for s in (skills or []) if s.strip()]
        student_college = college
        student_city = city

        if student_id and not student_skills:
            stu_res = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == student_id)
            )
            stu = stu_res.scalar_one_or_none()
            if stu:
                student_skills = [s.strip().lower() for s in (stu.skills or []) if s.strip()]
                student_college = student_college or stu.college
                student_city = student_city or stu.city

        # Fetch active opportunities
        query = select(Opportunity).where(Opportunity.is_active == True)
        if opportunity_type:
            query = query.where(Opportunity.opportunity_type == opportunity_type.lower())

        opps_res = await db.execute(query)
        opps = opps_res.scalars().all()

        # Query all real alumni from GiverProfile
        alumni_res = await db.execute(select(GiverProfile))
        all_alumni = alumni_res.scalars().all()

        # Fetch student's existing opt-ins if student_id is provided
        opted_in_opp_ids = set()
        if student_id:
            interest_res = await db.execute(
                select(OpportunityInterest).where(
                    OpportunityInterest.student_id == student_id,
                    OpportunityInterest.opted_in == True,
                )
            )
            opted_in_opp_ids = {str(i.opportunity_id) for i in interest_res.scalars().all()}

        items: List[OpportunityItemResponse] = []
        for opp in opps:
            # City filter (matches city or Remote)
            if city and opp.city.strip().lower() != "remote" and opp.city.strip().lower() != city.strip().lower():
                continue

            opp_skills = [s.strip().lower() for s in (opp.required_skills or []) if s.strip()]
            student_skill_set = set(student_skills)
            opp_skill_set = set(opp_skills)

            common_skills = student_skill_set.intersection(opp_skill_set)
            overlap_count = len(common_skills)
            overlap_ratio = round(overlap_count / max(1, len(opp_skill_set)), 2)

            # Match linked alumni from real records at this company
            company_clean = opp.company_name.strip().lower()
            matching_alumni = [
                a for a in all_alumni
                if company_clean in (a.headline or "").lower()
            ]

            # Prioritize student's college if known
            college_clean = (student_college or "").strip().lower()
            same_college_alumni = [
                a for a in matching_alumni
                if college_clean and (a.college or "").strip().lower() == college_clean
            ]

            alumni_to_show = same_college_alumni if same_college_alumni else matching_alumni
            alumni_count = len(alumni_to_show)

            if same_college_alumni and student_college:
                summary_text = f"{alumni_count} {student_college} alumni work here"
            elif alumni_count > 0:
                summary_text = f"{alumni_count} verified alumni work here"
            else:
                summary_text = f"Connect with alumni at {opp.company_name}"

            linked_alumni_list = [
                LinkedAlumnus(
                    giver_id=str(a.user_id),
                    full_name=a.full_name,
                    headline=a.headline or f"Alumnus at {opp.company_name}",
                    college=a.college or "Alumni Network",
                    skills=[s.strip() for s in (a.skills or "").split(",") if s.strip()],
                    can_one_click_request=True,
                )
                for a in alumni_to_show[:5]
            ]

            has_opted = str(opp.id) in opted_in_opp_ids

            items.append(
                OpportunityItemResponse(
                    id=str(opp.id),
                    creator_id=str(opp.creator_id),
                    company_name=opp.company_name,
                    title=opp.title,
                    opportunity_type=opp.opportunity_type,
                    description=opp.description,
                    required_skills=opp.required_skills or [],
                    city=opp.city,
                    deadline=opp.deadline.isoformat() if opp.deadline else None,
                    external_link=opp.external_link,
                    is_active=opp.is_active,
                    verified_employer_badge=True,
                    skill_overlap_count=overlap_count,
                    skill_overlap_ratio=overlap_ratio,
                    linked_alumni_summary=summary_text,
                    linked_alumni=linked_alumni_list,
                    has_student_opted_in=has_opted,
                    created_at=opp.created_at.isoformat(),
                )
            )

        # Rank by skill overlap count descending, then overlap ratio descending
        items.sort(key=lambda x: (x.skill_overlap_count, x.skill_overlap_ratio), reverse=True)

        return OpportunitiesFeedResponse(items=items, total=len(items))

    # --- 4. Student Opt-In & Privacy-Guarded Candidate Views ---

    async def create_or_update_student_profile(
        self, db: AsyncSession, user_id: uuid.UUID, req: StudentProfileInput
    ) -> StudentProfileResponse:
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        stu = result.scalar_one_or_none()
        if not stu:
            stu = StudentProfile(
                user_id=user_id,
                full_name=req.full_name,
                college=req.college,
                skills=req.skills or [],
                city=req.city or "Delhi",
                proof_of_work=req.proof_of_work or [],
                created_at=datetime.now(timezone.utc),
            )
            db.add(stu)
        else:
            stu.full_name = req.full_name
            stu.college = req.college
            stu.skills = req.skills or []
            stu.city = req.city or stu.city
            stu.proof_of_work = req.proof_of_work or stu.proof_of_work

        await db.commit()
        await db.refresh(stu)

        return StudentProfileResponse(
            id=str(stu.id),
            user_id=str(stu.user_id),
            full_name=stu.full_name,
            college=stu.college,
            skills=stu.skills or [],
            city=stu.city,
            proof_of_work=stu.proof_of_work or [],
            created_at=stu.created_at.isoformat(),
        )

    async def express_interest(
        self,
        db: AsyncSession,
        opportunity_id: uuid.UUID,
        student_id: uuid.UUID,
        req: OpportunityInterestInput,
    ) -> OpportunityInterestResponse:
        """Student expresses interest / opts in to an opportunity."""
        opp_res = await db.execute(
            select(Opportunity).where(Opportunity.id == opportunity_id)
        )
        opp = opp_res.scalar_one_or_none()
        if not opp or not opp.is_active:
            raise AppError(code="opportunity_not_found", message="Opportunity not found or inactive", status_code=404)

        result = await db.execute(
            select(OpportunityInterest).where(
                OpportunityInterest.opportunity_id == opportunity_id,
                OpportunityInterest.student_id == student_id,
            )
        )
        interest = result.scalar_one_or_none()
        if not interest:
            interest = OpportunityInterest(
                opportunity_id=opportunity_id,
                student_id=student_id,
                opted_in=True,
                note=req.note,
                proof_of_work=req.proof_of_work or [],
                created_at=datetime.now(timezone.utc),
            )
            db.add(interest)
        else:
            interest.opted_in = True
            if req.note is not None:
                interest.note = req.note
            if req.proof_of_work is not None:
                interest.proof_of_work = req.proof_of_work

        await db.commit()
        await db.refresh(interest)

        return OpportunityInterestResponse(
            id=str(interest.id),
            opportunity_id=str(interest.opportunity_id),
            student_id=str(interest.student_id),
            opted_in=interest.opted_in,
            note=interest.note,
            proof_of_work=interest.proof_of_work or [],
            created_at=interest.created_at.isoformat(),
        )

    async def get_opportunity_candidates(
        self, db: AsyncSession, opportunity_id: uuid.UUID, requester_id: uuid.UUID
    ) -> List[CandidateProfileResponse]:
        """
        Recruiter view of pre-matched interested candidates.
        STRICT PRIVACY RULE: Recruiters see ONLY students who opted in.
        Non-opted-in students are completely hidden.
        """
        opp_res = await db.execute(
            select(Opportunity).where(Opportunity.id == opportunity_id)
        )
        opp = opp_res.scalar_one_or_none()
        if not opp:
            raise AppError(code="opportunity_not_found", message="Opportunity not found", status_code=404)

        # Retrieve interests where student explicitly opted in
        interest_res = await db.execute(
            select(OpportunityInterest).where(
                OpportunityInterest.opportunity_id == opportunity_id,
                OpportunityInterest.opted_in == True,
            ).order_by(OpportunityInterest.created_at.desc())
        )
        interests = interest_res.scalars().all()

        candidates: List[CandidateProfileResponse] = []
        for item in interests:
            stu_res = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == item.student_id)
            )
            stu = stu_res.scalar_one_or_none()

            # Retrieve real vouches from vouches table
            vouch_res = await db.execute(
                select(Vouch).where(Vouch.student_id == item.student_id)
            )
            vouches = [
                f"Vouched by {v.giver_name} at {v.giver_company}"
                for v in vouch_res.scalars().all()
            ]

            full_name = stu.full_name if stu else "Verified Candidate"
            college = stu.college if stu else "Partner University"
            confirmed_skills = stu.skills if stu else []
            proof_of_work = (item.proof_of_work or []) or (stu.proof_of_work if stu else [])

            candidates.append(
                CandidateProfileResponse(
                    student_id=str(item.student_id),
                    full_name=full_name,
                    college=college,
                    confirmed_skills=confirmed_skills,
                    proof_of_work=proof_of_work,
                    vouches=vouches,
                    note=item.note,
                    opted_in=True,
                    opted_in_at=item.created_at.isoformat(),
                )
            )

        return candidates


matching_service = MatchingService()
