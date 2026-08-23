from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from backend.app.schemas.monitoring_zone import MonitoringZone, ZonePoint
from backend.app.schemas.ppe_requirement import PpeRequirementUpdate


class CameraConfigurationZone(BaseModel):
    zone_id: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    display_name: str = Field(min_length=1, max_length=100)
    points: list[ZonePoint] = Field(min_length=4, max_length=4)
    enabled: StrictBool = True
    order: int = Field(ge=0)
    ppe_requirements: PpeRequirementUpdate

    model_config = ConfigDict(extra="forbid")

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be blank")
        return value


class CameraConfigurationUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    asset_id: UUID
    machine_state: Literal["running", "stopped"]
    zones: list[CameraConfigurationZone] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_zone_identity(self):
        ids = [zone.zone_id.casefold() for zone in self.zones]
        orders = [zone.order for zone in self.zones]
        if len(ids) != len(set(ids)):
            raise ValueError("zone_id must be unique case-insensitively")
        if len(orders) != len(set(orders)):
            raise ValueError("zone order must be unique")
        return self

    def monitoring_zones(self) -> list[MonitoringZone]:
        return [
            MonitoringZone(
                zone_id=zone.zone_id,
                display_name=zone.display_name,
                points=zone.points,
                machine_state=self.machine_state,
                enabled=zone.enabled,
                order=zone.order,
            )
            for zone in self.zones
        ]


class CameraConfigurationResponse(BaseModel):
    camera_id: str
    revision: int
    asset_id: UUID | None
    machine_state: Literal["running", "stopped"]
    zones: list[CameraConfigurationZone]
    updated_at: datetime | None
