"""
Acceptance tests for giver availability, capacity caps, trust scores, and graduated request limits.
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.rate_limit import _in_memory_rate_limits
from app.core.worker import flip_stale_givers_job
from app.main import app
from app.modules.availability.models import AvailabilityNotification, GiverAvailability
from app.modules.matching.models import GiverProfile
from app.modules.sessions.models import MentorshipRequest
from app.modules.trust.models import UserTrust


@pytest.mark.asyncio
async def test_status_changes_reflect_immediately_in_student_match_list():
    """
    Acceptance test 1:
    Status changes reflect immediately in the student's match list:
    - active_now shows green dot (#15803D)
    - available_today with time window (e.g. 8 to 10 pm) shows amber dot (#F5A524)
    - inactive or reached-capacity givers disappear from matching immediately
    - response rate and reply time are computed from real request history
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())

    student_headers = {"X-User-Id": student_id}
    giver_headers = {"X-User-Id": giver_id}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create giver profile
        async with async_session_maker() as session:
            prof = GiverProfile(
                user_id=uuid.UUID(giver_id),
                full_name="Priya Sharma",
                headline="Staff Engineer at Google",
                college="VIPS-TC",
                skills="Python, System Design, Cloud",
                is_verified=True,
            )
            session.add(prof)
            await session.commit()

        # Step 1: Giver activates status to "active_now"
        res = await client.put(
            "/me/availability",
            headers=giver_headers,
            json={"status": "active_now", "weekly_capacity_cap": 2},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "active_now"
        assert res.json()["status_color"] == "#15803D"

        # Student checks recommendations
        res = await client.get("/recommendations", headers=student_headers)
        assert res.status_code == 200
        items = res.json()["items"]
        giver_match = next((item for item in items if item["giver_id"] == giver_id), None)
        assert giver_match is not None
        assert giver_match["status"] == "active_now"
        assert giver_match["status_color"] == "#15803D"
        assert giver_match["status_label"] == "Active now"

        # Step 2: Giver updates status to "available_today" with time window "8 to 10 pm"
        res = await client.put(
            "/me/availability",
            headers=giver_headers,
            json={"status": "available_today", "today_window": "8 to 10 pm"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "available_today"
        assert res.json()["today_window"] == "8 to 10 pm"
        assert res.json()["status_color"] == "#F5A524"

        # Student checks recommendations immediately -> reflects new status, amber dot, and window
        res = await client.get("/recommendations", headers=student_headers)
        assert res.status_code == 200
        items = res.json()["items"]
        giver_match = next((item for item in items if item["giver_id"] == giver_id), None)
        assert giver_match is not None
        assert giver_match["status"] == "available_today"
        assert giver_match["status_color"] == "#F5A524"
        assert giver_match["today_window"] == "8 to 10 pm"
        assert "8 to 10 pm" in giver_match["status_label"]

        # Step 3: Seed real request history to compute response rate and average reply time
        now = datetime.now(timezone.utc)
        req_id_1 = uuid.uuid4()
        req_id_2 = uuid.uuid4()
        async with async_session_maker() as session:
            # Request 1: answered after 3600 seconds (1 hour)
            r1 = MentorshipRequest(
                id=req_id_1,
                student_id=uuid.uuid4(),
                giver_id=uuid.UUID(giver_id),
                intent="Resume review",
                status="accepted",
                created_at=now - timedelta(hours=2),
                responded_at=now - timedelta(hours=1),
            )
            # Request 2: answered after 7200 seconds (2 hours)
            r2 = MentorshipRequest(
                id=req_id_2,
                student_id=uuid.uuid4(),
                giver_id=uuid.UUID(giver_id),
                intent="Mock interview",
                status="accepted",
                created_at=now - timedelta(hours=3),
                responded_at=now - timedelta(hours=1),
            )
            session.add_all([r1, r2])
            await session.commit()

        # Check giver availability response metrics
        res = await client.get("/me/availability", headers=giver_headers)
        assert res.status_code == 200
        avail_data = res.json()
        assert avail_data["response_rate"] == 100.0
        assert avail_data["avg_reply_time_display"] in ("1h", "2h", "1h 30m", "90m")

        # Step 4: Giver weekly capacity cap is 2, and 2 sessions are now accepted -> capacity cap reached!
        # Giver sees "capacity reached" banner
        assert avail_data["capacity_reached"] is True
        assert avail_data["capacity_banner"] is not None
        assert "Capacity reached" in avail_data["capacity_banner"]

        # Student checks recommendations -> GIVER DISAPPEARS FROM MATCHING!
        res = await client.get("/recommendations", headers=student_headers)
        assert res.status_code == 200
        items = res.json()["items"]
        giver_match = next((item for item in items if item["giver_id"] == giver_id), None)
        assert giver_match is None, "Giver must disappear from matching when capacity is reached"

        # Step 5: Increase capacity cap to 5, giver re-appears
        res = await client.put(
            "/me/availability",
            headers=giver_headers,
            json={"weekly_capacity_cap": 5},
        )
        assert res.json()["capacity_reached"] is False

        res = await client.get("/recommendations", headers=student_headers)
        items = res.json()["items"]
        assert any(item["giver_id"] == giver_id for item in items)

        # Step 6: Giver switches to "inactive" -> DISAPPEARS FROM MATCHING!
        res = await client.put(
            "/me/availability",
            headers=giver_headers,
            json={"status": "inactive"},
        )
        assert res.json()["status"] == "inactive"

        res = await client.get("/recommendations", headers=student_headers)
        items = res.json()["items"]
        assert not any(item["giver_id"] == giver_id for item in items), "Inactive giver must disappear from matching"


@pytest.mark.asyncio
async def test_scheduled_job_flips_stale_givers_to_inactive():
    """
    Acceptance test 2:
    A scheduled job flips stale givers (no activity in N days, default 7) to Inactive
    and sends a notification to confirm availability again.
    """
    stale_giver_id = uuid.uuid4()
    active_giver_id = uuid.uuid4()

    now = datetime.now(timezone.utc)
    eight_days_ago = now - timedelta(days=8)
    one_day_ago = now - timedelta(days=1)

    async with async_session_maker() as session:
        # Giver 1: stale (last active 8 days ago)
        g1 = GiverAvailability(
            user_id=stale_giver_id,
            status="active_now",
            last_active_at=eight_days_ago,
        )
        # Giver 2: active (last active 1 day ago)
        g2 = GiverAvailability(
            user_id=active_giver_id,
            status="active_now",
            last_active_at=one_day_ago,
        )
        session.add_all([g1, g2])
        await session.commit()

    # Run the scheduled job
    flipped = await flip_stale_givers_job()
    assert stale_giver_id in flipped
    assert active_giver_id not in flipped

    # Verify status in database
    async with async_session_maker() as session:
        res1 = await session.execute(
            select(GiverAvailability).where(GiverAvailability.user_id == stale_giver_id)
        )
        g1_after = res1.scalar_one()
        assert g1_after.status == "inactive", "Stale giver should be flipped to Inactive"

        res2 = await session.execute(
            select(GiverAvailability).where(GiverAvailability.user_id == active_giver_id)
        )
        g2_after = res2.scalar_one()
        assert g2_after.status == "active_now", "Recently active giver should remain Active"

        # Verify notification sent to confirm availability
        notif_res = await session.execute(
            select(AvailabilityNotification).where(
                AvailabilityNotification.user_id == stale_giver_id,
                AvailabilityNotification.type == "confirm_availability",
            )
        )
        notif = notif_res.scalar_one_or_none()
        assert notif is not None, "Notification must be sent to confirm availability"
        assert "confirm your availability" in notif.message.lower()


@pytest.mark.asyncio
async def test_fourth_open_request_for_new_student_blocked():
    """
    Acceptance test 3:
    Graduated limits: new students may have at most 3 open requests.
    The fourth open request for a new student is blocked with a clear message.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}

    # Clear rate limit counter for this student test
    _in_memory_rate_limits.clear()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create 4 available givers
        giver_ids = [str(uuid.uuid4()) for _ in range(4)]
        async with async_session_maker() as session:
            for gid in giver_ids:
                avail = GiverAvailability(
                    user_id=uuid.UUID(gid),
                    status="active_now",
                    weekly_capacity_cap=10,
                    last_active_at=datetime.now(timezone.utc),
                )
                session.add(avail)
            await session.commit()

        # Request 1 -> OK
        res1 = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_ids[0], "intent": "Question about interview prep"},
        )
        assert res1.status_code == 200
        assert res1.json()["status"] == "pending"

        # Request 2 -> OK
        res2 = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_ids[1], "intent": "Question about backend engineering"},
        )
        assert res2.status_code == 200

        # Request 3 -> OK (now has 3 open requests)
        res3 = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_ids[2], "intent": "Question about system design"},
        )
        assert res3.status_code == 200

        # Request 4 -> MUST BE BLOCKED WITH A CLEAR MESSAGE!
        res4 = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_ids[3], "intent": "Question about distributed systems"},
        )
        assert res4.status_code in (400, 403, 422, 429)
        err = res4.json()["error"]
        assert err["code"] in ("open_requests_limit_exceeded", "rate_limit_exceeded")
        assert "open request" in err["message"].lower() or "limit" in err["message"].lower()
        assert "3" in err["message"] or "new students" in err["message"].lower()


@pytest.mark.asyncio
async def test_student_must_rate_completed_session_before_sending_more():
    """
    Requirement 4:
    Students must rate completed sessions before sending more requests.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id_1 = str(uuid.uuid4())
    giver_id_2 = str(uuid.uuid4())

    student_headers = {"X-User-Id": student_id}
    _in_memory_rate_limits.clear()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create available givers
        async with async_session_maker() as session:
            for gid in (giver_id_1, giver_id_2):
                session.add(
                    GiverAvailability(
                        user_id=uuid.UUID(gid),
                        status="active_now",
                        weekly_capacity_cap=10,
                        last_active_at=datetime.now(timezone.utc),
                    )
                )
            await session.commit()

        # Seed a completed session for this student that has NOT been rated yet
        completed_req_id = uuid.uuid4()
        async with async_session_maker() as session:
            req = MentorshipRequest(
                id=completed_req_id,
                student_id=uuid.UUID(student_id),
                giver_id=uuid.UUID(giver_id_1),
                intent="Completed mock interview",
                status="completed",
                completed_at=datetime.now(timezone.utc),
                rated=False,
            )
            session.add(req)
            await session.commit()

        # Attempt to create a new request -> BLOCKED because of unrated completed session!
        res = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id_2, "intent": "Follow up mentorship"},
        )
        assert res.status_code == 400
        err = res.json()["error"]
        assert err["code"] == "unrated_sessions_pending"
        assert "rate completed sessions" in err["message"].lower()

        # Student submits rating for the completed session
        rate_res = await client.post(
            f"/sessions/{completed_req_id}/rating",
            headers=student_headers,
            json={"score": 5, "comment": "Outstanding session, learned a lot!"},
        )
        assert rate_res.status_code == 200

        # Now student can successfully send the new request!
        res_after = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id_2, "intent": "Follow up mentorship"},
        )
        assert res_after.status_code == 200
        assert res_after.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_rate_limiting_on_requests_per_day():
    """
    Requirement 5: Rate limiting on requests per day.
    Daily request limits by trust level: new: 3, verified: 10, established: 25, restricted: 1.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}
    _in_memory_rate_limits.clear()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create an available giver
        giver_id = str(uuid.uuid4())
        async with async_session_maker() as session:
            session.add(
                GiverAvailability(
                    user_id=uuid.UUID(giver_id),
                    status="active_now",
                    weekly_capacity_cap=20,
                    last_active_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        # 3 requests created today (allowed for trust level 'new')
        for i in range(3):
            res = await client.post(
                "/requests",
                headers=student_headers,
                json={"giver_id": giver_id, "intent": f"Session {i}"},
            )
            assert res.status_code == 200
            req_id = res.json()["id"]
            # Accept each so open_requests_count doesn't block the rate limit check
            await client.post(f"/requests/{req_id}/accept", headers={"X-User-Id": giver_id})

        # 4th request in the same day -> Exceeds daily rate limit of 3!
        res_limit = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id, "intent": "Exceeding daily limit"},
        )
        assert res_limit.status_code == 429
        err = res_limit.json()["error"]
        assert err["code"] == "rate_limit_exceeded"
        assert "daily limit" in err["message"].lower()

