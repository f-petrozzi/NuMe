from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clerk_user_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    profile: Mapped["UserProfile | None"] = relationship("UserProfile", back_populates="user", uselist=False)
    accessibility: Mapped["AccessibilityPreferences | None"] = relationship(
        "AccessibilityPreferences", back_populates="user", uselist=False
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    age_range: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    sex: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    height_cm: Mapped[float | None] = mapped_column(nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    goal: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    activity_level: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    dietary_style: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    allergies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    persona_type: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")


class AccessibilityPreferences(Base):
    __tablename__ = "accessibility_preferences"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    simplified_language: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    large_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    low_energy_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="accessibility")
