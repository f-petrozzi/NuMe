from __future__ import annotations

from typing import Any, Dict, Optional

from services.tools._client import api_request


def persist_audit(
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: Dict[str, Any],
    user_id: Optional[int] = None,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
) -> Dict[str, Any]:
    return api_request(
        method="POST",
        path="/api/audit-logs",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        json_payload={
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata,
            "user_id": user_id,
        },
    )
