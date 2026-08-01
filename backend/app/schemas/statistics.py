from pydantic import BaseModel


class ZoneComplianceStats(BaseModel):
    zone_id: str
    zone_name: str
    compliance_rate: float
    total_detections: int
    total_violations: int


class StatisticsSummaryResponse(BaseModel):
    total_events: int
    unacknowledged_events: int
    overall_compliance_rate: float
    violations_by_type: dict[str, int]
    violations_by_severity: dict[str, int]
    zone_stats: list[ZoneComplianceStats]
