from __future__ import annotations

from catalog_ranking import (
    DEFAULT_ACTIVITY_TEMPLATES,
    DEFAULT_WELLNESS_TEMPLATES,
    build_catalog_ranking_context,
    rank_activity_templates,
    rank_wellness_templates,
)


def test_activity_ranking_prefers_low_energy_options_when_capacity_is_low():
    context = build_catalog_ranking_context(
        profile={
            "goal": "stress_reduction",
            "accessibility": {"low_energy_mode": True},
        },
        dynamic_state={
            "activity_capacity": 0.28,
            "stress_load": 0.82,
            "sleep_debt": 0.64,
        },
        archetype_scores={
            "student_overload": 0.71,
            "performance_ready": 0.22,
        },
        risk_level="high",
    )

    ranked = rank_activity_templates(DEFAULT_ACTIVITY_TEMPLATES, context, limit=3)

    assert ranked[0].template["title"] == "Seated Mobility Reset"
    assert ranked[0].template["duration_minutes"] <= 10
    assert ranked[0].score > ranked[1].score


def test_wellness_ranking_prefers_sleep_support_when_sleep_debt_is_high():
    context = build_catalog_ranking_context(
        profile={
            "goal": "better_sleep",
            "accessibility": {"low_energy_mode": False},
        },
        dynamic_state={
            "stress_load": 0.22,
            "sleep_debt": 0.72,
            "routine_stability": 0.41,
        },
        risk_level="low",
    )

    ranked = rank_wellness_templates(DEFAULT_WELLNESS_TEMPLATES, context, limit=3)

    assert ranked[0].template["title"] == "Digital Sunset Prep"
    assert ranked[0].template["category"] == "sleep"
    assert ranked[0].score > ranked[1].score
