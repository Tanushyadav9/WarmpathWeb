"""Automated acceptance tests for Polished UI & Jury Demo Mode.
Validates:
1. HTML UI rendering at / and /demo with responsive landmarks, ARIA accessibility, and dark mode hooks.
2. One-click demo reset restoring deterministic baseline state.
3. Full 8-step Jury Demo story execution:
   (1) Student uploads resume & confirms skills
   (2) Enters vague intent and gets it refined
   (3) Sees ranked matches with why-this-match and active status dots
   (4) Books free same-college session & paid cross-college session (escrow hold)
   (5) Scam message is blocked in chat with safety alert
   (6) Session completes, rating releases credits, 1-click vouch added
   (7) Admin dashboard, skill gap analysis & learned scam rule created
   (8) Fake alumnus rejected, listed member auto-verified
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credits.models import Wallet
from app.modules.institution.models import AdminAuditLog, Report, VerificationRecord
from app.modules.matching.models import StudentProfile
from app.modules.ratings.models import SessionRating, Vouch
from app.modules.sessions.models import MentorshipRequest
from app.modules.trust.models import SafetyFlag, ScamRule
from app.modules.ui.demo_service import (
    DEMO_STUDENT_ID,
    DEMO_GIVER_SAME_ID,
    DEMO_GIVER_CROSS_ID,
    DEMO_REPORT_ID,
    DEMO_VERIF_FAKE_ID,
    DEMO_VERIF_REAL_ID,
)


@pytest.mark.asyncio
async def test_ui_endpoints_and_accessibility(async_client: AsyncClient):
    """Verifies that / and /demo return semantic HTML with accessible landmarks and dark mode."""
    for path in ("/", "/demo"):
        resp = await async_client.get(path)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        content = resp.text
        # Semantic landmarks
        assert 'role="banner"' in content
        assert 'role="region"' in content
        assert 'id="main-content"' in content
        assert 'class="skip-to-main' in content
        # Dark mode and accessibility
        assert 'dark:bg-brand-bgDark' in content
        assert 'aria-label=' in content
        assert 'Jury Demo Walkthrough' in content
        assert 'One-Click Reset' in content


@pytest.mark.asyncio
async def test_demo_reset_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """Verifies that POST /demo/reset cleanly resets all entities to initial Step 1 state."""
    resp = await async_client.post("/demo/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "reset_complete"
    assert data["student"]["name"] == "Aditi Sharma"
    assert data["student"]["credits"] == 20
    assert data["same_college_giver"]["status"] == "active_now"

    # Status check
    res_status = await async_client.get("/demo/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["completed_count"] == 0
    assert status_data["total_steps"] == 8


@pytest.mark.asyncio
async def test_jury_demo_eight_step_story_walkthrough(async_client: AsyncClient, db_session: AsyncSession):
    """
    Executes the entire 8-step Jury Demo story sequentially:
    (1) Resume upload & skills confirmation
    (2) Vague intent refined by AI
    (3) Ranked matches with why-this-match & active status
    (4) Free same-college session (0 credits) & cross-college session (5 credits escrow)
    (5) Scam message blocked in real-time
    (6) Session completes, rating releases escrow, vouch added
    (7) Admin dashboard, skill-gap & learned scam rule
    (8) Fake alumnus rejected, listed member auto-verified
    """
    # 0. Initial Reset
    r_reset = await async_client.post("/demo/reset")
    assert r_reset.status_code == 200

    # --- Step 1: Student Resume & Skills ---
    resp_step1 = await async_client.post("/demo/step/1")
    assert resp_step1.status_code == 200
    d1 = resp_step1.json()
    assert d1["step"] == 1
    assert "Distributed Systems" in d1["extracted_skills"]
    assert "FastAPI" in d1["extracted_skills"]
    assert "github.com/aditi/distributed-raft" in d1["proof_of_work"]
    assert d1["status"] == "completed"

    # Verify database student profile updated
    res_prof = await db_session.execute(select(StudentProfile).where(StudentProfile.user_id == DEMO_STUDENT_ID))
    db_prof = res_prof.scalar_one()
    assert "Distributed Systems" in db_prof.skills

    # --- Step 2: AI Intent Refinement ---
    resp_step2 = await async_client.post("/demo/step/2")
    assert resp_step2.status_code == 200
    d2 = resp_step2.json()
    assert d2["step"] == 2
    assert "System Design" in d2["refined_intent"]
    assert "Distributed Systems" in d2["refined_intent"]
    assert len(d2["focus_tags"]) >= 3

    # Also test live interactive intent refinement endpoint
    resp_live = await async_client.post(
        "/demo/refine-intent",
        json={"intent": "help me prepare for backend interview"},
    )
    assert resp_live.status_code == 200
    assert "System Design & Backend Architecture" in resp_live.json()["refined_intent"]

    # --- Step 3: Ranked Matches & Active Availability ---
    resp_step3 = await async_client.post("/demo/step/3")
    assert resp_step3.status_code == 200
    d3 = resp_step3.json()
    assert d3["step"] == 3
    matches = d3["matches"]
    assert len(matches) == 2
    rohan = next(m for m in matches if m["name"] == "Rohan Sharma")
    priya = next(m for m in matches if m["name"] == "Priya Patel")
    assert rohan["match_score"] == 98
    assert rohan["status"] == "active_now"
    assert rohan["session_cost_credits"] == 0
    assert priya["status"] == "available_today"
    assert priya["session_cost_credits"] == 5
    assert len(rohan["why_this_match"]) >= 2

    # --- Step 4: Book Sessions (Free Same-College + Paid Cross-College) ---
    resp_step4 = await async_client.post("/demo/step/4")
    assert resp_step4.status_code == 200
    d4 = resp_step4.json()
    assert d4["step"] == 4
    assert d4["same_college_session"]["cost_credits"] == 0
    assert d4["cross_college_session"]["cost_credits"] == 5
    assert d4["student_wallet"]["balance"] == 15
    assert d4["student_wallet"]["held"] == 5

    # Verify wallet in database has 5 held credits
    res_w = await db_session.execute(select(Wallet).where(Wallet.user_id == DEMO_STUDENT_ID))
    db_wallet = res_w.scalar_one()
    assert db_wallet.available_balance == 15
    assert db_wallet.held_balance == 5

    # --- Step 5: Scam Message Blocked in Chat ---
    resp_step5 = await async_client.post("/demo/step/5")
    assert resp_step5.status_code == 200
    d5 = resp_step5.json()
    assert d5["step"] == 5
    assert d5["action"] == "BLOCKED"
    assert any("UPI" in v or "Phone" in v for v in d5["detected_violations"])

    # Verify safety flag logged in database
    res_flags = await db_session.execute(select(SafetyFlag).where(SafetyFlag.sender_id == DEMO_STUDENT_ID))
    assert len(res_flags.scalars().all()) >= 1

    # --- Step 6: Session Complete, Release Escrow & 1-Click Vouch ---
    resp_step6 = await async_client.post("/demo/step/6")
    assert resp_step6.status_code == 200
    d6 = resp_step6.json()
    assert d6["step"] == 6
    assert d6["rating"]["stars"] == 5
    assert "Vouched by Rohan Sharma at Microsoft" in d6["vouch"]["badge"]

    # Verify rating and vouch recorded in database
    res_r = await db_session.execute(select(SessionRating).where(SessionRating.rater_id == DEMO_STUDENT_ID))
    assert res_r.scalar_one_or_none() is not None
    res_v = await db_session.execute(select(Vouch).where(Vouch.student_id == DEMO_STUDENT_ID))
    assert res_v.scalar_one_or_none() is not None

    # Verify escrow was released to Priya Patel
    res_w_g = await db_session.execute(select(Wallet).where(Wallet.user_id == DEMO_GIVER_CROSS_ID))
    db_w_giver = res_w_g.scalar_one()
    assert db_w_giver.available_balance == 14  # 10 initial + 4 payout (80% of 5)

    # --- Step 7: Admin Dashboard, Skill Gap & Incident Rule Learning ---
    resp_step7 = await async_client.post("/demo/step/7")
    assert resp_step7.status_code == 200
    d7 = resp_step7.json()
    assert d7["step"] == 7
    assert "SUSPENDED" in d7["moderation_resolution"]
    assert len(d7["dashboard_snapshot"]["skill_gap"]) >= 2
    assert "rules updated" in d7["learned_scam_rule"]["status"]

    # Verify new rule added in scam_rules table
    res_rules = await db_session.execute(select(ScamRule).where(ScamRule.category == "payment_request"))
    assert len(res_rules.scalars().all()) >= 1

    # Verify admin audit log
    res_audit = await db_session.execute(select(AdminAuditLog).where(AdminAuditLog.target_id == str(DEMO_REPORT_ID)))
    assert res_audit.scalar_one_or_none() is not None

    # --- Step 8: Verification Queue (Reject Fake & Auto-Verify Registered) ---
    resp_step8 = await async_client.post("/demo/step/8")
    assert resp_step8.status_code == 200
    d8 = resp_step8.json()
    assert d8["step"] == 8
    assert d8["rejected_applicant"]["status"] == "REJECTED"
    assert d8["auto_verified_member"]["status"] == "APPROVED"
    assert d8["auto_verified_member"]["badge"] == "Verified Alumni"

    # Verify verification records in database
    res_fake = await db_session.execute(select(VerificationRecord).where(VerificationRecord.id == DEMO_VERIF_FAKE_ID))
    assert res_fake.scalar_one().status == "rejected"
    res_real = await db_session.execute(select(VerificationRecord).where(VerificationRecord.id == DEMO_VERIF_REAL_ID))
    assert res_real.scalar_one().status == "approved"

    # Final status check: all 8 steps completed
    res_final = await async_client.get("/demo/status")
    assert res_final.json()["completed_count"] == 8

    # Reset again to confirm clean idempotent state
    r_reset_final = await async_client.post("/demo/reset")
    assert r_reset_final.status_code == 200
    res_after = await async_client.get("/demo/status")
    assert res_after.json()["completed_count"] == 0
