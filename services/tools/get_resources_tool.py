from __future__ import annotations

from typing import Any, Dict, List

from services.tools._client import api_request


def get_resources(
    *,
    persona: str,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
) -> List[Dict[str, Any]]:
    return api_request(
        method="GET",
        path="/api/resources",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        params={"persona": persona},
    )
