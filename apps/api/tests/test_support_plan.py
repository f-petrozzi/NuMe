from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    ActivityTemplate,
    AgentRun,
    Intervention,
    NormalizedEvent,
    PersonalizationStateSnapshot,
    Recipe,
    SupportPlanFeedbackEvent,
    WellnessTemplate,
)


async def test_get_current_support_plan_returns_structured_payload(
    client: AsyncClient,
    db: AsyncSession,
):
    norm = NormalizedEvent(
        user_id=1,
        signals={"sleep_hours": "4.8", "stress_level": "8", "check_in_mood": "3"},
        summary="sleep 4.8h; stress 8/10; mood: worried",
    )
    db.add(norm)
    await db.flush()

    run = AgentRun(user_id=1, normalized_event_id=norm.id, status="completed", risk_level="moderate")
    db.add(run)
    await db.flush()

    snapshot = PersonalizationStateSnapshot(
        user_id=1,
        run_id=run.id,
        source="live_checkin",
        profile_static={
            "persona_type": "student",
            "goal": "stress_reduction",
            "accessibility": {"low_energy_mode": True},
        },
        dynamic_state={
            "sleep_debt": 0.61,
            "stress_load": 0.78,
            "recovery_score": 0.32,
            "prep_capacity": 0.28,
            "routine_stability": 0.41,
        },
        archetype_scores={"student_overload": 0.81, "low_energy_recovery": 0.73},
        feature_windows={
            "sleep": {"7d": {"sleep_hours_avg": 5.1, "sample_count": 7}},
            "metrics": {"7d": {"stress_avg": 74, "sample_count": 7}},
        },
        inputs_summary={
            "recent_checkins": [
                {"mood": "3", "mood_score": 0.22, "note": "Overwhelmed today", "note_sentiment": -0.66}
            ]
        },
    )
    recipe = Recipe(
        user_id=1,
        title="Turkey and Rice Bowl",
        description="High-protein, low-prep lunch",
        prep_minutes=10,
        cook_minutes=15,
        calories=420,
        protein_grams=32.0,
        prep_effort="low",
        cost_level="medium",
        tags=["high_protein", "low_prep"],
        equipment_tags=["microwave"],
    )
    activity_template = ActivityTemplate(
        id=5,
        title="Ten-Minute Reset Walk",
        description="A short, low-pressure walk that supports recovery.",
        duration_minutes=10,
        intensity="low",
        accessibility_tags=["low_energy_friendly"],
        equipment_tags=[],
        time_cost_level="low",
        fatigue_sensitivity="high",
        contraindication_tags=[],
        metadata_json={"goal_tags": ["stress_reduction"]},
        active=True,
    )
    wellness_template = WellnessTemplate(
        id=11,
        title="Two-Minute Grounding Reset",
        description="A quick grounding prompt to settle the nervous system.",
        category="grounding",
        duration_minutes=2,
        accessibility_tags=["low_energy_friendly"],
        time_cost_level="low",
        fatigue_sensitivity="high",
        metadata_json={"goal_tags": ["stress_reduction"]},
        active=True,
    )
    db.add_all([snapshot, recipe, activity_template, wellness_template])
    await db.flush()

    intervention = Intervention(
        user_id=1,
        run_id=run.id,
        state_snapshot_id=snapshot.id,
        recipe_id=recipe.id,
        activity_template_id=activity_template.id,
        wellness_template_id=wellness_template.id,
        meal_suggestion="Turkey and Rice Bowl for steady energy.",
        activity_suggestion="Ten-Minute Reset Walk between classes.",
        wellness_action="Two-Minute Grounding Reset before dinner.",
        empathy_message="Today looks heavier than usual, so the plan stays deliberately low-friction.",
        meal_constraints=["high_protein", "low_prep"],
        risk_subscores={"physiological_strain": 0.71, "recovery_debt": 0.78},
        why_chosen={
            "meal": ["Fits current prep capacity", "Improves protein coverage without high effort"],
            "activity": ["Keeps intensity manageable for the current strain level"],
            "wellness": ["Directly addresses elevated stress load"],
        },
        alternatives_considered=[
            {"kind": "meal", "recipe_id": 17, "title": "Protein Oats", "rank": 2},
            {"kind": "activity", "template_id": 8, "title": "Seated Mobility Reset", "rank": 2},
            {"kind": "wellness", "template_id": 14, "title": "Breathing Ladder", "rank": 2},
        ],
        why_changed_from_previous=["Recovery score fell compared with yesterday"],
    )
    db.add(intervention)
    await db.commit()

    resp = await client.get("/api/support-plan/current")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["run"]["id"] == run.id
    assert body["state_snapshot"]["id"] == snapshot.id
    assert body["risk"]["level"] == "moderate"
    assert body["risk"]["subscores"] == {"physiological_strain": 0.71, "recovery_debt": 0.78}
    assert body["risk"]["drivers"]
    assert body["plan"]["meal"]["recipe_id"] == recipe.id
    assert body["plan"]["meal"]["recipe"]["title"] == "Turkey and Rice Bowl"
    assert body["plan"]["meal"]["why_chosen"] == [
        "Fits current prep capacity",
        "Improves protein coverage without high effort",
    ]
    assert body["plan"]["meal"]["alternatives_considered"][0]["kind"] == "meal"
    assert body["plan"]["activity"]["template"]["title"] == "Ten-Minute Reset Walk"
    assert body["plan"]["activity"]["alternatives_considered"][0]["kind"] == "activity"
    assert body["plan"]["wellness"]["template"]["title"] == "Two-Minute Grounding Reset"
    assert body["plan"]["why_changed_from_previous"] == ["Recovery score fell compared with yesterday"]


async def test_get_current_support_plan_falls_back_to_legacy_text_fields(
    client: AsyncClient,
    db: AsyncSession,
):
    run = AgentRun(user_id=1, normalized_event_id=None, status="completed", risk_level="low")
    db.add(run)
    await db.flush()

    intervention = Intervention(
        user_id=1,
        run_id=run.id,
        meal_suggestion="Easy protein-rich breakfast",
        activity_suggestion="10-minute outside walk",
        wellness_action="Block a short recovery window tonight",
        empathy_message="Start with one manageable step today.",
        alternatives_considered=[17, 23],
    )
    db.add(intervention)
    await db.commit()

    resp = await client.get("/api/support-plan/current")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["plan"]["meal"]["title"] == "Meal Suggestion"
    assert body["plan"]["meal"]["description"] == "Easy protein-rich breakfast"
    assert body["plan"]["meal"]["recipe"] is None
    assert body["plan"]["meal"]["alternatives_considered"] == [17, 23]
    assert body["plan"]["activity"]["title"] == "Activity Suggestion"
    assert body["plan"]["activity"]["description"] == "10-minute outside walk"
    assert body["plan"]["wellness"]["title"] == "Wellness Action"
    assert body["plan"]["wellness"]["description"] == "Block a short recovery window tonight"


async def test_get_current_support_plan_returns_empty_state_when_no_intervention_exists(
    client: AsyncClient,
):
    resp = await client.get("/api/support-plan/current")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["plan"] is None
    assert body["run"] is None
    assert body["state_snapshot"] is None
    assert body["risk"]["level"] == "low"
    assert body["risk"]["rationale"] == "No support plan has been generated for this member yet."


async def test_create_support_plan_feedback_event_persists_intervention_context(
    client: AsyncClient,
    db: AsyncSession,
):
    run = AgentRun(user_id=1, normalized_event_id=None, status="completed", risk_level="low")
    db.add(run)
    await db.flush()

    intervention = Intervention(
        user_id=1,
        run_id=run.id,
        meal_suggestion="Turkey and Rice Bowl for steady energy.",
        activity_suggestion="Ten-Minute Reset Walk between classes.",
        wellness_action="Two-Minute Grounding Reset before dinner.",
        empathy_message="Keep the plan low-friction today.",
    )
    db.add(intervention)
    await db.commit()

    resp = await client.post(
        "/api/support-plan/feedback",
        json={
            "intervention_id": intervention.id,
            "event_type": "accepted",
            "source": "member_dashboard",
            "recommendation_kind": "meal",
            "recommendation_id": 88,
            "payload": {
                "recommendation_title": "Turkey and Rice Bowl",
                "support_plan_generated_at": "2026-04-05T12:00:00Z",
            },
        },
    )
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["user_id"] == 1
    assert body["run_id"] == run.id
    assert body["intervention_id"] == intervention.id
    assert body["event_type"] == "accepted"
    assert body["payload"]["source"] == "member_dashboard"
    assert body["payload"]["recommendation_kind"] == "meal"
    assert body["payload"]["recommendation_id"] == 88
    assert body["payload"]["recommendation_title"] == "Turkey and Rice Bowl"

    event = (
        await db.execute(
            select(SupportPlanFeedbackEvent).where(SupportPlanFeedbackEvent.id == body["id"])
        )
    ).scalar_one()
    assert event.user_id == 1
    assert event.run_id == run.id
    assert event.intervention_id == intervention.id
    assert event.payload["source"] == "member_dashboard"


async def test_create_support_plan_feedback_event_rejects_foreign_intervention(
    client: AsyncClient,
    db: AsyncSession,
):
    intervention = Intervention(
        user_id=2,
        meal_suggestion="Foreign plan",
        activity_suggestion="Foreign activity",
        wellness_action="Foreign wellness",
        empathy_message="Not your plan.",
    )
    db.add(intervention)
    await db.commit()

    resp = await client.post(
        "/api/support-plan/feedback",
        json={
            "intervention_id": intervention.id,
            "event_type": "viewed",
            "source": "recipe_list_recommended",
            "recommendation_kind": "recipe",
            "recommendation_id": 101,
            "payload": {"recipe_title": "Foreign Recipe"},
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == "Support plan intervention not found"
