"""Pydantic schemas for wallets, subscriptions, credit ledger, and sponsor pools."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    id: str
    name: str
    price_inr: int
    monthly_credits: int
    description: str
    features: List[str] = []


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: str
    monthly_credits: int
    renews_at: Optional[str] = None
    created_at: str


class LedgerEntryResponse(BaseModel):
    id: str
    transaction_id: str
    operation: str
    amount: int
    description: str
    reference_id: Optional[str] = None
    created_at: str


class WalletResponse(BaseModel):
    user_id: str
    available_balance: int
    held_balance: int
    earned_total: int
    karma_balance: int
    history: List[LedgerEntryResponse] = []


class SubscribePlanInput(BaseModel):
    plan_id: str = Field(..., description="Plan ID to subscribe to: 'free', 'plus', or 'pro'")
    payment_id: Optional[str] = Field(None, description="Optional payment transaction id")


class BuyCreditsInput(BaseModel):
    credits: int = Field(..., ge=1, le=100, description="Number of credits to purchase")
    payment_id: Optional[str] = Field(None, description="Payment transaction id")


class PaymentOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    plan_id: str
    is_demo: bool
    label: str


class FundSponsorPoolInput(BaseModel):
    name: str = Field(..., description="Name of the sponsored pool, e.g. 'Alumni CSR Fund'")
    credits: int = Field(..., ge=1, description="Number of credits to fund")
    target_college: Optional[str] = Field(None, description="Target college eligible for sponsorship")


class ClaimSponsoredSeatInput(BaseModel):
    pool_id: str = Field(..., description="ID of the sponsor pool to claim credits from")
    request_id: Optional[str] = Field(None, description="Optional mentorship request id to associate")


class SponsorClaimResponse(BaseModel):
    id: str
    pool_id: str
    student_id: str
    request_id: Optional[str] = None
    credits: int
    status: str
    claimed_at: str


class SponsorPoolResponse(BaseModel):
    id: str
    name: str
    sponsor_id: str
    target_college: Optional[str] = None
    total_funded_credits: int
    allocated_credits: int
    remaining_credits: int
    created_at: str


class SponsorDashboardResponse(BaseModel):
    sponsor_id: str
    total_pools: int
    total_funded: int
    total_allocated: int
    total_remaining: int
    pools: List[SponsorPoolResponse] = []
    claims: List[SponsorClaimResponse] = []


class SetAffiliationInput(BaseModel):
    college: str = Field(..., description="College or university affiliation")
