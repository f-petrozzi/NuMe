from __future__ import annotations

from typing import Any, Dict

from services.remote_specialists.common import SpecialistRequest, StructuredSpecialistAgent


INSTRUCTION = """
You are the Caregiver Burnout Specialist for NüMe.

You receive signal findings, risk level, an intervention draft, and available support resources.
Return structured JSON only.

Your job is to:
- interpret the case through caregiver burden and depleted recovery capacity
- adjust interventions to be micro-effort and realistic under time scarcity
- surface support-group or respite resources from the provided list when relevant
- recommend coordinator escalation when burden is high
""".strip()


RESPONSE_SCHEMA = {
    "enriched_context": "caregiver-specific interpretation",
    "resources": ["resource title"],
    "intervention_adjustments": ["specific change"],
    "burnout_risk_flag": True,
    "escalation_recommendation": "none | coordinator_review | trusted_contact_outreach",
}


def _fallback(*, body: SpecialistRequest) -> Dict[str, Any]:
    return {
        "enriched_context": "Signals suggest caregiver burden with limited recovery capacity.",
        "resources": body.resources,
        "intervention_adjustments": [
            "Favor micro-effort actions with no equipment.",
            "Include respite and support-group resources.",
        ],
        "burnout_risk_flag": True,
        "escalation_recommendation": "coordinator_review"
        if body.risk.get("risk_level") in {"high", "critical"}
        else "none",
    }


root_agent = StructuredSpecialistAgent(
    name="CaregiverBurnoutSpecialist",
    description=(
        "Remote A2A specialist for caregiver persona. Enriches intervention plans with "
        "caregiver-burden context, respite resource recommendations, and escalation guidance."
    ),
    instruction=INSTRUCTION,
    response_schema=RESPONSE_SCHEMA,
    fallback_factory=_fallback,
)
