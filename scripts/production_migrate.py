"""Apply and verify Alembic migrations as the single deployment migration job."""

from __future__ import annotations

import subprocess
import sys

from backend.app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    if settings.app_env != "production":
        raise RuntimeError("Production migration job requires APP_ENV=production")
    if settings.database_fallback_enabled:
        raise RuntimeError("Production migration job requires DATABASE_FALLBACK_ENABLED=false")

    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    subprocess.run([sys.executable, "-m", "alembic", "current", "--check-heads"], check=True)


if __name__ == "__main__":
    main()
