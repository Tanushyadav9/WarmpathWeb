"""
backend/app/modules/verification/router.py - Layered Verification Endpoints.
Implements F2 (Alumni & Employer multi-channel verification) and F3 (Badges & Levels).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit_event
from app.core.db import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.models import (
    AlumniRosterRecord,
    AuditLog,
    Availability,
    Capacity,
    CreditWallet,
    GiverProfile,
    Institution,
    Opportunity,
    PeerVouchRequest,
    StudentProfile,
    User,
    VerificationRequest,
    utc_now,
)
from app.core.notifications import create_notification
from app.core.security import create_access_token, hash_password
from app.modules.verification.schemas import (
    AdminVerifyActionRequest,
    DocumentUploadRequest,
    OpportunityCreateRequest,
    RegisterAlumniRequest,
    RegisterEmployerRequest,
    RequestPeerVouchRequest,
    RespondPeerVouchRequest,
    RosterErrorRow,
    RosterPreviewResponse,
    RosterPreviewRow,
    RosterUploadRequest,
    SendOtpRequest,
    SendOtpResponse,
    VerificationStatusResponse,
)
from app.modules.verification.service import VerificationService

router = APIRouter(prefix="/api/v1", tags=["verification"])



# --- 1. Send OTP ---

@router.post("/verification/send-otp", response_model=SendOtpResponse)
async def send_otp(payload: SendOtpRequest, db: AsyncSession = Depends(get_db)):
    """Generates and returns an email OTP (displayed in debug panel in DEMO_MODE)."""
    service = VerificationService(db)
    code = await service.generate_otp(payload.email, payload.purpose)
    await db.commit()

    return SendOtpResponse(
        success=True,
        message=f"Verification code dispatched to {payload.email}",
        email=payload.email,
        demo_otp=code,
    )


# --- 2. Register Alumni / Faculty with Layered Verification ---

@router.post("/verification/register-alumni", status_code=status.HTTP_201_CREATED)
async def register_alumni(payload: RegisterAlumniRequest, db: AsyncSession = Depends(get_db)):
    """
    Registers alumni/faculty. Matches against institution's uploaded CSV roster:
    - Match found + OTP verified -> auto-approves as 'verified_alumnus'.
    - No match -> lands in 'pending' with fallback options (document upload or peer vouches).
    """
    service = VerificationService(db)
    clean_email = payload.email.lower().strip()

    # Rule: One email maps to one account
    existing = (await db.execute(select(User).where(User.email == clean_email))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Step 1: Verify OTP
    otp_valid = await service.verify_otp(clean_email, payload.otp_code, "alumni_registration")
    if not otp_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    # Step 2: Check institution CSV roster match (email + name + batch)
    roster_match = await service.match_roster(
        institution_id=payload.institution_id,
        email=clean_email,
        full_name=payload.full_name,
        batch=payload.batch,
    )

    is_auto_approved = roster_match is not None
    ver_level = "verified_alumnus" if is_auto_approved else "pending"
    trust_score = 65.0 if is_auto_approved else 50.0
    now = utc_now()
    reverification_date = now + timedelta(days=365) if is_auto_approved else None

    # Step 3: Create User
    user = User(
        id=uuid.uuid4(),
        email=clean_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        roles=[payload.role],
        institution_id=payload.institution_id,
        batch=payload.batch,
        branch=payload.branch,
        company=payload.company or "Industry Professional",
        verification_level=ver_level,
        trust_score=trust_score,
        last_verified_at=now if is_auto_approved else None,
        next_reverification_at=reverification_date,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Associated profiles
    giver = GiverProfile(
        user_id=user.id,
        headline=payload.headline or f"{payload.role.capitalize()} at {payload.company or 'Tech'}",
        company=payload.company or "Tech",
        role_title=payload.headline or "Professional",
        weekly_capacity=2,
        band="rising",
        rating_avg=4.0,
    )
    avail = Availability(user_id=user.id, status="active_now")
    cap = Capacity(user_id=user.id, weekly_cap=2, free_monthly_cap=4)
    wallet = CreditWallet(user_id=user.id, balance=0, escrow_held=0)
    db.add_all([giver, avail, cap, wallet])

    # Verification Request record
    ver_req = VerificationRequest(
        id=uuid.uuid4(),
        user_id=user.id,
        institution_id=payload.institution_id,
        request_type="csv_auto" if is_auto_approved else "document_review",
        status="approved" if is_auto_approved else "pending",
        review_notes="Auto-matched via official institution alumni roster" if is_auto_approved else "Awaiting document upload or peer vouches",
        reviewed_at=now if is_auto_approved else None,
    )
    db.add(ver_req)

    # Audit Log: Record status transition
    audit_action = "alumni_registered_verified_csv" if is_auto_approved else "alumni_registered_pending"
    await log_audit_event(
        db=db,
        action=audit_action,
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        metadata_json={
            "role": user.role,
            "institution_id": payload.institution_id,
            "batch": payload.batch,
            "auto_approved": is_auto_approved,
        },
    )

    # Dispatched Notification
    if is_auto_approved:
        await create_notification(
            db=db,
            user_id=user.id,
            title="Verification Approved",
            message="Your credentials matched IIIT Delhi's graduation roster. You are verified as an Alumnus!",
            notif_type="verification",
        )
    else:
        await create_notification(
            db=db,
            user_id=user.id,
            title="Verification Pending",
            message="Your details are not yet in the official roster. Please upload your degree certificate or request 2 peer vouches.",
            notif_type="verification",
        )

    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        str(user.id),
        claims={"role": user.role, "email": user.email, "name": user.full_name},
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "verification_level": user.verification_level,
            "trust_score": user.trust_score,
            "batch": user.batch,
            "branch": user.branch,
        },
        "auto_approved": is_auto_approved,
        "verification_level": user.verification_level,
        "fallback_options": [] if is_auto_approved else ["document_upload", "peer_vouch"],
    }


# --- 3. Register Employer (Recruiters & Founders) ---

@router.post("/verification/register-employer", status_code=status.HTTP_201_CREATED)
async def register_employer(payload: RegisterEmployerRequest, db: AsyncSession = Depends(get_db)):
    """
    Registers recruiter or founder with company email OTP and optional CIN/GSTIN format validation.
    On valid credentials, grants 'verified_professional' badge.
    """
    service = VerificationService(db)
    clean_email = payload.email.lower().strip()

    # Check duplicate email
    existing = (await db.execute(select(User).where(User.email == clean_email))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Verify OTP
    otp_valid = await service.verify_otp(clean_email, payload.otp_code, "employer_registration")
    if not otp_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    # Validate CIN if provided
    cin_clean = None
    if payload.cin:
        is_cin_valid, cin_res = service.validate_cin(payload.cin)
        if not is_cin_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=cin_res)
        cin_clean = cin_res

    # Validate GSTIN if provided
    gstin_clean = None
    if payload.gstin:
        is_gstin_valid, gstin_res = service.validate_gstin(payload.gstin)
        if not is_gstin_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=gstin_res)
        gstin_clean = gstin_res

    now = utc_now()
    user = User(
        id=uuid.uuid4(),
        email=clean_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        roles=[payload.role],
        company=payload.company.strip(),
        cin=cin_clean,
        gstin=gstin_clean,
        verification_level="verified_professional",
        trust_score=70.0,
        last_verified_at=now,
        next_reverification_at=now + timedelta(days=365),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    giver = GiverProfile(
        user_id=user.id,
        headline=payload.headline or f"{payload.role.capitalize()} at {payload.company}",
        company=payload.company,
        role_title=payload.headline or f"Talent Partner / Founder",
        weekly_capacity=5,
        band="rising",
        rating_avg=4.5,
    )
    avail = Availability(user_id=user.id, status="active_now")
    cap = Capacity(user_id=user.id, weekly_cap=5, free_monthly_cap=10)
    wallet = CreditWallet(user_id=user.id, balance=10, escrow_held=0)
    db.add_all([giver, avail, cap, wallet])

    ver_req = VerificationRequest(
        id=uuid.uuid4(),
        user_id=user.id,
        request_type="employer_cin_gst",
        company_name=payload.company,
        cin=cin_clean,
        gstin=gstin_clean,
        status="approved",
        review_notes="Verified via corporate email OTP and statutory registry lookup",
        reviewed_at=now,
    )
    db.add(ver_req)

    # Audit Log
    await log_audit_event(
        db=db,
        action="employer_verified",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        metadata_json={
            "company": payload.company,
            "has_cin": bool(cin_clean),
            "has_gstin": bool(gstin_clean),
            "role": payload.role,
        },
    )

    await create_notification(
        db=db,
        user_id=user.id,
        title="Employer Verified",
        message=f"Your {payload.company} organization credentials have been verified. You can now post opportunities.",
        notif_type="verification",
    )

    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        str(user.id),
        claims={"role": user.role, "email": user.email, "name": user.full_name},
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "company": user.company,
            "verification_level": user.verification_level,
            "trust_score": user.trust_score,
        },
    }


# --- 4. Fallback A: Document Upload ---

@router.post("/verification/upload-document")
async def upload_document(
    payload: DocumentUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fallback A: Upload degree certificate or old ID image, queued for admin review."""
    stmt = (
        select(VerificationRequest)
        .where(VerificationRequest.user_id == current_user.id)
        .order_by(VerificationRequest.created_at.desc())
    )
    ver_req = (await db.execute(stmt)).scalars().first()

    if not ver_req:
        ver_req = VerificationRequest(
            id=uuid.uuid4(),
            user_id=current_user.id,
            institution_id=current_user.institution_id,
            request_type="document_review",
            status="pending",
        )
        db.add(ver_req)

    ver_req.document_ref = payload.document_ref
    ver_req.document_type = payload.document_type
    ver_req.status = "pending"
    ver_req.review_notes = payload.notes or "Document uploaded for manual review"

    await log_audit_event(
        db=db,
        action="verification_document_uploaded",
        resource_type="verification_request",
        resource_id=str(ver_req.id),
        user_id=current_user.id,
        metadata_json={
            "document_type": payload.document_type,
            "document_ref": payload.document_ref,
        },
    )

    await create_notification(
        db=db,
        user_id=current_user.id,
        title="Document Queued for Review",
        message="Your degree certificate / ID has been submitted to the institution admin review queue.",
        notif_type="verification",
    )

    await db.commit()
    return {
        "success": True,
        "message": "Document queued for admin review",
        "status": "pending",
    }


# --- 5. Fallback B: Peer Vouching ---

@router.post("/verification/request-peer-vouches")
async def request_peer_vouches(
    payload: RequestPeerVouchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fallback B: Request two verified alumni of the same batch to vouch for you.
    Approval requires both vouchers to confirm.
    """
    if current_user.verification_level == "verified_alumnus":
        return {"success": True, "message": "User is already verified"}

    created_vouch_ids = []
    for voucher_email in payload.voucher_emails:
        clean_v_email = voucher_email.lower().strip()
        if clean_v_email == current_user.email.lower().strip():
            continue

        stmt = select(User).where(
            and_(
                User.email == clean_v_email,
                User.verification_level.in_(["verified_alumnus", "trusted"]),
                User.institution_id == current_user.institution_id,
                User.batch == current_user.batch,
            )
        )
        voucher = (await db.execute(stmt)).scalar_one_or_none()
        if not voucher:
            continue

        vouch = PeerVouchRequest(
            id=uuid.uuid4(),
            applicant_id=current_user.id,
            voucher_id=voucher.id,
            batch=current_user.batch or 2021,
            branch=current_user.branch,
            status="pending",
            comment=payload.message or "Batchmate verification vouch request",
        )
        db.add(vouch)
        created_vouch_ids.append(str(vouch.id))

        await create_notification(
            db=db,
            user_id=voucher.id,
            title="Peer Vouch Request",
            message=f"{current_user.full_name} from your Class of {current_user.batch} requested your verification vouch.",
            notif_type="verification",
            data={"vouch_id": str(vouch.id), "applicant_id": str(current_user.id)},
        )

    await log_audit_event(
        db=db,
        action="peer_vouches_requested",
        resource_type="user",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        metadata_json={"vouchers_targeted": len(created_vouch_ids)},
    )

    await db.commit()
    return {
        "success": True,
        "message": f"Peer vouch requests sent to {len(created_vouch_ids)} verified batchmates",
        "vouch_ids": created_vouch_ids,
    }


@router.post("/verification/respond-peer-vouch")
async def respond_peer_vouch(
    payload: RespondPeerVouchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A verified alumnus approves or rejects a batchmate's peer vouch request."""
    stmt = select(PeerVouchRequest).where(
        and_(
            PeerVouchRequest.id == payload.vouch_id,
            PeerVouchRequest.voucher_id == current_user.id,
        )
    )
    vouch = (await db.execute(stmt)).scalar_one_or_none()
    if not vouch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Peer vouch request not found")

    vouch.status = payload.action
    vouch.comment = payload.comment
    vouch.responded_at = utc_now()

    await log_audit_event(
        db=db,
        action=f"peer_vouch_{payload.action}",
        resource_type="peer_vouch_request",
        resource_id=str(vouch.id),
        user_id=current_user.id,
        metadata_json={"action": payload.action, "applicant_id": str(vouch.applicant_id)},
    )

    # Check if applicant now has 2 distinct approved peer vouches
    is_now_approved = False
    if payload.action == "approve":
        approved_stmt = select(func.count(PeerVouchRequest.id)).where(
            and_(
                PeerVouchRequest.applicant_id == vouch.applicant_id,
                PeerVouchRequest.status == "approve",
            )
        )
        approved_count = (await db.execute(approved_stmt)).scalar() or 0

        if approved_count >= 2:
            applicant = (await db.execute(select(User).where(User.id == vouch.applicant_id))).scalar_one_or_none()
            if applicant and applicant.verification_level == "pending":
                applicant.verification_level = "verified_alumnus"
                applicant.trust_score = 65.0
                applicant.last_verified_at = utc_now()
                applicant.next_reverification_at = utc_now() + timedelta(days=365)
                is_now_approved = True

                await log_audit_event(
                    db=db,
                    action="alumni_verified_via_peer_vouches",
                    resource_type="user",
                    resource_id=str(applicant.id),
                    user_id=applicant.id,
                    metadata_json={"approved_vouches_count": approved_count},
                )

                await create_notification(
                    db=db,
                    user_id=applicant.id,
                    title="Peer Verification Complete!",
                    message="Two verified alumni from your batch confirmed your credentials. You are now a Verified Alumnus!",
                    notif_type="verification",
                )

    await db.commit()
    return {
        "success": True,
        "vouch_status": payload.action,
        "applicant_promoted": is_now_approved,
    }


# --- 6. Employer Opportunity Posting Guard ---

@router.post("/opportunities", status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    payload: OpportunityCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Employers post jobs, referrals, hackathons, and events.
    Strict Rule: Unverified employers (verification_level == 'pending') CANNOT post jobs.
    """
    allowed_roles = ["recruiter", "founder", "admin", "institution_admin", "alumni"]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters, founders, or alumni can post opportunities",
        )

    # Hard gate: Block unverified employers
    if current_user.verification_level == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unverified employers cannot post jobs or message students. Please complete company verification.",
        )

    opportunity = Opportunity(
        id=uuid.uuid4(),
        creator_id=current_user.id,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        company=payload.company or current_user.company or "Verified Company",
        location=payload.location,
        skills=payload.skills,
        college_affinity_id=payload.college_affinity_id or current_user.institution_id,
        url=payload.url,
        is_verified=True,
    )
    db.add(opportunity)
    await db.flush()

    await log_audit_event(
        db=db,
        action="opportunity_posted",
        resource_type="opportunity",
        resource_id=str(opportunity.id),
        user_id=current_user.id,
        metadata_json={
            "type": payload.type,
            "title": payload.title,
            "company": opportunity.company,
        },
    )

    await db.commit()
    return {
        "id": str(opportunity.id),
        "title": opportunity.title,
        "type": opportunity.type,
        "company": opportunity.company,
        "is_verified": opportunity.is_verified,
        "created_at": opportunity.created_at,
    }


# --- 7. Admin Verification Queue & Review Actions ---

@router.get("/admin/verification-queue")
async def get_verification_queue(
    current_user: User = Depends(require_roles("admin", "institution_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin review queue with pending verification requests and applicant details."""
    stmt = (
        select(VerificationRequest, User)
        .join(User, VerificationRequest.user_id == User.id)
        .where(VerificationRequest.status == "pending")
        .order_by(VerificationRequest.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    queue = []
    for req, applicant in rows:
        queue.append({
            "request_id": str(req.id),
            "user_id": str(applicant.id),
            "full_name": applicant.full_name,
            "email": applicant.email,
            "role": applicant.role,
            "batch": applicant.batch,
            "branch": applicant.branch,
            "company": applicant.company,
            "institution_id": req.institution_id,
            "request_type": req.request_type,
            "document_ref": req.document_ref,
            "document_type": req.document_type,
            "cin": req.cin,
            "gstin": req.gstin,
            "submitted_at": req.created_at,
        })

    return {"queue": queue, "total_pending": len(queue)}


@router.post("/admin/verify-action")
async def admin_verify_action(
    payload: AdminVerifyActionRequest,
    current_user: User = Depends(require_roles("admin", "institution_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin approves or rejects a pending verification request with documented reason."""
    stmt = select(VerificationRequest).where(VerificationRequest.id == payload.request_id)
    ver_req = (await db.execute(stmt)).scalar_one_or_none()
    if not ver_req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    user_stmt = select(User).where(User.id == ver_req.user_id)
    applicant = (await db.execute(user_stmt)).scalar_one_or_none()
    if not applicant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Applicant user record not found")

    ver_req.status = payload.action
    ver_req.reviewed_by = current_user.id
    ver_req.review_notes = payload.reason
    ver_req.reviewed_at = utc_now()

    if payload.action == "approve":
        target_level = "verified_professional" if applicant.role in ["recruiter", "founder"] else "verified_alumnus"
        applicant.verification_level = target_level
        applicant.trust_score = 65.0
        applicant.last_verified_at = utc_now()
        applicant.next_reverification_at = utc_now() + timedelta(days=365)

        await create_notification(
            db=db,
            user_id=applicant.id,
            title="Verification Approved by Institution Admin",
            message=f"Your verification request was approved: {payload.reason}",
            notif_type="verification",
        )
    else:
        applicant.verification_level = "pending"
        await create_notification(
            db=db,
            user_id=applicant.id,
            title="Verification Rejected",
            message=f"Your verification request was not approved: {payload.reason}",
            notif_type="verification",
        )

    await log_audit_event(
        db=db,
        action=f"admin_{payload.action}_verification",
        resource_type="verification_request",
        resource_id=str(ver_req.id),
        user_id=current_user.id,
        metadata_json={
            "action": payload.action,
            "reason": payload.reason,
            "applicant_id": str(applicant.id),
        },
    )

    await db.commit()
    return {
        "success": True,
        "request_id": str(ver_req.id),
        "status": ver_req.status,
        "user_verification_level": applicant.verification_level,
    }


# --- 8. Admin Alumni CSV Upload with Preview & Error Rows ---

@router.post("/admin/roster/preview", response_model=RosterPreviewResponse)
async def preview_roster_csv(
    request: Request,
    current_user: User = Depends(require_roles("admin", "institution_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Parses uploaded CSV text, generating preview rows and detailing all error rows
    with exact line numbers before persisting to the database.
    """
    body = await request.json()
    csv_text = body.get("csv_content", "")
    service = VerificationService(db)
    valid_rows, error_rows = service.parse_roster_csv(csv_text)

    preview_rows = [
        RosterPreviewRow(
            line=r["line"],
            name=r["name"],
            email=r["email"],
            batch=r["batch"],
            branch=r["branch"],
            roll_number=r["roll_number"],
        )
        for r in valid_rows[:10]
    ]

    error_row_objs = [
        RosterErrorRow(line=e["line"], error=e["error"], data=e["data"])
        for e in error_rows
    ]

    return RosterPreviewResponse(
        total_rows=len(valid_rows) + len(error_rows),
        valid_count=len(valid_rows),
        error_count=len(error_rows),
        valid_preview=preview_rows,
        error_rows=error_row_objs,
    )


@router.post("/admin/roster/upload")
async def upload_roster_csv(
    payload: RosterUploadRequest,
    current_user: User = Depends(require_roles("admin", "institution_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads/replaces the institution's official alumni CSV roster records.
    Filters out malformed rows and commits all valid entries.
    """
    service = VerificationService(db)
    valid_rows, error_rows = service.parse_roster_csv(payload.csv_content)

    if payload.replace_existing:
        delete_stmt = select(AlumniRosterRecord).where(
            AlumniRosterRecord.institution_id == payload.institution_id
        )
        existing_records = (await db.execute(delete_stmt)).scalars().all()
        for r in existing_records:
            await db.delete(r)

    created_records = []
    for r in valid_rows:
        rec = AlumniRosterRecord(
            id=uuid.uuid4(),
            institution_id=payload.institution_id,
            email=r["email"].lower().strip(),
            full_name=r["name"].strip(),
            batch=r["batch"],
            branch=r["branch"],
            roll_number=r["roll_number"],
        )
        db.add(rec)
        created_records.append(rec)

    await log_audit_event(
        db=db,
        action="admin_uploaded_alumni_csv",
        resource_type="institution",
        resource_id=str(payload.institution_id),
        user_id=current_user.id,
        metadata_json={
            "valid_imported": len(created_records),
            "errors_skipped": len(error_rows),
            "replaced_existing": payload.replace_existing,
        },
    )

    await db.commit()
    return {
        "success": True,
        "records_imported": len(created_records),
        "errors_skipped": len(error_rows),
        "error_details": error_rows,
    }


# --- 9. Public / Authenticated Verification Status & Badge View ---

@router.get("/verification/status", response_model=VerificationStatusResponse)
async def get_verification_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns user's verification badge, level, and annual re-verification reminder status.
    Rule: Never displays roll number or raw contact details publicly.
    """
    is_due = False
    if current_user.next_reverification_at:
        target_dt = current_user.next_reverification_at
        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=timezone.utc)
        is_due = utc_now() >= target_dt


    # Dynamic badge mapping
    badges = {
        "pending": ("Pending Verification", "bg-amber-100 text-amber-800 border-amber-300"),
        "verified_alumnus": ("Verified Alumnus", "bg-teal-100 text-teal-800 border-teal-300"),
        "verified_professional": ("Verified Professional", "bg-purple-100 text-purple-800 border-purple-300"),
        "trusted": ("Trusted Giver", "bg-emerald-100 text-emerald-800 border-emerald-300"),
        "verified_employer": ("Verified Employer", "bg-blue-100 text-blue-800 border-blue-300"),
    }
    label, color = badges.get(
        current_user.verification_level,
        ("Unverified", "bg-slate-100 text-slate-800 border-slate-300"),
    )

    return VerificationStatusResponse(
        user_id=current_user.id,
        role=current_user.role,
        verification_level=current_user.verification_level,
        trust_score=current_user.trust_score,
        badge_label=label,
        badge_color=color,
        is_reverification_due=is_due,
        last_verified_at=current_user.last_verified_at,
        next_reverification_at=current_user.next_reverification_at,
    )
