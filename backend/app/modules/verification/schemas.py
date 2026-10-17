"""
backend/app/modules/verification/schemas.py - Verification Pydantic Schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, EmailStr, Field


class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str = "alumni_registration"


class SendOtpResponse(BaseModel):
    success: bool = True
    message: str
    email: str
    demo_otp: Optional[str] = None


class RegisterAlumniRequest(BaseModel):
    role: str = Field(default="alumni")  # alumni or faculty
    full_name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    institution_id: int
    batch: int = Field(ge=1970, le=2035)
    branch: str = Field(default="Computer Science")
    otp_code: str = Field(min_length=4)
    company: Optional[str] = None
    headline: Optional[str] = None


class RegisterEmployerRequest(BaseModel):
    role: str = Field(default="recruiter")  # recruiter or founder
    full_name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    company: str = Field(min_length=2)
    headline: Optional[str] = None
    cin: Optional[str] = None
    gstin: Optional[str] = None
    otp_code: str = Field(min_length=4)


class DocumentUploadRequest(BaseModel):
    document_ref: str
    document_type: str = "degree_certificate"  # degree_certificate, old_id_card, provisional_degree
    notes: Optional[str] = None


class RequestPeerVouchRequest(BaseModel):
    voucher_emails: List[EmailStr] = Field(min_length=2, max_length=5)
    message: Optional[str] = None



class RespondPeerVouchRequest(BaseModel):
    vouch_id: uuid.UUID
    action: str = Field(pattern="^(approve|reject)$")
    comment: Optional[str] = None


class AdminVerifyActionRequest(BaseModel):
    request_id: uuid.UUID
    action: str = Field(pattern="^(approve|reject)$")
    reason: str = Field(min_length=3)


class RosterPreviewRow(BaseModel):
    line: int
    name: str
    email: str
    batch: int
    branch: Optional[str] = None
    roll_number: Optional[str] = None


class RosterErrorRow(BaseModel):
    line: int
    error: str
    data: Dict[str, Any]


class RosterPreviewResponse(BaseModel):
    total_rows: int
    valid_count: int
    error_count: int
    valid_preview: List[RosterPreviewRow]
    error_rows: List[RosterErrorRow]


class RosterUploadRequest(BaseModel):
    institution_id: int
    csv_content: str
    replace_existing: bool = False


class OpportunityCreateRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=10)
    type: str = Field(default="job")  # job, referral, hackathon, event
    company: Optional[str] = None
    location: Optional[str] = "Bengaluru / Remote"
    skills: List[str] = Field(default_factory=list)
    college_affinity_id: Optional[int] = None
    url: Optional[str] = None


class VerificationStatusResponse(BaseModel):
    user_id: uuid.UUID
    role: str
    verification_level: str
    trust_score: float
    badge_label: str
    badge_color: str
    is_reverification_due: bool
    last_verified_at: Optional[datetime] = None
    next_reverification_at: Optional[datetime] = None
