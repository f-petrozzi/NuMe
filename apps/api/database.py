from __future__ import annotations

from typing import Any

from sqlalchemy.engine import make_url
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from settings import settings


def resolve_database_pool_mode(database_url: str, configured_mode: str) -> str:
    if configured_mode != "auto":
        return configured_mode

    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        return "null"
    if url.port == 6543:
        return "transaction"
    return "pooled"


def build_engine_kwargs(database_url: str) -> dict[str, Any]:
    url = make_url(database_url)
    pool_mode = resolve_database_pool_mode(database_url, settings.database_pool_mode)
    connect_args: dict[str, Any] = {}

    if url.drivername.startswith("postgresql+asyncpg"):
        connect_args["command_timeout"] = settings.database_command_timeout_seconds
        if pool_mode == "transaction":
            # Supabase transaction pooling does not support prepared statements.
            connect_args["statement_cache_size"] = 0
        else:
            connect_args["statement_cache_size"] = settings.database_statement_cache_size

    engine_kwargs: dict[str, Any] = {"echo": False, "connect_args": connect_args}
    if url.drivername.startswith("sqlite") or pool_mode in {"transaction", "null"}:
        engine_kwargs["poolclass"] = NullPool
        return engine_kwargs

    engine_kwargs.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
        pool_pre_ping=True,
    )
    return engine_kwargs


_engine_kwargs = build_engine_kwargs(settings.database_url)

engine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_rate_limit_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Separate session source for rate-limit accounting.

    The auth path already touches the main request session. Keeping limiter
    writes on their own session avoids nested transaction failures and makes the
    accounting transaction independent from request-scoped ORM work.
    """
    async with AsyncSessionLocal() as session:
        yield session
