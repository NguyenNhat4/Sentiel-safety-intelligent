import pytest
from fastapi import HTTPException

from backend.app.core.config import Settings
from backend.app.integrations.snapshot_storage import (
    FilesystemSnapshotStorage,
    S3SnapshotStorage,
    SnapshotStorageError,
    create_snapshot_storage,
)


def test_filesystem_snapshot_storage_round_trip_and_uses_opaque_key(tmp_path):
    storage = FilesystemSnapshotStorage(tmp_path)

    key = storage.put(b"redacted-jpeg")

    assert key.startswith("snapshots/")
    assert key.endswith(".jpg")
    assert storage.get(key) == b"redacted-jpeg"
    storage.delete(key)
    with pytest.raises(SnapshotStorageError):
        storage.get(key)


def test_s3_storage_requires_complete_runtime_configuration():
    settings = Settings(
        snapshot_storage_backend="s3",
        snapshot_storage_bucket="",
        snapshot_storage_endpoint_url="",
        snapshot_storage_access_key_id="",
        snapshot_storage_secret_access_key="",
    )

    with pytest.raises(ValueError, match="SNAPSHOT_STORAGE_BUCKET"):
        create_snapshot_storage(settings)


def test_s3_storage_readiness_uses_head_bucket_without_writing_an_object():
    class Client:
        def __init__(self):
            self.calls = []

        def head_bucket(self, **kwargs):
            self.calls.append(kwargs["Bucket"])

    client = Client()
    storage = object.__new__(S3SnapshotStorage)
    storage._bucket = "redacted-snapshots"
    storage._client = client

    storage.check_connection()

    assert client.calls == ["redacted-snapshots"]


@pytest.mark.asyncio
async def test_snapshot_route_serves_the_configured_storage_object(monkeypatch):
    class Storage:
        def get(self, key: str) -> bytes:
            assert key == "snapshots/event-redacted.jpg"
            return b"redacted-jpeg"

    from backend.app import main

    monkeypatch.setattr(main, "create_snapshot_storage", lambda _: Storage())
    response = await main.get_snapshot("event-redacted.jpg")

    assert response.status_code == 200
    assert response.body == b"redacted-jpeg"
    assert response.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_snapshot_route_rejects_path_traversal():
    from backend.app.main import get_snapshot

    with pytest.raises(HTTPException, match="Snapshot not found") as exc_info:
        await get_snapshot("../secret.jpg")

    assert exc_info.value.status_code == 404
