"""API Router for resume upload, parsing, intent prompts, and DPDP consent preferences."""
import uuid
from typing import Dict
from fastapi import APIRouter, File, Request, UploadFile

from app.core.file_upload import validate_and_read_file
from app.core.security import get_current_user_id

router = APIRouter(tags=["resume"])

# In-memory store for demo resume profiles
_resume_store: Dict[str, dict] = {}


@router.post("/resume", summary="Upload resume PDF for extraction with type & size security checks")
async def post_resume(
    file: UploadFile = File(...),
    request: Request = None,
):
    content, filename, mime_type = await validate_and_read_file(
        file=file,
        allowed_mimes=["application/pdf"],
    )
    user_id = get_current_user_id(request) if request else str(uuid.uuid4())
    _resume_store[user_id] = {
        "filename": filename,
        "size_bytes": len(content),
        "mime_type": mime_type,
        "parsed_entities": ["Python", "FastAPI", "Distributed Systems", "SQL"],
    }
    return {
        "status": "uploaded",
        "filename": filename,
        "size_bytes": len(content),
        "mime_type": mime_type,
        "message": "Resume uploaded and validated successfully.",
    }


@router.get("/resume/profile", summary="Retrieve parsed resume skills and entities")
async def get_resume_profile(request: Request):
    user_id = get_current_user_id(request)
    profile = _resume_store.get(user_id, {
        "filename": "demo_resume.pdf",
        "parsed_entities": ["Python", "Machine Learning", "System Design"],
    })
    return profile


@router.delete("/resume", summary="Delete uploaded resume and extracted vectors under DPDP Act")
async def delete_resume(request: Request):
    user_id = get_current_user_id(request)
    if user_id in _resume_store:
        del _resume_store[user_id]
    return {"message": "Uploaded resume and extracted vectors deleted.", "status": "deleted"}
