"""Unit tests for app.core.config — Settings loads from environment variables."""
import os

import pytest

from app.core.config import Settings


class TestSettingsLoadsFromEnv:
    """Test that Settings correctly reads configuration from environment variables."""

    def test_settings_loads_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings reads DATABASE_URL from the environment."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
        monkeypatch.setenv("API_KEY", "test-key-12345")
        settings = Settings()
        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/test"

    def test_settings_loads_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings reads API_KEY from the environment."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
        monkeypatch.setenv("API_KEY", "secret-api-key")
        settings = Settings()
        assert settings.api_key == "secret-api-key"

    def test_settings_loads_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings reads LOG_LEVEL from the environment with a default of INFO."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_settings_log_level_defaults_to_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LOG_LEVEL defaults to 'INFO' when not set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_settings_loads_app_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings reads APP_ENV from the environment."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("APP_ENV", "production")
        settings = Settings()
        assert settings.app_env == "production"

    def test_settings_app_env_defaults_to_development(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """APP_ENV defaults to 'development' when not set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.delenv("APP_ENV", raising=False)
        settings = Settings()
        assert settings.app_env == "development"

    def test_settings_reads_multiple_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings reads DATABASE_URL, API_KEY, and LOG_LEVEL from env together."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/mydb")
        monkeypatch.setenv("API_KEY", "my-api-key")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("APP_ENV", "staging")
        settings = Settings()
        assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/mydb"
        assert settings.api_key == "my-api-key"
        assert settings.log_level == "WARNING"
        assert settings.app_env == "staging"

    def test_settings_missing_required_field_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Settings raises ValidationError when a required env var is missing."""
        from pydantic import ValidationError

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)
        # Remove .env file influence by pointing to non-existent file
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]
