"""
backend/app/modules/notifications/router.py - Notification Center Endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.models import User
from app.core.notifications import (
    get_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", summary="Get notifications and unread count")
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await get_user_notifications(db, current_user.id)
    return data


@router.patch("/{notification_id}/read", summary="Mark single notification as read")
async def mark_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await mark_notification_read(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or unauthorized",
        )
    return {"status": "success", "message": "Notification marked as read"}


@router.post("/mark-all-read", summary="Mark all notifications as read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await mark_all_notifications_read(db, current_user.id)
    return {"status": "success", "marked_read_count": count}
