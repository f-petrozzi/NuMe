"""Add personalization snapshots and structured intervention metadata

Revision ID: 007
Revises: 006
Create Date: 2026-04-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "personalization_state_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="live_checkin"),
        sa.Column(
            "profile_static",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "dynamic_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "archetype_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "feature_windows",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "inputs_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_personalization_state_snapshots_user_id",
        "personalization_state_snapshots",
        ["user_id"],
    )
    op.create_index(
        "ix_personalization_state_snapshots_run_id",
        "personalization_state_snapshots",
        ["run_id"],
    )

    op.add_column("interventions", sa.Column("state_snapshot_id", sa.Integer(), nullable=True))
    op.add_column("interventions", sa.Column("recipe_id", sa.Integer(), nullable=True))
    op.add_column("interventions", sa.Column("activity_template_id", sa.Integer(), nullable=True))
    op.add_column("interventions", sa.Column("wellness_template_id", sa.Integer(), nullable=True))
    op.add_column(
        "interventions",
        sa.Column("risk_subscores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "interventions",
        sa.Column("why_chosen", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "interventions",
        sa.Column("alternatives_considered", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "interventions",
        sa.Column("why_changed_from_previous", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_foreign_key(
        "fk_interventions_state_snapshot_id",
        "interventions",
        "personalization_state_snapshots",
        ["state_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_interventions_recipe_id",
        "interventions",
        "recipes",
        ["recipe_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_interventions_state_snapshot_id", "interventions", ["state_snapshot_id"])
    op.create_index("ix_interventions_recipe_id", "interventions", ["recipe_id"])
    op.create_index("ix_interventions_activity_template_id", "interventions", ["activity_template_id"])
    op.create_index("ix_interventions_wellness_template_id", "interventions", ["wellness_template_id"])


def downgrade() -> None:
    op.drop_index("ix_interventions_wellness_template_id", table_name="interventions")
    op.drop_index("ix_interventions_activity_template_id", table_name="interventions")
    op.drop_index("ix_interventions_recipe_id", table_name="interventions")
    op.drop_index("ix_interventions_state_snapshot_id", table_name="interventions")

    op.drop_constraint("fk_interventions_recipe_id", "interventions", type_="foreignkey")
    op.drop_constraint("fk_interventions_state_snapshot_id", "interventions", type_="foreignkey")

    op.drop_column("interventions", "why_changed_from_previous")
    op.drop_column("interventions", "alternatives_considered")
    op.drop_column("interventions", "why_chosen")
    op.drop_column("interventions", "risk_subscores")
    op.drop_column("interventions", "wellness_template_id")
    op.drop_column("interventions", "activity_template_id")
    op.drop_column("interventions", "recipe_id")
    op.drop_column("interventions", "state_snapshot_id")

    op.drop_index("ix_personalization_state_snapshots_run_id", table_name="personalization_state_snapshots")
    op.drop_index("ix_personalization_state_snapshots_user_id", table_name="personalization_state_snapshots")
    op.drop_table("personalization_state_snapshots")
