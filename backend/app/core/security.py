"""
backend/app/core/security.py - Security, password hashing, and JWT tokens.
Supports Argon2 with seamless, secure PBKDF2-HMAC-SHA256 standard library fallback.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from typing import Any, Dict, Optional
import jwt

from app.core.config import settings
from app.core.errors import AppError


def hash_password(password: str) -> str:
    """Hash password using Argon2 if available, or secure PBKDF2-HMAC-SHA256."""
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        return ph.hash(password)
    except ImportError:
        salt = os.urandom(16).hex()
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()
        return f"pbkdf2:sha256:{salt}:{pwd_hash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed string."""
    if hashed_password.startswith("pbkdf2:sha256:"):
        try:
            _, _, salt, expected_hash = hashed_password.split(":")
            calc_hash = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                100_000,
            ).hex()
            return hmac.compare_digest(expected_hash, calc_hash)
        except Exception:
            return False

    try:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError
        ph = PasswordHasher()
        return ph.verify(hashed_password, plain_password)
    except Exception:
        return False


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
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
