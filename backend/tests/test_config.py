from backend.app.core.config import Settings


def test_settings_loads_production_env_file() -> None:
    assert Settings.model_config["env_file"] == ".env.production"
