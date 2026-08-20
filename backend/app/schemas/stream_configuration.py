from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StreamConfigurationUpdate(BaseModel):
    camera_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    model_config = ConfigDict(extra="forbid")


class StreamConfigurationResponse(BaseModel):
    active_camera_id: str | None
    updated_at: datetime | None
