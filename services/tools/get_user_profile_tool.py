from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from services.tools._client import api_request


def _default_profile(persona_type: str, user_id: int = 0) -> Dict[str, Any]:
    """Synthetic profile used when the running user has no real profile (e.g. admin/coordinator)."""
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


def _fallback_user_id(*, api_base_url: str, auth_header: str, demo_as: str = "") -> int:
    try:
        me = api_request(
            method="GET",
            path="/api/auth/me",
            api_base_url=api_base_url,
            auth_header=auth_header,
            demo_as=demo_as,
        )
    except RuntimeError:
        return 0

    try:
        return int(me.get("id") or 0)
    except (TypeError, ValueError):
        return 0


def get_user_profile(
    *,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
    fallback_persona: str = "student",
) -> Dict[str, Any]:
    try:
        profile = api_request(
            method="GET",
            path="/api/profile",
            api_base_url=api_base_url,
            auth_header=auth_header,
            demo_as=demo_as,
        )
    except RuntimeError:
        # User has no profile (e.g. admin or coordinator accounts).
        # Return a synthetic profile so the coordinator pipeline can proceed.
        return _default_profile(
            fallback_persona,
            user_id=_fallback_user_id(api_base_url=api_base_url, auth_header=auth_header, demo_as=demo_as),
        )

    try:
        accessibility = api_request(
            method="GET",
            path="/api/profile/accessibility",
            api_base_url=api_base_url,
            auth_header=auth_header,
            demo_as=demo_as,
        )
        profile["accessibility"] = accessibility
    except RuntimeError:
        profile["accessibility"] = {
            "user_id": profile.get("user_id", 0),
            "simplified_language": False,
            "large_text": False,
            "low_energy_mode": False,
        }
    return profile
