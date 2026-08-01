from typing import Any

from pydantic import BaseModel, Field


class StartAnalysisRequest(BaseModel):
    source_type: str = Field(..., description="video_file, rtsp_stream, or demo")
    source_path: str = Field(..., description="File path or RTSP URL")
    zone_ids: list[str] = Field(default_factory=lambda: ["zone_01"])
    enable_privacy_blur: bool = True
    conf_threshold: float = 0.5


class AnalysisStatusResponse(BaseModel):
    session_id: str
    status: str  # running, stopped, error, completed
    fps: float = 0.0
    processed_frames: int = 0
    total_frames: int | None = None
    active_violations_count: int = 0
    current_timestamp: str | None = None
    metadata: dict[str, Any] | None = None
