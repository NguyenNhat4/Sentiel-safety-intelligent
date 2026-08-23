import os
from pathlib import Path
from uuid import uuid4

import cv2
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
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
        display_name = display_name.strip()
        if not display_name or len(display_name) > 120:
            raise MediaAssetValidationError("display_name must contain 1 to 120 characters")
        extension = Path(upload.filename or "").suffix.casefold()
        media_format = _FORMATS.get(extension)
        if media_format is None:
            raise MediaAssetValidationError("Unsupported media file extension")
        media_type, content_types = media_format
        content_type = (upload.content_type or "").casefold()
        if content_type not in content_types:
            raise MediaAssetValidationError("File MIME type does not match its extension")

        asset_id = str(uuid4())
        filename = f"{asset_id}{extension}"
        directory = Path(media_asset_settings.media_asset_dir)
        directory.mkdir(parents=True, exist_ok=True)
        final_path = directory / filename
        temporary_path = directory / f".{asset_id}.uploading"
        asset = MediaAsset(
            id=asset_id,
            display_name=display_name,
            media_type=media_type.value,
            status=MediaAssetStatus.UPLOADING.value,
            content_type=content_type,
            size_bytes=0,
            storage_filename=filename,
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

    def get_ready_path(self, asset_id: str) -> tuple[MediaAsset, Path]:
        asset = self.db.get(MediaAsset, asset_id)
        if asset is None or asset.status != MediaAssetStatus.READY.value:
            raise MediaAssetNotFoundError("Media asset not found")
        path = Path(media_asset_settings.media_asset_dir) / asset.storage_filename
        if not path.is_file():
            raise MediaAssetNotFoundError("Media asset content not found")
        return asset, path

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
            self.db.delete(asset)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            if tombstone.exists():
                os.replace(tombstone, path)
            raise
        tombstone.unlink(missing_ok=True)

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
