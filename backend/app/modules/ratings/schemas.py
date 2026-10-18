"""Pydantic schemas for ratings, giver bands, vouches, and leaderboards."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RatingCreateInput(BaseModel):
    score: int = Field(..., ge=1, le=5, description="1 to 5 star rating")
    tags: List[str] = Field(
        default_factory=list,
        description="Rating tags e.g. Helpful, On time, Clear feedback",
    )
    comment: Optional[str] = Field(None, description="Optional written review")


class RatingResponse(BaseModel):
    id: str
    session_id: str
    rater_id: str
    giver_id: str
    score: int
    tags: List[str] = []
    comment: Optional[str] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    review_status: str = "approved"
    created_at: str


class GiverPublicRatingSummaryResponse(BaseModel):
    """
    Student-facing giver rating summary.
    Do NOT show tier labels to students as a judgment; show rating, session count and tags.
    """
    giver_id: str
    rating: float
    session_count: int
    top_tags: List[str] = []
    recent_reviews: List[RatingResponse] = []


class GiverBandResponse(BaseModel):
    """Giver-facing reputation and rating band information."""
    giver_id: str
    band: str  # Rising, Trusted, Top Rated
    smoothed_avg: float
    n: int
    completion_rate: float
    ranking_score: float
    next_threshold_message: str


class VouchCreateInput(BaseModel):
    note: Optional[str] = Field(None, description="Optional personal endorsement or recommendation note")


class VouchResponse(BaseModel):
    id: str
    session_id: str
    giver_id: str
    student_id: str
    giver_name: str
    giver_company: str
    display_text: str  # "Vouched by [name] at [company]"
    note: Optional[str] = None
    created_at: str


class LeaderboardEntryResponse(BaseModel):
    rank: int
    giver_id: str
    full_name: str
    headline: Optional[str] = None
    college: Optional[str] = None
    session_count: int
    average_rating: float
    ranking_score: float
    top_tags: List[str] = []
    karma_points: int = 0


class RatingReviewResolveInput(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    notes: Optional[str] = Field(None, description="Admin review resolution notes")
