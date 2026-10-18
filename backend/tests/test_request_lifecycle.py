"""
Acceptance tests for Request Lifecycle:
1. A message containing a phone number is blocked and logged.
2. Declined request notifies the student.
3. A session cannot be rated before completion.
4. The meeting link is generated on confirmation.
5. Role-based view of student profile hides contact details from giver.
6. Giver no-show triggers refund to student.
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.rate_limit import _in_memory_rate_limits
from app.main import app
from app.modules.availability.models import GiverAvailability
from app.modules.sessions.models import (
    MentorshipMessage,
    MentorshipRequest,
    SessionBooking,
    SessionNotification,
)
from app.modules.trust.models import SafetyFlag, UserTrust


@pytest.fixture(autouse=True)
def clear_limits():
    _in_memory_rate_limits.clear()


@pytest.mark.asyncio
async def test_message_containing_phone_number_is_blocked_and_logged():
    """
    Acceptance test 1:
    A message containing a phone number is blocked and logged in the safety_flags table.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}
    giver_headers = {"X-User-Id": giver_id}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create available giver
        async with async_session_maker() as session:
            session.add(
                GiverAvailability(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(giver_id),
                    status="active_now",
                    weekly_capacity_cap=10,
                    last_active_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        # Student creates mentorship request
        res_req = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id, "intent": "Interview preparation and resume review"},
        )
        assert res_req.status_code == 200
        req_id = res_req.json()["id"]

        # Giver accepts request
        res_acc = await client.post(f"/requests/{req_id}/accept", headers=giver_headers)
        assert res_acc.status_code == 200

        # Attempt to send message with Indian mobile phone number: "+91 9876543210"
        scam_message = "Hey, call me on +91 9876543210 or 9876543210 so we can chat outside."
        res_msg = await client.post(
            f"/requests/{req_id}/messages",
            headers=student_headers,
            json={"body": scam_message},
        )

        # MUST BE BLOCKED (HTTP 400 with safety_violation_blocked)
        assert res_msg.status_code == 400
        err = res_msg.json()["error"]
        assert err["code"] == "safety_violation_blocked"
        assert "phone" in err["message"].lower() or "blocked" in err["message"].lower()
        assert "phone_number" in err.get("details", {}).get("flags", [])

        # Verify safety flag was logged in database
        async with async_session_maker() as session:
            flag_res = await session.execute(
                select(SafetyFlag).where(SafetyFlag.sender_id == uuid.UUID(student_id))
            )
            logged_flag = flag_res.scalar_one_or_none()
            assert logged_flag is not None, "Safety violation must be logged in safety_flags table"
            assert logged_flag.action == "block"
            assert "phone_number" in logged_flag.flags
            assert logged_flag.message_text == scam_message

        # Send a safe message -> allowed!
        res_safe = await client.post(
            f"/requests/{req_id}/messages",
            headers=student_headers,
            json={"body": "Looking forward to our session and discussing distributed systems!"},
        )
        assert res_safe.status_code == 200
        safe_json = res_safe.json()
        assert safe_json["safety_action"] == "allow"
        assert safe_json["body"] == "Looking forward to our session and discussing distributed systems!"

        # Messages can be retrieved via polling
        res_poll = await client.get(f"/requests/{req_id}/messages", headers=giver_headers)
        assert res_poll.status_code == 200
        messages = res_poll.json()
        assert len(messages) == 1
        assert messages[0]["body"] == "Looking forward to our session and discussing distributed systems!"


@pytest.mark.asyncio
async def test_declined_request_notifies_the_student():
    """
    Acceptance test 2:
    Declined request notifies the student with the reason.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}
    giver_headers = {"X-User-Id": giver_id}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create available giver
        async with async_session_maker() as session:
            session.add(
                GiverAvailability(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(giver_id),
                    status="active_now",
                    weekly_capacity_cap=10,
                    last_active_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        # Student creates request
        res_req = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id, "intent": "System design mentorship"},
        )
        assert res_req.status_code == 200
        req_id = res_req.json()["id"]

        # Giver declines with specific reason
        decline_reason = "I am on call this week and have multiple production release deadlines."
        res_dec = await client.post(
            f"/requests/{req_id}/decline",
            headers=giver_headers,
            json={"reason": decline_reason},
        )
        assert res_dec.status_code == 200
        dec_data = res_dec.json()
        assert dec_data["status"] == "declined"
        assert dec_data["decline_reason"] == decline_reason

        # Student checks notifications
        res_notif = await client.get("/me/notifications", headers=student_headers)
        assert res_notif.status_code == 200
        notifications = res_notif.json()
        declined_notif = next((n for n in notifications if n["type"] == "request_declined"), None)
        assert declined_notif is not None, "Notification must be sent to student upon decline"
        assert decline_reason in declined_notif["message"]


@pytest.mark.asyncio
async def test_session_cannot_be_rated_before_completion():
    """
    Acceptance test 3:
    A session cannot be rated before completion.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}
    giver_headers = {"X-User-Id": giver_id}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create available giver
        async with async_session_maker() as session:
            session.add(
                GiverAvailability(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(giver_id),
                    status="active_now",
                    weekly_capacity_cap=10,
                    last_active_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        # Student creates request
        res_req = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id, "intent": "Coding interview review"},
        )
        assert res_req.status_code == 200
        req_id = res_req.json()["id"]

        # Giver accepts request (status is now 'accepted', NOT 'completed')
        await client.post(f"/requests/{req_id}/accept", headers=giver_headers)

        # Student attempts to rate session while accepted -> MUST FAIL (400 session_not_completed)
        res_rate_early = await client.post(
            f"/sessions/{req_id}/rating",
            headers=student_headers,
            json={"score": 5, "comment": "Great session before it even happened!"},
        )
        assert res_rate_early.status_code == 400
        err = res_rate_early.json()["error"]
        assert err["code"] == "session_not_completed"
        assert "cannot be rated before completion" in err["message"].lower()

        # Mark session completed
        res_comp = await client.post(f"/sessions/{req_id}/complete", headers=student_headers)
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "completed"

        # Now rating is permitted!
        res_rate = await client.post(
            f"/sessions/{req_id}/rating",
            headers=student_headers,
            json={"score": 5, "comment": "Incredible insights and helpful feedback!"},
        )
        assert res_rate.status_code == 200
        rate_json = res_rate.json()
        assert rate_json["score"] == 5
        assert rate_json["session_id"] == req_id

        # Check request status transitions to rated
        res_req_after = await client.get(f"/requests/{req_id}", headers=student_headers)
        assert res_req_after.json()["rated"] is True


@pytest.mark.asyncio
async def test_meeting_link_is_generated_on_confirmation():
    """
    Acceptance test 4:
    The meeting link is generated on confirmation via the calendar adapter.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}
    giver_headers = {"X-User-Id": giver_id}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create available giver
        async with async_session_maker() as session:
            session.add(
                GiverAvailability(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(giver_id),
                    status="active_now",
                    weekly_capacity_cap=10,
                    last_active_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        # Step 1: Create request
        res_req = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id, "intent": "Resume polishing and mock interview"},
        )
        req_id = res_req.json()["id"]

        # Step 2: Giver accepts
        await client.post(f"/requests/{req_id}/accept", headers=giver_headers)

        # Step 3: Giver proposes slots
        slot1 = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0).isoformat()
        slot2 = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0).isoformat()
        res_prop = await client.post(
            f"/requests/{req_id}/propose-slots",
            headers=giver_headers,
            json={"slots": [slot1, slot2]},
        )
        assert res_prop.status_code == 200
        assert res_prop.json()["proposed_slots"] == [slot1, slot2]

        # Step 4: Student confirms slot
        res_conf = await client.post(
            f"/requests/{req_id}/confirm-slot",
            headers=student_headers,
            json={"slot": slot1},
        )
        assert res_conf.status_code == 200
        conf_data = res_conf.json()
        assert conf_data["status"] == "scheduled"
        assert conf_data["meeting_link"] is not None
        assert f"{settings.JITSI_BASE_URL}/warmpath-{req_id}" in conf_data["meeting_link"]

        # Verify SessionBooking record created in DB
        async with async_session_maker() as session:
            bk_res = await session.execute(
                select(SessionBooking).where(SessionBooking.request_id == uuid.UUID(req_id))
            )
            booking = bk_res.scalar_one_or_none()
            assert booking is not None, "SessionBooking record must be created on slot confirmation"
            assert booking.meeting_link == conf_data["meeting_link"]
            assert booking.calendar_event_id is not None

        # Verify both student and giver received meeting scheduled notifications
        res_s_notif = await client.get("/me/notifications", headers=student_headers)
        s_notifs = res_s_notif.json()
        assert any(n["type"] == "session_scheduled" and conf_data["meeting_link"] in n["message"] for n in s_notifs)

        res_g_notif = await client.get("/me/notifications", headers=giver_headers)
        g_notifs = res_g_notif.json()
        assert any(n["type"] == "session_scheduled" and conf_data["meeting_link"] in n["message"] for n in g_notifs)


@pytest.mark.asyncio
async def test_role_based_student_profile_hides_contact_details():
    """
    Requirement 1:
    Givers see the student's relevant profile only (role-based view)
    where contact details (phone, email) stay strictly hidden.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}
    giver_headers = {"X-User-Id": giver_id}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create available giver
        async with async_session_maker() as session:
            session.add(
                GiverAvailability(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(giver_id),
                    status="active_now",
                    weekly_capacity_cap=10,
                    last_active_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        # Student creates request with intent and note
        res_req = await client.post(
            "/requests",
            headers=student_headers,
            json={
                "giver_id": giver_id,
                "intent": "Career transition guidance",
                "notes": "Interested in switching from web dev to ML engineering.",
            },
        )
        req_id = res_req.json()["id"]

        # Giver inspects request
        res_view = await client.get(f"/requests/{req_id}", headers=giver_headers)
        assert res_view.status_code == 200
        view_data = res_view.json()

        assert "student_profile" in view_data
        prof = view_data["student_profile"]
        assert prof is not None
        assert prof["intent"] == "Career transition guidance"
        assert prof["notes"] == "Interested in switching from web dev to ML engineering."

        # Verify contact details are completely omitted
        assert "email" not in prof
        assert "phone" not in prof
        assert "phone_number" not in prof


@pytest.mark.asyncio
async def test_giver_no_show_triggers_refund_and_notification():
    """
    Requirement 5:
    No-show handling: if giver fails to attend, session is marked no_show
    and triggers a refund notification to the student.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    student_headers = {"X-User-Id": student_id}
    giver_headers = {"X-User-Id": giver_id}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create available giver
        async with async_session_maker() as session:
            session.add(
                GiverAvailability(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(giver_id),
                    status="active_now",
                    weekly_capacity_cap=10,
                    last_active_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        # Student creates paid/credit session request
        res_req = await client.post(
            "/requests",
            headers=student_headers,
            json={"giver_id": giver_id, "intent": "System design deep dive", "is_free": False},
        )
        req_id = res_req.json()["id"]
        await client.post(f"/requests/{req_id}/accept", headers=giver_headers)

        slot = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        await client.post(f"/requests/{req_id}/confirm-slot", headers=student_headers, json={"slot": slot})

        # Student reports giver no-show
        res_no_show = await client.post(
            f"/sessions/{req_id}/no-show",
            headers=student_headers,
            json={"party": "giver", "reason": "Waited in meeting room for 20 minutes, giver did not arrive"},
        )
        assert res_no_show.status_code == 200
        ns_data = res_no_show.json()
        assert ns_data["status"] == "no_show"
        assert ns_data["no_show_party"] == "giver"

        # Check refund notification was issued to student
        res_notif = await client.get("/me/notifications", headers=student_headers)
        notifs = res_notif.json()
        refund_notif = next((n for n in notifs if n["type"] == "refund_issued"), None)
        assert refund_notif is not None, "Student must receive refund notification on giver no-show"
        assert "refund" in refund_notif["message"].lower()
