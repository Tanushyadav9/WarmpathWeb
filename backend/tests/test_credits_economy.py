"""
Acceptance tests for Single Credit Economy:
1. Ledger always balances to zero net.
2. Double-clicking release does not pay twice.
3. Decline refunds fully.
4. Same-college session never debits credits.
5. A sponsored student can book without paying.
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import func, select

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.ports import ports
from app.core.rate_limit import _in_memory_rate_limits
from app.main import app
from app.modules.availability.models import GiverAvailability
from app.modules.credits.models import (
    CreditLedger,
    SessionEscrow,
    SponsorPool,
    SponsoredClaim,
    Subscription,
    UserAffiliation,
    Wallet,
)
from app.modules.matching.models import GiverProfile
from app.modules.sessions.models import MentorshipRequest


@pytest.fixture(autouse=True)
def clear_limits():
    _in_memory_rate_limits.clear()


@pytest.mark.asyncio
async def test_ledger_always_balances_to_zero_net():
    """
    Acceptance test 1:
    Ledger always balances to zero net.
    Every transaction maintains strict double-entry equality (total debits == total credits),
    and the global sum of all credit_ledger rows is always 0.
    """
    transport = ASGITransport(app=app)
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    sponsor_user = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Purchase credits (user A buys 10 credits)
        res_buy = await client.post(
            "/credits/purchase",
            headers={"X-User-Id": user_a},
            json={"credits": 10},
        )
        assert res_buy.status_code == 200
        assert res_buy.json()["available_balance"] == 10

        # 2. Subscribe to Plus plan (user B gets 5 monthly credits)
        res_sub = await client.post(
            "/plans/subscribe",
            headers={"X-User-Id": user_b},
            json={"plan_id": "plus"},
        )
        assert res_sub.status_code == 200

        # 3. Sponsor funds a pool with 50 credits
        res_fund = await client.post(
            "/sponsors/fund-pool",
            headers={"X-User-Id": sponsor_user},
            json={"name": "Alumni Grant Fund", "credits": 50},
        )
        assert res_fund.status_code == 200
        pool_id = res_fund.json()["id"]

        # 4. User A reserves 5 credits in escrow for user B
        req_id = str(uuid.uuid4())
        await ports.credits.reserve(student_id=user_a, request_id=req_id, giver_id=user_b)

        # 5. Escrow is released (80% to giver B = 4 credits, 20% platform fee = 1 credit)
        await ports.credits.release(request_id=req_id)

        # 6. User B rewards karma for free session
        free_req_id = str(uuid.uuid4())
        await ports.credits.reward_karma(request_id=free_req_id, giver_id=user_b)

        # 7. Another request held and then refunded
        req_id_2 = str(uuid.uuid4())
        await ports.credits.reserve(student_id=user_a, request_id=req_id_2, giver_id=user_b)
        await ports.credits.refund(request_id=req_id_2, reason="Cancelled")

        # Global Invariant Check: SUM(amount) in credit_ledger MUST BE EXACTLY 0!
        async with async_session_maker() as session:
            sum_res = await session.execute(select(func.sum(CreditLedger.amount)))
            total_net_sum = sum_res.scalar()
            assert total_net_sum == 0, f"Ledger must balance to zero net, found {total_net_sum}"

            # Also verify every individual transaction balances to zero net
            tx_res = await session.execute(
                select(CreditLedger.transaction_id, func.sum(CreditLedger.amount)).group_by(
                    CreditLedger.transaction_id
                )
            )
            for tx_id, tx_sum in tx_res.all():
                assert tx_sum == 0, f"Transaction {tx_id} does not balance to zero net (sum={tx_sum})"


@pytest.mark.asyncio
async def test_double_clicking_release_does_not_pay_twice():
    """
    Acceptance test 2:
    Double-clicking release does not pay twice.
    The release operation is strictly idempotent.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Give student 10 credits
        await client.post(
            "/credits/purchase",
            headers={"X-User-Id": student_id},
            json={"credits": 10},
        )

        # Setup cross-college affiliation
        await client.post("/me/affiliation", headers={"X-User-Id": student_id}, json={"college": "DTU"})
        await client.post("/me/affiliation", headers={"X-User-Id": giver_id}, json={"college": "IIT Bombay"})

        # Hold 5 credits in escrow
        await ports.credits.reserve(student_id=student_id, request_id=request_id, giver_id=giver_id)

        # Verify initial giver wallet
        giver_res_initial = await client.get("/me/wallet", headers={"X-User-Id": giver_id})
        assert giver_res_initial.json()["available_balance"] == 0

        # First release call -> Giver gets 4 credits (80% of 5)
        await ports.credits.release(request_id=request_id)
        giver_res_first = await client.get("/me/wallet", headers={"X-User-Id": giver_id})
        assert giver_res_first.json()["available_balance"] == 4
        assert giver_res_first.json()["earned_total"] == 4

        # Second release call (simulating double-click or replay) -> MUST NOT PAY TWICE!
        await ports.credits.release(request_id=request_id)
        giver_res_second = await client.get("/me/wallet", headers={"X-User-Id": giver_id})
        assert giver_res_second.json()["available_balance"] == 4, "Giver must NOT receive double payout"
        assert giver_res_second.json()["earned_total"] == 4

        # Third release call -> still 4
        await ports.credits.release(request_id=request_id)
        giver_res_third = await client.get("/me/wallet", headers={"X-User-Id": giver_id})
        assert giver_res_third.json()["available_balance"] == 4

        # Verify ledger still perfectly balanced
        async with async_session_maker() as session:
            sum_res = await session.execute(select(func.sum(CreditLedger.amount)))
            assert sum_res.scalar() == 0


@pytest.mark.asyncio
async def test_decline_refunds_fully():
    """
    Acceptance test 3:
    Decline refunds fully.
    Credits moved to Held on request acceptance are fully refunded on decline.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed giver availability
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

        # Set cross colleges
        await client.post("/me/affiliation", headers={"X-User-Id": student_id}, json={"college": "NSUT"})
        await client.post("/me/affiliation", headers={"X-User-Id": giver_id}, json={"college": "BITS Pilani"})

        # Student purchases 10 credits
        await client.post(
            "/credits/purchase",
            headers={"X-User-Id": student_id},
            json={"credits": 10},
        )

        w_before = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert w_before.json()["available_balance"] == 10
        assert w_before.json()["held_balance"] == 0

        # Student creates mentorship request
        res_req = await client.post(
            "/requests",
            headers={"X-User-Id": student_id},
            json={"giver_id": giver_id, "intent": "Cross-college system design review"},
        )
        req_id = res_req.json()["id"]

        # Giver accepts request -> Escrow hold moves 5 credits to held!
        res_acc = await client.post(f"/requests/{req_id}/accept", headers={"X-User-Id": giver_id})
        assert res_acc.status_code == 200

        w_held = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert w_held.json()["available_balance"] == 5
        assert w_held.json()["held_balance"] == 5

        # Giver declines request with reason -> Full refund!
        res_dec = await client.post(
            f"/requests/{req_id}/decline",
            headers={"X-User-Id": giver_id},
            json={"reason": "Emergency production issue this week."},
        )
        assert res_dec.status_code == 200

        # Verify student available balance is fully restored to 10 and held is 0
        w_after = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert w_after.json()["available_balance"] == 10, "Student must be fully refunded 10 credits"
        assert w_after.json()["held_balance"] == 0

        # Verify escrow status in DB
        async with async_session_maker() as session:
            esc_res = await session.execute(
                select(SessionEscrow).where(SessionEscrow.request_id == uuid.UUID(req_id))
            )
            escrow = esc_res.scalar_one_or_none()
            assert escrow is not None
            assert escrow.status == "refunded"


@pytest.mark.asyncio
async def test_same_college_session_never_debits_credits():
    """
    Acceptance test 4:
    Same-college session never debits credits.
    Free connections between students and givers of the same college cost 0 credits.
    On completion and rating, giver earns karma credits.
    """
    transport = ASGITransport(app=app)
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed giver availability
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

        # Both users belong to the SAME college: "VIPS-TC"
        await client.post("/me/affiliation", headers={"X-User-Id": student_id}, json={"college": "VIPS-TC"})
        await client.post("/me/affiliation", headers={"X-User-Id": giver_id}, json={"college": "VIPS-TC"})

        # Student starts with 5 credits
        await client.post(
            "/credits/purchase",
            headers={"X-User-Id": student_id},
            json={"credits": 5},
        )

        w_start = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert w_start.json()["available_balance"] == 5

        # Check access via port: cost must be 0!
        access = await ports.credits.can_access(student_id, giver_id)
        assert access["is_same_college"] is True
        assert access["cost"] == 0

        # Student creates request
        res_req = await client.post(
            "/requests",
            headers={"X-User-Id": student_id},
            json={"giver_id": giver_id, "intent": "Alumni networking & mock interview"},
        )
        req_id = res_req.json()["id"]

        # Giver accepts request -> ZERO credits held!
        res_acc = await client.post(f"/requests/{req_id}/accept", headers={"X-User-Id": giver_id})
        assert res_acc.status_code == 200

        w_mid = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert w_mid.json()["available_balance"] == 5, "Same-college session must never debit available balance"
        assert w_mid.json()["held_balance"] == 0, "Same-college session must never hold credits"

        # Complete and rate session
        await client.post(f"/sessions/{req_id}/complete", headers={"X-User-Id": student_id})
        res_rate = await client.post(
            f"/sessions/{req_id}/rating",
            headers={"X-User-Id": student_id},
            json={"score": 5, "comment": "Great same-college mentorship!"},
        )
        assert res_rate.status_code == 200

        # Student still has 5 credits!
        w_end = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert w_end.json()["available_balance"] == 5

        # Giver has earned 1 karma credit!
        giver_w = await client.get("/me/wallet", headers={"X-User-Id": giver_id})
        assert giver_w.json()["karma_balance"] >= 1, "Giver must earn karma credits for free sessions"


@pytest.mark.asyncio
async def test_sponsored_student_can_book_without_paying():
    """
    Acceptance test 5:
    A sponsored student can book without paying.
    Sponsor funds pool, student with 0 credits claims sponsored seat,
    and books a cross-college session funded from the sponsor pool.
    """
    transport = ASGITransport(app=app)
    sponsor_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed giver availability
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

        # Set cross-colleges
        await client.post("/me/affiliation", headers={"X-User-Id": student_id}, json={"college": "Tier3 College"})
        await client.post("/me/affiliation", headers={"X-User-Id": giver_id}, json={"college": "Top Tech Alumni"})

        # Step 1: Sponsor funds a pool with 25 credits
        res_fund = await client.post(
            "/sponsors/fund-pool",
            headers={"X-User-Id": sponsor_id},
            json={"name": "Rural & Tier-3 Student Fellowship", "credits": 25},
        )
        assert res_fund.status_code == 200
        pool_id = res_fund.json()["id"]

        # Step 2: Student has 0 available credits!
        student_w_before = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert student_w_before.json()["available_balance"] == 0

        # Step 3: Student claims sponsored seat from the pool
        res_claim = await client.post(
            "/sponsored-seats/claim",
            headers={"X-User-Id": student_id},
            json={"pool_id": pool_id},
        )
        assert res_claim.status_code == 200
        claim_data = res_claim.json()
        assert claim_data["credits"] == 5
        assert claim_data["status"] == "claimed"

        # Check access via port confirms sponsored allowance
        access = await ports.credits.can_access(student_id, giver_id)
        assert access["allowed"] is True
        assert access["is_sponsored"] is True

        # Step 4: Student requests cross-college mentorship without paying any money!
        res_req = await client.post(
            "/requests",
            headers={"X-User-Id": student_id},
            json={"giver_id": giver_id, "intent": "Sponsored career transition guidance"},
        )
        assert res_req.status_code == 200
        req_id = res_req.json()["id"]

        # Step 5: Giver accepts request -> Escrow held from sponsor pool, NOT from student wallet
        res_acc = await client.post(f"/requests/{req_id}/accept", headers={"X-User-Id": giver_id})
        assert res_acc.status_code == 200

        # Student personal balance remains 0 (student did NOT pay anything)
        student_w_after = await client.get("/me/wallet", headers={"X-User-Id": student_id})
        assert student_w_after.json()["available_balance"] == 0
        assert student_w_after.json()["held_balance"] == 0

        # Step 6: Complete and rate session
        await client.post(f"/sessions/{req_id}/complete", headers={"X-User-Id": student_id})
        await client.post(
            f"/sessions/{req_id}/rating",
            headers={"X-User-Id": student_id},
            json={"score": 5, "comment": "Life changing mentorship session!"},
        )

        # Giver received payout (4 credits)
        giver_w = await client.get("/me/wallet", headers={"X-User-Id": giver_id})
        assert giver_w.json()["available_balance"] == 4

        # Step 7: Check sponsor dashboard shows 1 claim, 5 allocated credits, 20 remaining
        res_dash = await client.get("/sponsors/dashboard", headers={"X-User-Id": sponsor_id})
        assert res_dash.status_code == 200
        dash = res_dash.json()
        assert dash["total_funded"] == 25
        assert dash["total_allocated"] == 5
        assert dash["total_remaining"] == 20
        assert len(dash["claims"]) == 1
        assert dash["claims"][0]["student_id"] == student_id

        # Verify net-zero balance invariant
        async with async_session_maker() as session:
            sum_res = await session.execute(select(func.sum(CreditLedger.amount)))
            assert sum_res.scalar() == 0
