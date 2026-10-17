"""
backend/tests/test_f1_f35_f36.py - Comprehensive acceptance tests for F1, F35, and F36.

Verifies:
1. Login works for each role (Student, Alumni, Faculty, Recruiter, Founder, Admin).
2. Each role accesses their specialized dashboard view.
3. Unauthorized API calls return HTTP 403 Forbidden.
4. Notification center (F35) retrieves, filters, and marks read.
5. Demo switcher and Reset Demo (F36) restore database state.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

ROLES_CREDENTIALS = [
    ("student", "aarav.sharma@iiitd.ac.in", "demo1234"),
    ("alumni", "vikram.malhotra@alumni.iiitd.ac.in", "demo1234"),
    ("faculty", "dr.pankaj@iiitd.ac.in", "demo1234"),
    ("recruiter", "priya.recruiter@razorpay.com", "demo1234"),
    ("founder", "kunal.founder@postman.com", "demo1234"),
    ("admin", "admin@iiitd.ac.in", "demo1234"),
]


@pytest.mark.asyncio
async def test_login_works_for_all_six_roles():
    """Verify that email + password login succeeds for all 6 roles."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for expected_role, email, pwd in ROLES_CREDENTIALS:
            response = await client.post(
                "/auth/login",
                json={"email": email, "password": pwd},
            )
            assert response.status_code == 200, f"Login failed for {expected_role}: {response.text}"
            data = response.json()
            assert "access_token" in data
            assert data["user"]["role"] == expected_role
            assert data["user"]["email"] == email


@pytest.mark.asyncio
async def test_role_based_dashboards_access():
    """Verify each role accesses only its designated dashboard with role-specific data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tokens = {}
        for role, email, pwd in ROLES_CREDENTIALS:
            res = await client.post("/auth/login", json={"email": email, "password": pwd})
            tokens[role] = res.json()["access_token"]

        # Student Dashboard
        res = await client.get(
            "/api/v1/dashboard/student",
            headers={"Authorization": f"Bearer {tokens['student']}"},
        )
        assert res.status_code == 200
        student_data = res.json()
        assert student_data["view"] == "student_dashboard"
        assert "recommended_mentors" in student_data
        assert "wallet" in student_data

        # Alumni Dashboard
        res = await client.get(
            "/api/v1/dashboard/alumni",
            headers={"Authorization": f"Bearer {tokens['alumni']}"},
        )
        assert res.status_code == 200
        alumni_data = res.json()
        assert alumni_data["view"] == "alumni_dashboard"
        assert "incoming_requests" in alumni_data
        assert alumni_data["stats"]["band"] in ["rising", "trusted", "top_rated"]

        # Faculty Dashboard
        res = await client.get(
            "/api/v1/dashboard/faculty",
            headers={"Authorization": f"Bearer {tokens['faculty']}"},
        )
        assert res.status_code == 200
        faculty_data = res.json()
        assert faculty_data["view"] == "faculty_dashboard"
        assert faculty_data["user"]["verified_faculty_badge"] is True

        # Recruiter Dashboard
        res = await client.get(
            "/api/v1/dashboard/recruiter",
            headers={"Authorization": f"Bearer {tokens['recruiter']}"},
        )
        assert res.status_code == 200
        recruiter_data = res.json()
        assert recruiter_data["view"] == "recruiter_dashboard"
        assert "hiring_pipeline" in recruiter_data

        # Founder Dashboard
        res = await client.get(
            "/api/v1/dashboard/founder",
            headers={"Authorization": f"Bearer {tokens['founder']}"},
        )
        assert res.status_code == 200
        founder_data = res.json()
        assert founder_data["view"] == "founder_dashboard"
        assert founder_data["user"]["verified_employer_badge"] is True

        # Admin Dashboard
        res = await client.get(
            "/api/v1/dashboard/admin",
            headers={"Authorization": f"Bearer {tokens['admin']}"},
        )
        assert res.status_code == 200
        admin_data = res.json()
        assert admin_data["view"] == "admin_dashboard"
        assert admin_data["kpis"]["total_students"] >= 50
        assert "verification_queue" in admin_data
        assert "skill_gaps" in admin_data


@pytest.mark.asyncio
async def test_unauthorized_dashboard_calls_return_403():
    """Verify that RBAC middleware strictly rejects cross-role access with HTTP 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get student and alumni tokens
        res_stu = await client.post(
            "/auth/login",
            json={"email": "aarav.sharma@iiitd.ac.in", "password": "demo1234"},
        )
        student_token = res_stu.json()["access_token"]

        res_alm = await client.post(
            "/auth/login",
            json={"email": "vikram.malhotra@alumni.iiitd.ac.in", "password": "demo1234"},
        )
        alumni_token = res_alm.json()["access_token"]

        # 1. Student attempts Admin dashboard -> 403 Forbidden
        res = await client.get(
            "/api/v1/dashboard/admin",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res.status_code == 403
        assert "Access forbidden" in res.json()["detail"]

        # 2. Student attempts Recruiter dashboard -> 403 Forbidden
        res = await client.get(
            "/api/v1/dashboard/recruiter",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res.status_code == 403

        # 3. Alumni attempts Student dashboard -> 403 Forbidden
        res = await client.get(
            "/api/v1/dashboard/student",
            headers={"Authorization": f"Bearer {alumni_token}"},
        )
        assert res.status_code == 403

        # 4. Alumni attempts Admin dashboard -> 403 Forbidden
        res = await client.get(
            "/api/v1/dashboard/admin",
            headers={"Authorization": f"Bearer {alumni_token}"},
        )
        assert res.status_code == 403

        # 5. Missing token -> 401 Unauthorized
        res = await client.get("/api/v1/dashboard/admin")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_notification_center_f35():
    """Verify notification center listing, unread count, and mark-read operations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_login = await client.post(
            "/auth/login",
            json={"email": "aarav.sharma@iiitd.ac.in", "password": "demo1234"},
        )
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List notifications
        res = await client.get("/api/v1/notifications", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "unread_count" in data
        assert "notifications" in data
        assert len(data["notifications"]) >= 1

        notif_id = data["notifications"][0]["id"]

        # Mark single as read
        patch_res = await client.patch(f"/api/v1/notifications/{notif_id}/read", headers=headers)
        assert patch_res.status_code == 200

        # Mark all as read
        mark_all_res = await client.post("/api/v1/notifications/mark-all-read", headers=headers)
        assert mark_all_res.status_code == 200
        assert "marked_read_count" in mark_all_res.json()

        # Re-check unread count is 0
        recheck = await client.get("/api/v1/notifications", headers=headers)
        assert recheck.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_demo_mode_switcher_and_reset_f36():
    """Verify demo persona listing, 1-click login-as, and database reset."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch personas
        res = await client.get("/api/v1/demo/personas")
        assert res.status_code == 200
        data = res.json()
        assert data["demo_mode"] is True
        assert len(data["personas"]) == 6

        # 2. 1-Click Login As Alumni
        res_login = await client.post(
            "/api/v1/demo/login-as",
            json={"role": "alumni"},
        )
        assert res_login.status_code == 200
        alumni_auth = res_login.json()
        assert "access_token" in alumni_auth
        assert alumni_auth["user"]["role"] == "alumni"

        # 3. Reset Demo Database
        res_reset = await client.post("/api/v1/demo/reset")
        assert res_reset.status_code == 200
        assert res_reset.json()["status"] == "success"
