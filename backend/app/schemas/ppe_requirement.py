from datetime import datetime

from pydantic import BaseModel, ConfigDict, StrictBool


class PpeRequirementUpdate(BaseModel):
    helmet_required: StrictBool
    safety_glasses_required: StrictBool
    gloves_required: StrictBool

    model_config = ConfigDict(extra="forbid")


class PpeRequirementResponse(PpeRequirementUpdate):
    camera_id: str
    zone_id: str
    is_configured: bool = True
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
