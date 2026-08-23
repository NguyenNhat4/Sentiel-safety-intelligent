"""S3-compatible object storage boundary for backend-owned media assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class MediaStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    fields: dict[str, str]


@dataclass(frozen=True)
class StoredObjectMetadata:
    size_bytes: int
    content_type: str


class S3MediaStorage:
    def __init__(self, *, bucket: str, endpoint_url: str, region: str, access_key_id: str, secret_access_key: str):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - dependency setup is verified separately
            raise MediaStorageError("S3 media storage dependency is unavailable") from exc
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def prepare_upload(self, key: str, content_type: str, max_bytes: int) -> PresignedUpload:
        try:
            payload = self._client.generate_presigned_post(
                Bucket=self._bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=[{"Content-Type": content_type}, ["content-length-range", 1, max_bytes]],
                ExpiresIn=900,
            )
        except Exception as exc:
            raise MediaStorageError("Could not prepare media upload") from exc
        return PresignedUpload(url=payload["url"], fields=payload["fields"])

    def head(self, key: str) -> StoredObjectMetadata:
        try:
            payload = self._client.head_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise MediaStorageError("Could not verify uploaded media") from exc
        return StoredObjectMetadata(
            size_bytes=int(payload["ContentLength"]),
            content_type=str(payload.get("ContentType") or "").casefold(),
        )

    def put_file(self, key: str, path: Path, content_type: str) -> None:
        try:
            self._client.upload_file(str(path), self._bucket, key, ExtraArgs={"ContentType": content_type})
        except Exception as exc:
            raise MediaStorageError("Could not store media asset") from exc

    def download(self, key: str, path: Path) -> None:
        try:
            self._client.download_file(self._bucket, key, str(path))
        except Exception as exc:
            raise MediaStorageError("Could not read media asset") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise MediaStorageError("Could not delete media asset") from exc

    def playback_url(self, key: str) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=3600,
            )
        except Exception as exc:
            raise MediaStorageError("Could not prepare media playback") from exc


def create_media_storage(settings) -> S3MediaStorage:
    settings.validate_media_storage()
    return S3MediaStorage(
        bucket=settings.media_storage_bucket,
        endpoint_url=settings.media_storage_endpoint_url,
        region=settings.media_storage_region,
        access_key_id=settings.media_storage_access_key_id,
        secret_access_key=settings.media_storage_secret_access_key,
    )
