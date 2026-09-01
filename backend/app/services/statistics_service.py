from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.camera_configuration import CameraConfiguration
from backend.app.models.event import SafetyEvent
from backend.app.models.media_asset import MediaAsset
from backend.app.schemas.statistics import CameraEventStats, StatisticsSummaryResponse, ZoneComplianceStats

CAMERA_IDS = ("cam_1", "cam_2", "cam_3", "cam_4")


class StatisticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(
        self,
        zone_id: str | None = None,
        camera_ids: list[str] | None = None,
    ) -> StatisticsSummaryResponse:
        events = self.db.query(SafetyEvent)
        if camera_ids:
            events = events.filter(SafetyEvent.camera_id.in_(camera_ids))
        if zone_id:
            events = events.filter(SafetyEvent.zone_id == zone_id)
        official_violations = events.filter(SafetyEvent.status.in_(("acknowledged", "resolved")))
        total_events = official_violations.count()
        unacknowledged = events.filter(SafetyEvent.status == "unacknowledged").count()
        false_alarms = events.filter(SafetyEvent.status == "false_alarm").count()

        # Count by event type
        type_counts = (
            official_violations.with_entities(SafetyEvent.event_type, func.count(SafetyEvent.id))
            .group_by(SafetyEvent.event_type)
            .all()
        )
        violations_by_type = {event_type: count for event_type, count in type_counts}

        # Count by severity
        severity_counts = (
            official_violations.with_entities(SafetyEvent.severity, func.count(SafetyEvent.id))
            .group_by(SafetyEvent.severity)
            .all()
        )
        violations_by_severity = {severity: count for severity, count in severity_counts}

        if camera_ids is not None:
            dashboard_camera_ids = camera_ids
        elif zone_id:
            dashboard_camera_ids = [row[0] for row in events.with_entities(SafetyEvent.camera_id).distinct().all()]
        else:
            dashboard_camera_ids = list(CAMERA_IDS)

        zone_stats = []
        camera_names = dict(
            self.db.query(CameraConfiguration.camera_id, MediaAsset.display_name)
            .join(MediaAsset, CameraConfiguration.asset_id == MediaAsset.id)
            .filter(CameraConfiguration.camera_id.in_(dashboard_camera_ids))
            .all()
        )
        camera_stats = []
        for camera_id in dashboard_camera_ids:
            camera_events = events.filter(SafetyEvent.camera_id == camera_id)
            official_count = camera_events.filter(SafetyEvent.status.in_(("acknowledged", "resolved"))).count()
            pending_count = camera_events.filter(SafetyEvent.status == "unacknowledged").count()
            false_alarm_count = camera_events.filter(SafetyEvent.status == "false_alarm").count()
            camera_name = camera_names.get(camera_id, f"Camera {camera_id.rsplit('_', 1)[-1]}")
            camera_stats.append(
                CameraEventStats(
                    camera_id=camera_id,
                    camera_name=camera_name,
                    official_violations=official_count,
                    unacknowledged_events=pending_count,
                    false_alarm_events=false_alarm_count,
                )
            )
            # Deprecated compatibility row: counts are real event records and no compliance rate is claimed.
            zone_stats.append(
                ZoneComplianceStats(
                    zone_id=camera_id,
                    zone_name=camera_name,
                    compliance_rate=None,
                    total_detections=official_count + pending_count + false_alarm_count,
                    total_violations=official_count,
                )
            )

        return StatisticsSummaryResponse(
            total_events=total_events,
            unacknowledged_events=unacknowledged,
            false_alarm_events=false_alarms,
            camera_stats=camera_stats,
            overall_compliance_rate=None,
            violations_by_type=violations_by_type,
            violations_by_severity=violations_by_severity,
            zone_stats=zone_stats,
        )
