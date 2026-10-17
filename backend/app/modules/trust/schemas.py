"""Pydantic schemas for trust."""
from typing import Any, Dict, Optional
from pydantic import BaseModel


class TrustScoreResponse(BaseModel):
    user_id: str
    trust_score: int
    trust_level: str
    is_verified: bool
    reports_count: int
    max_open_requests: int
    open_requests_count: int
    unrated_completed_count: int
    can_request: bool
    breakdown: Dict[str, Any]
