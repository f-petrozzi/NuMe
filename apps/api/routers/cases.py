from datetime import datetime, timezone
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, is_staff
from database import get_db
from models.agents import Case, AgentRun
from models.events import NormalizedEvent
from models.user import User, UserProfile
from schemas.agents import CaseOut, CaseStatusUpdate


class CaseCreate(BaseModel):
    user_id: int
    run_id: Optional[int] = None
    risk_level: str = "low"

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _member_label(email: str | None, user_id: int) -> str:
    if not email:
        return f"Member #{user_id}"

    local_part = email.split("@")[0].strip()
    cleaned = re.sub(r"[._+-]+", " ", local_part)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() or f"Member #{user_id}"


def _serialize_case(
    case: Case,
    *,
    member_email: str | None,
    persona_type: str | None,
    summary: str | None,
) -> CaseOut:
    resolved_summary = summary.strip() if summary else f"{case.risk_level.title()} risk follow-up case."
    return CaseOut.model_validate(
        {
            "id": case.id,
            "user_id": case.user_id,
            "run_id": case.run_id,
            "risk_level": case.risk_level,
            "status": case.status,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
            "member_label": _member_label(member_email, case.user_id),
            "member_email": member_email,
            "persona_type": persona_type,
            "summary": resolved_summary,
        }
    )


async def _fetch_case_row(db: AsyncSession, case_id: int):
    result = await db.execute(
        select(Case, User.email, UserProfile.persona_type, NormalizedEvent.summary)
        .join(User, User.id == Case.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == Case.user_id)
        .outerjoin(AgentRun, AgentRun.id == Case.run_id)
        .outerjoin(NormalizedEvent, NormalizedEvent.id == AgentRun.normalized_event_id)
        .where(Case.id == case_id)
    )
    return result.one_or_none()


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(
    body: CaseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = Case(
        user_id=body.user_id,
        run_id=body.run_id,
        risk_level=body.risk_level,
        status="open",
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    row = await _fetch_case_row(db, case.id)
    if row is None:
        return case

    case, member_email, persona_type, summary = row
    return _serialize_case(case, member_email=member_email, persona_type=persona_type, summary=summary)


@router.get("", response_model=List[CaseOut])
async def list_cases(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Case, User.email, UserProfile.persona_type, NormalizedEvent.summary)
        .join(User, User.id == Case.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == Case.user_id)
        .outerjoin(AgentRun, AgentRun.id == Case.run_id)
        .outerjoin(NormalizedEvent, NormalizedEvent.id == AgentRun.normalized_event_id)
        .order_by(Case.created_at.desc())
        .limit(100)
    )
    if not is_staff(user):
        query = query.where(Case.user_id == user.id)

    result = await db.execute(query)
    return [
        _serialize_case(case, member_email=email, persona_type=persona_type, summary=summary)
        for case, email, persona_type, summary in result.all()
    ]


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(
    case_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await _fetch_case_row(db, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found")

    case, member_email, persona_type, summary = row
    if not is_staff(user) and case.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _serialize_case(case, member_email=member_email, persona_type=persona_type, summary=summary)


@router.put("/{case_id}/status", response_model=CaseOut)
async def update_case_status(
    case_id: int,
    body: CaseStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not is_staff(user) and case.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    case.status = body.status
    case.updated_at = datetime.now(timezone.utc)
    await db.commit()
    row = await _fetch_case_row(db, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found")

    case, member_email, persona_type, summary = row
    return _serialize_case(case, member_email=member_email, persona_type=persona_type, summary=summary)
