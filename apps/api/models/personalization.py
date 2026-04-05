from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class PersonalizationStateSnapshot(Base):
    __tablename__ = "personalization_state_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="live_checkin")
    profile_static: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dynamic_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    archetype_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    feature_windows: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    inputs_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class SupportPlanFeedbackEvent(Base):
    __tablename__ = "support_plan_feedback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    intervention_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interventions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ActivityTemplate(Base):
    __tablename__ = "activity_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    intensity: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    accessibility_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    equipment_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    time_cost_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    fatigue_sensitivity: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    contraindication_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class WellnessTemplate(Base):
    __tablename__ = "wellness_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="grounding")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    accessibility_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    time_cost_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    fatigue_sensitivity: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
