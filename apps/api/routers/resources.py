from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.agents import Resource
from models.user import User
from schemas.agents import ResourceOut

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("", response_model=List[ResourceOut])
async def list_resources(
    persona: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Resource)
    if persona:
        query = query.where(Resource.persona_type == persona)
    result = await db.execute(query.order_by(Resource.persona_type, Resource.category))
    return result.scalars().all()
