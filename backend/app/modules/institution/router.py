import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
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


# --- 4. Trust Layers Page ---

@router.get("/admin/trust-layers", response_model=TrustLayersResponse, summary="List the 7 defensive trust layers with live operational counts")
async def get_admin_trust_layers(
    db: AsyncSession = Depends(get_db),
):
    return await institution_service.get_trust_layers(db)
