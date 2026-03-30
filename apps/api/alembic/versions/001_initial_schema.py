"""Initial schema — all NüMe tables

Revision ID: 001
Revises:
Create Date: 2026-03-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── user_profiles ──────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("age_range", sa.String(20), nullable=False, server_default=""),
        sa.Column("sex", sa.String(10), nullable=False, server_default=""),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("goal", sa.String(50), nullable=False, server_default=""),
        sa.Column("activity_level", sa.String(30), nullable=False, server_default=""),
        sa.Column("dietary_style", sa.String(50), nullable=False, server_default=""),
        sa.Column("allergies", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("persona_type", sa.String(30), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # ── accessibility_preferences ──────────────────────────────────────────
    op.create_table(
        "accessibility_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("simplified_language", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("large_text", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("low_energy_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # ── wearable_events ────────────────────────────────────────────────────
    op.create_table(
        "wearable_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False, server_default=""),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wearable_events_user_id", "wearable_events", ["user_id"])

    # ── behavior_events ────────────────────────────────────────────────────
    op.create_table(
        "behavior_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_behavior_events_user_id", "behavior_events", ["user_id"])

    # ── normalized_events ──────────────────────────────────────────────────
    op.create_table(
        "normalized_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("signals", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_normalized_events_user_id", "normalized_events", ["user_id"])

    # ── agent_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("normalized_event_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["normalized_event_id"], ["normalized_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])

    # ── agent_messages ─────────────────────────────────────────────────────
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("agent_type", sa.String(20), nullable=False, server_default="local"),
        sa.Column("input", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_messages_run_id", "agent_messages", ["run_id"])

    # ── cases ──────────────────────────────────────────────────────────────
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cases_user_id", "cases", ["user_id"])

    # ── interventions ──────────────────────────────────────────────────────
    op.create_table(
        "interventions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("meal_suggestion", sa.Text(), nullable=False, server_default=""),
        sa.Column("activity_suggestion", sa.Text(), nullable=False, server_default=""),
        sa.Column("wellness_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("empathy_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interventions_user_id", "interventions", ["user_id"])

    # ── notifications ──────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # ── resources ──────────────────────────────────────────────────────────
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("persona_type", sa.String(30), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default=""),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("url", sa.String(500), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resources_persona_type", "resources", ["persona_type"])

    # ── audit_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(50), nullable=False, server_default=""),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── health_daily_metrics ───────────────────────────────────────────────
    op.create_table(
        "health_daily_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("step_goal", sa.Integer(), nullable=False, server_default="8000"),
        sa.Column("active_calories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_calories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resting_hr", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_hr", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("body_battery_high", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("body_battery_low", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stress_avg", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intensity_minutes_moderate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intensity_minutes_vigorous", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("floors_climbed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spo2_avg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("hrv_weekly_avg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("hrv_status", sa.String(50), nullable=False, server_default=""),
        sa.Column("vo2_max", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "metric_date", name="uq_daily_metrics_user_date"),
    )
    op.create_index("ix_health_daily_metrics_user_id", "health_daily_metrics", ["user_id"])

    # ── health_sleep_sessions ──────────────────────────────────────────────
    op.create_table(
        "health_sleep_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sleep_date", sa.Date(), nullable=False),
        sa.Column("sleep_start", sa.String(50), nullable=False, server_default=""),
        sa.Column("sleep_end", sa.String(50), nullable=False, server_default=""),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deep_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("light_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rem_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("awake_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sleep_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_spo2", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_respiration", sa.Float(), nullable=False, server_default="0"),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "sleep_date", name="uq_sleep_sessions_user_date"),
    )
    op.create_index("ix_health_sleep_sessions_user_id", "health_sleep_sessions", ["user_id"])

    # ── health_activities ──────────────────────────────────────────────────
    op.create_table(
        "health_activities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("garmin_activity_id", sa.String(50), nullable=False),
        sa.Column("activity_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("activity_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("start_time", sa.String(50), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distance_meters", sa.Float(), nullable=False, server_default="0"),
        sa.Column("calories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_hr", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_hr", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("elevation_gain_meters", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_speed_mps", sa.Float(), nullable=False, server_default="0"),
        sa.Column("training_load", sa.Float(), nullable=False, server_default="0"),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "garmin_activity_id", name="uq_activities_user_garmin_id"),
    )
    op.create_index("ix_health_activities_user_id", "health_activities", ["user_id"])

    # ── health_sync_runs ───────────────────────────────────────────────────
    op.create_table(
        "health_sync_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("sync_type", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activities_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sleep_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("details_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_sync_runs_user_id", "health_sync_runs", ["user_id"])

    # ── health_calorie_log ─────────────────────────────────────────────────
    op.create_table(
        "health_calorie_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False, server_default="snack"),
        sa.Column("food_name", sa.String(200), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity", sa.String(100), nullable=False, server_default="1 serving"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("ai_estimated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_calorie_log_user_id", "health_calorie_log", ["user_id"])

    # ── recipes ────────────────────────────────────────────────────────────
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_url", sa.String(1000), nullable=False, server_default=""),
        sa.Column("our_way_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("prep_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cook_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("servings", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("ingredients", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("photo_filename", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recipes_user_id", "recipes", ["user_id"])

    # ── meal_plan_slots ────────────────────────────────────────────────────
    op.create_table(
        "meal_plan_slots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column("custom_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meal_plan_slots_user_id", "meal_plan_slots", ["user_id"])


def downgrade() -> None:
    op.drop_table("meal_plan_slots")
    op.drop_table("recipes")
    op.drop_table("health_calorie_log")
    op.drop_table("health_sync_runs")
    op.drop_table("health_activities")
    op.drop_table("health_sleep_sessions")
    op.drop_table("health_daily_metrics")
    op.drop_table("audit_logs")
    op.drop_table("resources")
    op.drop_table("notifications")
    op.drop_table("interventions")
    op.drop_table("cases")
    op.drop_table("agent_messages")
    op.drop_table("agent_runs")
    op.drop_table("normalized_events")
    op.drop_table("behavior_events")
    op.drop_table("wearable_events")
    op.drop_table("accessibility_preferences")
    op.drop_table("user_profiles")
    op.drop_table("users")
