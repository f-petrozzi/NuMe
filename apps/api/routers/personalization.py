from __future__ import annotations

from fastapi import HTTPException
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.user import User
from personalization import build_personalization_context
from schemas.personalization import PersonalizationContextOut

router = APIRouter(prefix="/api/personalization", tags=["personalization"])


@router.get("/context", response_model=PersonalizationContextOut)
async def get_personalization_context(
    run_id: int | None = Query(None),
    scenario: str = Query("live"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await build_personalization_context(
            db=db,
            user=user,
            run_id=run_id,
            scenario=scenario,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
