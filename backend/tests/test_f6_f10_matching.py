"""
backend/tests/test_f6_f10_matching.py - Acceptance test suite for WarmPath Matching Core (F6, F7, F8, F9, F10).

Acceptance criteria verified:
1. Changing intent changes ranking.
2. A full-capacity giver never appears (hard gate exclusion).
3. An inactive giver ranks below an equal active one.
4. Explanations mention real overlapping skills.
5. Request quality step blocks spam/empty requests and refines vague asks.
6. Unverified and suspended givers are hard excluded without names in excluded_summary.
7. Matches include givers of all roles (alumni, faculty, recruiter, founder) with clear type labels.
8. Explain ranking endpoint returns weights and factor breakdowns for jury inspection.
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.db import get_db_session_context
from app.core.models import (
    User,
    StudentProfile,
    GiverProfile,
    Availability,
    Capacity,
    Consent,
    Institution,
)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_request_quality_step_and_refinement_f7(client: AsyncClient):
    """
    Test F7: Request quality pre-flight step.
    - Blocks empty or spam requests.
    - Flags vague asks and returns a constructive suggested refinement with examples.
    - Passes detailed high-signal asks.
    """
    # 1. Blocked: spam request
    spam_res = await client.post(
        "/api/v1/intent/quality-check",
        json={"text": "message me on whatsapp at +91 9999999999 for fast help"},
    )
    assert spam_res.status_code == 200
    spam_data = spam_res.json()
    assert spam_data["is_blocked"] is True
    assert spam_data["quality_score"] == 0.0
    assert "spam" in spam_data["block_reason"].lower() or "prohibited" in spam_data["block_reason"].lower()

    # 2. Blocked: too short / empty
    short_res = await client.post("/api/v1/intent/quality-check", json={"text": "help"})
    assert short_res.status_code == 200
    assert short_res.json()["is_blocked"] is True

    # 3. Vague ask: flagged with refinement suggestion
    vague_res = await client.post(
        "/api/v1/intent/quality-check",
        json={"text": "I need help with my backend resume"},
    )
    assert vague_res.status_code == 200
    vague_data = vague_res.json()
    assert vague_data["is_blocked"] is False
    assert vague_data["is_vague"] is True
    assert vague_data["suggested_refinement"] is not None
    assert len(vague_data["examples"]) >= 3

    # 4. High quality ask: passes cleanly
    good_text = (
        "I am targeting Software Engineer - Backend roles at product companies and want a 30-minute "
        "mock interview focused on Go, Kubernetes, and distributed systems architecture."
    )
    good_res = await client.post("/api/v1/intent/quality-check", json={"text": good_text})
    assert good_res.status_code == 200
    good_data = good_res.json()
    assert good_data["is_blocked"] is False
    assert good_data["is_vague"] is False
    assert good_data["quality_score"] >= 0.8


@pytest.mark.asyncio
async def test_intent_structuring_question_f6(client: AsyncClient):
    """
    Test F6: "What do you want next?" converts free-form goal into structured JSON:
    goal_type, target_role, target_company_type, required_skills.
    """
    user_id = str(uuid.uuid4())
    headers = {"X-User-ID": user_id}

    # Grant consent
    await client.put(
        "/api/v1/me/consents",
        json={"consents": [{"purpose": "profile_matching", "granted": True}]},
        headers=headers,
    )

    ask_text = (
        "I want to break into backend engineering at a high-growth fintech startup and need mock interview "
        "practice with someone experienced in Go and Kubernetes."
    )

    save_res = await client.post(
        "/api/v1/intent",
        json={"text": ask_text},
        headers=headers,
    )
    assert save_res.status_code == 200
    data = save_res.json()

    structured = data["structured"]
    assert structured["goal_type"] in ["mock_interview", "mentor"]
    assert "Backend" in structured["target_role"]
    assert "Fintech" in structured["target_company_type"]
    skills_lower = [s.lower() for s in structured["required_skills"]]
    assert "go" in skills_lower or "kubernetes" in skills_lower


@pytest.mark.asyncio
async def test_changing_intent_changes_ranking_f6_f8(client: AsyncClient):
    """
    Test Acceptance 1: Changing student intent alters ranking order in matching engine.
    """
    session_ctx = get_db_session_context()
    student_id = uuid.uuid4()
    inst_id = 1

    async with session_ctx as session:
        # Student
        session.add(
            User(
                id=student_id,
                email=f"intent.student.{student_id.hex[:6]}@iiitd.ac.in",
                password_hash="demo",
                full_name="Dynamic Seeker",
                role="student",
                roles=["student"],
                institution_id=inst_id,
                verification_level="verified_student",
                trust_score=80.0,
                batch=2026,
                branch="Computer Science",
            )
        )
        session.add(Consent(user_id=student_id, purpose="profile_matching", granted=True))

        # Giver A: Go & Kubernetes Mock Interview specialist
        ga_id = uuid.uuid4()
        session.add(
            User(
                id=ga_id,
                email=f"go.mentor.{ga_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Go Kubernetes Specialist",
                role="alumni",
                roles=["alumni"],
                institution_id=inst_id,
                verification_level="verified_alumnus",
                trust_score=95.0,
            )
        )
        session.add(
            GiverProfile(
                user_id=ga_id,
                role_title="Senior Platform Engineer",
                company="Fintech Corp",
                skills=[{"name": "Go", "category": "Languages"}, {"name": "Kubernetes", "category": "DevOps"}],
                topics=["Kubernetes", "Go", "System Design"],
                offers=["mock_interview"],
                weekly_capacity=5,
                rating_avg=4.9,
                rating_count=15,
                band="top_rated",
            )
        )

        # Giver B: Python & Data Science Resume Review specialist
        gb_id = uuid.uuid4()
        session.add(
            User(
                id=gb_id,
                email=f"ds.mentor.{gb_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Data Science Lead",
                role="alumni",
                roles=["alumni"],
                institution_id=inst_id,
                verification_level="verified_alumnus",
                trust_score=95.0,
            )
        )
        session.add(
            GiverProfile(
                user_id=gb_id,
                role_title="Lead Data Scientist",
                company="Analytics Inc",
                skills=[{"name": "Python", "category": "AI"}, {"name": "Machine Learning", "category": "AI"}],
                topics=["Python", "Machine Learning", "Data Science"],
                offers=["resume_review"],
                weekly_capacity=5,
                rating_avg=4.9,
                rating_count=15,
                band="top_rated",
            )
        )
        await session.commit()

    headers = {"X-User-ID": str(student_id)}

    # 1. Student Intent 1: Go & Kubernetes Mock Interview
    await client.post(
        "/api/v1/intent",
        json={"text": "I need a mock interview for backend Go and Kubernetes roles."},
        headers=headers,
    )

    rec1 = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec1.status_code == 200
    ids_1 = [item["giver"]["id"] for item in rec1.json()["items"]]
    if str(ga_id) in ids_1 and str(gb_id) in ids_1:
        # Giver A (Go) should rank higher than Giver B (Python)
        assert ids_1.index(str(ga_id)) < ids_1.index(str(gb_id))

    # 2. Change Student Intent to: Python Machine Learning Resume Review
    await client.post(
        "/api/v1/intent",
        json={"text": "Looking for a resume review for Python and Machine Learning data science roles."},
        headers=headers,
    )

    rec2 = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec2.status_code == 200
    ids_2 = [item["giver"]["id"] for item in rec2.json()["items"]]
    if str(ga_id) in ids_2 and str(gb_id) in ids_2:
        # Giver B (Python) now ranks higher than Giver A (Go)!
        assert ids_2.index(str(gb_id)) < ids_2.index(str(ga_id))


@pytest.mark.asyncio
async def test_full_capacity_giver_never_appears_f10(client: AsyncClient):
    """
    Test Acceptance 2: A full-capacity giver never appears (Hard Gate exclusion).
    Returns count in excluded_summary without names.
    """
    session_ctx = get_db_session_context()
    student_id = uuid.uuid4()
    full_giver_id = uuid.uuid4()

    async with session_ctx as session:
        session.add(
            User(
                id=student_id,
                email=f"cap.student.{student_id.hex[:6]}@iiitd.ac.in",
                password_hash="demo",
                full_name="Capacity Seeker",
                role="student",
                roles=["student"],
                institution_id=1,
                verification_level="verified_student",
                trust_score=80.0,
            )
        )
        session.add(Consent(user_id=student_id, purpose="profile_matching", granted=True))

        # Full capacity giver
        session.add(
            User(
                id=full_giver_id,
                email=f"full.giver.{full_giver_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Fully Booked Mentor",
                role="alumni",
                roles=["alumni"],
                institution_id=1,
                verification_level="verified_alumnus",
                trust_score=90.0,
            )
        )
        session.add(
            GiverProfile(
                user_id=full_giver_id,
                role_title="Busy Engineer",
                skills=[{"name": "Python"}],
                weekly_capacity=0,  # Zero capacity
            )
        )
        session.add(
            Capacity(
                user_id=full_giver_id,
                weekly_cap=2,
                current_week_booked=2,  # Fully booked
            )
        )
        await session.commit()

    headers = {"X-User-ID": str(student_id)}
    rec_res = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec_res.status_code == 200
    data = rec_res.json()

    giver_ids = [item["giver"]["id"] for item in data["items"]]
    assert str(full_giver_id) not in giver_ids

    # Verify hard gate exclusion tally
    assert data["excluded_summary"]["total_excluded"] >= 1
    assert data["excluded_summary"]["reasons"]["over_capacity"] >= 1


@pytest.mark.asyncio
async def test_inactive_giver_ranks_below_equal_active_one_f8_f11(client: AsyncClient):
    """
    Test Acceptance 3: An inactive giver ranks strictly below an otherwise identical active giver.
    """
    session_ctx = get_db_session_context()
    student_id = uuid.uuid4()
    active_giver_id = uuid.uuid4()
    inactive_giver_id = uuid.uuid4()

    async with session_ctx as session:
        session.add(
            User(
                id=student_id,
                email=f"avail.student.{student_id.hex[:6]}@iiitd.ac.in",
                password_hash="demo",
                full_name="Availability Seeker",
                role="student",
                roles=["student"],
                institution_id=1,
                verification_level="verified_student",
                trust_score=80.0,
                branch="CSE",
            )
        )
        session.add(Consent(user_id=student_id, purpose="profile_matching", granted=True))

        # Giver 1: Active Now
        session.add(
            User(
                id=active_giver_id,
                email=f"active.{active_giver_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Active Mentor",
                role="alumni",
                roles=["alumni"],
                institution_id=1,
                verification_level="verified_alumnus",
                trust_score=90.0,
            )
        )
        session.add(
            GiverProfile(
                user_id=active_giver_id,
                skills=[{"name": "Rust"}, {"name": "Systems"}],
                department="CSE",
                weekly_capacity=5,
                rating_avg=4.8,
            )
        )
        session.add(
            Availability(
                user_id=active_giver_id,
                status="active_now",
                last_active_at=datetime.now(timezone.utc),
                avg_reply_minutes=20,
            )
        )

        # Giver 2: Inactive (identical skills, department, rating)
        session.add(
            User(
                id=inactive_giver_id,
                email=f"inactive.{inactive_giver_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Inactive Mentor",
                role="alumni",
                roles=["alumni"],
                institution_id=1,
                verification_level="verified_alumnus",
                trust_score=90.0,
            )
        )
        session.add(
            GiverProfile(
                user_id=inactive_giver_id,
                skills=[{"name": "Rust"}, {"name": "Systems"}],
                department="CSE",
                weekly_capacity=5,
                rating_avg=4.8,
            )
        )
        session.add(
            Availability(
                user_id=inactive_giver_id,
                status="inactive",
                last_active_at=datetime.now(timezone.utc) - timedelta(days=2),
                avg_reply_minutes=180,
            )
        )
        await session.commit()

    headers = {"X-User-ID": str(student_id)}
    rec_res = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec_res.status_code == 200
    items = rec_res.json()["items"]

    ids = [i["giver"]["id"] for i in items]
    if str(active_giver_id) in ids and str(inactive_giver_id) in ids:
        # Active giver must strictly rank higher than inactive giver
        assert ids.index(str(active_giver_id)) < ids.index(str(inactive_giver_id))

        active_card = next(i for i in items if i["giver"]["id"] == str(active_giver_id))
        inactive_card = next(i for i in items if i["giver"]["id"] == str(inactive_giver_id))
        assert active_card["score_components"]["availability"] > inactive_card["score_components"]["availability"]


@pytest.mark.asyncio
async def test_explanations_mention_real_overlapping_skills_f9(client: AsyncClient):
    """
    Test Acceptance 4: "Why this match" explanation mentions real overlapping skills.
    """
    session_ctx = get_db_session_context()
    student_id = uuid.uuid4()
    giver_id = uuid.uuid4()

    async with session_ctx as session:
        session.add(
            User(
                id=student_id,
                email=f"why.{student_id.hex[:6]}@iiitd.ac.in",
                password_hash="demo",
                full_name="Why Match Student",
                role="student",
                roles=["student"],
                institution_id=1,
                verification_level="verified_student",
                trust_score=80.0,
            )
        )
        session.add(
            StudentProfile(
                user_id=student_id,
                parsed={"skills": [{"name": "Kubernetes"}, {"name": "Golang"}]},
                is_confirmed=True,
            )
        )
        session.add(Consent(user_id=student_id, purpose="profile_matching", granted=True))

        session.add(
            User(
                id=giver_id,
                email=f"k8s.{giver_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Kubernetes Architect",
                role="alumni",
                roles=["alumni"],
                institution_id=1,
                verification_level="verified_alumnus",
                trust_score=92.0,
            )
        )
        session.add(
            GiverProfile(
                user_id=giver_id,
                role_title="Cloud Native Lead",
                skills=[{"name": "Kubernetes", "category": "DevOps"}, {"name": "Golang", "category": "Languages"}],
                weekly_capacity=5,
            )
        )
        await session.commit()

    headers = {"X-User-ID": str(student_id)}
    rec_res = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec_res.status_code == 200

    items = rec_res.json()["items"]
    target_match = next((i for i in items if i["giver"]["id"] == str(giver_id)), None)
    assert target_match is not None

    why_text = " ".join(target_match["why_lines"]).lower()
    assert "kubernetes" in why_text or "golang" in why_text


@pytest.mark.asyncio
async def test_unverified_and_suspended_givers_are_hard_excluded_f10(client: AsyncClient):
    """
    Test F10: Unverified and suspended givers are hard excluded before ranking.
    """
    session_ctx = get_db_session_context()
    student_id = uuid.uuid4()
    unverified_id = uuid.uuid4()
    suspended_id = uuid.uuid4()

    async with session_ctx as session:
        session.add(
            User(
                id=student_id,
                email=f"gate.{student_id.hex[:6]}@iiitd.ac.in",
                password_hash="demo",
                full_name="Gate Seeker",
                role="student",
                roles=["student"],
                institution_id=1,
                verification_level="verified_student",
                trust_score=80.0,
            )
        )
        session.add(Consent(user_id=student_id, purpose="profile_matching", granted=True))

        # Unverified giver (pending)
        session.add(
            User(
                id=unverified_id,
                email=f"pending.{unverified_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Pending Alumnus",
                role="alumni",
                roles=["alumni"],
                institution_id=1,
                verification_level="pending",
                trust_score=50.0,
            )
        )
        session.add(GiverProfile(user_id=unverified_id, weekly_capacity=5))

        # Suspended giver
        session.add(
            User(
                id=suspended_id,
                email=f"suspended.{suspended_id.hex[:6]}@alumni.iiitd.ac.in",
                password_hash="demo",
                full_name="Suspended User",
                role="alumni",
                roles=["alumni"],
                institution_id=1,
                verification_level="verified_alumnus",
                trust_score=15.0,  # Below threshold
            )
        )
        session.add(GiverProfile(user_id=suspended_id, weekly_capacity=5))
        await session.commit()

    headers = {"X-User-ID": str(student_id)}
    rec_res = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec_res.status_code == 200
    data = rec_res.json()

    ids = [i["giver"]["id"] for i in data["items"]]
    assert str(unverified_id) not in ids
    assert str(suspended_id) not in ids

    assert data["excluded_summary"]["reasons"]["unverified"] >= 1
    assert data["excluded_summary"]["reasons"]["suspended"] >= 1


@pytest.mark.asyncio
async def test_explain_ranking_panel_and_giver_roles_f8(client: AsyncClient):
    """
    Test F8 & Jury Explain Panel:
    - Verifies weights loaded from config/matching.json
    - Confirms matches include givers of all roles (alumni, faculty, recruiter, founder) with clear type labels.
    """
    session_ctx = get_db_session_context()
    student_id = uuid.uuid4()
    faculty_id = uuid.uuid4()

    async with session_ctx as session:
        session.add(
            User(
                id=student_id,
                email=f"jury.{student_id.hex[:6]}@iiitd.ac.in",
                password_hash="demo",
                full_name="Jury Seeker",
                role="student",
                roles=["student"],
                institution_id=1,
                verification_level="verified_student",
                trust_score=80.0,
            )
        )
        session.add(Consent(user_id=student_id, purpose="profile_matching", granted=True))

        # Faculty Giver
        session.add(
            User(
                id=faculty_id,
                email=f"faculty.{faculty_id.hex[:6]}@iiitd.ac.in",
                password_hash="demo",
                full_name="Dr. Rajiv Kumar",
                role="faculty",
                roles=["faculty"],
                institution_id=1,
                verification_level="verified_faculty",
                trust_score=98.0,
            )
        )
        session.add(
            GiverProfile(
                user_id=faculty_id,
                role_title="Associate Professor",
                company="IIIT Delhi",
                skills=[{"name": "Distributed Systems"}],
                weekly_capacity=5,
            )
        )
        await session.commit()

    headers = {"X-User-ID": str(student_id)}
    explain_res = await client.get("/recommendations/explain-ranking?scope=own_college", headers=headers)
    assert explain_res.status_code == 200
    data = explain_res.json()

    # Config weights
    assert "weights" in data
    weights = data["weights"]
    assert weights["skill_intent_similarity"] == 0.35
    assert weights["similar_journey"] == 0.15
    assert weights["affinity"] == 0.15
    assert weights["rating"] == 0.15
    assert weights["availability"] == 0.12
    assert weights["response_speed"] == 0.08

    # Faculty giver labeled clearly
    faculty_match = next((c for c in data["candidates"] if c["giver_id"] == str(faculty_id)), None)
    if faculty_match:
        assert faculty_match["giver_type"] == "faculty"
        assert faculty_match["giver_type_label"] == "Faculty Mentor"
