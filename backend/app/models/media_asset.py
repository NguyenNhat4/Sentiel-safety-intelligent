import datetime
import enum

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class MediaType(enum.StrEnum):
    VIDEO = "video"
    IMAGE = "image"


class MediaAssetStatus(enum.StrEnum):
    UPLOADING = "UPLOADING"
    READY = "READY"
    ERROR = "ERROR"


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(String(36), primary_key=True)
    display_name = Column(String(120), nullable=False)
    media_type = Column(String(10), nullable=False)
    status = Column(String(16), nullable=False, index=True)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    storage_filename = Column(String(80), nullable=False, unique=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    assigned_configuration = relationship("CameraConfiguration", back_populates="asset", uselist=False)
    sessions = relationship("CameraSession", back_populates="asset")
