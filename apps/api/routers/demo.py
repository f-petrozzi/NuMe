from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import can_use_demo, get_real_user
from database import get_db
from models.user import User

router = APIRouter(prefix="/api/demo", tags=["demo"])

DEMO_USER_EMAILS = [
    "student@nume.demo",
    "student2@nume.demo",
    "student3@nume.demo",
    "caregiver@nume.demo",
    "caregiver2@nume.demo",
    "older_adult@nume.demo",
    "older_adult2@nume.demo",
    "accessibility@nume.demo",
    "coordinator@nume.demo",
    "admin@nume.demo",
]

DEMO_LABELS: dict[str, str] = {
    "student@nume.demo": "Student — stressed",
    "student2@nume.demo": "Student — female",
    "student3@nume.demo": "Student — recovering",
    "caregiver@nume.demo": "Caregiver — exhausted (F)",
    "caregiver2@nume.demo": "Caregiver — exhausted (M)",
    "older_adult@nume.demo": "Older Adult — disrupted",
    "older_adult2@nume.demo": "Older Adult — stable",
    "accessibility@nume.demo": "Accessibility Focused",
    "coordinator@nume.demo": "Coordinator (staff)",
    "admin@nume.demo": "Admin (staff)",
}


@router.get("/users")
async def list_demo_users(
    user: User = Depends(get_real_user),
    db: AsyncSession = Depends(get_db),
):
    """List available demo accounts. Only accessible to internal privileged accounts."""
    if not can_use_demo(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for demo access")

    result = await db.execute(select(User).where(User.email.in_(DEMO_USER_EMAILS)))
    users = result.scalars().all()

    by_email = {u.email: u for u in users}
    return [
        {
            "id": by_email[email].id,
            "email": email,
            "role": by_email[email].role,
            "label": DEMO_LABELS.get(email, email),
        }
        for email in DEMO_USER_EMAILS
        if email in by_email
    ]
