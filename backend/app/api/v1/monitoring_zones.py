from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.monitoring_zone import MonitoringZoneCollectionResponse, MonitoringZoneCollectionUpdate
from backend.app.services.monitoring_zone_service import (
    MonitoringZoneConflictError,
    MonitoringZoneGeometryError,
    MonitoringZonePersistenceError,
    MonitoringZoneService,
)

router = APIRouter(prefix="/cameras", tags=["Monitoring Zones"])
CameraId = Annotated[str, Path(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")]


@router.get("/{camera_id}/monitoring-zones", response_model=MonitoringZoneCollectionResponse)
async def get_monitoring_zones(camera_id: CameraId, db: Session = Depends(get_db)):
    return MonitoringZoneService(db).get(camera_id)


@router.put("/{camera_id}/monitoring-zones", response_model=MonitoringZoneCollectionResponse)
async def save_monitoring_zones(
    update: MonitoringZoneCollectionUpdate,
    camera_id: CameraId,
    db: Session = Depends(get_db),
):
    try:
        return MonitoringZoneService(db).save(camera_id, update)
    except MonitoringZoneConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "revision_conflict"}) from exc
    except MonitoringZoneGeometryError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "zone_geometry_conflict", "zone_ids": exc.zone_ids},
        ) from exc
    except MonitoringZonePersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
