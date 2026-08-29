from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_authenticated_user, require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.camera_session import CameraSessionResponse, SimulationRunResponse
from backend.app.services.camera_configuration_service import CAMERA_IDS, CameraConfigurationNotFoundError
from backend.app.services.camera_session_runtime import CameraSessionStartError, camera_session_runtime
from backend.app.services.media_asset_service import MediaAssetNotFoundError

router = APIRouter(tags=["Camera Sessions"])


@router.post("/simulation-runs", response_model=SimulationRunResponse)
def start_simulation_run(
    _: User = Depends(require_roles(UserRole.SAFETY_MANAGER, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    sessions = []
    errors = {}
    for camera_id in CAMERA_IDS:
        try:
            session = camera_session_runtime.start(db, camera_id)
        except CameraSessionStartError as exc:
            if str(exc) != "camera_not_configured":
                errors[camera_id] = str(exc)
        except (MediaAssetNotFoundError, OSError):
            db.rollback()
            errors[camera_id] = "media_asset_unavailable"
        else:
            sessions.append(session)
    return SimulationRunResponse(sessions=sessions, errors=errors)


@router.post("/camera-sessions/{camera_id}/replay", response_model=CameraSessionResponse)
def replay_camera_session(
    camera_id: str,
    _: User = Depends(require_roles(UserRole.SAFETY_MANAGER, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        return camera_session_runtime.start(db, camera_id)
    except CameraConfigurationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Camera configuration not found") from exc
    except CameraSessionStartError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
    except MediaAssetNotFoundError as exc:
        raise HTTPException(status_code=409, detail={"code": "media_asset_unavailable"}) from exc


@router.get("/camera-sessions", response_model=list[CameraSessionResponse])
def list_camera_sessions(
    _: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return camera_session_runtime.list(db)
