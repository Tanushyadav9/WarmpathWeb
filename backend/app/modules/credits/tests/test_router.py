import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_credits_plans_and_wallet_endpoints():
    transport = ASGITransport(app=app)
    user_id = str(uuid.uuid4())
    headers = {"X-User-Id": user_id}

    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        # GET /plans
        res_plans = await client.get("/plans")
        assert res_plans.status_code == 200
        plans = res_plans.json()
        assert len(plans) == 3
        plan_ids = [p["id"] for p in plans]
        assert "free" in plan_ids
        assert "plus" in plan_ids
        assert "pro" in plan_ids

        # GET /me/wallet
        res_wallet = await client.get("/me/wallet")
        assert res_wallet.status_code == 200
        wallet = res_wallet.json()
        assert wallet["user_id"] == user_id
        assert wallet["available_balance"] == 0
        assert wallet["held_balance"] == 0
