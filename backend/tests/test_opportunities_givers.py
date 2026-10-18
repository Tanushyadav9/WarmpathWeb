"""
Acceptance tests for other givers and the opportunity layer:
1. Unverified recruiter post is rejected
2. The opportunities feed ranks by skill overlap
3. Linked alumni are real records with one-click request
4. A student's data is hidden from recruiters until they opt in
5. Faculty domain mentor profile, custom credit rate, and verified expert badge
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.db import async_session_maker
from app.core.ports import ports
from app.main import app
from app.modules.matching.models import (
    EmployerProfile,
    FacultyProfile,
    GiverProfile,
    Opportunity,
    OpportunityInterest,
    StudentProfile,
)
from app.modules.ratings.models import Vouch
from app.modules.sessions.models import MentorshipRequest


@pytest.mark.asyncio
async def test_unverified_recruiter_post_is_rejected():
    """
    Acceptance test 1:
    Unverified employers cannot post opportunities.
    After verification, posting succeeds with verified-employer badge.
    """
    transport = ASGITransport(app=app)
    recruiter_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create unverified employer profile
        res_prof = await client.post(
            "/recruiters/profile",
            headers={"X-User-Id": recruiter_id},
            json={
                "full_name": "Rohan Mehta",
                "company_name": "Zomato",
                "company_domain": "zomato.com",
                "designation": "Talent Lead",
                "is_verified": False,
            },
        )
        assert res_prof.status_code == 200
        assert res_prof.json()["is_verified"] is False
        assert res_prof.json()["verified_employer_badge"] is False

        # 2. Attempt to post an opportunity fails
        res_post_fail = await client.post(
            "/opportunities",
            headers={"X-User-Id": recruiter_id},
            json={
                "title": "Backend Engineering Intern",
                "company_name": "Zomato",
                "opportunity_type": "job",
                "description": "Looking for Go/Python engineers",
                "required_skills": ["Python", "FastAPI"],
                "city": "Gurugram",
            },
        )
        assert res_post_fail.status_code == 403
        data = res_post_fail.json()
        assert data["error"]["code"] == "unverified_employer_cannot_post"
        assert "unverified" in data["error"]["message"].lower()

        # 3. Recruiter verifies business credentials
        res_verify = await client.post(
            "/recruiters/verify",
            headers={"X-User-Id": recruiter_id},
        )
        assert res_verify.status_code == 200
        assert res_verify.json()["is_verified"] is True
        assert res_verify.json()["verified_employer_badge"] is True

        # 4. Now posting succeeds with verified employer badge
        res_post_success = await client.post(
            "/opportunities",
            headers={"X-User-Id": recruiter_id},
            json={
                "title": "Backend Engineering Intern",
                "company_name": "Zomato",
                "opportunity_type": "job",
                "description": "Looking for Go/Python engineers",
                "required_skills": ["Python", "FastAPI"],
                "city": "Gurugram",
            },
        )
        assert res_post_success.status_code == 200
        opp_data = res_post_success.json()
        assert opp_data["title"] == "Backend Engineering Intern"
        assert opp_data["verified_employer_badge"] is True


@pytest.mark.asyncio
async def test_feed_ranks_by_skill_overlap():
    """
    Acceptance test 2:
    The opportunities feed ranks items by skill overlap count and ratio.
    """
    transport = ASGITransport(app=app)
    employer_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())

    async with async_session_maker() as db:
        # Seed verified employer
        db.add(
            EmployerProfile(
                user_id=uuid.UUID(employer_id),
                full_name="Ananya Roy",
                company_name="Microsoft",
                company_domain="microsoft.com",
                designation="University Recruiter",
                is_verified=True,
                verified_employer_badge=True,
            )
        )
        # Opportunity A: 4 skills matching student
        opp_a = Opportunity(
            id=uuid.uuid4(),
            creator_id=uuid.UUID(employer_id),
            company_name="Microsoft",
            title="Cloud Solutions Engineer",
            opportunity_type="job",
            description="Azure team role",
            required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            city="Bengaluru",
            is_active=True,
        )
        # Opportunity B: 1 skill matching student
        opp_b = Opportunity(
            id=uuid.uuid4(),
            creator_id=uuid.UUID(employer_id),
            company_name="Microsoft",
            title="Java Platform Engineer",
            opportunity_type="job",
            description="Java core team",
            required_skills=["Python", "Java", "Spring"],
            city="Bengaluru",
            is_active=True,
        )
        # Opportunity C: 0 skills matching student
        opp_c = Opportunity(
            id=uuid.uuid4(),
            creator_id=uuid.UUID(employer_id),
            company_name="Microsoft",
            title="Blockchain Researcher",
            opportunity_type="job",
            description="Web3 cryptography",
            required_skills=["Rust", "Solidity"],
            city="Bengaluru",
            is_active=True,
        )
        db.add_all([opp_a, opp_b, opp_c])

        # Seed student profile with 4 skills
        db.add(
            StudentProfile(
                user_id=uuid.UUID(student_id),
                full_name="Kavya Sharma",
                college="IIIT Delhi",
                skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
                city="Bengaluru",
                proof_of_work=["github.com/kavya/cloud-app"],
            )
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request feed for the student filtered by their city
        res = await client.get(
            "/opportunities/feed?city=Bengaluru",
            headers={"X-User-Id": student_id},
        )
        assert res.status_code == 200
        feed = res.json()["items"]
        assert len(feed) >= 3

        # Opp A should rank 1st (4 overlap)
        assert feed[0]["title"] == "Cloud Solutions Engineer"
        assert feed[0]["skill_overlap_count"] == 4

        # Opp B should rank 2nd (1 overlap)
        assert feed[1]["title"] == "Java Platform Engineer"
        assert feed[1]["skill_overlap_count"] == 1

        # Opp C should rank 3rd (0 overlap)
        assert feed[2]["title"] == "Blockchain Researcher"
        assert feed[2]["skill_overlap_count"] == 0


@pytest.mark.asyncio
async def test_linked_alumni_are_real_records_with_one_click_request():
    """
    Acceptance test 3:
    Linked alumni for an opportunity are real database records.
    Shows '3 IIIT Delhi alumni work here' summary and provides one-click request.
    """
    transport = ASGITransport(app=app)
    employer_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    student_college = "IIIT Delhi"

    async with async_session_maker() as db:
        # Create real alumni records working at Google
        alumni_1 = GiverProfile(
            user_id=uuid.uuid4(),
            full_name="Vikram Seth",
            headline="Staff Software Engineer at Google",
            college=student_college,
            skills="Go, Kubernetes, GCP",
            is_verified=True,
        )
        alumni_2 = GiverProfile(
            user_id=uuid.uuid4(),
            full_name="Meera Iyer",
            headline="Senior Engineering Manager at Google",
            college=student_college,
            skills="System Design, Leadership",
            is_verified=True,
        )
        alumni_3 = GiverProfile(
            user_id=uuid.uuid4(),
            full_name="Arjun Das",
            headline="Solutions Architect at Google",
            college=student_college,
            skills="Cloud Architecture, Python",
            is_verified=True,
        )
        db.add_all([alumni_1, alumni_2, alumni_3])

        # Opportunity at Google
        google_opp = Opportunity(
            id=uuid.uuid4(),
            creator_id=uuid.UUID(employer_id),
            company_name="Google",
            title="Google Summer of Mentorship & Hiring Chat",
            opportunity_type="hiring_chat",
            description="Meet the core engineering team",
            required_skills=["Python", "Cloud"],
            city="Remote",
            is_active=True,
        )
        db.add(google_opp)
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            f"/opportunities?college={student_college}",
            headers={"X-User-Id": student_id},
        )
        assert res.status_code == 200
        items = res.json()["items"]
        google_item = next(item for item in items if item["company_name"] == "Google")

        # Summary text displays linked alumni count
        assert "3 IIIT Delhi alumni work here" in google_item["linked_alumni_summary"]

        # Real alumni records are returned
        linked_alumni = google_item["linked_alumni"]
        assert len(linked_alumni) == 3
        alumni_names = [a["full_name"] for a in linked_alumni]
        assert "Vikram Seth" in alumni_names
        assert "Meera Iyer" in alumni_names
        assert "Arjun Das" in alumni_names
        # One-click request enabled
        assert all(a["can_one_click_request"] is True for a in linked_alumni)


@pytest.mark.asyncio
async def test_student_data_is_hidden_from_recruiters_until_opt_in():
    """
    Acceptance test 4:
    A student's data is completely hidden from recruiters until the student explicitly opts in.
    Recruiters see only opted-in candidates with confirmed skills, proof of work, and vouches.
    """
    transport = ASGITransport(app=app)
    recruiter_id = str(uuid.uuid4())
    student_opted_in = str(uuid.uuid4())
    student_not_opted_in = str(uuid.uuid4())
    opportunity_id = uuid.uuid4()

    async with async_session_maker() as db:
        # Create opportunity
        db.add(
            Opportunity(
                id=opportunity_id,
                creator_id=uuid.UUID(recruiter_id),
                company_name="Stripe",
                title="Payments Infrastructure Engineer",
                opportunity_type="job",
                description="High reliability distributed payments",
                required_skills=["Python", "Distributed Systems"],
                city="Remote",
                is_active=True,
            )
        )
        # Create Student 1 (Will opt in)
        db.add(
            StudentProfile(
                user_id=uuid.UUID(student_opted_in),
                full_name="Aman Verma",
                college="VIPS-TC",
                skills=["Python", "Distributed Systems", "SQL"],
                city="Delhi",
                proof_of_work=["github.com/aman/paxos-kv", "aman.dev"],
            )
        )
        # Create Student 2 (Will NOT opt in)
        db.add(
            StudentProfile(
                user_id=uuid.UUID(student_not_opted_in),
                full_name="Sneha Kapoor",
                college="VIPS-TC",
                skills=["Python", "Distributed Systems"],
                city="Delhi",
                proof_of_work=["github.com/sneha/raft"],
            )
        )
        # Add vouch for Student 1
        db.add(
            Vouch(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                giver_id=uuid.uuid4(),
                student_id=uuid.UUID(student_opted_in),
                giver_name="Priya Sharma",
                giver_company="Google",
                note="Strong systems fundamentals",
            )
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Before opt-in, recruiter sees 0 candidates (both students hidden)
        res_empty = await client.get(
            f"/opportunities/{opportunity_id}/candidates",
            headers={"X-User-Id": recruiter_id},
        )
        assert res_empty.status_code == 200
        assert len(res_empty.json()) == 0

        # 2. Student 1 expresses interest (opts in)
        res_opt = await client.post(
            f"/opportunities/{opportunity_id}/express-interest",
            headers={"X-User-Id": student_opted_in},
            json={
                "note": "Excited about payments reliability at Stripe",
                "proof_of_work": ["github.com/aman/paxos-kv"],
            },
        )
        assert res_opt.status_code == 200
        assert res_opt.json()["opted_in"] is True

        # 3. Recruiter checks candidates list
        res_cand = await client.get(
            f"/opportunities/{opportunity_id}/candidates",
            headers={"X-User-Id": recruiter_id},
        )
        assert res_cand.status_code == 200
        candidates = res_cand.json()

        # Recruiter sees Student 1 with confirmed skills, proof of work, and vouches
        assert len(candidates) == 1
        c1 = candidates[0]
        assert c1["student_id"] == student_opted_in
        assert c1["full_name"] == "Aman Verma"
        assert "Distributed Systems" in c1["confirmed_skills"]
        assert "github.com/aman/paxos-kv" in c1["proof_of_work"]
        assert any("Vouched by Priya Sharma at Google" in v for v in c1["vouches"])

        # Student 2 is COMPLETELY HIDDEN
        candidate_ids = [c["student_id"] for c in candidates]
        assert student_not_opted_in not in candidate_ids


@pytest.mark.asyncio
async def test_faculty_domain_mentor_profile_custom_rates_and_expert_badge():
    """
    Acceptance test 5:
    Faculty domain mentor profile with custom credit rate, verified expert badge,
    and rate compensation in the credit economy.
    """
    transport = ASGITransport(app=app)
    faculty_user_id = str(uuid.uuid4())
    student_user_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Faculty creates domain mentor profile with custom rate (8 credits)
        res_fac = await client.post(
            "/faculty/profile",
            headers={"X-User-Id": faculty_user_id},
            json={
                "full_name": "Prof. R. K. Mukherjee",
                "department": "Computer Science & Engineering",
                "institution": "IIIT Delhi",
                "expertise": ["Compilers", "Distributed Systems", "Computer Architecture"],
                "bio": "Professor with 15+ years of research in optimizing compilers.",
                "rate_credits": 8,
            },
        )
        assert res_fac.status_code == 200
        fac_data = res_fac.json()
        assert fac_data["full_name"] == "Prof. R. K. Mukherjee"
        assert fac_data["rate_credits"] == 8
        assert fac_data["verified_expert_badge"] is True
        assert fac_data["is_verified"] is True

        # 2. Public view of faculty profile displays verified expert badge
        res_pub = await client.get(f"/faculty/{faculty_user_id}")
        assert res_pub.status_code == 200
        assert res_pub.json()["verified_expert_badge"] is True
        assert res_pub.json()["rate_credits"] == 8

        # 3. Credits economy checks session cost against faculty's custom rate
        access_check = await ports.credits.can_access(student_user_id, faculty_user_id)
        assert access_check["cost"] == 8  # Custom faculty rate respected!
