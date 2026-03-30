"""
Shared Pydantic v2 models for NüMe.
All teams import from here — do not duplicate these in service-specific code.

Usage:
    from packages.shared_types.models import UserProfile, NormalizedEvent, ...
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class PersonaType(str, Enum):
    student = "student"
    caregiver = "caregiver"
    older_adult = "older_adult"
    accessibility_focused = "accessibility_focused"


class GoalType(str, Enum):
    stress_reduction = "stress_reduction"
    better_sleep = "better_sleep"
    weight_loss = "weight_loss"
    energy_improvement = "energy_improvement"
    burnout_recovery = "burnout_recovery"


class SignalType(str, Enum):
    sleep_hours = "sleep_hours"
    sleep_quality = "sleep_quality"
    stress_level = "stress_level"
    heart_rate = "heart_rate"
    steps = "steps"
    activity_level = "activity_level"
    check_in_mood = "check_in_mood"
    check_in_note = "check_in_note"


class CaseStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class AgentType(str, Enum):
    local = "local"
    a2a = "a2a"
    parallel = "parallel"
    loop = "loop"


# ---------------------------------------------------------------------------
# User / Profile
# ---------------------------------------------------------------------------

class AccessibilityPreferences(BaseModel):
    user_id: int
    simplified_language: bool = False
    large_text: bool = False
    low_energy_mode: bool = False


class UserProfile(BaseModel):
    id: int
    user_id: int
    age_range: str
    sex: str
    height_cm: Optional[float]
    weight_kg: Optional[float]
    goal: GoalType
    activity_level: str
    dietary_style: str
    allergies: List[str] = []
    persona_type: PersonaType
    created_at: datetime
    accessibility: Optional[AccessibilityPreferences] = None


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class NormalizedEvent(BaseModel):
    id: int
    user_id: int
    signals: Dict[str, Any]
    summary: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Agent system
# ---------------------------------------------------------------------------

class AgentMessage(BaseModel):
    id: int
    run_id: int
    agent_name: str
    agent_type: AgentType
    input: Dict[str, Any]
    output: Dict[str, Any]
    iteration: int
    duration_ms: Optional[int]
    created_at: datetime


class AgentRunRecord(BaseModel):
    id: int
    user_id: int
    normalized_event_id: Optional[int]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    risk_level: str
    messages: List[AgentMessage] = []


class InterventionPlan(BaseModel):
    meal_suggestion: str
    activity_suggestion: str
    wellness_action: str
    empathy_message: str


class CaseRecord(BaseModel):
    id: int
    user_id: int
    run_id: Optional[int]
    risk_level: RiskLevel
    status: CaseStatus
    created_at: datetime
    updated_at: datetime


class NotificationRecord(BaseModel):
    id: int
    user_id: int
    type: str
    content: str
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthDailyMetrics(BaseModel):
    id: int
    user_id: int
    metric_date: date
    steps: int
    step_goal: int
    active_calories: int
    total_calories: int
    resting_hr: int
    avg_hr: int
    body_battery_high: int
    body_battery_low: int
    stress_avg: int
    intensity_minutes_moderate: int
    intensity_minutes_vigorous: int
    floors_climbed: int
    spo2_avg: float
    hrv_weekly_avg: float
    hrv_status: str
    vo2_max: float
    active_minutes: int
    synced_at: datetime


class HealthSleepSession(BaseModel):
    id: int
    user_id: int
    sleep_date: date
    sleep_start: str
    sleep_end: str
    duration_seconds: int
    deep_seconds: int
    light_seconds: int
    rem_seconds: int
    awake_seconds: int
    sleep_score: int
    avg_spo2: float
    avg_respiration: float
    synced_at: datetime


class HealthActivity(BaseModel):
    id: int
    user_id: int
    garmin_activity_id: str
    activity_type: str
    activity_name: str
    start_time: str
    duration_seconds: int
    distance_meters: float
    calories: int
    avg_hr: int
    max_hr: int
    elevation_gain_meters: float
    avg_speed_mps: float
    training_load: float
    synced_at: datetime


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------

class RecipeIngredient(BaseModel):
    name: str
    quantity: str = ""
    category: str = "Other"
    section: str = ""


class Recipe(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    source_url: str
    our_way_notes: str
    prep_minutes: int
    cook_minutes: int
    servings: int
    tags: List[str]
    ingredients: List[RecipeIngredient]
    instructions: str
    photo_filename: str
    created_at: datetime


class MealPlanSlot(BaseModel):
    id: int
    user_id: int
    plan_date: date
    meal_type: str
    recipe_id: Optional[int]
    custom_name: str
    notes: str
    created_at: datetime
