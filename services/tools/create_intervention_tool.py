from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.tools._client import api_request


def create_intervention(
    *,
    user_id: int,
    run_id: Optional[int],
    state_snapshot_id: Optional[int] = None,
    recipe_id: Optional[int] = None,
    activity_template_id: Optional[int] = None,
    wellness_template_id: Optional[int] = None,
    meal_suggestion: str,
    activity_suggestion: str,
    wellness_action: str,
    empathy_message: str,
    meal_constraints: Optional[List[str]] = None,
    risk_subscores: Optional[Dict[str, Any]] = None,
    why_chosen: Optional[Dict[str, Any]] = None,
    alternatives_considered: Optional[List[Any]] = None,
    why_changed_from_previous: Optional[List[str]] = None,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
    internal_api_token: str = "",
    acting_user_id: int | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "run_id": run_id,
        "meal_suggestion": meal_suggestion,
        "activity_suggestion": activity_suggestion,
        "wellness_action": wellness_action,
        "empathy_message": empathy_message,
        "meal_constraints": meal_constraints or [],
        "risk_subscores": risk_subscores,
    }
    if state_snapshot_id is not None:
        payload["state_snapshot_id"] = state_snapshot_id
    if recipe_id is not None:
        payload["recipe_id"] = recipe_id
    if activity_template_id is not None:
        payload["activity_template_id"] = activity_template_id
    if wellness_template_id is not None:
        payload["wellness_template_id"] = wellness_template_id
    if why_chosen is not None:
        payload["why_chosen"] = why_chosen
    if alternatives_considered is not None:
        payload["alternatives_considered"] = alternatives_considered
    if why_changed_from_previous is not None:
        payload["why_changed_from_previous"] = why_changed_from_previous

    return api_request(
        method="POST",
        path="/api/interventions",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        internal_api_token=internal_api_token,
        acting_user_id=acting_user_id,
        json_payload=payload,
    )
