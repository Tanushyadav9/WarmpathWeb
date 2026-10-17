"""Pydantic schemas for availability."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def get_status_color(status: str) -> str:
    s = (status or "").lower()
    if s == "active_now":
        return "#15803D"  # Success green
    elif s == "available_today":
        return "#F5A524"  # Amber
    return "#64748B"  # Slate for inactive / offline


def get_status_label(status: str, today_window: Optional[str] = None) -> str:
    s = (status or "").lower()
    if s == "active_now":
        return "Active now"
    elif s == "available_today":
        if today_window:
            return f"Available today ({today_window})"
        return "Available today"
    return "Inactive"


class AvailabilityUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="active_now, available_today, or inactive")
    today_window: Optional[str] = Field(None, description="e.g. '8 to 10 pm'")
    weekly_capacity_cap: Optional[int] = Field(None, ge=1, le=50)
    monthly_free_session_cap: Optional[int] = Field(None, ge=1, le=100)


class AvailabilityResponse(BaseModel):
    user_id: str
    status: str
    today_window: Optional[str] = None
    status_color: str
    status_label: str
    weekly_capacity_cap: int
    weekly_sessions_used: int
    monthly_free_session_cap: int
    monthly_free_sessions_used: int
    capacity_left: int
    capacity_reached: bool
    capacity_banner: Optional[str] = None
    response_rate: float
    avg_reply_time_seconds: Optional[float] = None
    avg_reply_time_display: str
    last_active_at: Optional[str] = None


class PresenceStatusItem(BaseModel):
    online: bool
    status: str
    status_color: str
    status_label: str
    today_window: Optional[str] = None
    capacity_left: int
    capacity_reached: bool
    response_rate: float
    avg_reply_time_display: str


class PresenceResponse(BaseModel):
    users: Dict[str, PresenceStatusItem]
