import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.database import Base, engine

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables in development if DB is reachable
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to database on startup: {e}")

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
snapshot_dir = Path(__file__).resolve().parents[2] / "data" / "snapshots"
snapshot_dir.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=snapshot_dir), name="event-snapshots")


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "env": settings.app_env, "service": settings.app_name}


@app.get("/", include_in_schema=False)
async def frontend_index():
    return FileResponse(frontend_dir / "index.html")


if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir), name="frontend-assets")
