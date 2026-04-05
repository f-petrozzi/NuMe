from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, is_staff
from database import get_db
from models.agents import AgentRun, Intervention
from models.personalization import ActivityTemplate, PersonalizationStateSnapshot, WellnessTemplate
from models.recipes import Recipe
from models.user import User
from schemas.agents import InterventionOut


class InterventionCreate(BaseModel):
    user_id: int
    run_id: Optional[int] = None
    state_snapshot_id: Optional[int] = None
    recipe_id: Optional[int] = None
    activity_template_id: Optional[int] = None
    wellness_template_id: Optional[int] = None
    meal_suggestion: str = ""
    activity_suggestion: str = ""
    wellness_action: str = ""
    empathy_message: str = ""
    meal_constraints: List[str] = Field(default_factory=list)
    risk_subscores: Optional[Dict[str, Any]] = None
    why_chosen: Optional[Dict[str, Any]] = None
    alternatives_considered: Optional[List[Any]] = None
    why_changed_from_previous: Optional[List[str]] = None

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


async def _validate_related_records(
    *,
    body: InterventionCreate,
    target_user_id: int,
    db: AsyncSession,
) -> None:
    if body.state_snapshot_id is not None:
        snapshot = await db.get(PersonalizationStateSnapshot, body.state_snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Personalization state snapshot not found")
        if snapshot.user_id != target_user_id:
            raise HTTPException(status_code=403, detail="Snapshot does not belong to the target user")

    if body.recipe_id is not None:
        recipe = await db.get(Recipe, body.recipe_id)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if recipe.user_id not in {None, target_user_id}:
            raise HTTPException(status_code=403, detail="Recipe does not belong to the target user")

    if body.activity_template_id is not None:
        activity_template = await db.get(ActivityTemplate, body.activity_template_id)
        if activity_template is None or not activity_template.active:
            raise HTTPException(status_code=404, detail="Activity template not found")

    if body.wellness_template_id is not None:
        wellness_template = await db.get(WellnessTemplate, body.wellness_template_id)
        if wellness_template is None or not wellness_template.active:
            raise HTTPException(status_code=404, detail="Wellness template not found")


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
    await _validate_related_records(body=body, target_user_id=target_user_id, db=db)
    intervention = Intervention(
        user_id=target_user_id,
        run_id=body.run_id,
        state_snapshot_id=body.state_snapshot_id,
        recipe_id=body.recipe_id,
        activity_template_id=body.activity_template_id,
        wellness_template_id=body.wellness_template_id,
        meal_suggestion=body.meal_suggestion,
        activity_suggestion=body.activity_suggestion,
        wellness_action=body.wellness_action,
        empathy_message=body.empathy_message,
        meal_constraints=body.meal_constraints,
        risk_subscores=body.risk_subscores,
        why_chosen=body.why_chosen,
        alternatives_considered=body.alternatives_considered,
        why_changed_from_previous=body.why_changed_from_previous,
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
