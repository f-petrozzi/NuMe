from __future__ import annotations

import builtins
import json
from datetime import date, datetime, timezone
from typing import Optional, get_type_hints
from unittest.mock import patch

from httpx import AsyncClient

import garmin_sync
from openai_client import generate_text
from routers import health


def test_list_calorie_log_query_param_is_date_typed():
    hints = get_type_hints(health.list_calorie_log)
    assert hints["log_date"] == Optional[date]


async def test_list_calorie_log_filters_by_date(client: AsyncClient):
    first_resp = await client.post(
        "/api/health/calorie-log",
        json={
            "log_date": "2026-03-29",
            "meal_type": "breakfast",
            "food_name": "Oatmeal",
            "calories": 320,
            "quantity": "1 bowl",
            "notes": "",
            "ai_estimated": False,
        },
    )
    assert first_resp.status_code == 201, first_resp.text

    second_resp = await client.post(
        "/api/health/calorie-log",
        json={
            "log_date": "2026-03-28",
            "meal_type": "dinner",
            "food_name": "Salmon",
            "calories": 540,
            "quantity": "1 fillet",
            "notes": "",
            "ai_estimated": False,
        },
    )
    assert second_resp.status_code == 201, second_resp.text

    resp = await client.get("/api/health/calorie-log", params={"log_date": "2026-03-29"})
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert len(body) == 1
    assert body[0]["food_name"] == "Oatmeal"
    assert body[0]["log_date"] == "2026-03-29"


async def test_readiness_check_reports_database_ok(client: AsyncClient):
    resp = await client.get("/readyz")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "status": "ok",
        "service": "nume-api",
        "database": "ok",
    }


async def test_generate_text_missing_openai_package_raises_actionable_error(monkeypatch):
    real_import = builtins.__import__
    monkeypatch.setenv("OPENAI_API_VERSION", "2025-01-01-preview")

    def _missing_openai(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai":
            raise ModuleNotFoundError("No module named 'openai'", name="openai")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=_missing_openai):
        try:
            await generate_text("Estimate calories for an apple.")
        except RuntimeError as exc:
            assert "openai" in str(exc)
            assert "requirements.txt" in str(exc)
        else:
            raise AssertionError("Expected missing openai package to raise RuntimeError")


async def test_ai_calorie_estimate_falls_back_when_generate_text_fails(
    client: AsyncClient,
    monkeypatch,
):
    async def _failing_generate_text(_prompt: str, *, model_name=None) -> str:
        raise RuntimeError("The 'openai' package is not installed.")

    monkeypatch.setattr(health, "generate_text", _failing_generate_text)

    resp = await client.post(
        "/api/health/calorie-log/ai-estimate",
        json={"food_name": "Apple", "quantity": "1 medium"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "food_name": "Apple",
        "quantity": "1 medium",
        "estimated_calories": 0,
        "confidence": "low",
    }


async def test_garmin_connect_returns_mfa_challenge(client: AsyncClient, monkeypatch):
    async def _require_mfa(user_id: int, email: str, password: str) -> None:
        raise health.GarminMfaRequired(
            challenge_id="challenge-123",
            email_hint="t***@g***.com",
            expires_at=datetime(2026, 4, 5, 15, 10, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(health.settings, "garmin_enabled", True)
    monkeypatch.setattr(health, "connect_user", _require_mfa)

    resp = await client.post(
        "/api/health/garmin/connect",
        json={"email": "test@garmin.com", "password": "secret123"},
    )

    assert resp.status_code == 202, resp.text
    assert resp.json() == {
        "connected": False,
        "user_id": 1,
        "garmin_email": None,
        "last_sync": None,
        "auth_state": "mfa_required",
        "mfa_challenge_id": "challenge-123",
        "mfa_expires_at": "2026-04-05T15:10:00Z",
        "mfa_delivery_hint": "Garmin sent a verification code to your email. Enter it to finish connecting.",
        "mfa_email_hint": "t***@g***.com",
    }


async def test_garmin_connect_mfa_completes_connection(client: AsyncClient, monkeypatch):
    async def _complete_mfa(user_id: int, challenge_id: str, code: str) -> str:
        assert user_id == 1
        assert challenge_id == "challenge-123"
        assert code == "123456"
        return "test@garmin.com"

    monkeypatch.setattr(health.settings, "garmin_enabled", True)
    monkeypatch.setattr(health, "complete_mfa_connect", _complete_mfa)

    resp = await client.post(
        "/api/health/garmin/connect/mfa",
        json={"challenge_id": "challenge-123", "code": "123456"},
    )

    assert resp.status_code == 201, resp.text
    assert resp.json() == {
        "connected": True,
        "user_id": 1,
        "garmin_email": "test@garmin.com",
        "last_sync": None,
        "auth_state": "connected",
        "mfa_challenge_id": None,
        "mfa_expires_at": None,
        "mfa_delivery_hint": None,
        "mfa_email_hint": None,
    }

    status_resp = await client.get("/api/health/garmin/auth-status")
    assert status_resp.status_code == 200, status_resp.text
    assert status_resp.json()["connected"] is True
    assert status_resp.json()["garmin_email"] == "test@garmin.com"


async def test_garmin_connect_maps_upstream_rate_limit_to_429(client: AsyncClient, monkeypatch):
    class _FakeResponse:
        status_code = 429

    class _FakeHttpError:
        response = _FakeResponse()

        def __str__(self) -> str:
            return "429 Too Many Requests"

    class _FakeGarthHttpError(Exception):
        def __init__(self) -> None:
            self.error = _FakeHttpError()

    async def _rate_limited(user_id: int, email: str, password: str) -> None:
        raise _FakeGarthHttpError()

    monkeypatch.setattr(health.settings, "garmin_enabled", True)
    monkeypatch.setattr(health, "connect_user", _rate_limited)

    resp = await client.post(
        "/api/health/garmin/connect",
        json={"email": "test@garmin.com", "password": "secret123"},
    )

    assert resp.status_code == 429, resp.text
    assert resp.json() == {
        "detail": "Garmin is temporarily rate limiting sign-in attempts. Wait 10 to 15 minutes, then try again.",
    }


def test_garmin_token_cache_is_encrypted_at_rest(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    token_dir = tmp_path / "tokens"
    source_dir.mkdir()
    token_dir.mkdir()
    monkeypatch.setattr(garmin_sync.settings, "garmin_token_dir", str(tmp_path))
    monkeypatch.setattr(garmin_sync.settings, "garmin_token_encryption_key", "unit-test-secret")

    oauth1_payload = {"token": "oauth1-secret"}
    oauth2_payload = {"token": "oauth2-secret"}
    (source_dir / "oauth1_token.json").write_text(json.dumps(oauth1_payload), encoding="utf-8")
    (source_dir / "oauth2_token.json").write_text(json.dumps(oauth2_payload), encoding="utf-8")

    garmin_sync._persist_tokenstore_dir(str(source_dir), str(token_dir))

    assert not (token_dir / "oauth1_token.json").exists()
    assert not (token_dir / "oauth2_token.json").exists()
    assert (token_dir / "oauth1_token.json.enc").exists()
    assert (token_dir / "oauth2_token.json.enc").exists()

    with garmin_sync._decrypted_tokenstore(str(token_dir)) as decrypted_dir:
        with open(f"{decrypted_dir}/oauth1_token.json", encoding="utf-8") as handle:
            assert json.load(handle) == oauth1_payload
        with open(f"{decrypted_dir}/oauth2_token.json", encoding="utf-8") as handle:
            assert json.load(handle) == oauth2_payload
