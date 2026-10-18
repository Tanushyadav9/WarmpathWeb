import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_auth_request_otp():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/request-otp", json={"email": "student@iiitd.ac.in"})
        assert response.status_code == 200
        data = response.json()
        assert "otp_code" in data
        assert "expires_in_minutes" in data
