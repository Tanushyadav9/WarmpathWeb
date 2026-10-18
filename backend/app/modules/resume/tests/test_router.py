import io
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_resume_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test GET /resume/profile
        res = await client.get("/resume/profile", headers={"X-User-Id": "11111111-1111-1111-1111-111111111111"})
        assert res.status_code == 200
        data = res.json()
        assert "parsed_entities" in data

        # Test POST /resume with PDF
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("test_resume.pdf", pdf_bytes, "application/pdf")}
        upload_res = await client.post("/resume", files=files)
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        assert upload_data["status"] == "uploaded"
