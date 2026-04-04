from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecipeIngredient(BaseModel):
    name: str
    quantity: str = ""
    category: str = "Other"
    section: str = ""


class RecipeIn(BaseModel):
    title: str
    description: str = ""
    source_url: str = ""
    our_way_notes: str = ""
    prep_minutes: int = 0
    cook_minutes: int = 0
    servings: int = 2
    calories: Optional[int] = None
    protein_grams: Optional[float] = None
    carbs_grams: Optional[float] = None
    fat_grams: Optional[float] = None
    fiber_grams: Optional[float] = None
    prep_effort: Optional[str] = None
    equipment_tags: List[str] = Field(default_factory=list)
    cost_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    ingredients: List[RecipeIngredient] = Field(default_factory=list)
    instructions: str = ""
    photo_filename: str = ""


class RecipeOut(BaseModel):
    id: int
    user_id: Optional[int]
    title: str
    description: str
    source_url: str
    our_way_notes: str
    prep_minutes: int
    cook_minutes: int
    servings: int
    calories: Optional[int] = None
    protein_grams: Optional[float] = None
    carbs_grams: Optional[float] = None
    fat_grams: Optional[float] = None
    fiber_grams: Optional[float] = None
    prep_effort: Optional[str] = None
    equipment_tags: List[str] = Field(default_factory=list)
    cost_level: Optional[str] = None
    tags: List[str]
    ingredients: List[Dict[str, Any]]
    instructions: str
    photo_filename: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeParseUrlRequest(BaseModel):
    url: str


class RecipeParseTextRequest(BaseModel):
    text: str


class ParsedRecipe(BaseModel):
    title: str
    description: str = ""
    source_url: str = ""
    prep_minutes: int = 0
    cook_minutes: int = 0
    servings: int = 2
    calories: Optional[int] = None
    protein_grams: Optional[float] = None
    carbs_grams: Optional[float] = None
    fat_grams: Optional[float] = None
    fiber_grams: Optional[float] = None
    prep_effort: Optional[str] = None
    equipment_tags: List[str] = Field(default_factory=list)
    cost_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    ingredients: List[Dict[str, Any]] = Field(default_factory=list)
    instructions: str = ""
    photo_url: str = ""


class MealPlanSlotIn(BaseModel):
    plan_date: str  # YYYY-MM-DD
    meal_type: str  # breakfast|lunch|dinner|snack
    recipe_id: Optional[int] = None
    custom_name: str = ""
    notes: str = ""


class MealPlanSlotOut(BaseModel):
    id: int
    user_id: int
    plan_date: Any
    meal_type: str
    recipe_id: Optional[int]
    custom_name: str
    notes: str
    created_at: datetime
    recipe: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}
