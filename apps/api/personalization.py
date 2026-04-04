from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import fmean
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.agents import AgentRun, Intervention
from models.events import NormalizedEvent, WearableEvent
from models.health import HealthCalorieLog, HealthDailyMetrics, HealthSleepSession
from models.personalization import PersonalizationStateSnapshot
from models.recipes import MealPlanSlot
from models.user import AccessibilityPreferences, User, UserProfile

_NEGATIVE_NOTE_TOKENS = {
    "anxious",
    "behind",
    "burned out",
    "confused",
    "drained",
    "exhausted",
    "overwhelmed",
    "stressed",
    "tired",
    "worried",
}
_POSITIVE_NOTE_TOKENS = {
    "calm",
    "energized",
    "good",
    "great",
    "ok",
    "okay",
    "rested",
    "steady",
}
_MILD_NEGATIVE_MOODS = {"anxious", "confused", "drained", "exhausted", "overwhelmed", "stressed", "tired"}
_MILD_POSITIVE_MOODS = {"calm", "good", "great", "okay", "rested", "steady"}


def _scenario_persona(scenario: str) -> str:
    if scenario == "stressed_student":
        return "student"
    if scenario == "exhausted_caregiver":
        return "caregiver"
    return "older_adult"


def _default_profile(*, user_id: int, persona_type: str) -> dict[str, Any]:
    goal_map = {
        "student": "stress_reduction",
        "caregiver": "burnout_recovery",
        "older_adult": "general_wellness",
        "accessibility_focused": "stress_reduction",
    }
    return {
        "id": 0,
        "user_id": user_id,
        "age_range": "18-24" if persona_type == "student" else "35-44",
        "sex": "unspecified",
        "height_cm": 170.0,
        "weight_kg": 70.0,
        "goal": goal_map.get(persona_type, "stress_reduction"),
        "activity_level": "moderate",
        "dietary_style": "omnivore",
        "allergies": [],
        "persona_type": persona_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "accessibility": {
            "user_id": user_id,
            "simplified_language": persona_type == "accessibility_focused",
            "large_text": False,
            "low_energy_mode": persona_type in {"caregiver", "accessibility_focused"},
        },
    }


def _serialize_profile(
    profile: UserProfile | None,
    accessibility: AccessibilityPreferences | None,
    *,
    user_id: int,
    fallback_persona: str,
) -> dict[str, Any]:
    if profile is None:
        return _default_profile(user_id=user_id, persona_type=fallback_persona)

    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "age_range": profile.age_range,
        "sex": profile.sex,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "goal": profile.goal,
        "activity_level": profile.activity_level,
        "dietary_style": profile.dietary_style,
        "allergies": list(profile.allergies or []),
        "persona_type": profile.persona_type or fallback_persona,
        "created_at": profile.created_at.isoformat(),
        "accessibility": {
            "user_id": user_id,
            "simplified_language": bool(getattr(accessibility, "simplified_language", False)),
            "large_text": bool(getattr(accessibility, "large_text", False)),
            "low_energy_mode": bool(getattr(accessibility, "low_energy_mode", False)),
        },
    }


def _mean(values: Iterable[float], *, default: float = 0.0) -> float:
    values = list(values)
    if not values:
        return default
    return float(fmean(values))


def _clamp(value: float, *, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sentiment_score(note: str | None) -> float:
    text = (note or "").strip().lower()
    if not text:
        return 0.0

    score = 0.0
    for token in _NEGATIVE_NOTE_TOKENS:
        if token in text:
            score -= 1.0
    for token in _POSITIVE_NOTE_TOKENS:
        if token in text:
            score += 1.0
    return _clamp((score + 3.0) / 6.0, low=0.0, high=1.0) * 2.0 - 1.0


def _mood_score(raw_mood: Any) -> float | None:
    if raw_mood is None:
        return None

    numeric = _safe_float(raw_mood, default=-1.0)
    if numeric >= 0:
        if numeric > 10:
            numeric = 10.0
        return _clamp((numeric - 1.0) / 9.0)

    mood = str(raw_mood).strip().lower()
    if not mood:
        return None
    if mood in _MILD_POSITIVE_MOODS:
        return 0.75
    if mood in _MILD_NEGATIVE_MOODS:
        return 0.25
    return 0.5


def _window_metrics(metrics: list[HealthDailyMetrics], *, days: int) -> dict[str, Any]:
    subset = metrics[:days]
    if not subset:
        return {
            "days": days,
            "sample_count": 0,
            "steps_avg": 0.0,
            "stress_avg": 0.0,
            "active_minutes_avg": 0.0,
            "body_battery_high_avg": 0.0,
            "body_battery_low_avg": 0.0,
            "total_calories_avg": 0.0,
        }

    return {
        "days": days,
        "sample_count": len(subset),
        "steps_avg": round(_mean(item.steps for item in subset), 2),
        "stress_avg": round(_mean(item.stress_avg for item in subset), 2),
        "active_minutes_avg": round(_mean(item.active_minutes for item in subset), 2),
        "body_battery_high_avg": round(_mean(item.body_battery_high for item in subset), 2),
        "body_battery_low_avg": round(_mean(item.body_battery_low for item in subset), 2),
        "total_calories_avg": round(_mean(item.total_calories for item in subset), 2),
    }


def _window_sleep(sessions: list[HealthSleepSession], *, days: int) -> dict[str, Any]:
    subset = sessions[:days]
    if not subset:
        return {
            "days": days,
            "sample_count": 0,
            "sleep_hours_avg": 0.0,
            "sleep_score_avg": 0.0,
        }

    return {
        "days": days,
        "sample_count": len(subset),
        "sleep_hours_avg": round(_mean(item.duration_seconds / 3600 for item in subset), 2),
        "sleep_score_avg": round(_mean(item.sleep_score for item in subset), 2),
    }


def _build_recent_checkins(events: list[WearableEvent]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        ts = event.recorded_at.isoformat()
        bucket = grouped.setdefault(
            ts,
            {
                "recorded_at": ts,
                "source": event.source,
                "mood": None,
                "mood_score": None,
                "note": "",
                "note_sentiment": 0.0,
            },
        )
        if event.signal_type == "check_in_mood":
            bucket["mood"] = event.value
            bucket["mood_score"] = _mood_score(event.value)
        elif event.signal_type == "check_in_note":
            bucket["note"] = event.value
            bucket["note_sentiment"] = round(_sentiment_score(event.value), 3)

    ordered = sorted(grouped.values(), key=lambda item: item["recorded_at"], reverse=True)
    return ordered[:10]


def _derive_dynamic_state(
    *,
    signals: dict[str, Any],
    profile: dict[str, Any],
    feature_windows: dict[str, Any],
    recent_checkins: list[dict[str, Any]],
    calorie_summary: dict[str, Any],
) -> dict[str, Any]:
    sleep_hours = _safe_float(signals.get("sleep_hours"), feature_windows["sleep"]["7d"]["sleep_hours_avg"])
    stress_level = _safe_float(signals.get("stress_level"), feature_windows["metrics"]["7d"]["stress_avg"])
    body_battery_high = _safe_float(
        signals.get("body_battery_high"), feature_windows["metrics"]["7d"]["body_battery_high_avg"]
    )
    active_minutes = _safe_float(signals.get("active_minutes"), feature_windows["metrics"]["7d"]["active_minutes_avg"])

    sleep_debt = _clamp((8.0 - sleep_hours) / 4.0)
    stress_load = _clamp(stress_level / 10.0)
    recovery_signal = _clamp(body_battery_high / 100.0) if body_battery_high > 0 else _clamp(1.0 - stress_load)
    recovery_score = round(_clamp((1.0 - sleep_debt + recovery_signal) / 2.0), 3)
    activity_capacity = round(
        _clamp((_clamp(active_minutes / 60.0) + recovery_score) / 2.0),
        3,
    )
    low_energy_mode = bool((profile.get("accessibility") or {}).get("low_energy_mode", False))
    prep_capacity = round(
        _clamp(
            (recovery_score * 0.6)
            + ((0.2 if not low_energy_mode else 0.0))
            + ((1.0 - stress_load) * 0.2)
        ),
        3,
    )
    calorie_balance = int((calorie_summary.get("avg_intake_7d") or 0) - (calorie_summary.get("avg_burn_7d") or 0))
    adherence_score = round(
        _clamp(
            ((calorie_summary.get("logging_days_7d", 0) / 7.0) * 0.6)
            + ((len(recent_checkins) / 7.0) * 0.4)
        ),
        3,
    )
    routine_stability = round(
        _clamp(
            (
                _clamp(feature_windows["sleep"]["7d"]["sample_count"] / 7.0)
                + _clamp(feature_windows["metrics"]["7d"]["sample_count"] / 7.0)
                + adherence_score
            )
            / 3.0
        ),
        3,
    )

    latest_mood_score = next(
        (item["mood_score"] for item in recent_checkins if item.get("mood_score") is not None),
        _mood_score(signals.get("check_in_mood")),
    )
    latest_note_sentiment = next(
        (item["note_sentiment"] for item in recent_checkins if item.get("note")),
        round(_sentiment_score(str(signals.get("check_in_note", ""))), 3),
    )

    return {
        "sleep_debt": round(sleep_debt, 3),
        "stress_load": round(stress_load, 3),
        "recovery_score": recovery_score,
        "activity_capacity": activity_capacity,
        "prep_capacity": prep_capacity,
        "calorie_balance": calorie_balance,
        "protein_gap": None,
        "adherence_score": adherence_score,
        "routine_stability": routine_stability,
        "latest_mood_score": None if latest_mood_score is None else round(latest_mood_score, 3),
        "latest_note_sentiment": latest_note_sentiment,
    }


def _derive_archetype_scores(
    *,
    persona_type: str,
    dynamic_state: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, float]:
    sleep_debt = dynamic_state["sleep_debt"]
    stress_load = dynamic_state["stress_load"]
    recovery_score = dynamic_state["recovery_score"]
    routine_stability = dynamic_state["routine_stability"]
    prep_capacity = dynamic_state["prep_capacity"]
    low_energy_mode = bool((profile.get("accessibility") or {}).get("low_energy_mode", False))
    simplified_language = bool((profile.get("accessibility") or {}).get("simplified_language", False))

    student_overload = _clamp((0.45 if persona_type == "student" else 0.0) + (stress_load * 0.35) + (sleep_debt * 0.2))
    caregiver_burden = _clamp((0.45 if persona_type == "caregiver" else 0.0) + (stress_load * 0.3) + ((1.0 - prep_capacity) * 0.25))
    low_energy_recovery = _clamp(((1.0 - recovery_score) * 0.55) + (sleep_debt * 0.25) + ((0.2 if low_energy_mode else 0.0)))
    routine_rebuild = _clamp(((1.0 - routine_stability) * 0.65) + ((1.0 - prep_capacity) * 0.15))
    accessibility_support = _clamp(
        (0.5 if persona_type == "accessibility_focused" else 0.0)
        + (0.25 if low_energy_mode else 0.0)
        + (0.25 if simplified_language else 0.0)
    )
    performance_ready = _clamp((recovery_score * 0.45) + ((1.0 - stress_load) * 0.35) + (routine_stability * 0.2))

    return {
        "student_overload": round(student_overload, 3),
        "caregiver_burden": round(caregiver_burden, 3),
        "low_energy_recovery": round(low_energy_recovery, 3),
        "routine_rebuild": round(routine_rebuild, 3),
        "accessibility_support": round(accessibility_support, 3),
        "performance_ready": round(performance_ready, 3),
    }


def _serialize_recent_interventions(interventions: list[Intervention]) -> dict[str, Any]:
    latest = interventions[0] if interventions else None
    recent_recipe_ids = [item.recipe_id for item in interventions if item.recipe_id is not None]
    return {
        "count_30d": len(interventions),
        "latest": (
            {
                "id": latest.id,
                "run_id": latest.run_id,
                "state_snapshot_id": latest.state_snapshot_id,
                "recipe_id": latest.recipe_id,
                "created_at": latest.created_at.isoformat(),
                "meal_suggestion": latest.meal_suggestion,
                "activity_suggestion": latest.activity_suggestion,
                "wellness_action": latest.wellness_action,
            }
            if latest is not None
            else None
        ),
        "recent_recipe_ids": recent_recipe_ids[:10],
    }


async def build_personalization_context(
    *,
    db: AsyncSession,
    user: User,
    run_id: int | None = None,
    scenario: str = "live",
) -> dict[str, Any]:
    fallback_persona = _scenario_persona(scenario)

    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()

    accessibility_result = await db.execute(
        select(AccessibilityPreferences).where(AccessibilityPreferences.user_id == user.id)
    )
    accessibility = accessibility_result.scalar_one_or_none()

    profile_payload = _serialize_profile(
        profile,
        accessibility,
        user_id=user.id,
        fallback_persona=fallback_persona,
    )
    persona_type = str(profile_payload.get("persona_type") or fallback_persona)

    run = await db.get(AgentRun, run_id) if run_id is not None else None
    if run_id is not None and run is None:
        raise LookupError(f"Run not found: {run_id}")
    if run is not None and run.user_id != user.id:
        raise PermissionError(f"Run {run.id} does not belong to user {user.id}")
    normalized_event = await db.get(NormalizedEvent, run.normalized_event_id) if run and run.normalized_event_id else None

    since_30 = date.today() - timedelta(days=30)
    metrics = (
        (
            await db.execute(
                select(HealthDailyMetrics)
                .where(HealthDailyMetrics.user_id == user.id, HealthDailyMetrics.metric_date >= since_30)
                .order_by(HealthDailyMetrics.metric_date.desc())
            )
        )
        .scalars()
        .all()
    )
    sleep_sessions = (
        (
            await db.execute(
                select(HealthSleepSession)
                .where(HealthSleepSession.user_id == user.id, HealthSleepSession.sleep_date >= since_30)
                .order_by(HealthSleepSession.sleep_date.desc())
            )
        )
        .scalars()
        .all()
    )
    checkin_events = (
        (
            await db.execute(
                select(WearableEvent)
                .where(
                    WearableEvent.user_id == user.id,
                    WearableEvent.signal_type.in_(["check_in_mood", "check_in_note"]),
                    WearableEvent.recorded_at >= datetime.now(timezone.utc) - timedelta(days=30),
                )
                .order_by(WearableEvent.recorded_at.desc())
            )
        )
        .scalars()
        .all()
    )
    calorie_logs = (
        (
            await db.execute(
                select(HealthCalorieLog)
                .where(HealthCalorieLog.user_id == user.id, HealthCalorieLog.log_date >= since_30)
                .order_by(HealthCalorieLog.log_date.desc())
            )
        )
        .scalars()
        .all()
    )
    meal_plan_slots = (
        (
            await db.execute(
                select(MealPlanSlot)
                .where(MealPlanSlot.user_id == user.id, MealPlanSlot.plan_date >= since_30)
                .order_by(MealPlanSlot.plan_date.desc())
            )
        )
        .scalars()
        .all()
    )
    interventions = (
        (
            await db.execute(
                select(Intervention)
                .where(Intervention.user_id == user.id, Intervention.created_at >= datetime.now(timezone.utc) - timedelta(days=30))
                .order_by(Intervention.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    recent_checkins = _build_recent_checkins(checkin_events)
    feature_windows = {
        "metrics": {
            "1d": _window_metrics(metrics, days=1),
            "7d": _window_metrics(metrics, days=7),
            "30d": _window_metrics(metrics, days=30),
        },
        "sleep": {
            "1d": _window_sleep(sleep_sessions, days=1),
            "7d": _window_sleep(sleep_sessions, days=7),
            "30d": _window_sleep(sleep_sessions, days=30),
        },
    }

    intake_by_day: dict[str, int] = defaultdict(int)
    for item in calorie_logs:
        intake_by_day[item.log_date.isoformat()] += item.calories

    avg_burn_7d = feature_windows["metrics"]["7d"]["total_calories_avg"]
    calorie_summary = {
        "logging_days_7d": len({item.log_date for item in calorie_logs if item.log_date >= date.today() - timedelta(days=7)}),
        "logging_days_30d": len({item.log_date for item in calorie_logs}),
        "avg_intake_7d": round(
            _mean(
                calories
                for day, calories in intake_by_day.items()
                if date.fromisoformat(day) >= date.today() - timedelta(days=7)
            ),
            2,
        ),
        "avg_intake_30d": round(_mean(intake_by_day.values()), 2),
        "avg_burn_7d": avg_burn_7d,
        "latest_logged_date": max(intake_by_day.keys()) if intake_by_day else None,
    }

    recipe_history = {
        "meal_plan_slot_count_30d": len(meal_plan_slots),
        "recent_meal_plan_recipe_ids": [slot.recipe_id for slot in meal_plan_slots if slot.recipe_id is not None][:10],
        "recent_intervention_recipe_ids": [item.recipe_id for item in interventions if item.recipe_id is not None][:10],
    }
    intervention_history = _serialize_recent_interventions(interventions)

    signals: dict[str, Any] = dict(normalized_event.signals if normalized_event is not None else {})
    latest_metric = metrics[0] if metrics else None
    latest_sleep = sleep_sessions[0] if sleep_sessions else None
    if latest_metric is not None:
        signals.setdefault("steps", latest_metric.steps)
        signals.setdefault("step_goal", latest_metric.step_goal)
        signals.setdefault("active_calories", latest_metric.active_calories)
        signals.setdefault("total_calories", latest_metric.total_calories)
        signals.setdefault("resting_hr", latest_metric.resting_hr)
        signals.setdefault("avg_hr", latest_metric.avg_hr)
        signals.setdefault("body_battery_high", latest_metric.body_battery_high)
        signals.setdefault("body_battery_low", latest_metric.body_battery_low)
        signals.setdefault("stress_level", latest_metric.stress_avg)
        signals.setdefault("active_minutes", latest_metric.active_minutes)
        signals.setdefault("hrv_weekly_avg", latest_metric.hrv_weekly_avg)
        signals.setdefault("hrv_status", latest_metric.hrv_status)
    if latest_sleep is not None:
        signals.setdefault("sleep_hours", round(latest_sleep.duration_seconds / 3600, 2))
        signals.setdefault("sleep_score", latest_sleep.sleep_score)

    latest_checkin = recent_checkins[0] if recent_checkins else None
    if latest_checkin is not None:
        if latest_checkin.get("mood") and "check_in_mood" not in signals:
            signals["check_in_mood"] = latest_checkin["mood"]
        if latest_checkin.get("note") and "check_in_note" not in signals:
            signals["check_in_note"] = latest_checkin["note"]

    dynamic_state = _derive_dynamic_state(
        signals=signals,
        profile=profile_payload,
        feature_windows=feature_windows,
        recent_checkins=recent_checkins,
        calorie_summary=calorie_summary,
    )
    archetype_scores = _derive_archetype_scores(
        persona_type=persona_type,
        dynamic_state=dynamic_state,
        profile=profile_payload,
    )

    inputs_summary = {
        "recent_checkins": recent_checkins[:5],
        "calorie_summary": calorie_summary,
        "recipe_history": recipe_history,
        "intervention_history": intervention_history,
    }

    snapshot = PersonalizationStateSnapshot(
        user_id=user.id,
        run_id=run_id,
        source=scenario,
        profile_static=profile_payload,
        dynamic_state=dynamic_state,
        archetype_scores=archetype_scores,
        feature_windows=feature_windows,
        inputs_summary=inputs_summary,
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    return {
        "snapshot_id": snapshot.id,
        "user_id": user.id,
        "run_id": run_id,
        "scenario": scenario,
        "persona_type": persona_type,
        "profile": profile_payload,
        "dynamic_state": dynamic_state,
        "archetype_scores": archetype_scores,
        "feature_windows": feature_windows,
        "recent_checkins": recent_checkins,
        "calorie_summary": calorie_summary,
        "recipe_history": recipe_history,
        "intervention_history": intervention_history,
        "signals": signals,
        "normalized_event_id": getattr(run, "normalized_event_id", None),
    }
