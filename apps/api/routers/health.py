"""
Health data endpoints — all reads come from local DB, never live from Garmin.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from garmin_sync import (
    _cache_get,
    _cache_set,
    connect_user,
    disconnect_user,
    get_connected_user_ids,
    run_manual_sync,
    settings,
)
from models.health import (
    GarminConnection,
    HealthActivity,
    HealthCalorieLog,
    HealthDailyMetrics,
    HealthSleepSession,
    HealthSyncRun,
)
from models.user import User
from openai_client import generate_text
from schemas.health import (
    ActivityOut,
    CalorieEstimateOut,
    CalorieEstimateRequest,
    CalorieLogIn,
    CalorieLogOut,
    DailyMetricsOut,
    GarminAuthStatus,
    GarminConnectIn,
    HealthOverviewOut,
    SleepSessionOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


# ---------------------------------------------------------------------------
# Overview (cached)
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=HealthOverviewOut)
async def health_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = _cache_get(user.id)
    if cached:
        return HealthOverviewOut(**cached)

    today = date.today()

    # Latest daily metrics
    daily_result = await db.execute(
        select(HealthDailyMetrics)
        .where(HealthDailyMetrics.user_id == user.id)
        .order_by(HealthDailyMetrics.metric_date.desc())
        .limit(1)
    )
    daily = daily_result.scalar_one_or_none()

    # Latest sleep session
    sleep_result = await db.execute(
        select(HealthSleepSession)
        .where(HealthSleepSession.user_id == user.id)
        .order_by(HealthSleepSession.sleep_date.desc())
        .limit(1)
    )
    sleep = sleep_result.scalar_one_or_none()

    garmin_connected = user.id in get_connected_user_ids() or 0 in get_connected_user_ids()

    data = {
        "latest_date": daily.metric_date.isoformat() if daily else None,
        "steps": daily.steps if daily else 0,
        "step_goal": daily.step_goal if daily else 8000,
        "active_calories": daily.active_calories if daily else 0,
        "total_calories": daily.total_calories if daily else 0,
        "resting_hr": daily.resting_hr if daily else 0,
        "avg_hr": daily.avg_hr if daily else 0,
        "body_battery_high": daily.body_battery_high if daily else 0,
        "body_battery_low": daily.body_battery_low if daily else 0,
        "stress_avg": daily.stress_avg if daily else 0,
        "active_minutes": daily.active_minutes if daily else 0,
        "sleep_hours": round(sleep.duration_seconds / 3600, 1) if sleep else 0.0,
        "sleep_score": sleep.sleep_score if sleep else 0,
        "garmin_connected": garmin_connected,
    }
    _cache_set(user.id, data)
    return HealthOverviewOut(**data)


# ---------------------------------------------------------------------------
# Daily metrics list
# ---------------------------------------------------------------------------

@router.get("/daily", response_model=List[DailyMetricsOut])
async def daily_metrics(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(HealthDailyMetrics)
        .where(HealthDailyMetrics.user_id == user.id, HealthDailyMetrics.metric_date >= since)
        .order_by(HealthDailyMetrics.metric_date.desc())
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Sleep history
# ---------------------------------------------------------------------------

@router.get("/sleep", response_model=List[SleepSessionOut])
async def sleep_history(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(HealthSleepSession)
        .where(HealthSleepSession.user_id == user.id, HealthSleepSession.sleep_date >= since)
        .order_by(HealthSleepSession.sleep_date.desc())
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------

@router.get("/activities", response_model=List[ActivityOut])
async def activities(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HealthActivity)
        .where(HealthActivity.user_id == user.id)
        .order_by(HealthActivity.start_time.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Garmin auth status
# ---------------------------------------------------------------------------

@router.get("/garmin/auth-status", response_model=GarminAuthStatus)
async def garmin_auth_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check both in-memory client registry and DB connection record
    in_memory = user.id in get_connected_user_ids() or 0 in get_connected_user_ids()
    conn_result = await db.execute(
        select(GarminConnection).where(GarminConnection.user_id == user.id)
    )
    conn_row = conn_result.scalar_one_or_none()
    connected = in_memory or conn_row is not None

    last_sync = conn_row.last_sync_at if conn_row else None
    if connected and last_sync is None:
        run_result = await db.execute(
            select(HealthSyncRun)
            .where(HealthSyncRun.user_id == user.id, HealthSyncRun.status == "success")
            .order_by(HealthSyncRun.finished_at.desc())
            .limit(1)
        )
        run = run_result.scalar_one_or_none()
        if run:
            last_sync = run.finished_at

    return GarminAuthStatus(
        connected=connected,
        user_id=user.id if connected else None,
        garmin_email=conn_row.garmin_email if conn_row else None,
        last_sync=last_sync,
    )


@router.post("/garmin/connect", response_model=GarminAuthStatus, status_code=201)
async def garmin_connect(
    body: GarminConnectIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Link a Garmin account to this user. Authenticates immediately and caches tokens."""
    if not settings.garmin_enabled:
        raise HTTPException(status_code=400, detail="Garmin integration is not enabled in server config")
    try:
        await connect_user(user.id, body.email, body.password)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Garmin authentication failed: {exc}") from exc

    now = datetime.now(timezone.utc)
    # Upsert connection record
    conn_result = await db.execute(
        select(GarminConnection).where(GarminConnection.user_id == user.id)
    )
    conn_row = conn_result.scalar_one_or_none()
    if conn_row:
        conn_row.garmin_email = body.email
        conn_row.connected_at = now
    else:
        conn_row = GarminConnection(user_id=user.id, garmin_email=body.email, connected_at=now)
        db.add(conn_row)
    await db.commit()
    await db.refresh(conn_row)

    return GarminAuthStatus(
        connected=True,
        user_id=user.id,
        garmin_email=conn_row.garmin_email,
        last_sync=None,
    )


@router.delete("/garmin/disconnect", status_code=204)
async def garmin_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unlink Garmin — removes in-memory client, token files, and DB record."""
    await disconnect_user(user.id)
    await db.execute(
        delete(GarminConnection).where(GarminConnection.user_id == user.id)
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Manual sync trigger
# ---------------------------------------------------------------------------

@router.post("/sync")
async def manual_sync(user: User = Depends(get_current_user)):
    if not settings.garmin_enabled:
        raise HTTPException(status_code=400, detail="Garmin integration is not enabled")
    result = await run_manual_sync(user.id)
    return result


# ---------------------------------------------------------------------------
# Calorie log
# ---------------------------------------------------------------------------

@router.get("/calorie-log", response_model=List[CalorieLogOut])
async def list_calorie_log(
    log_date: Optional[date] = Query(None, description="YYYY-MM-DD filter"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(HealthCalorieLog).where(HealthCalorieLog.user_id == user.id)
    if log_date:
        query = query.where(HealthCalorieLog.log_date == log_date)
    result = await db.execute(query.order_by(HealthCalorieLog.created_at.desc()).limit(200))
    return result.scalars().all()


@router.post("/calorie-log", response_model=CalorieLogOut, status_code=201)
async def add_calorie_log(
    body: CalorieLogIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = HealthCalorieLog(
        user_id=user.id,
        log_date=body.log_date,
        meal_type=body.meal_type,
        food_name=body.food_name,
        calories=body.calories,
        quantity=body.quantity,
        notes=body.notes,
        ai_estimated=body.ai_estimated,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/calorie-log/{entry_id}", status_code=204)
async def delete_calorie_log(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HealthCalorieLog).where(HealthCalorieLog.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.delete(entry)
    await db.commit()


@router.post("/calorie-log/ai-estimate", response_model=CalorieEstimateOut)
async def ai_calorie_estimate(
    body: CalorieEstimateRequest,
    user: User = Depends(get_current_user),
):
    """Use Azure OpenAI to estimate calories for a food item."""
    try:
        prompt = (
            f"Estimate the calories in: {body.food_name}, quantity: {body.quantity}. "
            "Reply with only a JSON object: {\"calories\": <integer>, \"confidence\": \"high|medium|low\"}"
        )
        import json, re
        text = await generate_text(prompt)
        m = re.search(r'\{[^}]+\}', text)
        if m:
            data = json.loads(m.group())
            return CalorieEstimateOut(
                food_name=body.food_name,
                quantity=body.quantity,
                estimated_calories=int(data.get("calories", 0)),
                confidence=data.get("confidence", "medium"),
            )
    except Exception as exc:
        logger.warning("AI calorie estimate failed: %s", exc)

    return CalorieEstimateOut(
        food_name=body.food_name,
        quantity=body.quantity,
        estimated_calories=0,
        confidence="low",
    )
