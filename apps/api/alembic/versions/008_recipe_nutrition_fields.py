"""Add nutrition and effort fields to recipes

Revision ID: 008
Revises: 007
Create Date: 2026-04-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("calories", sa.Integer(), nullable=True))
    op.add_column("recipes", sa.Column("protein_grams", sa.Float(), nullable=True))
    op.add_column("recipes", sa.Column("carbs_grams", sa.Float(), nullable=True))
    op.add_column("recipes", sa.Column("fat_grams", sa.Float(), nullable=True))
    op.add_column("recipes", sa.Column("fiber_grams", sa.Float(), nullable=True))
    op.add_column("recipes", sa.Column("prep_effort", sa.String(length=20), nullable=True))
    op.add_column(
        "recipes",
        sa.Column(
            "equipment_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("recipes", sa.Column("cost_level", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "cost_level")
    op.drop_column("recipes", "equipment_tags")
    op.drop_column("recipes", "prep_effort")
    op.drop_column("recipes", "fiber_grams")
    op.drop_column("recipes", "fat_grams")
    op.drop_column("recipes", "carbs_grams")
    op.drop_column("recipes", "protein_grams")
    op.drop_column("recipes", "calories")
