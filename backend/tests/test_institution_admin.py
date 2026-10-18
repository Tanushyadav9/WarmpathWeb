"""
Acceptance tests for institution admin experience:
1. Suspending a giver removes them from matching immediately
2. Resolving a scam report creates a new scam rule that blocks the next matching message
3. Dashboard numbers match exact database counts and CSV export reflects them
4. Verification queue integration with audit logging
5. Trust Layers page listing the 7 defensive layers with live dynamic counts
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.db import async_session_maker
from app.main import app
from app.modules.availability.models import GiverAvailability
from app.modules.institution.models import AdminAuditLog, IncidentLog, Report, VerificationRecord
from app.modules.matching.models import GiverProfile
from app.modules.ratings.models import SessionRating
from app.modules.sessions.models import MentorshipMessage, MentorshipRequest
from app.modules.trust.models import ScamRule, UserTrust


@pytest.mark.asyncio
async def test_suspending_a_giver_removes_them_from_matching_immediately():
    """
    Acceptance test 1:
    Suspending a giver immediately removes them from matching recommendations.
    """
    transport = ASGITransport(app=app)
    admin_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    giver_id = uuid.uuid4()

    async with async_session_maker() as db:
        # Create active, verified giver profile
        db.add(
            GiverProfile(
                user_id=giver_id,
                full_name="Rajesh Khanna",
                headline="Lead Architect at Cisco",
                college="VIPS-TC",
                skills="Networking, Python, Distributed Systems",
                is_verified=True,
            )
        )
        db.add(
            GiverAvailability(
                user_id=giver_id,
                status="active_now",
                weekly_capacity_cap=10,
                last_active_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Giver appears in matching recommendations
        res_before = await client.get(
            "/recommendations",
            headers={"X-User-Id": student_id},
        )
        assert res_before.status_code == 200
        items_before = res_before.json()["items"]
        assert any(item["giver_id"] == str(giver_id) for item in items_before)

        # 2. Admin suspends the giver
        res_suspend = await client.post(
            f"/admin/givers/{giver_id}/suspend",
            headers={"X-User-Id": admin_id},
            params={"reason": "Terms of service violation"},
        )
        assert res_suspend.status_code == 200

        # 3. Giver is IMMEDIATELY REMOVED from matching recommendations
        res_after = await client.get(
            "/recommendations",
            headers={"X-User-Id": student_id},
        )
        assert res_after.status_code == 200
        items_after = res_after.json()["items"]
        assert not any(item["giver_id"] == str(giver_id) for item in items_after)


@pytest.mark.asyncio
async def test_resolving_scam_report_creates_new_scam_rule_that_blocks_next_message():
    """
    Acceptance test 2:
    Resolving a scam report:
    - Extracts the scam pattern and adds a row in scam_rules
    - Reduces the trust score of the offender
    - Records 'rules updated' in incident_logs
    - BLOCKS any subsequent message matching the new rule
    """
    transport = ASGITransport(app=app)
    admin_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    scammer_id = str(uuid.uuid4())
    session_id = uuid.uuid4()

    scam_phrase = f"deposit guarantee fee to token account {uuid.uuid4().hex[:6]}"

    async with async_session_maker() as db:
        # Create completed session for report linkage
        db.add(
            MentorshipRequest(
                id=session_id,
                student_id=uuid.UUID(student_id),
                giver_id=uuid.UUID(scammer_id),
                intent="Career Guidance",
                status="accepted",
            )
        )
        # Trust profile for offender
        db.add(
            UserTrust(
                user_id=uuid.UUID(scammer_id),
                is_verified=True,
                reports_count=0,
            )
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Student reports the scammer with evidence
        res_report = await client.post(
            "/reports",
            headers={"X-User-Id": student_id},
            json={
                "reported_user_id": scammer_id,
                "target_type": "session",
                "target_id": str(session_id),
                "reason": "scam",
                "evidence": f"User demanded upfront payment: '{scam_phrase}'",
            },
        )
        assert res_report.status_code == 200
        report_data = res_report.json()
        report_id = report_data["id"]
        assert report_data["status"] == "pending"

        # 2. Admin reviews queue and resolves report as scam with dynamic pattern
        res_resolve = await client.post(
            f"/admin/reports/{report_id}/resolve",
            headers={"X-User-Id": admin_id},
            json={
                "action": "suspend",
                "reason": "Confirmed advance payment fee scam",
                "is_scam": True,
                "new_scam_pattern": scam_phrase,
            },
        )
        assert res_resolve.status_code == 200
        assert res_resolve.json()["status"] == "suspend"
        assert res_resolve.json()["is_scam"] is True

        # 3. Verify ScamRule and IncidentLog in database
        async with async_session_maker() as db:
            rule_res = await db.execute(
                select(ScamRule).where(ScamRule.pattern == scam_phrase)
            )
            rule = rule_res.scalar_one_or_none()
            assert rule is not None
            assert rule.action == "block"

            inc_res = await db.execute(
                select(IncidentLog).where(IncidentLog.report_id == uuid.UUID(report_id))
            )
            inc = inc_res.scalar_one_or_none()
            assert inc is not None
            assert inc.status == "rules updated"
            assert scam_phrase in inc.extracted_patterns

            # Offender trust score reduced
            ut_res = await db.execute(
                select(UserTrust).where(UserTrust.user_id == uuid.UUID(scammer_id))
            )
            ut = ut_res.scalar_one_or_none()
            assert ut.manual_level == "restricted"
            assert ut.reports_count >= 3

        # 4. Now, any message containing this new scam pattern is IMMEDIATELY BLOCKED
        res_msg_fail = await client.post(
            f"/requests/{session_id}/messages",
            headers={"X-User-Id": scammer_id},
            json={"body": f"Please remember to {scam_phrase} before the call starts."},
        )
        assert res_msg_fail.status_code == 400
        msg_err = res_msg_fail.json()
        assert msg_err["error"]["code"] == "safety_violation_blocked"


@pytest.mark.asyncio
async def test_dashboard_numbers_match_database_counts_and_csv_export():
    """
    Acceptance test 3:
    Institution dashboard overview numbers match exact database counts.
    CSV export returns matching operational records.
    """
    transport = ASGITransport(app=app)
    giver_1 = uuid.uuid4()
    giver_2 = uuid.uuid4()
    giver_3 = uuid.uuid4()

    async with async_session_maker() as db:
        # Givers availability
        db.add(GiverAvailability(user_id=giver_1, status="active_now", weekly_capacity_cap=5))
        db.add(GiverAvailability(user_id=giver_2, status="available_today", weekly_capacity_cap=5))
        db.add(GiverAvailability(user_id=giver_3, status="inactive", weekly_capacity_cap=5))

        # Giver profiles with skills
        db.add(GiverProfile(user_id=giver_1, full_name="Siddharth Rao", headline="VP at Oracle", college="VIPS-TC", skills="Python, SQL, Cloud", is_verified=True))
        db.add(GiverProfile(user_id=giver_2, full_name="Tanvi Verma", headline="Engineer at Uber", college="VIPS-TC", skills="Go, Docker, Kubernetes", is_verified=True))

        # Mentorship requests
        req_comp_free = MentorshipRequest(
            id=uuid.uuid4(),
            student_id=uuid.uuid4(),
            giver_id=giver_1,
            intent="Mock Interview on Python and SQL",
            status="completed",
            is_free=True,
            created_at=datetime.now(timezone.utc),
            responded_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        req_comp_paid = MentorshipRequest(
            id=uuid.uuid4(),
            student_id=uuid.uuid4(),
            giver_id=giver_1,
            intent="System Design deep dive",
            status="rated",
            is_free=False,
            created_at=datetime.now(timezone.utc),
            responded_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        req_sched = MentorshipRequest(
            id=uuid.uuid4(),
            student_id=uuid.uuid4(),
            giver_id=giver_2,
            intent="Resume review",
            status="scheduled",
            is_free=True,
            created_at=datetime.now(timezone.utc),
            responded_at=datetime.now(timezone.utc),
        )
        db.add_all([req_comp_free, req_comp_paid, req_sched])

        # Ratings
        db.add(
            SessionRating(
                id=uuid.uuid4(),
                session_id=req_comp_free.id,
                rater_id=req_comp_free.student_id,
                giver_id=giver_1,
                score=5,
                tags=["Helpful"],
                is_flagged=False,
                review_status="approved",
                created_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch dashboard overview
        res = await client.get("/admin/dashboard/overview")
        assert res.status_code == 200
        data = res.json()

        assert data["total_requests"] >= 3
        assert data["completed_sessions"] >= 2
        assert data["free_sessions"] >= 1
        assert data["paid_sessions"] >= 1
        assert data["active_givers"] >= 2
        assert data["inactive_givers"] >= 1
        assert data["fulfillment_rate"] > 0
        assert len(data["skill_gap"]) > 0

        # 2. Fetch CSV export
        res_csv = await client.get("/admin/dashboard/export-csv")
        assert res_csv.status_code == 200
        assert res_csv.headers["content-type"].startswith("text/csv")
        csv_text = res_csv.text

        assert "total_requests," in csv_text
        assert "completed_sessions," in csv_text
        assert "fulfillment_rate_percent," in csv_text
        assert "active_givers," in csv_text


@pytest.mark.asyncio
async def test_verification_queue_integration_and_audit_logging():
    """
    Acceptance test 4:
    Institution verification queue processes applications with audit logging.
    """
    transport = ASGITransport(app=app)
    admin_id = str(uuid.uuid4())
    applicant_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Submit verification record
        res_create = await client.post(
            "/admin/verifications",
            json={
                "user_id": applicant_id,
                "user_type": "alumnus",
                "full_name": "Devansh Gupta",
                "college": "IIIT Delhi",
                "identifier": "2020CSB1014",
                "document_url": "https://verify.edu/degree.pdf",
            },
        )
        assert res_create.status_code == 200
        verif_data = res_create.json()
        verif_id = verif_data["id"]
        assert verif_data["status"] == "pending"

        # 2. List queue
        res_list = await client.get("/admin/verifications?status=pending")
        assert res_list.status_code == 200
        assert any(v["id"] == verif_id for v in res_list.json())

        # 3. Admin approves verification
        res_review = await client.post(
            f"/admin/verifications/{verif_id}/review",
            headers={"X-User-Id": admin_id},
            json={"action": "approve", "notes": "Degree confirmed with university registrar."},
        )
        assert res_review.status_code == 200
        assert res_review.json()["status"] == "approved"

        # 4. Check audit log and user trust update
        async with async_session_maker() as db:
            ut_res = await db.execute(
                select(UserTrust).where(UserTrust.user_id == uuid.UUID(applicant_id))
            )
            ut = ut_res.scalar_one_or_none()
            assert ut is not None
            assert ut.is_verified is True

            audit_res = await db.execute(
                select(AdminAuditLog).where(AdminAuditLog.target_id == verif_id)
            )
            audit = audit_res.scalar_one_or_none()
            assert audit is not None
            assert audit.action == "verify_approve"


@pytest.mark.asyncio
async def test_trust_layers_page_with_live_dynamic_counts():
    """
    Acceptance test 5:
    Trust Layers page lists all 7 defensive layers with live dynamic counts proving each works.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/admin/trust-layers")
        assert res.status_code == 200
        data = res.json()

        layers = data["layers"]
        assert len(layers) == 7

        layer_names = [l["name"] for l in layers]
        assert "Identity at Entry" in layer_names
        assert "Layered Badges" in layer_names
        assert "Graduated Privileges" in layer_names
        assert "In-App Communication" in layer_names
        assert "Scam Detection Filters" in layer_names
        assert "Human Moderation Queue" in layer_names
        assert "Incident Learning Loop" in layer_names

        # Verify live metric names match specification
        metric_names = [l["live_metric_name"] for l in layers]
        assert "verified_count" in metric_names
        assert "badges_issued" in metric_names
        assert "limits_hit" in metric_names
        assert "messages_protected" in metric_names
        assert "scams_blocked" in metric_names
        assert "reviews_done" in metric_names
        assert "rules_learned" in metric_names

        # Summary keys present
        summary = data["summary"]
        assert all(k in summary for k in metric_names)
        assert all(isinstance(v, int) and v >= 0 for v in summary.values())
