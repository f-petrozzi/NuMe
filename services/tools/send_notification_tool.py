from __future__ import annotations

from typing import Any, Dict

from services.tools._client import api_request


def send_notification(
    *,
    user_id: int,
    type: str,
    content: str,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
) -> Dict[str, Any]:
    return api_request(
        method="POST",
        path="/api/notifications",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        json_payload={"user_id": user_id, "type": type, "content": content},
    )
