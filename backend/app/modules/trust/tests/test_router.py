import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_trust_me_endpoint():
    transport = ASGITransport(app=app)
    headers = {"X-User-Id": "11111111-1111-1111-1111-111111111111"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        response = await client.get("/me/trust")
        assert response.status_code == 200
        data = response.json()
        assert data["trust_level"] in ["new", "established", "verified"]
        assert data["max_open_requests"] >= 3
        assert data["can_request"] is True

@pytest.mark.asyncio
async def test_trust_unimplemented_endpoints_return_501():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/blocks")
        assert response.status_code == 501
        data = response.json()
        assert data["error"]["code"] == "module_not_implemented"
