"""Pydantic schemas for institution dashboard, verification queue, moderation reports, audit logs, and trust layers."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Dashboard & Metrics Schemas ---

class SkillGapItem(BaseModel):
    skill: str
    requested_count: int
    alumni_coverage_count: int
    gap_score: int


class TopGiverItem(BaseModel):
    giver_id: str
    full_name: str
    college: str
    completed_sessions: int
    average_rating: float


class DashboardOverviewResponse(BaseModel):
    total_requests: int
    answered_within_72h: int
    fulfillment_rate: float
    average_response_time_seconds: Optional[float] = None
    average_response_time_display: str = "N/A"
    active_givers: int
    inactive_givers: int
    completed_sessions: int
    average_rating: float
    free_sessions: int
    paid_sessions: int
    total_outcomes_reported: int = 0
    positive_outcomes_count: int = 0
    outcome_rate: float = 0.0
    outcome_breakdown: Dict[str, int] = {}
    skill_gap: List[SkillGapItem] = []
    top_givers: List[TopGiverItem] = []
    charts_data: Dict[str, Any] = {}


# --- Verification Queue Schemas ---

class VerificationCreateInput(BaseModel):
    user_id: str
    user_type: str = Field(..., description="'student', 'alumnus', 'faculty', 'recruiter'")
    full_name: str
    college: str
    identifier: str = Field(..., description="Roll number, official email, or CIN/GST")
    document_url: Optional[str] = None


class VerificationReviewInput(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    notes: Optional[str] = None


class VerificationResponse(BaseModel):
    id: str
    user_id: str
    user_type: str
    full_name: str
    college: str
    identifier: str
    document_url: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: str
    reviewed_at: Optional[str] = None


# --- Report & Moderation Schemas ---

class ReportCreateInput(BaseModel):
    reported_user_id: str
    target_type: str = Field(..., description="'profile', 'message', 'session'")
    target_id: str
    reason: str
    evidence: str = Field(..., description="Message excerpt or evidence description")


class ReportResolveInput(BaseModel):
    action: str = Field(..., description="'dismiss', 'warn', 'suspend', 'remove'")
    reason: str = Field(..., description="Action justification stored in audit log")
    is_scam: bool = Field(False, description="Whether incident constitutes scam activity")
    new_scam_pattern: Optional[str] = Field(None, description="Extracted pattern to add to scam_rules")
    admin_notes: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    reporter_id: str
    reported_user_id: str
    target_type: str
    target_id: str
    reason: str
    evidence: str
    status: str
    admin_notes: Optional[str] = None
    is_scam: bool = False
    created_at: str
    resolved_at: Optional[str] = None


# --- Audit & Incident Logs ---

class AuditLogResponse(BaseModel):
    id: str
    admin_id: str
    action: str
    target_type: str
    target_id: str
    reason: str
    metadata_json: Dict[str, Any] = {}
    created_at: str


class IncidentLogResponse(BaseModel):
    id: str
    report_id: Optional[str] = None
    offender_id: str
    incident_type: str
    extracted_patterns: List[str]
    status: str
    notes: Optional[str] = None
    created_at: str


# --- 7 Trust Layers Schemas ---

class TrustLayerItem(BaseModel):
    layer_number: int
    name: str
    threat_prevented: str
    status: str = "active"
    live_metric_name: str
    live_count: int
    proof_description: str


class TrustLayersResponse(BaseModel):
    layers: List[TrustLayerItem]
    summary: Dict[str, int]


# --- Outcome Tracking Schemas ---

class SessionOutcomeCreateInput(BaseModel):
    outcome: str = Field(..., description="'interview', 'referral', 'project_feedback', 'offer', 'nothing_yet'")
    notes: Optional[str] = None


class SessionOutcomeResponse(BaseModel):
    id: str
    session_id: str
    student_id: str
    giver_id: str
    outcome: str
    notes: Optional[str] = None
    created_at: str


# --- Network Graph Schemas ---

class GraphNode(BaseModel):
    id: str
    label: str
    role: str  # student, alumnus, faculty, recruiter, founder
    color: str  # #3B82F6 (student), #10B981 (alumnus), #8B5CF6 (faculty), #F59E0B (recruiter), #EC4899 (founder)
    college: str
    skills: List[str] = []
    safe_summary: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # "completed_session" or "vouch"
    label: str


class NetworkGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    summary: Dict[str, Any]


# --- Pilot Metrics & Launch Gate Schemas ---

class LaunchGateStatus(BaseModel):
    is_open: bool
    color: str  # "green" or "red"
    label: str  # "Launch Gate Open - Enabled for New College" or "Launch Gate Locked - Requirements Pending"
    verified_givers_target: int = 50
    verified_givers_current: int
    answer_rate_target_percent: float = 60.0
    answer_rate_current_percent: float
    requirements_met: bool
    missing_requirements: List[str] = []


class PlanPhase(BaseModel):
    phase_days: str  # "30-day", "60-day", "90-day"
    name: str  # "Prepare", "Open", "Prove"
    objective: str
    key_actions: List[str]
    target_milestones: List[str]
    status: str  # "completed", "in_progress", "pending"


class PilotMetricsResponse(BaseModel):
    launch_gate: LaunchGateStatus
    verified_givers_count: int
    verified_givers_target: int = 50
    answer_rate_72h_percent: float
    answer_rate_target_percent: float = 60.0
    thirty_sixty_ninety_plan: List[PlanPhase]


class CollegeCreateInput(BaseModel):
    name: str
    code: str


class CollegeEnableInput(BaseModel):
    college_id: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None


class CollegeResponse(BaseModel):
    id: str
    name: str
    code: str
    is_enabled: bool
    created_at: str

