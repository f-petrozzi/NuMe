"""
Agent run management.
POST /api/runs/trigger — create a run record (agents pick it up via ADK)
GET  /api/runs/:id     — full trace with messages
GET  /api/runs         — list runs for current user
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, is_admin
from agent_runner import run_coordinator_for_run
from database import get_db
from models.agents import AgentMessage, AgentRun, Case, Intervention
from models.events import NormalizedEvent
from models.user import User, UserProfile
from run_dispatch import coordinator_api_base_url, coordinator_auth_header
from schemas.agents import AgentMessageOut, AgentRunOut, RunTraceOut, TriggerRunRequest


class RunUpdate(BaseModel):
    status: Optional[str] = None        # pending|running|completed|failed
    risk_level: Optional[str] = None
    completed_at: Optional[datetime] = None


class AgentMessageCreate(BaseModel):
    run_id: int
    agent_name: str
    agent_type: str = "local"           # local|a2a|parallel|loop
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    iteration: int = 0
    duration_ms: Optional[int] = None

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _member_label(email: str | None, user_id: int) -> str:
    if not email:
        return f"Member #{user_id}"

    local_part = email.split("@")[0].strip()
    cleaned = re.sub(r"[._+-]+", " ", local_part)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() or f"Member #{user_id}"


def _serialize_run(
    run: AgentRun,
    *,
    member_email: str | None,
    persona_type: str | None,
    summary: str | None,
) -> AgentRunOut:
    return AgentRunOut.model_validate(
        {
            "id": run.id,
            "user_id": run.user_id,
            "normalized_event_id": run.normalized_event_id,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "risk_level": run.risk_level,
            "member_label": _member_label(member_email, run.user_id),
            "member_email": member_email,
            "persona_type": persona_type,
            "summary": summary.strip() if summary else None,
        }
    )


def _serialize_case(
    case: Case,
    *,
    member_email: str | None,
    persona_type: str | None,
    summary: str | None,
):
    return {
        "id": case.id,
        "user_id": case.user_id,
        "run_id": case.run_id,
        "risk_level": case.risk_level,
        "status": case.status,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "member_label": _member_label(member_email, case.user_id),
        "member_email": member_email,
        "persona_type": persona_type,
        "summary": summary.strip() if summary else f"{case.risk_level.title()} risk follow-up case.",
    }


@router.post("/trigger", response_model=AgentRunOut, status_code=201)
async def trigger_run(
    body: TriggerRunRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.normalized_event_id is None:
        raise HTTPException(
            status_code=422,
            detail="normalized_event_id is required. Use POST /api/events/checkin for check-ins "
                   "or POST /api/scenarios/{id}/run for seeded scenarios.",
        )

    # Validate the normalized event exists and belongs to this user
    ne_result = await db.execute(
        select(NormalizedEvent).where(
            NormalizedEvent.id == body.normalized_event_id,
            NormalizedEvent.user_id == user.id,
        )
    )
    if not ne_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Normalized event not found")

    run = AgentRun(
        user_id=user.id,
        normalized_event_id=body.normalized_event_id,
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


@router.get("", response_model=List[AgentRunOut])
async def list_runs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AgentRun, User.email, UserProfile.persona_type, NormalizedEvent.summary)
        .join(User, User.id == AgentRun.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == AgentRun.user_id)
        .outerjoin(NormalizedEvent, NormalizedEvent.id == AgentRun.normalized_event_id)
        .order_by(AgentRun.started_at.desc())
        .limit(50)
    )
    if not is_admin(user):
        query = query.where(AgentRun.user_id == user.id)

    result = await db.execute(query)
    return [
        _serialize_run(run, member_email=email, persona_type=persona_type, summary=summary)
        for run, email, persona_type, summary in result.all()
    ]


@router.put("/{run_id}", response_model=AgentRunOut)
async def update_run(
    run_id: int,
    body: RunUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user.id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if body.status is not None:
        run.status = body.status
    if body.risk_level is not None:
        run.risk_level = body.risk_level
    if body.completed_at is not None:
        run.completed_at = body.completed_at
    elif body.status in ("completed", "failed"):
        run.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/messages", response_model=AgentMessageOut, status_code=201)
async def create_agent_message(
    body: AgentMessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    msg = AgentMessage(
        run_id=body.run_id,
        agent_name=body.agent_name,
        agent_type=body.agent_type,
        input=body.input,
        output=body.output,
        iteration=body.iteration,
        duration_ms=body.duration_ms,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.get("/{run_id}", response_model=RunTraceOut)
async def get_run_trace(
    run_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run_query = (
        select(AgentRun, User.email, UserProfile.persona_type, NormalizedEvent.summary)
        .join(User, User.id == AgentRun.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == AgentRun.user_id)
        .outerjoin(NormalizedEvent, NormalizedEvent.id == AgentRun.normalized_event_id)
        .where(AgentRun.id == run_id)
    )
    if not is_admin(user):
        run_query = run_query.where(AgentRun.user_id == user.id)

    run_result = await db.execute(run_query)
    row = run_result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    run, member_email, persona_type, summary = row

    msgs_result = await db.execute(
        select(AgentMessage).where(AgentMessage.run_id == run_id).order_by(AgentMessage.created_at)
    )
    messages = msgs_result.scalars().all()

    intervention_result = await db.execute(
        select(Intervention).where(Intervention.run_id == run_id).order_by(Intervention.created_at.desc()).limit(1)
    )
    intervention = intervention_result.scalar_one_or_none()

    case_result = await db.execute(
        select(Case).where(Case.run_id == run_id).order_by(Case.created_at.desc()).limit(1)
    )
    case = case_result.scalar_one_or_none()

    return RunTraceOut(
        run=_serialize_run(run, member_email=member_email, persona_type=persona_type, summary=summary),
        messages=messages,
        intervention=intervention,
        case=(
            _serialize_case(case, member_email=member_email, persona_type=persona_type, summary=summary)
            if case is not None
            else None
        ),
    )
