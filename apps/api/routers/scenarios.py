"""
Scenario runner — lists seeded scenarios and triggers them for a user.
"""
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from agent_runner import run_coordinator_for_run
from database import get_db
from models.events import NormalizedEvent, WearableEvent
from models.agents import AgentRun
from models.user import User
from run_dispatch import coordinator_api_base_url, coordinator_auth_header

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

SCENARIOS = [
    {
        "id": "stressed_student",
        "name": "Stressed Student",
        "description": "Finals week — minimal sleep, high stress, low activity",
        "persona_type": "student",
    },
    {
        "id": "exhausted_caregiver",
        "name": "Exhausted Caregiver",
        "description": "Caregiver burnout — sleep-deprived, high stress, completely drained",
        "persona_type": "caregiver",
    },
    {
        "id": "older_adult",
        "name": "Older Adult Routine Disruption",
        "description": "Fragmented sleep, very low steps, missed morning check-in",
        "persona_type": "older_adult",
    },
]

_SIGNAL_BUNDLES: dict[str, list[dict]] = {
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


@router.get("")
async def list_scenarios(user: User = Depends(get_current_user)):
    return SCENARIOS


class RunScenarioResponse(BaseModel):
    scenario_id: str
    normalized_event_id: int
    run_id: int


@router.post("/{scenario_id}/run", response_model=RunScenarioResponse, status_code=201)
async def run_scenario(
    scenario_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bundle = _SIGNAL_BUNDLES.get(scenario_id)
    if not bundle:
        raise HTTPException(404, f"Unknown scenario: {scenario_id}")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    signals: dict = {}

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

    summary_parts = []
    if "sleep_hours" in signals:
        summary_parts.append(f"sleep {signals['sleep_hours']}h")
    if "stress_level" in signals:
        summary_parts.append(f"stress {signals['stress_level']}/10")
    if "check_in_mood" in signals:
        summary_parts.append(f"mood: {signals['check_in_mood']}")

    norm = NormalizedEvent(
        user_id=user.id,
        signals=signals,
        summary="; ".join(summary_parts),
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
        scenario=scenario_id,
    )

    return RunScenarioResponse(scenario_id=scenario_id, normalized_event_id=norm.id, run_id=run.id)
