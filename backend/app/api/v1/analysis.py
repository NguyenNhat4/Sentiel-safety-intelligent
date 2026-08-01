from fastapi import APIRouter, HTTPException

from backend.app.schemas.analysis import AnalysisStatusResponse, StartAnalysisRequest
from backend.app.services.analysis_service import AnalysisService

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
