from __future__ import annotations

import os

from fastapi import Request


def coordinator_api_base_url(request: Request) -> str:
    configured = os.getenv("API_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


def coordinator_auth_header(request: Request) -> str:
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header:
        return auth_header

    session_token = request.cookies.get("__session", "").strip()
    if session_token:
        return f"Bearer {session_token}"

    return ""
