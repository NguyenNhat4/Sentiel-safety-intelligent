import asyncio
import base64
import logging
import threading
from uuid import NAMESPACE_URL, uuid5

import cv2
import numpy as np

from backend.app.core.database import SessionLocal
from backend.app.integrations.rtsp_frame_source import RtspFrameSource, build_rtsp_camera_url
from backend.app.schemas.analysis import FrameInferenceRequest
from backend.app.services.camera_detection_hub import camera_detection_hub
from backend.app.services.camera_inference_supervisor import CameraInferenceSupervisor
from backend.app.services.camera_inference_worker import CameraInferenceWorker
from backend.app.services.frame_inference_service import frame_inference_service
from backend.app.services.monitoring_zone_service import MonitoringZoneService
from backend.app.services.ppe_requirement_service import PpeRequirementService
from backend.app.services.stream_configuration_service import StreamConfigurationService

logger = logging.getLogger(__name__)


class ServerCameraInferenceRuntime:
    """Reconcile mappings and run one RTSP inference worker per connected camera."""

    def __init__(self, rtsp_origin: str, *, max_fps: float = 2.0, poll_seconds: float = 5.0) -> None:
        self._rtsp_origin = rtsp_origin
        self._max_fps = max_fps
        self._poll_seconds = poll_seconds
        self._model_lock = threading.Lock()
        self._supervisor = CameraInferenceSupervisor(self._create_worker)
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        self._stopped.clear()
        try:
            while not self._stopped.is_set():
                try:
                    await asyncio.to_thread(self.reconcile_once)
                except Exception:
                    logger.exception("Could not reconcile server-side camera inference mappings")
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=self._poll_seconds)
                except TimeoutError:
                    pass
        finally:
            self._supervisor.stop_all()

    def stop(self) -> None:
        self._stopped.set()

    def reconcile_once(self) -> None:
        with SessionLocal() as db:
            mappings = StreamConfigurationService(db).get().mappings
        self._supervisor.reconcile(mappings)

    def _create_worker(self, camera_id: str, stream_camera_id: str) -> CameraInferenceWorker:
        source = RtspFrameSource(
            build_rtsp_camera_url(self._rtsp_origin, stream_camera_id),
            max_fps=self._max_fps,
        )
        return CameraInferenceWorker(
            camera_id,
            stream_camera_id,
            source=source,
            process_frame=self._process_frame,
            publish=camera_detection_hub.publish,
        )

    def _process_frame(
        self,
        camera_id: str,
        stream_camera_id: str,
        frame_id: int,
        captured_at: float,
        frame: np.ndarray,
    ) -> dict:
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            raise ValueError("RTSP frame could not be encoded as JPEG")
        image_data = f"data:image/jpeg;base64,{base64.b64encode(encoded).decode()}"
        session_id = uuid5(NAMESPACE_URL, f"p047:rtsp:{camera_id}:{stream_camera_id}")
        with SessionLocal() as db:
            zones = MonitoringZoneService(db).get(camera_id)
            requirement_service = PpeRequirementService(db)
            requirements_by_zone = {
                zone.zone_id: requirement_service.get(camera_id, zone.zone_id) for zone in zones.zones
            }
            requirements = requirement_service.get(camera_id, "zone_01")
        request = FrameInferenceRequest(
            image_data=image_data,
            camera_id=camera_id,
            zones=zones.zones,
            zone_revision=zones.revision,
            monitoring_session_id=session_id,
            frame_id=frame_id,
        )
        with self._model_lock:
            result = frame_inference_service.infer(
                request,
                requirements=requirements,
                requirements_by_zone=requirements_by_zone,
            )
        payload = result.model_dump(mode="json")
        payload.pop("snapshot_data", None)
        return {
            "type": "camera_inference_result",
            "monitoring_session_id": str(session_id),
            "captured_at": captured_at,
            **payload,
        }
