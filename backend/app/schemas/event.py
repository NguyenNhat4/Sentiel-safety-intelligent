from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.analysis import ModelDetection, PersonDetection


class EventBase(BaseModel):
    zone_id: str
    camera_id: str = "cam_01"
    event_type: str
    severity: str = "high"
    details: dict[str, Any] | None = None


class EventCreate(EventBase):
    status: Literal["unacknowledged", "acknowledged", "false_alarm"] = "unacknowledged"
    acknowledged_by: str | None = None
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

    model_config = ConfigDict(from_attributes=True)
