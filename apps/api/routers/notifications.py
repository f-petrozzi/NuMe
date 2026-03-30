from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.agents import Notification
from models.user import User
from schemas.agents import NotificationOut


class NotificationCreate(BaseModel):
    user_id: int
    type: str
    content: str

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("", response_model=NotificationOut, status_code=201)
async def create_notification(
    body: NotificationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notif = Notification(user_id=body.user_id, type=body.type, content=body.content, status="queued")
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


@router.get("", response_model=List[NotificationOut])
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.put("/{notification_id}/delivered", response_model=NotificationOut)
async def mark_delivered(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    notif.status = "delivered"
    await db.commit()
    await db.refresh(notif)
    return notif
