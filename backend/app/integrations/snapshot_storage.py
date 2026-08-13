"""Provider boundary for server-owned redacted snapshot bytes."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol


class SnapshotStorageError(RuntimeError):
    """A bounded storage error safe to return through application services."""


class SnapshotStorage(Protocol):
    def put(self, content: bytes) -> str: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


def new_snapshot_key() -> str:
    return f"snapshots/{uuid.uuid4().hex}.jpg"


class FilesystemSnapshotStorage:
    def __init__(self, directory: Path):
        self._directory = directory

    def put(self, content: bytes) -> str:
        key = new_snapshot_key()
        target = self._path(key)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as exc:
            raise SnapshotStorageError("Could not persist the redacted snapshot") from exc
        return key

    def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except OSError as exc:
            raise SnapshotStorageError("Could not read the redacted snapshot") from exc

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError as exc:
            raise SnapshotStorageError("Could not delete the redacted snapshot") from exc

    def _path(self, key: str) -> Path:
        name = Path(key).name
        if not name.endswith(".jpg"):
            raise SnapshotStorageError("Invalid snapshot key")
        return self._directory / name


class S3SnapshotStorage:
    def __init__(self, *, bucket: str, endpoint_url: str, region: str, access_key_id: str, secret_access_key: str):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - dependency setup is verified separately
            raise SnapshotStorageError("S3 snapshot storage dependency is unavailable") from exc
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def put(self, content: bytes) -> str:
        key = new_snapshot_key()
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=content, ContentType="image/jpeg")
        except Exception as exc:
            raise SnapshotStorageError("Could not persist the redacted snapshot") from exc
        return key

    def get(self, key: str) -> bytes:
        try:
            return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()
        except Exception as exc:
            raise SnapshotStorageError("Could not read the redacted snapshot") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise SnapshotStorageError("Could not delete the redacted snapshot") from exc


def create_snapshot_storage(settings) -> SnapshotStorage:
    settings.validate_snapshot_storage()
    if settings.snapshot_storage_backend == "filesystem":
        return FilesystemSnapshotStorage(Path(settings.snapshot_dir))
    return S3SnapshotStorage(
        bucket=settings.snapshot_storage_bucket,
        endpoint_url=settings.snapshot_storage_endpoint_url,
        region=settings.snapshot_storage_region,
        access_key_id=settings.snapshot_storage_access_key_id,
        secret_access_key=settings.snapshot_storage_secret_access_key,
    )
