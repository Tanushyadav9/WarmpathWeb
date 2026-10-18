"""
backend/app/core/security.py - Security, password hashing, and JWT tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(subject: str, claims: Optional[Dict[str, Any]] = None, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if claims:
        to_encode.update(claims)

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AppError(code="token_expired", message="Token has expired", status_code=401)
    except jwt.InvalidTokenError:
        raise AppError(code="token_invalid", message="Invalid token", status_code=401)


DEFAULT_DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"


def get_current_user_id(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        data = decode_token(token)
        return str(data.get("sub", DEFAULT_DEMO_USER_ID))

    user_header = request.headers.get("X-User-Id")
    if user_header:
        return user_header

    return DEFAULT_DEMO_USER_ID


def get_current_user_claims(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        return decode_token(token)
    return {}


def require_role(*allowed_roles: str):
    def role_checker(request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            claims = decode_token(token)
            user_role = claims.get("role")
            if user_role and user_role not in allowed_roles:
                raise AppError(
                    code="access_denied",
                    message=f"Access denied for role: {user_role}. Required: {', '.join(allowed_roles)}",
                    status_code=403,
                )
        return True
    return role_checker

