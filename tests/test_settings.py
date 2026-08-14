from backend.app.core.config import Settings


def test_settings_uses_platform_port_when_app_port_is_not_set(monkeypatch):
    monkeypatch.setenv("PORT", "4567")
    monkeypatch.delenv("APP_PORT", raising=False)

    assert Settings(_env_file=None).app_port == 4567
