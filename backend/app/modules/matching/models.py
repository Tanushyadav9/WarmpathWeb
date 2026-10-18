"""SQLAlchemy models for matching, faculty domain mentors, recruiters, and opportunities."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.core.db import Base, PG_UUID, PG_JSON


class GiverProfile(Base):
    __tablename__ = "giver_profiles"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    headline = Column(String(255), nullable=True)
    college = Column(String(255), nullable=True)
    skills = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class FacultyProfile(Base):
    """Domain mentor profile for faculty members with custom credit rates and expertise."""
    __tablename__ = "faculty_profiles"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    institution = Column(String(255), nullable=False)
    expertise = Column(PG_JSON, default=list, nullable=False)  # List of domain skills / topics
    bio = Column(Text, nullable=True)
    rate_credits = Column(Integer, default=5, nullable=False)  # Custom rate in credits per session
    is_verified = Column(Boolean, default=True, nullable=False)
    verified_expert_badge = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EmployerProfile(Base):
    """Employer / recruiter / founder profile with corporate verification checks."""
    __tablename__ = "employer_profiles"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    company_name = Column(String(255), index=True, nullable=False)
    company_domain = Column(String(255), nullable=False)
    designation = Column(String(100), default="Recruiter", nullable=False)
    cin_or_gst = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_employer_badge = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Opportunity(Base):
    """Opportunity layer item (job, referral, hiring_chat, talk, hackathon, event, meetup)."""
    __tablename__ = "opportunities"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    creator_id = Column(PG_UUID, index=True, nullable=False)  # Recruiter / founder
    company_name = Column(String(255), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    opportunity_type = Column(String(50), nullable=False)  # job, referral, hiring_chat, talk, hackathon, event, meetup
    description = Column(Text, nullable=False)
    required_skills = Column(PG_JSON, default=list, nullable=False)  # List of skill strings
    city = Column(String(100), default="Remote", nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    external_link = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class StudentProfile(Base):
    """Confirmed student profile including skills, college, and proof of work."""
    __tablename__ = "student_profiles"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID, unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    college = Column(String(255), nullable=False)
    skills = Column(PG_JSON, default=list, nullable=False)  # Confirmed skills
    city = Column(String(100), default="Delhi", nullable=False)
    proof_of_work = Column(PG_JSON, default=list, nullable=False)  # Project / portfolio links
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class OpportunityInterest(Base):
    """Student expression of interest (opt-in) for an opportunity."""
    __tablename__ = "opportunity_interests"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(PG_UUID, index=True, nullable=False)
    student_id = Column(PG_UUID, index=True, nullable=False)
    opted_in = Column(Boolean, default=True, nullable=False)
    note = Column(Text, nullable=True)
    proof_of_work = Column(PG_JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
