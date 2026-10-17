"""Pydantic schemas for ratings."""
from typing import Optional
from pydantic import BaseModel, Field


class RatingCreateInput(BaseModel):
    score: int = Field(..., ge=1, le=5, description="1 to 5 star rating")
    comment: Optional[str] = Field(None, description="Optional written review")


class RatingResponse(BaseModel):
    id: str
    session_id: str
    rater_id: str
    giver_id: str
    score: int
    comment: Optional[str] = None
    created_at: str
