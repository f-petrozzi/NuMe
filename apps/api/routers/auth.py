from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.user import User
from schemas.auth import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.refresh(user, ["profile"])
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        has_profile=user.profile is not None,
    )
