import os
from pathlib import Path
from uuid import uuid4

import cv2
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.integrations.media_storage import MediaStorageError, PresignedUpload, create_media_storage
from backend.app.models.camera_configuration import CameraConfiguration, CameraSession
from backend.app.models.media_asset import MediaAsset, MediaAssetStatus, MediaType
from backend.app.schemas.media_asset import MediaAssetResponse

media_asset_settings = get_settings()

_FORMATS = {
    ".mp4": (MediaType.VIDEO, {"video/mp4"}),
    ".mov": (MediaType.VIDEO, {"video/quicktime", "video/mp4"}),
    ".avi": (MediaType.VIDEO, {"video/x-msvideo", "video/avi"}),
    ".mkv": (MediaType.VIDEO, {"video/x-matroska", "video/mkv"}),
    ".jpg": (MediaType.IMAGE, {"image/jpeg"}),
    ".jpeg": (MediaType.IMAGE, {"image/jpeg"}),
    ".png": (MediaType.IMAGE, {"image/png"}),
}


class MediaAssetValidationError(ValueError):
    pass


class MediaAssetConflictError(RuntimeError):
    pass


class MediaAssetNotFoundError(LookupError):
    pass


class MediaAssetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, include_unready: bool) -> list[MediaAssetResponse]:
        statement = select(MediaAsset).order_by(MediaAsset.uploaded_at.desc(), MediaAsset.id)
        if not include_unready:
            statement = statement.where(MediaAsset.status == MediaAssetStatus.READY.value)
        return [self._response(asset) for asset in self.db.scalars(statement)]

    async def create(self, display_name: str, upload: UploadFile) -> MediaAssetResponse:
        display_name, extension, media_type, content_type = self._validate_metadata(
            display_name,
            upload.filename or "",
            upload.content_type or "",
        )

        asset_id = str(uuid4())
        filename = self._storage_key(asset_id, extension)
        directory = Path(media_asset_settings.media_asset_dir)
        directory.mkdir(parents=True, exist_ok=True)
        final_path = directory / filename
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = directory / f".{asset_id}.uploading"
        asset = MediaAsset(
            id=asset_id,
            display_name=display_name,
            media_type=media_type.value,
            status=MediaAssetStatus.UPLOADING.value,
            content_type=content_type,
            size_bytes=0,
            storage_filename=filename,
            storage_backend=media_asset_settings.media_storage_backend,
        )
        self.db.add(asset)
        self.db.commit()

        try:
            size = 0
            with temporary_path.open("xb") as target:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > media_asset_settings.max_media_asset_bytes:
                        raise MediaAssetValidationError("Media asset exceeds MAX_MEDIA_ASSET_BYTES")
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            if size == 0:
                raise MediaAssetValidationError("Media file is empty")
            if not self._decodes_first_frame(temporary_path, media_type):
                raise MediaAssetValidationError("Media file could not decode its first frame")
            if asset.storage_backend == "s3":
                create_media_storage(media_asset_settings).put_file(filename, temporary_path, content_type)
            os.replace(temporary_path, final_path)
            asset.size_bytes = size
            asset.status = MediaAssetStatus.READY.value
            self.db.commit()
        except Exception as exc:
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            asset.status = MediaAssetStatus.ERROR.value
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
            if isinstance(exc, MediaAssetValidationError):
                raise
            raise MediaAssetValidationError("Could not store media asset") from exc
        finally:
            await upload.close()
        return self._response(asset)

    def prepare_direct_upload(
        self,
        display_name: str,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> tuple[MediaAssetResponse, PresignedUpload]:
        if media_asset_settings.media_storage_backend != "s3":
            raise MediaAssetConflictError("direct_upload_unavailable")
        display_name, extension, media_type, content_type = self._validate_metadata(
            display_name,
            filename,
            content_type,
        )
        if size_bytes <= 0:
            raise MediaAssetValidationError("Media file is empty")
        if size_bytes > media_asset_settings.max_media_asset_bytes:
            raise MediaAssetValidationError("Media asset exceeds MAX_MEDIA_ASSET_BYTES")

        asset_id = str(uuid4())
        storage_key = self._storage_key(asset_id, extension)
        asset = MediaAsset(
            id=asset_id,
            display_name=display_name,
            media_type=media_type.value,
            status=MediaAssetStatus.UPLOADING.value,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_filename=storage_key,
            storage_backend="s3",
        )
        self.db.add(asset)
        self.db.commit()
        try:
            upload = create_media_storage(media_asset_settings).prepare_upload(
                storage_key,
                content_type,
                media_asset_settings.max_media_asset_bytes,
            )
        except MediaStorageError:
            asset.status = MediaAssetStatus.ERROR.value
            self.db.commit()
            raise MediaAssetValidationError("Could not prepare media upload") from None
        return self._response(asset), upload

    def complete_direct_upload(self, asset_id: str) -> MediaAssetResponse:
        asset = self.db.get(MediaAsset, asset_id)
        if asset is None or asset.storage_backend != "s3":
            raise MediaAssetNotFoundError("Media asset not found")
        if asset.status == MediaAssetStatus.READY.value:
            return self._response(asset)
        if asset.status != MediaAssetStatus.UPLOADING.value:
            raise MediaAssetConflictError("media_upload_not_pending")

        directory = Path(media_asset_settings.media_asset_dir)
        directory.mkdir(parents=True, exist_ok=True)
        final_path = directory / asset.storage_filename
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = directory / f".{asset.id}.{uuid4().hex}.validating"
        storage = create_media_storage(media_asset_settings)
        try:
            metadata = storage.head(asset.storage_filename)
            if metadata.size_bytes != asset.size_bytes or metadata.content_type != asset.content_type.casefold():
                raise MediaAssetValidationError("Uploaded media metadata does not match the request")
            temporary_path.parent.mkdir(parents=True, exist_ok=True)
            storage.download(asset.storage_filename, temporary_path)
            if not self._decodes_first_frame(temporary_path, MediaType(asset.media_type)):
                raise MediaAssetValidationError("Media file could not decode its first frame")
            os.replace(temporary_path, final_path)
            asset.status = MediaAssetStatus.READY.value
            self.db.commit()
        except Exception as exc:
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            asset.status = MediaAssetStatus.ERROR.value
            self.db.commit()
            try:
                storage.delete(asset.storage_filename)
            except MediaStorageError:
                pass
            if isinstance(exc, MediaAssetValidationError):
                raise
            raise MediaAssetValidationError("Could not validate uploaded media") from exc
        return self._response(asset)

    def get_ready_asset(self, asset_id: str) -> MediaAsset:
        asset = self.db.get(MediaAsset, asset_id)
        if asset is None or asset.status != MediaAssetStatus.READY.value:
            raise MediaAssetNotFoundError("Media asset not found")
        return asset

    def get_ready_path(self, asset_id: str) -> tuple[MediaAsset, Path]:
        asset = self.get_ready_asset(asset_id)
        path = Path(media_asset_settings.media_asset_dir) / asset.storage_filename
        if asset.storage_backend == "s3" and not path.is_file():
            temporary_path = path.with_name(f".{asset.id}.{uuid4().hex}.downloading")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                create_media_storage(media_asset_settings).download(asset.storage_filename, temporary_path)
                os.replace(temporary_path, path)
            except (OSError, MediaStorageError) as exc:
                temporary_path.unlink(missing_ok=True)
                raise MediaAssetNotFoundError("Media asset content not found") from exc
        if not path.is_file():
            raise MediaAssetNotFoundError("Media asset content not found")
        return asset, path

    def playback_url(self, asset_id: str) -> str:
        asset = self.get_ready_asset(asset_id)
        if asset.storage_backend != "s3":
            raise MediaAssetConflictError("direct_playback_unavailable")
        try:
            return create_media_storage(media_asset_settings).playback_url(asset.storage_filename)
        except MediaStorageError as exc:
            raise MediaAssetNotFoundError("Media asset content not found") from exc

    def delete(self, asset_id: str) -> None:
        asset = self.db.get(MediaAsset, asset_id)
        if asset is None:
            raise MediaAssetNotFoundError("Media asset not found")
        assigned = self.db.scalar(select(CameraConfiguration.camera_id).where(CameraConfiguration.asset_id == asset_id))
        referenced = self.db.scalar(select(CameraSession.id).where(CameraSession.asset_id == asset_id).limit(1))
        if assigned or referenced:
            raise MediaAssetConflictError("Assigned or referenced media assets cannot be deleted")
        path = Path(media_asset_settings.media_asset_dir) / asset.storage_filename
        tombstone = path.with_name(f".{path.name}.deleting")
        if path.exists():
            os.replace(path, tombstone)
        try:
            if asset.storage_backend == "s3":
                create_media_storage(media_asset_settings).delete(asset.storage_filename)
            self.db.delete(asset)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            if tombstone.exists():
                os.replace(tombstone, path)
            raise
        tombstone.unlink(missing_ok=True)

    @staticmethod
    def _validate_metadata(display_name: str, filename: str, content_type: str):
        display_name = display_name.strip()
        if not display_name or len(display_name) > 120:
            raise MediaAssetValidationError("display_name must contain 1 to 120 characters")
        extension = Path(filename).suffix.casefold()
        media_format = _FORMATS.get(extension)
        if media_format is None:
            raise MediaAssetValidationError("Unsupported media file extension")
        media_type, content_types = media_format
        content_type = content_type.casefold()
        if content_type not in content_types:
            raise MediaAssetValidationError("File MIME type does not match its extension")
        return display_name, extension, media_type, content_type

    @staticmethod
    def _storage_key(asset_id: str, extension: str) -> str:
        prefix = "media-assets/" if media_asset_settings.media_storage_backend == "s3" else ""
        return f"{prefix}{asset_id}{extension}"

    def _response(self, asset: MediaAsset) -> MediaAssetResponse:
        assigned_camera_id = self.db.scalar(
            select(CameraConfiguration.camera_id).where(CameraConfiguration.asset_id == asset.id)
        )
        referenced = self.db.scalar(select(CameraSession.id).where(CameraSession.asset_id == asset.id).limit(1))
        return MediaAssetResponse(
            id=asset.id,
            display_name=asset.display_name,
            media_type=asset.media_type,
            status=asset.status,
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
            storage_backend=asset.storage_backend,
            uploaded_at=asset.uploaded_at,
            assigned_camera_id=assigned_camera_id,
            can_delete=assigned_camera_id is None and referenced is None,
        )

    @staticmethod
    def _decodes_first_frame(path: Path, media_type: MediaType) -> bool:
        if media_type is MediaType.IMAGE:
            return cv2.imread(str(path), cv2.IMREAD_COLOR) is not None
        capture = cv2.VideoCapture(str(path))
        try:
            opened, frame = capture.read()
            return bool(opened and frame is not None and frame.size)
        finally:
            capture.release()
