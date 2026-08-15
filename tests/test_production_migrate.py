from types import SimpleNamespace

import pytest

from scripts import production_migrate, production_start


def test_main_upgrades_then_verifies_single_database_head(monkeypatch):
    commands: list[list[str]] = []

    monkeypatch.setattr(
        production_migrate.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )
    monkeypatch.setattr(
        production_migrate,
        "get_settings",
        lambda: SimpleNamespace(app_env="production", database_fallback_enabled=False),
    )

    production_migrate.main()

    assert commands == [
        [production_migrate.sys.executable, "-m", "alembic", "upgrade", "head"],
        [production_migrate.sys.executable, "-m", "alembic", "current", "--check-heads"],
    ]


def test_production_start_skips_migrations_when_the_deployment_job_owns_them(monkeypatch):
    commands: list[list[str]] = []

    monkeypatch.setattr(
        production_start,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="production",
            database_fallback_enabled=False,
            run_db_migrations_on_start=False,
            app_port=8000,
        ),
    )
    monkeypatch.setattr(production_start, "validate_runtime_files", lambda settings: None)
    monkeypatch.setattr(
        production_start.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )
    monkeypatch.setattr(
        production_start.os,
        "execvp",
        lambda executable, arguments: (_ for _ in ()).throw(SystemExit()),
    )

    with pytest.raises(SystemExit):
        production_start.main()

    assert commands == []


def test_container_start_allows_development_mode_for_the_compose_seed_database(monkeypatch):
    monkeypatch.setattr(
        production_start,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            database_fallback_enabled=False,
            run_db_migrations_on_start=False,
            app_port=8000,
        ),
    )
    monkeypatch.setattr(production_start, "validate_runtime_files", lambda settings: None)
    monkeypatch.setattr(
        production_start.os,
        "execvp",
        lambda executable, arguments: (_ for _ in ()).throw(SystemExit()),
    )

    with pytest.raises(SystemExit):
        production_start.main()
