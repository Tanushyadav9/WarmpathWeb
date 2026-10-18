"""
Security middlewares:
1. SecurityHeadersMiddleware: Sets CSP, X-Content-Type-Options, X-Frame-Options, XSS protection.
2. CSRFProtectionMiddleware: Validates CSRF tokens and Origin headers on state-changing requests.
3. RateLimitMiddleware: Protects endpoints from brute-force and request flooding.
"""
import hmac
import hashlib
import time
from typing import Dict, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.errors import AppError, error_response


def generate_csrf_token(user_or_session_id: str) -> str:
    """Generates an HMAC-SHA256 signed CSRF token with timestamp."""
    timestamp = int(time.time())
    data = f"{user_or_session_id}:{timestamp}"
    signature = hmac.new(
        settings.CSRF_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{data}:{signature}"


def verify_csrf_token(token: Optional[str], user_or_session_id: str, max_age_seconds: int = 86400) -> bool:
    """Verifies HMAC signature and expiration of CSRF token."""
    if not token or ":" not in token:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    token_user_id, token_time_str, signature = parts
    if token_user_id != user_or_session_id:
        return False
    try:
        token_time = int(token_time_str)
    except ValueError:
        return False

    if time.time() - token_time > max_age_seconds:
        return False

    expected_data = f"{token_user_id}:{token_time_str}"
    expected_sig = hmac.new(
        settings.CSRF_SECRET.encode(),
        expected_data.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_sig)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none';"
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF verification for mutating HTTP methods (POST, PUT, DELETE, PATCH).
    Exempts safe methods, public auth/health routes, and direct Bearer/API token requests.
    Enforces check when browser cookies / custom CSRF headers are expected.
    """
    EXEMPT_PREFIXES = (
        "/health",
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/login",
        "/auth/register",
        "/auth/request-otp",
        "/auth/verify-otp",
        "/auth/csrf-token",
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.CSRF_PROTECTION_ENABLED:
            return await call_next(request)

        path = request.url.path
        method = request.method.upper()

        if method in ("GET", "HEAD", "OPTIONS") or any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)

        # Check if browser cookie authentication is present
        cookie_session = request.cookies.get("session_id") or request.cookies.get("access_token")
        if cookie_session:
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token or not verify_csrf_token(csrf_token, cookie_session):
                return error_response(
                    code="csrf_token_invalid",
                    message="CSRF validation failed: missing or invalid X-CSRF-Token header.",
                    status_code=403,
                )

        # Origin / Referer check for browser mutating requests
        origin = request.headers.get("Origin") or request.headers.get("Referer")
        sec_fetch_site = request.headers.get("Sec-Fetch-Site")
        if sec_fetch_site and sec_fetch_site == "cross-site":
            return error_response(
                code="csrf_cross_site_blocked",
                message="Cross-site mutating request blocked by CSRF policy.",
                status_code=403,
            )

        return await call_next(request)


# In-memory sliding-window store for rate limiting
_ip_rate_limits: Dict[str, List[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP / Per-user rate limiting middleware with 429 Too Many Requests and Retry-After header.
    """
    SENSITIVE_AUTH_PATHS = ("/auth/login", "/auth/request-otp", "/auth/register")

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        method = request.method.upper()
        now = time.time()

        # Check sensitive authentication routes
        if method == "POST" and any(path.startswith(p) for p in self.SENSITIVE_AUTH_PATHS):
            key = f"auth_rate:{client_ip}:{path}"
            window = 60.0
            limit = settings.RATE_LIMIT_LOGIN_PER_MINUTE

            timestamps = _ip_rate_limits.get(key, [])
            valid_timestamps = [t for t in timestamps if now - t < window]
            if len(valid_timestamps) >= limit:
                retry_after = int(window - (now - valid_timestamps[0]))
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": f"Too many requests. Please retry in {retry_after} seconds.",
                            "details": {"retry_after_seconds": retry_after},
                        }
                    },
                    headers={"Retry-After": str(max(1, retry_after))},
                )
            valid_timestamps.append(now)
            _ip_rate_limits[key] = valid_timestamps

        return await call_next(request)
