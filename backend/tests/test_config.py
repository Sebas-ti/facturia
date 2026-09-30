from pytest import MonkeyPatch

from app.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_env == "local"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_env_override(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    settings = Settings(_env_file=None)
    assert settings.app_env == "test"
