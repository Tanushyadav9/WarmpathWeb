import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_institution_dashboard_overview_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "fulfillment_rate" in data
        assert "active_givers" in data
        assert "completed_sessions" in data
