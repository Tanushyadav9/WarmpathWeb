"""API Router for credits, wallets, plans, payments, and sponsored seats."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.modules.credits.schemas import (
    BuyCreditsInput,
    ClaimSponsoredSeatInput,
    FundSponsorPoolInput,
    PlanResponse,
    SetAffiliationInput,
    SponsorClaimResponse,
    SponsorDashboardResponse,
    SponsorPoolResponse,
    SubscribePlanInput,
    SubscriptionResponse,
    WalletResponse,
)
from app.modules.credits.service import credits_service

router = APIRouter(tags=["credits"])


@router.get("/plans", response_model=List[PlanResponse], summary="List subscription plans and credit allowances")
async def get_plans():
    return await credits_service.get_plans()


@router.get("/me/subscription", response_model=SubscriptionResponse, summary="Get authenticated user active subscription")
async def get_me_subscription(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.get_subscription(db, user_id)


@router.post("/plans/subscribe", response_model=SubscriptionResponse, summary="Subscribe to Free, Plus, or Pro plan")
async def post_plans_subscribe(
    body: SubscribePlanInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.subscribe_plan(db, user_id, body.plan_id, body.payment_id)


@router.post("/subscriptions", response_model=SubscriptionResponse, summary="Create/activate subscription (demo or razorpay)")
async def post_subscriptions(
    body: SubscribePlanInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.subscribe_plan(db, user_id, body.plan_id, body.payment_id)


@router.post("/credits/purchase", response_model=WalletResponse, summary="Directly purchase credits with mock/real payment")
async def post_credits_purchase(
    body: BuyCreditsInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.purchase_credits(db, user_id, body.credits, body.payment_id)


@router.get("/me/wallet", response_model=WalletResponse, summary="Get credit balance, held, earned, and transaction history")
async def get_me_wallet(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.get_wallet_details(db, user_id)


@router.get("/me/earnings", summary="Get earned credits and cashout availability")
async def get_me_earnings(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    wallet = await credits_service.get_wallet_details(db, user_id)
    return {
        "user_id": str(user_id),
        "earned_total": wallet.earned_total,
        "available_balance": wallet.available_balance,
        "karma_balance": wallet.karma_balance,
        "cashout_eligible": wallet.earned_total >= 10,
    }


@router.post("/me/affiliation", summary="Set or update user's college affiliation")
async def post_me_affiliation(
    body: SetAffiliationInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(get_current_user_id(request))
    await credits_service.set_user_affiliation(db, user_id, body.college)
    return {"status": "ok", "college": body.college}


@router.post("/sponsors/fund-pool", response_model=SponsorPoolResponse, summary="Sponsor or institution funds a credit pool")
async def post_sponsors_fund_pool(
    body: FundSponsorPoolInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sponsor_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.fund_sponsor_pool(
        db, sponsor_id, body.name, body.credits, body.target_college
    )


@router.post("/admin/sponsored-seats", response_model=SponsorPoolResponse, summary="Allocate sponsored seats for institution")
async def post_admin_sponsored_seats(
    body: FundSponsorPoolInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sponsor_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.fund_sponsor_pool(
        db, sponsor_id, body.name, body.credits, body.target_college
    )


@router.post("/sponsored-seats/claim", response_model=SponsorClaimResponse, summary="Eligible student claims sponsored seat")
async def post_sponsored_seats_claim(
    body: ClaimSponsoredSeatInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    student_id = uuid.UUID(get_current_user_id(request))
    pool_id = uuid.UUID(body.pool_id) if body.pool_id else None
    req_id = uuid.UUID(body.request_id) if body.request_id else None
    return await credits_service.claim_sponsored_seat(db, student_id, pool_id=pool_id, request_id=req_id)


@router.get("/sponsors/dashboard", response_model=SponsorDashboardResponse, summary="Sponsor dashboard with usage and pool stats")
async def get_sponsors_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sponsor_id = uuid.UUID(get_current_user_id(request))
    return await credits_service.get_sponsor_dashboard(db, sponsor_id)


@router.get("/sponsored-seats", summary="Check sponsored seat availability")
async def get_sponsored_seats(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    student_id = uuid.UUID(get_current_user_id(request))
    college = await credits_service.get_user_college(db, student_id)
    return {
        "student_id": str(student_id),
        "college": college,
        "has_sponsored_seat": True,
    }
