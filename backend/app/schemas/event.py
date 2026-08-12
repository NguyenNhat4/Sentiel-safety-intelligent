from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.analysis import ModelDetection, PersonDetection


class EventBase(BaseModel):
    zone_id: str
    camera_id: str = "cam_01"
    event_type: str
    severity: str = "high"
    details: dict[str, Any] | None = None
    monitoring_session_id: UUID | None = None


class EventCreate(EventBase):
    status: Literal["unacknowledged", "acknowledged", "false_alarm"] = "unacknowledged"
    acknowledged_by: str | None = None
    occurrence_ids: list[UUID] = Field(default_factory=list)
    snapshot_data: str | None = Field(
        None,
        exclude=True,
        description="Base64 JPEG data URL captured at the violation timestamp",
    )
    snapshot_people: list[PersonDetection] = Field(
        default_factory=list,
        exclude=True,
        description="Detected people used only to annotate the persisted snapshot",
    )
    snapshot_detections: list[ModelDetection] = Field(
        default_factory=list,
        exclude=True,
        description="SH17 detections used only to annotate the persisted snapshot",
    )


class EventUpdate(BaseModel):
    status: str | None = Field(None, description="unacknowledged, acknowledged, false_alarm")
    acknowledged_by: str | None = None


class EventResponse(EventBase):
    id: int
    timestamp: datetime
    status: str
    snapshot_path: str | None = None
    privacy_blurred: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    occurrence_ids: list[UUID] = Field(default_factory=list)
    batch_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class EventBatchItem(BaseModel):
    zone_id: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    event_type: Literal["zone_intrusion"] = "zone_intrusion"
    severity: str = "critical"
    occurrence_ids: list[UUID] = Field(min_length=1)
    details: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class EventBatchCreate(BaseModel):
    monitoring_session_id: UUID
    camera_id: str = Field(default="uploaded_video", min_length=1, max_length=50)
    status: Literal["acknowledged", "false_alarm"]
    acknowledged_by: str | None = None
    snapshot_data: str | None = Field(default=None, exclude=True)
    snapshot_people: list[PersonDetection] = Field(default_factory=list, exclude=True)
    snapshot_detections: list[ModelDetection] = Field(default_factory=list, exclude=True)
    events: list[EventBatchItem] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_zones_and_occurrences(self):
        zone_ids = [item.zone_id.casefold() for item in self.events]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("A batch cannot repeat zone_id")
        occurrence_ids = [occurrence for item in self.events for occurrence in item.occurrence_ids]
        if len(occurrence_ids) != len(set(occurrence_ids)):
            raise ValueError("A batch cannot repeat occurrence_id")
        return self


class EventBatchResponse(BaseModel):
    batch_id: UUID
    snapshot_path: str | None = None
    events: list[EventResponse]
