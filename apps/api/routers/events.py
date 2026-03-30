"""
Event ingestion and wearable simulator.
POST /api/events/ingest   — accepts a single signal event (raw; no normalization)
POST /api/events/checkin  — atomic: ingest check-in bundle + normalize + create run
POST /api/events/simulate — generates a realistic bundle for a named scenario
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_runner import run_coordinator_for_run
from auth import get_current_user
from database import get_db
from models.agents import AgentRun
from models.events import BehaviorEvent, NormalizedEvent, WearableEvent
from models.user import User
from run_dispatch import coordinator_api_base_url, coordinator_auth_header
from schemas.agents import AgentRunOut
from schemas.events import CheckInRequest, IngestEventRequest, NormalizedEventOut, SimulateRequest, WearableEventOut

router = APIRouter(prefix="/api/events", tags=["events"])

# ---------------------------------------------------------------------------
# Scenario bundles for the simulator
# ---------------------------------------------------------------------------

_SCENARIOS: dict[str, list[dict]] = {
    "stressed_student": [
        {"signal_type": "sleep_hours", "value": "4.5", "unit": "hours"},
        {"signal_type": "sleep_quality", "value": "2", "unit": "1-10"},
        {"signal_type": "stress_level", "value": "8", "unit": "1-10"},
        {"signal_type": "steps", "value": "800", "unit": "steps"},
        {"signal_type": "check_in_mood", "value": "anxious", "unit": ""},
        {"signal_type": "check_in_note", "value": "Finals week, haven't slept properly in days", "unit": ""},
    ],
    "exhausted_caregiver": [
        {"signal_type": "sleep_hours", "value": "5", "unit": "hours"},
        {"signal_type": "sleep_quality", "value": "3", "unit": "1-10"},
        {"signal_type": "stress_level", "value": "9", "unit": "1-10"},
        {"signal_type": "activity_level", "value": "1", "unit": "1-10"},
        {"signal_type": "check_in_mood", "value": "exhausted", "unit": ""},
        {"signal_type": "check_in_note", "value": "completely drained, been caring for mom all week", "unit": ""},
    ],
    "older_adult": [
        {"signal_type": "steps", "value": "1200", "unit": "steps"},
        {"signal_type": "sleep_hours", "value": "5.5", "unit": "hours"},
        {"signal_type": "sleep_quality", "value": "4", "unit": "1-10"},
        {"signal_type": "heart_rate", "value": "88", "unit": "bpm"},
        {"signal_type": "check_in_mood", "value": "confused", "unit": ""},
        {"signal_type": "check_in_note", "value": "Missed morning routine, joints aching", "unit": ""},
    ],
}


def _build_summary(signals: dict[str, Any]) -> str:
    parts = []
    if "sleep_hours" in signals:
        parts.append(f"sleep {signals['sleep_hours']}h")
    if "stress_level" in signals:
        parts.append(f"stress {signals['stress_level']}/10")
    if "steps" in signals:
        parts.append(f"{signals['steps']} steps")
    if "check_in_mood" in signals:
        parts.append(f"mood: {signals['check_in_mood']}")
    return "; ".join(parts) if parts else "health check-in"


@router.get("/recent", response_model=List[WearableEventOut])
async def recent_events(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the N most recent wearable events for this user. Used by get_recent_signals_tool."""
    result = await db.execute(
        select(WearableEvent)
        .where(WearableEvent.user_id == user.id)
        .order_by(WearableEvent.recorded_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/ingest", response_model=WearableEventOut, status_code=201)
async def ingest_event(
    body: IngestEventRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = body.recorded_at or datetime.now(timezone.utc)
    event = WearableEvent(
        user_id=user.id,
        source=body.source,
        signal_type=body.signal_type,
        value=body.value,
        unit=body.unit,
        recorded_at=now,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.post("/checkin", response_model=AgentRunOut, status_code=201)
async def checkin(
    body: CheckInRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Atomic check-in: create raw wearable events, normalize them into a bundle,
    create an agent run linked to that bundle, and enqueue the coordinator.
    Returns the AgentRun so the frontend can navigate directly to the trace.
    """
    now = datetime.now(timezone.utc)
    signals: dict[str, Any] = {}

    # Convert frontend stress (0-100) to 1-10 scale
    stress_1_10 = max(1, min(10, round(body.stress / 10))) or 1

    raw_events = [
        {"signal_type": "check_in_mood", "value": str(body.mood), "unit": "1-10"},
        {"signal_type": "sleep_hours", "value": str(body.sleep_hours), "unit": "hours"},
        {"signal_type": "stress_level", "value": str(stress_1_10), "unit": "1-10"},
    ]
    if body.note.strip():
        raw_events.append({"signal_type": "check_in_note", "value": body.note.strip(), "unit": ""})

    for sig in raw_events:
        event = WearableEvent(
            user_id=user.id,
            source="manual",
            signal_type=sig["signal_type"],
            value=sig["value"],
            unit=sig["unit"],
            recorded_at=now,
        )
        db.add(event)
        signals[sig["signal_type"]] = sig["value"]

    norm = NormalizedEvent(
        user_id=user.id,
        signals=signals,
        summary=_build_summary(signals),
    )
    db.add(norm)
    await db.flush()

    run = AgentRun(
        user_id=user.id,
        normalized_event_id=norm.id,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(
        run_coordinator_for_run,
        user_id=user.id,
        run_id=run.id,
        auth_header=coordinator_auth_header(request),
        api_base_url=coordinator_api_base_url(request),
        demo_as=request.headers.get("x-demo-as", ""),
        scenario="live",
    )
    return run


@router.post("/simulate", response_model=NormalizedEventOut, status_code=201)
async def simulate(
    body: SimulateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bundle = _SCENARIOS.get(body.scenario)
    if not bundle:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{body.scenario}'. Available: {list(_SCENARIOS)}",
        )

    now = datetime.now(timezone.utc)
    signals: dict[str, Any] = {}

    for sig in bundle:
        event = WearableEvent(
            user_id=user.id,
            source="simulated",
            signal_type=sig["signal_type"],
            value=sig["value"],
            unit=sig["unit"],
            recorded_at=now,
        )
        db.add(event)
        signals[sig["signal_type"]] = sig["value"]

    norm = NormalizedEvent(
        user_id=user.id,
        signals=signals,
        summary=_build_summary(signals),
    )
    db.add(norm)
    await db.commit()
    await db.refresh(norm)
    return norm
