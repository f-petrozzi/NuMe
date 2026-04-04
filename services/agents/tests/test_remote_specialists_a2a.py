from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from a2a.types import AgentCard
from fastapi.testclient import TestClient
import httpx
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.agents.config import Settings
from services.agents.coordinator.agent import CareCoordinatorPipeline
from services.agents.runtime import AgentType
from services.agents.tooling import ToolProvider
from services.remote_specialists.caregiver_burnout.agent import root_agent as caregiver_root_agent
from services.remote_specialists.common import build_specialist_app
from services.remote_specialists.student_support.agent import root_agent as student_root_agent


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


@pytest.mark.parametrize(
    ("agent", "service_name", "expected_name"),
    [
        (student_root_agent, "student-support-specialist", "StudentSupportSpecialist"),
        (caregiver_root_agent, "caregiver-burnout-specialist", "CaregiverBurnoutSpecialist"),
    ],
)
def test_specialist_apps_expose_health_and_a2a_agent_cards(
    monkeypatch,
    agent,
    service_name: str,
    expected_name: str,
):
    monkeypatch.delenv("A2A_PUBLIC_BASE_URL", raising=False)
    app = build_specialist_app(
        agent=agent,
        service_name=service_name,
        default_public_base_url="http://testserver",
    )

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {
            "status": "ok",
            "service": service_name,
            "agent": expected_name,
        }

        card = client.get("/.well-known/agent-card.json")
        assert card.status_code == 200
        body = card.json()
        assert body["name"] == expected_name
        assert body["description"]
        assert body["url"].startswith("http://testserver")

        legacy_card = client.get("/.well-known/agent.json")
        assert legacy_card.status_code == 200
        assert legacy_card.json()["name"] == expected_name


def test_coordinator_consumes_remote_specialist_over_official_adk_a2a(monkeypatch):
    for key in (
        "AZURE_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "AZURE_API_KEY",
        "OPENAI_BASE_URL",
        "AZURE_OPENAI_BASE_URL",
        "AZURE_OPENAI_ENDPOINT",
        "OPENAI_API_VERSION",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_MODEL",
        "OPENAI_MODEL",
        "A2A_PUBLIC_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    app = build_specialist_app(
        agent=student_root_agent,
        service_name="student-support-specialist",
        default_public_base_url="http://testserver",
    )

    with TestClient(app) as client:
        card = AgentCard(**client.get("/.well-known/agent-card.json").json())
        async_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        )

        specialist_agent = RemoteA2aAgent(
            name="StudentSupportSpecialist",
            agent_card=card,
            description=card.description or "",
            httpx_client=async_client,
        )

        pipeline = CareCoordinatorPipeline(Settings(), ToolProvider(use_stubs=True))
        monkeypatch.setattr(
            pipeline.tool_provider,
            "get_resources",
            lambda persona: [{"title": "Campus counseling"}],
        )

        try:
            name, agent_type, result = pipeline._run_specialist(
                persona_type="student",
                findings=[],
                risk={"risk_level": "moderate"},
                draft_plan=_full_plan(),
                specialist_agent=specialist_agent,
            )
        finally:
            asyncio.run(async_client.aclose())

    assert name == "StudentSupportSpecialist"
    assert agent_type == AgentType.a2a
    assert result["generation_mode"] == "fallback"
    assert result["resources"] == ["Campus counseling"]
    assert result["burnout_risk_flag"] is True
    assert "study-break" in " ".join(result["intervention_adjustments"])


def test_coordinator_retries_transient_remote_specialist_failures(monkeypatch):
    pipeline = CareCoordinatorPipeline(Settings(), ToolProvider(use_stubs=True))
    attempts = {"count": 0}

    def fake_run_text_agent(**_kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError(
                "Failed to initialize remote A2A agent StudentSupportSpecialist: "
                "Failed to resolve AgentCard from URL http://specialist-student:8001/.well-known/agent-card.json: "
                "HTTP Error 503: Network communication error fetching agent card from "
                "http://specialist-student:8001/.well-known/agent-card.json: All connection attempts failed"
            )
        return [
            SimpleNamespace(
                author="StudentSupportSpecialist",
                error_message="",
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            text=json.dumps(
                                {
                                    "enriched_context": "Student-specific support context.",
                                    "resources": ["Campus counseling", "Peer tutoring"],
                                    "intervention_adjustments": ["Keep the plan low-pressure."],
                                    "burnout_risk_flag": True,
                                    "escalation_recommendation": "coordinator_review",
                                    "generation_mode": "llm",
                                    "generation_error": "",
                                }
                            )
                        )
                    ]
                ),
            )
        ]

    monkeypatch.setattr("services.agents.coordinator.agent.run_text_agent", fake_run_text_agent)
    monkeypatch.setattr("services.agents.coordinator.agent.sleep", lambda _seconds: None)

    specialist = type("FakeRemoteAgent", (), {"name": "StudentSupportSpecialist"})()
    result = pipeline._invoke_remote_specialist(
        specialist_agent=specialist,
        persona_type="student",
        findings=[],
        risk={"risk_level": "moderate"},
        draft_plan=_full_plan(),
        resources=["Campus counseling"],
    )

    assert attempts["count"] == 3
    assert result["generation_mode"] == "llm"
    assert result["burnout_risk_flag"] is True
    assert result["resources"] == ["Campus counseling", "Peer tutoring"]
