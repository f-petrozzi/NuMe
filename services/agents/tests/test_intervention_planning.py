from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.agents.intervention_planning.agent import InterventionPlanningAgent


def test_fallback_meal_constraints_use_snapshot_features_not_only_raw_signals(monkeypatch):
    agent = InterventionPlanningAgent()
    monkeypatch.setattr(agent, "_generate_with_llm", lambda **_kwargs: None)
    agent._last_generation_error = "forced fallback"

    result = agent.run(
        persona_type="student",
        goal="stress_reduction",
        dietary_style="balanced",
        allergies=["peanuts"],
        resources=[],
        accessibility={"low_energy_mode": True},
        signals={"stress_level": 2, "sleep_hours": 8, "steps": 1500},
        dynamic_state={
            "prep_capacity": 0.2,
            "activity_capacity": 0.3,
            "calorie_balance": 320,
            "protein_gap": 0.45,
            "stress_load": 0.2,
            "sleep_debt": 0.1,
        },
        archetype_scores={"low_energy_recovery": 0.62},
    )

    assert result["generation_mode"] == "fallback"
    assert result["activity_template_id"] is not None
    assert result["wellness_template_id"] is not None
    assert "avoid_nuts" in result["meal_constraints"]
    assert "low_prep" in result["meal_constraints"]
    assert "high_protein" in result["meal_constraints"]
    assert "light" in result["meal_constraints"]
    assert result["why_chosen"]["meal"]
    assert result["why_chosen"]["activity"]
    assert result["why_chosen"]["wellness"]
    assert any(item["kind"] == "activity" for item in result["alternatives_considered"])
    assert any(item["kind"] == "wellness" for item in result["alternatives_considered"])


def test_build_prompt_from_state_includes_retrieve_rank_compose_context():
    agent = InterventionPlanningAgent()

    prompt = agent._build_prompt_from_state(
        {
            "persona_type": "student",
            "goal": "stress_reduction",
            "dietary_style": "balanced",
            "allergies": ["peanuts"],
            "profile": {"accessibility": {"low_energy_mode": True}},
            "resources": ["Campus counseling"],
            "signals": {"stress_level": 2, "sleep_hours": 8},
            "dynamic_state": {
                "prep_capacity": 0.2,
                "activity_capacity": 0.3,
                "calorie_balance": 320,
                "protein_gap": 0.45,
                "stress_load": 0.2,
                "sleep_debt": 0.1,
            },
            "archetype_scores": {"low_energy_recovery": 0.62},
            "signal_interpretation": {"findings": []},
            "risk_assessment": {"risk_level": "low"},
        }
    )

    assert '"meal_ranking_context"' in prompt
    assert '"selected_support_plan"' in prompt
    assert '"ranked_activity_candidates"' in prompt
    assert '"ranked_wellness_candidates"' in prompt
    assert '"derived_constraints"' in prompt
    assert '"avoid_nuts"' in prompt
    assert '"low_prep"' in prompt


def test_coerce_plan_preserves_selected_catalog_ids_and_alternatives():
    agent = InterventionPlanningAgent()
    base_plan = {
        "meal_suggestion": {
            "title": "Hydration Citrus Oats",
            "description": "Soft oats with fruit and chia for recovery after poor sleep or elevated stress.",
            "rationale": "Supports recovery after lighter sleep.",
        },
        "activity_suggestion": {
            "title": "Ten-Minute Reset Walk",
            "description": "A short walk that lowers pressure and helps reset attention without turning the day into a workout.",
            "duration_minutes": 10,
            "intensity": "low",
            "rationale": "Keeps intensity manageable for the current strain level.",
        },
        "wellness_action": {
            "title": "Two-Minute Grounding Reset",
            "description": "A quick sensory grounding exercise for calming the nervous system when the day feels heavy.",
            "rationale": "Directly addresses elevated stress load.",
        },
        "recipe_id": None,
        "activity_template_id": 1,
        "wellness_template_id": 1,
        "resources": ["Campus counseling"],
        "notes": "Retrieve-rank-compose picked the strongest fit.",
        "meal_constraints": ["hydration_support", "high_protein"],
        "why_chosen": {
            "meal": ["Supports recovery after lighter sleep."],
            "activity": ["Keeps intensity manageable for the current strain level."],
            "wellness": ["Directly addresses elevated stress load."],
        },
        "alternatives_considered": [{"kind": "activity", "template_id": 2, "title": "Seated Mobility Reset", "rank": 2}],
        "why_changed_from_previous": ["Activity changed to better match today's capacity and recovery signals."],
    }

    result = agent._coerce_plan(
        {
            "meal_suggestion": {
                "title": "Different Title",
                "description": "LLM-adapted meal copy.",
                "rationale": "LLM meal rationale.",
            },
            "activity_suggestion": {
                "title": "Different Activity",
                "description": "LLM-adapted activity copy.",
                "duration_minutes": 30,
                "intensity": "moderate",
                "rationale": "LLM activity rationale.",
            },
            "wellness_action": {
                "title": "Different Wellness",
                "description": "LLM-adapted wellness copy.",
                "rationale": "LLM wellness rationale.",
            },
            "why_chosen": {
                "activity": ["LLM added context."],
            },
            "resources": ["Campus counseling", "Advising office"],
            "notes": "LLM notes.",
        },
        base_plan=base_plan,
        resources=["Campus counseling"],
        persona_type="student",
    )

    assert result["generation_mode"] == "llm"
    assert result["activity_template_id"] == 1
    assert result["wellness_template_id"] == 1
    assert result["activity_suggestion"]["title"] == "Ten-Minute Reset Walk"
    assert result["activity_suggestion"]["duration_minutes"] == 10
    assert result["activity_suggestion"]["intensity"] == "low"
    assert result["alternatives_considered"] == base_plan["alternatives_considered"]
    assert "LLM added context." in result["why_chosen"]["activity"]
