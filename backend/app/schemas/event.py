from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.schemas.analysis import ModelDetection, PersonDetection
from backend.app.schemas.monitoring_zone import ZonePoint
from backend.app.schemas.ppe_requirement import PpeRequirementUpdate


class EventRuleContextInput(BaseModel):
    triggered_rule_keys: list[str] = Field(min_length=1, max_length=20)
    ppe_profile: Literal["hat_vest_v1"]
    ppe_requirements: PpeRequirementUpdate

    model_config = ConfigDict(extra="forbid")

    @field_validator("triggered_rule_keys")
    @classmethod
    def validate_rule_keys(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 120 for value in normalized):
            raise ValueError("triggered_rule_keys must contain non-empty values of at most 120 characters")
        if len(normalized) != len(set(normalized)):
            raise ValueError("triggered_rule_keys must be unique")
        return normalized


class StoredEventRuleContext(EventRuleContextInput):
    rule_version: Literal["safety_rule_v1"] = "safety_rule_v1"
    violation_frame_count: int = Field(ge=1, le=60)


class EventSceneContextInput(BaseModel):
    frame_id: int = Field(ge=0)
    video_timestamp_seconds: float = Field(ge=0)
    machine_state: Literal["running", "stopped"]
    zone_name: str = Field(min_length=1, max_length=100)
    zone_revision: int | None = Field(default=None, ge=0)
    zone_points: list[ZonePoint] = Field(default_factory=list, max_length=4)
    people: list[PersonDetection] = Field(default_factory=list, max_length=100)
    detections: list[ModelDetection] = Field(default_factory=list, max_length=300)

    model_config = ConfigDict(extra="forbid")

    @field_validator("zone_points")
    @classmethod
    def validate_zone_points(cls, value: list[ZonePoint]) -> list[ZonePoint]:
        if len(value) not in (0, 4):
            raise ValueError("zone_points must contain zero or four points")
        return value


class StoredEventSceneContext(EventSceneContextInput):
    camera_id: str
    zone_id: str


class EventSystemDecisionInput(BaseModel):
    result: Literal["violate"]
    reason_codes: list[str] = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 120 for value in normalized):
            raise ValueError("reason_codes must contain non-empty values of at most 120 characters")
        if len(normalized) != len(set(normalized)):
            raise ValueError("reason_codes must be unique")
        return normalized


class StoredEventSystemDecision(EventSystemDecisionInput):
    severity: Literal["low", "medium", "high", "critical"]


class EventHumanReviewContext(BaseModel):
    outcome: Literal["actual_violation", "false_alarm"]
    actor_user_id: str | None = None
    actor_name: str
    actor_role: str | None = None
    reviewed_at: datetime


class DecisionContextInput(BaseModel):
    rule: EventRuleContextInput
    scene: EventSceneContextInput
    system_decision: EventSystemDecisionInput

    model_config = ConfigDict(extra="forbid")


class StoredDecisionContext(BaseModel):
    schema_version: Literal["decision_context_v1"] = "decision_context_v1"
    rule: StoredEventRuleContext
    scene: StoredEventSceneContext
    system_decision: StoredEventSystemDecision
    human_review: EventHumanReviewContext


class EventIncidentSummary(BaseModel):
    text: str
    source: Literal["llm", "deterministic"]
    context_schema_version: Literal["decision_context_v1"] | None = None


class EventBase(BaseModel):
    zone_id: str
    camera_id: str = "cam_01"
    event_type: str
    severity: str = "high"
    details: dict[str, Any] | None = None
    decision_context: StoredDecisionContext | None = None
    monitoring_session_id: UUID | None = None
    track_id: int | None = Field(default=None, ge=0)


class EventCreate(EventBase):
    status: Literal["unacknowledged", "acknowledged", "false_alarm"] = "unacknowledged"
    acknowledged_by: str | None = None
    occurrence_ids: list[UUID] = Field(default_factory=list)
    decision_context: DecisionContextInput | None = None
    snapshot_data: str | None = Field(
        None,
        exclude=True,
        description="Base64 JPEG data URL captured at the violation timestamp",
    )
    snapshot_people: list[PersonDetection] = Field(
        default_factory=list,
        exclude=True,
        description="Detected people used only to annotate the persisted snapshot",
    )
    snapshot_detections: list[ModelDetection] = Field(
        default_factory=list,
        exclude=True,
        description="Hat/person/vest detections used only to annotate the persisted snapshot",
    )


class EventUpdate(BaseModel):
    status: Literal["unacknowledged", "acknowledged", "false_alarm", "resolved"] | None = Field(
        None, description="unacknowledged, acknowledged, false_alarm, resolved"
    )
    acknowledged_by: str | None = None

    model_config = ConfigDict(extra="forbid")


class EventResponse(EventBase):
    id: int
    timestamp: datetime
    status: str
    snapshot_path: str | None = None
    privacy_blurred: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    audit_retention_until: datetime | None = None
    snapshot_retention_until: datetime | None = None
    occurrence_ids: list[UUID] = Field(default_factory=list)
    batch_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(EventResponse):
    summary: EventIncidentSummary


class EventBatchItem(BaseModel):
    zone_id: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    event_type: Literal["zone_intrusion"] = "zone_intrusion"
    severity: str = "critical"
    occurrence_ids: list[UUID] = Field(min_length=1)
    details: dict[str, Any] | None = None
    decision_context: DecisionContextInput | None = None

    model_config = ConfigDict(extra="forbid")


class EventBatchCreate(BaseModel):
    monitoring_session_id: UUID
    camera_id: str = Field(default="uploaded_video", min_length=1, max_length=50)
    status: Literal["acknowledged", "false_alarm"]
    acknowledged_by: str | None = None
    snapshot_data: str | None = Field(default=None, exclude=True)
    snapshot_people: list[PersonDetection] = Field(default_factory=list, exclude=True)
    snapshot_detections: list[ModelDetection] = Field(default_factory=list, exclude=True)
    events: list[EventBatchItem] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_zones_and_occurrences(self):
        zone_ids = [item.zone_id.casefold() for item in self.events]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("A batch cannot repeat zone_id")
        occurrence_ids = [occurrence for item in self.events for occurrence in item.occurrence_ids]
        if len(occurrence_ids) != len(set(occurrence_ids)):
            raise ValueError("A batch cannot repeat occurrence_id")
        return self


class EventBatchResponse(BaseModel):
    batch_id: UUID
    snapshot_path: str | None = None
    events: list[EventResponse]
