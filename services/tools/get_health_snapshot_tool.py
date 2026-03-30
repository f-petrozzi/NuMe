from __future__ import annotations

from typing import Any, Dict

from services.tools._client import api_request


def get_health_snapshot(*, api_base_url: str, auth_header: str) -> Dict[str, Any]:
    """
    Fetch the current user's health overview from /api/health/overview.
    Returns a dict with today's steps, sleep, stress, body battery, HR, etc.
    Falls back to an empty dict if the endpoint is unavailable or returns no data.
    """
    try:
        data = api_request(
            method="GET",
            path="/api/health/overview",
            api_base_url=api_base_url,
            auth_header=auth_header,
        )
        return data or {}
    except Exception:
        return {}
