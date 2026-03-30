from __future__ import annotations

from starlette.requests import Request

from run_dispatch import coordinator_api_base_url


def _request(url: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": url.split("://", 1)[0],
            "server": ("testserver", 80),
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
        }
    )


def test_coordinator_api_base_url_prefers_explicit_env(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://api.railway.internal:8000/")

    assert coordinator_api_base_url(_request("http://example.com")) == "http://api.railway.internal:8000"


def test_coordinator_api_base_url_falls_back_to_request_base_url(monkeypatch):
    monkeypatch.delenv("API_BASE_URL", raising=False)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "server": ("hackusf26-production.up.railway.app", 443),
            "path": "/api/events/checkin",
            "raw_path": b"/api/events/checkin",
            "query_string": b"",
            "headers": [(b"host", b"hackusf26-production.up.railway.app")],
        }
    )

    assert coordinator_api_base_url(request) == "https://hackusf26-production.up.railway.app"
