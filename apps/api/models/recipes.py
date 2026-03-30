from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    our_way_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prep_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cook_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{name, quantity, category, section}]
    ingredients: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    photo_filename: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class MealPlanSlot(Base):
    __tablename__ = "meal_plan_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # breakfast|lunch|dinner|snack
    recipe_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    custom_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
