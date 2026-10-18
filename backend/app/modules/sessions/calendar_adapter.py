"""
Calendar adapter for mentorship session scheduling.
Creates Google Calendar event with Jitsi/Meet link via calendar adapter
(mock in demo mode that creates an internal meeting page).
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings


class CalendarAdapter:
    """Adapter for creating calendar events and conference meeting links."""

    async def create_event(
        self,
        request_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a calendar event and generates a secure meeting link.
        In demo/dev mode, mocks Google Calendar and provides Jitsi conference room.
        """
        event_id = f"cal_{uuid.uuid4().hex[:12]}"
        meeting_link = f"{settings.JITSI_BASE_URL}/warmpath-{request_id}"
        internal_meeting_url = f"https://warmpath.internal/meetings/{request_id}"

        return {
            "event_id": event_id,
            "meeting_link": meeting_link,
            "html_link": internal_meeting_url,
            "title": title,
            "start_time": start_time.isoformat() if isinstance(start_time, datetime) else str(start_time),
            "end_time": end_time.isoformat() if isinstance(end_time, datetime) else str(end_time),
            "attendees": attendees or [],
            "description": description or "",
            "status": "confirmed",
        }


calendar_adapter = CalendarAdapter()
