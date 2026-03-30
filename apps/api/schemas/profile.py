from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class OnboardingRequest(BaseModel):
    age_range: str
    sex: str
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: str
    activity_level: str
    dietary_style: str
    allergies: List[str] = []
    persona_type: str
    # accessibility (optional at onboarding)
    simplified_language: bool = False
    large_text: bool = False
    low_energy_mode: bool = False


class ProfileUpdate(BaseModel):
    age_range: Optional[str] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    activity_level: Optional[str] = None
    dietary_style: Optional[str] = None
    allergies: Optional[List[str]] = None
    persona_type: Optional[str] = None


class AccessibilityUpdate(BaseModel):
    simplified_language: Optional[bool] = None
    large_text: Optional[bool] = None
    low_energy_mode: Optional[bool] = None


class ProfileOut(BaseModel):
    id: int
    user_id: int
    age_range: str
    sex: str
    height_cm: Optional[float]
    weight_kg: Optional[float]
    goal: str
    activity_level: str
    dietary_style: str
    allergies: List[str]
    persona_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AccessibilityOut(BaseModel):
    user_id: int
    simplified_language: bool
    large_text: bool
    low_energy_mode: bool

    model_config = {"from_attributes": True}
