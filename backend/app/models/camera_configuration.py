import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class CameraConfiguration(Base):
    __tablename__ = "camera_configurations"
    __table_args__ = (
        CheckConstraint("camera_id IN ('cam_1','cam_2','cam_3','cam_4')", name="ck_camera_configurations_id"),
    )

    camera_id = Column(String(16), primary_key=True)
    asset_id = Column(String(36), ForeignKey("media_assets.id", ondelete="RESTRICT"), unique=True, nullable=True)
    machine_state = Column(String(20), nullable=False, default="stopped")
    revision = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    asset = relationship("MediaAsset", back_populates="assigned_configuration")


class CameraSession(Base):
    __tablename__ = "camera_sessions"
    __table_args__ = (
        CheckConstraint("camera_id IN ('cam_1','cam_2','cam_3','cam_4')", name="ck_camera_sessions_id"),
        Index(
            "uq_camera_sessions_active_camera",
            "camera_id",
            unique=True,
            postgresql_where=text("status IN ('STARTING','RUNNING')"),
            sqlite_where=text("status IN ('STARTING','RUNNING')"),
        ),
    )

    id = Column(String(36), primary_key=True)
    camera_id = Column(String(16), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey("media_assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    media_type = Column(String(10), nullable=False)
    status = Column(String(16), nullable=False, index=True)
    config_revision = Column(Integer, nullable=False)
    inference_fps = Column(Float, nullable=False, default=0.0)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    running_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(64), nullable=True)
    asset = relationship("MediaAsset", back_populates="sessions")
