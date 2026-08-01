from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.core.database import Base, engine
from backend.app.api.router import api_router

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


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "env": settings.app_env, "service": settings.app_name}
