import datetime

from sqlalchemy import JSON, BigInteger, CheckConstraint, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB

from backend.app.core.database import Base


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class VisionTrackingState(Base):
    __tablename__ = "vision_tracking_states"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="ck_vision_tracking_states_revision"),
        CheckConstraint("last_frame_id >= 0", name="ck_vision_tracking_states_last_frame_id"),
        Index("ix_vision_tracking_states_expires_at", "expires_at"),
    )

    monitoring_session_id = Column(String(36), primary_key=True)
    contract_version = Column(String(32), nullable=False)
    state_schema_version = Column(String(40), nullable=False)
    revision = Column(BigInteger, nullable=False, default=0)
    last_frame_id = Column(BigInteger, nullable=False)
    state_payload = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __mapper_args__ = {
        "version_id_col": revision,
        "version_id_generator": False,
    }
