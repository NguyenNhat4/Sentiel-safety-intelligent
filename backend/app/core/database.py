from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.app.core.config import get_settings

settings = get_settings()

# Use SQLite fallback in dev/test if Postgres driver is missing or SQLite URL passed
db_url = settings.database_url
if db_url.startswith("sqlite"):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
