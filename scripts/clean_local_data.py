"""Destructively clear local PostgreSQL application data and runtime files."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text

from backend.app.core.config import get_settings

EXCLUDED_TABLES = {"alembic_version"}


def _require_local_postgres(database_url: str, app_env: str) -> None:
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").casefold()
    if not database_url.startswith(("postgresql://", "postgresql+", "postgres://")):
        raise SystemExit("Refusing cleanup: DATABASE_URL must be PostgreSQL.")
    if app_env == "production" or host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Refusing cleanup: only local PostgreSQL is allowed (localhost/127.0.0.1/::1).")


def _safe_runtime_dir(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    path = path.resolve()
    if path in {repo_root, repo_root.parent, Path("/")} or repo_root not in path.parents:
        raise SystemExit(f"Refusing cleanup outside repository: {path}")
    return path


def _clear_directory(path: Path) -> int:
    if not path.exists():
        return 0
    removed = 0
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed += 1
    return removed


def clear_postgres(database_url: str) -> list[str]:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            tables = sorted(set(inspect(connection).get_table_names()) - EXCLUDED_TABLES)
            if tables:
                quoted = ", ".join(f'"{table.replace(chr(34), chr(34) * 2)}"' for table in tables)
                connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
            return tables
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="confirm destructive local cleanup")
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("Nothing deleted. Re-run with --yes after checking the local target.")

    settings = get_settings()
    _require_local_postgres(settings.database_url, settings.app_env)
    repo_root = Path(__file__).resolve().parents[1]
    directories = {
        "media": _safe_runtime_dir(settings.media_asset_dir, repo_root),
        "snapshots": _safe_runtime_dir(settings.snapshot_dir, repo_root),
        "logs": _safe_runtime_dir(Path(settings.operational_metrics_log_path).parent, repo_root),
    }
    print(f"target_database={urlparse(settings.database_url).hostname}:{urlparse(settings.database_url).port}")
    print(f"tables={','.join(clear_postgres(settings.database_url)) or '(none)'}")
    for name, directory in directories.items():
        print(f"{name}_entries_removed={_clear_directory(directory)} path={directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
