from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class Dumpable:
    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Finding(Dumpable):
    type: str
    severity: str
    confidence: float
    evidence: str


@dataclass
class SignalInterpretationResult(Dumpable):
    findings: List[Finding]
    summary: str
    generation_mode: str = "fallback"
    generation_error: str = ""


@dataclass
class RiskAssessment(Dumpable):
    risk_level: str
    urgency: str
    escalation_needed: bool
    coordinator_review: bool
    confidence: float
    rationale: str
    generation_mode: str = "fallback"
    generation_error: str = ""


@dataclass
class MealSuggestion(Dumpable):
    title: str
    description: str
    rationale: str


@dataclass
class ActivitySuggestion(Dumpable):
    title: str
    description: str
    duration_minutes: int
    intensity: str
    rationale: str


@dataclass
class WellnessAction(Dumpable):
    title: str
    description: str
    rationale: str


@dataclass
class InterventionDraft(Dumpable):
    meal_suggestion: MealSuggestion
    activity_suggestion: ActivitySuggestion
    wellness_action: WellnessAction
    generation_mode: str = "fallback"
    generation_error: str = ""
    resources: List[str] = field(default_factory=list)
    notes: str = ""
    meal_constraints: List[str] = field(default_factory=list)


@dataclass
class EmpathyResult(Dumpable):
    empathy_message: str
    generation_mode: str = "fallback"
    generation_error: str = ""


@dataclass
class ValidationIssue(Dumpable):
    type: str
    description: str
    suggested_fix: str


@dataclass
class ValidationResult(Dumpable):
    approved: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    revised_plan: Optional[Dict[str, Any]] = None
    halt: bool = False
    generation_mode: str = "fallback"
    generation_error: str = ""


@dataclass
class SpecialistResult(Dumpable):
    enriched_context: str
    resources: List[str] = field(default_factory=list)
    intervention_adjustments: List[str] = field(default_factory=list)
    burnout_risk_flag: Optional[bool] = None
    escalation_recommendation: Optional[str] = None
    generation_mode: str = "fallback"
    generation_error: str = ""


@dataclass
class FinalPlan(Dumpable):
    meal_suggestion: str
    activity_suggestion: str
    wellness_action: str
    empathy_message: str
    risk_level: str
    generation_mode: str = "fallback"
    generation_error: str = ""
    resources: List[str] = field(default_factory=list)
    notes: str = ""
