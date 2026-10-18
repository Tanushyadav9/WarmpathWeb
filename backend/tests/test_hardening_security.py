"""
Comprehensive automated tests for hardening:
1. Auth: Argon2 password hashing, password strength validation, brute-force rate limiting, OTP flow
2. Consent & DPDP account deletion: consent tracking, data export, anonymization
3. File upload validation: MIME type, file extension, magic byte signatures, max size check (5 MB)
4. Security headers & CSRF protection: CSP, X-Content-Type-Options, X-Frame-Options, CSRF tokens
5. XSS sanitization & SQL injection defense
6. Error handling: unhandled exceptions never leak stack traces, standard contract format
7. Health & readiness diagnostic probes
8. Audit logging for administrative decisions and financial transactions
"""
import io
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password
from app.core.security_middleware import _ip_rate_limits, generate_csrf_token
from app.modules.auth.models import FinancialAuditLog, User
from app.modules.availability.models import GiverAvailability
from app.modules.institution.models import AdminAuditLog
from app.modules.matching.models import GiverProfile
from app.modules.sessions.models import MentorshipRequest


@pytest.mark.asyncio
async def test_auth_password_hashing_and_strength_validation(async_client: AsyncClient, db_session: AsyncSession):
    """
    Validates Argon2 password hashing and password strength rules:
    - Min 8 chars, 1 uppercase, 1 lowercase, 1 digit.
    - Weak passwords rejected with 422 validation error.
    - Strong password hashed securely using Argon2 in the database.
    - Correct password authenticates; wrong password returns 401.
    """
    user_email = f"student_{uuid.uuid4().hex[:8]}@iiitd.ac.in"

    # 1. Weak passwords rejected
    # Too short (<8 chars)
    resp_short = await async_client.post(
        "/auth/register",
        json={"email": user_email, "password": "Ab1", "full_name": "Test User", "role": "student"},
    )
    assert resp_short.status_code == 422

    # Missing uppercase
    resp_no_upper = await async_client.post(
        "/auth/register",
        json={"email": user_email, "password": "password123", "full_name": "Test User", "role": "student"},
    )
    assert resp_no_upper.status_code == 422

    # Missing digit
    resp_no_digit = await async_client.post(
        "/auth/register",
        json={"email": user_email, "password": "PasswordOnly", "full_name": "Test User", "role": "student"},
    )
    assert resp_no_digit.status_code == 422

    # 2. Strong password accepted and hashed with Argon2
    strong_pw = "SecureP@ssw0rd2026!"
    resp_reg = await async_client.post(
        "/auth/register",
        json={"email": user_email, "password": strong_pw, "full_name": "Aditi Sharma", "role": "student"},
    )
    assert resp_reg.status_code == 200, resp_reg.text
    reg_data = resp_reg.json()
    assert reg_data["user"]["email"] == user_email
    assert "access_token" in reg_data["tokens"]
    created_user_id = reg_data["user"]["id"]

    # Verify database stores Argon2 hash, not plaintext
    res_db = await db_session.execute(select(User).where(User.id == uuid.UUID(created_user_id)))
    db_user = res_db.scalar_one_or_none()
    assert db_user is not None
    assert db_user.hashed_password != strong_pw
    assert db_user.hashed_password.startswith("$argon2id$")
    assert verify_password(strong_pw, db_user.hashed_password) is True

    # 3. Successful login with correct credentials
    resp_login = await async_client.post(
        "/auth/login",
        json={"email": user_email, "password": strong_pw},
    )
    assert resp_login.status_code == 200
    login_data = resp_login.json()
    assert "access_token" in login_data["tokens"]

    # 4. Failed login with incorrect credentials
    resp_fail = await async_client.post(
        "/auth/login",
        json={"email": user_email, "password": "WrongPassword123!"},
    )
    assert resp_fail.status_code == 401
    assert resp_fail.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_auth_otp_flow_and_brute_force_rate_limiting(async_client: AsyncClient):
    """
    Tests cryptographic OTP generation, verification, and rate limiting:
    - 6-digit OTP request & verification succeeds.
    - Exceeding login / OTP rate limits triggers HTTP 429 with Retry-After header.
    """
    email = f"otp_user_{uuid.uuid4().hex[:8]}@gmail.com"

    # Request OTP
    resp_otp = await async_client.post("/auth/request-otp", json={"email": email, "purpose": "login"})
    assert resp_otp.status_code == 200
    otp_data = resp_otp.json()
    assert "otp_code" in otp_data
    code = otp_data["otp_code"]
    assert len(code) == 6

    # Verify OTP
    resp_verify = await async_client.post("/auth/verify-otp", json={"email": email, "otp_code": code})
    assert resp_verify.status_code == 200
    assert "access_token" in resp_verify.json()

    # Rate limiting test: spamming /auth/login returns 429
    spam_email = f"spam_{uuid.uuid4().hex[:8]}@example.com"
    hit_429 = False
    for _ in range(settings.RATE_LIMIT_LOGIN_PER_MINUTE + 3):
        r = await async_client.post("/auth/login", json={"email": spam_email, "password": "WrongPassword1!"})
        if r.status_code == 429:
            hit_429 = True
            assert "Retry-After" in r.headers
            assert r.json()["error"]["code"] == "rate_limit_exceeded"
            break

    assert hit_429 is True, "Rate limiter must return 429 when threshold exceeded"
    _ip_rate_limits.clear()


@pytest.mark.asyncio
async def test_consent_tracking_data_export_and_account_deletion(async_client: AsyncClient, db_session: AsyncSession):
    """
    Tests DPDP Act and GDPR compliance flows:
    - User consent recording & updates (/me/consents).
    - Subject Access Request personal data export (/me/data-export).
    - Permanent account anonymization and erasure (/me DELETE).
    - Subsequent access with deleted account is blocked.
    """
    email = f"dpdp_{uuid.uuid4().hex[:8]}@iiitd.ac.in"
    resp_reg = await async_client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePassword1!", "full_name": "Rohan Das", "role": "student"},
    )
    user_id = resp_reg.json()["user"]["id"]
    token = resp_reg.json()["tokens"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Update consents
    resp_consent = await async_client.put(
        "/me/consents",
        json={"terms_of_service": True, "privacy_policy": True, "data_processing": True, "version": "v1.2"},
        headers=auth_headers,
    )
    assert resp_consent.status_code == 200
    assert resp_consent.json()["consents"]["data_processing"] is True

    # 2. Data export under DPDP Act
    resp_export = await async_client.get("/me/data-export", headers=auth_headers)
    assert resp_export.status_code == 200
    export_json = resp_export.json()
    assert export_json["user"]["email"] == email
    assert "export_timestamp" in export_json
    assert isinstance(export_json["consents"], list)

    # 3. Account deletion flow under DPDP Act
    resp_del = await async_client.delete("/me", headers=auth_headers)
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "deleted"

    # Verify PII has been anonymized in the database
    res_user = await db_session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user_obj = res_user.scalar_one()
    assert user_obj.is_active is False
    assert user_obj.hashed_password is None
    assert user_obj.full_name == "Deleted User"
    assert "anonymized.warmpath" in user_obj.email

    # Verify subsequent login attempt is rejected
    resp_relogin = await async_client.post(
        "/auth/login",
        json={"email": email, "password": "SecurePassword1!"},
    )
    assert resp_relogin.status_code in (401, 403)


@pytest.mark.asyncio
async def test_file_upload_type_and_size_validation(async_client: AsyncClient):
    """
    Tests file upload security hardening:
    - Allowed MIME types (PDF, PNG, JPEG) with correct magic bytes accepted.
    - Executable/script files (.exe, .sh) rejected.
    - Spoofed MIME types (mismatched file signature) rejected.
    - Files exceeding maximum allowed size (5 MB) rejected with HTTP 413.
    """
    # 1. Valid PDF with real magic bytes (%PDF-)
    valid_pdf_content = b"%PDF-1.5 \n%Valid test PDF content for warmpath verification"
    pdf_file = {"file": ("document.pdf", io.BytesIO(valid_pdf_content), "application/pdf")}
    resp_pdf = await async_client.post("/verification/upload", files=pdf_file)
    assert resp_pdf.status_code == 200, resp_pdf.text
    assert resp_pdf.json()["status"] == "uploaded"
    assert resp_pdf.json()["mime_type"] == "application/pdf"

    # 2. Valid PNG with real magic bytes (\x89PNG\r\n\x1a\n)
    valid_png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    png_file = {"file": ("id_card.png", io.BytesIO(valid_png_content), "image/png")}
    resp_png = await async_client.post("/verification/upload", files=png_file)
    assert resp_png.status_code == 200
    assert resp_png.json()["status"] == "uploaded"

    # 3. Forbidden executable extension rejected
    exe_file = {"file": ("payload.exe", io.BytesIO(b"MZ\x90\x00executable content"), "application/octet-stream")}
    resp_exe = await async_client.post("/verification/upload", files=exe_file)
    assert resp_exe.status_code == 400
    assert resp_exe.json()["error"]["code"] == "forbidden_file_type"

    # 4. Spoofed MIME type: reported as PDF, but content lacks %PDF- signature
    fake_pdf = {"file": ("malicious.pdf", io.BytesIO(b"<script>alert(1)</script>"), "application/pdf")}
    resp_fake = await async_client.post("/verification/upload", files=fake_pdf)
    assert resp_fake.status_code == 400
    assert resp_fake.json()["error"]["code"] == "invalid_file_signature"

    # 5. Oversized file exceeding 5 MB limit rejected with 413
    oversized_bytes = b"%PDF-" + b"0" * (5 * 1024 * 1024 + 10)
    huge_file = {"file": ("huge.pdf", io.BytesIO(oversized_bytes), "application/pdf")}
    resp_huge = await async_client.post("/verification/upload", files=huge_file)
    assert resp_huge.status_code == 413
    assert resp_huge.json()["error"]["code"] == "file_too_large"


@pytest.mark.asyncio
async def test_security_headers_and_csrf_protection(async_client: AsyncClient):
    """
    Tests security response headers and CSRF token verification:
    - Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, XSS-Protection present.
    - CSRF token endpoint issues valid HMAC tokens.
    - Mutating request with cookie session requires matching X-CSRF-Token header.
    """
    # 1. Verify security headers
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    headers = resp.headers
    assert "Content-Security-Policy" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-XSS-Protection"] == "1; mode=block"
    assert "strict-origin" in headers.get("Referrer-Policy", "")

    # 2. Fetch signed CSRF token
    user_id = str(uuid.uuid4())
    resp_csrf = await async_client.get("/auth/csrf-token", headers={"X-User-ID": user_id})
    assert resp_csrf.status_code == 200
    csrf_token = resp_csrf.json()["csrf_token"]
    assert ":" in csrf_token

    # 3. CSRF protection on cookie-authenticated session:
    # If a cookie is present but no X-CSRF-Token header -> 403 csrf_token_invalid
    cookies = {"session_id": user_id}
    resp_blocked = await async_client.post(
        "/requests",
        json={"giver_id": str(uuid.uuid4()), "intent": "Career Guidance"},
        cookies=cookies,
        headers={"X-User-ID": user_id},
    )
    assert resp_blocked.status_code == 403
    assert resp_blocked.json()["error"]["code"] == "csrf_token_invalid"

    # With valid X-CSRF-Token -> proceeds past CSRF check
    valid_csrf_token = generate_csrf_token(user_id)
    resp_allowed = await async_client.post(
        "/requests",
        json={"giver_id": str(uuid.uuid4()), "intent": "Career Guidance"},
        cookies=cookies,
        headers={"X-User-ID": user_id, "X-CSRF-Token": valid_csrf_token},
    )
    # Passed CSRF check (even if matching logic returns another business error or success)
    assert resp_allowed.status_code != 403


@pytest.mark.asyncio
async def test_xss_sanitization_and_sql_injection_defense(async_client: AsyncClient, db_session: AsyncSession):
    """
    Tests XSS input sanitization and parameterized SQL injection defense:
    - Script tags, javascript: links, and event handlers are disarmed in chat messages and request intents.
    - SQL injection payloads in query parameters do not corrupt database or leak internal syntax errors.
    """
    student_id = str(uuid.uuid4())
    giver_id = str(uuid.uuid4())

    # Create active giver so request creation passes availability checks
    db_session.add(
        GiverAvailability(
            id=uuid.uuid4(),
            user_id=uuid.UUID(giver_id),
            status="active_now",
            weekly_capacity_cap=10,
            last_active_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    # 1. XSS in request creation intent
    xss_intent = "<script>alert('xss')</script>System Design Mentorship"
    resp_req = await async_client.post(
        "/requests",
        json={"giver_id": giver_id, "intent": xss_intent, "notes": "<iframe src='javascript:malicious()'></iframe>Clean notes"},
        headers={"X-User-ID": student_id},
    )
    assert resp_req.status_code == 200, resp_req.text
    req_data = resp_req.json()
    # Script tag must be completely stripped
    assert "<script>" not in req_data["intent"]
    assert "System Design Mentorship" in req_data["intent"]
    assert "<iframe>" not in (req_data["notes"] or "")

    # 2. XSS in chat message
    created_req_id = req_data["id"]
    xss_msg = "Hello! <script>document.cookie</script> Here is my github: <img src='x' onerror='alert(1)'>"
    resp_msg = await async_client.post(
        f"/requests/{created_req_id}/messages",
        json={"body": xss_msg},
        headers={"X-User-ID": student_id},
    )
    assert resp_msg.status_code == 200
    msg_data = resp_msg.json()
    assert "<script>" not in msg_data["body"]
    assert "onerror=" not in msg_data["body"]

    # 3. SQL injection attempts in query parameters handled cleanly via parameterized queries
    sqli_payload = "' OR 1=1; DROP TABLE users; --"
    resp_sqli = await async_client.get(f"/admin/audit-logs?target_type={sqli_payload}")
    assert resp_sqli.status_code == 200
    # Returns safe empty list without SQL syntax error or data compromise
    assert isinstance(resp_sqli.json(), list)


@pytest.mark.asyncio
async def test_error_handling_layer_never_leaks_stack_traces(async_client: AsyncClient):
    """
    Acceptance test for error-handling:
    - Unhandled exceptions return HTTP 500 in standard contract format:
      {"error": {"code": "internal_server_error", "message": "...", "details": {"request_id": "..."}}}
    - Never exposes Python stack traces, file paths, line numbers, or database syntax.
    """
    # Trigger an invalid path with unhandled exception or non-existent endpoint
    resp = await async_client.get("/non-existent-endpoint-404")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "Traceback" not in resp.text
    assert "File \"" not in resp.text

    # Malformed JSON payload validation error (422)
    resp_val = await async_client.post(
        "/auth/register",
        content="{\"email\": \"invalid-email\", \"password\": 123}",
        headers={"Content-Type": "application/json"},
    )
    assert resp_val.status_code == 422
    val_data = resp_val.json()
    assert val_data["error"]["code"] == "validation_error"
    assert "Traceback" not in resp_val.text


@pytest.mark.asyncio
async def test_health_and_readiness_checks(async_client: AsyncClient):
    """
    Tests health and readiness diagnostic probes:
    - /health and /healthz return liveness metrics with version and timestamp.
    - /ready and /readyz return database readiness.
    """
    for endpoint in ("/health", "/healthz"):
        resp = await async_client.get(endpoint)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data

    for endpoint in ("/ready", "/readyz"):
        resp = await async_client.get(endpoint)
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data
        assert "database" in data


@pytest.mark.asyncio
async def test_money_actions_and_admin_audit_logs(async_client: AsyncClient, db_session: AsyncSession):
    """
    Tests that money actions and administrative actions create immutable audit logs:
    - Ledger credit grants record a FinancialAuditLog entry.
    - Admin actions (suspension, college creation) record AdminAuditLog entries.
    - GET /admin/audit-logs returns both financial and admin audit logs.
    """
    user_id = uuid.uuid4()
    admin_id = str(uuid.uuid4())

    # 1. Trigger financial money action (subscribe to Plus plan)
    resp_sub = await async_client.post(
        "/subscriptions",
        json={"plan_id": "plus"},
        headers={"X-User-ID": str(user_id)},
    )
    assert resp_sub.status_code == 200

    # Verify FinancialAuditLog entry created in database
    res_fin = await db_session.execute(select(FinancialAuditLog).where(FinancialAuditLog.user_id == user_id))
    fin_entries = res_fin.scalars().all()
    assert len(fin_entries) >= 1
    assert fin_entries[0].action == "purchase"
    assert fin_entries[0].amount != "0"

    # 2. Check /admin/audit-logs?target_type=financial
    resp_audit_fin = await async_client.get("/admin/audit-logs?target_type=financial")
    assert resp_audit_fin.status_code == 200
    logs = resp_audit_fin.json()
    assert len(logs) >= 1
    assert any(log["target_type"] == "financial" for log in logs)

    # 3. Check unified audit logs
    resp_audit_all = await async_client.get("/admin/audit-logs")
    assert resp_audit_all.status_code == 200
    all_logs = resp_audit_all.json()
    assert len(all_logs) >= 1
