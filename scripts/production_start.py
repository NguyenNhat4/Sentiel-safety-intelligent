"""Container entrypoint: validate files and start one production worker."""

from __future__ import annotations

import os
import subprocess
import sys

from backend.app.core.config import get_settings
from backend.app.core.startup_validation import validate_runtime_files
from scripts.bootstrap_legacy_sqlite import bootstrap_legacy_sqlite


def main() -> None:
    settings = get_settings()
    if settings.app_env != "production":
        raise RuntimeError("Container startup requires APP_ENV=production")
    if settings.database_fallback_enabled:
        raise RuntimeError("Production container requires DATABASE_FALLBACK_ENABLED=false")

    validate_runtime_files(settings)
    if settings.run_db_migrations_on_start:
        bootstrap_legacy_sqlite(settings.database_url)
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
        subprocess.run([sys.executable, "-m", "alembic", "current", "--check-heads"], check=True)
    os.execvp(
        "uvicorn",
        ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", str(settings.app_port)],
    )


if __name__ == "__main__":
    main()
