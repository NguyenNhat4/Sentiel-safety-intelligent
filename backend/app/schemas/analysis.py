from typing import Any, Literal

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


class ZonePoint(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class FrameInferenceRequest(BaseModel):
    image_data: str = Field(..., description="Base64 JPEG data URL")
    zone_points: list[ZonePoint] = Field(default_factory=list, max_length=4)
    machine_state: Literal["running", "stopped"] = "running"
    camera_id: str = Field(default="uploaded_video", min_length=1, max_length=50)
    zone_id: str = Field(default="zone_01", min_length=1, max_length=50)


class PpeObservation(BaseModel):
    status: Literal["present", "missing", "unknown"]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class PersonPpeObservations(BaseModel):
    helmet: PpeObservation
    safety_glasses: PpeObservation
    gloves: PpeObservation


class ModelDetection(BaseModel):
    class_id: int = Field(..., ge=0, le=16)
    class_name: str = Field(..., min_length=1)
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    person_index: int | None = Field(default=None, ge=0)


class PersonDetection(BaseModel):
    bbox: list[int]
    confidence: float
    foot_point: list[int]
    inside_zone: bool
    safety_shirt: bool
    ppe: PersonPpeObservations
    missing_required_ppe: list[Literal["helmet", "safety_glasses", "gloves"]] = Field(default_factory=list)


class FrameInferenceResponse(BaseModel):
    result: Literal["normal", "violate"]
    review_required: bool
    people: list[PersonDetection]
    detections: list[ModelDetection] = Field(default_factory=list)
    snapshot_data: str | None = None
    rule: dict[str, Any]


class InferenceWebSocketConfigure(BaseModel):
    type: Literal["configure"]
    zone_points: list[ZonePoint] = Field(default_factory=list, max_length=4)
    machine_state: Literal["running", "stopped"] = "running"
    camera_id: str = Field(default="uploaded_video", min_length=1, max_length=50)
    zone_id: str = Field(default="zone_01", min_length=1, max_length=50)


class InferenceWebSocketFrameMeta(BaseModel):
    type: Literal["frame_meta"]
    frame_id: int = Field(..., ge=0)
    video_time: float = Field(..., ge=0.0)
