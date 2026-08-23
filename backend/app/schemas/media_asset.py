from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class MediaAssetResponse(BaseModel):
    id: UUID
    display_name: str
    media_type: Literal["video", "image"]
    status: Literal["UPLOADING", "READY", "ERROR"]
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    assigned_camera_id: str | None = None
    can_delete: bool = False
