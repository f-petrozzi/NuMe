from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


def _request_headers(
    *,
    auth_header: str,
    demo_as: str,
    internal_api_token: str,
    acting_user_id: int | None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if internal_api_token:
        if acting_user_id is None:
            raise ValueError("acting_user_id is required when internal_api_token is configured")
        headers["X-Internal-Api-Key"] = internal_api_token
        headers["X-Internal-User-Id"] = str(acting_user_id)
        return headers

    if auth_header:
        headers["Authorization"] = auth_header
    if demo_as:
        headers["X-Demo-As"] = demo_as
    return headers


def api_request(
    *,
    method: str,
    path: str,
    api_base_url: str,
    auth_header: str,
    demo_as: str = "",
    internal_api_token: str = "",
    acting_user_id: int | None = None,
    json_payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    headers = _request_headers(
        auth_header=auth_header,
        demo_as=demo_as,
        internal_api_token=internal_api_token,
        acting_user_id=acting_user_id,
    )
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
