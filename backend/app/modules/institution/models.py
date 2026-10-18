"""SQLAlchemy models for institution administration, moderation, reports, and audit logs."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.core.db import Base, PG_UUID, PG_JSON


class Report(Base):
    """Student or giver safety / abuse report for a profile, message, or session."""
    __tablename__ = "reports"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    reporter_id = Column(PG_UUID, index=True, nullable=False)
    reported_user_id = Column(PG_UUID, index=True, nullable=False)
    target_type = Column(String(50), nullable=False)  # profile, message, session
    target_id = Column(PG_UUID, index=True, nullable=False)
    reason = Column(String(100), nullable=False)  # scam, harassment, payment_request, no_show, abuse
    evidence = Column(Text, nullable=False)  # Message excerpt or detail
    status = Column(String(30), default="pending", nullable=False)  # pending, dismissed, warned, suspended, removed
    admin_notes = Column(Text, nullable=True)
    is_scam = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class AdminAuditLog(Base):
    """Immutable audit log for administrative moderation and verification decisions."""
    __tablename__ = "admin_audit_logs"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    admin_id = Column(PG_UUID, index=True, nullable=False)
    action = Column(String(50), nullable=False)  # dismiss, warn, suspend, remove, verify_approve, verify_reject, rule_created, rule_updated
    target_type = Column(String(50), nullable=False)  # report, user, giver, opportunity, verification, scam_rule
    target_id = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    metadata_json = Column(PG_JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class IncidentLog(Base):
    """Post-mortem incident learning log showing extracted patterns and updated rules."""
    __tablename__ = "incident_logs"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    report_id = Column(PG_UUID, nullable=True)
    offender_id = Column(PG_UUID, index=True, nullable=False)
    incident_type = Column(String(100), default="scam", nullable=False)
    extracted_patterns = Column(PG_JSON, default=list, nullable=False)
    status = Column(String(50), default="rules updated", nullable=False)  # "rules updated"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class VerificationRecord(Base):
    """Institution verification queue record for students, alumni, faculty, and employers."""
    __tablename__ = "verification_records"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    user_type = Column(String(50), nullable=False)  # student, alumnus, faculty, recruiter
    full_name = Column(String(255), nullable=False)
    college = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)  # Roll number, email, or CIN/GST
    document_url = Column(String(255), nullable=True)
    status = Column(String(30), default="pending", nullable=False)  # pending, approved, rejected
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
