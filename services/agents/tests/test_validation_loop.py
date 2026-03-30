from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.agents.config import Settings
from services.agents.coordinator.agent import CareCoordinatorPipeline
from services.agents.runtime import AgentType
from services.agents.tooling import ToolProvider
from services.agents.validation_loop.agent import ValidationLoopAgent


def _full_plan() -> dict:
    return {
        "meal_suggestion": {
            "title": "Supportive Meal",
            "description": "A balanced meal.",
            "rationale": "Stable energy.",
        },
        "activity_suggestion": {
            "title": "Gentle Reset",
            "description": "Take a short walk.",
            "duration_minutes": 15,
            "intensity": "low",
            "rationale": "Manageable movement.",
        },
        "wellness_action": {
            "title": "Check-In",
            "description": "Pause for breathing.",
            "rationale": "Reduce stress.",
        },
        "generation_mode": "llm",
        "generation_error": "",
        "resources": ["Campus counseling"],
        "notes": "Initial notes.",
        "meal_constraints": ["high_protein"],
    }


def test_validation_loop_merges_partial_revised_plan_and_preserves_it_on_approval(monkeypatch):
    agent = ValidationLoopAgent()
    responses = iter(
        [
            {
                "approved": False,
                "issues": [
                    {
                        "type": "accessibility_mismatch",
                        "description": "Trim effort.",
                        "suggested_fix": "Reduce duration.",
                    }
                ],
                "revised_plan": {
                    "activity_suggestion": {"duration_minutes": 5},
                    "notes": "Validation updated the plan.",
                },
                "halt": False,
            },
            {
                "approved": True,
                "issues": [],
                "revised_plan": None,
                "halt": False,
            },
        ]
    )
    monkeypatch.setattr(agent, "_generate_with_llm", lambda **_kwargs: next(responses))

    result, iterations = agent.validate(
        findings=[],
        risk_level="moderate",
        intervention_plan=_full_plan(),
        empathy_message="You can do this.",
        user_profile={"accessibility": None},
    )

    assert result["approved"] is True
    assert result["revised_plan"]["meal_suggestion"]["description"] == "A balanced meal."
    assert result["revised_plan"]["activity_suggestion"]["duration_minutes"] == 5
    assert result["revised_plan"]["activity_suggestion"]["description"] == "Take a short walk."
    assert result["revised_plan"]["notes"] == "Validation updated the plan."
    assert iterations[0]["output"]["revised_plan"]["wellness_action"]["description"] == "Pause for breathing."


def test_coordinator_run_handles_partial_validation_patch_without_crashing(monkeypatch):
    pipeline = CareCoordinatorPipeline(Settings(), ToolProvider(use_stubs=True))

    monkeypatch.setattr(
        pipeline.tool_provider,
        "get_user_profile",
        lambda persona_type="student": {
            "user_id": 12,
            "goal": "stress_reduction",
            "dietary_style": "balanced",
            "allergies": [],
            "persona_type": "student",
            "accessibility": None,
        },
    )
    monkeypatch.setattr(
        pipeline.tool_provider,
        "get_recent_signals",
        lambda scenario="stressed_student": [
            {"signal_type": "stress_level", "value": 8},
            {"signal_type": "sleep_hours", "value": 5.5},
        ],
    )
    monkeypatch.setattr(
        pipeline.tool_provider,
        "get_resources",
        lambda persona: [{"title": "Campus counseling"}],
    )
    monkeypatch.setattr(
        pipeline.signal_agent,
        "run",
        lambda **_kwargs: {
            "findings": [{"type": "stress", "severity": "high", "confidence": 0.9, "evidence": "check-in"}],
            "summary": "High stress day.",
            "generation_mode": "llm",
            "generation_error": "",
        },
    )
    monkeypatch.setattr(
        pipeline.risk_agent,
        "run",
        lambda **_kwargs: {
            "risk_level": "moderate",
            "urgency": "today",
            "escalation_needed": False,
            "coordinator_review": False,
            "confidence": 0.8,
            "rationale": "Elevated stress.",
            "generation_mode": "llm",
            "generation_error": "",
        },
    )
    monkeypatch.setattr(pipeline.intervention_agent, "run", lambda **_kwargs: _full_plan())
    monkeypatch.setattr(
        pipeline,
        "_run_specialist",
        lambda **_kwargs: (
            "StudentSupportSpecialist",
            AgentType.a2a,
            {
                "enriched_context": "",
                "resources": [],
                "intervention_adjustments": [],
                "generation_mode": "llm",
                "generation_error": "",
            },
        ),
    )
    monkeypatch.setattr(
        pipeline.empathy_agent,
        "run",
        lambda **_kwargs: {
            "empathy_message": "Take it one step at a time.",
            "generation_mode": "llm",
            "generation_error": "",
        },
    )
    monkeypatch.setattr(
        pipeline.validation_loop,
        "validate",
        lambda **_kwargs: (
            {
                "approved": True,
                "issues": [],
                "revised_plan": {
                    "notes": "Validation updated the plan.",
                    "activity_suggestion": {"duration_minutes": 5},
                },
                "halt": False,
                "generation_mode": "llm",
                "generation_error": "",
            },
            [],
        ),
    )

    result = pipeline.run(user_id="12", scenario="stressed_student", run_id=9)

    assert result["final_plan"]["meal_suggestion"] == "A balanced meal."
    assert result["final_plan"]["activity_suggestion"] == "Take a short walk."
    assert result["final_plan"]["notes"] == "Validation updated the plan."
    assert result["intervention_record"]["meal_suggestion"] == "A balanced meal."


def test_coordinator_persists_artifacts_for_run_owner_not_profile_user(monkeypatch):
    pipeline = CareCoordinatorPipeline(Settings(), ToolProvider(use_stubs=True))
    captured: dict[str, dict] = {}

    monkeypatch.setattr(
        pipeline.tool_provider,
        "get_user_profile",
        lambda persona_type="student": {
            "user_id": 999,
            "goal": "stress_reduction",
            "dietary_style": "balanced",
            "allergies": [],
            "persona_type": "student",
            "accessibility": None,
        },
    )
    monkeypatch.setattr(
        pipeline.tool_provider,
        "get_recent_signals",
        lambda scenario="stressed_student": [
            {"signal_type": "stress_level", "value": 8},
            {"signal_type": "sleep_hours", "value": 5.5},
        ],
    )
    monkeypatch.setattr(
        pipeline.tool_provider,
        "get_resources",
        lambda persona: [{"title": "Campus counseling"}],
    )
    monkeypatch.setattr(
        pipeline.signal_agent,
        "run",
        lambda **_kwargs: {
            "findings": [{"type": "stress", "severity": "high", "confidence": 0.9, "evidence": "check-in"}],
            "summary": "High stress day.",
            "generation_mode": "llm",
            "generation_error": "",
        },
    )
    monkeypatch.setattr(
        pipeline.risk_agent,
        "run",
        lambda **_kwargs: {
            "risk_level": "moderate",
            "urgency": "today",
            "escalation_needed": False,
            "coordinator_review": False,
            "confidence": 0.8,
            "rationale": "Elevated stress.",
            "generation_mode": "llm",
            "generation_error": "",
        },
    )
    monkeypatch.setattr(pipeline.intervention_agent, "run", lambda **_kwargs: _full_plan())
    monkeypatch.setattr(
        pipeline,
        "_run_specialist",
        lambda **_kwargs: (
            "StudentSupportSpecialist",
            AgentType.a2a,
            {
                "enriched_context": "",
                "resources": [],
                "intervention_adjustments": [],
                "generation_mode": "llm",
                "generation_error": "",
            },
        ),
    )
    monkeypatch.setattr(
        pipeline.empathy_agent,
        "run",
        lambda **_kwargs: {
            "empathy_message": "Take it one step at a time.",
            "generation_mode": "llm",
            "generation_error": "",
        },
    )
    monkeypatch.setattr(
        pipeline.validation_loop,
        "validate",
        lambda **_kwargs: (
            {
                "approved": True,
                "issues": [],
                "revised_plan": None,
                "halt": False,
                "generation_mode": "llm",
                "generation_error": "",
            },
            [],
        ),
    )
    monkeypatch.setattr(
        pipeline.tool_provider,
        "create_intervention",
        lambda payload: captured.setdefault("intervention", payload) or {"id": 1, **payload},
    )
    monkeypatch.setattr(
        pipeline.tool_provider,
        "create_case",
        lambda payload: captured.setdefault("case", payload) or {"id": 2, **payload, "status": "open"},
    )
    monkeypatch.setattr(
        pipeline.tool_provider,
        "send_notification",
        lambda payload: captured.setdefault("notification", payload) or {"id": 3, **payload, "status": "queued"},
    )

    result = pipeline.run(user_id="12", scenario="stressed_student", run_id=9)

    assert captured["intervention"]["user_id"] == 12
    assert captured["case"]["user_id"] == 12
    assert captured["notification"]["user_id"] == 12
    assert result["intervention_record"]["user_id"] == 12


def test_run_specialist_falls_back_locally_when_remote_service_is_unavailable(monkeypatch):
    pipeline = CareCoordinatorPipeline(Settings(), ToolProvider(use_stubs=True))

    monkeypatch.setattr(
        pipeline.tool_provider,
        "get_resources",
        lambda persona: [{"title": "Campus counseling"}],
    )
    monkeypatch.setattr(
        pipeline,
        "_invoke_remote_specialist",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("connect timeout")),
    )
    monkeypatch.setattr(
        pipeline,
        "_generate_local_specialist",
        lambda **kwargs: {
            "enriched_context": "Local fallback used.",
            "resources": kwargs["resources"],
            "intervention_adjustments": ["Use the local specialist fallback."],
            "generation_mode": "llm_fallback",
            "generation_error": kwargs["upstream_error"],
        },
    )

    name, agent_type, result = pipeline._run_specialist(
        persona_type="student",
        findings=[],
        risk={"risk_level": "moderate"},
        draft_plan=_full_plan(),
        specialist_agent=pipeline._specialist_for("student"),
    )

    assert name == "StudentSupportFallback"
    assert agent_type == AgentType.local
    assert result["generation_mode"] == "llm_fallback"
    assert "connect timeout" in result["generation_error"]
