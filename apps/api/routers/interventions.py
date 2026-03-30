from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, is_staff
from database import get_db
from models.agents import AgentRun, Intervention
from models.user import User
from schemas.agents import InterventionOut


class InterventionCreate(BaseModel):
    user_id: int
    run_id: Optional[int] = None
    meal_suggestion: str = ""
    activity_suggestion: str = ""
    wellness_action: str = ""
    empathy_message: str = ""
    meal_constraints: List[str] = []

router = APIRouter(prefix="/api/interventions", tags=["interventions"])


async def _resolve_target_user_id(
    *,
    requested_user_id: int,
    run_id: Optional[int],
    current_user: User,
    db: AsyncSession,
) -> int:
    if run_id is not None:
        run = (
            await db.execute(select(AgentRun).where(AgentRun.id == run_id))
        ).scalar_one_or_none()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if not is_staff(current_user) and run.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return run.user_id

    if not is_staff(current_user):
        return current_user.id

    return requested_user_id


@router.post("", response_model=InterventionOut, status_code=201)
async def create_intervention(
    body: InterventionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_user_id = await _resolve_target_user_id(
        requested_user_id=body.user_id,
        run_id=body.run_id,
        current_user=user,
        db=db,
    )
    intervention = Intervention(
        user_id=target_user_id,
        run_id=body.run_id,
        meal_suggestion=body.meal_suggestion,
        activity_suggestion=body.activity_suggestion,
        wellness_action=body.wellness_action,
        empathy_message=body.empathy_message,
        meal_constraints=body.meal_constraints,
    )
    db.add(intervention)
    await db.commit()
    await db.refresh(intervention)
    return intervention


@router.get("", response_model=List[InterventionOut])
async def list_interventions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Intervention)
        .where(Intervention.user_id == user.id)
        .order_by(Intervention.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.get("/{intervention_id}", response_model=InterventionOut)
async def get_intervention(
    intervention_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    if intervention.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return intervention
