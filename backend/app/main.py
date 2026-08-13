import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.database import Base, SessionLocal, database_runtime, engine
from backend.app.core.operational_metrics import configure_operational_metrics_logger, record_operational_event
from backend.app.services.auth_service import AuthService
from backend.app.services.frame_inference_service import frame_inference_service

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_operational_metrics_logger(
        settings.operational_metrics_log_path,
        max_bytes=settings.operational_metrics_log_max_bytes,
        backup_count=settings.operational_metrics_log_backup_count,
    )
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
    logger.info("Unified YOLO11m Safety person/hat/vest inference model loaded.")

    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
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
snapshot_dir = Path(__file__).resolve().parents[2] / "data" / "snapshots"
snapshot_dir.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=snapshot_dir), name="event-snapshots")


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {
        "status": "ok",
        "env": settings.app_env,
        "service": settings.app_name,
        "database": database_runtime.backend,
        "database_fallback_active": database_runtime.fallback_active,
    }


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
