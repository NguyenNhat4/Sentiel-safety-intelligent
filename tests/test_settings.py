import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_uses_platform_port_when_app_port_is_not_set(monkeypatch):
    monkeypatch.setenv("PORT", "4567")
    monkeypatch.delenv("APP_PORT", raising=False)

    assert Settings(_env_file=None).app_port == 4567


def test_settings_defaults_to_the_pinned_unified_safety_checkpoint():
    settings = Settings(_env_file=None)

    assert settings.ppe_model_path == "models/yolo11n_safety_kd_best.pt"
    assert settings.vision_provider == "local"


def test_remote_vision_provider_requires_url():
    with pytest.raises(ValidationError, match="VISION_REMOTE_URL"):
        Settings(_env_file=None, vision_provider="remote")


def test_remote_vision_provider_uses_typed_connection_settings():
    settings = Settings(
        _env_file=None,
        vision_provider="remote",
        vision_remote_url="https://vision.example",
        vision_remote_api_key="secret-token",
        vision_remote_timeout_seconds=2.5,
    )

    assert settings.vision_remote_url == "https://vision.example"
    assert settings.vision_remote_api_key.get_secret_value() == "secret-token"
    assert settings.vision_remote_timeout_seconds == 2.5


def test_production_remote_vision_requires_api_key():
    with pytest.raises(ValidationError, match="VISION_REMOTE_API_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            vision_provider="remote",
            vision_remote_url="https://vision.example",
        )
