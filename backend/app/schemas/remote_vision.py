from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRACT_VERSION = "safety_vision_v1"
CONTRACT_VERSION_V2 = "safety_vision_v2"
TRACKING_STATE_SCHEMA_VERSION = "bytetrack_ppe_state_v1"


class RemotePpeObservation(BaseModel):
    status: Literal["present", "unknown"]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class RemotePersonPpeObservations(BaseModel):
    hat: RemotePpeObservation
    vest: RemotePpeObservation


class RemoteCanonicalPerson(BaseModel):
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    track_id: int = Field(..., ge=1)

    @field_validator("bbox")
    @classmethod
    def validate_xywh_bbox(cls, bbox: list[int]) -> list[int]:
        x, y, width, height = bbox
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError("canonical person bbox must be non-negative xywh with positive size")
        return bbox


class RemoteModelDetection(BaseModel):
    class_id: Literal[0, 3, 4]
    class_name: Literal["hat", "person", "vest"]
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    person_index: int | None = Field(default=None, ge=0)

    @field_validator("bbox")
    @classmethod
    def validate_xyxy_bbox(cls, bbox: list[int]) -> list[int]:
        x1, y1, x2, y2 = bbox
        if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
            raise ValueError("detection bbox must be non-negative ordered xyxy")
        return bbox

    @model_validator(mode="after")
    def validate_class_mapping(self):
        expected_name = {0: "hat", 3: "person", 4: "vest"}[self.class_id]
        if self.class_name != expected_name:
            raise ValueError("class_id and class_name do not match")
        return self


class RemoteVisionResponse(BaseModel):
    contract_version: Literal["safety_vision_v1"] = CONTRACT_VERSION
    request_id: UUID
    model_version: str = Field(..., min_length=1, max_length=200)
    canonical_people: list[RemoteCanonicalPerson]
    people: list[RemotePersonPpeObservations]
    detections: list[RemoteModelDetection]

    @model_validator(mode="after")
    def validate_person_references(self):
        if len(self.people) != len(self.canonical_people):
            raise ValueError("people and canonical_people must have equal length")
        for detection in self.detections:
            if detection.person_index is not None and detection.person_index >= len(self.people):
                raise ValueError("detection person_index is out of range")
        return self


class RemoteVisionHealth(BaseModel):
    status: Literal["healthy"] = "healthy"
    contract_version: Literal["safety_vision_v1"] = CONTRACT_VERSION
    model_version: str = Field(..., min_length=1, max_length=200)


class _StrictStateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RemoteByteTrackEntry(_StrictStateModel):
    track_id: int = Field(..., ge=1)
    tlwh: list[float] = Field(..., min_length=4, max_length=4)
    mean: list[float] = Field(..., min_length=8, max_length=8)
    covariance: list[list[float]] = Field(..., min_length=8, max_length=8)
    is_activated: bool
    state: Literal[0, 1, 2, 3]
    score: float = Field(..., ge=0.0, le=1.0)
    start_frame: int = Field(..., ge=0)
    frame_id: int = Field(..., ge=0)
    tracklet_len: int = Field(..., ge=0)
    class_id: Literal[0, 3, 4]
    detection_index: int = Field(..., ge=0)
    angle: float | None = None

    @field_validator("tlwh")
    @classmethod
    def validate_tlwh(cls, value: list[float]) -> list[float]:
        if value[2] <= 0 or value[3] <= 0:
            raise ValueError("track tlwh width and height must be positive")
        return value

    @field_validator("covariance")
    @classmethod
    def validate_covariance(cls, value: list[list[float]]) -> list[list[float]]:
        if any(len(row) != 8 for row in value):
            raise ValueError("track covariance must be 8x8")
        return value


class RemoteByteTrackerState(_StrictStateModel):
    frame_id: int = Field(..., ge=0)
    last_track_id: int = Field(..., ge=0)
    tracked: list[RemoteByteTrackEntry] = Field(default_factory=list, max_length=256)
    lost: list[RemoteByteTrackEntry] = Field(default_factory=list, max_length=256)

    @model_validator(mode="after")
    def validate_track_identity(self):
        entries = [*self.tracked, *self.lost]
        if len(entries) > 256:
            raise ValueError("tracking state retains at most 256 tracks")
        track_ids = [entry.track_id for entry in entries]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("tracking state track IDs must be unique")
        if track_ids and self.last_track_id < max(track_ids):
            raise ValueError("last_track_id cannot precede a retained track ID")
        if any(entry.state != 1 for entry in self.tracked):
            raise ValueError("tracked pool may contain only active tracks")
        if any(entry.state != 2 for entry in self.lost):
            raise ValueError("lost pool may contain only recoverable lost tracks")
        return self


class RemotePpeSmootherEntry(_StrictStateModel):
    track_id: int = Field(..., ge=1)
    hat_present_streak: int = Field(..., ge=0)
    hat_missing_streak: int = Field(..., ge=0)
    hat_present_confirmed: bool
    vest_present_streak: int = Field(..., ge=0)
    vest_missing_streak: int = Field(..., ge=0)
    vest_present_confirmed: bool
    lost_frames: int = Field(..., ge=0)


class RemotePpeSmootherState(_StrictStateModel):
    temporal_frames: int = Field(..., ge=1, le=60)
    tracks: list[RemotePpeSmootherEntry] = Field(default_factory=list, max_length=256)

    @field_validator("tracks")
    @classmethod
    def validate_unique_tracks(cls, value: list[RemotePpeSmootherEntry]) -> list[RemotePpeSmootherEntry]:
        track_ids = [entry.track_id for entry in value]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("smoother track IDs must be unique")
        return value


class RemoteTrackingState(_StrictStateModel):
    schema_version: Literal["bytetrack_ppe_state_v1"] = TRACKING_STATE_SCHEMA_VERSION
    tracker: RemoteByteTrackerState
    smoother: RemotePpeSmootherState

    @model_validator(mode="after")
    def validate_smoother_identity_range(self):
        if any(entry.track_id > self.tracker.last_track_id for entry in self.smoother.tracks):
            raise ValueError("smoother track ID cannot exceed the tracker ID counter")
        return self


class RemoteVisionV2Response(RemoteVisionResponse):
    contract_version: Literal["safety_vision_v2"] = CONTRACT_VERSION_V2
    monitoring_session_id: UUID
    frame_id: int = Field(..., ge=0)
    base_state_revision: int = Field(..., ge=0)
    tracking_state: RemoteTrackingState


class RemoteVisionV2Health(BaseModel):
    status: Literal["healthy"] = "healthy"
    contract_version: Literal["safety_vision_v2"] = CONTRACT_VERSION_V2
    model_version: str = Field(..., min_length=1, max_length=200)
