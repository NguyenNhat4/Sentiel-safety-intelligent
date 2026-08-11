import logging
from collections.abc import Generator
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseRuntime:
    engine: Engine
    url: str
    backend: str
    fallback_active: bool


def _create_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    connect_args = {}
    if url.startswith(("postgresql", "postgres")):
        connect_args.update(
            connect_timeout=settings.database_connect_timeout_seconds,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
    return create_engine(
        url,
        pool_pre_ping=settings.database_pool_pre_ping,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_pool_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
        pool_use_lifo=settings.database_pool_use_lifo,
        connect_args=connect_args,
    )


def _verify_connection(candidate: Engine) -> None:
    with candidate.connect() as connection:
        connection.execute(text("SELECT 1"))


def create_database_runtime(primary_url: str, fallback_url: str, fallback_enabled: bool) -> DatabaseRuntime:
    primary = _create_engine(primary_url)
    try:
        _verify_connection(primary)
        backend = "postgresql" if primary_url.startswith(("postgresql", "postgres")) else "sqlite"
        return DatabaseRuntime(primary, primary_url, backend, False)
    except Exception as exc:
        primary.dispose()
        if not fallback_enabled or primary_url.startswith("sqlite"):
            raise
        fallback = _create_engine(fallback_url)
        _verify_connection(fallback)
        logger.warning(
            "Primary database is unavailable (%s); using SQLite fallback for this process. "
            "Restart the service to retry the primary database.",
            type(exc).__name__,
        )
        return DatabaseRuntime(fallback, fallback_url, "sqlite_fallback", True)


database_runtime = create_database_runtime(
    settings.database_url,
    settings.database_fallback_url,
    settings.database_fallback_enabled,
)
engine = database_runtime.engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
