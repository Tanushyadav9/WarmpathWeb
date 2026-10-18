"""
Acceptance tests for outcome tracking, interactive network graph, and pilot metrics with launch gate.
"""
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.matching.models import (
    EmployerProfile,
    FacultyProfile,
    GiverProfile,
    StudentProfile,
)
from app.modules.ratings.models import Vouch
from app.modules.sessions.models import MentorshipRequest
from app.modules.institution.models import College, SessionOutcome


@pytest.mark.asyncio
async def test_network_graph_edges_and_nodes(async_client: AsyncClient, db_session: AsyncSession):
    """
    Acceptance test 1:
    - Interactive force-directed network graph displays colored nodes:
      students (#3B82F6), alumni (#10B981), faculty (#8B5CF6), recruiters (#F59E0B), founders (#EC4899).
    - Real database edges connect completed sessions and vouches.
    - Safe summary hides contact details (contact_hidden=True).
    - Role, college, and skill filters work properly.
    """
    student_id = uuid.uuid4()
    giver_id = uuid.uuid4()
    faculty_id = uuid.uuid4()
    recruiter_id = uuid.uuid4()
    founder_id = uuid.uuid4()

    # Create profiles
    sp = StudentProfile(
        user_id=student_id,
        full_name="Aarav Sharma",
        college="IIIT Delhi",
        skills=["Python", "FastAPI", "Distributed Systems"],
        city="Delhi",
    )
    gp = GiverProfile(
        user_id=giver_id,
        full_name="Priya Patel",
        headline="Staff Engineer at Stripe",
        college="IIIT Delhi",
        skills="Python, System Design, Cloud",
        is_verified=True,
    )
    fp = FacultyProfile(
        user_id=faculty_id,
        full_name="Dr. Radhika Gupta",
        department="Computer Science",
        institution="IIIT Delhi",
        expertise=["Distributed Systems", "AI", "Cloud"],
        rate_credits=6,
        is_verified=True,
    )
    ep_rec = EmployerProfile(
        user_id=recruiter_id,
        full_name="Karan Malhotra",
        company_name="Google",
        company_domain="google.com",
        designation="Technical Recruiter",
        is_verified=True,
    )
    ep_founder = EmployerProfile(
        user_id=founder_id,
        full_name="Neha Verma",
        company_name="NextScale AI",
        company_domain="nextscale.ai",
        designation="Founder & CEO",
        is_verified=True,
    )

    db_session.add_all([sp, gp, fp, ep_rec, ep_founder])
    await db_session.commit()

    # Create a real completed session between Student and Giver
    sess_id = uuid.uuid4()
    req = MentorshipRequest(
        id=sess_id,
        student_id=student_id,
        giver_id=giver_id,
        intent="System Architecture review",
        status="completed",
        is_free=True,
        confirmed_slot=datetime(2026, 10, 25, 14, 0, tzinfo=timezone.utc),
    )
    db_session.add(req)

    # Create a real vouch from Giver to Student
    vouch = Vouch(
        session_id=sess_id,
        giver_id=giver_id,
        student_id=student_id,
        giver_name="Priya Patel",
        giver_company="Stripe",
        note="Exceptional grasp of scalable distributed caching architectures.",
    )
    db_session.add(vouch)
    await db_session.commit()

    # Query network graph
    resp = await async_client.get("/admin/network-graph")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    nodes = data["nodes"]
    edges = data["edges"]
    node_map = {n["id"]: n for n in nodes}

    # Verify student node
    assert str(student_id) in node_map
    student_node = node_map[str(student_id)]
    assert student_node["role"] == "student"
    assert student_node["color"] == "#3B82F6"
    assert student_node["safe_summary"]["contact_hidden"] is True
    assert "email" not in student_node["safe_summary"]
    assert "phone" not in student_node["safe_summary"]
    assert student_node["safe_summary"]["completed_sessions"] >= 1
    assert student_node["safe_summary"]["vouches"] >= 1

    # Verify alumni node
    assert str(giver_id) in node_map
    giver_node = node_map[str(giver_id)]
    assert giver_node["role"] == "alumnus"
    assert giver_node["color"] == "#10B981"
    assert giver_node["safe_summary"]["contact_hidden"] is True

    # Verify faculty node
    assert str(faculty_id) in node_map
    faculty_node = node_map[str(faculty_id)]
    assert faculty_node["role"] == "faculty"
    assert faculty_node["color"] == "#8B5CF6"

    # Verify recruiter node
    assert str(recruiter_id) in node_map
    recruiter_node = node_map[str(recruiter_id)]
    assert recruiter_node["role"] == "recruiter"
    assert recruiter_node["color"] == "#F59E0B"

    # Verify founder node
    assert str(founder_id) in node_map
    founder_node = node_map[str(founder_id)]
    assert founder_node["role"] == "founder"
    assert founder_node["color"] == "#EC4899"

    # Verify real database edges
    session_edge = next((e for e in edges if e["type"] == "completed_session" and e["source"] == str(student_id) and e["target"] == str(giver_id)), None)
    assert session_edge is not None, "Completed session edge must reflect real database record"

    vouch_edge = next((e for e in edges if e["type"] == "vouch" and e["source"] == str(giver_id) and e["target"] == str(student_id)), None)
    assert vouch_edge is not None, "Vouch edge must reflect real database record"

    # Test filtering by role
    resp_role = await async_client.get("/admin/network-graph?role=student")
    assert resp_role.status_code == 200
    filtered_role = resp_role.json()["nodes"]
    assert all(n["role"] == "student" for n in filtered_role)

    # Test filtering by college
    resp_coll = await async_client.get("/admin/network-graph?college=IIIT%20Delhi")
    assert resp_coll.status_code == 200
    filtered_coll = resp_coll.json()["nodes"]
    assert any(n["id"] == str(student_id) for n in filtered_coll)

    # Test filtering by skill
    resp_skill = await async_client.get("/admin/network-graph?skill=FastAPI")
    assert resp_skill.status_code == 200
    filtered_skill = resp_skill.json()["nodes"]
    assert any(n["id"] == str(student_id) for n in filtered_skill)


@pytest.mark.asyncio
async def test_launch_gate_locked_until_pilot_targets_met(async_client: AsyncClient, db_session: AsyncSession):
    """
    Acceptance test 2:
    - The launch gate stays locked (red) until pilot targets are met:
      target: 50 verified givers AND >=60.0% request answer rate within 72h.
    - Enabling a college while the launch gate is locked is rejected with 400 launch_gate_locked.
    - Once targets are met, the launch gate turns green and college enablement succeeds.
    """
    admin_id = str(uuid.uuid4())

    # 1. Check pilot metrics when targets are NOT yet met
    resp_init = await async_client.get("/admin/pilot-metrics")
    assert resp_init.status_code == 200
    init_metrics = resp_init.json()
    assert init_metrics["launch_gate"]["is_open"] is False
    assert init_metrics["launch_gate"]["color"] == "red"
    assert "Requirements Pending" in init_metrics["launch_gate"]["label"]
    assert len(init_metrics["launch_gate"]["missing_requirements"]) > 0

    # Verify 30/60/90-day plan structure
    plan = init_metrics["thirty_sixty_ninety_plan"]
    assert len(plan) == 3
    assert plan[0]["phase_days"] == "30-day" and plan[0]["name"] == "Prepare"
    assert plan[1]["phase_days"] == "60-day" and plan[1]["name"] == "Open"
    assert plan[2]["phase_days"] == "90-day" and plan[2]["name"] == "Prove"

    # Attempt to enable a new college while launch gate is locked
    resp_block = await async_client.post(
        "/admin/colleges/enable",
        json={"name": "Birla Institute of Technology", "code": "BITS"},
        headers={"X-User-ID": admin_id},
    )
    assert resp_block.status_code == 400
    err_body = resp_block.json()
    assert err_body["error"]["code"] == "launch_gate_locked"
    assert "The launch gate is locked" in err_body["error"]["message"]

    # 2. Satisfy pilot targets:
    # A) Seed at least 50 verified givers
    res_curr_vg = await db_session.execute(select(GiverProfile).where(GiverProfile.is_verified == True))
    current_count = len(res_curr_vg.scalars().all())
    needed = max(0, 50 - current_count)

    for i in range(needed):
        uid = uuid.uuid4()
        gp = GiverProfile(
            user_id=uid,
            full_name=f"Verified Mentor {i + 1}",
            college="IIIT Delhi",
            skills="Python, SQL",
            is_verified=True,
        )
        db_session.add(gp)

    # B) Ensure answer rate >= 60.0% within 72h
    # Create answered requests
    for i in range(5):
        s_uid = uuid.uuid4()
        g_uid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        req = MentorshipRequest(
            id=uuid.uuid4(),
            student_id=s_uid,
            giver_id=g_uid,
            intent="Interview Guidance",
            status="completed",
            is_free=True,
            created_at=now - timedelta(hours=10),
            responded_at=now - timedelta(hours=8),  # 2h reply (< 72h)
        )
        db_session.add(req)

    await db_session.commit()

    # 3. Verify launch gate turns green
    resp_green = await async_client.get("/admin/pilot-metrics")
    assert resp_green.status_code == 200
    green_metrics = resp_green.json()
    assert green_metrics["verified_givers_count"] >= 50
    assert green_metrics["answer_rate_72h_percent"] >= 60.0
    assert green_metrics["launch_gate"]["is_open"] is True
    assert green_metrics["launch_gate"]["color"] == "green"
    assert "Launch Gate Open" in green_metrics["launch_gate"]["label"]
    assert len(green_metrics["launch_gate"]["missing_requirements"]) == 0

    # 4. Enable college now succeeds
    resp_enable = await async_client.post(
        "/admin/colleges/enable",
        json={"name": "Birla Institute of Technology", "code": "BITS"},
        headers={"X-User-ID": admin_id},
    )
    assert resp_enable.status_code == 200, resp_enable.text
    college_data = resp_enable.json()
    assert college_data["name"] == "Birla Institute of Technology"
    assert college_data["code"] == "BITS"
    assert college_data["is_enabled"] is True

    # Check listing colleges
    resp_list = await async_client.get("/admin/colleges")
    assert resp_list.status_code == 200
    colleges = resp_list.json()
    assert any(c["code"] == "BITS" and c["is_enabled"] is True for c in colleges)


@pytest.mark.asyncio
async def test_session_outcome_tracking_and_dashboard_integration(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Acceptance test 3:
    - 7 days after a completed session, student reports "What happened after?"
      (interview, referral, project_feedback, offer, nothing_yet).
    - Session outcomes appear in the institution dashboard:
      total_outcomes_reported, positive_outcomes_count, outcome_rate, outcome_breakdown.
    - Dashboard export CSV reflects outcome metrics.
    """
    student_1 = uuid.uuid4()
    student_2 = uuid.uuid4()
    student_3 = uuid.uuid4()
    giver_id = uuid.uuid4()

    # Create 3 completed sessions
    sess_1_id = uuid.uuid4()
    sess_2_id = uuid.uuid4()
    sess_3_id = uuid.uuid4()

    s1 = MentorshipRequest(
        id=sess_1_id,
        student_id=student_1,
        giver_id=giver_id,
        intent="Resume Review",
        status="completed",
        is_free=True,
    )
    s2 = MentorshipRequest(
        id=sess_2_id,
        student_id=student_2,
        giver_id=giver_id,
        intent="Mock Technical Interview",
        status="rated",
        is_free=True,
    )
    s3 = MentorshipRequest(
        id=sess_3_id,
        student_id=student_3,
        giver_id=giver_id,
        intent="Portfolio feedback",
        status="completed",
        is_free=True,
    )

    db_session.add_all([s1, s2, s3])
    await db_session.commit()

    # 1. Student 1 reports outcome: "interview"
    resp_out1 = await async_client.post(
        f"/sessions/{sess_1_id}/outcome",
        json={"outcome": "interview", "notes": "Got invited to 1st round engineer interview!"},
        headers={"X-User-ID": str(student_1)},
    )
    assert resp_out1.status_code == 200, resp_out1.text
    out1_data = resp_out1.json()
    assert out1_data["outcome"] == "interview"
    assert out1_data["session_id"] == str(sess_1_id)
    assert out1_data["student_id"] == str(student_1)

    # 2. Student 2 reports outcome: "referral"
    resp_out2 = await async_client.post(
        f"/sessions/{sess_2_id}/outcome",
        json={"outcome": "referral", "notes": "Giver submitted internal referral to hiring team."},
        headers={"X-User-ID": str(student_2)},
    )
    assert resp_out2.status_code == 200
    assert resp_out2.json()["outcome"] == "referral"

    # 3. Student 3 reports outcome: "nothing_yet"
    resp_out3 = await async_client.post(
        f"/sessions/{sess_3_id}/outcome",
        json={"outcome": "nothing_yet", "notes": "Still waiting for recruiter update."},
        headers={"X-User-ID": str(student_3)},
    )
    assert resp_out3.status_code == 200
    assert resp_out3.json()["outcome"] == "nothing_yet"

    # 4. Verify outcomes appear on institution dashboard overview
    resp_dash = await async_client.get("/admin/dashboard/overview")
    assert resp_dash.status_code == 200
    dash_data = resp_dash.json()

    assert dash_data["total_outcomes_reported"] >= 3
    assert dash_data["positive_outcomes_count"] >= 2  # interview + referral
    assert dash_data["outcome_rate"] > 0
    assert dash_data["outcome_breakdown"]["interview"] >= 1
    assert dash_data["outcome_breakdown"]["referral"] >= 1
    assert dash_data["outcome_breakdown"]["nothing_yet"] >= 1

    # 5. Verify CSV export contains outcome numbers
    resp_csv = await async_client.get("/admin/dashboard/export-csv")
    assert resp_csv.status_code == 200
    csv_text = resp_csv.text
    assert "total_outcomes_reported," in csv_text
    assert "outcome_rate_percent," in csv_text


@pytest.mark.asyncio
async def test_session_outcome_auth_and_status_validation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Validation tests:
    - Non-student cannot report outcome for another user's session (403 forbidden).
    - Outcome cannot be reported for an incomplete / pending session (400 invalid_session_status).
    - Invalid outcome values are rejected (400 invalid_outcome).
    """
    student_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    giver_id = uuid.uuid4()

    # Session in 'pending' status
    pending_sess_id = uuid.uuid4()
    pending_req = MentorshipRequest(
        id=pending_sess_id,
        student_id=student_id,
        giver_id=giver_id,
        intent="Pending request",
        status="pending",
        is_free=True,
    )
    db_session.add(pending_req)
    await db_session.commit()

    # Attempt to report outcome on pending session -> 400
    resp_pending = await async_client.post(
        f"/sessions/{pending_sess_id}/outcome",
        json={"outcome": "interview"},
        headers={"X-User-ID": str(student_id)},
    )
    assert resp_pending.status_code == 400
    assert resp_pending.json()["error"]["code"] == "invalid_session_status"

    # Now make it completed
    pending_req.status = "completed"
    await db_session.commit()

    # Attempt by someone other than the student -> 403
    resp_unauth = await async_client.post(
        f"/sessions/{pending_sess_id}/outcome",
        json={"outcome": "interview"},
        headers={"X-User-ID": str(other_user_id)},
    )
    assert resp_unauth.status_code == 403
    assert resp_unauth.json()["error"]["code"] == "forbidden"

    # Attempt with an invalid outcome string -> 400
    resp_invalid = await async_client.post(
        f"/sessions/{pending_sess_id}/outcome",
        json={"outcome": "random_unsupported_string"},
        headers={"X-User-ID": str(student_id)},
    )
    assert resp_invalid.status_code == 400
    assert resp_invalid.json()["error"]["code"] == "invalid_outcome"
