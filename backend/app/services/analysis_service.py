import uuid
from typing import Any

from backend.app.schemas.analysis import AnalysisStatusResponse, StartAnalysisRequest


class AnalysisService:
    def __init__(self):
        # In-memory session tracking for active analysis sessions
        self._active_sessions: dict[str, dict[str, Any]] = {}

    def start_analysis(self, request: StartAnalysisRequest) -> AnalysisStatusResponse:
        session_id = str(uuid.uuid4())
        session_info = {
            "session_id": session_id,
            "status": "running",
            "source_type": request.source_type,
            "source_path": request.source_path,
            "zone_ids": request.zone_ids,
            "fps": 25.0,
            "processed_frames": 0,
            "active_violations_count": 0,
        }
        self._active_sessions[session_id] = session_info
        return AnalysisStatusResponse(**session_info)

    def stop_analysis(self, session_id: str) -> AnalysisStatusResponse | None:
        if session_id in self._active_sessions:
            self._active_sessions[session_id]["status"] = "stopped"
            return AnalysisStatusResponse(**self._active_sessions[session_id])
        return None

    def get_status(self, session_id: str) -> AnalysisStatusResponse | None:
        if session_id in self._active_sessions:
            return AnalysisStatusResponse(**self._active_sessions[session_id])
        return None
