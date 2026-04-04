from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


_NON_RESTRICTIVE_DIETARY_STYLES = {"", "none", "balanced", "omnivore"}
_PREP_EFFORT_SCORE = {"low": 2.4, "medium": 0.7, "high": -1.4}
_ALLERGY_ALIASES = {
    "peanut": "nuts",
    "peanuts": "nuts",
    "tree_nut": "nuts",
    "tree_nuts": "nuts",
    "nut": "nuts",
    "nuts": "nuts",
    "milk": "dairy",
    "lactose": "dairy",
    "gluten": "gluten",
    "wheat": "gluten",
    "soybean": "soy",
}
_ALLERGY_KEYWORDS = {
    "nuts": {"nut", "nuts", "walnut", "walnuts", "almond", "almonds", "peanut", "peanuts", "cashew", "cashews"},
    "dairy": {"milk", "yogurt", "cheese", "butter", "cream", "whey"},
    "soy": {"soy", "soybean", "tofu", "edamame", "tempeh"},
    "gluten": {"bread", "wheat", "flour", "pasta", "noodle", "breadcrumbs"},
    "egg": {"egg", "eggs", "mayonnaise"},
}
_MEAT_KEYWORDS = {
    "beef",
    "chicken",
    "pork",
    "turkey",
    "ham",
    "bacon",
    "salmon",
    "tuna",
    "shrimp",
    "fish",
    "sausage",
}


class RecipeLike(Protocol):
    id: int | None
    title: str
    tags: Sequence[str] | None
    ingredients: Sequence[Any] | None
    prep_effort: str | None
    prep_minutes: int | None
    cook_minutes: int | None
    calories: int | None
    protein_grams: float | None


@dataclass(frozen=True)
class RecipeRankingContext:
    profile: Mapping[str, Any] = field(default_factory=dict)
    dynamic_state: Mapping[str, Any] = field(default_factory=dict)
    archetype_scores: Mapping[str, Any] = field(default_factory=dict)
    feature_windows: Mapping[str, Any] = field(default_factory=dict)
    recent_checkins: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    calorie_summary: Mapping[str, Any] = field(default_factory=dict)
    recipe_history: Mapping[str, Any] = field(default_factory=dict)
    intervention_history: Mapping[str, Any] = field(default_factory=dict)
    signals: Mapping[str, Any] = field(default_factory=dict)
    carried_constraints: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class RecipePreferenceProfile:
    dietary_style: str
    allergies: tuple[str, ...]
    weighted_tags: Mapping[str, float]
    derived_constraints: tuple[str, ...]
    recent_recipe_ids: tuple[int, ...]
    low_prep_priority: bool
    high_protein_priority: bool
    light_meal_priority: bool
    fuel_meal_priority: bool


@dataclass(frozen=True)
class RankedRecipe:
    recipe: RecipeLike
    score: float
    components: Mapping[str, float]
    matched_tags: tuple[str, ...]


def build_recipe_ranking_context(
    *,
    profile: Mapping[str, Any] | None = None,
    dynamic_state: Mapping[str, Any] | None = None,
    archetype_scores: Mapping[str, Any] | None = None,
    feature_windows: Mapping[str, Any] | None = None,
    recent_checkins: Sequence[Mapping[str, Any]] | None = None,
    calorie_summary: Mapping[str, Any] | None = None,
    recipe_history: Mapping[str, Any] | None = None,
    intervention_history: Mapping[str, Any] | None = None,
    signals: Mapping[str, Any] | None = None,
    carried_constraints: Sequence[str] | None = None,
) -> RecipeRankingContext:
    return RecipeRankingContext(
        profile=dict(profile or {}),
        dynamic_state=dict(dynamic_state or {}),
        archetype_scores=dict(archetype_scores or {}),
        feature_windows=dict(feature_windows or {}),
        recent_checkins=tuple(recent_checkins or ()),
        calorie_summary=dict(calorie_summary or {}),
        recipe_history=dict(recipe_history or {}),
        intervention_history=dict(intervention_history or {}),
        signals=dict(signals or {}),
        carried_constraints=tuple(carried_constraints or ()),
    )


def derive_meal_constraints(context: RecipeRankingContext) -> list[str]:
    return list(build_recipe_preference_profile(context).derived_constraints)


def summarize_recipe_preferences(context: RecipeRankingContext) -> dict[str, Any]:
    preferences = build_recipe_preference_profile(context)
    return {
        "derived_constraints": list(preferences.derived_constraints),
        "weighted_tags": {
            tag: round(weight, 2)
            for tag, weight in sorted(
                preferences.weighted_tags.items(),
                key=lambda item: (-item[1], item[0]),
            )
        },
        "priorities": {
            "low_prep": preferences.low_prep_priority,
            "high_protein": preferences.high_protein_priority,
            "light_meal": preferences.light_meal_priority,
            "fuel_meal": preferences.fuel_meal_priority,
        },
        "recent_recipe_ids": list(preferences.recent_recipe_ids),
    }


def rank_recipes(
    recipes: Sequence[RecipeLike],
    context: RecipeRankingContext,
    *,
    limit: int | None = None,
) -> list[RankedRecipe]:
    preferences = build_recipe_preference_profile(context)
    ranked = [_score_recipe(recipe, preferences) for recipe in recipes]
    ranked.sort(
        key=lambda item: (
            -item.score,
            _recipe_sort_id(item.recipe),
            str(getattr(item.recipe, "title", "")).lower(),
        )
    )
    return ranked[:limit] if limit is not None else ranked


def build_recipe_preference_profile(context: RecipeRankingContext) -> RecipePreferenceProfile:
    profile = dict(context.profile or {})
    accessibility = dict(profile.get("accessibility") or {})
    dynamic_state = dict(context.dynamic_state or {})
    archetype_scores = dict(context.archetype_scores or {})
    signals = dict(context.signals or {})
    carried_constraints = {_normalize_tag(item) for item in context.carried_constraints if _normalize_tag(item)}

    dietary_style = _normalize_tag(profile.get("dietary_style"))
    goal = _normalize_tag(profile.get("goal"))
    allergies = tuple(
        sorted(
            {
                canonical
                for raw in profile.get("allergies", []) or []
                if (canonical := _canonicalize_allergy(raw)) is not None
            }
        )
    )

    stress_load = _safe_float(dynamic_state.get("stress_load"), _safe_float(signals.get("stress_level")) / 10.0)
    sleep_debt = _safe_float(
        dynamic_state.get("sleep_debt"),
        max(0.0, (8.0 - _safe_float(signals.get("sleep_hours"), 8.0)) / 4.0),
    )
    prep_capacity = _safe_float(dynamic_state.get("prep_capacity"), 0.5)
    activity_capacity = _safe_float(dynamic_state.get("activity_capacity"), 0.5)
    calorie_balance = int(_safe_float(dynamic_state.get("calorie_balance"), 0.0))
    low_energy_recovery = _safe_float(archetype_scores.get("low_energy_recovery"), 0.0)
    student_overload = _safe_float(archetype_scores.get("student_overload"), 0.0)
    caregiver_burden = _safe_float(archetype_scores.get("caregiver_burden"), 0.0)
    performance_ready = _safe_float(archetype_scores.get("performance_ready"), 0.0)
    protein_gap = _safe_float(dynamic_state.get("protein_gap"), 0.0)

    low_prep_priority = bool(
        accessibility.get("low_energy_mode")
        or prep_capacity <= 0.45
        or stress_load >= 0.7
        or student_overload >= 0.6
        or caregiver_burden >= 0.6
        or "low_prep" in carried_constraints
    )
    high_protein_priority = bool(
        protein_gap >= 0.25
        or sleep_debt >= 0.45
        or low_energy_recovery >= 0.55
        or performance_ready >= 0.65
        or goal in {"muscle_gain", "strength", "performance", "fat_loss"}
        or "high_protein" in carried_constraints
    )
    comforting_priority = bool(
        stress_load >= 0.65
        or student_overload >= 0.6
        or caregiver_burden >= 0.6
        or "comforting" in carried_constraints
    )
    hydration_priority = bool(
        sleep_debt >= 0.45
        or low_energy_recovery >= 0.55
        or "hydration_support" in carried_constraints
    )
    light_meal_priority = bool(
        calorie_balance >= 250
        or activity_capacity <= 0.45
        or "light" in carried_constraints
    )
    fuel_meal_priority = bool(
        calorie_balance <= -250
        or performance_ready >= 0.65
        or _safe_float(signals.get("steps"), 0.0) >= 10000
        or "high_calorie" in carried_constraints
    )

    weighted_tags: dict[str, float] = {}
    derived_constraints: list[str] = []

    def add_constraint(tag: str, weight: float, *, include_in_constraints: bool = True) -> None:
        normalized = _normalize_tag(tag)
        if not normalized:
            return
        weighted_tags[normalized] = round(weighted_tags.get(normalized, 0.0) + weight, 3)
        if include_in_constraints and normalized not in derived_constraints:
            derived_constraints.append(normalized)

    for tag in sorted(carried_constraints):
        add_constraint(tag, 0.85, include_in_constraints=False)

    if dietary_style not in _NON_RESTRICTIVE_DIETARY_STYLES:
        add_constraint(dietary_style, 1.4)
    for allergy in allergies:
        add_constraint(f"avoid_{allergy}", 1.8)
    if low_prep_priority:
        add_constraint("low_prep", 2.4)
    if comforting_priority:
        add_constraint("comforting", 1.25)
    if hydration_priority:
        add_constraint("hydration_support", 1.2)
    if high_protein_priority:
        add_constraint("high_protein", 1.35)
    if light_meal_priority:
        add_constraint("light", 0.8)
    if fuel_meal_priority:
        add_constraint("high_calorie", 0.9)

    recent_recipe_ids = _unique_ints(
        [
            *(context.recipe_history.get("recent_meal_plan_recipe_ids", []) or []),
            *(context.recipe_history.get("recent_intervention_recipe_ids", []) or []),
            *(context.intervention_history.get("recent_recipe_ids", []) or []),
        ]
    )

    return RecipePreferenceProfile(
        dietary_style=dietary_style,
        allergies=allergies,
        weighted_tags=weighted_tags,
        derived_constraints=tuple(derived_constraints),
        recent_recipe_ids=recent_recipe_ids,
        low_prep_priority=low_prep_priority,
        high_protein_priority=high_protein_priority,
        light_meal_priority=light_meal_priority,
        fuel_meal_priority=fuel_meal_priority,
    )


def _score_recipe(recipe: RecipeLike, preferences: RecipePreferenceProfile) -> RankedRecipe:
    tags = {_normalize_tag(tag) for tag in getattr(recipe, "tags", []) or [] if _normalize_tag(tag)}
    components = {
        "tag_alignment": round(sum(preferences.weighted_tags.get(tag, 0.0) for tag in tags), 3),
        "allergy_guard": _score_allergy_fit(recipe, preferences, tags=tags),
        "dietary_fit": _score_dietary_fit(recipe, preferences, tags=tags),
        "prep_fit": _score_prep_fit(recipe, preferences),
        "nutrition_fit": _score_nutrition_fit(recipe, preferences),
        "variety": _score_variety(recipe, preferences),
    }
    total = round(sum(components.values()), 3)
    return RankedRecipe(
        recipe=recipe,
        score=total,
        components=components,
        matched_tags=tuple(sorted(tag for tag in tags if tag in preferences.weighted_tags)),
    )


def _score_allergy_fit(
    recipe: RecipeLike,
    preferences: RecipePreferenceProfile,
    *,
    tags: set[str],
) -> float:
    score = 0.0
    ingredients = _ingredient_names(recipe)
    for allergy in preferences.allergies:
        if f"avoid_{allergy}" in tags:
            score += 1.25
        keywords = _ALLERGY_KEYWORDS.get(allergy, set())
        if keywords and _ingredients_contain(ingredients, keywords):
            score -= 4.0
    return round(score, 3)


def _score_dietary_fit(recipe: RecipeLike, preferences: RecipePreferenceProfile, *, tags: set[str]) -> float:
    dietary_style = preferences.dietary_style
    if dietary_style in _NON_RESTRICTIVE_DIETARY_STYLES:
        return 0.0

    ingredients = _ingredient_names(recipe)
    if dietary_style == "vegetarian":
        if _ingredients_contain(ingredients, _MEAT_KEYWORDS):
            return -3.0
        if "vegetarian" in tags:
            return 1.0
        return 0.0

    if dietary_style == "vegan":
        if _ingredients_contain(ingredients, _MEAT_KEYWORDS):
            return -3.5
        if _ingredients_contain(ingredients, _ALLERGY_KEYWORDS["dairy"]) or _ingredients_contain(
            ingredients, _ALLERGY_KEYWORDS["egg"]
        ):
            return -3.0
        if "vegan" in tags or "avoid_dairy" in tags:
            return 1.0
        return 0.0

    if dietary_style == "dairy_free":
        if _ingredients_contain(ingredients, _ALLERGY_KEYWORDS["dairy"]):
            return -3.0
        if "avoid_dairy" in tags:
            return 1.0

    return 0.0


def _score_prep_fit(recipe: RecipeLike, preferences: RecipePreferenceProfile) -> float:
    if not preferences.low_prep_priority:
        return 0.0

    prep_effort = _normalize_tag(getattr(recipe, "prep_effort", "")) or "low"
    total_minutes = _recipe_total_minutes(recipe)
    score = _PREP_EFFORT_SCORE.get(prep_effort, 0.0)
    if total_minutes <= 10:
        score += 0.9
    elif total_minutes <= 20:
        score += 0.4
    elif total_minutes >= 30:
        score -= 0.8
    return round(score, 3)


def _score_nutrition_fit(recipe: RecipeLike, preferences: RecipePreferenceProfile) -> float:
    score = 0.0
    protein = _safe_float(getattr(recipe, "protein_grams", None), 0.0)
    calories = _safe_float(getattr(recipe, "calories", None), 0.0)

    if preferences.high_protein_priority:
        if protein >= 20:
            score += 1.4
        elif protein >= 15:
            score += 0.8
        elif protein > 0:
            score += 0.2

    if preferences.light_meal_priority and calories > 0:
        if calories <= 400:
            score += 0.75
        elif calories >= 550:
            score -= 0.35

    if preferences.fuel_meal_priority and calories > 0:
        if calories >= 350:
            score += 0.55
        if protein >= 20:
            score += 0.4

    return round(score, 3)


def _score_variety(recipe: RecipeLike, preferences: RecipePreferenceProfile) -> float:
    recipe_id = getattr(recipe, "id", None)
    if recipe_id is not None and recipe_id in preferences.recent_recipe_ids:
        return -1.25
    return 0.0


def _ingredient_names(recipe: RecipeLike) -> list[str]:
    names: list[str] = []
    for item in getattr(recipe, "ingredients", []) or []:
        if isinstance(item, Mapping):
            value = str(item.get("name", "")).strip().lower()
        else:
            value = str(item).strip().lower()
        if value:
            names.append(value)
    return names


def _ingredients_contain(ingredients: Sequence[str], keywords: set[str]) -> bool:
    for ingredient in ingredients:
        for keyword in keywords:
            if keyword in ingredient:
                return True
    return False


def _recipe_total_minutes(recipe: RecipeLike) -> int:
    prep = int(getattr(recipe, "prep_minutes", 0) or 0)
    cook = int(getattr(recipe, "cook_minutes", 0) or 0)
    return prep + cook


def _recipe_sort_id(recipe: RecipeLike) -> int:
    recipe_id = getattr(recipe, "id", None)
    return recipe_id if isinstance(recipe_id, int) else 10**9


def _normalize_tag(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _canonicalize_allergy(value: Any) -> str | None:
    normalized = _normalize_tag(value)
    if not normalized:
        return None
    return _ALLERGY_ALIASES.get(normalized, normalized)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _unique_ints(values: Sequence[Any]) -> tuple[int, ...]:
    seen: set[int] = set()
    ordered: list[int] = []
    for item in values:
        if not isinstance(item, int) or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return tuple(ordered)
