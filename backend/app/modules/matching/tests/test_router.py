import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_matching_recommendations_endpoint():
    transport = ASGITransport(app=app)
    headers = {"X-User-Id": "11111111-1111-1111-1111-111111111111"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        response = await client.get("/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
