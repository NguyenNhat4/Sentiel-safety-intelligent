from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_authenticated_user, require_system_admin
from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.media_asset import MediaAssetResponse
from backend.app.services.media_asset_service import (
    MediaAssetConflictError,
    MediaAssetNotFoundError,
    MediaAssetService,
    MediaAssetValidationError,
)

router = APIRouter(prefix="/media-assets", tags=["Media Assets"])


@router.get("", response_model=list[MediaAssetResponse])
def list_media_assets(
    actor: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return MediaAssetService(db).list(include_unready=actor.role == UserRole.SYSTEM_ADMIN.value)


@router.post("", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_media_asset(
    display_name: str = Form(...),
    file: UploadFile = File(...),
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    try:
        return await MediaAssetService(db).create(display_name, file)
    except MediaAssetValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_media_asset", "message": str(exc)}) from exc


@router.get("/{asset_id}/content")
def get_media_asset_content(
    asset_id: str,
    range_header: str | None = Header(default=None, alias="Range"),
    _: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    try:
        asset, path = MediaAssetService(db).get_ready_path(asset_id)
    except MediaAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Media asset not found") from exc
    size = asset.size_bytes
    start, end, partial = _parse_range(range_header, size)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Cache-Control": "private, max-age=3600",
    }
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(
        _read_range(path, start, end),
        status_code=206 if partial else 200,
        media_type=asset.content_type,
        headers=headers,
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media_asset(
    asset_id: str,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    try:
        MediaAssetService(db).delete(asset_id)
    except MediaAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Media asset not found") from exc
    except MediaAssetConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "media_asset_in_use"}) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _parse_range(value: str | None, size: int) -> tuple[int, int, bool]:
    if value is None:
        return 0, size - 1, False
    try:
        unit, requested = value.split("=", 1)
        if unit.casefold() != "bytes" or "," in requested:
            raise ValueError
        first, last = requested.split("-", 1)
        if first:
            start = int(first)
            end = int(last) if last else size - 1
        else:
            suffix = int(last)
            if suffix <= 0:
                raise ValueError
            start = max(0, size - suffix)
            end = size - 1
        if start < 0 or start >= size or end < start:
            raise ValueError
        return start, min(end, size - 1), True
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=416,
            detail="Requested range is not satisfiable",
            headers={"Content-Range": f"bytes */{size}"},
        ) from None


def _read_range(path: Path, start: int, end: int) -> Iterator[bytes]:
    remaining = end - start + 1
    with path.open("rb") as source:
        source.seek(start)
        while remaining:
            chunk = source.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
