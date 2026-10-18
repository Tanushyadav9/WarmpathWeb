"""SQLAlchemy models for wallets, immutable credit ledger, escrow, and sponsor pools."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.core.db import Base, PG_UUID


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    available_balance = Column(Integer, default=0, nullable=False)
    held_balance = Column(Integer, default=0, nullable=False)
    earned_total = Column(Integer, default=0, nullable=False)
    karma_balance = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    transaction_id = Column(PG_UUID, index=True, nullable=False)
    account_id = Column(String(100), index=True, nullable=False)
    user_id = Column(PG_UUID, nullable=True)
    operation = Column(
        String(30), nullable=False
    )  # hold, release, refund, fee, grant, purchase, karma, sponsor_fund, sponsor_claim
    amount = Column(Integer, nullable=False)  # positive = credit (+), negative = debit (-)
    reference_id = Column(String(100), index=True, nullable=True)
    idempotency_key = Column(String(150), index=True, nullable=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class SessionEscrow(Base):
    __tablename__ = "session_escrows"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    request_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    student_id = Column(PG_UUID, index=True, nullable=False)
    giver_id = Column(PG_UUID, index=True, nullable=False)
    amount = Column(Integer, nullable=False)
    sponsor_pool_id = Column(PG_UUID, nullable=True)
    status = Column(String(20), default="held", nullable=False)  # held, released, refunded
    held_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)


class SponsorPool(Base):
    __tablename__ = "sponsor_pools"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    sponsor_id = Column(PG_UUID, index=True, nullable=False)
    institution_id = Column(PG_UUID, nullable=True)
    target_college = Column(String(255), nullable=True)
    total_funded_credits = Column(Integer, default=0, nullable=False)
    allocated_credits = Column(Integer, default=0, nullable=False)
    remaining_credits = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class SponsoredClaim(Base):
    __tablename__ = "sponsored_claims"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    pool_id = Column(PG_UUID, index=True, nullable=False)
    student_id = Column(PG_UUID, index=True, nullable=False)
    request_id = Column(PG_UUID, nullable=True)
    credits = Column(Integer, nullable=False)
    status = Column(String(20), default="claimed", nullable=False)  # claimed, used, refunded
    claimed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class UserAffiliation(Base):
    __tablename__ = "user_affiliations"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    college = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    plan_id = Column(String(50), nullable=False)  # free, plus, pro
    status = Column(String(20), default="active", nullable=False)
    monthly_credits = Column(Integer, default=0, nullable=False)
    renews_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
