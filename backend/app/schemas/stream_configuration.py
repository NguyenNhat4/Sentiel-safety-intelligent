from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StreamMapping(BaseModel):
    camera_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    stream_camera_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    model_config = ConfigDict(extra="forbid")


class StreamConfigurationUpdate(BaseModel):
    mappings: list[StreamMapping] = Field(default_factory=list, max_length=4)

    model_config = ConfigDict(extra="forbid")


class StreamConfigurationResponse(BaseModel):
    mappings: list[StreamMapping]
    updated_at: datetime | None
