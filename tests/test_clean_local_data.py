from pathlib import Path

import pytest

from scripts.clean_local_data import _require_local_postgres, _safe_runtime_dir


def test_cleanup_requires_local_postgres():
    with pytest.raises(SystemExit, match="only local PostgreSQL"):
        _require_local_postgres("postgresql://user:pass@postgres-3ljr.railway.internal/db", "development")


def test_cleanup_rejects_production_even_on_local_host():
    with pytest.raises(SystemExit, match="only local PostgreSQL"):
        _require_local_postgres("postgresql://user:pass@localhost/db", "production")


def test_runtime_directory_must_be_inside_repository(tmp_path: Path):
    with pytest.raises(SystemExit, match="outside repository"):
        _safe_runtime_dir("/tmp", tmp_path)

