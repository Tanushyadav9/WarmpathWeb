"""Pydantic schemas for matching recommendations."""
from typing import List, Optional
from pydantic import BaseModel


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
