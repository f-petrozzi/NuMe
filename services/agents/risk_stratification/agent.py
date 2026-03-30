from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from services.agents.adk_compat import LlmAgent
    from services.agents.llm_utils import OpenAIJsonClient, build_json_prompt
    from services.agents.prompts import RISK_STRATIFICATION_PROMPT
    from services.agents.schemas import RiskAssessment
except ImportError:
    from adk_compat import LlmAgent
    from llm_utils import OpenAIJsonClient, build_json_prompt
    from prompts import RISK_STRATIFICATION_PROMPT
    from schemas import RiskAssessment


class RiskStratificationAgent:
    def __init__(self) -> None:
        self.definition = LlmAgent(
            name="RiskStratification",
            instruction=RISK_STRATIFICATION_PROMPT,
        )
        self._llm = OpenAIJsonClient()

    def run(
        self,
        *,
        persona_type: str,
        findings: Optional[List[Dict[str, Any]]] = None,
        signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        findings = findings or self._derive_findings(signals or {})
        llm_result = self._generate_with_llm(persona_type=persona_type, findings=findings)
        if llm_result and "risk_level" in llm_result:
            return llm_result

        significant_count = sum(1 for finding in findings if finding["severity"] == "significant")
        distress_count = len(findings)

        risk_level = "low"
        urgency = "routine"
        escalation_needed = False
        coordinator_review = False

        if significant_count >= 2 or (persona_type == "caregiver" and distress_count >= 3):
            risk_level = "high"
            urgency = "same_day"
            escalation_needed = True
            coordinator_review = True
        elif significant_count >= 1 or distress_count >= 3:
            risk_level = "moderate"
            urgency = "next_day"
            escalation_needed = True

        if persona_type == "student" and any(
            finding["type"] == "negative_checkin" for finding in findings
        ) and significant_count >= 2:
            risk_level = "high"
            urgency = "same_day"
            escalation_needed = True
            coordinator_review = True

        rationale = (
            f"{persona_type} persona with {distress_count} active findings and "
            f"{significant_count} significant signals requires a {risk_level} response."
        )
        return RiskAssessment(
            risk_level=risk_level,
            urgency=urgency,
            escalation_needed=escalation_needed,
            coordinator_review=coordinator_review,
            confidence=0.82 if risk_level in {"moderate", "high"} else 0.68,
            rationale=rationale,
            generation_mode="fallback",
            generation_error=(llm_result or {}).get("generation_error", ""),
        ).model_dump()

    @staticmethod
    def _derive_findings(signals: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        sleep_hours = float(signals.get("sleep_hours", 7) or 7)
        stress_level = float(signals.get("stress_level", 3) or 3)
        steps = float(signals.get("steps", 4000) or 4000)
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
        if signals.get("check_in_mood") or signals.get("check_in_note"):
            findings.append({"type": "negative_checkin", "severity": "moderate"})
        return findings or [{"type": "routine_disruption", "severity": "mild"}]

    def _generate_with_llm(
        self,
        *,
        persona_type: str,
        findings: List[Dict[str, Any]],
    ) -> Dict[str, Any] | None:
        response_schema = {
            "risk_level": "low | moderate | high | critical",
            "urgency": "routine | next_day | same_day | immediate",
            "escalation_needed": True,
            "coordinator_review": True,
            "confidence": 0.8,
            "rationale": "brief explanation",
        }
        prompt = build_json_prompt(
            instruction=RISK_STRATIFICATION_PROMPT,
            response_schema=response_schema,
            payload={"persona_type": persona_type, "findings": findings},
        )
        result = self._llm.generate_json(prompt)
        if not result.payload:
            return {"generation_error": result.error}

        try:
            risk_level = str(result.payload.get("risk_level", "low")).strip()
            urgency = str(result.payload.get("urgency", "routine")).strip()
            if risk_level not in {"low", "moderate", "high", "critical"}:
                raise ValueError(f"Unsupported risk level: {risk_level}")
            if urgency not in {"routine", "next_day", "same_day", "immediate"}:
                raise ValueError(f"Unsupported urgency: {urgency}")

            return RiskAssessment(
                risk_level=risk_level,
                urgency=urgency,
                escalation_needed=bool(result.payload.get("escalation_needed", False)),
                coordinator_review=bool(result.payload.get("coordinator_review", False)),
                confidence=max(0.0, min(float(result.payload.get("confidence", 0.5)), 1.0)),
                rationale=str(result.payload.get("rationale", "")).strip(),
                generation_mode="llm",
                generation_error="",
            ).model_dump()
        except Exception as exc:
            return {"generation_error": f"{type(exc).__name__}: {exc}"}
