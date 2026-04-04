from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from main import app
from models import AgentMessage, AgentRun, AuditLog, PersonalizationStateSnapshot, User
from settings import settings


@asynccontextmanager
async def _internal_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _internal_headers(*, api_key: str, user_id: int) -> dict[str, str]:
    return {
        "X-Internal-Api-Key": api_key,
        "X-Internal-User-Id": str(user_id),
    }


@pytest.mark.asyncio
async def test_internal_auth_me_returns_acting_user(db: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    user = User(id=7, email="internal@example.com", role="member")
    db.add(user)
    await db.commit()

    monkeypatch.setattr(settings, "internal_api_token", "test-internal-token")

    async with _internal_client(db) as client:
        response = await client.get(
            "/api/auth/me",
            headers=_internal_headers(api_key="test-internal-token", user_id=user.id),
        )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == user.id
    assert response.json()["email"] == "internal@example.com"


@pytest.mark.asyncio
async def test_internal_auth_rejects_bad_api_key(db: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    user = User(id=8, email="bad-key@example.com", role="member")
    db.add(user)
    await db.commit()

    monkeypatch.setattr(settings, "internal_api_token", "expected-token")

    async with _internal_client(db) as client:
        response = await client.get(
            "/api/auth/me",
            headers=_internal_headers(api_key="wrong-token", user_id=user.id),
        )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Invalid internal API token"


@pytest.mark.asyncio
async def test_internal_auth_supports_run_failure_persistence(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    user = User(id=9, email="runner@example.com", role="member")
    db.add(user)
    await db.flush()

    run = AgentRun(user_id=user.id, status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    monkeypatch.setattr(settings, "internal_api_token", "test-internal-token")
    headers = _internal_headers(api_key="test-internal-token", user_id=user.id)

    async with _internal_client(db) as client:
        message_response = await client.post(
            "/api/runs/messages",
            headers=headers,
            json={
                "run_id": run.id,
                "agent_name": "ValidationLoop",
                "agent_type": "loop",
                "input": {"attempt": 1},
                "output": {"status": "ok"},
                "iteration": 1,
            },
        )
        update_response = await client.put(
            f"/api/runs/{run.id}",
            headers=headers,
            json={"status": "failed"},
        )
        audit_response = await client.post(
            "/api/audit-logs",
            headers=headers,
            json={
                "user_id": user.id,
                "action": "agent_failed",
                "entity_type": "agent_run",
                "entity_id": str(run.id),
                "metadata": {"error": "RuntimeError: boom"},
            },
        )

    assert message_response.status_code == 201, message_response.text
    assert update_response.status_code == 200, update_response.text
    assert audit_response.status_code == 201, audit_response.text

    refreshed_run = await db.get(AgentRun, run.id)
    assert refreshed_run is not None
    assert refreshed_run.status == "failed"

    messages = (await db.execute(select(AgentMessage).where(AgentMessage.run_id == run.id))).scalars().all()
    assert len(messages) == 1
    assert messages[0].agent_name == "ValidationLoop"

    audits = (await db.execute(select(AuditLog).where(AuditLog.entity_id == str(run.id)))).scalars().all()
    assert len(audits) == 1
    assert audits[0].user_id == user.id


@pytest.mark.asyncio
async def test_internal_auth_can_build_personalization_context(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    user = User(id=10, email="personalization@example.com", role="member")
    db.add(user)
    await db.commit()

    monkeypatch.setattr(settings, "internal_api_token", "test-internal-token")

    async with _internal_client(db) as client:
        response = await client.get(
            "/api/personalization/context",
            params={"scenario": "stressed_student"},
            headers=_internal_headers(api_key="test-internal-token", user_id=user.id),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_id"] == user.id
    assert body["persona_type"] == "student"
    assert body["snapshot_id"] is not None

    snapshot = await db.get(PersonalizationStateSnapshot, body["snapshot_id"])
    assert snapshot is not None
    assert snapshot.user_id == user.id
