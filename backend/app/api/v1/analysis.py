from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.analysis import (
    AnalysisStatusResponse,
    FrameInferenceRequest,
    FrameInferenceResponse,
    StartAnalysisRequest,
)
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.frame_inference_service import InvalidFrameError, StaleFrameError, frame_inference_service
from backend.app.services.monitoring_zone_service import MonitoringZoneGeometryError, MonitoringZoneService
from backend.app.services.ppe_requirement_service import PpeRequirementService

router = APIRouter(prefix="/analysis", tags=["Analysis"])
analysis_service = AnalysisService()


@router.post("/start", response_model=AnalysisStatusResponse)
async def start_analysis(request: StartAnalysisRequest):
    """Start video analysis stream/file processing."""
    return analysis_service.start_analysis(request)


@router.post("/stop/{session_id}", response_model=AnalysisStatusResponse)
async def stop_analysis(session_id: str):
    """Stop active video analysis session."""
    status = analysis_service.stop_analysis(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Analysis session not found")
    return status


@router.get("/status/{session_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(session_id: str):
    """Get status of an analysis session."""
    status = analysis_service.get_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Analysis session not found")
    return status


@router.post("/frame", response_model=FrameInferenceResponse)
async def infer_frame(request: FrameInferenceRequest, db: Session = Depends(get_db)):
    """Evaluate one browser video frame against the predefined safety rule."""
    try:
        if request.zones is not None:
            persisted = MonitoringZoneService(db).get(request.camera_id)
            requested_zones = [
                zone.model_dump(mode="json") for zone in sorted(request.zones, key=lambda item: item.order)
            ]
            saved_zones = [zone.model_dump(mode="json") for zone in persisted.zones]
            if request.zone_revision != persisted.revision or requested_zones != saved_zones:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "zone_revision_conflict"},
                )
        requirements = PpeRequirementService(db).get(request.camera_id, request.zone_id)
        return frame_inference_service.infer(request, requirements=requirements)
    except InvalidFrameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StaleFrameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MonitoringZoneGeometryError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "zone_geometry_conflict", "zone_ids": exc.zone_ids},
        ) from exc
