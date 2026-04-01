from __future__ import annotations

from typing import Any, Dict, List

from services.tools._client import api_request


def get_recent_signals(
    *,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
    internal_api_token: str = "",
    acting_user_id: int | None = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    return api_request(
        method="GET",
        path="/api/events/recent",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        internal_api_token=internal_api_token,
        acting_user_id=acting_user_id,
        params={"limit": limit},
    )
