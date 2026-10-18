"""
backend/app/core/audit.py - Centralized Audit Logging Helper.
Ensures every security action, verification decision, and status transition is recorded.
"""

from typing import Any, Dict, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditLog


async def log_audit_event(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Creates and persists an immutable audit log entry."""
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        metadata_json=metadata_json or {},
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry
