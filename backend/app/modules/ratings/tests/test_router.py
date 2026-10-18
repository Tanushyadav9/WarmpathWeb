import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from app.core.db import async_session_maker
from app.main import app
from app.modules.sessions.models import MentorshipRequest

@pytest.mark.asyncio
async def test_ratings_session_rating_endpoint():
    transport = ASGITransport(app=app)
    student_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    session_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    giver_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async with async_session_maker() as db:
        req = MentorshipRequest(
            id=session_id,
            student_id=student_id,
            giver_id=giver_id,
            intent="Mock Interview",
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(req)
        await db.commit()

    headers = {"X-User-Id": str(student_id)}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        response = await client.post(
            f"/sessions/{session_id}/rating",
            json={"score": 5, "comment": "Great mentorship!", "tags": ["Helpful"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 5
