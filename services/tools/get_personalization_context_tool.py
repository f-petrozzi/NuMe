from __future__ import annotations

from typing import Any, Dict

from services.tools._client import api_request


def get_personalization_context(
    *,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
    internal_api_token: str = "",
    acting_user_id: int | None = None,
    run_id: int | None = None,
    scenario: str = "live",
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"scenario": scenario}
    if run_id is not None:
        params["run_id"] = run_id

    return api_request(
        method="GET",
        path="/api/personalization/context",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        internal_api_token=internal_api_token,
        acting_user_id=acting_user_id,
        params=params,
    )
