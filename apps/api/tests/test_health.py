from __future__ import annotations

import builtins
from datetime import date
from typing import Optional, get_type_hints
from unittest.mock import patch

from httpx import AsyncClient

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
