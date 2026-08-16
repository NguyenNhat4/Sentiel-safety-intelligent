from backend.app.core.config import Settings


def test_settings_load_development_environment_file_by_default() -> None:
    assert Settings.model_config["env_file"] == ".env.development"
