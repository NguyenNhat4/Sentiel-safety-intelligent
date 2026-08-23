from fastapi import APIRouter

from backend.app.api.v1 import (
    agent,
    analysis,
    auth,
    camera_configurations,
    camera_sessions,
    events,
    media_assets,
    monitoring_zones,
    operational_metrics,
    ppe_requirements,
    statistics,
    websocket,
)

api_router = APIRouter()

api_router.include_router(analysis.router)
api_router.include_router(auth.router)
api_router.include_router(media_assets.router)
api_router.include_router(camera_configurations.router)
api_router.include_router(camera_sessions.router)
api_router.include_router(events.router)
api_router.include_router(events.batch_router)
api_router.include_router(monitoring_zones.router)
api_router.include_router(statistics.router)
api_router.include_router(operational_metrics.router)
api_router.include_router(websocket.router)
api_router.include_router(agent.router)
api_router.include_router(ppe_requirements.router)
