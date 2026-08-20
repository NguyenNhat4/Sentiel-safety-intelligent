import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from backend.app.core.database import Base


def utc_now():
    return datetime.datetime.now(datetime.UTC)


class StreamConfiguration(Base):
    __tablename__ = "stream_configuration"

    id = Column(Integer, primary_key=True, default=1)
    active_camera_id = Column(String(64), nullable=True)
    mappings = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
