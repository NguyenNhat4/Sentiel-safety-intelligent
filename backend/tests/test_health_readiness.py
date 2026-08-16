from types import SimpleNamespace

import pytest

from backend.app import main


def _set_ready_runtime(monkeypatch):
    monkeypatch.setattr(
        main,
        "database_runtime",
        SimpleNamespace(backend="postgresql", fallback_active=False),
    )
    monkeypatch.setattr(main.settings, "snapshot_storage_backend", "s3")
    main.app.state.ready = True
    main.app.state.runtime_files = {"data_writable": True, "models_verified": True}


@pytest.mark.asyncio
async def test_health_is_ready_only_when_postgresql_and_s3_are_available(monkeypatch):
    _set_ready_runtime(monkeypatch)
    monkeypatch.setattr(main, "check_database_connection", lambda _: None)
    monkeypatch.setattr(main, "check_snapshot_storage_connection", lambda _: None)

    response = await main.health_check()

    assert response.status == "ok"
    assert response.ready is True
    assert response.dependencies["postgresql"].ready is True
    assert response.dependencies["snapshot_storage"].ready is True


@pytest.mark.asyncio
async def test_health_identifies_unavailable_postgresql_without_leaking_exception(monkeypatch):
    _set_ready_runtime(monkeypatch)
    monkeypatch.setattr(
        main, "check_database_connection", lambda _: (_ for _ in ()).throw(ConnectionError("secret host"))
    )
    monkeypatch.setattr(main, "check_snapshot_storage_connection", lambda _: None)

    response = await main.health_check()

    assert response.status == "degraded"
    assert response.ready is False
    assert response.dependencies["postgresql"].ready is False
    assert response.dependencies["postgresql"].reason == "connection_failed"
    assert "secret host" not in str(response)


@pytest.mark.asyncio
async def test_health_identifies_unavailable_s3_without_leaking_exception(monkeypatch):
    _set_ready_runtime(monkeypatch)
    monkeypatch.setattr(main, "check_database_connection", lambda _: None)
    monkeypatch.setattr(
        main, "check_snapshot_storage_connection", lambda _: (_ for _ in ()).throw(ConnectionError("secret endpoint"))
    )

    response = await main.health_check()

    assert response.status == "degraded"
    assert response.ready is False
    assert response.dependencies["snapshot_storage"].ready is False
    assert response.dependencies["snapshot_storage"].reason == "connection_failed"
    assert "secret endpoint" not in str(response)
