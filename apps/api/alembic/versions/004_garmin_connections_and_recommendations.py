"""Garmin connections, meal_constraints on interventions, is_template on recipes

Revision ID: 004
Revises: 003
Create Date: 2026-03-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── garmin_connections ─────────────────────────────────────────────────
    op.create_table(
        "garmin_connections",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("garmin_email", sa.String(255), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # ── interventions: add meal_constraints ────────────────────────────────
    op.add_column(
        "interventions",
        sa.Column(
            "meal_constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )

    # ── recipes: add is_template + make user_id nullable ───────────────────
    op.add_column(
        "recipes",
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("recipes", "user_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("recipes", "user_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("recipes", "is_template")
    op.drop_column("interventions", "meal_constraints")
    op.drop_table("garmin_connections")
