"""Pydantic schemas for sessions, request lifecycle, chat, and scheduling."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateRequestInput(BaseModel):
    giver_id: str = Field(..., description="Target giver user ID")
    intent: str = Field(..., description="Student intent / goal for mentorship")
    notes: Optional[str] = Field(None, description="Additional context or questions")
    is_free: bool = Field(True, description="True for own-college free session, False for paid credit")


class DeclineRequestInput(BaseModel):
    reason: str = Field(..., description="Reason for declining the request")


class DecisionInput(BaseModel):
    reason: Optional[str] = Field(None, description="Optional note on decision")


class ProposeSlotsInput(BaseModel):
    slots: List[str] = Field(..., description="List of proposed ISO datetime slot strings")


class ConfirmSlotInput(BaseModel):
    slot: str = Field(..., description="Selected ISO datetime slot string to confirm")


class NoShowReportInput(BaseModel):
    party: str = Field(..., description="Which party did not show: 'giver' or 'student'")
    reason: Optional[str] = Field(None, description="Details or reason for reporting no-show")


class MessageCreateInput(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000, description="Chat message body")


class MessageResponse(BaseModel):
    id: str
    request_id: str
    sender_id: str
    recipient_id: str
    body: str
    flags: List[str] = []
    safety_action: str = "allow"
    safety_warning: Optional[str] = None
    created_at: str


class StudentProfileRoleView(BaseModel):
    """
    Role-based view of student profile for givers.
    Contact details (email, phone) stay strictly hidden.
    """
    student_id: str
    display_name: str
    college: Optional[str] = None
    headline: Optional[str] = None
    intent: str
    notes: Optional[str] = None


class BookingResponse(BaseModel):
    id: str
    request_id: str
    scheduled_at: str
    room_id: str
    meeting_link: str
    calendar_event_id: Optional[str] = None
    created_at: str


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    request_id: str
    type: str
    message: str
    created_at: str


class RequestResponse(BaseModel):
    id: str
    student_id: str
    giver_id: str
    intent: str
    notes: Optional[str] = None
    status: str
    decline_reason: Optional[str] = None
    is_free: bool
    proposed_slots: Optional[List[str]] = None
    confirmed_slot: Optional[str] = None
    meeting_link: Optional[str] = None
    no_show_party: Optional[str] = None
    created_at: str
    responded_at: Optional[str] = None
    scheduled_at: Optional[str] = None
    completed_at: Optional[str] = None
    rated: bool = False
    student_profile: Optional[StudentProfileRoleView] = None
