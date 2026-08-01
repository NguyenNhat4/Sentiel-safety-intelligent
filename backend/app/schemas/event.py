from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    zone_id: str
    camera_id: str = "cam_01"
    event_type: str
    severity: str = "high"
    snapshot_path: str | None = None
    privacy_blurred: bool = True
    details: dict[str, Any] | None = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    status: str | None = Field(None, description="unacknowledged, acknowledged, false_alarm")
    acknowledged_by: str | None = None


class EventResponse(EventBase):
    id: int
    timestamp: datetime
    status: str
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
