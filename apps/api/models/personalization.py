from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
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
