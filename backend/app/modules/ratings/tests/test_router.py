import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_ratings_session_rating_endpoint():
    transport = ASGITransport(app=app)
    headers = {"X-User-Id": "11111111-1111-1111-1111-111111111111"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        response = await client.post(
            "/sessions/22222222-2222-2222-2222-222222222222/rating",
            json={"score": 5, "comment": "Great mentorship!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 5
