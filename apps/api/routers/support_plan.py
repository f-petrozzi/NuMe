from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.agents import Intervention
from models.personalization import SupportPlanFeedbackEvent
from models.user import User
from schemas.agents import SupportPlanCurrentOut, SupportPlanFeedbackEventIn, SupportPlanFeedbackEventOut
from support_plan import build_current_support_plan

router = APIRouter(prefix="/api/support-plan", tags=["support-plan"])


@router.get("/current", response_model=SupportPlanCurrentOut)
async def get_current_support_plan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await build_current_support_plan(db=db, user=user)


@router.post(
    "/feedback",
    response_model=SupportPlanFeedbackEventOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_support_plan_feedback_event(
    feedback: SupportPlanFeedbackEventIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    intervention = (
        await db.execute(
            select(Intervention)
            .where(Intervention.id == feedback.intervention_id, Intervention.user_id == user.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if intervention is None:
        raise HTTPException(status_code=404, detail="Support plan intervention not found")

    if feedback.run_id is not None and feedback.run_id != intervention.run_id:
        raise HTTPException(
            status_code=400,
            detail="Feedback run_id does not match the linked intervention",
        )

    payload = dict(feedback.payload or {})
    payload["source"] = feedback.source.strip()
    payload["recommendation_kind"] = feedback.recommendation_kind
    if feedback.recommendation_id is not None:
        payload["recommendation_id"] = feedback.recommendation_id

    event = SupportPlanFeedbackEvent(
        user_id=user.id,
        run_id=intervention.run_id,
        intervention_id=intervention.id,
        event_type=feedback.event_type,
        payload=payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
