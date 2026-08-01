from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class EventBase(BaseModel):
    zone_id: str
    camera_id: str = "cam_01"
    event_type: str
    severity: str = "high"
    snapshot_path: Optional[str] = None
    privacy_blurred: bool = True
    details: Optional[Dict[str, Any]] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    status: Optional[str] = Field(None, description="unacknowledged, acknowledged, false_alarm")
    acknowledged_by: Optional[str] = None


class EventResponse(EventBase):
    id: int
    timestamp: datetime
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
