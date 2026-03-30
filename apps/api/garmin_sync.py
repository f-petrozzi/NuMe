"""
garmin_sync.py — Garmin Connect health data sync engine.

Adapted from Nest homelab app:
  - Replaced `person` string key with `user_id` (int FK)
  - Replaced aiosqlite with SQLAlchemy 2.0 async sessions
  - Replaced SQLite INSERT OR REPLACE with PostgreSQL INSERT ... ON CONFLICT DO UPDATE
  - Token cache dir keyed by user_id instead of person_a/person_b
  - No household/multi-person assumptions — one user account per client
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import stat
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.events import NormalizedEvent
from models.health import (
    HealthActivity,
    HealthDailyMetrics,
    HealthSleepSession,
    HealthSyncRun,
)
from settings import settings

logger = logging.getLogger(__name__)

_GARMIN_TOKEN_FILES = ("oauth1_token.json", "oauth2_token.json")

# ---------------------------------------------------------------------------
# Module-level client registry: user_id → authenticated Garmin client
# ---------------------------------------------------------------------------
_garmin_clients: dict[int, Any] = {}
_client_lock = asyncio.Lock()

# In-memory overview cache: user_id → (data_dict, monotonic_ts)
_METRIC_CACHE: dict[int, tuple[dict, float]] = {}
_CACHE_TTL = 900.0  # 15 minutes


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_get(user_id: int) -> dict | None:
    entry = _METRIC_CACHE.get(user_id)
    if entry and (time.monotonic() - entry[1]) < _CACHE_TTL:
        return entry[0]
    return None


def _cache_set(user_id: int, data: dict) -> None:
    _METRIC_CACHE[user_id] = (data, time.monotonic())


def _cache_invalidate(user_id: int | None = None) -> None:
    if user_id is not None:
        _METRIC_CACHE.pop(user_id, None)
    else:
        _METRIC_CACHE.clear()


# ---------------------------------------------------------------------------
# Token directory helpers
# ---------------------------------------------------------------------------

def _token_dir(user_id: int) -> str:
    return os.path.join(settings.garmin_token_dir, str(user_id))


def _ensure_private_dir(path: str) -> None:
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)


def _has_token_cache(token_dir: str) -> bool:
    return all(os.path.exists(os.path.join(token_dir, f)) for f in _GARMIN_TOKEN_FILES)


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------

def _load_garmin_client_sync(email: str, password: str, token_dir: str) -> Any:
    """Synchronous — always called via asyncio.to_thread()."""
    try:
        from garminconnect import Garmin  # type: ignore[import]
    except ImportError:
        raise RuntimeError("garminconnect package is not installed")

    client = Garmin(email=email, password=password, is_cn=False, prompt_mfa=None)
    if _has_token_cache(token_dir):
        try:
            client.login(tokenstore=token_dir)
            return client
        except Exception:
            logger.warning("Garmin token cache stale for %s — re-authenticating", token_dir)

    client.login()
    _ensure_private_dir(token_dir)
    client.garth.dump(token_dir)
    return client


async def init_garmin_clients(user_id: int | None = None) -> None:
    """
    Initialize Garmin client(s) on startup or after bootstrap.
    When user_id is None, initializes the global default user from env vars.
    Tokens are loaded from disk — no network call if cache is fresh (~1 year TTL).
    """
    if not settings.garmin_enabled:
        return

    email = settings.garmin_username
    password = settings.garmin_password
    if not email:
        logger.debug("GARMIN_USERNAME not set — skipping Garmin init")
        return

    # For multi-user we'd look up per-user credentials from DB.
    # MVP: single global Garmin account mapped to whichever user_id is given.
    # When called from the bootstrap script a real user_id is passed.
    target_id = user_id or 0  # 0 = global placeholder until a real user is set
    tdir = _token_dir(target_id)
    _ensure_private_dir(settings.garmin_token_dir)
    _ensure_private_dir(tdir)

    if not password and not _has_token_cache(tdir):
        logger.debug("Garmin user %s missing password and token cache — skipping", target_id)
        return

    async with _client_lock:
        try:
            client = await asyncio.to_thread(_load_garmin_client_sync, email, password, tdir)
            _garmin_clients[target_id] = client
            logger.info("Garmin client ready for user_id=%s (%s)", target_id, email)
        except Exception as exc:
            logger.error("Garmin auth failed for user_id=%s: %s", target_id, exc)


async def _get_client(user_id: int) -> Any | None:
    """Return authenticated client for this user, or None if not configured."""
    async with _client_lock:
        # Direct match
        if user_id in _garmin_clients:
            return _garmin_clients[user_id]
        # Fall back to global placeholder (user_id=0) when only one account configured
        return _garmin_clients.get(0)


def get_connected_user_ids() -> list[int]:
    return list(_garmin_clients.keys())


async def connect_user(user_id: int, email: str, password: str) -> None:
    """
    Authenticate a specific user's Garmin account and register the client.
    Dumps OAuth tokens to disk for future token-only logins.
    Raises on authentication failure so the caller can return a 400.
    """
    tdir = _token_dir(user_id)
    _ensure_private_dir(settings.garmin_token_dir)
    _ensure_private_dir(tdir)
    async with _client_lock:
        client = await asyncio.to_thread(_load_garmin_client_sync, email, password, tdir)
        _garmin_clients[user_id] = client
    logger.info("Garmin connected for user_id=%s (%s)", user_id, email)


async def disconnect_user(user_id: int) -> None:
    """Remove the in-memory client and delete cached tokens from disk."""
    import shutil

    async with _client_lock:
        _garmin_clients.pop(user_id, None)
    _cache_invalidate(user_id)
    tdir = _token_dir(user_id)
    if os.path.exists(tdir):
        await asyncio.to_thread(shutil.rmtree, tdir, ignore_errors=True)
    logger.info("Garmin disconnected for user_id=%s", user_id)


# ---------------------------------------------------------------------------
# Metric extraction helpers (identical logic to Nest, field names unchanged)
# ---------------------------------------------------------------------------

def _safe(val: Any, default: Any = 0) -> Any:
    return val if val is not None else default


def _extract_daily_stats(stats: dict | None) -> dict:
    if not stats:
        return {}
    return {
        "steps": _safe(stats.get("totalSteps"), 0),
        "step_goal": _safe(stats.get("dailyStepGoal"), 8000),
        "active_calories": _safe(stats.get("activeKilocalories"), 0),
        "total_calories": _safe(stats.get("totalKilocalories"), 0),
        "resting_hr": _safe(stats.get("restingHeartRate"), 0),
        "avg_hr": _safe(stats.get("averageHeartRate") or stats.get("avgHeartRate"), 0),
        "floors_climbed": _safe(stats.get("floorsAscended"), 0),
        "active_minutes": int(_safe(stats.get("activeSeconds", 0), 0) // 60),
    }


def _extract_body_battery(bb_data: list | None) -> dict:
    if not bb_data:
        return {}
    high_val = low_val = 0
    for day in bb_data:
        for row in (day.get("bodyBatteryValuesArray") or []):
            if len(row) >= 2 and row[1] is not None:
                val = int(row[1])
                if val > high_val:
                    high_val = val
                if low_val == 0 or (val > 0 and val < low_val):
                    low_val = val
    return {"body_battery_high": high_val, "body_battery_low": low_val}


def _extract_stress(stress_data: dict | None) -> dict:
    if not stress_data:
        return {}
    avg = stress_data.get("avgStressLevel") or stress_data.get("averageStressLevel") or 0
    return {"stress_avg": int(avg)}


def _extract_intensity(intensity: dict | None) -> dict:
    if not intensity:
        return {}
    return {
        "intensity_minutes_moderate": int(_safe(intensity.get("weeklyModerateIntensityMinutes"), 0)),
        "intensity_minutes_vigorous": int(_safe(intensity.get("weeklyVigorousIntensityMinutes"), 0)),
    }


def _extract_hrv(hrv_data: dict | None) -> dict:
    if not hrv_data:
        return {}
    summary = hrv_data.get("hrvSummary") or hrv_data
    return {
        "hrv_weekly_avg": float(_safe(summary.get("weeklyAvg"), 0)),
        "hrv_status": str(_safe(summary.get("status") or summary.get("hrvStatus"), "")),
    }


def _extract_sleep(sleep_data: dict | None) -> dict:
    if not sleep_data:
        return {}
    sd = sleep_data.get("dailySleepDTO") or sleep_data
    return {
        "sleep_start": str(sd.get("sleepStartTimestampGMT") or sd.get("sleepStart") or ""),
        "sleep_end": str(sd.get("sleepEndTimestampGMT") or sd.get("sleepEnd") or ""),
        "duration_seconds": _safe(sd.get("sleepTimeSeconds"), 0),
        "deep_seconds": _safe(sd.get("deepSleepSeconds"), 0),
        "light_seconds": _safe(sd.get("lightSleepSeconds"), 0),
        "rem_seconds": _safe(sd.get("remSleepSeconds"), 0),
        "awake_seconds": _safe(sd.get("awakeSleepSeconds"), 0),
        "sleep_score": _safe(
            ((sd.get("sleepScores") or {}).get("overall") or {}).get("value")
            or sd.get("sleepScore")
            or sd.get("averageSleepStress"),
            0,
        ),
        "avg_spo2": float(_safe(sleep_data.get("averageSpO2Value") or sd.get("avgSpO2"), 0)),
        "avg_respiration": float(_safe(sd.get("averageRespirationValue") or sd.get("avgRespirationRate"), 0)),
    }


def _extract_activity(raw: dict) -> dict:
    return {
        "garmin_activity_id": str(raw.get("activityId", "")),
        "activity_type": str(
            (raw.get("activityType") or {}).get("typeKey")
            or raw.get("activityType")
            or "other"
        ),
        "activity_name": str(raw.get("activityName") or ""),
        "start_time": str(raw.get("startTimeGMT") or raw.get("startTimeLocal") or ""),
        "duration_seconds": int(_safe(raw.get("duration"), 0)),
        "distance_meters": float(_safe(raw.get("distance"), 0)),
        "calories": int(_safe(raw.get("calories"), 0)),
        "avg_hr": int(_safe(raw.get("averageHR"), 0)),
        "max_hr": int(_safe(raw.get("maxHR"), 0)),
        "elevation_gain_meters": float(_safe(raw.get("elevationGain"), 0)),
        "avg_speed_mps": float(_safe(raw.get("averageSpeed"), 0)),
        "training_load": float(_safe(raw.get("trainingLoadScore") or raw.get("aerobicTrainingEffect"), 0)),
        "raw_json": raw,
    }


# ---------------------------------------------------------------------------
# Core sync functions
# ---------------------------------------------------------------------------

async def _sync_daily_for_date(
    db: AsyncSession,
    client: Any,
    user_id: int,
    date_str: str,
) -> dict:
    merged: dict = {
        "steps": 0, "step_goal": 8000, "active_calories": 0, "total_calories": 0,
        "resting_hr": 0, "avg_hr": 0, "body_battery_high": 0, "body_battery_low": 0,
        "stress_avg": 0, "intensity_minutes_moderate": 0, "intensity_minutes_vigorous": 0,
        "floors_climbed": 0, "spo2_avg": 0.0, "hrv_weekly_avg": 0.0,
        "hrv_status": "", "vo2_max": 0.0, "active_minutes": 0,
    }

    try:
        stats = await asyncio.to_thread(client.get_stats, date_str)
        merged.update(_extract_daily_stats(stats or {}))
    except Exception as exc:
        logger.warning("get_stats failed user=%s date=%s: %s", user_id, date_str, exc)

    try:
        bb = await asyncio.to_thread(client.get_body_battery, date_str, date_str)
        if bb:
            merged.update(_extract_body_battery(bb if isinstance(bb, list) else [bb]))
    except Exception as exc:
        logger.debug("get_body_battery failed user=%s date=%s: %s", user_id, date_str, exc)

    try:
        stress = await asyncio.to_thread(client.get_stress_data, date_str)
        merged.update(_extract_stress(stress or {}))
    except Exception as exc:
        logger.debug("get_stress_data failed user=%s date=%s: %s", user_id, date_str, exc)

    try:
        intensity = await asyncio.to_thread(client.get_intensity_minutes_data, date_str)
        merged.update(_extract_intensity(intensity or {}))
    except Exception as exc:
        logger.debug("get_intensity_minutes failed user=%s date=%s: %s", user_id, date_str, exc)

    try:
        hrv = await asyncio.to_thread(client.get_hrv_data, date_str)
        merged.update(_extract_hrv(hrv or {}))
    except Exception as exc:
        logger.debug("get_hrv_data failed user=%s date=%s: %s", user_id, date_str, exc)

    try:
        maxmetrics = await asyncio.to_thread(client.get_max_metrics, date_str)
        if isinstance(maxmetrics, list) and maxmetrics:
            maxmetrics = maxmetrics[0]
        if isinstance(maxmetrics, dict):
            vo2 = maxmetrics.get("vo2MaxPreciseValue") or maxmetrics.get("vo2Max") or 0
            if vo2:
                merged["vo2_max"] = float(vo2)
    except Exception as exc:
        logger.debug("get_max_metrics failed user=%s date=%s: %s", user_id, date_str, exc)

    now = datetime.now(timezone.utc)
    stmt = pg_insert(HealthDailyMetrics).values(
        user_id=user_id,
        metric_date=date.fromisoformat(date_str),
        steps=merged["steps"],
        step_goal=merged["step_goal"],
        active_calories=merged["active_calories"],
        total_calories=merged["total_calories"],
        resting_hr=merged["resting_hr"],
        avg_hr=merged["avg_hr"],
        body_battery_high=merged["body_battery_high"],
        body_battery_low=merged["body_battery_low"],
        stress_avg=merged["stress_avg"],
        intensity_minutes_moderate=merged["intensity_minutes_moderate"],
        intensity_minutes_vigorous=merged["intensity_minutes_vigorous"],
        floors_climbed=merged["floors_climbed"],
        spo2_avg=merged["spo2_avg"],
        hrv_weekly_avg=merged["hrv_weekly_avg"],
        hrv_status=merged["hrv_status"],
        vo2_max=merged["vo2_max"],
        active_minutes=merged["active_minutes"],
        raw_json={"date": date_str, "user_id": user_id},
        synced_at=now,
    ).on_conflict_do_update(
        constraint="uq_daily_metrics_user_date",
        set_={
            "steps": merged["steps"],
            "step_goal": merged["step_goal"],
            "active_calories": merged["active_calories"],
            "total_calories": merged["total_calories"],
            "resting_hr": merged["resting_hr"],
            "avg_hr": merged["avg_hr"],
            "body_battery_high": merged["body_battery_high"],
            "body_battery_low": merged["body_battery_low"],
            "stress_avg": merged["stress_avg"],
            "intensity_minutes_moderate": merged["intensity_minutes_moderate"],
            "intensity_minutes_vigorous": merged["intensity_minutes_vigorous"],
            "floors_climbed": merged["floors_climbed"],
            "spo2_avg": merged["spo2_avg"],
            "hrv_weekly_avg": merged["hrv_weekly_avg"],
            "hrv_status": merged["hrv_status"],
            # vo2_max: only update if new value > 0
            "active_minutes": merged["active_minutes"],
            "synced_at": now,
        },
    )
    await db.execute(stmt)
    return merged


async def _sync_sleep_for_date(
    db: AsyncSession,
    client: Any,
    user_id: int,
    date_str: str,
) -> dict:
    try:
        sleep_data = await asyncio.to_thread(client.get_sleep_data, date_str)
    except Exception as exc:
        logger.warning("get_sleep_data failed user=%s date=%s: %s", user_id, date_str, exc)
        return {}

    extracted = _extract_sleep(sleep_data or {})
    if not extracted.get("duration_seconds"):
        return {}

    now = datetime.now(timezone.utc)
    stmt = pg_insert(HealthSleepSession).values(
        user_id=user_id,
        sleep_date=date.fromisoformat(date_str),
        sleep_start=extracted.get("sleep_start", ""),
        sleep_end=extracted.get("sleep_end", ""),
        duration_seconds=extracted.get("duration_seconds", 0),
        deep_seconds=extracted.get("deep_seconds", 0),
        light_seconds=extracted.get("light_seconds", 0),
        rem_seconds=extracted.get("rem_seconds", 0),
        awake_seconds=extracted.get("awake_seconds", 0),
        sleep_score=extracted.get("sleep_score", 0),
        avg_spo2=extracted.get("avg_spo2", 0.0),
        avg_respiration=extracted.get("avg_respiration", 0.0),
        raw_json={"date": date_str, "user_id": user_id},
        synced_at=now,
    ).on_conflict_do_update(
        constraint="uq_sleep_sessions_user_date",
        set_={
            "sleep_start": extracted.get("sleep_start", ""),
            "sleep_end": extracted.get("sleep_end", ""),
            "duration_seconds": extracted.get("duration_seconds", 0),
            "deep_seconds": extracted.get("deep_seconds", 0),
            "light_seconds": extracted.get("light_seconds", 0),
            "rem_seconds": extracted.get("rem_seconds", 0),
            "awake_seconds": extracted.get("awake_seconds", 0),
            "sleep_score": extracted.get("sleep_score", 0),
            "avg_spo2": extracted.get("avg_spo2", 0.0),
            "avg_respiration": extracted.get("avg_respiration", 0.0),
            "synced_at": now,
        },
    )
    await db.execute(stmt)
    return extracted


async def _sync_activities_for_range(
    db: AsyncSession,
    client: Any,
    user_id: int,
    start_date: str,
    end_date: str,
    limit: int = 50,
) -> int:
    try:
        activities = await asyncio.to_thread(client.get_activities_by_date, start_date, end_date)
    except Exception as exc:
        logger.warning("get_activities_by_date failed user=%s: %s", user_id, exc)
        return 0

    if not activities:
        return 0

    upserted = 0
    now = datetime.now(timezone.utc)
    for raw in activities[:limit]:
        ex = _extract_activity(raw)
        if not ex.get("garmin_activity_id") or not ex.get("start_time"):
            continue
        try:
            stmt = pg_insert(HealthActivity).values(
                user_id=user_id,
                garmin_activity_id=ex["garmin_activity_id"],
                activity_type=ex["activity_type"],
                activity_name=ex["activity_name"],
                start_time=ex["start_time"],
                duration_seconds=ex["duration_seconds"],
                distance_meters=ex["distance_meters"],
                calories=ex["calories"],
                avg_hr=ex["avg_hr"],
                max_hr=ex["max_hr"],
                elevation_gain_meters=ex["elevation_gain_meters"],
                avg_speed_mps=ex["avg_speed_mps"],
                training_load=ex["training_load"],
                raw_json=ex["raw_json"],
                synced_at=now,
            ).on_conflict_do_update(
                constraint="uq_activities_user_garmin_id",
                set_={
                    "activity_type": ex["activity_type"],
                    "activity_name": ex["activity_name"],
                    "duration_seconds": ex["duration_seconds"],
                    "distance_meters": ex["distance_meters"],
                    "calories": ex["calories"],
                    "avg_hr": ex["avg_hr"],
                    "max_hr": ex["max_hr"],
                    "elevation_gain_meters": ex["elevation_gain_meters"],
                    "avg_speed_mps": ex["avg_speed_mps"],
                    "training_load": ex["training_load"],
                    "synced_at": now,
                },
            )
            await db.execute(stmt)
            upserted += 1
        except Exception as exc:
            logger.warning("Failed to upsert activity %s user=%s: %s", ex["garmin_activity_id"], user_id, exc)

    return upserted


# ---------------------------------------------------------------------------
# Public sync API
# ---------------------------------------------------------------------------

async def sync_user_range(
    db: AsyncSession,
    user_id: int,
    days_back: int = 7,
) -> dict[str, int]:
    """
    Sync daily metrics, sleep, and activities for one user for the last N days.
    Returns {metrics_upserted, sleep_upserted, activities_upserted}.
    """
    client = await _get_client(user_id)
    if client is None:
        logger.warning("No Garmin client for user_id=%s — skipping", user_id)
        return {"metrics_upserted": 0, "sleep_upserted": 0, "activities_upserted": 0}

    today = date.today()
    counts = {"metrics_upserted": 0, "sleep_upserted": 0, "activities_upserted": 0}
    start_date = (today - timedelta(days=days_back - 1)).isoformat()
    end_date = today.isoformat()

    for i in range(days_back):
        day = (today - timedelta(days=i)).isoformat()
        try:
            await _sync_daily_for_date(db, client, user_id, day)
            counts["metrics_upserted"] += 1
        except Exception as exc:
            logger.error("Daily sync failed user=%s date=%s: %s", user_id, day, exc)

        try:
            result = await _sync_sleep_for_date(db, client, user_id, day)
            if result:
                counts["sleep_upserted"] += 1
        except Exception as exc:
            logger.error("Sleep sync failed user=%s date=%s: %s", user_id, day, exc)

    try:
        acts = await _sync_activities_for_range(db, client, user_id, start_date, end_date)
        counts["activities_upserted"] = acts
    except Exception as exc:
        logger.error("Activity sync failed user=%s: %s", user_id, exc)

    await db.commit()
    _cache_invalidate(user_id)

    # Project latest day's data into a NormalizedEvent so the agent pipeline
    # can read real Garmin signals via /api/events/recent.
    try:
        await _emit_health_snapshot_event(db, user_id, today.isoformat())
        await db.commit()
    except Exception as exc:
        logger.warning("NormalizedEvent emission failed user=%s: %s", user_id, exc)

    return counts


async def _emit_health_snapshot_event(db: AsyncSession, user_id: int, date_str: str) -> None:
    """Write a NormalizedEvent summarising today's health metrics for the agent layer."""
    result = await db.execute(
        select(HealthDailyMetrics)
        .where(HealthDailyMetrics.user_id == user_id, HealthDailyMetrics.metric_date == date.fromisoformat(date_str))
        .limit(1)
    )
    metrics = result.scalar_one_or_none()

    sleep_result = await db.execute(
        select(HealthSleepSession)
        .where(HealthSleepSession.user_id == user_id, HealthSleepSession.sleep_date == date.fromisoformat(date_str))
        .limit(1)
    )
    sleep = sleep_result.scalar_one_or_none()

    signals: dict = {}
    if metrics:
        signals.update({
            "steps": metrics.steps,
            "step_goal": metrics.step_goal,
            "active_calories": metrics.active_calories,
            "resting_hr": metrics.resting_hr,
            "body_battery_high": metrics.body_battery_high,
            "body_battery_low": metrics.body_battery_low,
            "stress_level": metrics.stress_avg,
            "hrv_weekly_avg": metrics.hrv_weekly_avg,
            "hrv_status": metrics.hrv_status,
            "vo2_max": metrics.vo2_max,
            "active_minutes": metrics.active_minutes,
        })
    if sleep:
        sleep_hours = round(sleep.duration_seconds / 3600, 2) if sleep.duration_seconds else 0
        signals.update({
            "sleep_hours": sleep_hours,
            "sleep_score": sleep.sleep_score,
            "deep_sleep_minutes": sleep.deep_seconds // 60,
            "rem_sleep_minutes": sleep.rem_seconds // 60,
            "avg_spo2": sleep.avg_spo2,
        })

    if not signals:
        return

    summary_parts = []
    if "steps" in signals:
        summary_parts.append(f"steps={signals['steps']}")
    if "sleep_hours" in signals:
        summary_parts.append(f"sleep={signals['sleep_hours']}h")
    if "stress_level" in signals:
        summary_parts.append(f"stress={signals['stress_level']}")
    if "body_battery_high" in signals:
        summary_parts.append(f"battery_high={signals['body_battery_high']}")

    event = NormalizedEvent(
        user_id=user_id,
        signals=signals,
        summary=f"Garmin sync {date_str}: " + ", ".join(summary_parts),
    )
    db.add(event)


async def run_manual_sync(user_id: int, days_back: int = 7) -> dict:
    """API-triggered manual sync. Creates a sync audit row."""
    async with AsyncSessionLocal() as db:
        run = HealthSyncRun(
            user_id=user_id,
            status="running",
            sync_type="manual",
            details_json={"days_back": days_back},
        )
        db.add(run)
        await db.flush()
        run_id = run.id

        errors: list[str] = []
        try:
            counts = await sync_user_range(db, user_id, days_back=days_back)
            status = "success"
        except Exception as exc:
            counts = {"metrics_upserted": 0, "sleep_upserted": 0, "activities_upserted": 0}
            errors.append(str(exc))
            status = "failed"

        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        run.metrics_upserted = counts["metrics_upserted"]
        run.sleep_upserted = counts["sleep_upserted"]
        run.activities_upserted = counts["activities_upserted"]
        run.error_text = "; ".join(errors)
        await db.commit()

        return {
            "run_id": run_id,
            "status": status,
            **counts,
            "errors": errors,
        }


async def run_scheduled_sync() -> None:
    """APScheduler entry point — syncs all configured users."""
    user_ids = get_connected_user_ids()
    if not user_ids:
        logger.debug("Scheduled sync: no Garmin clients configured")
        return

    logger.info("Scheduled Garmin sync starting for %d user(s)", len(user_ids))
    async with AsyncSessionLocal() as db:
        for uid in user_ids:
            real_uid = uid if uid != 0 else None
            if real_uid is None:
                continue
            try:
                counts = await sync_user_range(db, real_uid, days_back=2)
                logger.info("Scheduled sync complete user=%s: %s", real_uid, counts)
            except Exception as exc:
                logger.error("Scheduled sync failed user=%s: %s", real_uid, exc)
