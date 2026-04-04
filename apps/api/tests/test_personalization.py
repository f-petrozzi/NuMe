from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    AccessibilityPreferences,
    AgentRun,
    HealthCalorieLog,
    HealthDailyMetrics,
    HealthSleepSession,
    Intervention,
    MealPlanSlot,
    NormalizedEvent,
    PersonalizationStateSnapshot,
    UserProfile,
    WearableEvent,
)


async def test_personalization_context_aggregates_sources_and_persists_snapshot(
    client: AsyncClient, db: AsyncSession
):
    profile = UserProfile(
        user_id=1,
        age_range="18-24",
        sex="female",
        goal="stress_reduction",
        activity_level="moderate",
        dietary_style="omnivore",
        allergies=["peanuts"],
        persona_type="student",
    )
    accessibility = AccessibilityPreferences(user_id=1, simplified_language=True, low_energy_mode=True)
    metric = HealthDailyMetrics(
        user_id=1,
        metric_date=date.today(),
        steps=3200,
        step_goal=8000,
        active_calories=280,
        total_calories=2100,
        resting_hr=62,
        avg_hr=78,
        body_battery_high=48,
        body_battery_low=16,
        stress_avg=6,
        active_minutes=22,
        hrv_weekly_avg=51.0,
        hrv_status="balanced",
    )
    sleep = HealthSleepSession(
        user_id=1,
        sleep_date=date.today(),
        sleep_start="2026-04-03T23:10:00Z",
        sleep_end="2026-04-04T05:20:00Z",
        duration_seconds=int(6.17 * 3600),
        sleep_score=72,
    )
    note_time = datetime.now(timezone.utc)
    mood_event = WearableEvent(
        user_id=1,
        source="manual",
        signal_type="check_in_mood",
        value="4",
        unit="1-10",
        recorded_at=note_time,
    )
    note_event = WearableEvent(
        user_id=1,
        source="manual",
        signal_type="check_in_note",
        value="Feeling overwhelmed and behind today",
        unit="",
        recorded_at=note_time,
    )
    calorie_log = HealthCalorieLog(
        user_id=1,
        log_date=date.today(),
        meal_type="lunch",
        food_name="Turkey bowl",
        calories=650,
        quantity="1 bowl",
    )
    norm = NormalizedEvent(
        user_id=1,
        signals={"stress_level": "8", "sleep_hours": "5.5", "check_in_mood": "anxious"},
        summary="sleep 5.5h; stress 8/10; mood anxious",
    )
    db.add_all([profile, accessibility, metric, sleep, mood_event, note_event, calorie_log, norm])
    await db.flush()

    run = AgentRun(user_id=1, normalized_event_id=norm.id, status="pending")
    meal_plan = MealPlanSlot(user_id=1, plan_date=date.today(), meal_type="lunch", custom_name="Turkey bowl")
    intervention = Intervention(user_id=1, run_id=None, meal_suggestion="Protein lunch", empathy_message="Start small.")
    db.add_all([run, meal_plan, intervention])
    await db.commit()
    await db.refresh(run)

    response = await client.get(f"/api/personalization/context?run_id={run.id}&scenario=live")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["snapshot_id"] is not None
    assert body["run_id"] == run.id
    assert body["persona_type"] == "student"
    assert body["profile"]["accessibility"]["simplified_language"] is True
    assert body["signals"]["stress_level"] == "8"
    assert body["signals"]["steps"] == 3200
    assert body["dynamic_state"]["sleep_debt"] >= 0
    assert "student_overload" in body["archetype_scores"]
    assert body["recent_checkins"][0]["note"] == "Feeling overwhelmed and behind today"
    assert body["calorie_summary"]["logging_days_7d"] == 1
    assert body["recipe_history"]["meal_plan_slot_count_30d"] == 1
    assert body["intervention_history"]["count_30d"] == 1

    snapshot = (
        await db.execute(
            select(PersonalizationStateSnapshot).where(PersonalizationStateSnapshot.id == body["snapshot_id"])
        )
    ).scalar_one()
    assert snapshot.run_id == run.id
    assert snapshot.user_id == 1
    assert snapshot.dynamic_state["sleep_debt"] == body["dynamic_state"]["sleep_debt"]


async def test_personalization_context_rejects_foreign_run(client: AsyncClient, db: AsyncSession):
    foreign_norm = NormalizedEvent(user_id=2, signals={"stress_level": "9"}, summary="stress 9/10")
    db.add(foreign_norm)
    await db.flush()
    foreign_run = AgentRun(user_id=2, normalized_event_id=foreign_norm.id, status="pending")
    db.add(foreign_run)
    await db.commit()
    await db.refresh(foreign_run)

    response = await client.get(f"/api/personalization/context?run_id={foreign_run.id}&scenario=live")
    assert response.status_code == 403, response.text
