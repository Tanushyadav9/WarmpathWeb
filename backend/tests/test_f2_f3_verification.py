"""
backend/tests/test_f2_f3_verification.py - Acceptance Tests for F2 & F3 Layered Verification.

Acceptance Criteria:
1. Listed email in CSV roster auto-verifies to 'verified_alumnus' with audit log.
2. Unlisted email lands in 'pending' status with fallback options.
3. Fallback A: Document upload queues for admin review.
4. Fallback B: Two peer vouches from verified batchmates approve applicant to 'verified_alumnus'.
5. Unverified employer (pending) is blocked from posting opportunities (returns 403 Forbidden).
6. Verified employer with valid CIN/GST gets 'verified_professional' and can post opportunities.
7. Duplicate email registration is strictly rejected (returns 400 Bad Request).
8. Admin CSV upload provides preview with error rows and commits valid records.
9. Every status transition writes an audit_log record.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, and_

from app.core.models import (
    AlumniRosterRecord,
    AuditLog,
    Opportunity,
    PeerVouchRequest,
    User,
    VerificationRequest,
)
from app.core.security import create_access_token
from app.main import app


@pytest.mark.asyncio
async def test_listed_email_auto_verifies_f2():
    """1. Listed email in alumni CSV roster auto-verifies to 'verified_alumnus' with audit log."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_email = f"rohan.{uuid.uuid4().hex[:6]}@alumni.iiitd.ac.in"

        # Pre-seed matching roster record in institution roster
        from app.core.db import get_db_session_context
        db = get_db_session_context()
        try:
            rec = AlumniRosterRecord(
                id=uuid.uuid4(),
                institution_id=1,
                email=test_email,
                full_name="Rohan Gupta",
                batch=2021,
                branch="Computer Science",
                roll_number="2017089",
            )
            db.add(rec)
            await db.commit()
        finally:
            await db.close()

        # Request OTP
        otp_res = await client.post(
            "/api/v1/verification/send-otp",
            json={"email": test_email, "purpose": "alumni_registration"},
        )
        assert otp_res.status_code == 200
        demo_otp = otp_res.json()["demo_otp"]

        # Register with matching roster details
        reg_res = await client.post(
            "/api/v1/verification/register-alumni",
            json={
                "role": "alumni",
                "full_name": "Rohan Gupta",
                "email": test_email,
                "password": "demoPassword123",
                "institution_id": 1,
                "batch": 2021,
                "branch": "Computer Science",
                "otp_code": demo_otp,
                "company": "Amazon AWS",
                "headline": "SDE-2 at AWS Distributed Databases",
            },
        )

        assert reg_res.status_code == 201
        data = reg_res.json()
        assert data["auto_approved"] is True
        assert data["verification_level"] == "verified_alumnus"
        assert data["user"]["verification_level"] == "verified_alumnus"
        assert len(data["fallback_options"]) == 0

        # Verify audit log was written
        user_id = data["user"]["id"]
        from app.core.db import get_db_session_context
        db = get_db_session_context()
        try:
            stmt = select(AuditLog).where(
                and_(
                    AuditLog.resource_id == user_id,
                    AuditLog.action == "alumni_registered_verified_csv",
                )
            )
            audit = (await db.execute(stmt)).scalars().first()
            assert audit is not None
            assert audit.metadata_json["auto_approved"] is True
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_unlisted_email_lands_in_pending_f2():
    """2. Unlisted email lands in 'pending' status with fallback options (document upload & peer vouch)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request OTP for unlisted alumni
        unlisted_email = f"unlisted.{uuid.uuid4().hex[:6]}@iiitd.ac.in"
        otp_res = await client.post(
            "/api/v1/verification/send-otp",
            json={"email": unlisted_email, "purpose": "alumni_registration"},
        )
        assert otp_res.status_code == 200
        demo_otp = otp_res.json()["demo_otp"]

        # Register with details not in the roster
        reg_res = await client.post(
            "/api/v1/verification/register-alumni",
            json={
                "role": "alumni",
                "full_name": "Deepak Malhotra",
                "email": unlisted_email,
                "password": "demoPassword123",
                "institution_id": 1,
                "batch": 2019,  # Unlisted batch/email pair
                "branch": "Computer Science",
                "otp_code": demo_otp,
                "company": "Microsoft",
            },
        )
        assert reg_res.status_code == 201
        data = reg_res.json()
        assert data["auto_approved"] is False
        assert data["verification_level"] == "pending"
        assert "document_upload" in data["fallback_options"]
        assert "peer_vouch" in data["fallback_options"]

        token = data["access_token"]

        # Fallback A: Upload degree certificate
        doc_res = await client.post(
            "/api/v1/verification/upload-document",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "document_ref": "https://storage.warmpath.org/degrees/deepak_degree_2019.pdf",
                "document_type": "degree_certificate",
                "notes": "Graduated in 2019 with B.Tech Honors in CSE",
            },
        )
        assert doc_res.status_code == 200
        assert doc_res.json()["status"] == "pending"

        # Verify audit log for pending registration and document upload
        from app.core.db import get_db_session_context
        db = get_db_session_context()
        try:
            stmt = select(AuditLog).where(AuditLog.user_id == uuid.UUID(data["user"]["id"]))
            actions = [log.action for log in (await db.execute(stmt)).scalars().all()]
            assert "alumni_registered_pending" in actions
            assert "verification_document_uploaded" in actions
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_two_peer_vouches_approve_applicant_f2():
    """3. Two peer vouches from verified batchmates approve applicant to 'verified_alumnus'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step A: Create a pending alumni user for Class of 2021
        applicant_email = f"applicant.{uuid.uuid4().hex[:6]}@iiitd.ac.in"
        otp_res = await client.post(
            "/api/v1/verification/send-otp",
            json={"email": applicant_email, "purpose": "alumni_registration"},
        )
        reg_res = await client.post(
            "/api/v1/verification/register-alumni",
            json={
                "role": "alumni",
                "full_name": "Akash Verma",
                "email": applicant_email,
                "password": "demoPassword123",
                "institution_id": 1,
                "batch": 2021,
                "branch": "Computer Science",
                "otp_code": otp_res.json()["demo_otp"],
            },
        )
        applicant_data = reg_res.json()
        applicant_id = applicant_data["user"]["id"]
        applicant_token = applicant_data["access_token"]
        assert applicant_data["verification_level"] == "pending"

        # Step B: Get 2 verified alumni from Class of 2021 (e.g. Vikram Malhotra & another 2021 alumni)
        from app.core.db import get_db_session_context
        db = get_db_session_context()
        try:
            stmt = select(User).where(
                and_(
                    User.role == "alumni",
                    User.institution_id == 1,
                    User.batch == 2021,
                    User.verification_level.in_(["verified_alumnus", "trusted"]),
                )
            ).limit(2)
            vouchers = (await db.execute(stmt)).scalars().all()
            assert len(vouchers) >= 2
            v1, v2 = vouchers[0], vouchers[1]
        finally:
            await db.close()

        # Step C: Applicant requests peer vouches from both
        req_res = await client.post(
            "/api/v1/verification/request-peer-vouches",
            headers={"Authorization": f"Bearer {applicant_token}"},
            json={
                "voucher_emails": [v1.email, v2.email],
                "message": "Hey batchmates, please confirm our 2021 IIITD B.Tech CS graduation!",
            },
        )
        assert req_res.status_code == 200
        vouch_ids = req_res.json()["vouch_ids"]
        assert len(vouch_ids) == 2

        # Step D: First voucher approves -> Applicant should STILL be pending (needs 2)
        v1_token = create_access_token(str(v1.id), claims={"role": v1.role, "email": v1.email})
        resp1 = await client.post(
            "/api/v1/verification/respond-peer-vouch",
            headers={"Authorization": f"Bearer {v1_token}"},
            json={"vouch_id": vouch_ids[0], "action": "approve", "comment": "Yes, studied together in 2021 CS"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["applicant_promoted"] is False

        # Verify applicant is still pending
        status_check1 = await client.get(
            "/api/v1/verification/status",
            headers={"Authorization": f"Bearer {applicant_token}"},
        )
        assert status_check1.json()["verification_level"] == "pending"

        # Step E: Second voucher approves -> Applicant is PROMOTED to 'verified_alumnus'!
        v2_token = create_access_token(str(v2.id), claims={"role": v2.role, "email": v2.email})
        resp2 = await client.post(
            "/api/v1/verification/respond-peer-vouch",
            headers={"Authorization": f"Bearer {v2_token}"},
            json={"vouch_id": vouch_ids[1], "action": "approve", "comment": "Confirmed, worked on capstone with Akash"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["applicant_promoted"] is True

        # Verify applicant is now Verified Alumnus with updated badge
        status_check2 = await client.get(
            "/api/v1/verification/status",
            headers={"Authorization": f"Bearer {applicant_token}"},
        )
        final_status = status_check2.json()
        assert final_status["verification_level"] == "verified_alumnus"
        assert final_status["badge_label"] == "Verified Alumnus"

        # Verify audit log entry
        db = get_db_session_context()
        try:
            audit_stmt = select(AuditLog).where(
                and_(
                    AuditLog.resource_id == applicant_id,
                    AuditLog.action == "alumni_verified_via_peer_vouches",
                )
            )
            audit = (await db.execute(audit_stmt)).scalars().first()
            assert audit is not None
            assert audit.metadata_json["approved_vouches_count"] == 2
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_unverified_employer_blocked_from_posting_f2_f3():
    """4. Unverified employer (pending) is blocked from posting jobs (returns 403 Forbidden)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create an unverified recruiter with pending status
        from app.core.db import get_db_session_context
        db = get_db_session_context()
        try:
            unverified_recruiter = User(
                id=uuid.uuid4(),
                email=f"pending.recruiter.{uuid.uuid4().hex[:6]}@startup.io",
                password_hash="fakehash",
                full_name="Alex Recruiter",
                role="recruiter",
                roles=["recruiter"],
                company="Stealth AI",
                verification_level="pending",
                trust_score=40.0,
                is_active=True,
            )
            db.add(unverified_recruiter)
            await db.commit()
            recruiter_id = unverified_recruiter.id
            recruiter_email = unverified_recruiter.email
        finally:
            await db.close()

        unverified_token = create_access_token(
            str(recruiter_id),
            claims={"role": "recruiter", "email": recruiter_email},
        )

        # Attempt to post a job opportunity -> MUST return 403 Forbidden
        post_res = await client.post(
            "/api/v1/opportunities",
            headers={"Authorization": f"Bearer {unverified_token}"},
            json={
                "title": "Backend SDE-1 (Golang)",
                "description": "Looking for fresh graduates with strong systems background to join our early backend team.",
                "type": "job",
                "skills": ["Go", "Distributed Systems"],
            },
        )
        assert post_res.status_code == 403
        assert "Unverified employers cannot post jobs" in post_res.json()["detail"]


@pytest.mark.asyncio
async def test_verified_employer_registration_and_opportunity_posting_f2_f3():
    """5. Verified employer with valid CIN/GST gets 'verified_professional' and can post opportunities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        employer_email = f"careers.{uuid.uuid4().hex[:6]}@postman.com"

        # Request OTP
        otp_res = await client.post(
            "/api/v1/verification/send-otp",
            json={"email": employer_email, "purpose": "employer_registration"},
        )
        assert otp_res.status_code == 200

        # Register employer with valid Indian CIN (21 chars) and GSTIN (15 chars)
        reg_res = await client.post(
            "/api/v1/verification/register-employer",
            json={
                "role": "recruiter",
                "full_name": "Tanvi Tech Hiring",
                "email": employer_email,
                "password": "strongPassword123",
                "company": "Postman API Tools",
                "headline": "Lead Technical Recruiter",
                "cin": "U72900DL2021PTC123456",  # Valid 21-char CIN
                "gstin": "07AAAAA0000A1Z5",       # Valid 15-char GSTIN
                "otp_code": otp_res.json()["demo_otp"],
            },
        )
        assert reg_res.status_code == 201
        employer_data = reg_res.json()
        assert employer_data["user"]["verification_level"] == "verified_professional"
        employer_token = employer_data["access_token"]

        # Now verified employer posts opportunity -> MUST succeed (201 Created)
        post_res = await client.post(
            "/api/v1/opportunities",
            headers={"Authorization": f"Bearer {employer_token}"},
            json={
                "title": "API Platform Engineer - Core Runtime",
                "description": "Join our core execution team building high-performance proxy routing systems.",
                "type": "job",
                "company": "Postman API Tools",
                "location": "Bengaluru / Remote",
                "skills": ["TypeScript", "Node.js", "Distributed Systems"],
            },
        )
        assert post_res.status_code == 201
        opp = post_res.json()
        assert opp["title"] == "API Platform Engineer - Core Runtime"
        assert opp["is_verified"] is True


@pytest.mark.asyncio
async def test_duplicate_email_rejected_f2():
    """6. Duplicate email is rejected with 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Existing email: aarav.sharma@iiitd.ac.in
        otp_res = await client.post(
            "/api/v1/verification/send-otp",
            json={"email": "aarav.sharma@iiitd.ac.in", "purpose": "alumni_registration"},
        )
        res = await client.post(
            "/api/v1/verification/register-alumni",
            json={
                "role": "alumni",
                "full_name": "Duplicate Aarav",
                "email": "aarav.sharma@iiitd.ac.in",
                "password": "password123",
                "institution_id": 1,
                "batch": 2021,
                "branch": "Computer Science",
                "otp_code": otp_res.json()["demo_otp"],
            },
        )
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_csv_preview_and_upload_f2():
    """7. Admin CSV upload provides preview with error rows and commits valid records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Admin
        admin_login = await client.post(
            "/auth/login",
            json={"email": "admin@iiitd.ac.in", "password": "demo1234"},
        )
        admin_token = admin_login.json()["access_token"]

        pooja_email = f"pooja.{uuid.uuid4().hex[:6]}@alumni.iiitd.ac.in"
        # CSV text containing 2 valid rows and 2 malformed rows (bad email, invalid batch)
        csv_payload = (
            "Name,Email,Batch,Branch,Roll_Number\n"
            f"Pooja Verma,{pooja_email},2022,Computer Science,2018090\n"
            "Bad Email Row,invalid-email-format,2021,Computer Science,2017002\n"
            "Saurabh Mehra,saurabh.mehra@alumni.iiitd.ac.in,2020,ECE,2016010\n"
            "Invalid Year Row,karan@iiitd.ac.in,not-a-year,Computer Science,2017003\n"
        )

        # Step 1: Preview CSV
        prev_res = await client.post(
            "/api/v1/admin/roster/preview",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"csv_content": csv_payload},
        )
        assert prev_res.status_code == 200
        prev_data = prev_res.json()
        assert prev_data["total_rows"] == 4
        assert prev_data["valid_count"] == 2
        assert prev_data["error_count"] == 2
        assert len(prev_data["error_rows"]) == 2
        assert prev_data["error_rows"][0]["line"] == 3  # line 3 is bad email
        assert "email" in prev_data["error_rows"][0]["error"].lower()

        # Step 2: Commit valid rows
        upload_res = await client.post(
            "/api/v1/admin/roster/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "institution_id": 1,
                "csv_content": csv_payload,
                "replace_existing": False,
            },
        )
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        assert upload_data["records_imported"] == 2
        assert upload_data["errors_skipped"] == 2

        # Step 3: Now Pooja Verma can auto-verify against this newly imported CSV
        otp_res = await client.post(
            "/api/v1/verification/send-otp",
            json={"email": pooja_email, "purpose": "alumni_registration"},
        )
        reg_res = await client.post(
            "/api/v1/verification/register-alumni",
            json={
                "role": "alumni",
                "full_name": "Pooja Verma",
                "email": pooja_email,
                "password": "demoPassword123",
                "institution_id": 1,
                "batch": 2022,
                "branch": "Computer Science",
                "otp_code": otp_res.json()["demo_otp"],
            },
        )

        assert reg_res.status_code == 201
        assert reg_res.json()["auto_approved"] is True
        assert reg_res.json()["verification_level"] == "verified_alumnus"


@pytest.mark.asyncio
async def test_admin_review_queue_and_approval_f2_f3():
    """8. Admin views review queue and approves pending verification request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Admin
        admin_login = await client.post(
            "/auth/login",
            json={"email": "admin@iiitd.ac.in", "password": "demo1234"},
        )
        admin_token = admin_login.json()["access_token"]

        # View queue
        queue_res = await client.get(
            "/api/v1/admin/verification-queue",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert queue_res.status_code == 200
        queue = queue_res.json()["queue"]
        assert len(queue) >= 1

        target_req = queue[0]
        req_id = target_req["request_id"]

        # Admin approves with reason
        action_res = await client.post(
            "/api/v1/admin/verify-action",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "request_id": req_id,
                "action": "approve",
                "reason": "Degree certificate verified against university graduation ledger 2020",
            },
        )
        assert action_res.status_code == 200
        assert action_res.json()["status"] == "approve"
        assert action_res.json()["user_verification_level"] == "verified_alumnus"
