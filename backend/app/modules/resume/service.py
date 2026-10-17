import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError
from app.core.events import event_bus, ResumeParsedPayload, ProfileUpdatedPayload
from app.core.models import (
    Consent,
    StudentProfile,
    StudentIntent,
    Resume,
    GitHubProof,
    StudentMatchProfile,
    User,
    Request,
    RequestMessage,
    AuditLog,
)
from app.adapters.github import get_github_adapter
from app.modules.resume.schemas import (
    ConsentUpdateItem,
    ConsentItemResponse,
    ConsentsListResponse,
    ParsedResumeData,
    StructuredIntent,
    GitHubProofResponse,
)
from app.modules.resume.storage import get_storage_driver
from app.modules.resume.extractor import extract_resume_text
from app.modules.resume.parser import (
    RESUME_PARSER_SYSTEM_PROMPT,
    INTENT_STRUCTURING_SYSTEM_PROMPT,
    call_gemini_json,
    normalize_skills,
    generate_embedding,
)

VALID_CONSENT_PURPOSES = [
    "resume_processing",
    "profile_matching",
    "visibility_to_matched_givers",
]


class ResumeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = get_storage_driver()

    # --- Consent Operations (DPDP Act - F33) ---

    async def get_consents(self, user_id: uuid.UUID) -> ConsentsListResponse:
        stmt = select(Consent).where(Consent.user_id == user_id)
        res = await self.session.execute(stmt)
        records = {c.purpose: c for c in res.scalars().all()}

        items = []
        for purpose in VALID_CONSENT_PURPOSES:
            c = records.get(purpose)
            if c:
                items.append(
                    ConsentItemResponse(
                        purpose=c.purpose,
                        granted=c.granted,
                        granted_at=c.granted_at,
                        withdrawn_at=c.withdrawn_at,
                        text_version=c.text_version,
                    )
                )
            else:
                items.append(
                    ConsentItemResponse(
                        purpose=purpose,
                        granted=False,
                        granted_at=None,
                        withdrawn_at=None,
                        text_version="v1.0",
                    )
                )
        return ConsentsListResponse(items=items)

    async def has_consent(self, user_id: uuid.UUID, purpose: str) -> bool:
        stmt = select(Consent).where(
            Consent.user_id == user_id,
            Consent.purpose == purpose,
            Consent.granted == True,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def update_consents(
        self,
        user_id: uuid.UUID,
        consents: List[ConsentUpdateItem],
        text_version: str = "v1.0",
    ) -> ConsentsListResponse:
        now = datetime.now(timezone.utc)
        resume_processing_withdrawn = False
        profile_matching_withdrawn = False

        for item in consents:
            purpose = item["purpose"] if isinstance(item, dict) else item.purpose
            granted = item["granted"] if isinstance(item, dict) else item.granted
            if purpose not in VALID_CONSENT_PURPOSES:
                continue

            stmt = select(Consent).where(
                Consent.user_id == user_id,
                Consent.purpose == purpose,
            )
            res = await self.session.execute(stmt)
            record = res.scalar_one_or_none()

            if record:
                if not granted and record.granted:
                    record.granted = False
                    record.withdrawn_at = now
                    if purpose == "resume_processing":
                        resume_processing_withdrawn = True
                    elif purpose == "profile_matching":
                        profile_matching_withdrawn = True
                elif granted and not record.granted:
                    record.granted = True
                    record.granted_at = now
                    record.withdrawn_at = None
                record.text_version = text_version
            else:
                record = Consent(
                    user_id=user_id,
                    purpose=purpose,
                    granted=granted,
                    granted_at=now if granted else None,
                    withdrawn_at=None if granted else now,
                    text_version=text_version,
                )
                self.session.add(record)
                if not item.granted and item.purpose == "resume_processing":
                    resume_processing_withdrawn = True
                elif not item.granted and item.purpose == "profile_matching":
                    profile_matching_withdrawn = True

        await self.session.flush()

        # If resume_processing is withdrawn, delete derived resume and embeddings
        if resume_processing_withdrawn:
            await self.delete_resume_data(user_id)

        # If profile_matching is withdrawn, clear matching projection
        if profile_matching_withdrawn:
            await self.session.execute(
                delete(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id)
            )

        await self.session.commit()
        return await self.get_consents(user_id)

    # --- Resume Upload and Parsing Pipeline (F4) ---

    async def process_resume_upload(
        self,
        user_id: uuid.UUID,
        file_bytes: bytes,
        original_filename: str,
    ) -> str:
        # 1. Enforce DPDP consent requirement
        if not await self.has_consent(user_id, "resume_processing"):
            raise AppError(
                code="consent_required",
                message="DPDP consent for 'resume_processing' is required prior to uploading a resume.",
                status_code=403,
            )

        # 2. Extract and validate format & contents
        doc_format, raw_text = extract_resume_text(file_bytes)

        # 3. Store file through storage driver
        resume_id = str(uuid.uuid4())
        filename = f"{user_id}_{resume_id}.{doc_format}"
        file_path = await self.storage.save(file_bytes, filename)

        # 4. Parse structured data using Gemini
        parsed_json = await call_gemini_json(RESUME_PARSER_SYSTEM_PROMPT, raw_text)

        # 5. Normalize skills against taxonomy
        normalized_skills = await normalize_skills(parsed_json.get("skills", []), self.session)
        parsed_json["skills"] = normalized_skills

        # 6. Generate embedding from skills and domains
        embedding_text = f"Skills: {', '.join(s['name'] for s in normalized_skills)}. Domains: {', '.join(parsed_json.get('domains', []))}. Experience: {parsed_json.get('experience_level', 'student')}"
        embedding = await generate_embedding(embedding_text)

        now = datetime.now(timezone.utc)

        # 7. Upsert student_profile
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()

        if profile:
            profile.raw_text = raw_text
            profile.resume_file_path = file_path
            profile.parsed = parsed_json
            profile.edited = None
            profile.is_confirmed = False
            profile.skills_label = "extracted skills, student-confirmed"
            profile.embedding = embedding
            profile.updated_at = now
        else:
            profile = StudentProfile(
                user_id=user_id,
                raw_text=raw_text,
                resume_file_path=file_path,
                parsed=parsed_json,
                edited=None,
                is_confirmed=False,
                skills_label="extracted skills, student-confirmed",
                embedding=embedding,
                updated_at=now,
            )
            self.session.add(profile)

        # 8. Upsert Resume table
        stmt_r = select(Resume).where(Resume.user_id == user_id)
        res_r = await self.session.execute(stmt_r)
        resume_rec = res_r.scalar_one_or_none()
        if resume_rec:
            resume_rec.raw_file_ref = file_path
            resume_rec.parsed_json = parsed_json
            resume_rec.edited_json = None
            resume_rec.is_committed = False
            resume_rec.parsed_at = now
        else:
            resume_rec = Resume(
                user_id=user_id,
                raw_file_ref=file_path,
                parsed_json=parsed_json,
                edited_json=None,
                is_committed=False,
                parsed_at=now,
            )
            self.session.add(resume_rec)

        # 9. Sync StudentMatchProfile
        stmt_m = select(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id)
        res_m = await self.session.execute(stmt_m)
        match_prof = res_m.scalar_one_or_none()
        if match_prof:
            match_prof.skills = normalized_skills
            match_prof.domains = parsed_json.get("domains", [])
            match_prof.profile_embedding = embedding
            match_prof.profile_version = (match_prof.profile_version or 1) + 1
            match_prof.updated_at = now
        else:
            match_prof = StudentMatchProfile(
                user_id=user_id,
                skills=normalized_skills,
                domains=parsed_json.get("domains", []),
                profile_embedding=embedding,
                updated_at=now,
            )
            self.session.add(match_prof)

        # 10. Outbox events: resume.parsed and profile.updated
        await event_bus.publish(
            self.session,
            "resume.parsed",
            ResumeParsedPayload(
                user_id=str(user_id),
                skills_count=len(normalized_skills),
                projects_count=len(parsed_json.get("projects", [])),
            ),
        )
        await event_bus.publish(
            self.session,
            "profile.updated",
            ProfileUpdatedPayload(
                user_id=str(user_id),
                updated_fields=["skills", "education", "projects", "embedding"],
            ),
        )

        await self.session.commit()
        return resume_id

    # --- Student Profile Operations (F4) ---

    async def get_profile(self, user_id: uuid.UUID) -> Dict[str, Any]:
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile or not profile.parsed:
            raise AppError(
                code="profile_not_found",
                message="No resume profile found for this student. Please upload your resume first.",
                status_code=404,
            )

        merged = dict(profile.parsed)
        if profile.edited:
            merged.update({k: v for k, v in profile.edited.items() if v is not None})

        return {
            "user_id": profile.user_id,
            "parsed": profile.parsed,
            "edited": profile.edited,
            "merged": merged,
            "is_confirmed": getattr(profile, "is_confirmed", False),
            "skills_label": getattr(profile, "skills_label", "extracted skills, student-confirmed"),
            "hide_cgpa": getattr(profile, "hide_cgpa", False),
            "has_embedding": profile.embedding is not None,
            "updated_at": profile.updated_at,
        }

    async def update_profile(self, user_id: uuid.UUID, updates: Dict[str, Any]) -> Dict[str, Any]:
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            raise AppError(
                code="profile_not_found",
                message="Profile not found. Please upload a resume first.",
                status_code=404,
            )

        current_edits = dict(profile.edited or {})
        for k, v in updates.items():
            if v is not None:
                current_edits[k] = v
        profile.edited = current_edits
        now = datetime.now(timezone.utc)
        profile.updated_at = now

        # Merge and re-embed
        merged = dict(profile.parsed or {})
        merged.update(current_edits)

        skills = merged.get("skills", [])
        domains = merged.get("domains", [])
        skills_str = ", ".join(s["name"] if isinstance(s, dict) else str(s) for s in skills)
        domains_str = ", ".join(domains) if isinstance(domains, list) else str(domains)
        embed_text = f"Skills: {skills_str}. Domains: {domains_str}. Experience: {merged.get('experience_level', 'student')}"

        new_embedding = await generate_embedding(embed_text)
        profile.embedding = new_embedding

        # Update Resume record
        stmt_r = select(Resume).where(Resume.user_id == user_id)
        res_r = await self.session.execute(stmt_r)
        resume_rec = res_r.scalar_one_or_none()
        if resume_rec:
            resume_rec.edited_json = current_edits

        # Update StudentMatchProfile projection
        stmt_m = select(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id)
        res_m = await self.session.execute(stmt_m)
        match_prof = res_m.scalar_one_or_none()
        if match_prof:
            match_prof.skills = skills
            match_prof.domains = domains if isinstance(domains, list) else [str(domains)]
            match_prof.profile_embedding = new_embedding
            match_prof.profile_version = (match_prof.profile_version or 1) + 1
            match_prof.updated_at = now

        await event_bus.publish(
            self.session,
            "profile.updated",
            ProfileUpdatedPayload(
                user_id=str(user_id),
                updated_fields=list(updates.keys()) + ["embedding"],
            ),
        )

        await self.session.commit()
        return await self.get_profile(user_id)

    async def confirm_profile(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Explicit student confirmation of extracted/edited profile."""
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            raise AppError(code="profile_not_found", message="Profile not found.", status_code=404)

        profile.is_confirmed = True
        profile.skills_label = "extracted skills, student-confirmed"
        profile.updated_at = datetime.now(timezone.utc)

        stmt_r = select(Resume).where(Resume.user_id == user_id)
        res_r = await self.session.execute(stmt_r)
        resume_rec = res_r.scalar_one_or_none()
        if resume_rec:
            resume_rec.is_committed = True

        await self.session.commit()
        return await self.get_profile(user_id)

    # --- GitHub Proof of Work (F5) ---

    async def add_or_update_github_proof(self, user_id: uuid.UUID, repo_url_or_username: str) -> GitHubProofResponse:
        adapter = get_github_adapter()
        proof_data = await adapter.fetch_proof(repo_url_or_username)

        stmt = select(GitHubProof).where(GitHubProof.user_id == user_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if record:
            record.username = proof_data.username
            record.repo_url = proof_data.repo_url
            record.repo_count = proof_data.repo_count
            record.top_languages = proof_data.top_languages
            record.total_commits = proof_data.total_commits
            record.stars_count = proof_data.stars_count
            record.verified_at = now
        else:
            record = GitHubProof(
                user_id=user_id,
                username=proof_data.username,
                repo_url=proof_data.repo_url,
                repo_count=proof_data.repo_count,
                top_languages=proof_data.top_languages,
                total_commits=proof_data.total_commits,
                stars_count=proof_data.stars_count,
                verified_at=now,
            )
            self.session.add(record)

        # Update StudentMatchProfile with proof of work
        stmt_m = select(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id)
        res_m = await self.session.execute(stmt_m)
        match_prof = res_m.scalar_one_or_none()
        if match_prof:
            match_prof.has_github_proof = True
            match_prof.github_languages = proof_data.top_languages
            match_prof.updated_at = now

        await self.session.commit()
        return GitHubProofResponse(
            id=record.id,
            user_id=record.user_id,
            username=record.username,
            repo_url=record.repo_url,
            repo_count=record.repo_count,
            top_languages=record.top_languages,
            total_commits=record.total_commits,
            stars_count=record.stars_count,
            verified_at=record.verified_at,
            badge="Proof of work",
        )

    async def get_github_proof(self, user_id: uuid.UUID) -> GitHubProofResponse:
        stmt = select(GitHubProof).where(GitHubProof.user_id == user_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise AppError(
                code="github_proof_not_found",
                message="No GitHub proof linked yet. Submit your repository link.",
                status_code=404,
            )
        return GitHubProofResponse(
            id=record.id,
            user_id=record.user_id,
            username=record.username,
            repo_url=record.repo_url,
            repo_count=record.repo_count,
            top_languages=record.top_languages,
            total_commits=record.total_commits,
            stars_count=record.stars_count,
            verified_at=record.verified_at,
            badge="Proof of work",
        )

    # --- Student Intent Operations (F6) ---

    async def get_intent(self, user_id: uuid.UUID) -> Dict[str, Any]:
        stmt = select(StudentIntent).where(StudentIntent.user_id == user_id)
        res = await self.session.execute(stmt)
        intent = res.scalar_one_or_none()

        if not intent:
            raise AppError(
                code="intent_not_found",
                message="No intent registered for this student yet.",
                status_code=404,
            )

        return {
            "user_id": intent.user_id,
            "raw_text": intent.raw_text,
            "goal_type": intent.goal_type,
            "target_roles": intent.target_roles or [],
            "target_domains": intent.target_domains or [],
            "structured": intent.structured,
            "has_embedding": intent.intent_embedding is not None,
            "updated_at": intent.updated_at,
        }

    async def update_intent(
        self,
        user_id: uuid.UUID,
        raw_text: str,
        goal_type: Optional[str] = "internship",
        target_roles: Optional[List[str]] = None,
        target_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        structured = await call_gemini_json(INTENT_STRUCTURING_SYSTEM_PROMPT, raw_text)
        embed_text = f"Goal: {structured.get('goal', raw_text)}. Roles: {', '.join(structured.get('roles', []))}. Domains: {', '.join(structured.get('domains', []))}"
        embedding = await generate_embedding(embed_text)

        stmt = select(StudentIntent).where(StudentIntent.user_id == user_id)
        res = await self.session.execute(stmt)
        intent = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        roles = target_roles or structured.get("roles", [])
        domains = target_domains or structured.get("domains", [])

        if intent:
            intent.raw_text = raw_text
            intent.goal_type = goal_type or structured.get("goal")
            intent.target_roles = roles
            intent.target_domains = domains
            intent.structured = structured
            intent.intent_embedding = embedding
            intent.updated_at = now
        else:
            intent = StudentIntent(
                user_id=user_id,
                raw_text=raw_text,
                goal_type=goal_type or structured.get("goal"),
                target_roles=roles,
                target_domains=domains,
                structured=structured,
                intent_embedding=embedding,
                updated_at=now,
            )
            self.session.add(intent)

        # Sync intent with StudentMatchProfile
        stmt_m = select(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id)
        res_m = await self.session.execute(stmt_m)
        match_prof = res_m.scalar_one_or_none()
        if match_prof:
            match_prof.intent_goal = raw_text
            match_prof.intent_roles = roles
            match_prof.intent_domains = domains
            match_prof.intent_help_type = structured.get("help_type", "guidance")
            match_prof.intent_embedding = embedding
            match_prof.updated_at = now

        await event_bus.publish(
            self.session,
            "profile.updated",
            ProfileUpdatedPayload(
                user_id=str(user_id),
                updated_fields=["intent", "intent_embedding"],
            ),
        )

        await self.session.commit()
        return await self.get_intent(user_id)

    # --- Deletion and Privacy Data Purge (F33) ---

    async def delete_resume_data(self, user_id: uuid.UUID) -> None:
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()

        if profile:
            if profile.resume_file_path:
                await self.storage.delete(profile.resume_file_path)
            profile.parsed = None
            profile.edited = None
            profile.raw_text = None
            profile.resume_file_path = None
            profile.embedding = None
            profile.is_confirmed = False

        # Delete resume table row
        await self.session.execute(delete(Resume).where(Resume.user_id == user_id))

        # Clear match projection embedding
        stmt_m = select(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id)
        res_m = await self.session.execute(stmt_m)
        match_prof = res_m.scalar_one_or_none()
        if match_prof:
            match_prof.profile_embedding = None

        await event_bus.publish(
            self.session,
            "profile.updated",
            ProfileUpdatedPayload(
                user_id=str(user_id),
                updated_fields=["resume_deleted", "embedding_deleted"],
            ),
        )
        await self.session.flush()

    async def update_profile_visibility(self, user_id: uuid.UUID, hide_cgpa: Optional[bool] = None) -> Dict[str, Any]:
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise AppError(code="profile_not_found", message="Profile not found", status_code=404)

        if hide_cgpa is not None:
            profile.hide_cgpa = hide_cgpa
        await self.session.commit()
        return {"hide_cgpa": profile.hide_cgpa}

    async def export_user_data(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Generates comprehensive machine-readable JSON bundle for DPDP data export."""
        res_u = await self.session.execute(select(User).where(User.id == user_id))
        user = res_u.scalar_one_or_none()
        if not user:
            raise AppError(code="user_not_found", message="User not found", status_code=404)

        user_dict = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "institution_id": user.institution_id,
            "verification_level": user.verification_level,
            "trust_score": user.trust_score,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

        # Profile
        res_p = await self.session.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))
        p = res_p.scalar_one_or_none()
        profile_dict = None
        if p:
            profile_dict = {
                "headline": p.headline,
                "bio": p.bio,
                "batch": p.batch,
                "department": p.department,
                "cgpa": p.cgpa if not p.hide_cgpa else None,
                "target_role": p.target_role,
                "target_domain": p.target_domain,
                "skills_label": p.skills_label,
                "is_confirmed": p.is_confirmed,
            }

        # Resume
        res_r = await self.session.execute(select(Resume).where(Resume.user_id == user_id))
        r = res_r.scalar_one_or_none()
        resume_dict = None
        if r:
            resume_dict = {
                "parsed": r.parsed_json,
                "edited": r.edited_json,
                "is_committed": r.is_committed,
                "parsed_at": r.parsed_at.isoformat() if r.parsed_at else None,
            }

        # GitHub
        res_g = await self.session.execute(select(GitHubProof).where(GitHubProof.user_id == user_id))
        g = res_g.scalar_one_or_none()
        github_dict = None
        if g:
            github_dict = {
                "username": g.username,
                "repo_url": g.repo_url,
                "repo_count": g.repo_count,
                "top_languages": g.top_languages,
                "total_commits": g.total_commits,
                "stars_count": g.stars_count,
                "verified_at": g.verified_at.isoformat() if g.verified_at else None,
            }

        # Consents
        res_c = await self.session.execute(select(Consent).where(Consent.user_id == user_id))
        consents_list = [
            {
                "purpose": c.purpose,
                "granted": c.granted,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                "text_version": c.text_version,
            }
            for c in res_c.scalars().all()
        ]

        # Requests
        res_req = await self.session.execute(
            select(Request).where((Request.seeker_id == user_id) | (Request.giver_id == user_id))
        )
        requests_list = [
            {
                "id": str(req.id),
                "status": req.status,
                "intent_category": req.intent_category,
                "ask_details": req.ask_details,
                "created_at": req.created_at.isoformat() if req.created_at else None,
            }
            for req in res_req.scalars().all()
        ]

        return {
            "user": user_dict,
            "profile": profile_dict,
            "resume": resume_dict,
            "github_proof": github_dict,
            "consents": consents_list,
            "requests": requests_list,
            "exported_at": datetime.now(timezone.utc),
        }

    async def purge_all_user_data(self, user_id: uuid.UUID) -> None:
        """Completely purges all data related to a user for permanent Right to be Forgotten deletion."""
        # 1. Clean up file storage
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile and profile.resume_file_path:
            await self.storage.delete(profile.resume_file_path)

        # 2. Delete User entity (cascades to all child relations)
        stmt_u = select(User).where(User.id == user_id)
        res_u = await self.session.execute(stmt_u)
        user = res_u.scalar_one_or_none()
        if user:
            await self.session.delete(user)

        # 3. Explicitly delete any non-cascaded tables
        await self.session.execute(delete(Consent).where(Consent.user_id == user_id))
        await self.session.execute(delete(StudentIntent).where(StudentIntent.user_id == user_id))
        await self.session.execute(delete(StudentMatchProfile).where(StudentMatchProfile.user_id == user_id))
        await self.session.execute(delete(Resume).where(Resume.user_id == user_id))
        await self.session.execute(delete(GitHubProof).where(GitHubProof.user_id == user_id))

        # 4. Audit log entry
        self.session.add(
            AuditLog(
                user_id=None,
                action="account_deleted_dpdp",
                resource_type="user",
                resource_id=str(user_id),
                metadata_json={"reason": "right_to_be_forgotten"},
            )
        )
        await self.session.commit()
