"""
Tests for the event-ingest → normalize → run pipeline.

Covers:
- POST /api/events/checkin  (atomic check-in flow)
- POST /api/events/simulate (scenario simulator)
- POST /api/runs/trigger    (explicit trigger; must supply normalized_event_id)
- POST /api/scenarios/{id}/run (scenario runner)
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import AgentMessage, AgentRun, Case, Intervention, NormalizedEvent, User, UserProfile, WearableEvent


# ---------------------------------------------------------------------------
# POST /api/events/checkin
# ---------------------------------------------------------------------------

async def test_checkin_creates_normalized_event_and_run(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/events/checkin", json={
        "mood": 6,
        "sleep_hours": 6.5,
        "stress": 70,
        "note": "Feeling a bit off today",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # Response is an AgentRun
    assert body["status"] == "pending"
    assert body["normalized_event_id"] is not None
    run_id = body["id"]
    norm_id = body["normalized_event_id"]

    # Wearable events persisted (mood, sleep_hours, stress_level, check_in_note = 4)
    events = (await db.execute(
        select(WearableEvent).where(WearableEvent.user_id == 1)
    )).scalars().all()
    signal_types = {e.signal_type for e in events}
    assert "sleep_hours" in signal_types
    assert "stress_level" in signal_types
    assert "check_in_mood" in signal_types
    assert "check_in_note" in signal_types

    # NormalizedEvent row exists and belongs to user
    norm = (await db.execute(
        select(NormalizedEvent).where(NormalizedEvent.id == norm_id)
    )).scalar_one()
    assert norm.user_id == 1
    assert "sleep_hours" in norm.signals
    assert "stress_level" in norm.signals

    # AgentRun linked to the normalized event
    run = (await db.execute(
        select(AgentRun).where(AgentRun.id == run_id)
    )).scalar_one()
    assert run.normalized_event_id == norm_id
    assert run.user_id == 1


async def test_checkin_stress_converted_to_1_10(client: AsyncClient, db: AsyncSession):
    """Frontend sends stress 0-100; backend must store it as 1-10."""
    await client.post("/api/events/checkin", json={
        "mood": 5,
        "sleep_hours": 7.0,
        "stress": 80,  # 80% → 8/10
        "note": "",
    })
    events = (await db.execute(
        select(WearableEvent).where(
            WearableEvent.user_id == 1,
            WearableEvent.signal_type == "stress_level",
        )
    )).scalars().all()
    assert len(events) >= 1
    assert events[-1].value == "8"


async def test_checkin_without_note_omits_checkin_note_event(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/events/checkin", json={
        "mood": 7,
        "sleep_hours": 8.0,
        "stress": 30,
        "note": "",  # blank — should not create a check_in_note event
    })
    assert resp.status_code == 201
    events = (await db.execute(
        select(WearableEvent).where(
            WearableEvent.user_id == 1,
            WearableEvent.signal_type == "check_in_note",
        )
    )).scalars().all()
    assert len(events) == 0


# ---------------------------------------------------------------------------
# POST /api/events/simulate
# ---------------------------------------------------------------------------

async def test_simulate_creates_normalized_event(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/events/simulate", json={"scenario": "stressed_student"})
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["user_id"] == 1
    assert "sleep_hours" in body["signals"]
    assert "stress_level" in body["signals"]

    # Wearable events also created
    events = (await db.execute(
        select(WearableEvent).where(
            WearableEvent.user_id == 1,
            WearableEvent.source == "simulated",
        )
    )).scalars().all()
    assert len(events) >= 4


async def test_simulate_unknown_scenario_returns_400(client: AsyncClient):
    resp = await client.post("/api/events/simulate", json={"scenario": "nonexistent"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/runs/trigger
# ---------------------------------------------------------------------------

async def test_trigger_without_normalized_event_id_returns_422(client: AsyncClient):
    resp = await client.post("/api/runs/trigger", json={})
    assert resp.status_code == 422


async def test_trigger_with_null_normalized_event_id_returns_422(client: AsyncClient):
    resp = await client.post("/api/runs/trigger", json={"normalized_event_id": None})
    assert resp.status_code == 422


async def test_trigger_with_foreign_normalized_event_id_returns_404(
    client: AsyncClient, db: AsyncSession
):
    """A normalized event owned by a different user (id=2) must be rejected."""
    # Create a NormalizedEvent for user 2 directly in the DB
    foreign_norm = NormalizedEvent(
        user_id=2,  # different from the test user (id=1)
        signals={"stress_level": "8"},
        summary="stress 8/10",
    )
    db.add(foreign_norm)
    await db.commit()
    await db.refresh(foreign_norm)

    resp = await client.post("/api/runs/trigger", json={"normalized_event_id": foreign_norm.id})
    assert resp.status_code == 404


async def test_trigger_with_valid_normalized_event_id_creates_run(
    client: AsyncClient, db: AsyncSession
):
    # First, simulate to get a normalized event belonging to user 1
    sim_resp = await client.post("/api/events/simulate", json={"scenario": "stressed_student"})
    norm_id = sim_resp.json()["id"]

    trigger_resp = await client.post("/api/runs/trigger", json={"normalized_event_id": norm_id})
    assert trigger_resp.status_code == 201, trigger_resp.text
    body = trigger_resp.json()
    assert body["normalized_event_id"] == norm_id
    assert body["status"] == "pending"
    assert body["user_id"] == 1


# ---------------------------------------------------------------------------
# POST /api/scenarios/{id}/run
# ---------------------------------------------------------------------------

async def test_scenario_run_creates_all_records(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/scenarios/stressed_student/run")
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["scenario_id"] == "stressed_student"
    assert body["normalized_event_id"] is not None
    assert body["run_id"] is not None

    # AgentRun linked to normalized event
    run = (await db.execute(
        select(AgentRun).where(AgentRun.id == body["run_id"])
    )).scalar_one()
    assert run.normalized_event_id == body["normalized_event_id"]
    assert run.user_id == 1


async def test_scenario_run_unknown_scenario_returns_404(client: AsyncClient):
    resp = await client.post("/api/scenarios/unknown_scenario/run")
    assert resp.status_code == 404


async def test_admin_can_run_scenario_without_profile(admin_client: AsyncClient, db: AsyncSession):
    """Admin user (no profile) should be able to trigger a scenario without crashing."""
    resp = await admin_client.post("/api/scenarios/stressed_student/run")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["run_id"] is not None

    run = (await db.execute(
        select(AgentRun).where(AgentRun.id == body["run_id"])
    )).scalar_one()
    # Run is created under the admin's user_id (99)
    assert run.user_id == 99


async def test_member_intervention_creation_uses_run_owner_for_support_plan(
    client: AsyncClient, db: AsyncSession
):
    norm = NormalizedEvent(user_id=1, signals={"stress_level": "8"}, summary="stress 8/10")
    db.add(norm)
    await db.flush()

    run = AgentRun(user_id=1, normalized_event_id=norm.id, status="completed", risk_level="moderate")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    create_resp = await client.post(
        "/api/interventions",
        json={
            "user_id": 2,
            "run_id": run.id,
            "meal_suggestion": "Protein-forward breakfast",
            "activity_suggestion": "10-minute walk",
            "wellness_action": "Block 5 quiet minutes",
            "empathy_message": "Start small today.",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["user_id"] == 1
    assert created["run_id"] == run.id

    list_resp = await client.get("/api/interventions")
    assert list_resp.status_code == 200, list_resp.text
    interventions = list_resp.json()
    assert len(interventions) == 1
    assert interventions[0]["user_id"] == 1
    assert interventions[0]["run_id"] == run.id
    assert interventions[0]["meal_suggestion"] == "Protein-forward breakfast"

    persisted = (await db.execute(select(Intervention).where(Intervention.id == created["id"]))).scalar_one()
    assert persisted.user_id == 1


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}  — trace access control
# ---------------------------------------------------------------------------

async def test_get_run_trace_own_run(client: AsyncClient, db: AsyncSession):
    """User can view their own run trace."""
    create_resp = await client.post("/api/scenarios/stressed_student/run")
    run_id = create_resp.json()["run_id"]

    trace_resp = await client.get(f"/api/runs/{run_id}")
    assert trace_resp.status_code == 200
    assert trace_resp.json()["run"]["id"] == run_id


async def test_get_run_trace_foreign_run_returns_404(client: AsyncClient, db: AsyncSession):
    """User cannot view another user's run trace."""
    # Create a run for user 2 directly
    norm = NormalizedEvent(user_id=2, signals={}, summary="")
    db.add(norm)
    await db.flush()
    foreign_run = AgentRun(user_id=2, normalized_event_id=norm.id, status="completed")
    db.add(foreign_run)
    await db.commit()
    await db.refresh(foreign_run)

    resp = await client.get(f"/api/runs/{foreign_run.id}")
    assert resp.status_code == 404


async def test_admin_can_list_and_get_member_runs(admin_client: AsyncClient, db: AsyncSession):
    member = User(id=2, email="student.member@example.com", role="member")
    profile = UserProfile(
        user_id=2,
        age_range="18-24",
        sex="female",
        goal="stress_reduction",
        activity_level="low",
        dietary_style="omnivore",
        allergies=[],
        persona_type="student",
    )
    norm = NormalizedEvent(
        user_id=2,
        signals={"sleep_hours": "4.5", "stress_level": "8"},
        summary="sleep 4.5h; stress 8/10; mood: anxious",
    )
    db.add(member)
    await db.flush()
    db.add_all([profile, norm])
    await db.flush()

    run = AgentRun(user_id=2, normalized_event_id=norm.id, status="completed", risk_level="high")
    db.add(run)
    await db.flush()

    db.add(
        AgentMessage(
            run_id=run.id,
            agent_name="RiskStratification",
            agent_type="parallel",
            input={},
            output={"summary": "High risk due to sustained sleep deprivation."},
        )
    )
    db.add(
        Intervention(
            user_id=2,
            run_id=run.id,
            meal_suggestion="Easy protein-rich breakfast",
            activity_suggestion="10-minute outside walk",
            wellness_action="Block a short recovery window tonight",
            empathy_message="You have been stretched thin. Start with one manageable step today.",
        )
    )
    db.add(Case(user_id=2, run_id=run.id, risk_level="high", status="open"))
    await db.commit()

    runs_resp = await admin_client.get("/api/runs")
    assert runs_resp.status_code == 200, runs_resp.text
    runs = runs_resp.json()
    listed = next(item for item in runs if item["id"] == run.id)
    assert listed["user_id"] == 2
    assert listed["member_label"] == "Student Member"
    assert listed["persona_type"] == "student"
    assert listed["summary"] == "sleep 4.5h; stress 8/10; mood: anxious"

    trace_resp = await admin_client.get(f"/api/runs/{run.id}")
    assert trace_resp.status_code == 200, trace_resp.text
    trace = trace_resp.json()
    assert trace["run"]["id"] == run.id
    assert trace["run"]["member_email"] == "student.member@example.com"
    assert trace["intervention"]["meal_suggestion"] == "Easy protein-rich breakfast"
    assert trace["case"]["risk_level"] == "high"


async def test_coordinator_case_payload_includes_member_context(
    coordinator_client: AsyncClient,
    db: AsyncSession,
):
    member = User(id=7, email="care.giver@example.com", role="member")
    profile = UserProfile(
        user_id=7,
        age_range="35-44",
        sex="female",
        goal="burnout_recovery",
        activity_level="low",
        dietary_style="omnivore",
        allergies=[],
        persona_type="caregiver",
    )
    norm = NormalizedEvent(
        user_id=7,
        signals={"sleep_hours": "5", "stress_level": "9"},
        summary="sleep 5h; stress 9/10; mood: exhausted",
    )
    db.add(member)
    await db.flush()
    db.add_all([profile, norm])
    await db.flush()

    run = AgentRun(user_id=7, normalized_event_id=norm.id, status="completed", risk_level="high")
    db.add(run)
    await db.flush()

    case = Case(user_id=7, run_id=run.id, risk_level="high", status="open")
    db.add(case)
    await db.commit()

    list_resp = await coordinator_client.get("/api/cases")
    assert list_resp.status_code == 200, list_resp.text
    payload = next(item for item in list_resp.json() if item["id"] == case.id)
    assert payload["member_label"] == "Care Giver"
    assert payload["member_email"] == "care.giver@example.com"
    assert payload["persona_type"] == "caregiver"
    assert payload["summary"] == "sleep 5h; stress 9/10; mood: exhausted"

    detail_resp = await coordinator_client.get(f"/api/cases/{case.id}")
    assert detail_resp.status_code == 200, detail_resp.text
    assert detail_resp.json()["member_label"] == "Care Giver"
