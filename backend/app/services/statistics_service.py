from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.event import SafetyEvent
from backend.app.schemas.statistics import StatisticsSummaryResponse, ZoneComplianceStats


class StatisticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, zone_id: str | None = None) -> StatisticsSummaryResponse:
        events = self.db.query(SafetyEvent)
        if zone_id:
            events = events.filter(SafetyEvent.zone_id == zone_id)
        total_events = events.count()
        unacknowledged = events.filter(SafetyEvent.status == "unacknowledged").count()

        # Count by event type
        type_counts = (
            events.with_entities(SafetyEvent.event_type, func.count(SafetyEvent.id))
            .group_by(SafetyEvent.event_type)
            .all()
        )
        violations_by_type = {event_type: count for event_type, count in type_counts}

        # Count by severity
        severity_counts = (
            events.with_entities(SafetyEvent.severity, func.count(SafetyEvent.id)).group_by(SafetyEvent.severity).all()
        )
        violations_by_severity = {severity: count for severity, count in severity_counts}

        # Zone stats calculation
        zones = [zone_id] if zone_id else ["zone_01", "zone_02", "zone_03"]
        zone_stats = []
        for z in zones:
            v_count = self.db.query(SafetyEvent).filter(SafetyEvent.zone_id == z).count()
            # Simulated total detections for compliance calculation
            total_det = max(v_count + 50, 100)
            compliance = round(((total_det - v_count) / total_det) * 100, 2)
            zone_stats.append(
                ZoneComplianceStats(
                    zone_id=z,
                    zone_name=f"Zone {z.split('_')[-1]}",
                    compliance_rate=compliance,
                    total_detections=total_det,
                    total_violations=v_count,
                )
            )

        overall_compliance = (
            round(sum(z.compliance_rate for z in zone_stats) / len(zone_stats), 2) if zone_stats else 100.0
        )

        return StatisticsSummaryResponse(
            total_events=total_events,
            unacknowledged_events=unacknowledged,
            overall_compliance_rate=overall_compliance,
            violations_by_type=violations_by_type,
            violations_by_severity=violations_by_severity,
            zone_stats=zone_stats,
        )
