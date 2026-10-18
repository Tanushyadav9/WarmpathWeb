"""
backend/app/core/notifications.py - Notification Center Helper and Service.
Provides a shared notification creation utility that any module can call.
"""

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Notification


async def create_notification(
    db: AsyncSession,
    user_id: Any,
    title: str,
    message: str,
    type: str = "system",
    notif_type: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Notification:
    """
    Creates and persists a notification for a user.
    Types: 'request', 'session', 'verification', 'system', 'credit', 'report'
    """
    actual_type = notif_type or type
    notification = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        message=message,
        type=actual_type,
        data=data or {},
        is_read=False,
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def get_user_notifications(
    db: AsyncSession,
    user_id: Any,
    limit: int = 50,
) -> Dict[str, Any]:
    """Retrieve notifications and unread count for a user."""
    u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

    # Count unread
    count_stmt = select(func.count(Notification.id)).where(
        Notification.user_id == u_uuid,
        Notification.is_read.is_(False),
    )
    unread_res = await db.execute(count_stmt)
    unread_count = unread_res.scalar() or 0

    # Fetch recent
    stmt = (
        select(Notification)
        .where(Notification.user_id == u_uuid)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "unread_count": unread_count,
        "total": len(items),
        "notifications": [
            {
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "data": n.data,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


async def mark_notification_read(
    db: AsyncSession,
    notification_id: Any,
    user_id: Any,
) -> bool:
    """Mark a single notification as read."""
    n_uuid = uuid.UUID(str(notification_id)) if not isinstance(notification_id, uuid.UUID) else notification_id
    u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

    stmt = (
        update(Notification)
        .where(Notification.id == n_uuid, Notification.user_id == u_uuid)
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def mark_all_notifications_read(
    db: AsyncSession,
    user_id: Any,
) -> int:
    """Mark all notifications as read for a user."""
    u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

    stmt = (
        update(Notification)
        .where(Notification.user_id == u_uuid, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount
