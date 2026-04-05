"""Add activity and wellness catalogs

Revision ID: 009
Revises: 008
Create Date: 2026-04-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("intensity", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column(
            "accessibility_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "equipment_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("time_cost_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("fatigue_sensitivity", sa.String(length=20), nullable=False, server_default="high"),
        sa.Column(
            "contraindication_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_activity_templates_active", "activity_templates", ["active"])

    op.create_table(
        "wellness_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="grounding"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "accessibility_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("time_cost_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("fatigue_sensitivity", sa.String(length=20), nullable=False, server_default="high"),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_wellness_templates_active", "wellness_templates", ["active"])

    activity_templates = sa.table(
        "activity_templates",
        sa.column("id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("duration_minutes", sa.Integer()),
        sa.column("intensity", sa.String()),
        sa.column("accessibility_tags", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("equipment_tags", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("time_cost_level", sa.String()),
        sa.column("fatigue_sensitivity", sa.String()),
        sa.column("contraindication_tags", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("active", sa.Boolean()),
    )
    op.bulk_insert(
        activity_templates,
        [
            {
                "id": 1,
                "title": "Ten-Minute Reset Walk",
                "description": "A short walk that lowers pressure and helps reset attention without turning the day into a workout.",
                "duration_minutes": 10,
                "intensity": "low",
                "accessibility_tags": ["low_energy_friendly", "outdoor_optional"],
                "equipment_tags": [],
                "time_cost_level": "low",
                "fatigue_sensitivity": "high",
                "contraindication_tags": [],
                "metadata": {"goal_tags": ["stress_reduction", "better_sleep", "burnout_recovery"], "style_tags": ["walking", "reset", "recovery"]},
                "active": True,
            },
            {
                "id": 2,
                "title": "Seated Mobility Reset",
                "description": "Gentle seated range-of-motion work for days when energy is low and standing effort needs to stay minimal.",
                "duration_minutes": 8,
                "intensity": "very_low",
                "accessibility_tags": ["chair_optional", "small_space", "low_energy_friendly"],
                "equipment_tags": [],
                "time_cost_level": "low",
                "fatigue_sensitivity": "high",
                "contraindication_tags": [],
                "metadata": {"goal_tags": ["stress_reduction", "burnout_recovery", "general_wellness"], "style_tags": ["mobility", "indoor", "recovery"]},
                "active": True,
            },
            {
                "id": 3,
                "title": "Fresh-Air Recovery Walk",
                "description": "A longer walk with a little more rhythm when the body can handle light movement and a mental reset.",
                "duration_minutes": 20,
                "intensity": "moderate",
                "accessibility_tags": ["outdoor_optional"],
                "equipment_tags": [],
                "time_cost_level": "medium",
                "fatigue_sensitivity": "medium",
                "contraindication_tags": [],
                "metadata": {"goal_tags": ["stress_reduction", "energy_improvement", "weight_loss"], "style_tags": ["walking", "outdoor", "cardio"]},
                "active": True,
            },
            {
                "id": 4,
                "title": "Bodyweight Energy Circuit",
                "description": "A compact bodyweight circuit for days with better recovery and enough capacity for a more energizing push.",
                "duration_minutes": 18,
                "intensity": "moderate",
                "accessibility_tags": ["small_space"],
                "equipment_tags": ["mat_optional"],
                "time_cost_level": "medium",
                "fatigue_sensitivity": "low",
                "contraindication_tags": [],
                "metadata": {"goal_tags": ["energy_improvement", "performance", "weight_loss"], "style_tags": ["strength", "conditioning"]},
                "active": True,
            },
            {
                "id": 5,
                "title": "Bedtime Stretch Downshift",
                "description": "An evening-friendly stretch flow designed to reduce physical tension and make winding down easier.",
                "duration_minutes": 12,
                "intensity": "very_low",
                "accessibility_tags": ["evening_friendly", "small_space"],
                "equipment_tags": ["mat_optional"],
                "time_cost_level": "low",
                "fatigue_sensitivity": "high",
                "contraindication_tags": [],
                "metadata": {"goal_tags": ["better_sleep", "stress_reduction"], "style_tags": ["stretch", "sleep_support"]},
                "active": True,
            },
            {
                "id": 6,
                "title": "Gentle Mobility Flow",
                "description": "A light standing mobility sequence for rebuilding consistency when the day can support a bit more movement.",
                "duration_minutes": 15,
                "intensity": "low",
                "accessibility_tags": ["small_space"],
                "equipment_tags": [],
                "time_cost_level": "medium",
                "fatigue_sensitivity": "medium",
                "contraindication_tags": [],
                "metadata": {"goal_tags": ["general_wellness", "better_sleep", "stress_reduction"], "style_tags": ["mobility", "balance", "recovery"]},
                "active": True,
            },
        ],
    )

    wellness_templates = sa.table(
        "wellness_templates",
        sa.column("id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("category", sa.String()),
        sa.column("duration_minutes", sa.Integer()),
        sa.column("accessibility_tags", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("time_cost_level", sa.String()),
        sa.column("fatigue_sensitivity", sa.String()),
        sa.column("metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("active", sa.Boolean()),
    )
    op.bulk_insert(
        wellness_templates,
        [
            {
                "id": 1,
                "title": "Two-Minute Grounding Reset",
                "description": "A quick sensory grounding exercise for calming the nervous system when the day feels heavy.",
                "category": "grounding",
                "duration_minutes": 2,
                "accessibility_tags": ["low_energy_friendly", "small_space"],
                "time_cost_level": "low",
                "fatigue_sensitivity": "high",
                "metadata": {"goal_tags": ["stress_reduction", "burnout_recovery"], "style_tags": ["calming", "nervous_system"]},
                "active": True,
            },
            {
                "id": 2,
                "title": "Box Breathing Break",
                "description": "A simple breathing pattern that can lower perceived stress without requiring extra setup.",
                "category": "breathing",
                "duration_minutes": 3,
                "accessibility_tags": ["low_energy_friendly", "small_space"],
                "time_cost_level": "low",
                "fatigue_sensitivity": "high",
                "metadata": {"goal_tags": ["stress_reduction", "better_sleep"], "style_tags": ["breathwork", "calming"]},
                "active": True,
            },
            {
                "id": 3,
                "title": "Five-Minute Brain Dump",
                "description": "Write down the loudest thoughts and next steps so they stop competing for attention.",
                "category": "reflection",
                "duration_minutes": 5,
                "accessibility_tags": ["simplified_language_friendly", "small_space"],
                "time_cost_level": "low",
                "fatigue_sensitivity": "medium",
                "metadata": {"goal_tags": ["stress_reduction", "better_sleep"], "style_tags": ["journaling", "mental_offload"]},
                "active": True,
            },
            {
                "id": 4,
                "title": "Digital Sunset Prep",
                "description": "A brief pre-sleep routine that reduces stimulation and makes bedtime more recoverable.",
                "category": "sleep",
                "duration_minutes": 10,
                "accessibility_tags": ["evening_friendly", "small_space"],
                "time_cost_level": "medium",
                "fatigue_sensitivity": "high",
                "metadata": {"goal_tags": ["better_sleep", "burnout_recovery"], "style_tags": ["sleep_support", "routine"]},
                "active": True,
            },
            {
                "id": 5,
                "title": "Next-Step Planning Reset",
                "description": "Choose one realistic next step and one thing to postpone so the rest of the day feels smaller.",
                "category": "planning",
                "duration_minutes": 5,
                "accessibility_tags": ["simplified_language_friendly", "low_energy_friendly"],
                "time_cost_level": "low",
                "fatigue_sensitivity": "medium",
                "metadata": {"goal_tags": ["stress_reduction", "burnout_recovery", "general_wellness"], "style_tags": ["planning", "routine"]},
                "active": True,
            },
            {
                "id": 6,
                "title": "Hydration and Daylight Pause",
                "description": "Pair a glass of water with a short daylight break to support energy and routine stability.",
                "category": "routine",
                "duration_minutes": 5,
                "accessibility_tags": ["low_energy_friendly", "outdoor_optional"],
                "time_cost_level": "low",
                "fatigue_sensitivity": "high",
                "metadata": {"goal_tags": ["energy_improvement", "better_sleep", "general_wellness"], "style_tags": ["routine", "recovery"]},
                "active": True,
            },
        ],
    )

    op.create_foreign_key(
        "fk_interventions_activity_template_catalog_id",
        "interventions",
        "activity_templates",
        ["activity_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_interventions_wellness_template_catalog_id",
        "interventions",
        "wellness_templates",
        ["wellness_template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_interventions_wellness_template_catalog_id", "interventions", type_="foreignkey")
    op.drop_constraint("fk_interventions_activity_template_catalog_id", "interventions", type_="foreignkey")
    op.drop_index("ix_wellness_templates_active", table_name="wellness_templates")
    op.drop_table("wellness_templates")
    op.drop_index("ix_activity_templates_active", table_name="activity_templates")
    op.drop_table("activity_templates")
