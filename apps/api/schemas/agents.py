from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TriggerRunRequest(BaseModel):
    user_id: Optional[int] = None  # admin can specify; otherwise inferred from JWT
    normalized_event_id: Optional[int] = None


class AgentRunOut(BaseModel):
    id: int
    user_id: int
    normalized_event_id: Optional[int]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    risk_level: str
    member_label: Optional[str] = None
    member_email: Optional[str] = None
    persona_type: Optional[str] = None
    summary: Optional[str] = None

    model_config = {"from_attributes": True}


class AgentMessageOut(BaseModel):
    id: int
    run_id: int
    agent_name: str
    agent_type: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    iteration: int
    duration_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseOut(BaseModel):
    id: int
    user_id: int
    run_id: Optional[int]
    risk_level: str
    status: str
    created_at: datetime
    updated_at: datetime
    member_label: Optional[str] = None
    member_email: Optional[str] = None
    persona_type: Optional[str] = None
    summary: Optional[str] = None

    model_config = {"from_attributes": True}


class CaseStatusUpdate(BaseModel):
    status: str  # open|in_progress|closed


class InterventionOut(BaseModel):
    id: int
    run_id: Optional[int]
    user_id: int
    state_snapshot_id: Optional[int] = None
    recipe_id: Optional[int] = None
    activity_template_id: Optional[int] = None
    wellness_template_id: Optional[int] = None
    meal_suggestion: str
    activity_suggestion: str
    wellness_action: str
    empathy_message: str
    meal_constraints: List[str] = Field(default_factory=list)
    risk_subscores: Optional[Dict[str, Any]] = None
    why_chosen: Optional[Dict[str, Any]] = None
    alternatives_considered: Optional[List[Any]] = None
    why_changed_from_previous: Optional[List[str]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunTraceOut(BaseModel):
    run: AgentRunOut
    messages: List[AgentMessageOut]
    intervention: Optional[InterventionOut] = None
    case: Optional[CaseOut] = None


class SupportPlanRunOut(BaseModel):
    id: int
    status: str
    risk_level: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    normalized_event_id: Optional[int] = None


class SupportPlanStateSnapshotOut(BaseModel):
    id: int
    run_id: Optional[int] = None
    source: str
    created_at: datetime
    dynamic_state: Dict[str, Any] = Field(default_factory=dict)
    archetype_scores: Dict[str, Any] = Field(default_factory=dict)


class SupportPlanRiskOut(BaseModel):
    level: str = "low"
    urgency: str = "routine"
    confidence: float = 0.0
    subscores: Dict[str, Any] = Field(default_factory=dict)
    drivers: List[str] = Field(default_factory=list)
    rationale: str = ""


class SupportPlanRecipeOut(BaseModel):
    id: int
    title: str
    description: str
    tags: List[str] = Field(default_factory=list)
    prep_minutes: int
    cook_minutes: int
    calories: Optional[int] = None
    protein_grams: Optional[float] = None
    carbs_grams: Optional[float] = None
    fat_grams: Optional[float] = None
    fiber_grams: Optional[float] = None
    prep_effort: Optional[str] = None
    cost_level: Optional[str] = None
    equipment_tags: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SupportPlanActivityTemplateOut(BaseModel):
    id: int
    title: str
    description: str
    duration_minutes: int
    intensity: str
    accessibility_tags: List[str] = Field(default_factory=list)
    equipment_tags: List[str] = Field(default_factory=list)
    time_cost_level: str
    fatigue_sensitivity: str
    contraindication_tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SupportPlanWellnessTemplateOut(BaseModel):
    id: int
    title: str
    description: str
    category: str
    duration_minutes: int
    accessibility_tags: List[str] = Field(default_factory=list)
    time_cost_level: str
    fatigue_sensitivity: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SupportPlanMealOut(BaseModel):
    recipe_id: Optional[int] = None
    title: str
    description: str
    text: str = ""
    constraints: List[str] = Field(default_factory=list)
    why_chosen: List[str] = Field(default_factory=list)
    alternatives_considered: List[Any] = Field(default_factory=list)
    recipe: Optional[SupportPlanRecipeOut] = None


class SupportPlanActivityOut(BaseModel):
    template_id: Optional[int] = None
    title: str
    description: str
    text: str = ""
    duration_minutes: Optional[int] = None
    intensity: Optional[str] = None
    why_chosen: List[str] = Field(default_factory=list)
    alternatives_considered: List[Any] = Field(default_factory=list)
    template: Optional[SupportPlanActivityTemplateOut] = None


class SupportPlanWellnessOut(BaseModel):
    template_id: Optional[int] = None
    title: str
    description: str
    text: str = ""
    category: Optional[str] = None
    why_chosen: List[str] = Field(default_factory=list)
    alternatives_considered: List[Any] = Field(default_factory=list)
    template: Optional[SupportPlanWellnessTemplateOut] = None


class SupportPlanPlanOut(BaseModel):
    intervention_id: int
    created_at: datetime
    meal: SupportPlanMealOut
    activity: SupportPlanActivityOut
    wellness: SupportPlanWellnessOut
    empathy_message: str
    rationale: str = ""
    why_changed_from_previous: List[str] = Field(default_factory=list)


class SupportPlanCurrentOut(BaseModel):
    generated_at: datetime
    run: Optional[SupportPlanRunOut] = None
    state_snapshot: Optional[SupportPlanStateSnapshotOut] = None
    risk: SupportPlanRiskOut
    plan: Optional[SupportPlanPlanOut] = None


SupportPlanFeedbackEventType = Literal[
    "viewed",
    "accepted",
    "skipped",
    "completed",
    "recipe_cooked",
    "calorie_logged_after_recommendation",
    "manual_override",
]
SupportPlanRecommendationKind = Literal["meal", "activity", "wellness", "recipe"]


class SupportPlanFeedbackEventIn(BaseModel):
    intervention_id: int
    run_id: Optional[int] = None
    event_type: SupportPlanFeedbackEventType
    source: str = Field(min_length=1, max_length=100)
    recommendation_kind: SupportPlanRecommendationKind
    recommendation_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class SupportPlanFeedbackEventOut(BaseModel):
    id: int
    user_id: int
    run_id: Optional[int] = None
    intervention_id: int
    event_type: SupportPlanFeedbackEventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: int
    user_id: int
    type: str
    content: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResourceOut(BaseModel):
    id: int
    persona_type: str
    category: str
    title: str
    description: str
    url: str

    model_config = {"from_attributes": True}
