"""
Quota endpoint — exposes current rate limit counters for the authenticated user.
GET /api/quota/daily
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.user import User
from settings import settings

router = APIRouter(prefix="/api/quota", tags=["quota"])


class DailyQuotaOut(BaseModel):
    global_units_today: int
    global_units_limit: int
    user_units_today: int
    user_units_limit: int
    user_units_this_hour: int
    user_hourly_limit: int
    reset_at: str   # ISO-8601 UTC midnight tomorrow
    ai_enabled: bool


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _hour() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")


async def _get_count(db: AsyncSession, key: str) -> int:
    result = await db.execute(
        text("SELECT count FROM ai_rate_counters WHERE bucket_key = :k"),
        {"k": key},
    )
    row = result.one_or_none()
    return row[0] if row else 0


@router.get("/daily", response_model=DailyQuotaOut)
async def get_daily_quota(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today, hour = _today(), _hour()

    global_count = await _get_count(db, f"g:{today}")
    user_day = await _get_count(db, f"u:{user.id}:{today}")
    user_hour = await _get_count(db, f"u:{user.id}:h:{hour}")

    now = datetime.now(timezone.utc)
    reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return DailyQuotaOut(
        global_units_today=global_count,
        global_units_limit=settings.rate_limit_global_daily_units,
        user_units_today=user_day,
        user_units_limit=settings.rate_limit_user_daily_units,
        user_units_this_hour=user_hour,
        user_hourly_limit=settings.rate_limit_user_hourly_units,
        reset_at=reset.isoformat(),
        ai_enabled=settings.ai_endpoints_enabled,
    )
