from __future__ import annotations

from typing import Any, Dict

from services.remote_specialists.common import SpecialistRequest, build_specialist_app


INSTRUCTION = """
You are the Student Support Specialist for NüMe.

You receive signal findings, risk level, an intervention draft, and available campus resources.
Return structured JSON only.

Your job is to:
- interpret the case in the context of academic overload, exam pressure, and student recovery
- strengthen the intervention with realistic, low-pressure student-specific adjustments
- include campus-specific resources already provided when relevant
- flag burnout risk when the case suggests sustained academic overload
""".strip()


RESPONSE_SCHEMA = {
    "enriched_context": "student-specific interpretation",
    "resources": ["resource title"],
    "intervention_adjustments": ["specific change"],
    "burnout_risk_flag": True,
    "escalation_recommendation": "none | coordinator_review",
}


def _fallback(*, body: SpecialistRequest) -> Dict[str, Any]:
    return {
        "enriched_context": "Stress pattern aligns with academic overload and low recovery.",
        "resources": body.resources,
        "intervention_adjustments": [
            "Favor low-pressure study-break framing.",
            "Include campus counseling and academic support options.",
        ],
        "burnout_risk_flag": body.risk.get("risk_level") in {"moderate", "high", "critical"},
        "escalation_recommendation": "coordinator_review"
        if body.risk.get("risk_level") in {"high", "critical"}
        else "none",
    }


app = build_specialist_app(
    title="student-support-specialist",
    instruction=INSTRUCTION,
    response_schema=RESPONSE_SCHEMA,
    fallback_factory=_fallback,
)
