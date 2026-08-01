import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
