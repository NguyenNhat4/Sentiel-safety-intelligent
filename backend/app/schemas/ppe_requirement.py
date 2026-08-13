from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class PpeRequirementUpdate(BaseModel):
    profile: Literal["hat_vest_v1"]
    hat_required: StrictBool
    vest_required: StrictBool

    model_config = ConfigDict(extra="forbid")


class PpeRequirementResponse(PpeRequirementUpdate):
    camera_id: str
    zone_id: str
    is_configured: bool = True
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
