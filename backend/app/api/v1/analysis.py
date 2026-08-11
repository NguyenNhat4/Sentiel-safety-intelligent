from fastapi import APIRouter, HTTPException

from backend.app.schemas.analysis import (
    AnalysisStatusResponse,
    FrameInferenceRequest,
    FrameInferenceResponse,
    StartAnalysisRequest,
)
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.frame_inference_service import InvalidFrameError, StaleFrameError, frame_inference_service

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
async def infer_frame(request: FrameInferenceRequest):
    """Evaluate one browser video frame against the predefined safety rule."""
    try:
        return frame_inference_service.infer(request)
    except InvalidFrameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StaleFrameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
