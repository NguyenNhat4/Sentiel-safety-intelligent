from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.schemas.monitoring_zone import MonitoringZone, ZonePoint


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


class FrameInferenceRequest(BaseModel):
    image_data: str = Field(..., description="Base64 JPEG data URL")
    zone_points: list[ZonePoint] = Field(default_factory=list, max_length=4)
    machine_state: Literal["running", "stopped"] = "running"
    camera_id: str = Field(default="uploaded_video", min_length=1, max_length=50)
    zone_id: str = Field(default="zone_01", min_length=1, max_length=50)
    zones: list[MonitoringZone] | None = None
    zone_revision: int | None = Field(default=None, ge=0)
    monitoring_session_id: UUID | None = None
    frame_id: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_session_frame_pair(self):
        if (self.monitoring_session_id is None) != (self.frame_id is None):
            raise ValueError("monitoring_session_id and frame_id must be provided together")
        if self.zones is not None and {"zone_points", "zone_id"} & self.model_fields_set:
            raise ValueError("Use either legacy zone fields or zones, not both")
        if self.zones is None and "zone_revision" in self.model_fields_set:
            raise ValueError("zone_revision is only valid with zones")
        return self


class PpeObservation(BaseModel):
    status: Literal["present", "missing", "unknown"]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class PersonPpeObservations(BaseModel):
    hat: PpeObservation
    vest: PpeObservation


class ModelDetection(BaseModel):
    class_id: Literal[0, 3, 4]
    class_name: Literal["hat", "person", "vest"]
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    person_index: int | None = Field(default=None, ge=0)


class ActiveViolation(BaseModel):
    occurrence_id: UUID
    rule_key: str
    zone_id: str | None = None
    is_new: bool


class ZoneMembership(BaseModel):
    zone_id: str
    inside: bool


class PersonDetection(BaseModel):
    track_id: int | None = Field(default=None, ge=1)
    bbox: list[int]
    confidence: float
    foot_point: list[int]
    inside_zone: bool
    zone_memberships: list[ZoneMembership] = Field(default_factory=list)
    ppe: PersonPpeObservations
    missing_required_ppe: list[Literal["hat", "vest"]] = Field(default_factory=list)
    active_violations: list[ActiveViolation] = Field(default_factory=list)


class FrameInferenceResponse(BaseModel):
    result: Literal["normal", "violate"]
    review_required: bool
    has_active_violation: bool
    people: list[PersonDetection]
    detections: list[ModelDetection] = Field(default_factory=list)
    snapshot_data: str | None = None
    rule: dict[str, Any]


class InferenceWebSocketConfigure(BaseModel):
    type: Literal["configure"]
    monitoring_session_id: UUID
    zone_points: list[ZonePoint] = Field(default_factory=list, max_length=4)
    machine_state: Literal["running", "stopped"] = "running"
    camera_id: str = Field(default="uploaded_video", min_length=1, max_length=50)
    zone_id: str = Field(default="zone_01", min_length=1, max_length=50)
    zones: list[MonitoringZone] | None = None
    zone_revision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_configuration_mode(self):
        if self.zones is not None and {"zone_points", "zone_id"} & self.model_fields_set:
            raise ValueError("Use either legacy zone fields or zones, not both")
        if self.zones is None and "zone_revision" in self.model_fields_set:
            raise ValueError("zone_revision is only valid with zones")
        return self

    @field_validator("zone_points")
    @classmethod
    def require_empty_or_four_point_zone(cls, value: list[ZonePoint]) -> list[ZonePoint]:
        if len(value) not in (0, 4):
            raise ValueError("zone_points must contain zero or four points")
        return value


class InferenceWebSocketFrameMeta(BaseModel):
    type: Literal["frame_meta"]
    frame_id: int = Field(..., ge=0)
    video_time: float = Field(..., ge=0.0)
