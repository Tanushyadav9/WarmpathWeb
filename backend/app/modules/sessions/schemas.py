"""Pydantic schemas for sessions."""
from typing import Optional
from pydantic import BaseModel, Field


class CreateRequestInput(BaseModel):
    giver_id: str = Field(..., description="Target giver user ID")
    intent: str = Field(..., description="Student intent / goal for mentorship")
    notes: Optional[str] = Field(None, description="Additional context or questions")
    is_free: bool = Field(True, description="True for own-college free session, False for paid credit")


class DecisionInput(BaseModel):
    reason: Optional[str] = Field(None, description="Optional note on decision")


class RequestResponse(BaseModel):
    id: str
    student_id: str
    giver_id: str
    intent: str
    notes: Optional[str] = None
    status: str
    is_free: bool
    created_at: str
    responded_at: Optional[str] = None
    completed_at: Optional[str] = None
    rated: bool
