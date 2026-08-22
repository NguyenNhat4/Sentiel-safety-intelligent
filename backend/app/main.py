import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.database import Base, SessionLocal, check_database_connection, database_runtime, engine
from backend.app.core.operational_metrics import configure_operational_metrics_logger, record_operational_event
from backend.app.integrations.privacy_vision import get_configured_privacy_vision_adapter
from backend.app.integrations.snapshot_storage import (
    SnapshotStorageError,
    check_snapshot_storage_connection,
    create_snapshot_storage,
)
from backend.app.schemas.health import DependencyReadiness, HealthResponse
from backend.app.services.auth_service import AuthService
from backend.app.services.frame_inference_service import frame_inference_service
from backend.app.services.server_camera_inference_runtime import ServerCameraInferenceRuntime

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_operational_metrics_logger(
        settings.operational_metrics_log_path,
        max_bytes=settings.operational_metrics_log_max_bytes,
        backup_count=settings.operational_metrics_log_backup_count,
    )
    app.state.ready = False
    app.state.runtime_files = {}
    # Auto-create tables in development if DB is reachable
    try:
        Base.metadata.create_all(bind=engine)
        if settings.app_env != "production":
            db = SessionLocal()
            try:
                AuthService(db).seed_demo_users()
            finally:
                db.close()
        logger.info("Database tables verified/created successfully using %s.", database_runtime.backend)
    except Exception as e:
        logger.warning(f"Could not connect to database on startup: {e}")

    frame_inference_service.preload_models()
    logger.info("Safety vision inference provider is ready.")
    get_configured_privacy_vision_adapter().preload()
    logger.info("OpenCV YuNet face detector loaded for snapshot privacy.")
    app.state.ready = True

    camera_inference_runtime = None
    camera_inference_task = None
    if settings.hls_inference_enabled:
        if not settings.hls_reader_origin:
            raise RuntimeError("HLS_READER_ORIGIN is required when HLS inference is enabled")
        camera_inference_runtime = ServerCameraInferenceRuntime(
            settings.hls_reader_origin,
            max_fps=settings.hls_inference_max_fps,
            poll_seconds=settings.hls_mapping_poll_seconds,
            media_protocol="hls",
        )
        camera_inference_task = asyncio.create_task(camera_inference_runtime.run())
        logger.info("Server-side HLS camera inference started.")

    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    if camera_inference_runtime is not None and camera_inference_task is not None:
        camera_inference_runtime.stop()
        await camera_inference_task
    print("Shutting down backend...")


app = FastAPI(
    title=settings.app_name,
    description="Backend API for Realtime Computer Vision Safety Monitoring & Escalation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=(r"https?://(localhost|127\.0\.0\.1)(:\d+)?" if settings.app_env != "production" else None),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_http_metrics(request: Request, call_next):
    if request.url.path == f"{settings.api_v1_prefix}/operational-metrics":
        return await call_next(request)
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        record_operational_event(
            "http_request_completed",
            method=request.method,
            route=getattr(request.scope.get("route"), "path", "unmatched"),
            status_class="5xx",
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
            outcome="error",
            error_kind="unhandled_exception",
        )
        raise
    record_operational_event(
        "http_request_completed",
        method=request.method,
        route=getattr(request.scope.get("route"), "path", "unmatched"),
        status_class=f"{response.status_code // 100}xx",
        duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        outcome="success" if response.status_code < 400 else "error",
    )
    return response


app.include_router(api_router, prefix=settings.api_v1_prefix)

frontend_dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/snapshots/{filename}", include_in_schema=False)
async def get_snapshot(filename: str):
    """Serve a redacted snapshot from the configured private storage backend."""
    if Path(filename).name != filename or not filename.endswith(".jpg"):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    try:
        content = create_snapshot_storage(settings).get(f"snapshots/{filename}")
    except SnapshotStorageError as exc:
        raise HTTPException(status_code=404, detail="Snapshot not found") from exc
    return Response(content=content, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


def _dependency_readiness(check, unavailable_reason: str) -> DependencyReadiness:
    try:
        check()
    except Exception:
        return DependencyReadiness(ready=False, reason=unavailable_reason)
    return DependencyReadiness(ready=True)


def check_streamer_connection(origin: str) -> None:
    response = httpx.get(
        f"{origin.rstrip('/')}/health",
        timeout=settings.streamer_health_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if payload != {"status": "ok"}:
        raise RuntimeError("Streamer returned an unexpected health response")


@app.get("/health", response_model=HealthResponse, tags=["Health Check"])
async def health_check() -> HealthResponse:
    if database_runtime.backend != "postgresql" or database_runtime.fallback_active:
        postgresql = DependencyReadiness(ready=False, reason="postgresql_required")
    else:
        postgresql = _dependency_readiness(
            lambda: check_database_connection(engine),
            "connection_failed",
        )

    if settings.snapshot_storage_backend != "s3":
        snapshot_storage = DependencyReadiness(ready=False, reason="s3_required")
    else:
        snapshot_storage = _dependency_readiness(
            lambda: check_snapshot_storage_connection(settings),
            "connection_failed",
        )

    if len(settings.hls_token_secret) < 32 or not settings.streamer_internal_origin:
        streamer = DependencyReadiness(ready=False, reason="not_configured")
    else:
        streamer = _dependency_readiness(
            lambda: check_streamer_connection(settings.streamer_internal_origin),
            "connection_failed",
        )

    ready = bool(getattr(app.state, "ready", False)) and postgresql.ready and snapshot_storage.ready and streamer.ready
    return HealthResponse(
        status="ok" if ready else "degraded",
        ready=ready,
        env=settings.app_env,
        service=settings.app_name,
        database=database_runtime.backend,
        database_fallback_active=database_runtime.fallback_active,
        dependencies={"postgresql": postgresql, "snapshot_storage": snapshot_storage, "streamer": streamer},
        runtime_files=getattr(app.state, "runtime_files", {}),
    )


@app.get("/", include_in_schema=False)
async def frontend_index():
    index_file = frontend_dist_dir / "index.html"
    if not index_file.exists():
        return HTMLResponse(
            "Frontend build is missing. Run `make frontend-build` first.",
            status_code=503,
        )
    return FileResponse(index_file)


if frontend_dist_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dist_dir), name="frontend-assets")
