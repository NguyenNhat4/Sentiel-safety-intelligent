import datetime
import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

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
    __table_args__ = (UniqueConstraint("monitoring_session_id", "track_id", name="uq_safety_events_session_track"),)

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
    monitoring_session_id = Column(String(36), nullable=True, index=True)
    track_id = Column(Integer, nullable=True, index=True)
    occurrences = relationship(
        "EventOccurrence",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def occurrence_ids(self) -> list[str]:
        return [occurrence.occurrence_id for occurrence in self.occurrences]

    @property
    def batch_id(self) -> str | None:
        return getattr(self, "_transient_batch_id", None)

    @batch_id.setter
    def batch_id(self, value: str | None) -> None:
        self._transient_batch_id = value


class EventOccurrence(Base):
    __tablename__ = "event_occurrences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    occurrence_id = Column(String(36), nullable=False, unique=True, index=True)
    event_id = Column(Integer, ForeignKey("safety_events.id", ondelete="CASCADE"), nullable=False, index=True)
    event = relationship("SafetyEvent", back_populates="occurrences")
