from fastapi import APIRouter

from backend.app.api.v1 import agent, analysis, events, statistics, websocket

api_router = APIRouter()

api_router.include_router(analysis.router)
api_router.include_router(events.router)
api_router.include_router(statistics.router)
api_router.include_router(websocket.router)
api_router.include_router(agent.router)
