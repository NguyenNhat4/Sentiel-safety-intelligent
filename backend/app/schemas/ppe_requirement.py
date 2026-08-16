from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, StrictBool, model_validator


class PpeRequirementUpdate(BaseModel):
    LEGACY_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"helmet_required", "safety_glasses_required", "gloves_required"}
    )

    profile: Literal["hat_vest_v1"]
    hat_required: StrictBool
    vest_required: StrictBool
    restricted_area_detection_enabled: StrictBool = False

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def map_complete_legacy_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict) or set(value) != cls.LEGACY_FIELDS:
            return value
        return {
            "profile": "hat_vest_v1",
            "hat_required": value["helmet_required"],
            "vest_required": True,
        }


class PpeRequirementResponse(PpeRequirementUpdate):
    camera_id: str
    zone_id: str
    is_configured: bool = True
    updated_at: datetime | None
    helmet_required: bool = False
    safety_glasses_required: bool = False
    gloves_required: bool = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_legacy_read_aliases(self):
        """Keep GET response aliases additive without requiring callers to supply them."""
        if "helmet_required" not in self.model_fields_set:
            self.helmet_required = self.hat_required
        return self
