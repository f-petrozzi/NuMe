from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def get_user_profile_stub(persona_type: str = "student") -> Dict[str, Any]:
    return {
        "id": 1,
        "user_id": 1,
        "age_range": "18-24" if persona_type == "student" else "35-44",
        "sex": "unspecified",
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "goal": "stress_reduction" if persona_type == "student" else "burnout_recovery",
        "activity_level": "light",
        "dietary_style": "omnivore",
        "allergies": [],
        "persona_type": persona_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "accessibility": {
            "user_id": 1,
            "simplified_language": persona_type == "accessibility_focused",
            "large_text": False,
            "low_energy_mode": persona_type in {"caregiver", "accessibility_focused"},
        },
    }


def get_recent_signals_stub(scenario: str = "stressed_student") -> List[Dict[str, Any]]:
    scenario_signals = {
        "stressed_student": {
            "sleep_hours": "4.5",
            "stress_level": "8",
            "steps": "800",
            "check_in_mood": "anxious",
            "check_in_note": "I am behind on studying and feel overwhelmed.",
        },
        "exhausted_caregiver": {
            "sleep_hours": "5.0",
            "stress_level": "9",
            "steps": "1200",
            "activity_level": "low",
            "check_in_note": "Completely drained after caring for family all week.",
        },
        "older_adult": {
            "sleep_hours": "5.5",
            "stress_level": "6",
            "steps": "600",
            "check_in_mood": "off_routine",
            "check_in_note": "My usual routine has been disrupted this week.",
        },
    }
    signals = scenario_signals.get(scenario, scenario_signals["stressed_student"])
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": index + 1,
            "user_id": 1,
            "source": "simulated",
            "signal_type": signal_type,
            "value": value,
            "unit": "",
            "recorded_at": now,
        }
        for index, (signal_type, value) in enumerate(signals.items())
    ]


def get_resources_stub(persona: str) -> List[Dict[str, Any]]:
    resources = {
        "student": ["Student Counseling Services", "Academic Success Center"],
        "caregiver": ["Caregiver Support Group", "Local Respite Network"],
        "older_adult": ["Routine Support Hotline", "Community Wellness Check"],
        "accessibility_focused": ["Accessible Wellness Services", "Low-Energy Planning Guide"],
    }
    return [{"title": title} for title in resources.get(persona, [])]

