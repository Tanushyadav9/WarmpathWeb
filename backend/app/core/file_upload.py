"""
File upload validation utility: MIME type, magic bytes, extension, and size inspection.
"""
import os
from typing import List, Optional, Tuple
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError

# Allowed MIME types and their corresponding magic byte signatures
ALLOWED_FILE_SIGNATURES = {
    "application/pdf": [b"%PDF-"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
}

ALLOWED_EXTENSIONS = {
    "application/pdf": [".pdf"],
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
}

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".py", ".php", ".js", ".html",
    ".htm", ".svg", ".vbs", ".msi", ".jar", ".war", ".dll", ".scr"
}


async def validate_and_read_file(
    file: UploadFile,
    max_size_bytes: int = settings.MAX_UPLOAD_SIZE_BYTES,
    allowed_mimes: Optional[List[str]] = None,
) -> Tuple[bytes, str, str]:
    """
    Validates uploaded file against security checks:
    1. Path traversal & filename sanitization
    2. Forbidden dangerous extensions
    3. Maximum file size limit (reads max_size_bytes + 1 to detect oversized files)
    4. Allowed MIME types
    5. Real file header / magic byte signatures

    Returns (file_content_bytes, sanitized_filename, validated_mime_type)
    """
    if allowed_mimes is None:
        allowed_mimes = list(ALLOWED_FILE_SIGNATURES.keys())

    if not file.filename:
        raise AppError(code="invalid_filename", message="No filename provided in upload.", status_code=400)

    # 1. Path traversal sanitization
    sanitized_filename = os.path.basename(file.filename.replace("\\", "/"))
    _, ext = os.path.splitext(sanitized_filename.lower())

    if not ext:
        raise AppError(code="invalid_extension", message="File must have a valid extension.", status_code=400)

    # 2. Reject dangerous executable/script extensions
    if ext in DANGEROUS_EXTENSIONS:
        raise AppError(
            code="forbidden_file_type",
            message=f"Executable or script file type '{ext}' is forbidden for upload.",
            status_code=400,
        )

    # 3. Size check: read up to max_size_bytes + 1
    content = await file.read(max_size_bytes + 1)
    if len(content) > max_size_bytes:
        limit_mb = max_size_bytes // (1024 * 1024)
        raise AppError(
            code="file_too_large",
            message=f"File exceeds maximum allowed size of {limit_mb} MB.",
            status_code=413,
            details={"max_size_bytes": max_size_bytes, "limit_mb": limit_mb},
        )

    if len(content) == 0:
        raise AppError(code="empty_file", message="Uploaded file cannot be empty.", status_code=400)

    # 4. Check Content-Type
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in allowed_mimes:
        raise AppError(
            code="unsupported_media_type",
            message=f"Unsupported file MIME type '{content_type}'. Allowed types: {allowed_mimes}",
            status_code=415,
        )

    # Check extension matches MIME type
    valid_exts = ALLOWED_EXTENSIONS.get(content_type, [])
    if ext not in valid_exts:
        raise AppError(
            code="mismatched_extension",
            message=f"Extension '{ext}' does not match content type '{content_type}'. Expected: {valid_exts}",
            status_code=400,
        )

    # 5. Magic byte signature inspection
    expected_signatures = ALLOWED_FILE_SIGNATURES.get(content_type, [])
    signature_matches = any(content.startswith(sig) for sig in expected_signatures)
    if not signature_matches:
        raise AppError(
            code="invalid_file_signature",
            message=f"File content does not match the expected magic bytes for '{content_type}'.",
            status_code=400,
        )

    return content, sanitized_filename, content_type
