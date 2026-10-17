"""
backend/app/core/models.py - Normalized SQLAlchemy Models for WarmPath.
Defines all 25 core schema tables supporting both PostgreSQL (with pgvector)
and local SQLite (for lightning-fast isolated testing and seed states).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
    JSON,
    Uuid,
    types,
)
from sqlalchemy.orm import relationship

from app.core.base import Base


def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class VectorFallbackType(types.TypeDecorator):
    """
    Transparent vector column:
    Uses pgvector Vector(768) on PostgreSQL, falls back to JSON float-list on SQLite.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 768, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                return dialect.type_descriptor(types.NullType())
        return dialect.type_descriptor(JSON())


# 1. Institutions
class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    short_name = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    email_domains = Column(JSON, nullable=False, default=list)  # e.g. ["iiitd.ac.in"]
    verified_domain = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    users = relationship("User", back_populates="institution")
    opportunities = relationship("Opportunity", back_populates="institution")


# 2. Users (Role-based: student, alumni, faculty, recruiter, founder, admin)
class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="student")  # student, alumni, faculty, recruiter, founder, admin
    roles = Column(JSON, nullable=False, default=lambda: ["student"])
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True)
    verification_level = Column(String(50), nullable=False, default="pending")  # pending, verified_alumnus, verified_professional, trusted, verified_employer
    trust_score = Column(Float, nullable=False, default=50.0)
    consent_flags = Column(JSON, nullable=False, default=lambda: {"data_processing": True, "profile_visible": True, "dpdp_accepted": True})
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    institution = relationship("Institution", back_populates="users")
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    giver_profile = relationship("GiverProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    availability = relationship("Availability", back_populates="user", uselist=False, cascade="all, delete-orphan")
    capacity = relationship("Capacity", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credit_wallet = relationship("CreditWallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


# 3. Student Profiles (Seeker)
class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    headline = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    batch = Column(Integer, nullable=True)
    department = Column(String(100), nullable=True)
    cgpa = Column(Float, nullable=True)
    target_role = Column(String(100), nullable=True)
    target_domain = Column(String(100), nullable=True)
    intent_ask = Column(Text, nullable=True)
    embedding = Column(VectorFallbackType(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="student_profile")


# 4. Giver Profiles (Alumni / Faculty / Founder / Recruiter)
class GiverProfile(Base):
    __tablename__ = "giver_profiles"

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    headline = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    role_title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    domain = Column(String(100), nullable=True)
    topics = Column(JSON, nullable=False, default=list)  # e.g. ["System Design", "Career Navigation"]
    offers = Column(JSON, nullable=False, default=list)  # e.g. ["mock_interview", "resume_review"]
    languages = Column(JSON, nullable=False, default=lambda: ["English", "Hindi"])
    band = Column(String(50), nullable=False, default="rising")  # rising, trusted, top_rated
    rating_avg = Column(Float, nullable=False, default=4.0)
    rating_count = Column(Integer, nullable=False, default=0)
    completion_rate = Column(Float, nullable=False, default=1.0)
    weekly_capacity = Column(Integer, nullable=False, default=2)
    embedding = Column(VectorFallbackType(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="giver_profile")


# 5. Skills
class Skill(Base):
    __tablename__ = "skills"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)


# 6. User Skills
class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_id = Column(Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False)
    endorsements_count = Column(Integer, default=0, nullable=False)
    added_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )


# 7. Resumes
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    raw_file_ref = Column(String(500), nullable=True)
    parsed_json = Column(JSON, nullable=True)
    edited_json = Column(JSON, nullable=True)
    is_committed = Column(Boolean, default=False, nullable=False)
    parsed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 8. GitHub Proofs
class GitHubProof(Base):
    __tablename__ = "github_proofs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    repo_url = Column(String(500), nullable=False)
    repo_count = Column(Integer, default=0, nullable=False)
    top_languages = Column(JSON, default=list, nullable=False)
    total_commits = Column(Integer, default=0, nullable=False)
    stars_count = Column(Integer, default=0, nullable=False)
    verified_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 9. Availability
class Availability(Base):
    __tablename__ = "availability"

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(50), nullable=False, default="active_now")  # active_now, available_today, inactive
    time_window = Column(JSON, nullable=False, default=list)  # e.g. ["18:00-20:00"]
    last_active_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    response_rate = Column(Float, nullable=False, default=0.95)
    avg_reply_minutes = Column(Integer, nullable=False, default=45)
    auto_inactive_days = Column(Integer, nullable=False, default=14)

    user = relationship("User", back_populates="availability")


# 10. Capacity
class Capacity(Base):
    __tablename__ = "capacity"

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    weekly_cap = Column(Integer, nullable=False, default=2)
    free_monthly_cap = Column(Integer, nullable=False, default=4)
    current_week_booked = Column(Integer, nullable=False, default=0)
    current_month_free_booked = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="capacity")


# 11. Requests (Connection Lifecycle)
class Request(Base):
    __tablename__ = "requests"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seeker_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    giver_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, accepted, declined, cancelled, completed
    intent_category = Column(String(100), nullable=False)  # mock_interview, resume_review, career_guidance
    ask_details = Column(Text, nullable=False)
    proposed_slots = Column(JSON, nullable=False, default=list)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    credits_locked = Column(Integer, nullable=False, default=0)
    is_cross_college = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    messages = relationship("RequestMessage", back_populates="request", cascade="all, delete-orphan")


# 12. Request Messages (Private In-App Comms)
class RequestMessage(Base):
    __tablename__ = "request_messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    flagged_as_scam = Column(Boolean, default=False, nullable=False)
    scam_reasons = Column(JSON, default=list, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    request = relationship("Request", back_populates="messages")


# 13. Sessions
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid(as_uuid=True), ForeignKey("requests.id"), unique=True, nullable=False)
    giver_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    seeker_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=45, nullable=False)
    meeting_link = Column(String(500), nullable=True)
    status = Column(String(50), default="scheduled", nullable=False)  # scheduled, completed, no_show, disputed
    completed_at = Column(DateTime(timezone=True), nullable=True)


# 14. Ratings
class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), unique=True, nullable=False)
    reviewer_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    score = Column(Integer, nullable=False)  # 1 to 5
    tags = Column(JSON, default=list, nullable=False)  # ["Helpful", "On time", "Clear feedback"]
    comment = Column(Text, nullable=True)
    audit_status = Column(String(50), default="normal", nullable=False)  # normal, flagged, approved
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 15. Vouches
class Vouch(Base):
    __tablename__ = "vouches"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    giver_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    student_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    vouch_text = Column(Text, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 16. Credit Wallets
class CreditWallet(Base):
    __tablename__ = "credit_wallets"

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    balance = Column(Integer, default=0, nullable=False)
    escrow_held = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="credit_wallet")


# 17. Credit Ledger
class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(Uuid(as_uuid=True), ForeignKey("credit_wallets.user_id"), index=True, nullable=False)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # purchase, hold, release, refund, fee
    amount = Column(Integer, nullable=False)
    related_request_id = Column(Uuid(as_uuid=True), ForeignKey("requests.id"), nullable=True)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 18. Subscriptions
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id = Column(String(50), nullable=False)  # standard, high, premium
    plan_name = Column(String(100), nullable=False)
    monthly_credits = Column(Integer, default=1, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


# 19. Sponsored Seats
class SponsoredSeat(Base):
    __tablename__ = "sponsored_seats"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    granted_by = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    credit_amount = Column(Integer, default=3, nullable=False)
    remaining_credits = Column(Integer, default=3, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, exhausted, revoked
    granted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 20. Opportunities (Jobs, Referrals, Hackathons, Events)
class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    type = Column(String(50), nullable=False)  # job, referral, hackathon, event
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    company = Column(String(255), nullable=True)
    location = Column(String(100), nullable=True)
    skills = Column(JSON, default=list, nullable=False)
    college_affinity_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    url = Column(String(500), nullable=True)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    institution = relationship("Institution", back_populates="opportunities")


# 21. Reports (Moderation & Human Review Queue)
class Report(Base):
    __tablename__ = "reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reported_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    context_type = Column(String(50), nullable=False)  # chat, profile, session
    context_id = Column(String(100), nullable=True)
    reason = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, reviewing, dismissed, resolved
    action_taken = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


# 22. Scam Rules (Chat & Profile Security Filter)
class ScamRule(Base):
    __tablename__ = "scam_rules"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern = Column(String(255), nullable=False)
    rule_type = Column(String(50), default="regex", nullable=False)  # regex, keyword, pattern
    severity = Column(String(50), default="flag", nullable=False)  # flag, block
    reason = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 23. Notifications (F35 Center)
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="system", nullable=False)  # request, session, verification, system
    data = Column(JSON, default=dict, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="notifications")


# 24. Audit Log
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# 25. Embeddings
class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)  # student_intent, giver_profile, opportunity
    entity_id = Column(Uuid(as_uuid=True), index=True, nullable=False)
    embedding = Column(VectorFallbackType(768), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
