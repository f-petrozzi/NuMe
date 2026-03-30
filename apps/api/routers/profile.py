from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.user import AccessibilityPreferences, User, UserProfile
from schemas.profile import (
    AccessibilityOut,
    AccessibilityUpdate,
    OnboardingRequest,
    ProfileOut,
    ProfileUpdate,
)

router = APIRouter(prefix="/api", tags=["profile"])


@router.post("/onboarding", response_model=ProfileOut, status_code=201)
async def onboarding(
    body: OnboardingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Profile already exists — use PUT /api/profile")

    profile = UserProfile(
        user_id=user.id,
        age_range=body.age_range,
        sex=body.sex,
        height_cm=body.height_cm,
        weight_kg=body.weight_kg,
        goal=body.goal,
        activity_level=body.activity_level,
        dietary_style=body.dietary_style,
        allergies=body.allergies,
        persona_type=body.persona_type,
    )
    db.add(profile)

    access = AccessibilityPreferences(
        user_id=user.id,
        simplified_language=body.simplified_language,
        large_text=body.large_text,
        low_energy_mode=body.low_energy_mode,
    )
    db.add(access)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/profile", response_model=ProfileOut)
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — complete onboarding first")
    return profile


@router.put("/profile", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/profile/accessibility", response_model=AccessibilityOut)
async def get_accessibility(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AccessibilityPreferences).where(AccessibilityPreferences.user_id == user.id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Accessibility preferences not found")
    return prefs


@router.put("/profile/accessibility", response_model=AccessibilityOut)
async def update_accessibility(
    body: AccessibilityUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AccessibilityPreferences).where(AccessibilityPreferences.user_id == user.id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = AccessibilityPreferences(user_id=user.id)
        db.add(prefs)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)

    await db.commit()
    await db.refresh(prefs)
    return prefs
