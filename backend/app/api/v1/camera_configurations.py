from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_authenticated_user, require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.camera_configuration import CameraConfigurationResponse, CameraConfigurationUpdate
from backend.app.services.camera_configuration_service import (
    CameraConfigurationConflictError,
    CameraConfigurationInvalidError,
    CameraConfigurationNotFoundError,
    CameraConfigurationService,
)
from backend.app.services.monitoring_zone_service import MonitoringZoneGeometryError

router = APIRouter(prefix="/camera-configurations", tags=["Camera Configurations"])


@router.get("", response_model=list[CameraConfigurationResponse])
def list_camera_configurations(
    _: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return CameraConfigurationService(db).list()


@router.get("/{camera_id}", response_model=CameraConfigurationResponse)
def get_camera_configuration(
    camera_id: str,
    _: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    try:
        return CameraConfigurationService(db).get(camera_id)
    except CameraConfigurationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Camera configuration not found") from exc


@router.put("/{camera_id}", response_model=CameraConfigurationResponse)
def save_camera_configuration(
    camera_id: str,
    payload: CameraConfigurationUpdate,
    _: User = Depends(require_roles(UserRole.SAFETY_MANAGER, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        return CameraConfigurationService(db).save(camera_id, payload)
    except CameraConfigurationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Camera configuration not found") from exc
    except CameraConfigurationConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "configuration_conflict"}) from exc
    except CameraConfigurationInvalidError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_configuration"}) from exc
    except MonitoringZoneGeometryError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "zone_geometry_conflict", "zone_ids": exc.zone_ids},
        ) from exc
