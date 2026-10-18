"""
Acceptance tests for Trust & Reputation:
1. Rating before completion is rejected
2. Second rating on the same session is rejected
3. Band changes when thresholds are crossed (Rising -> Trusted -> Top Rated)
4. Flagged rating does not change the giver's average (outlier & mutual ring anti-gaming)
5. Self-rating is blocked
6. Vouch / referral requires score >= 4 and formats display text correctly
7. Student-facing view hides judgment tier labels
8. Top Giver leaderboard per institution and month with fair-start boost
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.ports import ports
from app.main import app
from app.modules.matching.models import GiverProfile
from app.modules.ratings.models import SessionRating, Vouch
from app.modules.sessions.models import MentorshipRequest


@pytest.mark.asyncio
async def test_rating_before_completion_is_rejected():
    """Acceptance test 1: A session cannot be rated before completion."""
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    session_id = uuid.uuid4()

    async with async_session_maker() as db:
        # Session is in pending or scheduled status (not completed)
        req = MentorshipRequest(
            id=session_id,
            student_id=uuid.UUID(student_id),
            giver_id=uuid.UUID(giver_id),
            intent="Resume Review",
            status="scheduled",
        )
        db.add(req)
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/sessions/{session_id}/rating",
            headers={"X-User-Id": student_id},
            json={"score": 5, "tags": ["Helpful", "Clear feedback"], "comment": "Great prep!"},
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "session_not_completed"
        assert "before completion" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_second_rating_on_same_session_is_rejected():
    """Acceptance test 2: Second rating on the same session is rejected."""
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    session_id = uuid.uuid4()

    async with async_session_maker() as db:
        req = MentorshipRequest(
            id=session_id,
            student_id=uuid.UUID(student_id),
            giver_id=uuid.UUID(giver_id),
            intent="Mock Interview",
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(req)
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First rating succeeds
        res1 = await client.post(
            f"/sessions/{session_id}/rating",
            headers={"X-User-Id": student_id},
            json={"score": 5, "tags": ["Helpful"], "comment": "Super helpful!"},
        )
        assert res1.status_code == 200
        assert res1.json()["score"] == 5

        # Second rating fails
        res2 = await client.post(
            f"/sessions/{session_id}/rating",
            headers={"X-User-Id": student_id},
            json={"score": 4, "tags": ["On time"], "comment": "Second rating attempt"},
        )
        assert res2.status_code == 400
        data = res2.json()
        assert data["error"]["code"] == "already_rated"


@pytest.mark.asyncio
async def test_band_changes_when_thresholds_are_crossed():
    """
    Acceptance test 3: Giver band transitions as thresholds are crossed.
    Initial: Rising (n < 5)
    Threshold 1: Trusted (n >= 5, smoothed_avg >= 4.2)
    Threshold 2: Top Rated (n >= 10, smoothed_avg >= 4.6, completion >= 0.90)
    """
    transport = ASGITransport(app=app)
    giver_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Initial band check for new giver
        res_initial = await client.get("/me/band", headers={"X-User-Id": giver_id})
        assert res_initial.status_code == 200
        initial_data = res_initial.json()
        assert initial_data["band"] == "Rising"
        assert initial_data["n"] == 0
        assert initial_data["smoothed_avg"] == 4.0
        assert initial_data["ranking_score"] > initial_data["smoothed_avg"]  # fair-start boost applied

        # 2. Add 5 sessions rated 5 stars
        async with async_session_maker() as db:
            for _ in range(5):
                sid = uuid.uuid4()
                stu_id = uuid.uuid4()
                req = MentorshipRequest(
                    id=sid,
                    student_id=stu_id,
                    giver_id=uuid.UUID(giver_id),
                    intent="Career Guidance",
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(req)
                rating = SessionRating(
                    id=uuid.uuid4(),
                    session_id=sid,
                    rater_id=stu_id,
                    giver_id=uuid.UUID(giver_id),
                    score=5,
                    tags=["Helpful", "Clear feedback"],
                    is_flagged=False,
                    review_status="approved",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(rating)
            await db.commit()

        # Check band: n = 5, smoothed_avg = (4.0*5 + 25) / 10 = 4.5 >= 4.2 -> Trusted
        res_trusted = await client.get("/me/band", headers={"X-User-Id": giver_id})
        assert res_trusted.status_code == 200
        trusted_data = res_trusted.json()
        assert trusted_data["band"] == "Trusted"
        assert trusted_data["n"] == 5
        assert trusted_data["smoothed_avg"] == 4.5

        # 3. Add 5 more sessions rated 5 stars (total 10 sessions)
        async with async_session_maker() as db:
            for _ in range(5):
                sid = uuid.uuid4()
                stu_id = uuid.uuid4()
                req = MentorshipRequest(
                    id=sid,
                    student_id=stu_id,
                    giver_id=uuid.UUID(giver_id),
                    intent="System Design",
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(req)
                rating = SessionRating(
                    id=uuid.uuid4(),
                    session_id=sid,
                    rater_id=stu_id,
                    giver_id=uuid.UUID(giver_id),
                    score=5,
                    tags=["Clear feedback", "On time"],
                    is_flagged=False,
                    review_status="approved",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(rating)
            await db.commit()

        # Check band: n = 10, smoothed_avg = (4.0*5 + 50) / 15 = 4.67 >= 4.6 -> Top Rated
        res_top = await client.get("/me/band", headers={"X-User-Id": giver_id})
        assert res_top.status_code == 200
        top_data = res_top.json()
        assert top_data["band"] == "Top Rated"
        assert top_data["n"] == 10
        assert top_data["smoothed_avg"] == 4.67


@pytest.mark.asyncio
async def test_flagged_rating_does_not_change_giver_average():
    """
    Acceptance test 4:
    Outlier ratings are automatically flagged and queued for human review.
    Flagged ratings do NOT change the giver's average rating or band calculation.
    """
    transport = ASGITransport(app=app)
    giver_id = str(uuid.uuid4())

    # Seed giver with 3 non-flagged 5-star ratings
    # Smoothed avg: (4.0 * 5 + 15) / (5 + 3) = 35 / 8 = 4.38
    async with async_session_maker() as db:
        for _ in range(3):
            sid = uuid.uuid4()
            stu_id = uuid.uuid4()
            req = MentorshipRequest(
                id=sid,
                student_id=stu_id,
                giver_id=uuid.UUID(giver_id),
                intent="Design Interview",
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            db.add(req)
            rating = SessionRating(
                id=uuid.uuid4(),
                session_id=sid,
                rater_id=stu_id,
                giver_id=uuid.UUID(giver_id),
                score=5,
                tags=["Helpful"],
                is_flagged=False,
                review_status="approved",
                created_at=datetime.now(timezone.utc),
            )
            db.add(rating)
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check initial average
        res_before = await client.get(f"/givers/{giver_id}/rating-summary")
        assert res_before.status_code == 200
        avg_before = res_before.json()["rating"]
        count_before = res_before.json()["session_count"]
        assert count_before == 3
        assert avg_before == 4.38

        # Create a new completed session
        new_session_id = uuid.uuid4()
        new_student_id = str(uuid.uuid4())
        async with async_session_maker() as db:
            db.add(
                MentorshipRequest(
                    id=new_session_id,
                    student_id=uuid.UUID(new_student_id),
                    giver_id=uuid.UUID(giver_id),
                    intent="Mock Interview",
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()

        # Submit an extreme outlier rating (score = 1 when history is 5.0)
        res_rate = await client.post(
            f"/sessions/{new_session_id}/rating",
            headers={"X-User-Id": new_student_id},
            json={"score": 1, "tags": [], "comment": "Troll negative review"},
        )
        assert res_rate.status_code == 200
        rate_data = res_rate.json()
        assert rate_data["is_flagged"] is True
        assert rate_data["flag_reason"] == "outlier_rating"
        assert rate_data["review_status"] == "pending"
        rating_id = rate_data["id"]

        # Verify giver's public summary and band average are UNCHANGED
        res_after = await client.get(f"/givers/{giver_id}/rating-summary")
        assert res_after.status_code == 200
        assert res_after.json()["rating"] == avg_before
        assert res_after.json()["session_count"] == count_before

        band_after = await client.get("/me/band", headers={"X-User-Id": giver_id})
        assert band_after.status_code == 200
        assert band_after.json()["smoothed_avg"] == avg_before

        # Check that outlier review appears in the admin queue
        res_queue = await client.get("/admin/ratings/reviews?status=pending")
        assert res_queue.status_code == 200
        reviews = res_queue.json()
        assert any(r["id"] == rating_id for r in reviews)

        # Admin rejects the review
        res_resolve = await client.post(
            f"/admin/ratings/{rating_id}/resolve",
            json={"decision": "reject", "notes": "Confirmed malicious outlier"},
        )
        assert res_resolve.status_code == 200
        assert res_resolve.json()["review_status"] == "rejected"

        # Giver's average remains unchanged
        res_final = await client.get(f"/givers/{giver_id}/rating-summary")
        assert res_final.json()["rating"] == avg_before


@pytest.mark.asyncio
async def test_self_ratings_are_blocked():
    """Anti-gaming test: Self-ratings are blocked."""
    transport = ASGITransport(app=app)
    user_id = str(uuid.uuid4())
    session_id = uuid.uuid4()

    async with async_session_maker() as db:
        req = MentorshipRequest(
            id=session_id,
            student_id=uuid.UUID(user_id),
            giver_id=uuid.UUID(user_id),  # same user
            intent="Mock Interview",
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(req)
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/sessions/{session_id}/rating",
            headers={"X-User-Id": user_id},
            json={"score": 5, "comment": "Rating myself"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "self_rating_blocked"


@pytest.mark.asyncio
async def test_mutual_rating_rings_are_flagged():
    """Anti-gaming test: Mutual rating rings are flagged for review."""
    transport = ASGITransport(app=app)
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())

    # User B previously rated user A 2 times
    async with async_session_maker() as db:
        for _ in range(2):
            sid = uuid.uuid4()
            req = MentorshipRequest(
                id=sid,
                student_id=uuid.UUID(user_b),
                giver_id=uuid.UUID(user_a),
                intent="Mentorship",
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            db.add(req)
            db.add(
                SessionRating(
                    id=uuid.uuid4(),
                    session_id=sid,
                    rater_id=uuid.UUID(user_b),
                    giver_id=uuid.UUID(user_a),
                    score=5,
                    is_flagged=False,
                    review_status="approved",
                    created_at=datetime.now(timezone.utc),
                )
            )
        await db.commit()

    # Now User A tries to rate User B (forming a reciprocal ring)
    session_id = uuid.uuid4()
    async with async_session_maker() as db:
        db.add(
            MentorshipRequest(
                id=session_id,
                student_id=uuid.UUID(user_a),
                giver_id=uuid.UUID(user_b),
                intent="Mentorship",
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/sessions/{session_id}/rating",
            headers={"X-User-Id": user_a},
            json={"score": 5, "comment": "Reciprocal 5 stars"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_flagged"] is True
        assert data["flag_reason"] == "mutual_rating_ring"
        assert data["review_status"] == "pending"


@pytest.mark.asyncio
async def test_vouch_requires_high_rating_and_shows_formatted_endorsement():
    """
    Acceptance test 5:
    - Vouch requires session rating >= 4
    - After rating >= 4, giver can vouch with one click
    - Formats "Vouched by [name] at [company]" on student profile
    """
    transport = ASGITransport(app=app)
    giver_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    session_id = uuid.uuid4()

    async with async_session_maker() as db:
        # Create giver profile with company headline
        db.add(
            GiverProfile(
                user_id=uuid.UUID(giver_id),
                full_name="Priya Sharma",
                headline="Staff Engineer at Google",
                college="VIPS-TC",
                skills="Cloud, Go, Kubernetes",
                is_verified=True,
            )
        )
        # Create completed session
        db.add(
            MentorshipRequest(
                id=session_id,
                student_id=uuid.UUID(student_id),
                giver_id=uuid.UUID(giver_id),
                intent="System Design",
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Rate with 3 stars (< 4)
        res_rate = await client.post(
            f"/sessions/{session_id}/rating",
            headers={"X-User-Id": student_id},
            json={"score": 3, "tags": ["On time"], "comment": "Good discussion"},
        )
        assert res_rate.status_code == 200

        # Attempt to vouch fails because score is < 4
        res_vouch_fail = await client.post(
            f"/sessions/{session_id}/vouch",
            headers={"X-User-Id": giver_id},
            json={"note": "Endorsing candidate"},
        )
        assert res_vouch_fail.status_code == 400
        assert res_vouch_fail.json()["error"]["code"] == "vouch_score_too_low"

        # 2. Second session with 5 stars
        session_id_2 = uuid.uuid4()
        async with async_session_maker() as db:
            db.add(
                MentorshipRequest(
                    id=session_id_2,
                    student_id=uuid.UUID(student_id),
                    giver_id=uuid.UUID(giver_id),
                    intent="Mock Interview",
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()

        await client.post(
            f"/sessions/{session_id_2}/rating",
            headers={"X-User-Id": student_id},
            json={"score": 5, "tags": ["Clear feedback", "Helpful"]},
        )

        # Now giver vouches
        res_vouch = await client.post(
            f"/sessions/{session_id_2}/vouch",
            headers={"X-User-Id": giver_id},
            json={"note": "Demonstrated exceptional problem solving in distributed systems."},
        )
        assert res_vouch.status_code == 200
        vouch_data = res_vouch.json()
        assert vouch_data["giver_name"] == "Priya Sharma"
        assert vouch_data["giver_company"] == "Google"
        assert vouch_data["display_text"] == "Vouched by Priya Sharma at Google"

        # Check student profile / recruiter view
        res_vouches = await client.get(f"/students/{student_id}/vouches")
        assert res_vouches.status_code == 200
        v_list = res_vouches.json()
        assert len(v_list) >= 1
        assert v_list[0]["display_text"] == "Vouched by Priya Sharma at Google"


@pytest.mark.asyncio
async def test_student_public_summary_hides_tier_labels():
    """
    Acceptance test 6:
    Do not show tier labels to students as a judgment;
    show rating, session count and tags.
    """
    transport = ASGITransport(app=app)
    giver_id = str(uuid.uuid4())

    async with async_session_maker() as db:
        # Give giver 10 five-star ratings (top rated tier internally)
        for _ in range(10):
            sid = uuid.uuid4()
            stu_id = uuid.uuid4()
            db.add(
                SessionRating(
                    id=uuid.uuid4(),
                    session_id=sid,
                    rater_id=stu_id,
                    giver_id=uuid.UUID(giver_id),
                    score=5,
                    tags=["Helpful", "Clear feedback", "On time"],
                    is_flagged=False,
                    review_status="approved",
                    created_at=datetime.now(timezone.utc),
                )
            )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/givers/{giver_id}/rating-summary")
        assert res.status_code == 200
        data = res.json()
        # Verify rating, session_count, and tags are present
        assert data["session_count"] == 10
        assert data["rating"] == 4.67
        assert "Helpful" in data["top_tags"]
        assert "Clear feedback" in data["top_tags"]
        # Verify judgment tier labels (Rising, Trusted, Top Rated) are NOT in the schema
        assert "band" not in data
        assert "tier" not in data


@pytest.mark.asyncio
async def test_top_giver_leaderboard_per_institution_and_month():
    """
    Acceptance test 7:
    Top Giver leaderboard per institution and per month with fair-start boost.
    """
    transport = ASGITransport(app=app)
    college = f"DTU-{uuid.uuid4().hex[:6]}"
    giver_1 = uuid.uuid4()
    giver_2 = uuid.uuid4()

    async with async_session_maker() as db:
        db.add(
            GiverProfile(
                user_id=giver_1,
                full_name="Aarav Gupta",
                headline="Software Engineer at Microsoft",
                college=college,
                is_verified=True,
            )
        )
        db.add(
            GiverProfile(
                user_id=giver_2,
                full_name="Bhavna Singh",
                headline="Product Manager at Uber",
                college=college,
                is_verified=True,
            )
        )
        # Giver 1 has 2 ratings in 2026-10
        for _ in range(2):
            db.add(
                SessionRating(
                    id=uuid.uuid4(),
                    session_id=uuid.uuid4(),
                    rater_id=uuid.uuid4(),
                    giver_id=giver_1,
                    score=5,
                    tags=["Helpful"],
                    is_flagged=False,
                    review_status="approved",
                    created_at=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
                )
            )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Query leaderboard filtered by college and month
        res = await client.get(f"/leaderboard?college={college}&month=2026-10")
        assert res.status_code == 200
        entries = res.json()
        assert len(entries) >= 1
        top_entry = entries[0]
        assert top_entry["giver_id"] == str(giver_1)
        assert top_entry["full_name"] == "Aarav Gupta"
        assert top_entry["session_count"] == 2
        assert top_entry["rank"] == 1
        assert top_entry["ranking_score"] > 0
