"""
Shared test fixtures for the NüMe API test suite.

Uses SQLite in-memory so no real PostgreSQL is required.
Clerk auth is replaced by a dependency override that returns a seeded test User.
The coordinator background task is patched to a no-op to avoid Gemini calls.
"""
from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# The app must be imported AFTER we've set a dummy DATABASE_URL so pydantic
# settings doesn't choke on a missing env var.
# ---------------------------------------------------------------------------
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CLERK_SECRET_KEY", "test")
os.environ.setdefault("CLERK_JWT_KEY", "test")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
os.environ.setdefault("OPENAI_API_VERSION", "2025-01-01-preview")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")

# Patch PostgreSQL-specific JSONB to plain JSON so SQLite can create the schema.
# This must happen before any model imports.
from sqlalchemy.types import JSON as _JSON
import sqlalchemy.dialects.postgresql as _pg
_pg.JSONB = _JSON  # type: ignore[assignment]

from main import app
from database import get_db, get_rate_limit_db
from auth import get_current_user
from models import Base, User

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


def _enable_wal(dbapi_conn, _):
    """Enable WAL mode and foreign keys for each SQLite connection."""
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DB_URL)
    event.listen(engine.sync_engine, "connect", _enable_wal)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _insert_user(db: AsyncSession, user_id: int, role: str = "member") -> User:
    u = User()
    u.id = user_id
    u.email = f"test-{user_id}@example.com"
    u.role = role
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """HTTP client wired to the app with a seeded member user (id=1) in the DB."""
    member = await _insert_user(db, user_id=1, role="member")
    # Also insert user 2 so FK-referencing tests can use it
    await _insert_user(db, user_id=2, role="member")
    await db.commit()

    async def _override_db():
        yield db

    assert db.bind is not None
    rate_limit_factory = async_sessionmaker(db.bind, class_=AsyncSession, expire_on_commit=False)

    async def _override_rate_limit_db():
        async with rate_limit_factory() as session:
            yield session

    def _override_user():
        return member

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_rate_limit_db] = _override_rate_limit_db
    app.dependency_overrides[get_current_user] = _override_user

    with patch("agent_runner.run_coordinator_for_run"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession):
    """HTTP client using an admin user (id=99, no profile in DB)."""
    admin = await _insert_user(db, user_id=99, role="admin")
    await db.commit()

    async def _override_db():
        yield db

    assert db.bind is not None
    rate_limit_factory = async_sessionmaker(db.bind, class_=AsyncSession, expire_on_commit=False)

    async def _override_rate_limit_db():
        async with rate_limit_factory() as session:
            yield session

    def _override_user():
        return admin

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_rate_limit_db] = _override_rate_limit_db
    app.dependency_overrides[get_current_user] = _override_user

    with patch("agent_runner.run_coordinator_for_run"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def coordinator_client(db: AsyncSession):
    """HTTP client using a coordinator user (id=50, no profile in DB)."""
    coordinator = await _insert_user(db, user_id=50, role="coordinator")
    await db.commit()

    async def _override_db():
        yield db

    assert db.bind is not None
    rate_limit_factory = async_sessionmaker(db.bind, class_=AsyncSession, expire_on_commit=False)

    async def _override_rate_limit_db():
        async with rate_limit_factory() as session:
            yield session

    def _override_user():
        return coordinator

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_rate_limit_db] = _override_rate_limit_db
    app.dependency_overrides[get_current_user] = _override_user

    with patch("agent_runner.run_coordinator_for_run"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()
