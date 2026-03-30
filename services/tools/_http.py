"""Shared HTTP helper for all tools."""
import os
import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
_TIMEOUT = 10.0


def get(path: str, params: dict = None, token: str = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = httpx.get(f"{API_BASE_URL}{path}", params=params, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        # Retry once
        resp = httpx.get(f"{API_BASE_URL}{path}", params=params, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()


def post(path: str, body: dict, token: str = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = httpx.post(f"{API_BASE_URL}{path}", json=body, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        # Retry once
        resp = httpx.post(f"{API_BASE_URL}{path}", json=body, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
