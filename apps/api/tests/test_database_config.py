from __future__ import annotations

from sqlalchemy.pool import NullPool

from database import build_engine_kwargs, resolve_database_pool_mode
from settings import settings


def test_resolve_database_pool_mode_detects_supabase_transaction_pool():
    database_url = "postgresql+asyncpg://postgres:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

    assert resolve_database_pool_mode(database_url, "auto") == "transaction"


def test_build_engine_kwargs_uses_null_pool_for_transaction_pooling(monkeypatch):
    monkeypatch.setattr(settings, "database_pool_mode", "auto")
    monkeypatch.setattr(settings, "database_command_timeout_seconds", 45)
    monkeypatch.setattr(settings, "database_statement_cache_size", 123)

    kwargs = build_engine_kwargs(
        "postgresql+asyncpg://postgres:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    )

    assert kwargs["poolclass"] is NullPool
    assert kwargs["connect_args"]["command_timeout"] == 45
    assert kwargs["connect_args"]["statement_cache_size"] == 0


def test_build_engine_kwargs_uses_sqlalchemy_pooling_for_persistent_postgres(monkeypatch):
    monkeypatch.setattr(settings, "database_pool_mode", "pooled")
    monkeypatch.setattr(settings, "database_pool_size", 7)
    monkeypatch.setattr(settings, "database_max_overflow", 11)
    monkeypatch.setattr(settings, "database_pool_timeout_seconds", 33)
    monkeypatch.setattr(settings, "database_pool_recycle_seconds", 777)
    monkeypatch.setattr(settings, "database_statement_cache_size", 222)

    kwargs = build_engine_kwargs("postgresql+asyncpg://postgres:secret@db.internal:5432/postgres")

    assert kwargs["pool_size"] == 7
    assert kwargs["max_overflow"] == 11
    assert kwargs["pool_timeout"] == 33
    assert kwargs["pool_recycle"] == 777
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["connect_args"]["statement_cache_size"] == 222
