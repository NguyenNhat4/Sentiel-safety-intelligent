from pydantic import BaseModel, Field


class ZoneComplianceStats(BaseModel):
    zone_id: str
    zone_name: str
    compliance_rate: float | None
    total_detections: int
    total_violations: int


class CameraEventStats(BaseModel):
    camera_id: str
    camera_name: str
    official_violations: int
    unacknowledged_events: int
    false_alarm_events: int


class StatisticsSummaryResponse(BaseModel):
    total_events: int
    unacknowledged_events: int
    false_alarm_events: int = 0
    camera_stats: list[CameraEventStats] = Field(default_factory=list)
    overall_compliance_rate: float | None
    violations_by_type: dict[str, int]
    violations_by_severity: dict[str, int]
    zone_stats: list[ZoneComplianceStats]
