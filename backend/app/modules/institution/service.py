"""Business logic service for institution admin experience: dashboard, reports, moderation, and trust layers."""
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import OutboxEvent
from app.core.errors import AppError
from app.modules.auth.models import FinancialAuditLog
from app.modules.availability.models import AvailabilityNotification, GiverAvailability
from app.modules.institution.models import AdminAuditLog, College, IncidentLog, Report, SessionOutcome, VerificationRecord
from app.modules.institution.schemas import (
    DashboardOverviewResponse,
    SkillGapItem,
    TopGiverItem,
    VerificationCreateInput,
    VerificationResponse,
    VerificationReviewInput,
    ReportCreateInput,
    ReportResponse,
    ReportResolveInput,
    AuditLogResponse,
    IncidentLogResponse,
    TrustLayerItem,
    TrustLayersResponse,
    SessionOutcomeCreateInput,
    SessionOutcomeResponse,
    GraphNode,
    GraphEdge,
    NetworkGraphResponse,
    LaunchGateStatus,
    PlanPhase,
    PilotMetricsResponse,
    CollegeCreateInput,
    CollegeEnableInput,
    CollegeResponse,
)
from app.modules.matching.models import EmployerProfile, FacultyProfile, GiverProfile, StudentProfile
from app.modules.ratings.models import SessionRating, Vouch
from app.modules.sessions.models import MentorshipMessage, MentorshipRequest
from app.modules.trust.models import SafetyFlag, ScamRule, UserTrust


def to_utc_datetime(dt: Any) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class InstitutionService:
    # --- 1. Admin Dashboard & Metrics ---

    async def get_dashboard_overview(
        self, db: AsyncSession, college: Optional[str] = None
    ) -> DashboardOverviewResponse:
        """
        Computes aggregate operational and trust metrics:
        total requests, answered within 72h, fulfillment rate, average response time,
        active vs inactive givers, completed sessions, average rating, free vs paid,
        skill-gap analysis, and top givers.
        """
        # 1. Mentorship Requests
        query_req = select(MentorshipRequest)
        res_req = await db.execute(query_req)
        all_reqs = res_req.scalars().all()

        total_requests = len(all_reqs)
        responded_reqs = [
            r for r in all_reqs
            if r.responded_at is not None or r.status in ("accepted", "declined", "completed", "scheduled", "rated")
        ]

        answered_within_72h = 0
        reply_diffs = []
        for r in responded_reqs:
            creat_dt = to_utc_datetime(r.created_at)
            resp_dt = to_utc_datetime(r.responded_at)
            if creat_dt and resp_dt:
                diff_sec = (resp_dt - creat_dt).total_seconds()
                if diff_sec >= 0:
                    reply_diffs.append(diff_sec)
                    if diff_sec <= 72 * 3600:
                        answered_within_72h += 1
            elif r.status in ("accepted", "declined", "completed", "scheduled", "rated"):
                # Count as answered if processed
                answered_within_72h += 1

        avg_reply_sec = (sum(reply_diffs) / len(reply_diffs)) if reply_diffs else None
        avg_reply_display = f"{int(avg_reply_sec // 60)}m" if avg_reply_sec else "N/A"

        fulfilled_reqs = [r for r in all_reqs if r.status in ("completed", "rated", "scheduled", "accepted")]
        fulfillment_rate = round((len(fulfilled_reqs) / total_requests) * 100, 1) if total_requests > 0 else 100.0

        completed_sessions = sum(1 for r in all_reqs if r.status in ("completed", "rated"))
        free_sessions = sum(1 for r in all_reqs if r.is_free and r.status in ("completed", "rated"))
        paid_sessions = sum(1 for r in all_reqs if not r.is_free and r.status in ("completed", "rated"))

        # 2. Giver Availability
        res_avail = await db.execute(select(GiverAvailability))
        all_avails = res_avail.scalars().all()
        active_givers = sum(1 for a in all_avails if a.status in ("active_now", "available_today"))
        inactive_givers = sum(1 for a in all_avails if a.status == "inactive")

        # 3. Ratings
        res_ratings = await db.execute(
            select(SessionRating).where(
                SessionRating.is_flagged == False,
                SessionRating.review_status == "approved",
            )
        )
        approved_ratings = res_ratings.scalars().all()
        avg_rating = round(sum(r.score for r in approved_ratings) / len(approved_ratings), 2) if approved_ratings else 4.0

        # 4. Skill Gap Analysis (requested skills vs verified alumni coverage)
        requested_skill_counts: Dict[str, int] = {}
        for r in all_reqs:
            # Extract skills from intent
            text = f"{r.intent or ''} {r.notes or ''}"
            words = [w.strip(".,;:?!()[]").capitalize() for w in text.split() if len(w) > 3]
            for w in words:
                requested_skill_counts[w] = requested_skill_counts.get(w, 0) + 1

        res_givers = await db.execute(select(GiverProfile).where(GiverProfile.is_verified == True))
        verified_givers = res_givers.scalars().all()

        alumni_skill_counts: Dict[str, int] = {}
        for g in verified_givers:
            for s in (g.skills or "").split(","):
                clean_s = s.strip().capitalize()
                if clean_s:
                    alumni_skill_counts[clean_s] = alumni_skill_counts.get(clean_s, 0) + 1

        skill_gap_items: List[SkillGapItem] = []
        # Check prominent demand skills
        common_tech_skills = ["Python", "FastAPI", "Distributed Systems", "Cloud", "Machine Learning", "System Design", "SQL", "Docker"]
        for s in common_tech_skills:
            req_cnt = requested_skill_counts.get(s, 0)
            alumni_cnt = alumni_skill_counts.get(s, 0)
            gap = max(0, req_cnt - alumni_cnt)
            skill_gap_items.append(
                SkillGapItem(
                    skill=s,
                    requested_count=req_cnt,
                    alumni_coverage_count=alumni_cnt,
                    gap_score=gap,
                )
            )

        # 5. Top Givers
        giver_counts: Dict[str, int] = {}
        for r in all_reqs:
            if r.status in ("completed", "rated"):
                gid_str = str(r.giver_id)
                giver_counts[gid_str] = giver_counts.get(gid_str, 0) + 1

        giver_prof_map = {str(g.user_id): g for g in verified_givers}
        top_givers_list: List[TopGiverItem] = []
        for gid_str, count in sorted(giver_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            prof = giver_prof_map.get(gid_str)
            full_name = prof.full_name if prof else f"Mentor {gid_str[:6]}"
            college_val = prof.college if prof and prof.college else "Alumni Network"
            # Get rating
            giver_ratings = [r.score for r in approved_ratings if str(r.giver_id) == gid_str]
            g_avg = round(sum(giver_ratings) / len(giver_ratings), 2) if giver_ratings else 4.0
            top_givers_list.append(
                TopGiverItem(
                    giver_id=gid_str,
                    full_name=full_name,
                    college=college_val,
                    completed_sessions=count,
                    average_rating=g_avg,
                )
            )

        # 6. Session Outcomes Tracking
        res_outcomes = await db.execute(select(SessionOutcome))
        all_outcomes = res_outcomes.scalars().all()
        total_outcomes_reported = len(all_outcomes)
        positive_types = {"interview", "referral", "project_feedback", "offer"}
        positive_count = sum(1 for o in all_outcomes if o.outcome in positive_types)
        outcome_rate = round((positive_count / max(1, total_outcomes_reported)) * 100, 1) if total_outcomes_reported > 0 else 0.0

        outcome_breakdown: Dict[str, int] = {
            "interview": 0,
            "referral": 0,
            "project_feedback": 0,
            "offer": 0,
            "nothing_yet": 0,
        }
        for o in all_outcomes:
            outcome_breakdown[o.outcome] = outcome_breakdown.get(o.outcome, 0) + 1

        # 7. Charts Data
        status_dist: Dict[str, int] = {}
        for r in all_reqs:
            status_dist[r.status] = status_dist.get(r.status, 0) + 1

        charts_data = {
            "status_distribution": status_dist,
            "sessions_free_vs_paid": {"free": free_sessions, "paid": paid_sessions},
            "alumni_status": {"active": active_givers, "inactive": inactive_givers},
            "outcome_distribution": outcome_breakdown,
        }

        return DashboardOverviewResponse(
            total_requests=total_requests,
            answered_within_72h=answered_within_72h,
            fulfillment_rate=fulfillment_rate,
            average_response_time_seconds=avg_reply_sec,
            average_response_time_display=avg_reply_display,
            active_givers=active_givers,
            inactive_givers=inactive_givers,
            completed_sessions=completed_sessions,
            average_rating=avg_rating,
            free_sessions=free_sessions,
            paid_sessions=paid_sessions,
            total_outcomes_reported=total_outcomes_reported,
            positive_outcomes_count=positive_count,
            outcome_rate=outcome_rate,
            outcome_breakdown=outcome_breakdown,
            skill_gap=skill_gap_items,
            top_givers=top_givers_list,
            charts_data=charts_data,
        )

    async def export_dashboard_csv(self, db: AsyncSession, college: Optional[str] = None) -> str:
        """Exports institutional metrics as CSV."""
        data = await self.get_dashboard_overview(db, college=college)
        lines = [
            "metric,value",
            f"total_requests,{data.total_requests}",
            f"answered_within_72h,{data.answered_within_72h}",
            f"fulfillment_rate_percent,{data.fulfillment_rate}",
            f"average_response_time_seconds,{data.average_response_time_seconds or 0}",
            f"active_givers,{data.active_givers}",
            f"inactive_givers,{data.inactive_givers}",
            f"completed_sessions,{data.completed_sessions}",
            f"average_rating,{data.average_rating}",
            f"free_sessions,{data.free_sessions}",
            f"paid_sessions,{data.paid_sessions}",
            f"total_outcomes_reported,{data.total_outcomes_reported}",
            f"positive_outcomes_count,{data.positive_outcomes_count}",
            f"outcome_rate_percent,{data.outcome_rate}",
        ]
        return "\n".join(lines)

    # --- 2. Verification Queue ---

    async def create_verification(
        self, db: AsyncSession, req: VerificationCreateInput
    ) -> VerificationResponse:
        user_uuid = uuid.UUID(req.user_id)
        res = await db.execute(
            select(VerificationRecord).where(VerificationRecord.user_id == user_uuid)
        )
        rec = res.scalar_one_or_none()
        if not rec:
            rec = VerificationRecord(
                user_id=user_uuid,
                user_type=req.user_type.lower(),
                full_name=req.full_name,
                college=req.college,
                identifier=req.identifier,
                document_url=req.document_url,
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
            db.add(rec)
        else:
            rec.user_type = req.user_type.lower()
            rec.full_name = req.full_name
            rec.college = req.college
            rec.identifier = req.identifier
            rec.document_url = req.document_url
            rec.status = "pending"

        await db.commit()
        await db.refresh(rec)

        return VerificationResponse(
            id=str(rec.id),
            user_id=str(rec.user_id),
            user_type=rec.user_type,
            full_name=rec.full_name,
            college=rec.college,
            identifier=rec.identifier,
            document_url=rec.document_url,
            status=rec.status,
            admin_notes=rec.admin_notes,
            created_at=rec.created_at.isoformat(),
            reviewed_at=rec.reviewed_at.isoformat() if rec.reviewed_at else None,
        )

    async def list_verifications(
        self, db: AsyncSession, status: Optional[str] = None
    ) -> List[VerificationResponse]:
        query = select(VerificationRecord)
        if status:
            query = query.where(VerificationRecord.status == status.lower())
        query = query.order_by(VerificationRecord.created_at.desc())

        res = await db.execute(query)
        records = res.scalars().all()
        return [
            VerificationResponse(
                id=str(r.id),
                user_id=str(r.user_id),
                user_type=r.user_type,
                full_name=r.full_name,
                college=r.college,
                identifier=r.identifier,
                document_url=r.document_url,
                status=r.status,
                admin_notes=r.admin_notes,
                created_at=r.created_at.isoformat(),
                reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
            )
            for r in records
        ]

    async def review_verification(
        self,
        db: AsyncSession,
        admin_id: uuid.UUID,
        verification_id: uuid.UUID,
        req: VerificationReviewInput,
    ) -> VerificationResponse:
        res = await db.execute(
            select(VerificationRecord).where(VerificationRecord.id == verification_id)
        )
        rec = res.scalar_one_or_none()
        if not rec:
            raise AppError(code="verification_not_found", message="Verification record not found", status_code=404)

        decision = req.action.lower()
        if decision == "approve":
            rec.status = "approved"
            # Update user trust and profiles
            ut_res = await db.execute(select(UserTrust).where(UserTrust.user_id == rec.user_id))
            ut = ut_res.scalar_one_or_none()
            if not ut:
                ut = UserTrust(user_id=rec.user_id, is_verified=True)
                db.add(ut)
            else:
                ut.is_verified = True

            # If alumnus / giver
            prof_res = await db.execute(select(GiverProfile).where(GiverProfile.user_id == rec.user_id))
            prof = prof_res.scalar_one_or_none()
            if prof:
                prof.is_verified = True

            # If recruiter
            emp_res = await db.execute(select(EmployerProfile).where(EmployerProfile.user_id == rec.user_id))
            emp = emp_res.scalar_one_or_none()
            if emp:
                emp.is_verified = True
                emp.verified_employer_badge = True

            # If faculty
            fac_res = await db.execute(select(FacultyProfile).where(FacultyProfile.user_id == rec.user_id))
            fac = fac_res.scalar_one_or_none()
            if fac:
                fac.is_verified = True
                fac.verified_expert_badge = True

        elif decision == "reject":
            rec.status = "rejected"
        else:
            raise AppError(code="invalid_action", message="Action must be 'approve' or 'reject'", status_code=400)

        rec.admin_notes = req.notes
        rec.reviewed_at = datetime.now(timezone.utc)

        # Audit log
        db.add(
            AdminAuditLog(
                admin_id=admin_id,
                action=f"verify_{decision}",
                target_type="verification",
                target_id=str(rec.id),
                reason=req.notes or f"Verification {decision}",
                metadata_json={"user_id": str(rec.user_id), "user_type": rec.user_type},
                created_at=datetime.now(timezone.utc),
            )
        )

        await db.commit()
        await db.refresh(rec)

        return VerificationResponse(
            id=str(rec.id),
            user_id=str(rec.user_id),
            user_type=rec.user_type,
            full_name=rec.full_name,
            college=rec.college,
            identifier=rec.identifier,
            document_url=rec.document_url,
            status=rec.status,
            admin_notes=rec.admin_notes,
            created_at=rec.created_at.isoformat(),
            reviewed_at=rec.reviewed_at.isoformat() if rec.reviewed_at else None,
        )

    # --- 3. Safety Reports & Moderation Queue ---

    async def create_report(
        self, db: AsyncSession, reporter_id: uuid.UUID, req: ReportCreateInput
    ) -> ReportResponse:
        rep = Report(
            reporter_id=reporter_id,
            reported_user_id=uuid.UUID(req.reported_user_id),
            target_type=req.target_type.lower(),
            target_id=uuid.UUID(req.target_id),
            reason=req.reason,
            evidence=req.evidence,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(rep)
        db.add(
            OutboxEvent(
                topic="report.created",
                payload={
                    "report_id": str(rep.id),
                    "reported_user_id": req.reported_user_id,
                    "target_type": req.target_type,
                    "reason": req.reason,
                },
            )
        )
        await db.commit()
        await db.refresh(rep)

        return ReportResponse(
            id=str(rep.id),
            reporter_id=str(rep.reporter_id),
            reported_user_id=str(rep.reported_user_id),
            target_type=rep.target_type,
            target_id=str(rep.target_id),
            reason=rep.reason,
            evidence=rep.evidence,
            status=rep.status,
            admin_notes=rep.admin_notes,
            is_scam=rep.is_scam,
            created_at=rep.created_at.isoformat(),
            resolved_at=rep.resolved_at.isoformat() if rep.resolved_at else None,
        )

    async def list_reports(
        self, db: AsyncSession, status: Optional[str] = None
    ) -> List[ReportResponse]:
        query = select(Report)
        if status:
            query = query.where(Report.status == status.lower())
        query = query.order_by(Report.created_at.desc())

        res = await db.execute(query)
        reports = res.scalars().all()
        return [
            ReportResponse(
                id=str(r.id),
                reporter_id=str(r.reporter_id),
                reported_user_id=str(r.reported_user_id),
                target_type=r.target_type,
                target_id=str(r.target_id),
                reason=r.reason,
                evidence=r.evidence,
                status=r.status,
                admin_notes=r.admin_notes,
                is_scam=r.is_scam,
                created_at=r.created_at.isoformat(),
                resolved_at=r.resolved_at.isoformat() if r.resolved_at else None,
            )
            for r in reports
        ]

    async def resolve_report(
        self,
        db: AsyncSession,
        admin_id: uuid.UUID,
        report_id: uuid.UUID,
        req: ReportResolveInput,
    ) -> ReportResponse:
        """
        Resolves an admin safety report with action: dismiss, warn, suspend, remove.
        Stores reason in audit_log.
        If scam incident: extracts pattern, adds row to scam_rules, reduces trust score, and creates incident log.
        """
        res = await db.execute(select(Report).where(Report.id == report_id))
        rep = res.scalar_one_or_none()
        if not rep:
            raise AppError(code="report_not_found", message="Report not found", status_code=404)

        action = req.action.lower()
        if action not in ("dismiss", "warn", "suspend", "remove"):
            raise AppError(code="invalid_action", message="Action must be dismiss, warn, suspend, or remove", status_code=400)

        rep.status = action
        rep.admin_notes = req.admin_notes or req.reason
        rep.resolved_at = datetime.now(timezone.utc)
        rep.is_scam = req.is_scam

        # 1. Moderation Actions on Reported User
        if action == "suspend":
            await self.suspend_user(db, admin_id, rep.reported_user_id, req.reason)
        elif action == "remove":
            await self.remove_user(db, admin_id, rep.reported_user_id, req.reason)
        elif action == "warn":
            # Increment reports count
            ut_res = await db.execute(select(UserTrust).where(UserTrust.user_id == rep.reported_user_id))
            ut = ut_res.scalar_one_or_none()
            if ut:
                ut.reports_count += 1

        # 2. Incident Learning: Scam Pattern Extraction & Dynamic Rule Addition
        if req.is_scam:
            pattern = req.new_scam_pattern
            if not pattern:
                # Extract quoted or key phrase from evidence
                pattern = rep.evidence.strip()
                if len(pattern) > 50:
                    pattern = pattern[:50]

            # Add new row to scam_rules table
            scam_rule = ScamRule(
                pattern=pattern,
                category="scam_phrase",
                action="block",
                description=f"Auto-learned from report {rep.id}: {req.reason}",
                created_at=datetime.now(timezone.utc),
            )
            db.add(scam_rule)

            # Reduce trust score of the offender
            ut_res = await db.execute(select(UserTrust).where(UserTrust.user_id == rep.reported_user_id))
            ut = ut_res.scalar_one_or_none()
            if ut:
                ut.reports_count += 3
                ut.manual_level = "restricted"

            # Create IncidentLog with "rules updated"
            inc = IncidentLog(
                report_id=rep.id,
                offender_id=rep.reported_user_id,
                incident_type="scam",
                extracted_patterns=[pattern],
                status="rules updated",
                notes=f"Report {rep.id} resolved as scam. Rule added for '{pattern}'. Offender trust score restricted.",
                created_at=datetime.now(timezone.utc),
            )
            db.add(inc)

        # 3. Store action in audit_log
        db.add(
            AdminAuditLog(
                admin_id=admin_id,
                action=action,
                target_type="report",
                target_id=str(rep.id),
                reason=req.reason,
                metadata_json={
                    "reported_user_id": str(rep.reported_user_id),
                    "is_scam": req.is_scam,
                    "target_type": rep.target_type,
                    "target_id": str(rep.target_id),
                },
                created_at=datetime.now(timezone.utc),
            )
        )

        await db.commit()
        await db.refresh(rep)

        return ReportResponse(
            id=str(rep.id),
            reporter_id=str(rep.reporter_id),
            reported_user_id=str(rep.reported_user_id),
            target_type=rep.target_type,
            target_id=str(rep.target_id),
            reason=rep.reason,
            evidence=rep.evidence,
            status=rep.status,
            admin_notes=rep.admin_notes,
            is_scam=rep.is_scam,
            created_at=rep.created_at.isoformat(),
            resolved_at=rep.resolved_at.isoformat() if rep.resolved_at else None,
        )

    # --- 4. Moderation Helpers ---

    async def suspend_user(
        self, db: AsyncSession, admin_id: uuid.UUID, user_id: uuid.UUID, reason: str
    ) -> None:
        """
        Suspends a giver or user:
        - Sets GiverProfile.is_verified = False (immediately drops from matching).
        - Sets GiverAvailability.status = "inactive".
        - Sets UserTrust.manual_level = "restricted".
        - Records in audit_log.
        """
        # Giver Profile
        prof_res = await db.execute(select(GiverProfile).where(GiverProfile.user_id == user_id))
        prof = prof_res.scalar_one_or_none()
        if prof:
            prof.is_verified = False

        # Availability
        avail_res = await db.execute(select(GiverAvailability).where(GiverAvailability.user_id == user_id))
        avail = avail_res.scalar_one_or_none()
        if avail:
            avail.status = "inactive"

        # Trust score restriction
        ut_res = await db.execute(select(UserTrust).where(UserTrust.user_id == user_id))
        ut = ut_res.scalar_one_or_none()
        if not ut:
            ut = UserTrust(user_id=user_id, is_verified=False, manual_level="restricted", reports_count=2)
            db.add(ut)
        else:
            ut.manual_level = "restricted"
            ut.reports_count += 2

        db.add(
            AdminAuditLog(
                admin_id=admin_id,
                action="suspend",
                target_type="giver",
                target_id=str(user_id),
                reason=reason,
                metadata_json={"user_id": str(user_id), "status": "suspended"},
                created_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    async def remove_user(
        self, db: AsyncSession, admin_id: uuid.UUID, user_id: uuid.UUID, reason: str
    ) -> None:
        """Deactivates and permanently removes user from platform activities."""
        await self.suspend_user(db, admin_id, user_id, reason)
        db.add(
            AdminAuditLog(
                admin_id=admin_id,
                action="remove",
                target_type="user",
                target_id=str(user_id),
                reason=reason,
                metadata_json={"user_id": str(user_id), "status": "removed"},
                created_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    async def list_audit_logs(
        self, db: AsyncSession, target_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists audit logs for admin decisions and financial money movements."""
        results: List[Dict[str, Any]] = []

        if target_type == "financial":
            res = await db.execute(select(FinancialAuditLog).order_by(FinancialAuditLog.created_at.desc()))
            for f in res.scalars().all():
                results.append({
                    "id": str(f.id),
                    "action": f.action,
                    "target_type": "financial",
                    "target_id": f.reference_id or str(f.id),
                    "amount": f.amount,
                    "user_id": str(f.user_id) if f.user_id else None,
                    "metadata": f.metadata_json,
                    "created_at": f.created_at.isoformat(),
                })
        else:
            q = select(AdminAuditLog)
            if target_type:
                q = q.where(AdminAuditLog.target_type == target_type.lower())
            q = q.order_by(AdminAuditLog.created_at.desc())
            res = await db.execute(q)
            for a in res.scalars().all():
                results.append({
                    "id": str(a.id),
                    "admin_id": str(a.admin_id),
                    "action": a.action,
                    "target_type": a.target_type,
                    "target_id": a.target_id,
                    "reason": a.reason,
                    "metadata": a.metadata_json,
                    "created_at": a.created_at.isoformat(),
                })
            if not target_type:
                res_f = await db.execute(select(FinancialAuditLog).order_by(FinancialAuditLog.created_at.desc()))
                for f in res_f.scalars().all():
                    results.append({
                        "id": str(f.id),
                        "action": f.action,
                        "target_type": "financial",
                        "target_id": f.reference_id or str(f.id),
                        "amount": f.amount,
                        "user_id": str(f.user_id) if f.user_id else None,
                        "metadata": f.metadata_json,
                        "created_at": f.created_at.isoformat(),
                    })
                results.sort(key=lambda x: x["created_at"], reverse=True)

        return results

    # --- 5. Trust Layers Page with Live Counts ---

    async def get_trust_layers(self, db: AsyncSession) -> TrustLayersResponse:
        """
        Returns the 7 defensive layers with live dynamic counts proving each works:
        1. Identity at Entry (verified_count)
        2. Layered Badges (badges_issued)
        3. Graduated Privileges (limits_hit)
        4. In-App Communication (messages_protected)
        5. Scam Detection Filters (scams_blocked)
        6. Human Moderation Queue (reviews_done)
        7. Incident Learning Loop (rules_learned)
        """
        # 1. Identity at entry (verified users)
        res_v1 = await db.execute(select(func.count(UserTrust.id)).where(UserTrust.is_verified == True))
        cnt_v1 = res_v1.scalar() or 0
        res_v2 = await db.execute(select(func.count(GiverProfile.id)).where(GiverProfile.is_verified == True))
        cnt_v2 = res_v2.scalar() or 0
        verified_count = cnt_v1 + cnt_v2

        # 2. Layered badges (badges issued across experts, employers, givers)
        res_b1 = await db.execute(select(func.count(FacultyProfile.id)).where(FacultyProfile.verified_expert_badge == True))
        b1 = res_b1.scalar() or 0
        res_b2 = await db.execute(select(func.count(EmployerProfile.id)).where(EmployerProfile.verified_employer_badge == True))
        b2 = res_b2.scalar() or 0
        badges_issued = b1 + b2 + cnt_v2

        # 3. Graduated privileges (limits hit, capacity reached, or restricted users)
        res_l1 = await db.execute(select(func.count(AvailabilityNotification.id)).where(AvailabilityNotification.type == "capacity_reached"))
        l1 = res_l1.scalar() or 0
        res_l2 = await db.execute(select(func.count(UserTrust.id)).where(UserTrust.manual_level == "restricted"))
        l2 = res_l2.scalar() or 0
        limits_hit = l1 + l2

        # 4. In-app communication (messages protected inside in-app chat)
        res_msg = await db.execute(select(func.count(MentorshipMessage.id)))
        messages_protected = res_msg.scalar() or 0

        # 5. Scam detection filters (scams blocked)
        res_scam = await db.execute(select(func.count(SafetyFlag.id)).where(SafetyFlag.action == "block"))
        scams_blocked = res_scam.scalar() or 0

        # 6. Human moderation queue (reviews done)
        res_rev = await db.execute(select(func.count(Report.id)).where(Report.status != "pending"))
        cnt_rev = res_rev.scalar() or 0
        res_aud = await db.execute(select(func.count(AdminAuditLog.id)))
        cnt_aud = res_aud.scalar() or 0
        reviews_done = max(cnt_rev, cnt_aud)

        # 7. Incident learning loop (rules learned)
        res_rules = await db.execute(select(func.count(ScamRule.id)))
        rules_learned = res_rules.scalar() or 0

        layers = [
            TrustLayerItem(
                layer_number=1,
                name="Identity at Entry",
                threat_prevented="Impersonation, fake alumni, fake recruiters",
                status="active",
                live_metric_name="verified_count",
                live_count=verified_count,
                proof_description="Institutional email validation and corporate verification gate.",
            ),
            TrustLayerItem(
                layer_number=2,
                name="Layered Badges",
                threat_prevented="Unclear credentials, inflated titles",
                status="active",
                live_metric_name="badges_issued",
                live_count=badges_issued,
                proof_description="Verified expert, verified alumnus, and verified employer badges issued.",
            ),
            TrustLayerItem(
                layer_number=3,
                name="Graduated Privileges",
                threat_prevented="Throwaway spam accounts, mass scraping",
                status="active",
                live_metric_name="limits_hit",
                live_count=limits_hit,
                proof_description="Graduated open request caps, daily limits, and giver weekly capacity caps enforced.",
            ),
            TrustLayerItem(
                layer_number=4,
                name="In-App Communication",
                threat_prevented="Off-platform harassment, external payment demands",
                status="active",
                live_metric_name="messages_protected",
                live_count=messages_protected,
                proof_description="In-app messaging and calendar video meetings with contact details hidden.",
            ),
            TrustLayerItem(
                layer_number=5,
                name="Scam Detection Filters",
                threat_prevented="Recruitment fraud, upfront payment scams",
                status="active",
                live_metric_name="scams_blocked",
                live_count=scams_blocked,
                proof_description="Middleware scanner blocking phone numbers, payment phrases, and scam rules.",
            ),
            TrustLayerItem(
                layer_number=6,
                name="Human Moderation Queue",
                threat_prevented="Harassment, repeated bad behavior",
                status="active",
                live_metric_name="reviews_done",
                live_count=reviews_done,
                proof_description="Admin queue resolving reports with dismiss, warn, suspend, or remove actions.",
            ),
            TrustLayerItem(
                layer_number=7,
                name="Incident Learning Loop",
                threat_prevented="Repeated attack vectors",
                status="active",
                live_metric_name="rules_learned",
                live_count=rules_learned,
                proof_description="Automated rule extraction and dynamic regex addition from resolved scam reports.",
            ),
        ]

        summary = {
            "verified_count": verified_count,
            "badges_issued": badges_issued,
            "limits_hit": limits_hit,
            "messages_protected": messages_protected,
            "scams_blocked": scams_blocked,
            "reviews_done": reviews_done,
            "rules_learned": rules_learned,
        }

        return TrustLayersResponse(layers=layers, summary=summary)

    # --- 6. Post-Session Outcome Tracking ---

    async def submit_outcome(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        student_id: uuid.UUID,
        req: SessionOutcomeCreateInput,
    ) -> SessionOutcomeResponse:
        """
        Records 7-day post-session career outcome:
        interview, referral, project_feedback, offer, nothing_yet.
        """
        valid_outcomes = {"interview", "referral", "project_feedback", "offer", "nothing_yet"}
        outcome_val = req.outcome.strip().lower()
        if outcome_val not in valid_outcomes:
            raise AppError(
                code="invalid_outcome",
                message=f"Outcome must be one of: {sorted(list(valid_outcomes))}",
                status_code=400,
            )

        res_sess = await db.execute(select(MentorshipRequest).where(MentorshipRequest.id == session_id))
        session_req = res_sess.scalar_one_or_none()
        if not session_req:
            raise AppError(code="session_not_found", message="Session not found", status_code=404)

        if session_req.student_id != student_id:
            raise AppError(
                code="forbidden",
                message="Only the student in this session can report an outcome",
                status_code=403,
            )

        if session_req.status not in ("completed", "rated"):
            raise AppError(
                code="invalid_session_status",
                message="Outcomes can only be tracked for completed or rated sessions",
                status_code=400,
            )

        res_out = await db.execute(select(SessionOutcome).where(SessionOutcome.session_id == session_id))
        existing = res_out.scalar_one_or_none()
        if existing:
            existing.outcome = outcome_val
            existing.notes = req.notes
            await db.commit()
            await db.refresh(existing)
            rec = existing
        else:
            rec = SessionOutcome(
                session_id=session_id,
                student_id=student_id,
                giver_id=session_req.giver_id,
                outcome=outcome_val,
                notes=req.notes,
                created_at=datetime.now(timezone.utc),
            )
            db.add(rec)
            await db.commit()
            await db.refresh(rec)

        return SessionOutcomeResponse(
            id=str(rec.id),
            session_id=str(rec.session_id),
            student_id=str(rec.student_id),
            giver_id=str(rec.giver_id),
            outcome=rec.outcome,
            notes=rec.notes,
            created_at=rec.created_at.isoformat(),
        )

    # --- 7. Network Graph ("A Network, Not a Directory") ---

    async def get_network_graph(
        self,
        db: AsyncSession,
        role: Optional[str] = None,
        college: Optional[str] = None,
        skill: Optional[str] = None,
    ) -> NetworkGraphResponse:
        """
        Generates interactive force-directed network graph:
        - Colored nodes: students (#3B82F6), alumni (#10B981), faculty (#8B5CF6), recruiters (#F59E0B), founders (#EC4899)
        - Edges: completed_session and vouch from real database records
        - Safe summary with contact details hidden
        - Filtering by role, college, skill
        """
        # 1. Fetch completed sessions & vouches to compute edge & node session counts
        res_req = await db.execute(
            select(MentorshipRequest).where(MentorshipRequest.status.in_(["completed", "rated"]))
        )
        completed_reqs = res_req.scalars().all()

        res_vouch = await db.execute(select(Vouch))
        all_vouches = res_vouch.scalars().all()

        session_counts: Dict[str, int] = {}
        for r in completed_reqs:
            s_id = str(r.student_id)
            g_id = str(r.giver_id)
            session_counts[s_id] = session_counts.get(s_id, 0) + 1
            session_counts[g_id] = session_counts.get(g_id, 0) + 1

        vouch_counts: Dict[str, int] = {}
        for v in all_vouches:
            s_id = str(v.student_id)
            g_id = str(v.giver_id)
            vouch_counts[s_id] = vouch_counts.get(s_id, 0) + 1
            vouch_counts[g_id] = vouch_counts.get(g_id, 0) + 1

        # 2. Build nodes from database profiles
        nodes_dict: Dict[str, GraphNode] = {}

        # 2a. Students
        res_students = await db.execute(select(StudentProfile))
        for sp in res_students.scalars().all():
            nid = str(sp.user_id)
            sk = [s.strip() for s in sp.skills] if isinstance(sp.skills, list) else []
            nodes_dict[nid] = GraphNode(
                id=nid,
                label=sp.full_name,
                role="student",
                color="#3B82F6",
                college=sp.college,
                skills=sk,
                safe_summary={
                    "name": sp.full_name,
                    "role": "student",
                    "headline": f"Student at {sp.college}",
                    "college": sp.college,
                    "city": sp.city,
                    "skills": sk,
                    "completed_sessions": session_counts.get(nid, 0),
                    "vouches": vouch_counts.get(nid, 0),
                    "contact_hidden": True,
                    "safe_notice": "Contact details protected under Warmpath safe network protocol",
                },
            )

        # 2b. Alumni / Givers
        res_givers = await db.execute(select(GiverProfile))
        for gp in res_givers.scalars().all():
            nid = str(gp.user_id)
            sk = [s.strip() for s in (gp.skills or "").split(",") if s.strip()]
            nodes_dict[nid] = GraphNode(
                id=nid,
                label=gp.full_name,
                role="alumnus",
                color="#10B981",
                college=gp.college or "Alumni Network",
                skills=sk,
                safe_summary={
                    "name": gp.full_name,
                    "role": "alumnus",
                    "headline": gp.headline or f"Alumnus at {gp.college or 'Network'}",
                    "college": gp.college or "Alumni Network",
                    "skills": sk,
                    "completed_sessions": session_counts.get(nid, 0),
                    "vouches": vouch_counts.get(nid, 0),
                    "is_verified": gp.is_verified,
                    "contact_hidden": True,
                    "safe_notice": "Contact details protected under Warmpath safe network protocol",
                },
            )

        # 2c. Faculty
        res_faculty = await db.execute(select(FacultyProfile))
        for fp in res_faculty.scalars().all():
            nid = str(fp.user_id)
            sk = fp.expertise if isinstance(fp.expertise, list) else []
            nodes_dict[nid] = GraphNode(
                id=nid,
                label=fp.full_name,
                role="faculty",
                color="#8B5CF6",
                college=fp.institution,
                skills=sk,
                safe_summary={
                    "name": fp.full_name,
                    "role": "faculty",
                    "headline": f"Faculty, Department of {fp.department}",
                    "college": fp.institution,
                    "skills": sk,
                    "rate_credits": fp.rate_credits,
                    "completed_sessions": session_counts.get(nid, 0),
                    "vouches": vouch_counts.get(nid, 0),
                    "contact_hidden": True,
                    "safe_notice": "Contact details protected under Warmpath safe network protocol",
                },
            )

        # 2d. Recruiters & Founders
        res_employers = await db.execute(select(EmployerProfile))
        for ep in res_employers.scalars().all():
            nid = str(ep.user_id)
            desig_lower = (ep.designation or "").lower()
            is_founder = "founder" in desig_lower or "ceo" in desig_lower
            node_role = "founder" if is_founder else "recruiter"
            color_val = "#EC4899" if is_founder else "#F59E0B"
            nodes_dict[nid] = GraphNode(
                id=nid,
                label=ep.full_name,
                role=node_role,
                color=color_val,
                college=ep.company_name,
                skills=[],
                safe_summary={
                    "name": ep.full_name,
                    "role": node_role,
                    "headline": f"{ep.designation} at {ep.company_name}",
                    "college": ep.company_name,
                    "company": ep.company_name,
                    "company_domain": ep.company_domain,
                    "completed_sessions": session_counts.get(nid, 0),
                    "vouches": vouch_counts.get(nid, 0),
                    "contact_hidden": True,
                    "safe_notice": "Contact details protected under Warmpath safe network protocol",
                },
            )

        # 2e. Ensure any participants in sessions or vouches without profile exist as nodes
        for r in completed_reqs:
            s_id = str(r.student_id)
            g_id = str(r.giver_id)
            if s_id not in nodes_dict:
                nodes_dict[s_id] = GraphNode(
                    id=s_id,
                    label=f"Student {s_id[:6]}",
                    role="student",
                    color="#3B82F6",
                    college="Campus Network",
                    skills=[],
                    safe_summary={
                        "name": f"Student {s_id[:6]}",
                        "role": "student",
                        "headline": "Student Scholar",
                        "college": "Campus Network",
                        "skills": [],
                        "completed_sessions": session_counts.get(s_id, 0),
                        "vouches": vouch_counts.get(s_id, 0),
                        "contact_hidden": True,
                        "safe_notice": "Contact details protected under Warmpath safe network protocol",
                    },
                )
            if g_id not in nodes_dict:
                nodes_dict[g_id] = GraphNode(
                    id=g_id,
                    label=f"Mentor {g_id[:6]}",
                    role="alumnus",
                    color="#10B981",
                    college="Alumni Network",
                    skills=[],
                    safe_summary={
                        "name": f"Mentor {g_id[:6]}",
                        "role": "alumnus",
                        "headline": "Alumni Mentor",
                        "college": "Alumni Network",
                        "skills": [],
                        "completed_sessions": session_counts.get(g_id, 0),
                        "vouches": vouch_counts.get(g_id, 0),
                        "contact_hidden": True,
                        "safe_notice": "Contact details protected under Warmpath safe network protocol",
                    },
                )

        for v in all_vouches:
            s_id = str(v.student_id)
            g_id = str(v.giver_id)
            if s_id not in nodes_dict:
                nodes_dict[s_id] = GraphNode(
                    id=s_id,
                    label=f"Student {s_id[:6]}",
                    role="student",
                    color="#3B82F6",
                    college="Campus Network",
                    skills=[],
                    safe_summary={
                        "name": f"Student {s_id[:6]}",
                        "role": "student",
                        "headline": "Student Scholar",
                        "college": "Campus Network",
                        "skills": [],
                        "completed_sessions": session_counts.get(s_id, 0),
                        "vouches": vouch_counts.get(s_id, 0),
                        "contact_hidden": True,
                        "safe_notice": "Contact details protected under Warmpath safe network protocol",
                    },
                )
            if g_id not in nodes_dict:
                nodes_dict[g_id] = GraphNode(
                    id=g_id,
                    label=v.giver_name,
                    role="alumnus",
                    color="#10B981",
                    college=v.giver_company,
                    skills=[],
                    safe_summary={
                        "name": v.giver_name,
                        "role": "alumnus",
                        "headline": f"Leader at {v.giver_company}",
                        "college": v.giver_company,
                        "skills": [],
                        "completed_sessions": session_counts.get(g_id, 0),
                        "vouches": vouch_counts.get(g_id, 0),
                        "contact_hidden": True,
                        "safe_notice": "Contact details protected under Warmpath safe network protocol",
                    },
                )

        # 3. Filtering nodes by role, college, skill
        filtered_nodes = list(nodes_dict.values())
        if role:
            r_clean = role.strip().lower()
            filtered_nodes = [n for n in filtered_nodes if n.role.lower() == r_clean]

        if college:
            c_clean = college.strip().lower()
            filtered_nodes = [n for n in filtered_nodes if c_clean in n.college.lower()]

        if skill:
            s_clean = skill.strip().lower()
            filtered_nodes = [
                n for n in filtered_nodes
                if any(s_clean in sk.lower() for sk in n.skills)
            ]

        valid_node_ids = {n.id for n in filtered_nodes}

        # 4. Construct Edges from database (completed sessions and vouches)
        edges: List[GraphEdge] = []
        for r in completed_reqs:
            s_id = str(r.student_id)
            g_id = str(r.giver_id)
            if s_id in valid_node_ids and g_id in valid_node_ids:
                edges.append(
                    GraphEdge(
                        id=f"session-{r.id}",
                        source=s_id,
                        target=g_id,
                        type="completed_session",
                        label="Completed Session",
                    )
                )

        for v in all_vouches:
            s_id = str(v.student_id)
            g_id = str(v.giver_id)
            if g_id in valid_node_ids and s_id in valid_node_ids:
                edges.append(
                    GraphEdge(
                        id=f"vouch-{v.id}",
                        source=g_id,
                        target=s_id,
                        type="vouch",
                        label=f"Vouched ({v.giver_company})",
                    )
                )

        summary = {
            "total_nodes": len(filtered_nodes),
            "total_edges": len(edges),
            "nodes_by_role": {
                "student": sum(1 for n in filtered_nodes if n.role == "student"),
                "alumnus": sum(1 for n in filtered_nodes if n.role == "alumnus"),
                "faculty": sum(1 for n in filtered_nodes if n.role == "faculty"),
                "recruiter": sum(1 for n in filtered_nodes if n.role == "recruiter"),
                "founder": sum(1 for n in filtered_nodes if n.role == "founder"),
            },
            "edges_by_type": {
                "completed_session": sum(1 for e in edges if e.type == "completed_session"),
                "vouch": sum(1 for e in edges if e.type == "vouch"),
            },
        }

        return NetworkGraphResponse(nodes=filtered_nodes, edges=edges, summary=summary)

    # --- 8. Pilot Metrics & Launch Gate ---

    async def get_pilot_metrics(self, db: AsyncSession) -> PilotMetricsResponse:
        """
        Calculates pilot metrics:
        - 50 verified givers progress
        - 72h request answer rate vs 60% pilot target
        - Launch Gate indicator (green when targets met, otherwise locked red)
        - 30/60/90-day plan (Prepare, Open, Prove)
        """
        # 1. Verified givers count
        res_vg = await db.execute(select(func.count(GiverProfile.id)).where(GiverProfile.is_verified == True))
        verified_givers_count = res_vg.scalar() or 0

        # 2. Answer rate within 72h
        res_req = await db.execute(select(MentorshipRequest))
        all_reqs = res_req.scalars().all()
        total_requests = len(all_reqs)

        answered_within_72h = 0
        for r in all_reqs:
            creat_dt = to_utc_datetime(r.created_at)
            resp_dt = to_utc_datetime(r.responded_at)
            if creat_dt and resp_dt:
                diff_sec = (resp_dt - creat_dt).total_seconds()
                if 0 <= diff_sec <= 72 * 3600:
                    answered_within_72h += 1
            elif r.status in ("accepted", "declined", "completed", "scheduled", "rated"):
                answered_within_72h += 1

        answer_rate_72h = round((answered_within_72h / total_requests) * 100, 1) if total_requests > 0 else 0.0

        # 3. Launch gate evaluation
        is_open = (verified_givers_count >= 50) and (answer_rate_72h >= 60.0)
        gate_color = "green" if is_open else "red"
        gate_label = (
            "Launch Gate Open - Enabled for New College"
            if is_open
            else "Launch Gate Locked - Requirements Pending"
        )

        missing_reqs: List[str] = []
        if verified_givers_count < 50:
            missing_reqs.append(
                f"{50 - verified_givers_count} more verified givers needed (current: {verified_givers_count}/50)"
            )
        if answer_rate_72h < 60.0:
            missing_reqs.append(
                f"72h request answer rate must reach 60.0% (current: {answer_rate_72h}%/60.0%)"
            )

        launch_gate = LaunchGateStatus(
            is_open=is_open,
            color=gate_color,
            label=gate_label,
            verified_givers_target=50,
            verified_givers_current=verified_givers_count,
            answer_rate_target_percent=60.0,
            answer_rate_current_percent=answer_rate_72h,
            requirements_met=is_open,
            missing_requirements=missing_reqs,
        )

        # 4. 30/60/90-Day Plan (Prepare, Open, Prove)
        plan = [
            PlanPhase(
                phase_days="30-day",
                name="Prepare",
                objective="Seed the initial network with verified alumni and faculty domain mentors.",
                key_actions=[
                    "Onboard first 25 verified alumni mentors",
                    "Establish department student ambassadors",
                    "Calibrate scam middleware and calendar links",
                ],
                target_milestones=[
                    "25+ verified givers registered",
                    "Zero unresolved safety reports",
                ],
                status="completed" if verified_givers_count >= 25 else "in_progress",
            ),
            PlanPhase(
                phase_days="60-day",
                name="Open",
                objective="Open matching to first student cohort and validate 72h response SLA.",
                key_actions=[
                    "Launch student matching for pilot college cohort",
                    "Track 72h response rate against 60% threshold",
                    "Activate sponsored credits pool for cross-college access",
                ],
                target_milestones=[
                    "50 verified givers reached",
                    "60% 72h answer rate maintained",
                    "Launch gate unlocked for multi-college enablement",
                ],
                status="completed" if is_open else ("in_progress" if verified_givers_count >= 25 else "pending"),
            ),
            PlanPhase(
                phase_days="90-day",
                name="Prove",
                objective="Prove career impact via 7-day post-session outcome tracking and expand network.",
                key_actions=[
                    "Track 7-day post-session student career outcomes",
                    "Analyze skill gap and recruiter opt-in pipeline",
                    "Enable new partner colleges through unlocked launch gate",
                ],
                target_milestones=[
                    ">30% positive career outcome rate",
                    "Onboard second partner institution via green launch gate",
                    "Present Pilot metrics to Academic Dean and Placement Cell",
                ],
                status="in_progress" if is_open else "pending",
            ),
        ]

        return PilotMetricsResponse(
            launch_gate=launch_gate,
            verified_givers_count=verified_givers_count,
            verified_givers_target=50,
            answer_rate_72h_percent=answer_rate_72h,
            answer_rate_target_percent=60.0,
            thirty_sixty_ninety_plan=plan,
        )

    async def enable_college(
        self,
        db: AsyncSession,
        admin_id: uuid.UUID,
        req: CollegeEnableInput,
    ) -> CollegeResponse:
        """
        Enables a college institution. Blocked if the pilot launch gate is locked.
        """
        metrics = await self.get_pilot_metrics(db)
        if not metrics.launch_gate.is_open:
            raise AppError(
                code="launch_gate_locked",
                message=(
                    f"The launch gate is locked. Pilot targets (50 verified givers and 60% 72h answer rate) "
                    f"must be met before a new college can be enabled. "
                    f"Current: {metrics.verified_givers_count}/50 verified givers, "
                    f"{metrics.answer_rate_72h_percent}%/60.0% answer rate."
                ),
                status_code=400,
            )

        college_obj: Optional[College] = None
        if req.college_id:
            res = await db.execute(select(College).where(College.id == uuid.UUID(req.college_id)))
            college_obj = res.scalar_one_or_none()
            if not college_obj:
                raise AppError(code="college_not_found", message="College not found", status_code=404)
            college_obj.is_enabled = True
        else:
            name = req.name or "Partner College"
            code = req.code or name[:6].upper()
            res = await db.execute(select(College).where((College.name == name) | (College.code == code)))
            college_obj = res.scalar_one_or_none()
            if college_obj:
                college_obj.is_enabled = True
            else:
                college_obj = College(
                    name=name,
                    code=code,
                    is_enabled=True,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(college_obj)

        db.add(
            AdminAuditLog(
                admin_id=admin_id,
                action="enable_college",
                target_type="college",
                target_id=str(college_obj.id),
                reason="Pilot targets verified, launch gate green. College enabled.",
                metadata_json={"name": college_obj.name, "code": college_obj.code},
                created_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        await db.refresh(college_obj)

        return CollegeResponse(
            id=str(college_obj.id),
            name=college_obj.name,
            code=college_obj.code,
            is_enabled=college_obj.is_enabled,
            created_at=college_obj.created_at.isoformat(),
        )

    async def create_college(
        self,
        db: AsyncSession,
        admin_id: uuid.UUID,
        req: CollegeCreateInput,
    ) -> CollegeResponse:
        res = await db.execute(select(College).where((College.name == req.name) | (College.code == req.code)))
        existing = res.scalar_one_or_none()
        if existing:
            return CollegeResponse(
                id=str(existing.id),
                name=existing.name,
                code=existing.code,
                is_enabled=existing.is_enabled,
                created_at=existing.created_at.isoformat(),
            )

        col = College(
            name=req.name,
            code=req.code,
            is_enabled=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(col)
        db.add(
            AdminAuditLog(
                admin_id=admin_id,
                action="create_college",
                target_type="college",
                target_id=str(col.id),
                reason="College created (pending enablement via launch gate)",
                metadata_json={"name": col.name, "code": col.code},
                created_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        await db.refresh(col)

        return CollegeResponse(
            id=str(col.id),
            name=col.name,
            code=col.code,
            is_enabled=col.is_enabled,
            created_at=col.created_at.isoformat(),
        )

    async def list_colleges(self, db: AsyncSession) -> List[CollegeResponse]:
        res = await db.execute(select(College).order_by(College.name.asc()))
        colleges = res.scalars().all()
        return [
            CollegeResponse(
                id=str(c.id),
                name=c.name,
                code=c.code,
                is_enabled=c.is_enabled,
                created_at=c.created_at.isoformat(),
            )
            for c in colleges
        ]


institution_service = InstitutionService()
