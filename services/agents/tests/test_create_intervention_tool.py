from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.tools import create_intervention_tool


def test_create_intervention_tool_forwards_snapshot_and_structured_fields(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_api_request(**kwargs):
        captured.update(kwargs)
        return {"id": 42}

    monkeypatch.setattr(create_intervention_tool, "api_request", _fake_api_request)

    response = create_intervention_tool.create_intervention(
        user_id=11,
        run_id=16,
        state_snapshot_id=101,
        recipe_id=7,
        activity_template_id=3,
        wellness_template_id=4,
        meal_suggestion="Protein-forward meal",
        activity_suggestion="Gentle walk",
        wellness_action="Breathing reset",
        empathy_message="Take this one step at a time.",
        meal_constraints=["high_protein", "low_prep"],
        risk_subscores={"physiological_strain": 0.9},
        why_chosen={"meal": "best fit"},
        alternatives_considered=[{"meal": "backup"}],
        why_changed_from_previous=["Higher stress today."],
        api_base_url="http://api.test",
        auth_header="Bearer token",
    )

    assert response == {"id": 42}
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/interventions"
    assert captured["api_base_url"] == "http://api.test"
    assert captured["auth_header"] == "Bearer token"

    payload = captured["json_payload"]
    assert payload["user_id"] == 11
    assert payload["run_id"] == 16
    assert payload["state_snapshot_id"] == 101
    assert payload["recipe_id"] == 7
    assert payload["activity_template_id"] == 3
    assert payload["wellness_template_id"] == 4
    assert payload["meal_constraints"] == ["high_protein", "low_prep"]
    assert payload["risk_subscores"] == {"physiological_strain": 0.9}
    assert payload["why_chosen"] == {"meal": "best fit"}
    assert payload["alternatives_considered"] == [{"meal": "backup"}]
    assert payload["why_changed_from_previous"] == ["Higher stress today."]
