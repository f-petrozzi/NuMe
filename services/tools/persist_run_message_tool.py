from __future__ import annotations

from typing import Any, Dict, Optional

from services.tools._client import api_request


def persist_run_message(
    *,
    run_id: int,
    agent_name: str,
    agent_type: str,
    input: Dict[str, Any],
    output: Dict[str, Any],
    iteration: int = 0,
    duration_ms: Optional[int] = None,
    created_at: Optional[str] = None,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
    internal_api_token: str = "",
    acting_user_id: int | None = None,
) -> Dict[str, Any]:
    return api_request(
        method="POST",
        path="/api/runs/messages",
        api_base_url=api_base_url,
        auth_header=auth_header,
        demo_as=demo_as,
        internal_api_token=internal_api_token,
        acting_user_id=acting_user_id,
        json_payload={
            "run_id": run_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "input": input,
            "output": output,
            "iteration": iteration,
            "duration_ms": duration_ms,
        },
    )
