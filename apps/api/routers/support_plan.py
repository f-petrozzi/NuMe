from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.user import User
from schemas.agents import SupportPlanCurrentOut
from support_plan import build_current_support_plan

router = APIRouter(prefix="/api/support-plan", tags=["support-plan"])


@router.get("/current", response_model=SupportPlanCurrentOut)
async def get_current_support_plan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await build_current_support_plan(db=db, user=user)
