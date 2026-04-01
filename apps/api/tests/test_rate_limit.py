from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

from auth import get_current_user
from dependencies import rate_limit
from main import app
from models import AIRateCounter, NormalizedEvent, User


def _build_request(client_host: str, headers: dict[str, str] | None = None) -> Request:
    encoded_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": encoded_headers,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


async def _counter_map(db: AsyncSession) -> dict[str, int]:
    assert db.bind is not None
    factory = async_sessionmaker(db.bind, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(select(AIRateCounter))
        return {row.bucket_key: row.count for row in result.scalars().all()}


def test_extract_real_ip_trusts_docker_bridge_proxy_cidr(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_trusted_proxy_ips", "127.0.0.1,172.16.0.0/12")
    request = _build_request("172.18.0.8", headers={"CF-Connecting-IP": "1.2.3.4"})
    assert rate_limit._extract_real_ip(request) == "1.2.3.4"


def test_extract_real_ip_ignores_forwarded_headers_from_untrusted_host(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_trusted_proxy_ips", "127.0.0.1,::1")
    request = _build_request("8.8.8.8", headers={"CF-Connecting-IP": "1.2.3.4"})
    assert rate_limit._extract_real_ip(request) == "8.8.8.8"


async def test_checkin_succeeds_when_user_resolution_touches_db(client: AsyncClient, db: AsyncSession):
    async def _lookup_user() -> User:
        result = await db.execute(select(User).where(User.id == 1))
        return result.scalar_one()

    original_override = app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_current_user] = _lookup_user

    try:
        resp = await client.post(
            "/api/events/checkin",
            json={
                "mood": 6,
                "sleep_hours": 6.5,
                "stress": 70,
                "note": "Feeling a bit off today",
            },
        )
    finally:
        app.dependency_overrides[get_current_user] = original_override

    assert resp.status_code == 201, resp.text

    quota = await client.get("/api/quota/daily")
    assert quota.status_code == 200, quota.text
    assert quota.json()["global_units_today"] == 5
    assert quota.json()["user_units_today"] == 5


async def test_trigger_invalid_request_does_not_charge_quota(client: AsyncClient, db: AsyncSession):
    foreign_norm = NormalizedEvent(
        user_id=2,
        signals={"stress_level": "8"},
        summary="stress 8/10",
    )
    db.add(foreign_norm)
    await db.commit()
    await db.refresh(foreign_norm)

    resp = await client.post("/api/runs/trigger", json={"normalized_event_id": foreign_norm.id})
    assert resp.status_code == 404, resp.text
    assert await _counter_map(db) == {}


async def test_unknown_scenario_does_not_charge_quota(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/scenarios/unknown_scenario/run")
    assert resp.status_code == 404, resp.text
    assert await _counter_map(db) == {}


async def test_parse_text_empty_body_does_not_charge_quota(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/recipes/parse-text", json={"text": "   "})
    assert resp.status_code == 400, resp.text
    assert await _counter_map(db) == {}


async def test_ai_kill_switch_blocks_request_before_charging(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(rate_limit.settings, "ai_endpoints_enabled", False)

    resp = await client.post(
        "/api/events/checkin",
        json={
            "mood": 6,
            "sleep_hours": 6.5,
            "stress": 70,
            "note": "Feeling a bit off today",
        },
    )
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"]["error"] == "ai_disabled"
    assert await _counter_map(db) == {}
