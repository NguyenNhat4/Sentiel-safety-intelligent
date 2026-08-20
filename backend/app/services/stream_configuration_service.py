from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.stream_configuration import StreamConfiguration
from backend.app.schemas.stream_configuration import StreamConfigurationResponse, StreamConfigurationUpdate


class StreamConfigurationPersistenceError(RuntimeError):
    pass


class StreamConfigurationService:
    CONFIGURATION_ID = 1

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> StreamConfigurationResponse:
        configuration = self.db.get(StreamConfiguration, self.CONFIGURATION_ID)
        if configuration is None:
            return StreamConfigurationResponse(mappings=[], updated_at=None)
        mappings = configuration.mappings or []
        if not mappings and configuration.active_camera_id:
            mappings = [{"camera_id": "cam_1", "stream_camera_id": configuration.active_camera_id}]
        return StreamConfigurationResponse(
            mappings=mappings,
            updated_at=configuration.updated_at,
        )

    def update(self, payload: StreamConfigurationUpdate) -> StreamConfigurationResponse:
        stream_ids = [mapping.stream_camera_id for mapping in payload.mappings]
        if len(stream_ids) != len(set(stream_ids)):
            raise DuplicateStreamAssignmentError("Một stream chỉ được kết nối với một camera.")
        configuration = self.db.get(StreamConfiguration, self.CONFIGURATION_ID)
        if configuration is None:
            configuration = StreamConfiguration(id=self.CONFIGURATION_ID)
            self.db.add(configuration)
        configuration.mappings = [mapping.model_dump() for mapping in payload.mappings]
        configuration.active_camera_id = None
        configuration.updated_at = datetime.now(UTC)
        try:
            self.db.commit()
            self.db.refresh(configuration)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise StreamConfigurationPersistenceError("Could not save active stream configuration") from exc
        return self.get()

    def disconnect(self, camera_id: str) -> StreamConfigurationResponse:
        configuration = self.db.get(StreamConfiguration, self.CONFIGURATION_ID)
        if configuration is None:
            return self.get()
        configuration.mappings = [
            mapping for mapping in (configuration.mappings or []) if mapping.get("camera_id") != camera_id
        ]
        configuration.active_camera_id = None
        configuration.updated_at = datetime.now(UTC)
        try:
            self.db.commit()
            self.db.refresh(configuration)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise StreamConfigurationPersistenceError("Could not disconnect camera stream") from exc
        return self.get()


class DuplicateStreamAssignmentError(ValueError):
    pass
