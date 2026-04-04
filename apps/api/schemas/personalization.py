from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PersonalizationContextOut(BaseModel):
    snapshot_id: int
    user_id: int
    run_id: Optional[int] = None
    scenario: str
    persona_type: str
    profile: Dict[str, Any]
    dynamic_state: Dict[str, Any]
    archetype_scores: Dict[str, float]
    feature_windows: Dict[str, Any]
    recent_checkins: List[Dict[str, Any]] = Field(default_factory=list)
    calorie_summary: Dict[str, Any] = Field(default_factory=dict)
    recipe_history: Dict[str, Any] = Field(default_factory=dict)
    intervention_history: Dict[str, Any] = Field(default_factory=dict)
    signals: Dict[str, Any] = Field(default_factory=dict)
    normalized_event_id: Optional[int] = None
