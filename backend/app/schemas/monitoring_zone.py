from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


class ZonePoint(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class MonitoringZone(BaseModel):
    zone_id: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    display_name: str = Field(min_length=1, max_length=100)
    points: list[ZonePoint] = Field(min_length=4, max_length=4)
    machine_state: Literal["running", "stopped"] = "stopped"
    enabled: StrictBool = True
    order: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be blank")
        return value


class MonitoringZoneCollectionUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    zones: list[MonitoringZone] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_identity_and_order(self):
        ids = [zone.zone_id.casefold() for zone in self.zones]
        if len(ids) != len(set(ids)):
            raise ValueError("zone_id must be unique case-insensitively")
        orders = [zone.order for zone in self.zones]
        if len(orders) != len(set(orders)):
            raise ValueError("zone order must be unique")
        return self


class MonitoringZoneCollectionResponse(BaseModel):
    camera_id: str
    revision: int
    zones: list[MonitoringZone]
    updated_at: datetime | None
