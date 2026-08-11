import datetime
import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String

from backend.app.core.database import Base


class EventType(enum.StrEnum):
    MISSING_PPE = "missing_ppe"
    ZONE_INTRUSION = "zone_intrusion"
    MISSING_PPE_AND_INTRUSION = "missing_ppe_and_intrusion"


class SeverityLevel(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def utc_now():
    return datetime.datetime.now(datetime.UTC)


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    zone_id = Column(String(50), nullable=False, index=True)
    camera_id = Column(String(50), nullable=False, default="cam_01")
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="high")
    timestamp = Column(DateTime(timezone=True), default=utc_now, index=True)
    snapshot_path = Column(String(255), nullable=True)
    privacy_blurred = Column(Boolean, default=False)
    status = Column(String(20), default="unacknowledged", index=True)  # unacknowledged, acknowledged, false_alarm
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    details = Column(JSON, nullable=True)  # JSON for detected items, track_id, bounding boxes
