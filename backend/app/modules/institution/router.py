import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.file_upload import validate_and_read_file
from app.core.security import get_current_user_id
from app.modules.institution.schemas import (
    DashboardOverviewResponse,
    SkillGapItem,
    VerificationCreateInput,
    VerificationResponse,
    VerificationReviewInput,
    ReportCreateInput,
    ReportResponse,
    ReportResolveInput,
    TrustLayersResponse,
    SessionOutcomeCreateInput,
    SessionOutcomeResponse,
    NetworkGraphResponse,
    PilotMetricsResponse,
    CollegeCreateInput,
    CollegeEnableInput,
    CollegeResponse,
)
from app.modules.institution.service import institution_service

router = APIRouter(tags=["institution"])


# --- 1. Dashboard & Metrics Endpoints ---

@router.get("/admin/dashboard/overview", response_model=DashboardOverviewResponse, summary="Institution overview of requests, fulfillment, givers, and ratings")
async def get_admin_dashboard_overview(
    college: Optional[str] = Query(None, description="Optional college institution filter"),
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.get_dashboard_overview(db, college=college)


@router.get("/admin/dashboard/export-csv", summary="Export institution metrics as CSV")
async def get_admin_dashboard_export_csv(
    college: Optional[str] = Query(None, description="Optional college institution filter"),
    db: AsyncSession = Depends(get_db),
):
    csv_content = await institution_service.export_dashboard_csv(db, college=college)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=institution_metrics.csv"},
    )


@router.get("/admin/dashboard/skill-gap", response_model=List[SkillGapItem], summary="Skill-gap analysis: requested skills vs verified alumni supply")
async def get_admin_dashboard_skill_gap(
    college: Optional[str] = Query(None, description="Optional college institution filter"),
    db: AsyncSession = Depends(get_db),
):
    data = await institution_service.get_dashboard_overview(db, college=college)
    return data.skill_gap


@router.get("/admin/dashboard/safety-summary", summary="Safety incident summary and moderation resolution rate")
async def get_admin_dashboard_safety_summary(
    db: AsyncSession = Depends(get_db),
):
    reports = await institution_service.list_reports(db)
    resolved = sum(1 for r in reports if r.status != "pending")
    return {
        "total_reports": len(reports),
        "resolved_reports": resolved,
        "pending_reports": len(reports) - resolved,
        "resolution_rate": round((resolved / len(reports) * 100), 1) if reports else 100.0,
    }


@router.get("/admin/dashboard/seats", summary="Usage metrics for sponsored seats and credits")
async def get_admin_dashboard_seats(
    db: AsyncSession = Depends(get_db),
):
    data = await institution_service.get_dashboard_overview(db)
    return {
        "completed_sessions": data.completed_sessions,
        "free_sessions": data.free_sessions,
        "paid_sessions": data.paid_sessions,
    }


# --- 2. Verification Queue Endpoints ---

@router.post("/admin/verifications", response_model=VerificationResponse, summary="Submit user for institution verification")
async def post_admin_verification(
    req: VerificationCreateInput,
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.create_verification(db, req)


@router.get("/admin/verifications", response_model=List[VerificationResponse], summary="List pending or filtered verification records")
async def get_admin_verifications(
    status: Optional[str] = Query(None, description="Filter by status ('pending', 'approved', 'rejected')"),
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.list_verifications(db, status=status)


@router.post("/admin/verifications/{id}/review", response_model=VerificationResponse, summary="Review and approve/reject verification request")
async def post_admin_verification_review(
    id: str,
    req: VerificationReviewInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    verification_id = uuid.UUID(id)
    admin_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.review_verification(db, admin_id, verification_id, req)


# --- 3. Safety Reports & Moderation Queue ---

@router.post("/reports", response_model=ReportResponse, summary="Report a profile, message, or session")
async def post_create_report(
    req: ReportCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    reporter_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.create_report(db, reporter_id, req)


@router.get("/admin/reports", response_model=List[ReportResponse], summary="Admin moderation queue for reported profiles, messages, or sessions")
async def get_admin_reports(
    status: Optional[str] = Query(None, description="Filter status ('pending', 'dismissed', 'warned', 'suspended', 'removed')"),
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.list_reports(db, status=status)


@router.post("/admin/reports/{id}/resolve", response_model=ReportResponse, summary="Resolve a report: dismiss, warn, suspend, remove (with scam learning)")
async def post_admin_reports_resolve(
    id: str,
    req: ReportResolveInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    report_id = uuid.UUID(id)
    admin_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.resolve_report(db, admin_id, report_id, req)


@router.post("/admin/givers/{id}/suspend", summary="Directly suspend a giver (removes from matching immediately)")
async def post_admin_giver_suspend(
    id: str,
    request: Request,
    reason: str = Query("Admin moderation suspension", description="Reason for suspension"),
    db: AsyncSession = Depends(get_db),
):
    giver_id = uuid.UUID(id)
    admin_id = uuid.UUID(get_current_user_id(request))
    await institution_service.suspend_user(db, admin_id, giver_id, reason=reason)
    return {"message": "Giver suspended successfully and removed from matching", "giver_id": id}


@router.get("/admin/audit-logs", summary="List immutable audit logs for administrative actions and financial money transactions")
async def get_admin_audit_logs(
    target_type: Optional[str] = Query(None, description="Filter by target type ('report', 'verification', 'giver', 'college', 'user', 'financial')"),
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.list_audit_logs(db, target_type=target_type)


# --- 4. Trust Layers Page ---

@router.get("/admin/trust-layers", response_model=TrustLayersResponse, summary="List the 7 defensive trust layers with live operational counts")
async def get_admin_trust_layers(
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.get_trust_layers(db)


# --- 5. Post-Session Outcome Tracking ---

@router.post("/sessions/{id}/outcome", response_model=SessionOutcomeResponse, summary="Report 7-day post-session career outcome")
async def post_session_outcome(
    id: str,
    req: SessionOutcomeCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = uuid.UUID(id)
    student_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.submit_outcome(db, session_id, student_id, req)


@router.post("/requests/{id}/outcome", response_model=SessionOutcomeResponse, summary="Report 7-day post-session career outcome (alias)")
async def post_request_outcome(
    id: str,
    req: SessionOutcomeCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = uuid.UUID(id)
    student_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.submit_outcome(db, session_id, student_id, req)


# --- 6. Network Graph Endpoints ---

@router.get("/admin/network-graph", response_model=NetworkGraphResponse, summary="Interactive force-directed network graph")
async def get_admin_network_graph(
    role: Optional[str] = Query(None, description="Filter by role ('student', 'alumnus', 'faculty', 'recruiter', 'founder')"),
    college: Optional[str] = Query(None, description="Filter by college / institution name"),
    skill: Optional[str] = Query(None, description="Filter by skill tag"),
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.get_network_graph(db, role=role, college=college, skill=skill)


@router.get("/network-graph", response_model=NetworkGraphResponse, summary="Interactive network graph (safe view)")
async def get_public_network_graph(
    role: Optional[str] = Query(None, description="Filter by role ('student', 'alumnus', 'faculty', 'recruiter', 'founder')"),
    college: Optional[str] = Query(None, description="Filter by college / institution name"),
    skill: Optional[str] = Query(None, description="Filter by skill tag"),
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.get_network_graph(db, role=role, college=college, skill=skill)


# --- 7. Pilot Metrics & Launch Gate Endpoints ---

@router.get("/admin/pilot-metrics", response_model=PilotMetricsResponse, summary="Progress toward 50 verified givers, 72h answer rate, launch gate, and 30/60/90-day plan")
async def get_admin_pilot_metrics(
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.get_pilot_metrics(db)


@router.post("/admin/colleges/enable", response_model=CollegeResponse, summary="Enable college (guarded by pilot launch gate)")
async def post_admin_college_enable(
    req: CollegeEnableInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    admin_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.enable_college(db, admin_id, req)


@router.post("/admin/colleges/{id}/enable", response_model=CollegeResponse, summary="Enable college by ID (guarded by pilot launch gate)")
async def post_admin_college_id_enable(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    admin_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.enable_college(db, admin_id, CollegeEnableInput(college_id=id))


@router.post("/admin/colleges", response_model=CollegeResponse, summary="Create a new partner college")
async def post_admin_college_create(
    req: CollegeCreateInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    admin_id = uuid.UUID(get_current_user_id(request))
    return await institution_service.create_college(db, admin_id, req)


@router.get("/admin/colleges", response_model=List[CollegeResponse], summary="List all registered colleges and enablement status")
async def get_admin_colleges(
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.list_colleges(db)


@router.post("/verification/upload", summary="Secure document upload for verification with file type and size inspection")
async def post_verification_upload(
    file: UploadFile = File(...),
):
    content, filename, mime_type = await validate_and_read_file(
        file=file,
        allowed_mimes=["application/pdf", "image/png", "image/jpeg"],
    )
    doc_id = uuid.uuid4().hex[:12]
    return {
        "status": "uploaded",
        "document_url": f"https://warmpath.internal/docs/{doc_id}_{filename}",
        "filename": filename,
        "size_bytes": len(content),
        "mime_type": mime_type,
    }


