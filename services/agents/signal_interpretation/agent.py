from __future__ import annotations

from typing import Any, Dict, List, Mapping

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
            ),
            state_key=self.state_key,
            parse_output=lambda text, state: self.parse_response_text(text),
            fallback_output=lambda state, error: self.fallback_result(
                signals=dict(state.get("signals", {})),
                generation_error=error,
            ),
        )
        self._llm = OpenAIJsonClient()

    def run(self, *, signals: Dict[str, Any]) -> Dict[str, Any]:
        llm_result = self._generate_with_llm(signals=signals)
        if llm_result and "findings" in llm_result:
            return llm_result

        return self.fallback_result(
            signals=signals,
            generation_error=(llm_result or {}).get("generation_error", ""),
        )

    def build_prompt(self, *, signals: Dict[str, Any]) -> str:
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
            payload={"signals": signals},
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
        generation_error: str = "",
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        sleep_hours = float(signals.get("sleep_hours", 7) or 7)
        stress_level = float(signals.get("stress_level", 3) or 3)
        steps = float(signals.get("steps", 4000) or 4000)
        mood = str(signals.get("check_in_mood", "")).lower()
        note = str(signals.get("check_in_note", "")).lower()

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
        if any(token in mood for token in ["negative", "anxious", "overwhelmed"]) or any(
            token in note for token in ["overwhelmed", "drained", "behind"]
        ):
            findings.append(
                {
                    "type": "negative_checkin",
                    "severity": "moderate",
                    "confidence": 0.8,
                    "evidence": "Manual check-in language indicates distress.",
                }
            )

        if not findings:
            findings.append(
                {
                    "type": "routine_disruption",
                    "severity": "mild",
                    "confidence": 0.55,
                    "evidence": "Signals suggest a mild deviation from baseline.",
                }
            )

        summary = (
            "Signals show elevated strain with sleep, stress, and recovery patterns that merit support."
        )
        return SignalInterpretationResult(
            findings=findings,
            summary=summary,
            generation_mode="fallback",
            generation_error=generation_error,
        ).model_dump()

    def _generate_with_llm(self, *, signals: Dict[str, Any]) -> Dict[str, Any] | None:
        prompt = self.build_prompt(signals=signals)
        result = self._llm.generate_json(prompt)
        if not result.payload:
            return {"generation_error": result.error}

        try:
            return self._parse_payload(result.payload)
        except Exception as exc:
            return {"generation_error": f"{type(exc).__name__}: {exc}"}
