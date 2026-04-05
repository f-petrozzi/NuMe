from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

DEFAULT_ACTIVITY_TEMPLATES: list[dict[str, Any]] = [
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
        "metadata": {
            "goal_tags": ["stress_reduction", "better_sleep", "burnout_recovery"],
            "style_tags": ["walking", "reset", "recovery"],
        },
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
        "metadata": {
            "goal_tags": ["stress_reduction", "burnout_recovery", "general_wellness"],
            "style_tags": ["mobility", "indoor", "recovery"],
        },
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
        "metadata": {
            "goal_tags": ["stress_reduction", "energy_improvement", "weight_loss"],
            "style_tags": ["walking", "outdoor", "cardio"],
        },
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
        "metadata": {
            "goal_tags": ["energy_improvement", "performance", "weight_loss"],
            "style_tags": ["strength", "conditioning"],
        },
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
        "metadata": {
            "goal_tags": ["better_sleep", "stress_reduction"],
            "style_tags": ["stretch", "sleep_support"],
        },
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
        "metadata": {
            "goal_tags": ["general_wellness", "better_sleep", "stress_reduction"],
            "style_tags": ["mobility", "balance", "recovery"],
        },
        "active": True,
    },
]

DEFAULT_WELLNESS_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "Two-Minute Grounding Reset",
        "description": "A quick sensory grounding exercise for calming the nervous system when the day feels heavy.",
        "category": "grounding",
        "duration_minutes": 2,
        "accessibility_tags": ["low_energy_friendly", "small_space"],
        "time_cost_level": "low",
        "fatigue_sensitivity": "high",
        "metadata": {
            "goal_tags": ["stress_reduction", "burnout_recovery"],
            "style_tags": ["calming", "nervous_system"],
        },
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
        "metadata": {
            "goal_tags": ["stress_reduction", "better_sleep"],
            "style_tags": ["breathwork", "calming"],
        },
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
        "metadata": {
            "goal_tags": ["stress_reduction", "better_sleep"],
            "style_tags": ["journaling", "mental_offload"],
        },
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
        "metadata": {
            "goal_tags": ["better_sleep", "burnout_recovery"],
            "style_tags": ["sleep_support", "routine"],
        },
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
        "metadata": {
            "goal_tags": ["stress_reduction", "burnout_recovery", "general_wellness"],
            "style_tags": ["planning", "routine"],
        },
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
        "metadata": {
            "goal_tags": ["energy_improvement", "better_sleep", "general_wellness"],
            "style_tags": ["routine", "recovery"],
        },
        "active": True,
    },
]

_ACTIVITY_INTENSITY_MATRIX: dict[str, dict[str, float]] = {
    "very_low": {"very_low": 1.7, "low": 0.9, "moderate": -1.2},
    "low": {"very_low": 0.7, "low": 1.9, "moderate": 0.1},
    "moderate": {"very_low": -0.1, "low": 0.8, "moderate": 1.7},
}
_TIME_COST_WEIGHT = {"low": 1.1, "medium": 0.25, "high": -0.9}
_FATIGUE_WEIGHT = {"high": 1.0, "medium": 0.45, "low": -0.35}


class ActivityTemplateLike(Protocol):
    id: int | None
    title: str
    description: str
    duration_minutes: int | None
    intensity: str | None
    accessibility_tags: Sequence[str] | None
    equipment_tags: Sequence[str] | None
    time_cost_level: str | None
    fatigue_sensitivity: str | None
    contraindication_tags: Sequence[str] | None
    active: bool | None


class WellnessTemplateLike(Protocol):
    id: int | None
    title: str
    description: str
    category: str | None
    duration_minutes: int | None
    accessibility_tags: Sequence[str] | None
    time_cost_level: str | None
    fatigue_sensitivity: str | None
    active: bool | None


@dataclass(frozen=True)
class CatalogRankingContext:
    profile: Mapping[str, Any] = field(default_factory=dict)
    dynamic_state: Mapping[str, Any] = field(default_factory=dict)
    archetype_scores: Mapping[str, Any] = field(default_factory=dict)
    feature_windows: Mapping[str, Any] = field(default_factory=dict)
    recent_checkins: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    intervention_history: Mapping[str, Any] = field(default_factory=dict)
    signals: Mapping[str, Any] = field(default_factory=dict)
    risk_level: str = "low"


@dataclass(frozen=True)
class RankedCatalogItem:
    template: Any
    score: float
    components: Mapping[str, float]


def build_catalog_ranking_context(
    *,
    profile: Mapping[str, Any] | None = None,
    dynamic_state: Mapping[str, Any] | None = None,
    archetype_scores: Mapping[str, Any] | None = None,
    feature_windows: Mapping[str, Any] | None = None,
    recent_checkins: Sequence[Mapping[str, Any]] | None = None,
    intervention_history: Mapping[str, Any] | None = None,
    signals: Mapping[str, Any] | None = None,
    risk_level: str | None = None,
) -> CatalogRankingContext:
    return CatalogRankingContext(
        profile=dict(profile or {}),
        dynamic_state=dict(dynamic_state or {}),
        archetype_scores=dict(archetype_scores or {}),
        feature_windows=dict(feature_windows or {}),
        recent_checkins=tuple(recent_checkins or ()),
        intervention_history=dict(intervention_history or {}),
        signals=dict(signals or {}),
        risk_level=str(risk_level or "low"),
    )


def rank_activity_templates(
    templates: Sequence[ActivityTemplateLike | Mapping[str, Any]],
    context: CatalogRankingContext,
    *,
    limit: int | None = None,
) -> list[RankedCatalogItem]:
    ranked = [_score_activity_template(template, context) for template in templates if _is_active(template)]
    ranked.sort(
        key=lambda item: (
            -item.score,
            _item_id(item.template),
            _item_text(item.template, "title").lower(),
        )
    )
    return ranked[:limit] if limit is not None else ranked


def rank_wellness_templates(
    templates: Sequence[WellnessTemplateLike | Mapping[str, Any]],
    context: CatalogRankingContext,
    *,
    limit: int | None = None,
) -> list[RankedCatalogItem]:
    ranked = [_score_wellness_template(template, context) for template in templates if _is_active(template)]
    ranked.sort(
        key=lambda item: (
            -item.score,
            _item_id(item.template),
            _item_text(item.template, "title").lower(),
        )
    )
    return ranked[:limit] if limit is not None else ranked


def _score_activity_template(
    template: ActivityTemplateLike | Mapping[str, Any],
    context: CatalogRankingContext,
) -> RankedCatalogItem:
    profile = dict(context.profile or {})
    accessibility = dict(profile.get("accessibility") or {})
    dynamic_state = dict(context.dynamic_state or {})
    archetype_scores = dict(context.archetype_scores or {})
    intervention_history = dict(context.intervention_history or {})
    goal = _normalize_tag(profile.get("goal"))
    low_energy_mode = bool(accessibility.get("low_energy_mode", False))
    activity_capacity = _safe_float(dynamic_state.get("activity_capacity"), 0.5)
    stress_load = _safe_float(dynamic_state.get("stress_load"), _safe_float(context.signals.get("stress_level")) / 10.0)
    sleep_debt = _safe_float(dynamic_state.get("sleep_debt"), 0.0)
    performance_ready = _safe_float(archetype_scores.get("performance_ready"), 0.0)
    student_overload = _safe_float(archetype_scores.get("student_overload"), 0.0)
    caregiver_burden = _safe_float(archetype_scores.get("caregiver_burden"), 0.0)
    preferred_intensity = _preferred_activity_intensity(
        risk_level=context.risk_level,
        activity_capacity=activity_capacity,
        performance_ready=performance_ready,
    )
    preferred_duration = _preferred_activity_duration(
        risk_level=context.risk_level,
        activity_capacity=activity_capacity,
        low_energy_mode=low_energy_mode,
    )

    intensity = _normalize_tag(_item_value(template, "intensity", "low")) or "low"
    duration = max(1, int(_safe_float(_item_value(template, "duration_minutes", 10), 10.0)))
    metadata = _item_metadata(template)
    style_tags = {_normalize_tag(tag) for tag in metadata.get("style_tags", []) if _normalize_tag(tag)}
    goal_tags = {_normalize_tag(tag) for tag in metadata.get("goal_tags", []) if _normalize_tag(tag)}
    accessibility_tags = _item_tags(template, "accessibility_tags")
    equipment_tags = _item_tags(template, "equipment_tags")
    fatigue_sensitivity = _normalize_tag(_item_value(template, "fatigue_sensitivity", "medium")) or "medium"
    latest_activity_text = _latest_intervention_text(intervention_history, "activity_suggestion")

    components = {
        "intensity_fit": _ACTIVITY_INTENSITY_MATRIX.get(preferred_intensity, {}).get(intensity, 0.0),
        "duration_fit": _duration_fit(duration, preferred_duration),
        "fatigue_fit": _FATIGUE_WEIGHT.get(fatigue_sensitivity, 0.0) * (1.0 + max(stress_load, sleep_debt) * 0.4),
        "time_cost_fit": _TIME_COST_WEIGHT.get(_normalize_tag(_item_value(template, "time_cost_level", "low")), 0.0),
        "goal_fit": 1.0 if goal and goal in goal_tags else 0.0,
        "accessibility_fit": _accessibility_fit(
            accessibility_tags=accessibility_tags,
            equipment_tags=equipment_tags,
            low_energy_mode=low_energy_mode,
        ),
        "recovery_fit": _recovery_style_fit(
            style_tags=style_tags,
            stress_load=stress_load,
            sleep_debt=sleep_debt,
            student_overload=student_overload,
            caregiver_burden=caregiver_burden,
        ),
        "performance_fit": _performance_style_fit(style_tags=style_tags, performance_ready=performance_ready),
        "repetition_penalty": -0.8 if latest_activity_text and _item_text(template, "title").lower() in latest_activity_text else 0.0,
    }
    score = round(sum(components.values()), 3)
    return RankedCatalogItem(template=template, score=score, components=components)


def _score_wellness_template(
    template: WellnessTemplateLike | Mapping[str, Any],
    context: CatalogRankingContext,
) -> RankedCatalogItem:
    profile = dict(context.profile or {})
    accessibility = dict(profile.get("accessibility") or {})
    dynamic_state = dict(context.dynamic_state or {})
    intervention_history = dict(context.intervention_history or {})
    goal = _normalize_tag(profile.get("goal"))
    low_energy_mode = bool(accessibility.get("low_energy_mode", False))
    stress_load = _safe_float(dynamic_state.get("stress_load"), _safe_float(context.signals.get("stress_level")) / 10.0)
    sleep_debt = _safe_float(dynamic_state.get("sleep_debt"), 0.0)
    routine_stability = _safe_float(dynamic_state.get("routine_stability"), 0.5)
    latest_note_sentiment = _latest_note_sentiment(context.recent_checkins)
    preferred_duration = _preferred_wellness_duration(
        risk_level=context.risk_level,
        stress_load=stress_load,
        low_energy_mode=low_energy_mode,
    )

    category = _normalize_tag(_item_value(template, "category", "grounding")) or "grounding"
    duration = max(1, int(_safe_float(_item_value(template, "duration_minutes", 5), 5.0)))
    metadata = _item_metadata(template)
    goal_tags = {_normalize_tag(tag) for tag in metadata.get("goal_tags", []) if _normalize_tag(tag)}
    style_tags = {_normalize_tag(tag) for tag in metadata.get("style_tags", []) if _normalize_tag(tag)}
    accessibility_tags = _item_tags(template, "accessibility_tags")
    fatigue_sensitivity = _normalize_tag(_item_value(template, "fatigue_sensitivity", "medium")) or "medium"
    latest_wellness_text = _latest_intervention_text(intervention_history, "wellness_action")

    category_fit = 0.0
    if category in {"grounding", "breathing"} and stress_load >= 0.6:
        category_fit += 1.4
    if category == "sleep" and (sleep_debt >= 0.45 or goal == "better_sleep"):
        category_fit += 1.5
        if sleep_debt >= 0.45 and goal == "better_sleep":
            category_fit += 1.0
    if category in {"planning", "routine"} and routine_stability <= 0.45:
        category_fit += 1.0
    if category in {"grounding", "reflection"} and latest_note_sentiment < -0.15:
        category_fit += 0.55
    if goal and goal in goal_tags:
        category_fit += 0.75
    if category == "routine" and "routine" in style_tags:
        category_fit += 0.35

    components = {
        "category_fit": round(category_fit, 3),
        "duration_fit": _duration_fit(duration, preferred_duration),
        "fatigue_fit": _FATIGUE_WEIGHT.get(fatigue_sensitivity, 0.0) * (1.0 + max(stress_load, sleep_debt) * 0.35),
        "time_cost_fit": _TIME_COST_WEIGHT.get(_normalize_tag(_item_value(template, "time_cost_level", "low")), 0.0),
        "accessibility_fit": _wellness_accessibility_fit(
            accessibility_tags=accessibility_tags,
            low_energy_mode=low_energy_mode,
        ),
        "repetition_penalty": -0.7 if latest_wellness_text and _item_text(template, "title").lower() in latest_wellness_text else 0.0,
    }
    score = round(sum(components.values()), 3)
    return RankedCatalogItem(template=template, score=score, components=components)


def _preferred_activity_intensity(
    *,
    risk_level: str,
    activity_capacity: float,
    performance_ready: float,
) -> str:
    if risk_level in {"high", "critical"} or activity_capacity <= 0.35:
        return "very_low"
    if risk_level == "moderate" or activity_capacity <= 0.6 or performance_ready < 0.55:
        return "low"
    return "moderate"


def _preferred_activity_duration(
    *,
    risk_level: str,
    activity_capacity: float,
    low_energy_mode: bool,
) -> int:
    if risk_level in {"high", "critical"} or low_energy_mode or activity_capacity <= 0.35:
        return 10
    if risk_level == "moderate" or activity_capacity <= 0.6:
        return 15
    return 20


def _preferred_wellness_duration(
    *,
    risk_level: str,
    stress_load: float,
    low_energy_mode: bool,
) -> int:
    if risk_level in {"high", "critical"} or stress_load >= 0.7 or low_energy_mode:
        return 4
    if risk_level == "moderate" or stress_load >= 0.5:
        return 6
    return 10


def _duration_fit(duration: int, preferred_duration: int) -> float:
    if duration <= preferred_duration:
        return round(1.15 - ((preferred_duration - duration) / max(preferred_duration, 1)) * 0.35, 3)
    overage = duration - preferred_duration
    return round(max(-1.4, 0.4 - (overage * 0.22)), 3)


def _accessibility_fit(
    *,
    accessibility_tags: set[str],
    equipment_tags: set[str],
    low_energy_mode: bool,
) -> float:
    score = 0.0
    if low_energy_mode and {"low_energy_friendly", "chair_optional"} & accessibility_tags:
        score += 1.0
    if "small_space" in accessibility_tags:
        score += 0.25
    if low_energy_mode and not equipment_tags:
        score += 0.35
    if low_energy_mode and equipment_tags:
        score -= 0.55
    return round(score, 3)


def _wellness_accessibility_fit(
    *,
    accessibility_tags: set[str],
    low_energy_mode: bool,
) -> float:
    score = 0.0
    if low_energy_mode and "low_energy_friendly" in accessibility_tags:
        score += 0.95
    if {"small_space", "simplified_language_friendly"} & accessibility_tags:
        score += 0.25
    return round(score, 3)


def _recovery_style_fit(
    *,
    style_tags: set[str],
    stress_load: float,
    sleep_debt: float,
    student_overload: float,
    caregiver_burden: float,
) -> float:
    score = 0.0
    if {"recovery", "reset", "mobility"} & style_tags and max(stress_load, sleep_debt) >= 0.45:
        score += 0.75
    if "walking" in style_tags and max(student_overload, caregiver_burden) >= 0.55:
        score += 0.45
    if "sleep_support" in style_tags and sleep_debt >= 0.45:
        score += 0.35
    return round(score, 3)


def _performance_style_fit(*, style_tags: set[str], performance_ready: float) -> float:
    if performance_ready < 0.65:
        return 0.0
    if {"strength", "conditioning"} & style_tags:
        return round(0.85 + (performance_ready - 0.65), 3)
    return 0.0


def _latest_note_sentiment(recent_checkins: Sequence[Mapping[str, Any]]) -> float:
    if not recent_checkins:
        return 0.0
    return _safe_float(recent_checkins[0].get("note_sentiment"), 0.0)


def _latest_intervention_text(intervention_history: Mapping[str, Any], key: str) -> str:
    latest = dict(intervention_history.get("latest") or {})
    return str(latest.get(key, "")).strip().lower()


def _is_active(template: ActivityTemplateLike | WellnessTemplateLike | Mapping[str, Any]) -> bool:
    return bool(_item_value(template, "active", True))


def _item_id(template: ActivityTemplateLike | WellnessTemplateLike | Mapping[str, Any]) -> int:
    return int(_safe_float(_item_value(template, "id", 0), 0.0))


def _item_text(template: ActivityTemplateLike | WellnessTemplateLike | Mapping[str, Any], field_name: str) -> str:
    return str(_item_value(template, field_name, "")).strip()


def _item_tags(
    template: ActivityTemplateLike | WellnessTemplateLike | Mapping[str, Any],
    field_name: str,
) -> set[str]:
    raw = _item_value(template, field_name, []) or []
    return {_normalize_tag(item) for item in raw if _normalize_tag(item)}


def _item_metadata(template: ActivityTemplateLike | WellnessTemplateLike | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(template, Mapping):
        value = template.get("metadata") or template.get("metadata_json") or template.get("meta") or {}
    else:
        value = (
            getattr(template, "metadata_json", None)
            or getattr(template, "meta", None)
            or getattr(template, "metadata", None)
            or {}
        )
    return dict(value or {})


def _item_value(
    template: ActivityTemplateLike | WellnessTemplateLike | Mapping[str, Any],
    field_name: str,
    default: Any,
) -> Any:
    if isinstance(template, Mapping):
        return template.get(field_name, default)
    return getattr(template, field_name, default)


def _normalize_tag(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
