import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_resume_endpoint_validates_input():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/resume")
        # Missing file field produces 422 Unprocessable Entity
        assert response.status_code == 422
