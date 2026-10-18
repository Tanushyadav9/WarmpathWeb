"""Pydantic schemas for matching recommendations, faculty domain mentors, employers, and opportunities."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GiverRecommendationItem(BaseModel):
    giver_id: str
    full_name: str
    headline: str
    college: str
    skills: List[str]
    status: str
    status_color: str
    status_label: str
    today_window: Optional[str] = None
    response_rate: float
    avg_reply_time_display: str
    capacity_left: int
    why_matched: str


class RecommendationsResponse(BaseModel):
    items: List[GiverRecommendationItem]


# --- Faculty Domain Mentor Schemas ---

class FacultyProfileInput(BaseModel):
    full_name: str = Field(..., description="Full name with title e.g. Prof. Arvind Kumar")
    department: str = Field(..., description="Department e.g. Computer Science & Engineering")
    institution: str = Field(..., description="Institution e.g. IIIT Delhi, VIPS-TC")
    expertise: List[str] = Field(default_factory=list, description="Academic and research domain expertise")
    bio: Optional[str] = Field(None, description="Short bio and academic background")
    rate_credits: int = Field(5, ge=0, le=100, description="Rate in credits per completed rated session")


class FacultyProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    department: str
    institution: str
    expertise: List[str]
    bio: Optional[str] = None
    rate_credits: int
    is_verified: bool
    verified_expert_badge: bool
    created_at: str


# --- Recruiter & Employer Schemas ---

class EmployerProfileInput(BaseModel):
    full_name: str = Field(..., description="Contact name")
    company_name: str = Field(..., description="Registered company name")
    company_domain: str = Field(..., description="Official company domain e.g. google.com")
    designation: str = Field("Recruiter", description="Designation e.g. Founder, Technical Recruiter")
    cin_or_gst: Optional[str] = Field(None, description="Corporate identification or GST number for verification")
    is_verified: bool = Field(False, description="Whether business verification checks are completed")


class EmployerProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    company_name: str
    company_domain: str
    designation: str
    cin_or_gst: Optional[str] = None
    is_verified: bool
    verified_employer_badge: bool
    created_at: str


# --- Opportunity Layer Schemas ---

class OpportunityCreateInput(BaseModel):
    title: str = Field(..., description="Role title or event name")
    company_name: str = Field(..., description="Company or organizer name")
    opportunity_type: str = Field(
        ...,
        description="Type: job, referral, hiring_chat, talk, hackathon, event, meetup",
    )
    description: str = Field(..., description="Opportunity description and requirements")
    required_skills: List[str] = Field(
        default_factory=list,
        description="Required candidate skills for matching",
    )
    city: str = Field("Remote", description="City location or 'Remote'")
    deadline: Optional[str] = Field(None, description="Application deadline ISO string")
    external_link: Optional[str] = Field(None, description="External registration or application URL")


class LinkedAlumnus(BaseModel):
    giver_id: str
    full_name: str
    headline: str
    college: str
    skills: List[str] = []
    can_one_click_request: bool = True


class OpportunityItemResponse(BaseModel):
    id: str
    creator_id: str
    company_name: str
    title: str
    opportunity_type: str
    description: str
    required_skills: List[str]
    city: str
    deadline: Optional[str] = None
    external_link: Optional[str] = None
    is_active: bool
    verified_employer_badge: bool
    skill_overlap_count: int = 0
    skill_overlap_ratio: float = 0.0
    linked_alumni_summary: str = ""
    linked_alumni: List[LinkedAlumnus] = []
    has_student_opted_in: bool = False
    created_at: str


class OpportunitiesFeedResponse(BaseModel):
    items: List[OpportunityItemResponse]
    total: int


# --- Student Confirmed Profile & Opt-In Schemas ---

class StudentProfileInput(BaseModel):
    full_name: str
    college: str
    skills: List[str] = Field(default_factory=list)
    city: str = "Delhi"
    proof_of_work: List[str] = Field(default_factory=list, description="Verified project / portfolio links")


class StudentProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    college: str
    skills: List[str]
    city: str
    proof_of_work: List[str]
    created_at: str


class OpportunityInterestInput(BaseModel):
    note: Optional[str] = Field(None, description="Brief note on why the candidate is interested")
    proof_of_work: Optional[List[str]] = Field(None, description="Optional extra links for this opportunity")


class OpportunityInterestResponse(BaseModel):
    id: str
    opportunity_id: str
    student_id: str
    opted_in: bool
    note: Optional[str] = None
    proof_of_work: List[str] = []
    created_at: str


class CandidateProfileResponse(BaseModel):
    """
    Candidate record visible to recruiters ONLY after explicit opt-in.
    Shows confirmed skills, proof of work, and vouches.
    """
    student_id: str
    full_name: str
    college: str
    confirmed_skills: List[str]
    proof_of_work: List[str]
    vouches: List[str] = []  # e.g. ["Vouched by Priya Sharma at Google"]
    note: Optional[str] = None
    opted_in: bool = True
    opted_in_at: str
