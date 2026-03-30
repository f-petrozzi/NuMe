from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class HealthDailyMetrics(Base):
    __tablename__ = "health_daily_metrics"
    __table_args__ = (UniqueConstraint("user_id", "metric_date", name="uq_daily_metrics_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_goal: Mapped[int] = mapped_column(Integer, nullable=False, default=8000)
    active_calories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_calories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resting_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body_battery_high: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body_battery_low: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stress_avg: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intensity_minutes_moderate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intensity_minutes_vigorous: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    floors_climbed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spo2_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hrv_weekly_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hrv_status: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    vo2_max: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class HealthSleepSession(Base):
    __tablename__ = "health_sleep_sessions"
    __table_args__ = (UniqueConstraint("user_id", "sleep_date", name="uq_sleep_sessions_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sleep_date: Mapped[date] = mapped_column(Date, nullable=False)
    sleep_start: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    sleep_end: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deep_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    light_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rem_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    awake_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sleep_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_spo2: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_respiration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class HealthActivity(Base):
    __tablename__ = "health_activities"
    __table_args__ = (UniqueConstraint("user_id", "garmin_activity_id", name="uq_activities_user_garmin_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    garmin_activity_id: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    activity_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    start_time: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distance_meters: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    elevation_gain_meters: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_speed_mps: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    training_load: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class HealthSyncRun(Base):
    __tablename__ = "health_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # running|success|partial|failed
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")  # scheduled|manual|startup
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activities_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sleep_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class GarminConnection(Base):
    """Per-user Garmin account linkage. Presence of token files on disk is the
    authoritative "connected" state; this row is the registry/metadata layer."""
    __tablename__ = "garmin_connections"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    garmin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HealthCalorieLog(Base):
    __tablename__ = "health_calorie_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False, default="snack")  # breakfast|lunch|dinner|snack
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    calories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[str] = mapped_column(String(100), nullable=False, default="1 serving")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ai_estimated: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
