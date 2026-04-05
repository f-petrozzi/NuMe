"""Add support plan feedback events

Revision ID: 010
Revises: 009
Create Date: 2026-04-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_plan_feedback_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("intervention_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["intervention_id"], ["interventions.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_support_plan_feedback_events_user_id",
        "support_plan_feedback_events",
        ["user_id"],
    )
    op.create_index(
        "ix_support_plan_feedback_events_run_id",
        "support_plan_feedback_events",
        ["run_id"],
    )
    op.create_index(
        "ix_support_plan_feedback_events_intervention_id",
        "support_plan_feedback_events",
        ["intervention_id"],
    )
    op.create_index(
        "ix_support_plan_feedback_events_event_type",
        "support_plan_feedback_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_support_plan_feedback_events_event_type", table_name="support_plan_feedback_events")
    op.drop_index("ix_support_plan_feedback_events_intervention_id", table_name="support_plan_feedback_events")
    op.drop_index("ix_support_plan_feedback_events_run_id", table_name="support_plan_feedback_events")
    op.drop_index("ix_support_plan_feedback_events_user_id", table_name="support_plan_feedback_events")
    op.drop_table("support_plan_feedback_events")
