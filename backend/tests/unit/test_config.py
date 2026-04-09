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

    def test_settings_app_env_defaults_to_local(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """APP_ENV defaults to 'local' when not set (sourced from .env file)."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.delenv("APP_ENV", raising=False)
        settings = Settings()
        assert settings.app_env == "local"

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


class TestLLMAndGCPSettings:
    """Test that T3 LLM/GCP settings are present and have correct defaults."""

    def test_llm_provider_defaults_to_fake(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """llm_provider defaults to 'fake' when not set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        settings = Settings()
        assert settings.llm_provider == "fake"

    def test_llm_provider_can_be_set_to_gemini(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """llm_provider accepts 'gemini' as a valid value."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        settings = Settings()
        assert settings.llm_provider == "gemini"

    def test_gcp_project_defaults_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """gcp_project defaults to None when not set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        settings = Settings()
        assert settings.gcp_project is None

    def test_gcp_project_can_be_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """gcp_project is read from GCP_PROJECT env var."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("GCP_PROJECT", "my-gcp-project")
        settings = Settings()
        assert settings.gcp_project == "my-gcp-project"

    def test_gcp_location_defaults_to_europe_west3(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """gcp_location defaults to 'europe-west3' (EU-only data residency)."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.delenv("GCP_LOCATION", raising=False)
        settings = Settings()
        assert settings.gcp_location == "europe-west3"

    def test_gcp_location_can_be_overridden(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """gcp_location can be overridden via GCP_LOCATION env var."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("GCP_LOCATION", "us-central1")
        settings = Settings()
        assert settings.gcp_location == "us-central1"
