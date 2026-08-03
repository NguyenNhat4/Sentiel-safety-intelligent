import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from backend.app.schemas.analysis import (
    FrameInferenceRequest,
    InferenceWebSocketConfigure,
    InferenceWebSocketFrameMeta,
)
from backend.app.services.frame_inference_service import InvalidFrameError, frame_inference_service

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


@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time safety violation alerts."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open & handle incoming client messages if any
            data = await websocket.receive_text()
            # Echo ping / pong or client ack
            await websocket.send_text(json.dumps({"type": "pong", "received": data}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def send_inference_error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json({"type": "error", "code": code, "message": message})


@router.websocket("/ws/inference")
async def websocket_inference_endpoint(websocket: WebSocket):
    """Run sampled browser-frame inference over a persistent WebSocket."""
    await websocket.accept()
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
                        configuration = InferenceWebSocketConfigure.model_validate(payload)
                        pending_frame = None
                        await websocket.send_json({"type": "configured"})
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
            request = FrameInferenceRequest(
                image_data=image_data,
                zone_points=configuration.zone_points,
                machine_state=configuration.machine_state,
            )
            try:
                result = await asyncio.to_thread(frame_inference_service.infer, request)
            except InvalidFrameError as exc:
                await send_inference_error(websocket, "invalid_frame", str(exc))
                continue
            except Exception:
                logger.exception("WebSocket frame inference failed")
                await send_inference_error(websocket, "inference_failed", "Frame inference failed")
                continue

            await websocket.send_json(
                {
                    "type": "inference_result",
                    "frame_id": frame_meta.frame_id,
                    "video_time": frame_meta.video_time,
                    **result.model_dump(),
                }
            )
    except WebSocketDisconnect:
        pass
