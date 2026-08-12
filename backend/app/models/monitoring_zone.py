import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


def utc_now():
    return datetime.datetime.now(datetime.UTC)


class MonitoringZoneCollection(Base):
    __tablename__ = "monitoring_zone_collections"

    camera_id = Column(String(50), primary_key=True)
    revision = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    zones = relationship(
        "MonitoringZoneRecord",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MonitoringZoneRecord(Base):
    __tablename__ = "monitoring_zones"
    __table_args__ = (
        UniqueConstraint("camera_id", "normalized_zone_id", name="uq_monitoring_zones_camera_normalized_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(
        String(50),
        ForeignKey("monitoring_zone_collections.camera_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_id = Column(String(50), nullable=False)
    normalized_zone_id = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    points = Column(JSON, nullable=False)
    machine_state = Column(String(20), nullable=False, default="stopped")
    enabled = Column(Boolean, nullable=False, default=True)
    order = Column(Integer, nullable=False)
    collection = relationship("MonitoringZoneCollection", back_populates="zones")
