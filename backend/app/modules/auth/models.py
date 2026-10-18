"""SQLAlchemy models for auth, user accounts, OTPs, and DPDP consent tracking."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, String, Text
from app.core.db import Base, PG_UUID, PG_JSON, User


class OTPVerification(Base):
    """Cryptographic one-time password record for email verification and passwordless login."""
    __tablename__ = "otp_verifications"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), index=True, nullable=False)
    otp_code = Column(String(20), nullable=False)
    purpose = Column(String(50), default="login", nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ConsentRecord(Base):
    """Immutable DPDP Act & GDPR user consent audit trail."""
    __tablename__ = "consent_records"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, index=True, nullable=False)
    consent_type = Column(String(100), nullable=False)  # terms_of_service, privacy_policy, data_processing
    version = Column(String(20), default="v1.0", nullable=False)
    granted = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class FinancialAuditLog(Base):
    """Immutable financial audit trail recording all wallet, escrow, ledger, and money movements."""
    __tablename__ = "financial_audit_logs"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, index=True, nullable=True)
    action = Column(String(50), nullable=False)  # purchase, escrow_hold, escrow_release, escrow_refund, sponsored_grant
    amount = Column(String(50), nullable=False)
    reference_id = Column(String(100), nullable=True)
    idempotency_key = Column(String(255), nullable=True)
    metadata_json = Column(PG_JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
