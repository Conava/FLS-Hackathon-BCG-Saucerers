"""Application configuration loaded from environment variables.

Uses pydantic-settings v2 with SettingsConfigDict for env-file support.
No PHI is ever stored in settings — only connection strings, keys, and flags.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    All fields are read from environment variables (case-insensitive).
    An optional `.env` file at the working-directory root is also read if
    present; environment variables take precedence over the file.

    Required:
        database_url: Async SQLAlchemy DSN (must use ``asyncpg`` driver).
        api_key: Shared secret validated by the ``api_key_auth`` dependency.

    Optional:
        log_level: Standard Python logging level name. Default: ``"INFO"``.
        app_env: Deployment environment label. Default: ``"development"``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    """Async SQLAlchemy database URL, e.g. ``postgresql+asyncpg://user:pass@host/db``."""

    api_key: str
    """Shared API key validated on every protected request via ``X-API-Key`` header."""

    log_level: str = "INFO"
    """Python logging level name: DEBUG, INFO, WARNING, ERROR, CRITICAL."""

    app_env: str = "development"
    """Deployment environment: development, staging, production."""


def get_settings() -> Settings:
    """Return a fresh Settings instance.

    Call this at module-level in components that need access to settings.
    Tests can override env vars with ``monkeypatch.setenv`` before constructing.
    """
    return Settings()
