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
    assert "avoid_nuts" in result["meal_constraints"]
    assert "low_prep" in result["meal_constraints"]
    assert "high_protein" in result["meal_constraints"]
    assert "light" in result["meal_constraints"]


def test_build_prompt_from_state_includes_deterministic_meal_ranking_context():
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
    assert '"derived_constraints"' in prompt
    assert '"avoid_nuts"' in prompt
    assert '"low_prep"' in prompt
