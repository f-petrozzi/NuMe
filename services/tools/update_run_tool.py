from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from services.tools._client import api_request


def update_run(
    *,
    run_id: int,
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    completed_at: Optional[str | datetime] = None,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
) -> Dict[str, Any]:
    if isinstance(completed_at, datetime):
        completed_value: Optional[str] = completed_at.isoformat()
    else:
        completed_value = completed_at

    payload: Dict[str, Any] = {}
    if status is not None:
        payload["status"] = status
    if risk_level is not None:
        payload["risk_level"] = risk_level
    if completed_value is not None:
        payload["completed_at"] = completed_value

    return api_request(
        method="PUT",
        path=f"/api/runs/{run_id}",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        json_payload=payload,
    )
