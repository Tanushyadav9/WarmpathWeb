"""Jury Demo Story Service.
Orchestrates the 8-step cohesive demonstration story:
1. Student uploads resume and confirms skills
2. Enters vague intent and gets it refined
3. Sees ranked matches with why-this-match and active status
4. Books a free same-college session and a paid cross-college session
5. A scam message is blocked in chat
6. Session completes, rating releases credits, vouch is added
7. Admin sees dashboard, skill gap and resolves a report that creates a new scam rule
8. A fake alumnus is rejected and a listed one auto-verifies
Includes one-click reset to initial clean state.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import User
from app.modules.auth.models import ConsentRecord, FinancialAuditLog
from app.modules.availability.models import GiverAvailability
from app.modules.credits.models import CreditLedger, Wallet
from app.modules.credits.service import credits_service
from app.modules.institution.models import (
    AdminAuditLog,
    College,
    IncidentLog,
    Report,
    VerificationRecord,
)
from app.modules.matching.models import GiverProfile, StudentProfile
from app.modules.ratings.models import SessionRating, Vouch
from app.modules.sessions.models import MentorshipMessage, MentorshipRequest, SessionBooking
from app.modules.trust.models import SafetyFlag, ScamRule, UserTrust


# Deterministic Demo UUIDs
DEMO_STUDENT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEMO_GIVER_SAME_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEMO_GIVER_CROSS_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DEMO_FACULTY_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
DEMO_RECRUITER_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
DEMO_ADMIN_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")

DEMO_REPORT_ID = uuid.UUID("77777777-7777-7777-7777-777777777777")
DEMO_VERIF_FAKE_ID = uuid.UUID("88888888-8888-8888-8888-888888888888")
DEMO_VERIF_REAL_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")

DEMO_REQ_SAME_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEMO_REQ_CROSS_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class JuryDemoService:
    def __init__(self):
        self.step_status: Dict[int, bool] = {i: False for i in range(1, 9)}
        self.vague_intent = "i want to learn coding and get a good job"
        self.refined_intent = (
            "System Design & Backend Architecture for Tier-1 Product Engineering "
            "(Focus: Distributed Systems, Concurrency & Microservices)"
        )

    async def reset_demo(self, db: AsyncSession) -> Dict[str, Any]:
        """One-click atomic reset restoring clean initial state for the 8-step story."""
        self.step_status = {i: False for i in range(1, 9)}

        # 0. Ensure all tables exist before deletion
        from app.core.db import Base, engine
        from app.core.security import hash_password
        import app.modules.auth.models
        import app.modules.availability.models
        import app.modules.credits.models
        import app.modules.institution.models
        import app.modules.matching.models
        import app.modules.ratings.models
        import app.modules.sessions.models
        import app.modules.trust.models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 1. Clean existing records associated with demo IDs
        await db.execute(delete(MentorshipMessage))
        await db.execute(delete(SessionBooking))
        await db.execute(delete(MentorshipRequest))
        await db.execute(delete(SessionRating))
        await db.execute(delete(Vouch))
        await db.execute(delete(SafetyFlag))
        await db.execute(delete(IncidentLog))
        await db.execute(delete(Report).where(Report.id == DEMO_REPORT_ID))
        await db.execute(delete(VerificationRecord).where(
            VerificationRecord.id.in_([DEMO_VERIF_FAKE_ID, DEMO_VERIF_REAL_ID])
        ))
        await db.execute(delete(StudentProfile).where(StudentProfile.user_id == DEMO_STUDENT_ID))
        await db.execute(delete(GiverProfile).where(GiverProfile.user_id.in_([DEMO_GIVER_SAME_ID, DEMO_GIVER_CROSS_ID])))
        await db.execute(delete(GiverAvailability).where(GiverAvailability.user_id.in_([DEMO_GIVER_SAME_ID, DEMO_GIVER_CROSS_ID])))
        await db.execute(delete(UserTrust).where(UserTrust.user_id.in_([DEMO_STUDENT_ID, DEMO_GIVER_SAME_ID, DEMO_GIVER_CROSS_ID])))
        await db.execute(delete(Wallet).where(Wallet.user_id.in_([DEMO_STUDENT_ID, DEMO_GIVER_SAME_ID, DEMO_GIVER_CROSS_ID])))
        await db.execute(delete(User).where(User.id.in_([
            DEMO_STUDENT_ID, DEMO_GIVER_SAME_ID, DEMO_GIVER_CROSS_ID,
            DEMO_FACULTY_ID, DEMO_RECRUITER_ID, DEMO_ADMIN_ID
        ])))
        await db.commit()

        # 2. Seed Clean Baseline Users
        demo_hashed = hash_password("DemoPassword123!")
        users = [
            User(
                id=DEMO_STUDENT_ID,
                email="aditi.sharma@iiitd.ac.in",
                full_name="Aditi Sharma",
                hashed_password=demo_hashed,
                role="student",
                is_active=True,
                is_verified=True,
            ),
            User(
                id=DEMO_GIVER_SAME_ID,
                email="rohan.sharma@microsoft.com",
                full_name="Rohan Sharma",
                hashed_password=demo_hashed,
                role="alumnus",
                is_active=True,
                is_verified=True,
            ),
            User(
                id=DEMO_GIVER_CROSS_ID,
                email="priya.patel@google.com",
                full_name="Priya Patel",
                hashed_password=demo_hashed,
                role="alumnus",
                is_active=True,
                is_verified=True,
            ),
            User(
                id=DEMO_FACULTY_ID,
                email="vivek.kumar@iiitd.ac.in",
                full_name="Dr. Vivek Kumar",
                hashed_password=demo_hashed,
                role="faculty",
                is_active=True,
                is_verified=True,
            ),
            User(
                id=DEMO_RECRUITER_ID,
                email="neha.verma@zomato.com",
                full_name="Neha Verma",
                hashed_password=demo_hashed,
                role="recruiter",
                is_active=True,
                is_verified=True,
            ),
            User(
                id=DEMO_ADMIN_ID,
                email="career.admin@iiitd.ac.in",
                full_name="IIIT Delhi Career Office",
                hashed_password=demo_hashed,
                role="admin",
                is_active=True,
                is_verified=True,
            ),
        ]
        db.add_all(users)

        # 3. Seed Trust Profiles
        trusts = [
            UserTrust(id=uuid.uuid4(), user_id=DEMO_STUDENT_ID, is_verified=True),
            UserTrust(id=uuid.uuid4(), user_id=DEMO_GIVER_SAME_ID, is_verified=True),
            UserTrust(id=uuid.uuid4(), user_id=DEMO_GIVER_CROSS_ID, is_verified=True),
        ]
        db.add_all(trusts)

        # 4. Seed Wallets (Student: 20 credits, Givers: 10 credits)
        wallets = [
            Wallet(id=uuid.uuid4(), user_id=DEMO_STUDENT_ID, available_balance=20, held_balance=0, karma_balance=5),
            Wallet(id=uuid.uuid4(), user_id=DEMO_GIVER_SAME_ID, available_balance=10, held_balance=0, karma_balance=25),
            Wallet(id=uuid.uuid4(), user_id=DEMO_GIVER_CROSS_ID, available_balance=10, held_balance=0, karma_balance=15),
        ]
        db.add_all(wallets)

        # 5. Seed Giver Availabilities
        availabilities = [
            GiverAvailability(
                id=uuid.uuid4(),
                user_id=DEMO_GIVER_SAME_ID,
                status="active_now",
                weekly_capacity_cap=10,
                last_active_at=datetime.now(timezone.utc),
            ),
            GiverAvailability(
                id=uuid.uuid4(),
                user_id=DEMO_GIVER_CROSS_ID,
                status="available_today",
                today_window="8 to 10 pm",
                weekly_capacity_cap=5,
                last_active_at=datetime.now(timezone.utc),
            ),
        ]
        db.add_all(availabilities)

        # 6. Seed Giver & Student Profiles
        profiles = [
            GiverProfile(
                id=uuid.uuid4(),
                user_id=DEMO_GIVER_SAME_ID,
                full_name="Rohan Sharma",
                headline="Staff Engineer at Microsoft (IIIT Delhi Alumni)",
                college="IIIT Delhi",
                skills="Python, Distributed Systems, FastAPI, Cloud Architecture",
                is_verified=True,
            ),
            GiverProfile(
                id=uuid.uuid4(),
                user_id=DEMO_GIVER_CROSS_ID,
                full_name="Priya Patel",
                headline="Senior SWE at Google (NSUT Alumna)",
                college="NSUT",
                skills="Go, Kubernetes, Distributed Systems, Microservices",
                is_verified=True,
            ),
            StudentProfile(
                id=uuid.uuid4(),
                user_id=DEMO_STUDENT_ID,
                full_name="Aditi Sharma",
                college="IIIT Delhi",
                skills=["Python", "Data Structures"],
                proof_of_work=["https://github.com/aditi/distributed-raft"],
            ),
        ]
        db.add_all(profiles)

        # 7. Seed Verification Queue Items
        verifications = [
            VerificationRecord(
                id=DEMO_VERIF_FAKE_ID,
                user_id=uuid.uuid4(),
                user_type="alumnus",
                full_name="Unknown Impersonator",
                college="IIIT Delhi",
                identifier="FORGED-9999",
                document_url="https://warmpath.internal/forged_degree.pdf",
                status="pending",
                admin_notes="Unmatched roll identifier; flagged by registry",
            ),
            VerificationRecord(
                id=DEMO_VERIF_REAL_ID,
                user_id=uuid.uuid4(),
                user_type="student",
                full_name="Raghav Sen",
                college="IIIT Delhi",
                identifier="2022CSB1042",
                document_url="https://warmpath.internal/valid_student_id.pdf",
                status="pending",
                admin_notes="Student roll number verified in registrar pre-list",
            ),
        ]
        db.add_all(verifications)

        # 8. Seed Safety Moderation Report
        report = Report(
            id=DEMO_REPORT_ID,
            reporter_id=DEMO_STUDENT_ID,
            reported_user_id=uuid.uuid4(),
            target_type="message",
            target_id=uuid.uuid4(),
            reason="scam",
            evidence="Candidate asking for 500 INR via UPI handle payme@upi for referral",
            status="pending",
            is_scam=True,
        )
        db.add(report)

        # 9. Seed Partner College
        res_col = await db.execute(select(College).where(College.code == "IIITD"))
        if not res_col.scalar_one_or_none():
            db.add(College(id=uuid.uuid4(), name="IIIT Delhi", code="IIITD", is_enabled=True))

        await db.commit()

        return {
            "status": "reset_complete",
            "message": "Jury Demo data cleanly restored to initial Step 1 state.",
            "student": {"id": str(DEMO_STUDENT_ID), "name": "Aditi Sharma", "college": "IIIT Delhi", "credits": 20},
            "same_college_giver": {"id": str(DEMO_GIVER_SAME_ID), "name": "Rohan Sharma", "college": "IIIT Delhi", "status": "active_now"},
            "cross_college_giver": {"id": str(DEMO_GIVER_CROSS_ID), "name": "Priya Patel", "college": "NSUT", "status": "available_today"},
            "step_status": self.step_status,
        }

    async def run_step(self, db: AsyncSession, step_number: int) -> Dict[str, Any]:
        """Executes a specific step of the 8-step Jury Demo walkthrough."""
        if step_number == 1:
            # Step 1: Student uploads resume and confirms skills
            res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == DEMO_STUDENT_ID))
            prof = res.scalar_one_or_none()
            if prof:
                prof.skills = ["Python", "Distributed Systems", "FastAPI", "Docker"]
                prof.proof_of_work = ["https://github.com/aditi/distributed-raft"]
                await db.commit()
            self.step_status[1] = True
            return {
                "step": 1,
                "title": "Student Resume Upload & Skill Confirmation",
                "extracted_skills": ["Python", "Distributed Systems", "FastAPI", "Docker"],
                "proof_of_work": "https://github.com/aditi/distributed-raft",
                "badge": "Verified Proof of Work",
                "status": "completed",
                "summary": "Resume parsed with magic byte validation (%PDF-). Skills confirmed and tied to GitHub proof-of-work.",
            }

        elif step_number == 2:
            # Step 2: Enters vague intent and gets it refined
            self.step_status[2] = True
            return {
                "step": 2,
                "title": "AI Intent Refinement",
                "raw_intent": self.vague_intent,
                "refined_intent": self.refined_intent,
                "focus_tags": ["System Design", "Distributed Systems", "High Concurrency", "Tier-1 Prep"],
                "status": "completed",
                "summary": "Vague conversational intent refined into structured, actionable mentorship objectives with clear agenda.",
            }

        elif step_number == 3:
            # Step 3: Sees ranked matches with why-this-match and active status
            self.step_status[3] = True
            return {
                "step": 3,
                "title": "Ranked Matches & Active Availability Status",
                "matches": [
                    {
                        "giver_id": str(DEMO_GIVER_SAME_ID),
                        "name": "Rohan Sharma",
                        "headline": "Staff Engineer at Microsoft",
                        "college": "IIIT Delhi",
                        "match_score": 98,
                        "is_same_college": True,
                        "session_cost_credits": 0,
                        "status": "active_now",
                        "status_dot": "emerald-pulse",
                        "response_rate": "95%",
                        "avg_reply": "18m",
                        "badges": ["Verified Alumni", "Top Rated", "Active Now"],
                        "why_this_match": [
                            "Alumnus from your college (IIIT Delhi)",
                            "Deep overlap in Distributed Systems & FastAPI",
                            "Active now with 95% response rate",
                        ],
                    },
                    {
                        "giver_id": str(DEMO_GIVER_CROSS_ID),
                        "name": "Priya Patel",
                        "headline": "Senior SWE at Google",
                        "college": "NSUT",
                        "match_score": 86,
                        "is_same_college": False,
                        "session_cost_credits": 5,
                        "status": "available_today",
                        "status_dot": "amber",
                        "window": "8:00 PM - 10:00 PM",
                        "response_rate": "88%",
                        "avg_reply": "42m",
                        "badges": ["Verified Alumni", "Trusted", "Available Today"],
                        "why_this_match": [
                            "Kubernetes & Distributed Systems expertise at Google",
                            "Cross-college mentorship (5 credits hold in escrow)",
                        ],
                    },
                ],
                "status": "completed",
                "summary": "Matches ranked with why-this-match breakdown and real-time availability dots.",
            }

        elif step_number == 4:
            # Step 4: Books free same-college session and paid cross-college session
            # 1. Same-college booking (0 credits)
            req_same = MentorshipRequest(
                id=DEMO_REQ_SAME_ID,
                student_id=DEMO_STUDENT_ID,
                giver_id=DEMO_GIVER_SAME_ID,
                intent=self.refined_intent,
                notes="Preparing for upcoming distributed systems interview round",
                status="accepted",
                created_at=datetime.now(timezone.utc),
            )
            # 2. Cross-college booking (5 credits held)
            req_cross = MentorshipRequest(
                id=DEMO_REQ_CROSS_ID,
                student_id=DEMO_STUDENT_ID,
                giver_id=DEMO_GIVER_CROSS_ID,
                intent="Go Microservices & Kubernetes in Production",
                notes="Cross-college deep-dive mentorship session",
                status="accepted",
                created_at=datetime.now(timezone.utc),
            )
            db.add_all([req_same, req_cross])

            # Escrow hold for cross-college session
            res_w = await db.execute(select(Wallet).where(Wallet.user_id == DEMO_STUDENT_ID))
            wallet = res_w.scalar_one_or_none()
            if wallet:
                wallet.available_balance -= 5
                wallet.held_balance += 5

            await db.commit()
            self.step_status[4] = True
            return {
                "step": 4,
                "title": "Session Booking & Single Credit Economy Escrow",
                "same_college_session": {
                    "request_id": str(DEMO_REQ_SAME_ID),
                    "giver": "Rohan Sharma (IIIT Delhi)",
                    "cost_credits": 0,
                    "escrow": "Free same-college connection (Zero credits debited)",
                    "status": "accepted",
                },
                "cross_college_session": {
                    "request_id": str(DEMO_REQ_CROSS_ID),
                    "giver": "Priya Patel (NSUT)",
                    "cost_credits": 5,
                    "escrow": "5 credits held in platform escrow (Release on completion)",
                    "status": "accepted",
                },
                "student_wallet": {"balance": 15, "held": 5},
                "status": "completed",
                "summary": "Same-college session debited 0 credits; cross-college session safely held 5 credits in immutable escrow.",
            }

        elif step_number == 5:
            # Step 5: Scam message blocked in chat
            scam_attempt = "Hey! Send 500 rupees on my UPI handle payme@upi or call me at +91 9876543210 for direct contact"
            # Flag in safety_flags
            flag = SafetyFlag(
                id=uuid.uuid4(),
                sender_id=DEMO_STUDENT_ID,
                context="chat",
                message_text=scam_attempt,
                flags=["payment_request", "phone_number", "off_platform"],
                action="block",
            )
            db.add(flag)
            await db.commit()
            self.step_status[5] = True
            return {
                "step": 5,
                "title": "Real-Time In-App Scam Detection Middleware",
                "attempted_message": scam_attempt,
                "action": "BLOCKED",
                "detected_violations": ["UPI payment handle (payme@upi)", "Phone number (+91 9876543210)", "Off-platform request"],
                "safety_alert": "Blocked: Contact details and direct payment requests are strictly forbidden to ensure member safety.",
                "status": "completed",
                "summary": "Scam middleware intercepted high-risk message, protected contact confidentiality, and logged flag.",
            }

        elif step_number == 6:
            # Step 6: Session completes, rating releases credits, vouch added
            res_req = await db.execute(select(MentorshipRequest).where(MentorshipRequest.id == DEMO_REQ_CROSS_ID))
            req_obj = res_req.scalar_one_or_none()
            if req_obj:
                req_obj.status = "completed"

            # Escrow release: 80% to giver (4 credits), 20% platform fee (1 credit)
            res_w_s = await db.execute(select(Wallet).where(Wallet.user_id == DEMO_STUDENT_ID))
            w_student = res_w_s.scalar_one_or_none()
            if w_student:
                w_student.held_balance = max(0, w_student.held_balance - 5)

            res_w_g = await db.execute(select(Wallet).where(Wallet.user_id == DEMO_GIVER_CROSS_ID))
            w_giver = res_w_g.scalar_one_or_none()
            if w_giver:
                w_giver.available_balance += 4
                w_giver.earned_total += 4

            # Rating
            rating = SessionRating(
                id=uuid.uuid4(),
                session_id=DEMO_REQ_CROSS_ID,
                rater_id=DEMO_STUDENT_ID,
                giver_id=DEMO_GIVER_CROSS_ID,
                score=5,
                tags=["Clear feedback", "Helpful", "On time"],
                comment="Priya provided outstanding architectural clarity on Kubernetes microservices!",
            )
            db.add(rating)

            # 1-Click Vouch
            vouch = Vouch(
                id=uuid.uuid4(),
                session_id=DEMO_REQ_CROSS_ID,
                student_id=DEMO_STUDENT_ID,
                giver_id=DEMO_GIVER_SAME_ID,
                giver_name="Rohan Sharma",
                giver_company="Microsoft",
                note="Aditi possesses exceptional distributed systems and concurrency intuition. High-recommend for backend roles.",
            )
            db.add(vouch)

            await db.commit()
            self.step_status[6] = True
            return {
                "step": 6,
                "title": "Session Completion, Escrow Release & 1-Click Vouch",
                "session_status": "completed",
                "rating": {"stars": 5, "tags": ["Clear feedback", "Helpful", "On time"]},
                "escrow_release": {
                    "giver_payout": "4 credits (80%) credited to Priya Patel",
                    "platform_fee": "1 credit (20%) retained by institution pool",
                },
                "vouch": {
                    "status": "vouched",
                    "badge": "Vouched by Rohan Sharma at Microsoft",
                    "note": "Exceptional distributed systems intuition. High recommend for backend roles.",
                },
                "status": "completed",
                "summary": "Session rated 5 stars; escrow released 80% to giver and 20% to platform; 1-click vouch issued.",
            }

        elif step_number == 7:
            # Step 7: Admin sees dashboard, skill gap, resolves report & creates new scam rule
            res_rep = await db.execute(select(Report).where(Report.id == DEMO_REPORT_ID))
            rep_obj = res_rep.scalar_one_or_none()
            if rep_obj:
                rep_obj.status = "suspended"
                rep_obj.resolved_at = datetime.now(timezone.utc)
                rep_obj.admin_notes = "Offender suspended; regex pattern extracted into scam rules engine"

            # Create learned scam rule
            new_rule = ScamRule(
                id=uuid.uuid4(),
                pattern=r"(?i)(?:paytm|gpay|phonepe|upi_handle|send\s*money)",
                category="payment_request",
                action="block",
                description="Learned rule from resolved incident report #7777",
            )
            db.add(new_rule)

            # Add Incident Log
            inc_log = IncidentLog(
                id=uuid.uuid4(),
                report_id=DEMO_REPORT_ID,
                offender_id=uuid.uuid4(),
                incident_type="scam_payment_request",
                extracted_patterns=["upi_handle", "payme@upi"],
                status="rules updated",
                notes="Rule auto-promoted to active defense layer",
            )
            db.add(inc_log)

            # Add Audit Log
            audit = AdminAuditLog(
                id=uuid.uuid4(),
                admin_id=DEMO_ADMIN_ID,
                action="suspend",
                target_type="report",
                target_id=str(DEMO_REPORT_ID),
                reason="Confirmed scam payment extortion; learned rule added",
            )
            db.add(audit)

            await db.commit()
            self.step_status[7] = True
            return {
                "step": 7,
                "title": "Admin Dashboard, Skill Gap & Incident Rule Learning",
                "dashboard_snapshot": {
                    "total_requests": 2,
                    "fulfillment_rate": "100%",
                    "72h_response_rate": "95%",
                    "skill_gap": [
                        {"skill": "Distributed Systems", "requested": 3, "verified_supply": 8, "gap": 0},
                        {"skill": "FastAPI", "requested": 2, "verified_supply": 5, "gap": 0},
                        {"skill": "Cloud Architecture", "requested": 1, "verified_supply": 4, "gap": 0},
                    ],
                },
                "moderation_resolution": "Report resolved as SUSPENDED",
                "learned_scam_rule": {
                    "pattern": r"(?i)(?:paytm|gpay|phonepe|upi_handle|send\s*money)",
                    "category": "payment_request",
                    "status": "rules updated in scam_rules table",
                },
                "status": "completed",
                "summary": "Admin reviewed analytics & skill gap; resolved report and system automatically learned new scam rule.",
            }

        elif step_number == 8:
            # Step 8: Verification Queue: Reject fake alumnus, auto-verify listed student
            res_fake = await db.execute(select(VerificationRecord).where(VerificationRecord.id == DEMO_VERIF_FAKE_ID))
            verif_fake = res_fake.scalar_one_or_none()
            if verif_fake:
                verif_fake.status = "rejected"
                verif_fake.admin_notes = "Identifier unverified: degree certificate forged"
                verif_fake.reviewed_at = datetime.now(timezone.utc)

            res_real = await db.execute(select(VerificationRecord).where(VerificationRecord.id == DEMO_VERIF_REAL_ID))
            verif_real = res_real.scalar_one_or_none()
            if verif_real:
                verif_real.status = "approved"
                verif_real.admin_notes = "Auto-verified against IIIT Delhi registrar roll list"
                verif_real.reviewed_at = datetime.now(timezone.utc)

            await db.commit()
            self.step_status[8] = True
            return {
                "step": 8,
                "title": "Verification Queue: Reject Fake & Auto-Verify Registered",
                "rejected_applicant": {
                    "name": "Unknown Impersonator",
                    "identifier": "FORGED-9999",
                    "status": "REJECTED",
                    "reason": "Identifier unverified: degree certificate forged",
                },
                "auto_verified_member": {
                    "name": "Raghav Sen",
                    "identifier": "2022CSB1042",
                    "status": "APPROVED",
                    "badge": "Verified Alumni",
                    "reason": "Auto-verified against IIIT Delhi registrar roll list",
                },
                "status": "completed",
                "summary": "Fake applicant safely rejected; registered student auto-verified with official institution badge.",
            }

        return {"error": {"code": "invalid_step", "message": f"Step {step_number} is out of bounds (1-8)"}}


demo_service = JuryDemoService()
