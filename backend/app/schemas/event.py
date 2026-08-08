from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
