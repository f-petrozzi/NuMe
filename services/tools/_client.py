from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


def api_request(
    *,
    method: str,
    path: str,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
    json_payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    headers = {"Authorization": auth_header} if auth_header else {}
    if demo_as:
        headers["X-Demo-As"] = demo_as
    url = f"{api_base_url.rstrip('/')}{path}"
    last_exc: Exception | None = None

    for _ in range(2):
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_payload,
                    params=params,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            last_exc = exc

    raise RuntimeError(f"API request failed for {method} {path}: {last_exc}")
