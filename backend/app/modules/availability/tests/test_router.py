import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_availability_endpoints():
    transport = ASGITransport(app=app)
    headers = {"X-User-Id": "11111111-1111-1111-1111-111111111111"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        # GET default availability
        res = await client.get("/me/availability")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "inactive"
        assert data["weekly_capacity_cap"] == 5

        # PUT availability to active_now
        res = await client.put("/me/availability", json={"status": "active_now", "weekly_capacity_cap": 3})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active_now"
        assert data["status_color"] == "#15803D"
        assert data["weekly_capacity_cap"] == 3

        # PUT availability to available_today
        res = await client.put("/me/availability", json={"status": "available_today", "today_window": "8 to 10 pm"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "available_today"
        assert data["status_color"] == "#F5A524"
        assert data["today_window"] == "8 to 10 pm"

        # POST /me/online
        res = await client.post("/me/online")
        assert res.status_code == 200
        assert res.json()["status"] == "active_now"

        # DELETE /me/online
        res = await client.delete("/me/online")
        assert res.status_code == 200
        assert res.json()["status"] == "inactive"

        # GET /presence
        res = await client.get("/presence?user_ids=11111111-1111-1111-1111-111111111111")
        assert res.status_code == 200
        pdata = res.json()
        assert "11111111-1111-1111-1111-111111111111" in pdata["users"]
