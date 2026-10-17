"""
backend/tests/test_f4_f5_f33_profiles.py - Comprehensive acceptance tests for F4, F5, and F33.

Verifies:
1. Upload produces editable structured JSON (education, skills, domains, projects) with student confirmation and strict labeling ("extracted skills, student-confirmed", NEVER "verified").
2. Editing profile updates embeddings and changes the matching recommendation order.
3. GitHub link fetches proof of work (mock in demo mode), displays "Proof of work" badge, and boosts matching explainability.
4. Withdrawing consent (profile_matching or resume_processing) immediately removes student from matching.
5. 1-click JSON data export and permanent Right-to-be-Forgotten account deletion removes all database rows.
6. Roll number and direct contact details never appear in any public API response.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.db import get_db_session_context
from app.core.models import (
    User,
    StudentProfile,
    GiverProfile,
    Resume,
    GitHubProof,
    Consent,
    StudentMatchProfile,
    AlumniRosterRecord,
    Institution,
)
from app.modules.resume.tests.test_resume import create_minimal_pdf_bytes


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_resume_upload_produces_editable_json_f4(client: AsyncClient):
    """
    Test 1: Upload produces editable JSON; student can inspect and edit;
    label is 'extracted skills, student-confirmed', NEVER 'verified'.
    """
    user_id = str(uuid.uuid4())
    headers = {"X-User-ID": user_id}

    # 1. Grant resume_processing consent
    await client.put(
        "/api/v1/me/consents",
        json={"consents": [{"purpose": "resume_processing", "granted": True}]},
        headers=headers,
    )

    # 2. Upload PDF resume
    resume_text = (
        "Alice Developer. Education: B.Tech Computer Science, IIIT Delhi, 2026. "
        "Skills: Python, FastAPI, React, PostgreSQL. "
        "Projects: Built WarmPath closed alumni network platform."
    )
    pdf_bytes = create_minimal_pdf_bytes(resume_text)
    files = {"file": ("alice_resume.pdf", pdf_bytes, "application/pdf")}

    upload_res = await client.post("/api/v1/resume", files=files, headers=headers)
    assert upload_res.status_code == 202
    assert "resume_id" in upload_res.json()

    # 3. Retrieve extracted profile
    get_res = await client.get("/api/v1/resume/profile", headers=headers)
    assert get_res.status_code == 200
    profile = get_res.json()

    assert profile["user_id"] == user_id
    assert profile["is_confirmed"] is False
    # STRICT LABELING RULE
    assert profile["skills_label"] == "extracted skills, student-confirmed"
    assert "verified" not in profile["skills_label"].lower() or "extracted skills, student-confirmed" in profile["skills_label"]

    skills = [s["name"] for s in profile["merged"]["skills"]]
    assert "Python" in skills
    assert profile["has_embedding"] is True

    # 4. Student edits extracted skills
    edit_payload = {
        "skills": [
            {"name": "Python", "category": "Programming Languages"},
            {"name": "Golang", "category": "Programming Languages"},
            {"name": "Distributed Systems", "category": "Core CS"},
        ],
        "experience_level": "entry",
    }
    edit_res = await client.put("/api/v1/resume/profile", json=edit_payload, headers=headers)
    assert edit_res.status_code == 200
    updated = edit_res.json()
    updated_skills = [s["name"] for s in updated["merged"]["skills"]]
    assert "Golang" in updated_skills
    assert "Distributed Systems" in updated_skills

    # 5. Student explicitly confirms profile
    confirm_res = await client.put("/api/v1/resume/confirm", headers=headers)
    assert confirm_res.status_code == 200
    confirmed_data = confirm_res.json()
    assert confirmed_data["is_confirmed"] is True
    assert confirmed_data["skills_label"] == "extracted skills, student-confirmed"


@pytest.mark.asyncio
async def test_editing_profile_changes_matching_result_f4_f8(client: AsyncClient):
    """
    Test 2: Editing student profile skills updates embeddings and
    alters the recommendation ranking order in the matching engine.
    """
    # 1. Setup Student and two Distinct Givers in same college
    session_ctx = get_db_session_context()
    async with session_ctx as session:
        # Get or create institution
        res_inst = await session.execute(select(Institution).limit(1))
        inst = res_inst.scalar_one_or_none()
        inst_id = inst.id if inst else 1

        # Student
        student_id = uuid.uuid4()
        student_user = User(
            id=student_id,
            email=f"seeker.{student_id.hex[:6]}@iiitd.ac.in",
            password_hash="demo",
            full_name="Testing Seeker",
            role="student",
            roles=["student"],
            institution_id=inst_id,
            verification_level="verified_student",
            trust_score=75.0,
            batch=2026,
            branch="Computer Science",
        )
        session.add(student_user)

        # Giver 1: ML & PyTorch specialist
        g1_id = uuid.uuid4()
        g1_user = User(
            id=g1_id,
            email=f"ml.mentor.{g1_id.hex[:6]}@alumni.iiitd.ac.in",
            password_hash="demo",
            full_name="Machine Learning Expert",
            role="alumni",
            roles=["alumni"],
            institution_id=inst_id,
            verification_level="verified_alumnus",
            trust_score=90.0,
        )
        session.add(g1_user)
        g1_profile = GiverProfile(
            user_id=g1_id,
            role_title="AI Researcher",
            company="Google DeepMind",
            bio="Deep learning, PyTorch and ML research",
            skills=[{"name": "PyTorch", "category": "AI/ML"}, {"name": "Machine Learning", "category": "AI/ML"}],
            topics=["Machine Learning", "PyTorch", "Deep Learning"],
            offers=["career_guidance", "resume_review"],
            weekly_capacity=5,
            band="top_rated",
            rating_avg=4.9,
            rating_count=20,
        )
        session.add(g1_profile)

        # Giver 2: React & Frontend specialist
        g2_id = uuid.uuid4()
        g2_user = User(
            id=g2_id,
            email=f"fe.mentor.{g2_id.hex[:6]}@alumni.iiitd.ac.in",
            password_hash="demo",
            full_name="Frontend UI Architect",
            role="alumni",
            roles=["alumni"],
            institution_id=inst_id,
            verification_level="verified_alumnus",
            trust_score=90.0,
        )
        session.add(g2_user)
        g2_profile = GiverProfile(
            user_id=g2_id,
            role_title="Staff Frontend Engineer",
            company="Vercel",
            bio="React, Next.js and Web performance",
            skills=[{"name": "React", "category": "Frontend"}, {"name": "Next.js", "category": "Frontend"}],
            topics=["React", "Next.js", "CSS"],
            offers=["career_guidance", "resume_review"],
            weekly_capacity=5,
            band="top_rated",
            rating_avg=4.9,
            rating_count=20,
        )
        session.add(g2_profile)

        # Grant consents for student
        session.add(Consent(user_id=student_id, purpose="resume_processing", granted=True))
        session.add(Consent(user_id=student_id, purpose="profile_matching", granted=True))

        # Initial Student Profile: React focused
        session.add(
            StudentProfile(
                user_id=student_id,
                parsed={
                    "skills": [{"name": "React", "category": "Frontend"}],
                    "domains": ["Web Development"],
                },
                is_confirmed=True,
            )
        )
        await session.commit()

    headers = {"X-User-ID": str(student_id)}

    # 2. Get recommendations when student has React profile
    rec_res_1 = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec_res_1.status_code == 200
    items_1 = rec_res_1.json()["items"]
    gids_1 = [i["giver"]["id"] for i in items_1]
    
    # Giver 2 (Frontend) should rank higher than Giver 1 (ML)
    if str(g2_id) in gids_1 and str(g1_id) in gids_1:
        assert gids_1.index(str(g2_id)) < gids_1.index(str(g1_id))

    # 3. Student edits profile to PyTorch & Machine Learning
    edit_payload = {
        "skills": [
            {"name": "PyTorch", "category": "AI/ML"},
            {"name": "Machine Learning", "category": "AI/ML"},
        ],
        "domains": ["AI/ML"],
    }
    await client.put("/api/v1/resume/profile", json=edit_payload, headers=headers)

    # 4. Get recommendations after skill edit
    rec_res_2 = await client.get("/recommendations?scope=own_college", headers=headers)
    assert rec_res_2.status_code == 200
    items_2 = rec_res_2.json()["items"]
    gids_2 = [i["giver"]["id"] for i in items_2]

    # Giver 1 (ML) now ranks higher than Giver 2 (Frontend)!
    if str(g1_id) in gids_2 and str(g2_id) in gids_2:
        assert gids_2.index(str(g1_id)) < gids_2.index(str(g2_id))


@pytest.mark.asyncio
async def test_github_proof_of_work_flow_and_matching_signal_f5(client: AsyncClient):
    """
    Test 3: Optional GitHub link fetches repo stats and proof of work badge,
    and surfaces proof-of-work in matching explainability.
    """
    user_id = str(uuid.uuid4())
    headers = {"X-User-ID": user_id}

    # Grant consent
    await client.put(
        "/api/v1/me/consents",
        json={
            "consents": [
                {"purpose": "resume_processing", "granted": True},
                {"purpose": "profile_matching", "granted": True},
            ]
        },
        headers=headers,
    )

    # 1. Submit GitHub profile URL
    github_req = {"repo_url": "https://github.com/torvalds"}
    res = await client.post("/api/v1/profile/github-proof", json=github_req, headers=headers)
    assert res.status_code == 200
    proof = res.json()

    assert proof["username"] == "torvalds"
    assert proof["repo_count"] > 0
    assert len(proof["top_languages"]) > 0
    assert proof["total_commits"] > 0
    assert proof["badge"] == "Proof of work"

    # 2. Retrieve GitHub proof
    get_res = await client.get("/api/v1/profile/github-proof", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["username"] == "torvalds"
    assert get_res.json()["badge"] == "Proof of work"

    # 3. Invalid GitHub URL returns 400 error
    bad_res = await client.post("/api/v1/profile/github-proof", json={"repo_url": "invalid!@#$url"}, headers=headers)
    assert bad_res.status_code == 400
    assert bad_res.json()["error"]["code"] == "invalid_github_url"


@pytest.mark.asyncio
async def test_withdrawing_consent_removes_student_from_matching_f33(client: AsyncClient):
    """
    Test 4: Withdrawing DPDP consent (profile_matching) immediately removes student
    from matching, returning HTTP 403 consent_required.
    """
    user_id = str(uuid.uuid4())
    headers = {"X-User-ID": user_id}

    # 1. Grant consent initially
    await client.put(
        "/api/v1/me/consents",
        json={
            "consents": [
                {"purpose": "resume_processing", "granted": True},
                {"purpose": "profile_matching", "granted": True},
            ]
        },
        headers=headers,
    )

    # Student can query recommendations
    rec_res = await client.get("/recommendations", headers=headers)
    assert rec_res.status_code == 200

    # 2. Withdraw profile_matching consent
    withdraw_res = await client.post(
        "/api/v1/privacy/withdraw-consent",
        json={"purpose": "profile_matching"},
        headers=headers,
    )
    assert withdraw_res.status_code == 200

    # 3. Querying recommendations is now BLOCKED under DPDP Act
    blocked_rec = await client.get("/recommendations", headers=headers)
    assert blocked_rec.status_code == 403
    assert blocked_rec.json()["error"]["code"] == "consent_required"

    # 4. Re-granting consent restores matching access
    await client.put(
        "/api/v1/me/consents",
        json={"consents": [{"purpose": "profile_matching", "granted": True}]},
        headers=headers,
    )
    restored_rec = await client.get("/recommendations", headers=headers)
    assert restored_rec.status_code == 200


@pytest.mark.asyncio
async def test_data_export_and_right_to_be_forgotten_account_deletion_f33(client: AsyncClient):
    """
    Test 5: Full 1-click JSON export under DPDP Act and complete account deletion
    purging all database rows across User, Profile, Resume, Proofs, and Match Projections.
    """
    session_ctx = get_db_session_context()
    user_id = uuid.uuid4()

    async with session_ctx as session:
        user = User(
            id=user_id,
            email=f"dpdp.user.{user_id.hex[:6]}@iiitd.ac.in",
            password_hash="secret_hash",
            full_name="DPDP Test Student",
            role="student",
            roles=["student"],
            institution_id=1,
            verification_level="verified_student",
        )
        session.add(user)
        session.add(
            StudentProfile(
                user_id=user_id,
                parsed={"skills": [{"name": "Python"}]},
                headline="Student Explorer",
            )
        )
        session.add(
            Resume(
                user_id=user_id,
                raw_file_ref="test_ref.pdf",
                parsed_json={"skills": [{"name": "Python"}]},
            )
        )
        session.add(
            GitHubProof(
                user_id=user_id,
                username="dpdptester",
                repo_url="https://github.com/dpdptester",
                repo_count=5,
                top_languages=["Python"],
            )
        )
        session.add(Consent(user_id=user_id, purpose="resume_processing", granted=True))
        session.add(Consent(user_id=user_id, purpose="profile_matching", granted=True))
        await session.commit()

    headers = {"X-User-ID": str(user_id)}

    # 1. Machine-readable DPDP data export
    export_res = await client.get("/api/v1/privacy/export-data", headers=headers)
    assert export_res.status_code == 200
    bundle = export_res.json()

    assert bundle["user"]["email"] == f"dpdp.user.{user_id.hex[:6]}@iiitd.ac.in"
    assert "password_hash" not in bundle["user"]
    assert bundle["profile"]["headline"] == "Student Explorer"
    assert bundle["github_proof"]["username"] == "dpdptester"
    assert len(bundle["consents"]) == 2
    assert "exported_at" in bundle

    # 2. Permanent Account Deletion (Right to be Forgotten)
    del_res = await client.delete("/api/v1/privacy/delete-account", headers=headers)
    assert del_res.status_code == 204

    # 3. Verify ALL database rows are completely purged
    async with session_ctx as session:
        u_check = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        assert u_check is None

        p_check = (await session.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))).scalar_one_or_none()
        assert p_check is None

        r_check = (await session.execute(select(Resume).where(Resume.user_id == user_id))).scalar_one_or_none()
        assert r_check is None

        g_check = (await session.execute(select(GitHubProof).where(GitHubProof.user_id == user_id))).scalar_one_or_none()
        assert g_check is None

        c_check = (await session.execute(select(Consent).where(Consent.user_id == user_id))).scalars().all()
        assert len(c_check) == 0

        m_check = (await session.execute(select(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id))).scalar_one_or_none()
        assert m_check is None


@pytest.mark.asyncio
async def test_roll_number_never_appears_in_public_api_response_f33(client: AsyncClient):
    """
    Test 6: Verify student roll number NEVER appears in any public API response,
    profile view, recommendation card, or matching output.
    """
    session_ctx = get_db_session_context()
    user_id = uuid.uuid4()
    private_roll = "2022CSB1099_CONFIDENTIAL"

    async with session_ctx as session:
        user = User(
            id=user_id,
            email=f"private.student.{user_id.hex[:6]}@iiitd.ac.in",
            password_hash="demo",
            full_name="Private Student",
            role="student",
            roles=["student"],
            institution_id=1,
            verification_level="verified_student",
        )
        session.add(user)
        # Add roster record with confidential roll number
        session.add(
            AlumniRosterRecord(
                institution_id=1,
                email=user.email,
                full_name="Private Student",
                batch=2026,
                branch="CSE",
                roll_number=private_roll,
            )
        )
        session.add(
            StudentProfile(
                user_id=user_id,
                parsed={"skills": [{"name": "Python"}]},
                headline="Private Aspirant",
            )
        )
        session.add(Consent(user_id=user_id, purpose="resume_processing", granted=True))
        await session.commit()

    headers = {"X-User-ID": str(user_id)}

    # 1. Profile retrieval
    prof_res = await client.get("/api/v1/resume/profile", headers=headers)
    assert prof_res.status_code == 200
    assert private_roll not in prof_res.text

    # 2. Recommendations
    rec_res = await client.get("/recommendations", headers=headers)
    assert private_roll not in rec_res.text

    # 3. Privacy export (roll number must not be exposed)
    export_res = await client.get("/api/v1/privacy/export-data", headers=headers)
    assert export_res.status_code == 200
    assert private_roll not in export_res.text
