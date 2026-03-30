from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
    meal_suggestion: str
    activity_suggestion: str
    wellness_action: str
    empathy_message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RunTraceOut(BaseModel):
    run: AgentRunOut
    messages: List[AgentMessageOut]
    intervention: Optional[InterventionOut] = None
    case: Optional[CaseOut] = None


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
