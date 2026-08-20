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
            return StreamConfigurationResponse(active_camera_id=None, updated_at=None)
        return StreamConfigurationResponse(
            active_camera_id=configuration.active_camera_id,
            updated_at=configuration.updated_at,
        )

    def update(self, payload: StreamConfigurationUpdate) -> StreamConfigurationResponse:
        configuration = self.db.get(StreamConfiguration, self.CONFIGURATION_ID)
        if configuration is None:
            configuration = StreamConfiguration(id=self.CONFIGURATION_ID)
            self.db.add(configuration)
        configuration.active_camera_id = payload.camera_id
        configuration.updated_at = datetime.now(UTC)
        try:
            self.db.commit()
            self.db.refresh(configuration)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise StreamConfigurationPersistenceError("Could not save active stream configuration") from exc
        return self.get()
