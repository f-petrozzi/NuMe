from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HealthOverviewOut(BaseModel):
    latest_date: Optional[str]
    steps: int
    step_goal: int
    active_calories: int
    total_calories: int
    resting_hr: int
    avg_hr: int
    body_battery_high: int
    body_battery_low: int
    stress_avg: int
    active_minutes: int
    sleep_hours: float
    sleep_score: int
    garmin_connected: bool


class DailyMetricsOut(BaseModel):
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

    model_config = {"from_attributes": True}


class SleepSessionOut(BaseModel):
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

    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
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

    model_config = {"from_attributes": True}


class GarminAuthStatus(BaseModel):
    connected: bool
    user_id: Optional[int]
    garmin_email: Optional[str] = None
    last_sync: Optional[datetime]


class GarminConnectIn(BaseModel):
    email: str
    password: str


class CalorieLogIn(BaseModel):
    log_date: date
    meal_type: str
    food_name: str
    calories: int
    quantity: str = "1 serving"
    notes: str = ""
    ai_estimated: bool = False


class CalorieLogOut(BaseModel):
    id: int
    user_id: int
    log_date: date
    meal_type: str
    food_name: str
    calories: int
    quantity: str
    notes: str
    ai_estimated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CalorieEstimateRequest(BaseModel):
    food_name: str
    quantity: str = "1 serving"


class CalorieEstimateOut(BaseModel):
    food_name: str
    quantity: str
    estimated_calories: int
    confidence: str
