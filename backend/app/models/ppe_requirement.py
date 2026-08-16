import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class PpeRequirement(Base):
    __tablename__ = "ppe_requirements"
    __table_args__ = (UniqueConstraint("camera_id", "zone_id", name="uq_ppe_requirements_camera_zone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    zone_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    hat_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vest_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    restricted_area_detection_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
