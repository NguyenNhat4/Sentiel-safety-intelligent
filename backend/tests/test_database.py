from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.app.core import database


def sqlite_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_primary_database_is_selected_when_reachable(monkeypatch):
    primary = sqlite_engine()
    monkeypatch.setattr(database, "_create_engine", lambda url: primary)
    runtime = database.create_database_runtime("postgresql://primary", "sqlite:///fallback.db", True)
    assert runtime.engine is primary
    assert runtime.backend == "postgresql"
    assert runtime.fallback_active is False


def test_sqlite_fallback_is_selected_when_primary_is_unreachable(monkeypatch):
    primary = SimpleNamespace(dispose=lambda: None)
    fallback = sqlite_engine()
    engines = iter((primary, fallback))
    monkeypatch.setattr(database, "_create_engine", lambda url: next(engines))

    def verify(candidate):
        if candidate is primary:
            raise ConnectionError("offline")

    monkeypatch.setattr(database, "_verify_connection", verify)
    runtime = database.create_database_runtime("postgresql://primary", "sqlite:///fallback.db", True)
    assert runtime.engine is fallback
    assert runtime.backend == "sqlite_fallback"
    assert runtime.fallback_active is True


def test_unreachable_primary_raises_when_fallback_is_disabled(monkeypatch):
    primary = SimpleNamespace(dispose=lambda: None)
    monkeypatch.setattr(database, "_create_engine", lambda url: primary)

    def unavailable(candidate):
        raise ConnectionError("offline")

    monkeypatch.setattr(database, "_verify_connection", unavailable)
    with pytest.raises(ConnectionError):
        database.create_database_runtime("postgresql://primary", "sqlite:///fallback.db", False)


def test_postgresql_engine_reuses_warm_connections_without_pre_ping(monkeypatch):
    captured = {}
    monkeypatch.setattr(database.settings, "database_pool_pre_ping", False)

    def capture_create_engine(url, **kwargs):
        captured.update(url=url, **kwargs)
        return object()

    monkeypatch.setattr(database, "create_engine", capture_create_engine)
    database._create_engine("postgresql://primary")

    assert captured["pool_pre_ping"] is False
    assert captured["pool_use_lifo"] is True
    assert captured["pool_recycle"] == database.settings.database_pool_recycle_seconds
    assert captured["connect_args"]["keepalives"] == 1


def test_runtime_sessions_keep_loaded_values_after_commit():
    assert database.SessionLocal.kw["expire_on_commit"] is False
