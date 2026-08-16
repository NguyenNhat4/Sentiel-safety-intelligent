import asyncio
import base64
import json
import logging
import time

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.operational_metrics import record_operational_event
from backend.app.schemas.analysis import (
    FrameInferenceRequest,
    InferenceWebSocketConfigure,
    InferenceWebSocketFrameMeta,
)
from backend.app.services.frame_inference_service import (
    InvalidFrameError,
    StaleFrameError,
    frame_inference_service,
)
from backend.app.services.monitoring_zone_service import (
    MonitoringZoneGeometryError,
    MonitoringZoneService,
    validate_zone_geometry,
)
from backend.app.services.ppe_requirement_service import PpeRequirementService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Realtime WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")


manager = ConnectionManager()
active_inference_sessions: set[str] = set()


@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time safety violation alerts."""
    await manager.connect(websocket)
    record_operational_event("websocket_connection_opened", route="/api/v1/ws/alerts", outcome="connected")
    try:
        while True:
            # Keep connection open & handle incoming client messages if any
            data = await websocket.receive_text()
            # Echo ping / pong or client ack
            await websocket.send_text(json.dumps({"type": "pong", "received": data}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        record_operational_event("websocket_connection_closed", route="/api/v1/ws/alerts", outcome="disconnected")


async def send_inference_error(websocket: WebSocket, code: str, message: str) -> None:
    record_operational_event("inference_failed", outcome="error", error_kind=code)
    await websocket.send_json({"type": "error", "code": code, "message": message})


@router.websocket("/ws/inference")
async def websocket_inference_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """Run sampled browser-frame inference over a persistent WebSocket."""
    await websocket.accept()
    record_operational_event("websocket_connection_opened", route="/api/v1/ws/inference", outcome="connected")
    configuration: InferenceWebSocketConfigure | None = None
    pending_frame: InferenceWebSocketFrameMeta | None = None

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if message.get("text") is not None:
                try:
                    payload = json.loads(message["text"])
                except (json.JSONDecodeError, TypeError):
                    await send_inference_error(websocket, "invalid_json", "Message must be valid JSON")
                    continue

                message_type = payload.get("type") if isinstance(payload, dict) else None
                try:
                    if message_type == "configure":
                        candidate = InferenceWebSocketConfigure.model_validate(payload)
                        if candidate.zones is not None:
                            try:
                                validate_zone_geometry(candidate.zones)
                            except MonitoringZoneGeometryError as exc:
                                await send_inference_error(
                                    websocket,
                                    "zone_geometry_conflict",
                                    f"Conflicting zones: {', '.join(exc.zone_ids)}",
                                )
                                continue
                            persisted = MonitoringZoneService(db).get(candidate.camera_id)
                            candidate_zones = [
                                zone.model_dump(mode="json")
                                for zone in sorted(candidate.zones, key=lambda item: item.order)
                            ]
                            persisted_zones = [zone.model_dump(mode="json") for zone in persisted.zones]
                            if candidate.zone_revision != persisted.revision or candidate_zones != persisted_zones:
                                await send_inference_error(
                                    websocket,
                                    "zone_revision_conflict",
                                    "Monitoring zone configuration is not the saved revision",
                                )
                                continue
                        if (
                            configuration is not None
                            and candidate.monitoring_session_id != configuration.monitoring_session_id
                        ):
                            await send_inference_error(
                                websocket, "session_mismatch", "A connection cannot change monitoring session"
                            )
                            continue
                        candidate_session = str(candidate.monitoring_session_id)
                        if configuration is None and candidate_session in active_inference_sessions:
                            await send_inference_error(
                                websocket, "session_in_use", "Monitoring session already has an active connection"
                            )
                            continue
                        configuration = candidate
                        active_inference_sessions.add(candidate_session)
                        pending_frame = None
                        configured = {
                            "type": "configured",
                            "monitoring_session_id": str(configuration.monitoring_session_id),
                        }
                        if configuration.zones is not None:
                            configured["zone_revision"] = configuration.zone_revision
                        await websocket.send_json(configured)
                    elif message_type == "frame_meta":
                        if configuration is None:
                            await send_inference_error(
                                websocket,
                                "not_configured",
                                "Send a valid four-point configuration before frames",
                            )
                            continue
                        if pending_frame is not None:
                            await send_inference_error(
                                websocket,
                                "frame_pending",
                                "Send the pending JPEG before another frame_meta message",
                            )
                            continue
                        pending_frame = InferenceWebSocketFrameMeta.model_validate(payload)
                    else:
                        await send_inference_error(
                            websocket,
                            "unknown_message",
                            "Expected configure or frame_meta message",
                        )
                except ValidationError as exc:
                    await send_inference_error(websocket, "validation_error", str(exc))
                continue

            frame_bytes = message.get("bytes")
            if frame_bytes is None:
                await send_inference_error(websocket, "invalid_message", "Expected JSON text or JPEG bytes")
                continue
            if configuration is None:
                await send_inference_error(
                    websocket,
                    "not_configured",
                    "Send a valid four-point configuration before frames",
                )
                continue
            if pending_frame is None:
                await send_inference_error(
                    websocket,
                    "missing_frame_meta",
                    "Send frame_meta before JPEG bytes",
                )
                continue

            frame_meta = pending_frame
            pending_frame = None
            image_data = f"data:image/jpeg;base64,{base64.b64encode(frame_bytes).decode()}"
            configuration_fields = (
                {
                    "zones": configuration.zones,
                    "zone_revision": configuration.zone_revision,
                    "camera_id": configuration.camera_id,
                    "machine_state": configuration.machine_state,
                }
                if configuration.zones is not None
                else {
                    "zone_points": configuration.zone_points,
                    "machine_state": configuration.machine_state,
                    "camera_id": configuration.camera_id,
                    "zone_id": configuration.zone_id,
                }
            )
            request = FrameInferenceRequest(
                image_data=image_data,
                monitoring_session_id=configuration.monitoring_session_id,
                frame_id=frame_meta.frame_id,
                **configuration_fields,
            )
            started_at = time.perf_counter()
            try:
                requirements = PpeRequirementService(db).get(request.camera_id, request.zone_id)
                result = await asyncio.to_thread(frame_inference_service.infer, request, requirements=requirements)
            except InvalidFrameError as exc:
                await send_inference_error(websocket, "invalid_frame", str(exc))
                continue
            except StaleFrameError as exc:
                await send_inference_error(websocket, "stale_frame", str(exc))
                continue
            except Exception:
                logger.exception("WebSocket frame inference failed")
                await send_inference_error(websocket, "inference_failed", "Frame inference failed")
                continue

            await websocket.send_json(
                {
                    "type": "inference_result",
                    "monitoring_session_id": str(configuration.monitoring_session_id),
                    "frame_id": frame_meta.frame_id,
                    "video_time": frame_meta.video_time,
                    **result.model_dump(mode="json"),
                }
            )
            record_operational_event(
                "inference_completed",
                route="/api/v1/ws/inference",
                outcome=result.result,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
            )
    except WebSocketDisconnect:
        pass
    finally:
        if configuration is not None:
            active_inference_sessions.discard(str(configuration.monitoring_session_id))
        record_operational_event("websocket_connection_closed", route="/api/v1/ws/inference", outcome="disconnected")
