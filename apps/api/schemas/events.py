from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IngestEventRequest(BaseModel):
    signal_type: str  # sleep_hours|sleep_quality|stress_level|heart_rate|steps|activity_level|check_in_mood|check_in_note
    value: str
    unit: str = ""
    source: str = "manual"  # manual|simulated|garmin_future
    recorded_at: Optional[datetime] = None


class SimulateRequest(BaseModel):
    scenario: str  # stressed_student|exhausted_caregiver|older_adult


class CheckInRequest(BaseModel):
    mood: int = Field(ge=1, le=10)           # 1-10
    sleep_hours: float = Field(ge=0, le=24)  # 0-24
    stress: int = Field(ge=0, le=100)        # 0-100 (frontend percentage scale; stored as 1-10 in signal)
    note: str = ""


class WearableEventOut(BaseModel):
    id: int
    user_id: int
    source: str
    signal_type: str
    value: str
    unit: str
    recorded_at: datetime

    model_config = {"from_attributes": True}


class NormalizedEventOut(BaseModel):
    id: int
    user_id: int
    signals: Dict[str, Any]
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}
