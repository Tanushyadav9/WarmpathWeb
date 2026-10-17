import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Giver Profile Schemas ---

class GiverProfileCreateUpdate(BaseModel):
    offers: List[str] = Field(
        default_factory=list,
        description="Help types offered: resume_review, mock_interview, referral_advice, career_guidance, project_feedback, domain_talk",
    )
    topics: List[str] = Field(default_factory=list)
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    company: Optional[str] = Field(None, max_length=255)
    role_title: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=2000)
    languages: List[str] = Field(default_factory=lambda: ["English"])
    weekly_capacity: int = Field(default=3, ge=1, le=20)
    institution_id: Optional[int] = None
    department: Optional[str] = Field(None, max_length=100)
    batch: Optional[int] = None
    societies: List[str] = Field(default_factory=list)


class GiverProfileResponse(BaseModel):
    user_id: uuid.UUID
    offers: List[str]
    topics: List[str]
    skills: List[Dict[str, Any]]
    domains: List[str]
    company: Optional[str] = None
    role_title: Optional[str] = None
    bio: Optional[str] = None
    languages: List[str]
    weekly_capacity: int
    institution_id: Optional[int] = None
    department: Optional[str] = None
    batch: Optional[int] = None
    societies: List[str]
    has_embedding: bool
    response_stats: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# --- Scoring & Explainability Schemas ---

class ScoreComponents(BaseModel):
    # 6 Core Weights from config/matching.json
    skill_intent_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    similar_journey: float = Field(default=0.0, ge=0.0, le=1.0)
    affinity: float = Field(default=0.0, ge=0.0, le=1.0)
    rating: float = Field(default=0.0, ge=0.0, le=1.0)
    availability: float = Field(default=0.0, ge=0.0, le=1.0)
    response_speed: float = Field(default=0.0, ge=0.0, le=1.0)

    # Legacy / Compatibility fields
    expertise_fit: float = Field(default=0.0, ge=0.0, le=1.0)
    intent_fit: float = Field(default=0.0, ge=0.0, le=1.0)
    response_odds: float = Field(default=0.0, ge=0.0, le=1.0)
    cold_start_boost: float = Field(default=0.0, ge=0.0)
    total_score: float = Field(..., ge=0.0, le=1.0)


class RatingSummary(BaseModel):
    band: str = "Rising"
    smoothed_avg: float = 4.0
    total_sessions: int = 0
    completion_rate: float = 1.0


class AvailabilitySummary(BaseModel):
    online: bool = False
    capacity_left: int = 3
    status: str = "active_now"
    avg_reply_minutes: int = 45


# --- Public Giver Card & Feed Schemas ---

class GiverPublicCard(BaseModel):
    id: uuid.UUID
    full_name: str
    headline: str
    giver_type: str = "alumni"  # alumni | faculty | recruiter | founder
    giver_type_label: str = "Alumnus Mentor"  # Alumnus Mentor | Faculty Mentor | Verified Recruiter | Verified Founder
    company: Optional[str] = None
    role_title: Optional[str] = None
    bio: Optional[str] = None
    offers: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    badges: List[str] = Field(default_factory=list)
    band: str = "Rising"
    rating_summary: RatingSummary
    availability_summary: AvailabilitySummary
    why_lines: List[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    giver: GiverPublicCard
    score_components: ScoreComponents
    why_lines: List[str] = Field(default_factory=list)
    locked: bool = False
    lock_reason: Optional[str] = None


class HardGateExclusionSummary(BaseModel):
    total_excluded: int = 0
    reasons: Dict[str, int] = Field(
        default_factory=lambda: {
            "unverified": 0,
            "suspended": 0,
            "inactive_too_long": 0,
            "over_capacity": 0,
        }
    )


class RecommendationsResponse(BaseModel):
    items: List[RecommendationItem]
    excluded_summary: HardGateExclusionSummary = Field(default_factory=HardGateExclusionSummary)
    next_cursor: Optional[str] = None
    scope: str
    locked: bool = False
    lock_reason: Optional[str] = None


# --- Jury / Admin Explain Ranking Schemas ---

class CandidateRankingExplanation(BaseModel):
    giver_id: uuid.UUID
    giver_name: str
    giver_type: str
    giver_type_label: str
    role_title: Optional[str] = None
    company: Optional[str] = None
    score_breakdown: ScoreComponents
    shared_skills: List[str] = Field(default_factory=list)
    same_college: bool = False
    same_branch: bool = False
    availability_status: str = "active_now"
    avg_reply_minutes: int = 45
    rating_avg: float = 4.0
    why_lines: List[str] = Field(default_factory=list)


class ExplainRankingResponse(BaseModel):
    weights: Dict[str, float]
    hard_gates_config: Dict[str, Any]
    excluded_summary: HardGateExclusionSummary
    candidates: List[CandidateRankingExplanation]


# --- Intent & Request Quality Schemas (F6 & F7) ---

class IntentQualityCheckRequest(BaseModel):
    text: str


class IntentQualityCheckResponse(BaseModel):
    quality_score: float
    is_vague: bool
    is_blocked: bool
    block_reason: Optional[str] = None
    issues: List[str] = Field(default_factory=list)
    suggested_refinement: Optional[str] = None
    examples: List[str] = Field(default_factory=list)


class StructuredIntentData(BaseModel):
    goal_type: str  # mentor | referral | mock_interview | resume_review | project_feedback
    target_role: Optional[str] = None
    target_company_type: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    timeline: Optional[str] = None
    raw_text: str


class SaveIntentRequest(BaseModel):
    text: str
    goal_type: Optional[str] = None
    target_role: Optional[str] = None
    target_company_type: Optional[str] = None
    required_skills: Optional[List[str]] = None


class SaveIntentResponse(BaseModel):
    user_id: uuid.UUID
    structured: StructuredIntentData
    intent_embedding_present: bool = True
    message: str = "Intent saved successfully"
