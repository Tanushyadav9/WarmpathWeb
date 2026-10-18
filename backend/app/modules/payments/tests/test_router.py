import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_payments_endpoints_return_501():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhooks/razorpay")
        assert response.status_code == 501
        data = response.json()
        assert data["error"]["code"] == "module_not_implemented"
