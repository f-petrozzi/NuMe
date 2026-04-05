from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.agents import AgentRun, Intervention
from models.events import NormalizedEvent
from models.personalization import ActivityTemplate, PersonalizationStateSnapshot, WellnessTemplate
from models.recipes import Recipe
from models.user import User
from risk_scoring import build_deterministic_risk_assessment
from schemas.agents import (
    SupportPlanActivityOut,
    SupportPlanActivityTemplateOut,
    SupportPlanCurrentOut,
    SupportPlanMealOut,
    SupportPlanPlanOut,
    SupportPlanRecipeOut,
    SupportPlanRiskOut,
    SupportPlanRunOut,
    SupportPlanStateSnapshotOut,
    SupportPlanWellnessOut,
    SupportPlanWellnessTemplateOut,
)

_RISK_URGENCY_BY_LEVEL = {
    "critical": "immediate",
    "high": "today",
    "moderate": "next_day",
    "low": "routine",
}

_RISK_LABELS = {
    "physiological_strain": "Physiological strain",
    "emotional_strain": "Emotional strain",
    "recovery_debt": "Recovery debt",
    "adherence_risk": "Adherence risk",
}


async def build_current_support_plan(
    *,
    db: AsyncSession,
    user: User,
) -> SupportPlanCurrentOut:
    intervention = (
        (
            await db.execute(
                select(Intervention)
                .where(Intervention.user_id == user.id)
                .order_by(Intervention.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    if intervention is None:
        return _empty_support_plan()

    run = await _load_run(db=db, user_id=user.id, run_id=intervention.run_id)
    snapshot = await _load_snapshot(db=db, intervention=intervention, run=run)
    if run is None and snapshot is not None and snapshot.run_id is not None:
        run = await _load_run(db=db, user_id=user.id, run_id=snapshot.run_id)

    normalized_event = await _load_normalized_event(db=db, run=run)
    recipe = await _load_recipe(db=db, intervention=intervention)
    activity_template = await _load_activity_template(db=db, intervention=intervention)
    wellness_template = await _load_wellness_template(db=db, intervention=intervention)

    return SupportPlanCurrentOut(
        generated_at=intervention.created_at,
        run=_serialize_run(run) if run is not None else None,
        state_snapshot=_serialize_snapshot(snapshot) if snapshot is not None else None,
        risk=_build_risk(
            intervention=intervention,
            run=run,
            snapshot=snapshot,
            normalized_event=normalized_event,
        ),
        plan=_build_plan(
            intervention=intervention,
            recipe=recipe,
            activity_template=activity_template,
            wellness_template=wellness_template,
        ),
    )


async def _load_run(*, db: AsyncSession, user_id: int, run_id: int | None) -> AgentRun | None:
    if run_id is None:
        return None
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user_id).limit(1)
    )
    return result.scalar_one_or_none()


async def _load_snapshot(
    *,
    db: AsyncSession,
    intervention: Intervention,
    run: AgentRun | None,
) -> PersonalizationStateSnapshot | None:
    if intervention.state_snapshot_id is not None:
        snapshot = await db.get(PersonalizationStateSnapshot, intervention.state_snapshot_id)
        if snapshot is not None and snapshot.user_id == intervention.user_id:
            return snapshot

    if run is not None:
        result = await db.execute(
            select(PersonalizationStateSnapshot)
            .where(
                PersonalizationStateSnapshot.user_id == intervention.user_id,
                PersonalizationStateSnapshot.run_id == run.id,
            )
            .order_by(PersonalizationStateSnapshot.created_at.desc())
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is not None:
            return snapshot

    result = await db.execute(
        select(PersonalizationStateSnapshot)
        .where(PersonalizationStateSnapshot.user_id == intervention.user_id)
        .order_by(PersonalizationStateSnapshot.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _load_normalized_event(
    *,
    db: AsyncSession,
    run: AgentRun | None,
) -> NormalizedEvent | None:
    if run is None or run.normalized_event_id is None:
        return None
    return await db.get(NormalizedEvent, run.normalized_event_id)


async def _load_recipe(*, db: AsyncSession, intervention: Intervention) -> Recipe | None:
    if intervention.recipe_id is None:
        return None
    recipe = await db.get(Recipe, intervention.recipe_id)
    if recipe is None:
        return None
    if recipe.user_id not in {None, intervention.user_id}:
        return None
    return recipe


async def _load_activity_template(
    *,
    db: AsyncSession,
    intervention: Intervention,
) -> ActivityTemplate | None:
    if intervention.activity_template_id is None:
        return None
    template = await db.get(ActivityTemplate, intervention.activity_template_id)
    return template if template is not None and template.active else None


async def _load_wellness_template(
    *,
    db: AsyncSession,
    intervention: Intervention,
) -> WellnessTemplate | None:
    if intervention.wellness_template_id is None:
        return None
    template = await db.get(WellnessTemplate, intervention.wellness_template_id)
    return template if template is not None and template.active else None


def _empty_support_plan() -> SupportPlanCurrentOut:
    return SupportPlanCurrentOut(
        generated_at=datetime.now(timezone.utc),
        risk=SupportPlanRiskOut(
            level="low",
            urgency="routine",
            confidence=0.0,
            subscores={},
            drivers=[],
            rationale="No support plan has been generated for this member yet.",
        ),
        plan=None,
        run=None,
        state_snapshot=None,
    )


def _serialize_run(run: AgentRun) -> SupportPlanRunOut:
    return SupportPlanRunOut(
        id=run.id,
        status=run.status,
        risk_level=run.risk_level or "low",
        started_at=run.started_at,
        completed_at=run.completed_at,
        normalized_event_id=run.normalized_event_id,
    )


def _serialize_snapshot(snapshot: PersonalizationStateSnapshot) -> SupportPlanStateSnapshotOut:
    return SupportPlanStateSnapshotOut(
        id=snapshot.id,
        run_id=snapshot.run_id,
        source=snapshot.source,
        created_at=snapshot.created_at,
        dynamic_state=dict(snapshot.dynamic_state or {}),
        archetype_scores=dict(snapshot.archetype_scores or {}),
    )


def _build_risk(
    *,
    intervention: Intervention,
    run: AgentRun | None,
    snapshot: PersonalizationStateSnapshot | None,
    normalized_event: NormalizedEvent | None,
) -> SupportPlanRiskOut:
    if snapshot is None:
        level = str((run.risk_level if run is not None else "") or "low").strip() or "low"
        subscores = _normalize_subscores(intervention.risk_subscores)
        drivers = _drivers_from_subscores(subscores, fallback_level=level)
        return SupportPlanRiskOut(
            level=level,
            urgency=_RISK_URGENCY_BY_LEVEL.get(level, "routine"),
            confidence=0.0,
            subscores=subscores,
            drivers=drivers,
            rationale=(
                "Risk details are being reconstructed from the persisted support plan because the linked "
                "personalization snapshot is unavailable."
            ),
        )

    profile_static = dict(snapshot.profile_static or {})
    inputs_summary = dict(snapshot.inputs_summary or {})
    recent_checkins = _normalize_mapping_list(inputs_summary.get("recent_checkins"))
    risk_assessment = build_deterministic_risk_assessment(
        persona_type=str(profile_static.get("persona_type") or "older_adult"),
        signals=dict(normalized_event.signals or {}) if normalized_event is not None else {},
        dynamic_state=dict(snapshot.dynamic_state or {}),
        recent_checkins=recent_checkins,
        feature_windows=dict(snapshot.feature_windows or {}),
    )

    subscores = _normalize_subscores(intervention.risk_subscores or risk_assessment.get("subscores"))
    level = str(
        (run.risk_level if run is not None else "")
        or risk_assessment.get("risk_level")
        or "low"
    ).strip() or "low"
    return SupportPlanRiskOut(
        level=level,
        urgency=str(risk_assessment.get("urgency") or _RISK_URGENCY_BY_LEVEL.get(level, "routine")),
        confidence=_safe_float(risk_assessment.get("confidence"), default=0.0),
        subscores=subscores,
        drivers=[str(item).strip() for item in risk_assessment.get("drivers", []) if str(item).strip()],
        rationale=str(risk_assessment.get("rationale", "")).strip(),
    )


def _build_plan(
    *,
    intervention: Intervention,
    recipe: Recipe | None,
    activity_template: ActivityTemplate | None,
    wellness_template: WellnessTemplate | None,
) -> SupportPlanPlanOut:
    reasons = dict(intervention.why_chosen or {})
    alternatives = list(intervention.alternatives_considered or [])
    return SupportPlanPlanOut(
        intervention_id=intervention.id,
        created_at=intervention.created_at,
        meal=SupportPlanMealOut(
            recipe_id=intervention.recipe_id,
            title=recipe.title if recipe is not None else "Meal Suggestion",
            description=(
                recipe.description
                if recipe is not None and recipe.description
                else (intervention.meal_suggestion or "No meal suggestion available.")
            ),
            text=intervention.meal_suggestion,
            constraints=[str(item).strip() for item in intervention.meal_constraints or [] if str(item).strip()],
            why_chosen=_normalize_string_list(reasons.get("meal")),
            alternatives_considered=_filter_alternatives(alternatives, kind="meal"),
            recipe=_serialize_recipe(recipe) if recipe is not None else None,
        ),
        activity=SupportPlanActivityOut(
            template_id=intervention.activity_template_id,
            title=activity_template.title if activity_template is not None else "Activity Suggestion",
            description=(
                activity_template.description
                if activity_template is not None and activity_template.description
                else (intervention.activity_suggestion or "No activity suggestion available.")
            ),
            text=intervention.activity_suggestion,
            duration_minutes=activity_template.duration_minutes if activity_template is not None else None,
            intensity=activity_template.intensity if activity_template is not None else None,
            why_chosen=_normalize_string_list(reasons.get("activity")),
            alternatives_considered=_filter_alternatives(alternatives, kind="activity"),
            template=_serialize_activity_template(activity_template) if activity_template is not None else None,
        ),
        wellness=SupportPlanWellnessOut(
            template_id=intervention.wellness_template_id,
            title=wellness_template.title if wellness_template is not None else "Wellness Action",
            description=(
                wellness_template.description
                if wellness_template is not None and wellness_template.description
                else (intervention.wellness_action or "No wellness action available.")
            ),
            text=intervention.wellness_action,
            category=wellness_template.category if wellness_template is not None else None,
            why_chosen=_normalize_string_list(reasons.get("wellness")),
            alternatives_considered=_filter_alternatives(alternatives, kind="wellness"),
            template=_serialize_wellness_template(wellness_template) if wellness_template is not None else None,
        ),
        empathy_message=intervention.empathy_message,
        rationale=_build_plan_rationale(reasons),
        why_changed_from_previous=_normalize_string_list(intervention.why_changed_from_previous),
    )


def _serialize_recipe(recipe: Recipe) -> SupportPlanRecipeOut:
    return SupportPlanRecipeOut.model_validate(recipe)


def _serialize_activity_template(template: ActivityTemplate) -> SupportPlanActivityTemplateOut:
    return SupportPlanActivityTemplateOut(
        id=template.id,
        title=template.title,
        description=template.description,
        duration_minutes=template.duration_minutes,
        intensity=template.intensity,
        accessibility_tags=list(template.accessibility_tags or []),
        equipment_tags=list(template.equipment_tags or []),
        time_cost_level=template.time_cost_level,
        fatigue_sensitivity=template.fatigue_sensitivity,
        contraindication_tags=list(template.contraindication_tags or []),
        metadata=dict(template.metadata_json or {}),
    )


def _serialize_wellness_template(template: WellnessTemplate) -> SupportPlanWellnessTemplateOut:
    return SupportPlanWellnessTemplateOut(
        id=template.id,
        title=template.title,
        description=template.description,
        category=template.category,
        duration_minutes=template.duration_minutes,
        accessibility_tags=list(template.accessibility_tags or []),
        time_cost_level=template.time_cost_level,
        fatigue_sensitivity=template.fatigue_sensitivity,
        metadata=dict(template.metadata_json or {}),
    )


def _build_plan_rationale(reasons: Mapping[str, Any]) -> str:
    top_reasons: list[str] = []
    for key in ("meal", "activity", "wellness"):
        values = _normalize_string_list(reasons.get(key))
        if values:
            top_reasons.append(values[0])
    if top_reasons:
        return " ".join(top_reasons[:3])
    return "The current support plan keeps the recommendations aligned with the latest recovery, stress, and routine signals."


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes, dict)):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_mapping_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    normalized: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, Mapping):
            normalized.append(dict(value))
    return normalized


def _filter_alternatives(values: Iterable[Any], *, kind: str) -> list[Any]:
    alternatives: list[Any] = []
    for value in values:
        if isinstance(value, Mapping):
            value_kind = str(value.get("kind", "")).strip().lower()
            if value_kind == kind or (kind == "meal" and not value_kind):
                alternatives.append(dict(value))
            continue
        if kind == "meal":
            alternatives.append(value)
    return alternatives


def _normalize_subscores(values: Any) -> dict[str, float]:
    if not isinstance(values, Mapping):
        return {}
    normalized: dict[str, float] = {}
    for key, value in values.items():
        text_key = str(key).strip()
        if not text_key:
            continue
        normalized[text_key] = round(_safe_float(value), 3)
    return normalized


def _drivers_from_subscores(subscores: Mapping[str, float], *, fallback_level: str) -> list[str]:
    ranked = sorted(subscores.items(), key=lambda item: item[1], reverse=True)
    drivers = [
        f"{_RISK_LABELS.get(key, key.replace('_', ' ').title())} is elevated in the persisted support-plan record."
        for key, value in ranked
        if value >= 0.5
    ][:3]
    if drivers:
        return drivers
    if fallback_level != "low":
        return [f"The linked run is marked {fallback_level} risk."]
    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
