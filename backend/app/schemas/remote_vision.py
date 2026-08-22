from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

CONTRACT_VERSION = "safety_vision_v1"


class RemotePpeObservation(BaseModel):
    status: Literal["present", "unknown"]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class RemotePersonPpeObservations(BaseModel):
    hat: RemotePpeObservation
    vest: RemotePpeObservation


class RemoteCanonicalPerson(BaseModel):
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    track_id: int = Field(..., ge=1)

    @field_validator("bbox")
    @classmethod
    def validate_xywh_bbox(cls, bbox: list[int]) -> list[int]:
        x, y, width, height = bbox
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError("canonical person bbox must be non-negative xywh with positive size")
        return bbox


class RemoteModelDetection(BaseModel):
    class_id: Literal[0, 3, 4]
    class_name: Literal["hat", "person", "vest"]
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    person_index: int | None = Field(default=None, ge=0)

    @field_validator("bbox")
    @classmethod
    def validate_xyxy_bbox(cls, bbox: list[int]) -> list[int]:
        x1, y1, x2, y2 = bbox
        if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
            raise ValueError("detection bbox must be non-negative ordered xyxy")
        return bbox

    @model_validator(mode="after")
    def validate_class_mapping(self):
        expected_name = {0: "hat", 3: "person", 4: "vest"}[self.class_id]
        if self.class_name != expected_name:
            raise ValueError("class_id and class_name do not match")
        return self


class RemoteVisionResponse(BaseModel):
    contract_version: Literal["safety_vision_v1"] = CONTRACT_VERSION
    request_id: UUID
    model_version: str = Field(..., min_length=1, max_length=200)
    canonical_people: list[RemoteCanonicalPerson]
    people: list[RemotePersonPpeObservations]
    detections: list[RemoteModelDetection]

    @model_validator(mode="after")
    def validate_person_references(self):
        if len(self.people) != len(self.canonical_people):
            raise ValueError("people and canonical_people must have equal length")
        for detection in self.detections:
            if detection.person_index is not None and detection.person_index >= len(self.people):
                raise ValueError("detection person_index is out of range")
        return self


class RemoteVisionHealth(BaseModel):
    status: Literal["healthy"] = "healthy"
    contract_version: Literal["safety_vision_v1"] = CONTRACT_VERSION
    model_version: str = Field(..., min_length=1, max_length=200)
