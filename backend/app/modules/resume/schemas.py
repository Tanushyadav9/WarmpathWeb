import uuid
from datetime import datetime
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field


# --- Consent Schemas ---

class ConsentUpdateItem(BaseModel):
    purpose: str
    granted: bool


class UpdateConsentsRequest(BaseModel):
    consents: List[ConsentUpdateItem]
    text_version: Optional[str] = "v1.0"


class ConsentItemResponse(BaseModel):
    purpose: str
    granted: bool
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    text_version: str = "v1.0"


class ConsentsListResponse(BaseModel):
    items: List[ConsentItemResponse]


# --- Resume Upload & Parsing Schemas ---

class ResumeUploadResponse(BaseModel):
    resume_id: str
    status: str = "processing"


class EducationItem(BaseModel):
    degree: str
    institution: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    gpa: Optional[str] = None


class SkillItem(BaseModel):
    name: str
    category: str = "Other"


class ProjectItem(BaseModel):
    title: str
    description: str
    tech: List[str] = Field(default_factory=list)


class ParsedResumeData(BaseModel):
    education: List[EducationItem] = Field(default_factory=list)
    skills: List[SkillItem] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    experience_level: str = "student"  # student | entry | mid | senior
    links: Dict[str, str] = Field(default_factory=dict)
    confidence: float = 0.95


# --- Profile Schemas ---

class StudentProfileUpdateRequest(BaseModel):
    education: Optional[List[EducationItem]] = None
    skills: Optional[List[SkillItem]] = None
    domains: Optional[List[str]] = None
    projects: Optional[List[ProjectItem]] = None
    experience_level: Optional[str] = None
    links: Optional[Dict[str, str]] = None


class StudentProfileResponse(BaseModel):
    user_id: uuid.UUID
    parsed: Optional[Dict[str, Any]] = None
    edited: Optional[Dict[str, Any]] = None
    merged: Dict[str, Any]
    is_confirmed: bool = False
    skills_label: str = "extracted skills, student-confirmed"
    hide_cgpa: bool = False
    has_embedding: bool
    updated_at: datetime


# --- GitHub Proof Schemas (F5) ---

class GitHubProofRequest(BaseModel):
    repo_url: Optional[str] = None
    username: Optional[str] = None


class GitHubProofResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    repo_url: str
    repo_count: int
    top_languages: List[str]
    total_commits: int
    stars_count: int
    verified_at: datetime
    badge: str = "Proof of work"


# --- Privacy & DPDP Schemas (F33) ---

class ProfileVisibilityUpdateRequest(BaseModel):
    hide_cgpa: Optional[bool] = None


class WithdrawConsentRequest(BaseModel):
    purpose: str


class DataExportResponse(BaseModel):
    user: Dict[str, Any]
    profile: Optional[Dict[str, Any]] = None
    resume: Optional[Dict[str, Any]] = None
    github_proof: Optional[Dict[str, Any]] = None
    consents: List[Dict[str, Any]] = Field(default_factory=list)
    requests: List[Dict[str, Any]] = Field(default_factory=list)
    exported_at: datetime



# --- Intent Schemas ---

class StudentIntentUpdateRequest(BaseModel):
    text: str
    goal_type: Optional[str] = "internship"  # internship | job | startup | higher_studies | guidance | other
    target_roles: Optional[List[str]] = Field(default_factory=list)
    target_domains: Optional[List[str]] = Field(default_factory=list)


class StructuredIntent(BaseModel):
    goal: str
    roles: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    urgency: str = "normal"  # low | normal | high
    help_type: str = "guidance"  # referral | mentorship | mock_interview | guidance


class StudentIntentResponse(BaseModel):
    user_id: uuid.UUID
    raw_text: str
    goal_type: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    target_domains: List[str] = Field(default_factory=list)
    structured: Optional[StructuredIntent] = None
    has_embedding: bool
    updated_at: datetime
