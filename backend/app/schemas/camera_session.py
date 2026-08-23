from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SessionStatus = Literal["STARTING", "RUNNING", "COMPLETED", "ERROR", "STOPPED"]


class CameraSessionResponse(BaseModel):
    id: UUID
    camera_id: str
    asset_id: UUID
    media_type: Literal["video", "image"]
    status: SessionStatus
    config_revision: int
    inference_fps: float
    started_at: datetime
    running_at: datetime | None
    completed_at: datetime | None
    error_code: str | None


class SimulationRunResponse(BaseModel):
    sessions: list[CameraSessionResponse]
    errors: dict[str, str]
