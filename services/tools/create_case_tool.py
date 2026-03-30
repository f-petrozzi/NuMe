from __future__ import annotations

from typing import Any, Dict, Optional

from services.tools._client import api_request


def create_case(
    *,
    user_id: int,
    run_id: Optional[int],
    risk_level: str,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
) -> Dict[str, Any]:
    return api_request(
        method="POST",
        path="/api/cases",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        json_payload={"user_id": user_id, "run_id": run_id, "risk_level": risk_level},
    )
