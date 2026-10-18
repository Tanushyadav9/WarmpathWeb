"""Business logic service and CreditsPort implementation for credits economy, wallets, ledger, and escrow."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker, OutboxEvent
from app.core.errors import AppError
from app.core.ports import CreditsPort
from app.modules.credits.models import (
    CreditLedger,
    SessionEscrow,
    SponsorPool,
    SponsoredClaim,
    Subscription,
    UserAffiliation,
    Wallet,
)
from app.modules.credits.payment_adapter import payment_adapter
from app.modules.credits.schemas import (
    LedgerEntryResponse,
    PlanResponse,
    SponsorClaimResponse,
    SponsorDashboardResponse,
    SponsorPoolResponse,
    SubscriptionResponse,
    WalletResponse,
)
from app.modules.matching.models import GiverProfile

PLANS = [
    {
        "id": "free",
        "name": "Free Campus Plan",
        "price_inr": settings.PLAN_CAMPUS_PRICE,
        "monthly_credits": settings.PLAN_CAMPUS_CREDITS,
        "description": "Unlimited free same-college mentorship sessions.",
        "features": ["Same-college free connections", "Direct in-app messaging", "Campus community access"],
    },
    {
        "id": "plus",
        "name": "Plus Plan",
        "price_inr": settings.PLAN_STANDARD_PRICE,
        "monthly_credits": settings.CROSS_COLLEGE_CREDIT_COST,  # 5 credits = 1 cross-college session
        "description": "Includes 1 monthly cross-college session (5 credits) plus unlimited campus connections.",
        "features": ["5 monthly credits", "Cross-college booking", "Priority calendar slot matching"],
    },
    {
        "id": "pro",
        "name": "Pro Plan",
        "price_inr": settings.PLAN_PREMIUM_PRICE,
        "monthly_credits": 20,  # 4 cross-college sessions
        "description": "Includes 20 monthly credits (4 cross-college sessions) and top alumni matching.",
        "features": ["20 monthly credits", "Unlimited cross-college bookings", "Top Rated giver priority"],
    },
]


class CreditsService:
    async def get_or_create_wallet(self, db: AsyncSession, user_id: uuid.UUID) -> Wallet:
        result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            wallet = Wallet(
                id=uuid.uuid4(),
                user_id=user_id,
                available_balance=0,
                held_balance=0,
                earned_total=0,
                karma_balance=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)
        return wallet

    def post_double_entry(
        self,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        operation: str,
        entries: List[Dict[str, Any]],
        reference_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> None:
        """
        Posts balanced double-entry rows to CreditLedger.
        Strict invariant: sum of amounts must equal 0, ensuring net-zero balance!
        """
        net_sum = sum(e["amount"] for e in entries)
        if net_sum != 0:
            raise ValueError(f"Ledger entries must balance to zero net, got {net_sum}")

        now = datetime.now(timezone.utc)
        for e in entries:
            ledger_entry = CreditLedger(
                id=uuid.uuid4(),
                transaction_id=transaction_id,
                account_id=e["account_id"],
                user_id=e.get("user_id"),
                operation=operation,
                amount=e["amount"],
                reference_id=reference_id,
                idempotency_key=idempotency_key,
                description=e["description"],
                created_at=now,
            )
            db.add(ledger_entry)

    async def get_plans(self) -> List[PlanResponse]:
        return [PlanResponse(**p) for p in PLANS]

    async def get_subscription(self, db: AsyncSession, user_id: uuid.UUID) -> SubscriptionResponse:
        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = result.scalar_one_or_none()
        if not sub:
            # Default free plan
            sub = Subscription(
                id=uuid.uuid4(),
                user_id=user_id,
                plan_id="free",
                status="active",
                monthly_credits=0,
                created_at=datetime.now(timezone.utc),
            )
            db.add(sub)
            await db.commit()
            await db.refresh(sub)

        return SubscriptionResponse(
            id=str(sub.id),
            user_id=str(sub.user_id),
            plan_id=sub.plan_id,
            status=sub.status,
            monthly_credits=sub.monthly_credits,
            renews_at=sub.renews_at.isoformat() if sub.renews_at else None,
            created_at=sub.created_at.isoformat(),
        )

    async def subscribe_plan(
        self, db: AsyncSession, user_id: uuid.UUID, plan_id: str, payment_id: Optional[str] = None
    ) -> SubscriptionResponse:
        plan = next((p for p in PLANS if p["id"] == plan_id.lower()), None)
        if not plan:
            raise AppError("plan_not_found", f"Plan '{plan_id}' does not exist.", status_code=404)

        if plan["price_inr"] > 0:
            # Verify payment with adapter (mock in demo mode)
            verified = await payment_adapter.verify_payment(
                order_id=f"order_{uuid.uuid4().hex[:12]}",
                payment_id=payment_id or f"demo_pay_{uuid.uuid4().hex[:12]}",
            )
            if not verified:
                raise AppError("payment_failed", "Payment verification failed.", status_code=400)

        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        monthly_credits = plan["monthly_credits"]

        if not sub:
            sub = Subscription(
                id=uuid.uuid4(),
                user_id=user_id,
                plan_id=plan["id"],
                status="active",
                monthly_credits=monthly_credits,
                renews_at=now + timedelta(days=30),
                created_at=now,
            )
            db.add(sub)
        else:
            sub.plan_id = plan["id"]
            sub.monthly_credits = monthly_credits
            sub.renews_at = now + timedelta(days=30)

        # Grant monthly plan credits via balanced double-entry ledger
        if monthly_credits > 0:
            wallet = await self.get_or_create_wallet(db, user_id)
            wallet.available_balance += monthly_credits
            wallet.updated_at = now

            tx_id = uuid.uuid4()
            self.post_double_entry(
                db,
                transaction_id=tx_id,
                operation="purchase",
                reference_id=str(sub.id),
                idempotency_key=f"sub_grant:{sub.id}:{now.strftime('%Y%m')}",
                entries=[
                    {
                        "account_id": "@mint_system",
                        "user_id": None,
                        "amount": -monthly_credits,
                        "description": f"Subscription {plan['name']} credits grant",
                    },
                    {
                        "account_id": str(user_id),
                        "user_id": user_id,
                        "amount": monthly_credits,
                        "description": f"Subscription {plan['name']} monthly credits",
                    },
                ],
            )

        await db.commit()
        await db.refresh(sub)
        return SubscriptionResponse(
            id=str(sub.id),
            user_id=str(sub.user_id),
            plan_id=sub.plan_id,
            status=sub.status,
            monthly_credits=sub.monthly_credits,
            renews_at=sub.renews_at.isoformat() if sub.renews_at else None,
            created_at=sub.created_at.isoformat(),
        )

    async def purchase_credits(
        self, db: AsyncSession, user_id: uuid.UUID, credits: int, payment_id: Optional[str] = None
    ) -> WalletResponse:
        price_per_credit = 60  # INR per credit
        total_inr = credits * price_per_credit

        verified = await payment_adapter.verify_payment(
            order_id=f"order_{uuid.uuid4().hex[:12]}",
            payment_id=payment_id or f"demo_pay_{uuid.uuid4().hex[:12]}",
        )
        if not verified:
            raise AppError("payment_failed", "Payment verification failed.", status_code=400)

        now = datetime.now(timezone.utc)
        wallet = await self.get_or_create_wallet(db, user_id)
        wallet.available_balance += credits
        wallet.updated_at = now

        tx_id = uuid.uuid4()
        self.post_double_entry(
            db,
            transaction_id=tx_id,
            operation="purchase",
            reference_id=str(tx_id),
            idempotency_key=f"purchase:{tx_id}",
            entries=[
                {
                    "account_id": "@mint_system",
                    "user_id": None,
                    "amount": -credits,
                    "description": f"Direct purchase of {credits} credits for ₹{total_inr}",
                },
                {
                    "account_id": str(user_id),
                    "user_id": user_id,
                    "amount": credits,
                    "description": f"Purchased {credits} credits",
                },
            ],
        )
        await db.commit()
        await db.refresh(wallet)
        return await self.get_wallet_details(db, user_id)

    async def get_wallet_details(self, db: AsyncSession, user_id: uuid.UUID) -> WalletResponse:
        wallet = await self.get_or_create_wallet(db, user_id)

        # Get recent transactions
        res = await db.execute(
            select(CreditLedger)
            .where(CreditLedger.account_id == str(user_id))
            .order_by(CreditLedger.created_at.desc())
            .limit(50)
        )
        entries = res.scalars().all()

        history = [
            LedgerEntryResponse(
                id=str(e.id),
                transaction_id=str(e.transaction_id),
                operation=e.operation,
                amount=e.amount,
                description=e.description,
                reference_id=e.reference_id,
                created_at=e.created_at.isoformat(),
            )
            for e in entries
        ]

        return WalletResponse(
            user_id=str(wallet.user_id),
            available_balance=wallet.available_balance,
            held_balance=wallet.held_balance,
            earned_total=wallet.earned_total,
            karma_balance=wallet.karma_balance,
            history=history,
        )

    async def get_user_college(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[str]:
        # 1. Check UserAffiliation
        res_aff = await db.execute(
            select(UserAffiliation).where(UserAffiliation.user_id == user_id)
        )
        aff = res_aff.scalar_one_or_none()
        if aff and aff.college:
            return aff.college

        # 2. Check GiverProfile
        res_prof = await db.execute(
            select(GiverProfile).where(GiverProfile.user_id == user_id)
        )
        prof = res_prof.scalar_one_or_none()
        if prof and prof.college:
            return prof.college

        return None

    async def set_user_affiliation(self, db: AsyncSession, user_id: uuid.UUID, college: str) -> None:
        res_aff = await db.execute(
            select(UserAffiliation).where(UserAffiliation.user_id == user_id)
        )
        aff = res_aff.scalar_one_or_none()
        if not aff:
            aff = UserAffiliation(
                id=uuid.uuid4(),
                user_id=user_id,
                college=college,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(aff)
        else:
            aff.college = college
        await db.commit()

    async def can_access(
        self, db: AsyncSession, student_id: uuid.UUID, giver_id: uuid.UUID
    ) -> Dict[str, Any]:
        student_college = await self.get_user_college(db, student_id)
        giver_college = await self.get_user_college(db, giver_id)

        # Cross-college only when both colleges are known and different
        is_cross_college = (
            student_college is not None
            and giver_college is not None
            and student_college.strip().lower() != giver_college.strip().lower()
        )

        if not is_cross_college:
            return {
                "allowed": True,
                "reason": "Same-college / campus connection: free of charge (0 credits).",
                "plan": "campus_free",
                "cost": 0,
                "is_same_college": True,
                "is_sponsored": False,
            }

        # Cross-college session costs credits
        cost = settings.CROSS_COLLEGE_CREDIT_COST

        # Check if student has active sponsored claim
        res_claim = await db.execute(
            select(SponsoredClaim).where(
                SponsoredClaim.student_id == student_id,
                SponsoredClaim.status == "claimed",
            )
        )
        active_claim = res_claim.scalar_one_or_none()
        if active_claim:
            return {
                "allowed": True,
                "reason": "Sponsored seat available for cross-college mentorship.",
                "plan": "sponsored",
                "cost": cost,
                "is_same_college": False,
                "is_sponsored": True,
            }

        # Check student wallet balance
        wallet = await self.get_or_create_wallet(db, student_id)
        if wallet.available_balance >= cost:
            return {
                "allowed": True,
                "reason": f"Cross-college mentorship costs {cost} credits.",
                "plan": "credits",
                "cost": cost,
                "is_same_college": False,
                "is_sponsored": False,
            }

        return {
            "allowed": False,
            "reason": f"Cross-college mentorship requires {cost} credits. Please subscribe, buy credits, or claim a sponsored seat.",
            "plan": "none",
            "cost": cost,
            "is_same_college": False,
            "is_sponsored": False,
        }

    async def reserve_credits(
        self, db: AsyncSession, student_id: uuid.UUID, request_id: uuid.UUID, giver_id: uuid.UUID
    ) -> Optional[SessionEscrow]:
        """
        Idempotent escrow hold on request acceptance.
        If same-college: zero credits, no hold created.
        If cross-college: credits move from available to held in escrow.
        """
        # Idempotency check: if escrow already exists for this request_id, return it
        res_esc = await db.execute(
            select(SessionEscrow).where(SessionEscrow.request_id == request_id)
        )
        existing = res_esc.scalar_one_or_none()
        if existing:
            return existing

        access_info = await self.can_access(db, student_id, giver_id)
        if access_info.get("is_same_college", False):
            # Same college is completely free of charge (zero credits)
            return None

        cost = settings.CROSS_COLLEGE_CREDIT_COST
        tx_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Check if sponsored claim available
        res_claim = await db.execute(
            select(SponsoredClaim).where(
                SponsoredClaim.student_id == student_id,
                SponsoredClaim.status == "claimed",
            )
        )
        claim = res_claim.scalar_one_or_none()
        sponsor_pool_id = None

        if claim:
            sponsor_pool_id = claim.pool_id
            claim.status = "used"
            claim.request_id = request_id

            # Double-entry ledger: from sponsor pool to escrow
            self.post_double_entry(
                db,
                transaction_id=tx_id,
                operation="hold",
                reference_id=str(request_id),
                idempotency_key=f"hold:{request_id}",
                entries=[
                    {
                        "account_id": f"@sponsor_pool_{sponsor_pool_id}",
                        "user_id": None,
                        "amount": -cost,
                        "description": f"Sponsored seat hold for request {request_id}",
                    },
                    {
                        "account_id": "@escrow",
                        "user_id": None,
                        "amount": cost,
                        "description": f"Escrow held for request {request_id}",
                    },
                ],
            )
        else:
            wallet = await self.get_or_create_wallet(db, student_id)
            if wallet.available_balance < cost:
                raise AppError(
                    "insufficient_credits",
                    f"Insufficient credits for cross-college mentorship session (requires {cost} credits).",
                    status_code=400,
                )

            # Move credits from student's available to held
            wallet.available_balance -= cost
            wallet.held_balance += cost
            wallet.updated_at = now

            self.post_double_entry(
                db,
                transaction_id=tx_id,
                operation="hold",
                reference_id=str(request_id),
                idempotency_key=f"hold:{request_id}",
                entries=[
                    {
                        "account_id": str(student_id),
                        "user_id": student_id,
                        "amount": -cost,
                        "description": f"Held {cost} credits in escrow for request {request_id}",
                    },
                    {
                        "account_id": "@escrow",
                        "user_id": None,
                        "amount": cost,
                        "description": f"Escrow held for request {request_id}",
                    },
                ],
            )

        escrow = SessionEscrow(
            id=uuid.uuid4(),
            request_id=request_id,
            student_id=student_id,
            giver_id=giver_id,
            amount=cost,
            sponsor_pool_id=sponsor_pool_id,
            status="held",
            held_at=now,
        )
        db.add(escrow)
        await db.commit()
        await db.refresh(escrow)
        return escrow

    async def release_credits(self, db: AsyncSession, request_id: uuid.UUID) -> None:
        """
        Idempotent escrow release to giver (80%) and platform fee (20%).
        Double-clicking release does not pay twice!
        """
        res_esc = await db.execute(
            select(SessionEscrow).where(SessionEscrow.request_id == request_id)
        )
        escrow = res_esc.scalar_one_or_none()
        if not escrow:
            # Free session (no escrow record)
            return

        # Double-click guard: do not pay twice
        if escrow.status == "released":
            return
        if escrow.status != "held":
            return

        cost = escrow.amount
        giver_amount = int(round(cost * settings.GIVER_PAYOUT_SHARE))
        platform_fee = cost - giver_amount
        now = datetime.now(timezone.utc)
        tx_id = uuid.uuid4()

        self.post_double_entry(
            db,
            transaction_id=tx_id,
            operation="release",
            reference_id=str(request_id),
            idempotency_key=f"release:{request_id}",
            entries=[
                {
                    "account_id": "@escrow",
                    "user_id": None,
                    "amount": -cost,
                    "description": f"Escrow release for completed session {request_id}",
                },
                {
                    "account_id": str(escrow.giver_id),
                    "user_id": escrow.giver_id,
                    "amount": giver_amount,
                    "description": f"Session earnings (80%) for request {request_id}",
                },
                {
                    "account_id": "@platform_fee",
                    "user_id": None,
                    "amount": platform_fee,
                    "description": f"Platform fee (20%) for request {request_id}",
                },
            ],
        )

        escrow.status = "released"
        escrow.released_at = now

        # Update giver wallet (earn credits by giving time)
        giver_wallet = await self.get_or_create_wallet(db, escrow.giver_id)
        giver_wallet.available_balance += giver_amount
        giver_wallet.earned_total += giver_amount
        giver_wallet.updated_at = now

        # If student paid with personal credits, clear held balance
        if not escrow.sponsor_pool_id:
            student_wallet = await self.get_or_create_wallet(db, escrow.student_id)
            student_wallet.held_balance -= cost
            student_wallet.updated_at = now

        await db.commit()

    async def refund_credits(
        self, db: AsyncSession, request_id: uuid.UUID, reason: Optional[str] = None
    ) -> None:
        """
        Idempotent full refund on decline, cancellation, or no-show.
        """
        res_esc = await db.execute(
            select(SessionEscrow).where(SessionEscrow.request_id == request_id)
        )
        escrow = res_esc.scalar_one_or_none()
        if not escrow:
            return

        if escrow.status == "refunded":
            return
        if escrow.status != "held":
            return

        cost = escrow.amount
        now = datetime.now(timezone.utc)
        tx_id = uuid.uuid4()
        refund_note = reason or "Declined / cancelled session refund"

        if escrow.sponsor_pool_id:
            # Refund to sponsor pool
            self.post_double_entry(
                db,
                transaction_id=tx_id,
                operation="refund",
                reference_id=str(request_id),
                idempotency_key=f"refund:{request_id}",
                entries=[
                    {
                        "account_id": "@escrow",
                        "user_id": None,
                        "amount": -cost,
                        "description": f"Escrow refund for request {request_id}: {refund_note}",
                    },
                    {
                        "account_id": f"@sponsor_pool_{escrow.sponsor_pool_id}",
                        "user_id": None,
                        "amount": cost,
                        "description": f"Refund to sponsor pool for request {request_id}",
                    },
                ],
            )
            pool_res = await db.execute(
                select(SponsorPool).where(SponsorPool.id == escrow.sponsor_pool_id)
            )
            pool = pool_res.scalar_one_or_none()
            if pool:
                pool.allocated_credits -= cost
                pool.remaining_credits += cost
        else:
            # Refund to student wallet
            student_wallet = await self.get_or_create_wallet(db, escrow.student_id)
            student_wallet.held_balance -= cost
            student_wallet.available_balance += cost
            student_wallet.updated_at = now

            self.post_double_entry(
                db,
                transaction_id=tx_id,
                operation="refund",
                reference_id=str(request_id),
                idempotency_key=f"refund:{request_id}",
                entries=[
                    {
                        "account_id": "@escrow",
                        "user_id": None,
                        "amount": -cost,
                        "description": f"Escrow refund for request {request_id}: {refund_note}",
                    },
                    {
                        "account_id": str(escrow.student_id),
                        "user_id": escrow.student_id,
                        "amount": cost,
                        "description": f"Full refund for request {request_id}: {refund_note}",
                    },
                ],
            )

        escrow.status = "refunded"
        escrow.refunded_at = now
        await db.commit()

    async def reward_karma(
        self, db: AsyncSession, request_id: uuid.UUID, giver_id: uuid.UUID
    ) -> None:
        """
        Rewards karma credits to giver for completing free same-college sessions.
        Idempotent per request_id.
        """
        res_ledger = await db.execute(
            select(CreditLedger).where(
                CreditLedger.reference_id == str(request_id),
                CreditLedger.operation == "karma",
            )
        )
        if res_ledger.scalar_one_or_none():
            return  # Already rewarded

        karma_pts = settings.FREE_SESSION_KARMA_CREDITS
        tx_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        self.post_double_entry(
            db,
            transaction_id=tx_id,
            operation="karma",
            reference_id=str(request_id),
            idempotency_key=f"karma:{request_id}",
            entries=[
                {
                    "account_id": "@karma_system",
                    "user_id": None,
                    "amount": -karma_pts,
                    "description": f"Karma reward for free mentorship session {request_id}",
                },
                {
                    "account_id": str(giver_id),
                    "user_id": giver_id,
                    "amount": karma_pts,
                    "description": f"Karma points earned for mentoring request {request_id}",
                },
            ],
        )

        giver_wallet = await self.get_or_create_wallet(db, giver_id)
        giver_wallet.karma_balance += karma_pts
        giver_wallet.updated_at = now
        await db.commit()

    async def fund_sponsor_pool(
        self,
        db: AsyncSession,
        sponsor_id: uuid.UUID,
        name: str,
        credits: int,
        target_college: Optional[str] = None,
    ) -> SponsorPoolResponse:
        pool_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        pool = SponsorPool(
            id=pool_id,
            name=name,
            sponsor_id=sponsor_id,
            target_college=target_college,
            total_funded_credits=credits,
            allocated_credits=0,
            remaining_credits=credits,
            created_at=now,
        )
        db.add(pool)

        tx_id = uuid.uuid4()
        self.post_double_entry(
            db,
            transaction_id=tx_id,
            operation="sponsor_fund",
            reference_id=str(pool_id),
            idempotency_key=f"fund:{pool_id}",
            entries=[
                {
                    "account_id": "@mint_system",
                    "user_id": None,
                    "amount": -credits,
                    "description": f"Sponsor funded pool: {name}",
                },
                {
                    "account_id": f"@sponsor_pool_{pool_id}",
                    "user_id": None,
                    "amount": credits,
                    "description": f"Capitalized sponsor pool: {name}",
                },
            ],
        )
        await db.commit()
        await db.refresh(pool)
        return SponsorPoolResponse(
            id=str(pool.id),
            name=pool.name,
            sponsor_id=str(pool.sponsor_id),
            target_college=pool.target_college,
            total_funded_credits=pool.total_funded_credits,
            allocated_credits=pool.allocated_credits,
            remaining_credits=pool.remaining_credits,
            created_at=pool.created_at.isoformat(),
        )

    async def claim_sponsored_seat(
        self,
        db: AsyncSession,
        student_id: uuid.UUID,
        pool_id: Optional[uuid.UUID] = None,
        request_id: Optional[uuid.UUID] = None,
    ) -> SponsorClaimResponse:
        cost = settings.CROSS_COLLEGE_CREDIT_COST
        student_college = await self.get_user_college(db, student_id)

        # Find eligible pool
        if pool_id:
            res_pool = await db.execute(
                select(SponsorPool).where(
                    SponsorPool.id == pool_id,
                    SponsorPool.remaining_credits >= cost,
                )
            )
            pool = res_pool.scalar_one_or_none()
        else:
            # Find any open pool matching college or open to all
            query = select(SponsorPool).where(SponsorPool.remaining_credits >= cost)
            res_pools = await db.execute(query)
            pools = res_pools.scalars().all()
            pool = None
            if student_college:
                pool = next(
                    (p for p in pools if p.target_college and p.target_college.lower() == student_college.lower()),
                    None,
                )
            if not pool and pools:
                pool = next((p for p in pools if not p.target_college), pools[0])

        if not pool:
            raise AppError("no_sponsored_seats", "No sponsored credits currently available.", status_code=400)

        # Allocate credits from pool
        pool.allocated_credits += cost
        pool.remaining_credits -= cost

        claim = SponsoredClaim(
            id=uuid.uuid4(),
            pool_id=pool.id,
            student_id=student_id,
            request_id=request_id,
            credits=cost,
            status="claimed",
            claimed_at=datetime.now(timezone.utc),
        )
        db.add(claim)
        await db.commit()
        await db.refresh(claim)

        return SponsorClaimResponse(
            id=str(claim.id),
            pool_id=str(claim.pool_id),
            student_id=str(claim.student_id),
            request_id=str(claim.request_id) if claim.request_id else None,
            credits=claim.credits,
            status=claim.status,
            claimed_at=claim.claimed_at.isoformat(),
        )

    async def get_sponsor_dashboard(
        self, db: AsyncSession, sponsor_id: uuid.UUID
    ) -> SponsorDashboardResponse:
        res_pools = await db.execute(
            select(SponsorPool).where(SponsorPool.sponsor_id == sponsor_id)
        )
        pools = res_pools.scalars().all()
        pool_ids = [p.id for p in pools]

        claims: List[SponsoredClaim] = []
        if pool_ids:
            res_claims = await db.execute(
                select(SponsoredClaim).where(SponsoredClaim.pool_id.in_(pool_ids))
            )
            claims = res_claims.scalars().all()

        total_funded = sum(p.total_funded_credits for p in pools)
        total_allocated = sum(p.allocated_credits for p in pools)
        total_remaining = sum(p.remaining_credits for p in pools)

        return SponsorDashboardResponse(
            sponsor_id=str(sponsor_id),
            total_pools=len(pools),
            total_funded=total_funded,
            total_allocated=total_allocated,
            total_remaining=total_remaining,
            pools=[
                SponsorPoolResponse(
                    id=str(p.id),
                    name=p.name,
                    sponsor_id=str(p.sponsor_id),
                    target_college=p.target_college,
                    total_funded_credits=p.total_funded_credits,
                    allocated_credits=p.allocated_credits,
                    remaining_credits=p.remaining_credits,
                    created_at=p.created_at.isoformat(),
                )
                for p in pools
            ],
            claims=[
                SponsorClaimResponse(
                    id=str(c.id),
                    pool_id=str(c.pool_id),
                    student_id=str(c.student_id),
                    request_id=str(c.request_id) if c.request_id else None,
                    credits=c.credits,
                    status=c.status,
                    claimed_at=c.claimed_at.isoformat(),
                )
                for c in claims
            ],
        )


class CreditsPortImpl(CreditsPort):
    def __init__(self, service: CreditsService):
        self.service = service

    async def can_access(self, student_id: str, giver_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            sid = uuid.UUID(student_id)
            gid = uuid.UUID(giver_id)
            return await self.service.can_access(db, sid, gid)

    async def reserve(self, student_id: str, request_id: str, giver_id: str) -> None:
        async with async_session_maker() as db:
            sid = uuid.UUID(student_id)
            rid = uuid.UUID(request_id)
            gid = uuid.UUID(giver_id)
            await self.service.reserve_credits(db, sid, rid, gid)

    async def release(self, request_id: str) -> None:
        async with async_session_maker() as db:
            rid = uuid.UUID(request_id)
            await self.service.release_credits(db, rid)

    async def refund(self, request_id: str, reason: str) -> None:
        async with async_session_maker() as db:
            rid = uuid.UUID(request_id)
            await self.service.refund_credits(db, rid, reason)

    async def reward_karma(self, request_id: str, giver_id: str) -> None:
        async with async_session_maker() as db:
            rid = uuid.UUID(request_id)
            gid = uuid.UUID(giver_id)
            await self.service.reward_karma(db, rid, gid)


credits_service = CreditsService()
credits_port_instance = CreditsPortImpl(credits_service)
