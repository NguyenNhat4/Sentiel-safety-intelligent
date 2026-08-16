from backend.app.core.config import Settings


def test_settings_loads_legacy_env_after_development_defaults() -> None:
    assert Settings.model_config["env_file"] == (".env.development", ".env")
