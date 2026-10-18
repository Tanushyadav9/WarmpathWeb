"""Pydantic schemas for authentication, password validation, OTPs, and consent tracking."""
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.sanitization import sanitize_text


class UserRegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password with min 8 chars, 1 uppercase, 1 lowercase, 1 number")
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field("student", description="'student', 'alumnus', 'faculty', 'recruiter'")
    terms_accepted: bool = Field(True, description="Acceptance of platform terms & DPDP privacy policy")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        cleaned = sanitize_text(v)
        if not cleaned or len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = {"student", "alumnus", "faculty", "recruiter"}
        role_clean = v.strip().lower()
        if role_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {sorted(list(valid_roles))}")
        return role_clean


class UserLoginInput(BaseModel):
    email: EmailStr
    password: str


class OTPRequestInput(BaseModel):
    email: EmailStr
    purpose: str = Field("login", description="'login' or 'verification'")


class OTPVerifyInput(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=10)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: str


class ConsentUpdateInput(BaseModel):
    terms_of_service: bool = True
    privacy_policy: bool = True
    data_processing: bool = True
    version: str = "v1.0"


class ConsentResponse(BaseModel):
    user_id: str
    consents: Dict[str, Any]
    recorded_at: str


class DataExportResponse(BaseModel):
    user: Dict[str, Any]
    profiles: Dict[str, Any] = {}
    requests: List[Dict[str, Any]] = []
    vouches: List[Dict[str, Any]] = []
    ratings: List[Dict[str, Any]] = []
    consents: List[Dict[str, Any]] = []
    export_timestamp: str
