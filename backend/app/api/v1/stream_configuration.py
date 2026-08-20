from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_authenticated_user, require_system_admin
from backend.app.core.database import get_db
from backend.app.schemas.stream_configuration import StreamConfigurationResponse, StreamConfigurationUpdate
from backend.app.services.stream_configuration_service import (
    StreamConfigurationPersistenceError,
    StreamConfigurationService,
)

router = APIRouter(prefix="/stream-config", tags=["Stream configuration"])


@router.get("", response_model=StreamConfigurationResponse)
def get_stream_configuration(_: object = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return StreamConfigurationService(db).get()


@router.put("", response_model=StreamConfigurationResponse)
def update_stream_configuration(
    payload: StreamConfigurationUpdate,
    _: object = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    try:
        return StreamConfigurationService(db).update(payload)
    except StreamConfigurationPersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
