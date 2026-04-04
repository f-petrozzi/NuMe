from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional

API_ROOT = Path(__file__).resolve().parents[3] / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from risk_scoring import (
    build_deterministic_risk_assessment,
    is_negative_checkin,
    normalize_mood_score,
    safe_float,
    score_note_sentiment,
)

try:
    from services.agents.adk_compat import LlmAgent
    from services.agents.llm_utils import (
        DEFAULT_OPENAI_MODEL,
        OpenAIJsonClient,
        build_json_prompt,
        extract_json_object,
    )
    from services.agents.prompts import RISK_STRATIFICATION_PROMPT
    from services.agents.runtime import build_stateful_llm_agent
    from services.agents.schemas import RiskAssessment
except ImportError:
    from adk_compat import LlmAgent
    from llm_utils import (
        DEFAULT_OPENAI_MODEL,
        OpenAIJsonClient,
        build_json_prompt,
        extract_json_object,
    )
    from prompts import RISK_STRATIFICATION_PROMPT
    from runtime import build_stateful_llm_agent
    from schemas import RiskAssessment


class RiskStratificationAgent:
    state_key = "risk_assessment"

    def __init__(self, model: Any = DEFAULT_OPENAI_MODEL) -> None:
        self.definition = build_stateful_llm_agent(
            name="RiskStratification",
            model=model,
            instruction_builder=lambda state: self.build_prompt(
                persona_type=str(state.get("persona_type", "older_adult")),
                findings=self._findings_from_state(state),
                assessment=self._assessment_from_state(state),
            ),
            state_key=self.state_key,
            parse_output=lambda text, state: self.parse_response_text(text, state),
            fallback_output=lambda state, error: self.fallback_result(
                assessment=self._assessment_from_state(state),
                generation_error=error,
            ),
        )
        self._llm = OpenAIJsonClient()

    def run(
        self,
        *,
        persona_type: str,
        findings: Optional[List[Dict[str, Any]]] = None,
        signals: Optional[Dict[str, Any]] = None,
        dynamic_state: Optional[Dict[str, Any]] = None,
        recent_checkins: Optional[List[Dict[str, Any]]] = None,
        feature_windows: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        resolved_signals = signals or {}
        resolved_findings = list(findings) if findings is not None else self._derive_findings(
            resolved_signals,
            recent_checkins=recent_checkins or [],
        )
        assessment = self._build_assessment(
            persona_type=persona_type,
            findings=resolved_findings,
            signals=resolved_signals,
            dynamic_state=dynamic_state or {},
            recent_checkins=recent_checkins or [],
            feature_windows=feature_windows or {},
        )
        llm_result = self._generate_with_llm(
            persona_type=persona_type,
            findings=resolved_findings,
            assessment=assessment,
        )
        if llm_result and "risk_level" in llm_result:
            return llm_result

        return self.fallback_result(
            assessment=assessment,
            generation_error=(llm_result or {}).get("generation_error", ""),
        )

    def build_prompt(
        self,
        *,
        persona_type: str,
        findings: List[Dict[str, Any]],
        assessment: Mapping[str, Any],
    ) -> str:
        response_schema = {
            "drivers": ["brief driver"],
            "rationale": "brief explanation",
        }
        return build_json_prompt(
            instruction=RISK_STRATIFICATION_PROMPT,
            response_schema=response_schema,
            payload={
                "persona_type": persona_type,
                "findings": findings,
                "deterministic_risk": {
                    "risk_level": assessment["risk_level"],
                    "urgency": assessment["urgency"],
                    "confidence": assessment["confidence"],
                    "subscores": assessment["subscores"],
                    "drivers": assessment["drivers"],
                },
            },
        )

    def parse_response_text(self, text: str, state: Mapping[str, Any]) -> Dict[str, Any]:
        assessment = self._assessment_from_state(state)
        return self._parse_payload(
            extract_json_object(text),
            assessment=assessment,
            generation_mode="llm",
        )

    def _parse_payload(
        self,
        payload: Mapping[str, Any],
        *,
        assessment: Mapping[str, Any],
        generation_mode: str,
        generation_error: str = "",
    ) -> Dict[str, Any]:
        drivers = [
            str(item).strip()
            for item in payload.get("drivers", [])
            if str(item).strip()
        ] or list(assessment.get("drivers", []))
        rationale = str(payload.get("rationale", "")).strip() or str(assessment.get("rationale", "")).strip()
        if not rationale:
            raise ValueError("Model returned an empty rationale.")

        return RiskAssessment(
            risk_level=str(assessment["risk_level"]),
            urgency=str(assessment["urgency"]),
            escalation_needed=bool(assessment["escalation_needed"]),
            coordinator_review=bool(assessment["coordinator_review"]),
            confidence=max(0.0, min(float(assessment["confidence"]), 1.0)),
            subscores={
                str(key): round(safe_float(value), 3)
                for key, value in dict(assessment.get("subscores", {})).items()
            },
            drivers=drivers,
            rationale=rationale,
            generation_mode=generation_mode,
            generation_error=generation_error,
        ).model_dump()

    def fallback_result(
        self,
        *,
        assessment: Mapping[str, Any],
        generation_error: str = "",
    ) -> Dict[str, Any]:
        return RiskAssessment(
            risk_level=str(assessment["risk_level"]),
            urgency=str(assessment["urgency"]),
            escalation_needed=bool(assessment["escalation_needed"]),
            coordinator_review=bool(assessment["coordinator_review"]),
            confidence=max(0.0, min(float(assessment["confidence"]), 1.0)),
            subscores={
                str(key): round(safe_float(value), 3)
                for key, value in dict(assessment.get("subscores", {})).items()
            },
            drivers=list(assessment.get("drivers", [])),
            rationale=str(assessment.get("rationale", "")).strip(),
            generation_mode="fallback",
            generation_error=generation_error,
        ).model_dump()

    @staticmethod
    def _derive_findings(
        signals: Dict[str, Any],
        *,
        recent_checkins: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        recent_checkins = recent_checkins or []
        sleep_hours = safe_float(signals.get("sleep_hours"), 7.0)
        stress_level = safe_float(signals.get("stress_level"), 3.0)
        steps = safe_float(signals.get("steps"), 4000.0)
        mood_score = normalize_mood_score(signals.get("check_in_mood_score"))
        if mood_score is None:
            mood_score = normalize_mood_score(signals.get("check_in_mood"))
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
            findings.append({"type": "stress_spike", "severity": "significant"})
        if sleep_hours < 5.5:
            findings.append(
                {
                    "type": "sleep_decline",
                    "severity": "significant" if sleep_hours < 5 else "moderate",
                }
            )
        if steps < 1500:
            findings.append({"type": "low_activity", "severity": "moderate"})
        if is_negative_checkin(mood_score=mood_score, note_sentiment=note_sentiment):
            findings.append({"type": "negative_checkin", "severity": "moderate"})
        return findings or [{"type": "routine_disruption", "severity": "mild"}]

    def _findings_from_state(self, state: Mapping[str, Any]) -> List[Dict[str, Any]]:
        findings = list(((state.get("signal_interpretation", {}) or {}).get("findings", [])))
        if findings:
            return findings
        return self._derive_findings(
            dict(state.get("signals", {})),
            recent_checkins=list(state.get("recent_checkins", [])),
        )

    def _assessment_from_state(self, state: Mapping[str, Any]) -> Dict[str, Any]:
        return self._build_assessment(
            persona_type=str(state.get("persona_type", "older_adult")),
            findings=self._findings_from_state(state),
            signals=dict(state.get("signals", {})),
            dynamic_state=dict(state.get("dynamic_state", {})),
            recent_checkins=list(state.get("recent_checkins", [])),
            feature_windows=dict(state.get("feature_windows", {})),
        )

    def _build_assessment(
        self,
        *,
        persona_type: str,
        findings: List[Dict[str, Any]],
        signals: Dict[str, Any],
        dynamic_state: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]],
        feature_windows: Dict[str, Any],
    ) -> Dict[str, Any]:
        return build_deterministic_risk_assessment(
            persona_type=persona_type,
            signals=signals,
            dynamic_state=dynamic_state,
            recent_checkins=recent_checkins,
            feature_windows=feature_windows,
            findings=findings,
        )

    def _generate_with_llm(
        self,
        *,
        persona_type: str,
        findings: List[Dict[str, Any]],
        assessment: Mapping[str, Any],
    ) -> Dict[str, Any] | None:
        prompt = self.build_prompt(
            persona_type=persona_type,
            findings=findings,
            assessment=assessment,
        )
        result = self._llm.generate_json(prompt)
        if not result.payload:
            return {"generation_error": result.error}

        try:
            return self._parse_payload(
                result.payload,
                assessment=assessment,
                generation_mode="llm",
            )
        except Exception as exc:
            return {"generation_error": f"{type(exc).__name__}: {exc}"}
