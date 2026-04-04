from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping

API_ROOT = Path(__file__).resolve().parents[3] / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from risk_scoring import is_negative_checkin, normalize_mood_score, safe_float, score_note_sentiment

try:
    from services.agents.adk_compat import LlmAgent
    from services.agents.llm_utils import (
        DEFAULT_OPENAI_MODEL,
        OpenAIJsonClient,
        build_json_prompt,
        extract_json_object,
    )
    from services.agents.prompts import SIGNAL_INTERPRETATION_PROMPT
    from services.agents.runtime import build_stateful_llm_agent
    from services.agents.schemas import SignalInterpretationResult
except ImportError:
    from adk_compat import LlmAgent
    from llm_utils import (
        DEFAULT_OPENAI_MODEL,
        OpenAIJsonClient,
        build_json_prompt,
        extract_json_object,
    )
    from prompts import SIGNAL_INTERPRETATION_PROMPT
    from runtime import build_stateful_llm_agent
    from schemas import SignalInterpretationResult


class SignalInterpretationAgent:
    state_key = "signal_interpretation"

    def __init__(self, model: Any = DEFAULT_OPENAI_MODEL) -> None:
        self.definition = build_stateful_llm_agent(
            name="SignalInterpretation",
            model=model,
            instruction_builder=lambda state: self.build_prompt(
                signals=dict(state.get("signals", {})),
                recent_checkins=list(state.get("recent_checkins", [])),
            ),
            state_key=self.state_key,
            parse_output=lambda text, state: self.parse_response_text(text),
            fallback_output=lambda state, error: self.fallback_result(
                signals=dict(state.get("signals", {})),
                recent_checkins=list(state.get("recent_checkins", [])),
                generation_error=error,
            ),
        )
        self._llm = OpenAIJsonClient()

    def run(
        self,
        *,
        signals: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        llm_result = self._generate_with_llm(signals=signals, recent_checkins=recent_checkins or [])
        if llm_result and "findings" in llm_result:
            return llm_result

        return self.fallback_result(
            signals=signals,
            recent_checkins=recent_checkins or [],
            generation_error=(llm_result or {}).get("generation_error", ""),
        )

    def build_prompt(
        self,
        *,
        signals: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]] | None = None,
    ) -> str:
        response_schema = {
            "findings": [
                {
                    "type": "stress_spike | sleep_decline | low_activity | inactivity_anomaly | negative_checkin | routine_disruption | social_withdrawal_risk | recovery_deficit",
                    "severity": "mild | moderate | significant",
                    "confidence": 0.8,
                    "evidence": "brief evidence",
                }
            ],
            "summary": "one sentence summary",
        }
        return build_json_prompt(
            instruction=SIGNAL_INTERPRETATION_PROMPT,
            response_schema=response_schema,
            payload={
                "signals": signals,
                "recent_checkins": list(recent_checkins or [])[:5],
            },
        )

    def parse_response_text(self, text: str) -> Dict[str, Any]:
        return self._parse_payload(extract_json_object(text))

    def _parse_payload(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        findings = []
        for raw in payload.get("findings", []):
            findings.append(
                {
                    "type": str(raw.get("type", "routine_disruption")).strip(),
                    "severity": str(raw.get("severity", "mild")).strip(),
                    "confidence": max(0.0, min(float(raw.get("confidence", 0.5)), 1.0)),
                    "evidence": str(raw.get("evidence", "")).strip(),
                }
            )
        summary = str(payload.get("summary", "")).strip()
        if not summary:
            raise ValueError("Model returned an empty summary.")

        if not findings:
            findings.append(
                {
                    "type": "routine_disruption",
                    "severity": "mild",
                    "confidence": 0.55,
                    "evidence": summary,
                }
            )

        return SignalInterpretationResult(
            findings=findings,
            summary=summary,
            generation_mode="llm",
            generation_error="",
        ).model_dump()

    def fallback_result(
        self,
        *,
        signals: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]] | None = None,
        generation_error: str = "",
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        recent_checkins = recent_checkins or []
        sleep_hours = safe_float(signals.get("sleep_hours"), 7.0)
        stress_level = safe_float(signals.get("stress_level"), 3.0)
        steps = safe_float(signals.get("steps"), 4000.0)
        raw_mood = signals.get("check_in_mood")
        mood_score = normalize_mood_score(signals.get("check_in_mood_score"))
        if mood_score is None:
            mood_score = normalize_mood_score(raw_mood)
        if mood_score is None:
            mood_score = next(
                (
                    normalize_mood_score(item.get("mood_score"))
                    for item in recent_checkins
                    if item.get("mood_score") is not None
                ),
                None,
            )
        note = str(signals.get("check_in_note", "")).strip()
        note_sentiment = safe_float(signals.get("check_in_note_sentiment"), score_note_sentiment(note))
        if not note and recent_checkins:
            note_sentiment = next(
                (
                    safe_float(item.get("note_sentiment"), 0.0)
                    for item in recent_checkins
                    if item.get("note")
                ),
                note_sentiment,
            )

        if stress_level >= 8:
            findings.append(
                {
                    "type": "stress_spike",
                    "severity": "significant",
                    "confidence": 0.9,
                    "evidence": f"Stress level is elevated at {stress_level}/10.",
                }
            )
        if sleep_hours < 5.5:
            findings.append(
                {
                    "type": "sleep_decline",
                    "severity": "significant" if sleep_hours < 5 else "moderate",
                    "confidence": 0.88,
                    "evidence": f"Sleep is reduced to {sleep_hours} hours.",
                }
            )
        if steps < 1500:
            findings.append(
                {
                    "type": "low_activity",
                    "severity": "moderate",
                    "confidence": 0.78,
                    "evidence": f"Step count is low at {int(steps)}.",
                }
            )
        if is_negative_checkin(mood_score=mood_score, note_sentiment=note_sentiment):
            evidence_parts: List[str] = []
            if raw_mood is not None and mood_score is not None and mood_score <= 0.4:
                evidence_parts.append(f"Check-in mood is {raw_mood}/10.")
            if note and note_sentiment < 0:
                evidence_parts.append("Check-in note language indicates distress.")
            if not evidence_parts:
                evidence_parts.append("Recent check-in signals indicate distress.")
            findings.append(
                {
                    "type": "negative_checkin",
                    "severity": "moderate",
                    "confidence": 0.8,
                    "evidence": " ".join(evidence_parts),
                }
            )

        if not findings:
            summary = "Signals are mostly stable with only mild deviation from baseline."
            findings.append(
                {
                    "type": "routine_disruption",
                    "severity": "mild",
                    "confidence": 0.55,
                    "evidence": summary,
                }
            )
        elif any(item["severity"] == "significant" for item in findings):
            summary = "Signals show elevated strain with sleep, stress, and recovery patterns that merit support."
        elif any(item["type"] == "negative_checkin" for item in findings):
            summary = "Signals point to emotional strain in the latest check-in and a need for lighter support."
        else:
            summary = "Signals show mild strain that should be addressed with a manageable support plan."
        return SignalInterpretationResult(
            findings=findings,
            summary=summary,
            generation_mode="fallback",
            generation_error=generation_error,
        ).model_dump()

    def _generate_with_llm(
        self,
        *,
        signals: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any] | None:
        prompt = self.build_prompt(signals=signals, recent_checkins=recent_checkins or [])
        result = self._llm.generate_json(prompt)
        if not result.payload:
            return {"generation_error": result.error}

        try:
            return self._parse_payload(result.payload)
        except Exception as exc:
            return {"generation_error": f"{type(exc).__name__}: {exc}"}
