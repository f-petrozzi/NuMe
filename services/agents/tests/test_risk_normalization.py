from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.agents.llm_utils import LlmResult
from services.agents.risk_stratification.agent import RiskStratificationAgent
from services.agents.signal_interpretation.agent import SignalInterpretationAgent


def test_signal_interpretation_does_not_flag_positive_numeric_checkin(monkeypatch):
    agent = SignalInterpretationAgent()
    monkeypatch.setattr(
        agent._llm,
        "generate_json",
        lambda _prompt: LlmResult(payload=None, error="llm unavailable"),
    )

    result = agent.run(
        signals={
            "sleep_hours": "7.5",
            "stress_level": "2",
            "check_in_mood": "8",
            "check_in_note": "Feeling calm and rested today.",
            "check_in_mood_score": 0.778,
            "check_in_note_sentiment": 0.333,
        }
    )

    assert result["generation_mode"] == "fallback"
    assert all(finding["type"] != "negative_checkin" for finding in result["findings"])
    assert result["summary"] == "Signals are mostly stable with only mild deviation from baseline."


def test_signal_interpretation_flags_low_numeric_mood_with_distressed_note(monkeypatch):
    agent = SignalInterpretationAgent()
    monkeypatch.setattr(
        agent._llm,
        "generate_json",
        lambda _prompt: LlmResult(payload=None, error="llm unavailable"),
    )

    result = agent.run(
        signals={
            "sleep_hours": "4.5",
            "stress_level": "9",
            "check_in_mood": "2",
            "check_in_note": "Overwhelmed and behind on everything.",
        }
    )

    finding_types = [finding["type"] for finding in result["findings"]]
    assert "negative_checkin" in finding_types
    negative = next(finding for finding in result["findings"] if finding["type"] == "negative_checkin")
    assert "Check-in mood is 2/10." in negative["evidence"]


def test_risk_stratification_returns_deterministic_subscores_and_drivers(monkeypatch):
    agent = RiskStratificationAgent()
    monkeypatch.setattr(
        agent._llm,
        "generate_json",
        lambda _prompt: LlmResult(payload=None, error="llm unavailable"),
    )

    result = agent.run(
        persona_type="student",
        findings=[
            {"type": "stress_spike", "severity": "significant"},
            {"type": "sleep_decline", "severity": "significant"},
            {"type": "negative_checkin", "severity": "moderate"},
        ],
        signals={
            "sleep_hours": "4.5",
            "stress_level": "9",
            "body_battery_high": "25",
            "steps": "900",
            "check_in_mood": "2",
            "check_in_note": "Overwhelmed and behind on everything.",
        },
        dynamic_state={
            "sleep_debt": 0.875,
            "recovery_score": 0.28,
            "adherence_score": 0.42,
            "routine_stability": 0.38,
        },
        recent_checkins=[
            {"mood_score": 0.22, "note": "Overwhelmed", "note_sentiment": -0.333},
            {"mood_score": 0.28, "note": "Still behind", "note_sentiment": -0.333},
        ],
        feature_windows={"sleep": {"7d": {"sleep_hours_avg": 5.4}}},
    )

    assert result["generation_mode"] == "fallback"
    assert result["risk_level"] in {"high", "critical"}
    assert set(result["subscores"]) == {
        "physiological_strain",
        "emotional_strain",
        "recovery_debt",
        "adherence_risk",
    }
    assert result["subscores"]["recovery_debt"] >= 0.7
    assert result["subscores"]["emotional_strain"] >= 0.6
    assert result["drivers"]
    assert "risk driven mostly by" in result["rationale"].lower()
