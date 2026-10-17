import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_sessions_requests_endpoint():
    transport = ASGITransport(app=app)
    headers = {"X-User-Id": "11111111-1111-1111-1111-111111111111"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        # GET /requests
        response = await client.get("/requests")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
