from __future__ import annotations

from typing import Any, Iterable, Mapping

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
_NEGATIVE_MOOD_TOKENS = {
    "anxious",
    "confused",
    "drained",
    "exhausted",
    "negative",
    "overwhelmed",
    "stressed",
    "tired",
    "worried",
}
_POSITIVE_MOOD_TOKENS = {"calm", "good", "great", "okay", "positive", "rested", "steady"}
_SUBSCORE_LABELS = {
    "physiological_strain": "physiological strain",
    "emotional_strain": "emotional strain",
    "recovery_debt": "recovery debt",
    "adherence_risk": "adherence risk",
}


def clamp(value: float, *, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_mood_score(raw_mood: Any) -> float | None:
    if raw_mood is None:
        return None

    numeric = safe_float(raw_mood, default=-1.0)
    if numeric >= 0.0:
        if numeric <= 1.0:
            return round(clamp(numeric), 3)
        if numeric > 10.0:
            numeric = 10.0
        return round(clamp((numeric - 1.0) / 9.0), 3)

    mood = str(raw_mood).strip().lower()
    if not mood:
        return None
    if mood in _POSITIVE_MOOD_TOKENS:
        return 0.75
    if mood in _NEGATIVE_MOOD_TOKENS:
        return 0.25
    return 0.5


def score_note_sentiment(note: str | None) -> float:
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

    normalized = (clamp((score + 3.0) / 6.0, low=0.0, high=1.0) * 2.0) - 1.0
    return round(normalized, 3)


def coerce_checkin_stress_level(raw_stress: Any) -> int:
    value = safe_float(raw_stress, default=0.0)
    if value <= 10.0:
        return max(1, min(10, round(value))) or 1
    return max(1, min(10, round(value / 10.0))) or 1


def normalize_stress_score(raw_stress: Any) -> float:
    value = safe_float(raw_stress, default=0.0)
    if value <= 0.0:
        return 0.0
    if value <= 1.0:
        return round(clamp(value), 3)
    if value <= 10.0:
        return round(clamp(value / 10.0), 3)
    return round(clamp(coerce_checkin_stress_level(value) / 10.0), 3)


def is_negative_checkin(
    *,
    mood_score: float | None,
    note_sentiment: float,
) -> bool:
    if mood_score is not None and mood_score <= 0.25:
        return True
    if note_sentiment <= -0.35:
        return True
    if mood_score is not None and mood_score <= 0.4 and note_sentiment < 0.0:
        return True
    return False


def classify_checkin_valence(
    *,
    mood_score: float | None,
    note_sentiment: float,
) -> str:
    if is_negative_checkin(mood_score=mood_score, note_sentiment=note_sentiment):
        return "negative"
    if (mood_score is not None and mood_score >= 0.7) or note_sentiment >= 0.25:
        return "positive"
    return "neutral"


def normalize_checkin_payload(
    *,
    mood: int,
    sleep_hours: float,
    stress: int,
    note: str = "",
) -> dict[str, Any]:
    cleaned_note = note.strip()
    mood_score = normalize_mood_score(mood)
    stress_level = coerce_checkin_stress_level(stress)
    note_sentiment = score_note_sentiment(cleaned_note)

    signals: dict[str, Any] = {
        "check_in_mood": str(mood),
        "check_in_mood_score": mood_score,
        "check_in_valence": classify_checkin_valence(
            mood_score=mood_score,
            note_sentiment=note_sentiment,
        ),
        "sleep_hours": str(sleep_hours),
        "stress_level": str(stress_level),
        "stress_level_normalized": round(stress_level / 10.0, 3),
    }
    if cleaned_note:
        signals["check_in_note"] = cleaned_note
        signals["check_in_note_sentiment"] = note_sentiment

    return signals


def build_deterministic_risk_assessment(
    *,
    persona_type: str,
    signals: Mapping[str, Any] | None,
    dynamic_state: Mapping[str, Any] | None = None,
    recent_checkins: Iterable[Mapping[str, Any]] | None = None,
    feature_windows: Mapping[str, Any] | None = None,
    findings: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    signals = dict(signals or {})
    dynamic_state = dict(dynamic_state or {})
    feature_windows = dict(feature_windows or {})
    recent_checkins = list(recent_checkins or [])
    findings = list(findings or [])

    sleep_window = dict(feature_windows.get("sleep", {}).get("7d", {}))
    sleep_hours = safe_float(
        signals.get("sleep_hours"),
        safe_float(sleep_window.get("sleep_hours_avg"), 7.0),
    )
    stress_score = normalize_stress_score(
        signals.get("stress_level", dynamic_state.get("stress_load", 0.0))
    )
    body_battery_high = safe_float(signals.get("body_battery_high"), 0.0)
    steps = safe_float(signals.get("steps"), 0.0)
    active_minutes = safe_float(signals.get("active_minutes"), 0.0)

    mood_score = _resolve_mood_score(signals=signals, dynamic_state=dynamic_state, recent_checkins=recent_checkins)
    note_sentiment = _resolve_note_sentiment(
        signals=signals,
        dynamic_state=dynamic_state,
        recent_checkins=recent_checkins,
    )

    sleep_debt = _resolve_sleep_debt(dynamic_state=dynamic_state, sleep_hours=sleep_hours)
    recovery_score = _resolve_recovery_score(
        dynamic_state=dynamic_state,
        body_battery_high=body_battery_high,
        stress_score=stress_score,
    )
    adherence_score = _resolve_dynamic_score(
        dynamic_state.get("adherence_score"),
        default=_checkin_participation_score(recent_checkins),
    )
    routine_stability = _resolve_dynamic_score(
        dynamic_state.get("routine_stability"),
        default=0.55,
    )
    negative_recent_ratio = _recent_negative_checkin_ratio(recent_checkins)

    low_activity = _low_activity_score(steps=steps, active_minutes=active_minutes)
    battery_strain = (
        clamp((45.0 - body_battery_high) / 45.0)
        if body_battery_high > 0.0
        else clamp(1.0 - recovery_score)
    )
    mood_distress = (
        clamp((0.45 - mood_score) / 0.45)
        if mood_score is not None
        else 0.0
    )
    note_distress = clamp(-note_sentiment) if note_sentiment < 0.0 else 0.0
    baseline_sleep_gap = _baseline_sleep_gap(sleep_hours=sleep_hours, sleep_window=sleep_window)

    subscores = {
        "physiological_strain": round(
            clamp((stress_score * 0.45) + (battery_strain * 0.3) + (low_activity * 0.25)),
            3,
        ),
        "emotional_strain": round(
            clamp(
                (stress_score * 0.55)
                + (mood_distress * 0.25)
                + (note_distress * 0.15)
                + (negative_recent_ratio * 0.05)
            ),
            3,
        ),
        "recovery_debt": round(
            clamp((sleep_debt * 0.55) + ((1.0 - recovery_score) * 0.35) + (baseline_sleep_gap * 0.1)),
            3,
        ),
        "adherence_risk": round(
            clamp(((1.0 - adherence_score) * 0.6) + ((1.0 - routine_stability) * 0.4)),
            3,
        ),
    }

    significant_count = sum(1 for finding in findings if str(finding.get("severity", "")).strip() == "significant")
    moderate_count = sum(1 for finding in findings if str(finding.get("severity", "")).strip() == "moderate")
    severity_load = clamp(
        sum(
            {"mild": 0.05, "moderate": 0.1, "significant": 0.18}.get(
                str(finding.get("severity", "")).strip(),
                0.03,
            )
            for finding in findings
        ),
        high=0.35,
    )
    overall_score = round(
        clamp(
            (subscores["physiological_strain"] * 0.28)
            + (subscores["emotional_strain"] * 0.24)
            + (subscores["recovery_debt"] * 0.32)
            + (subscores["adherence_risk"] * 0.16)
            + severity_load
        ),
        3,
    )

    risk_level = "low"
    if (
        overall_score >= 0.82
        or (significant_count >= 3 and overall_score >= 0.7)
        or (
            subscores["recovery_debt"] >= 0.82
            and subscores["emotional_strain"] >= 0.78
            and stress_score >= 0.9
        )
    ):
        risk_level = "critical"
    elif (
        overall_score >= 0.62
        or significant_count >= 2
        or (
            subscores["recovery_debt"] >= 0.72
            and (
                subscores["physiological_strain"] >= 0.65
                or subscores["emotional_strain"] >= 0.65
            )
        )
        or (
            persona_type == "student"
            and subscores["emotional_strain"] >= 0.72
            and subscores["recovery_debt"] >= 0.62
        )
    ):
        risk_level = "high"
    elif (
        overall_score >= 0.38
        or significant_count >= 1
        or moderate_count >= 2
        or max(subscores.values()) >= 0.55
    ):
        risk_level = "moderate"

    urgency = {
        "low": "routine",
        "moderate": "next_day",
        "high": "same_day",
        "critical": "immediate",
    }[risk_level]
    escalation_needed = risk_level in {"moderate", "high", "critical"}
    coordinator_review = risk_level in {"high", "critical"} or (
        persona_type == "caregiver"
        and risk_level == "moderate"
        and subscores["recovery_debt"] >= 0.72
    )

    evidence_inputs = sum(
        [
            1 if sleep_hours > 0.0 else 0,
            1 if stress_score > 0.0 else 0,
            1 if body_battery_high > 0.0 else 0,
            1 if steps > 0.0 or active_minutes > 0.0 else 0,
            1 if mood_score is not None or note_sentiment != 0.0 else 0,
            1 if dynamic_state else 0,
        ]
    )
    confidence = round(
        clamp(
            0.56
            + (min(evidence_inputs, 6) * 0.04)
            + (min(len(recent_checkins), 3) * 0.02)
            + (min(len(findings), 3) * 0.03),
            low=0.56,
            high=0.92,
        ),
        3,
    )

    drivers = _build_drivers(
        subscores=subscores,
        sleep_hours=sleep_hours,
        stress_score=stress_score,
        body_battery_high=body_battery_high,
        low_activity=low_activity,
        mood_score=mood_score,
        note_sentiment=note_sentiment,
        adherence_risk=subscores["adherence_risk"],
        recent_negative_ratio=negative_recent_ratio,
    )
    rationale = _build_rationale(risk_level=risk_level, subscores=subscores)

    return {
        "risk_level": risk_level,
        "urgency": urgency,
        "escalation_needed": escalation_needed,
        "coordinator_review": coordinator_review,
        "confidence": confidence,
        "subscores": subscores,
        "drivers": drivers,
        "rationale": rationale,
    }


def _resolve_mood_score(
    *,
    signals: Mapping[str, Any],
    dynamic_state: Mapping[str, Any],
    recent_checkins: list[Mapping[str, Any]],
) -> float | None:
    raw_signal = signals.get("check_in_mood_score")
    if raw_signal is not None:
        return normalize_mood_score(raw_signal)

    dynamic_value = dynamic_state.get("latest_mood_score")
    if dynamic_value is not None:
        return normalize_mood_score(dynamic_value)

    for item in recent_checkins:
        if item.get("mood_score") is not None:
            return normalize_mood_score(item.get("mood_score"))

    return normalize_mood_score(signals.get("check_in_mood"))


def _resolve_note_sentiment(
    *,
    signals: Mapping[str, Any],
    dynamic_state: Mapping[str, Any],
    recent_checkins: list[Mapping[str, Any]],
) -> float:
    signal_value = signals.get("check_in_note_sentiment")
    if signal_value is not None:
        return round(clamp(safe_float(signal_value), low=-1.0, high=1.0), 3)

    dynamic_value = dynamic_state.get("latest_note_sentiment")
    if dynamic_value is not None:
        return round(clamp(safe_float(dynamic_value), low=-1.0, high=1.0), 3)

    for item in recent_checkins:
        if item.get("note"):
            return round(clamp(safe_float(item.get("note_sentiment")), low=-1.0, high=1.0), 3)

    return score_note_sentiment(str(signals.get("check_in_note", "")))


def _resolve_sleep_debt(*, dynamic_state: Mapping[str, Any], sleep_hours: float) -> float:
    dynamic_value = dynamic_state.get("sleep_debt")
    if dynamic_value is not None:
        return round(clamp(safe_float(dynamic_value)), 3)
    return round(clamp((8.0 - sleep_hours) / 4.0), 3)


def _resolve_recovery_score(
    *,
    dynamic_state: Mapping[str, Any],
    body_battery_high: float,
    stress_score: float,
) -> float:
    dynamic_value = dynamic_state.get("recovery_score")
    if dynamic_value is not None:
        return round(clamp(safe_float(dynamic_value)), 3)
    if body_battery_high > 0.0:
        return round(clamp(body_battery_high / 100.0), 3)
    return round(clamp(1.0 - (stress_score * 0.75)), 3)


def _resolve_dynamic_score(value: Any, *, default: float) -> float:
    if value is None:
        return round(clamp(default), 3)
    return round(clamp(safe_float(value)), 3)


def _checkin_participation_score(recent_checkins: list[Mapping[str, Any]]) -> float:
    if not recent_checkins:
        return 0.45
    return round(clamp((len(recent_checkins[:7]) / 7.0) * 0.4 + 0.35), 3)


def _recent_negative_checkin_ratio(recent_checkins: list[Mapping[str, Any]]) -> float:
    sample = recent_checkins[:5]
    if not sample:
        return 0.0
    negatives = sum(
        1
        for item in sample
        if is_negative_checkin(
            mood_score=normalize_mood_score(item.get("mood_score")),
            note_sentiment=round(clamp(safe_float(item.get("note_sentiment")), low=-1.0, high=1.0), 3),
        )
    )
    return round(negatives / len(sample), 3)


def _low_activity_score(*, steps: float, active_minutes: float) -> float:
    if active_minutes > 0.0:
        return round(clamp((20.0 - active_minutes) / 20.0), 3)
    if steps > 0.0:
        return round(clamp((2500.0 - steps) / 2500.0), 3)
    return 0.35


def _baseline_sleep_gap(*, sleep_hours: float, sleep_window: Mapping[str, Any]) -> float:
    baseline = safe_float(sleep_window.get("sleep_hours_avg"), 0.0)
    if baseline <= 0.0:
        return 0.0
    if sleep_hours < baseline:
        return round(clamp((baseline - sleep_hours) / 2.5), 3)
    return round(clamp((6.5 - baseline) / 2.5), 3)


def _build_drivers(
    *,
    subscores: Mapping[str, float],
    sleep_hours: float,
    stress_score: float,
    body_battery_high: float,
    low_activity: float,
    mood_score: float | None,
    note_sentiment: float,
    adherence_risk: float,
    recent_negative_ratio: float,
) -> list[str]:
    ranked: list[tuple[float, str]] = []
    if subscores["recovery_debt"] >= 0.5:
        if sleep_hours > 0.0 and sleep_hours < 6.0:
            ranked.append((subscores["recovery_debt"], f"Sleep is down to {sleep_hours:.1f} hours and recovery debt is building."))
        else:
            ranked.append((subscores["recovery_debt"], "Recovery reserve is lower than baseline and sleep debt is accumulating."))
    if subscores["physiological_strain"] >= 0.5:
        if stress_score >= 0.7 and body_battery_high > 0.0 and body_battery_high <= 45.0:
            ranked.append((subscores["physiological_strain"], "Stress is elevated and body battery is suppressed."))
        elif stress_score >= 0.7:
            ranked.append((subscores["physiological_strain"], "Stress is elevated and increasing physiological strain."))
        elif low_activity >= 0.55:
            ranked.append((subscores["physiological_strain"], "Movement is well below the recent target."))
    if subscores["emotional_strain"] >= 0.45:
        if mood_score is not None and mood_score <= 0.3:
            ranked.append((subscores["emotional_strain"], "The latest check-in mood is low and suggests reduced coping capacity."))
        elif note_sentiment <= -0.2:
            ranked.append((subscores["emotional_strain"], "The latest check-in note language points to emotional strain."))
        elif recent_negative_ratio >= 0.4:
            ranked.append((subscores["emotional_strain"], "Recent check-ins show repeated distress markers."))
    if adherence_risk >= 0.45:
        ranked.append((adherence_risk, "Routine stability and follow-through have softened recently."))

    ranked.sort(key=lambda item: item[0], reverse=True)
    drivers = [message for _score, message in ranked[:3]]
    if not drivers:
        drivers.append("Current signals are close to baseline with no strong distress indicators.")
    return drivers


def _build_rationale(*, risk_level: str, subscores: Mapping[str, float]) -> str:
    if risk_level == "low":
        return "Low risk with no strong distress drivers in the current signal mix."

    ranked = sorted(subscores.items(), key=lambda item: item[1], reverse=True)
    top_labels = [_SUBSCORE_LABELS[key] for key, _value in ranked[:2]]
    if len(top_labels) == 1:
        focus = top_labels[0]
    else:
        focus = f"{top_labels[0]} and {top_labels[1]}"
    return f"{risk_level.title()} risk driven mostly by {focus}."
