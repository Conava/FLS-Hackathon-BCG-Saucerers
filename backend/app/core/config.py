"""Application configuration loaded from environment variables.

Uses pydantic-settings v2 with SettingsConfigDict for env-file support.
No PHI is ever stored in settings — only connection strings, keys, and flags.
"""
from pathlib import Path
from typing import Literal

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
        photo_storage_backend: ``"local"`` (default) or ``"gcs"``.
        photo_local_dir: Root path for local photo storage. Default: ``./var/photos``.
        photo_gcs_bucket: GCS bucket name. Required when backend is ``"gcs"``.
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

    # ------------------------------------------------------------------
    # Photo storage
    # ------------------------------------------------------------------

    photo_storage_backend: Literal["local", "gcs"] = "local"
    """Which photo storage backend to use.

    ``"local"`` — writes under ``photo_local_dir`` (development/test).
    ``"gcs"`` — uploads to the GCS bucket named in ``photo_gcs_bucket`` (production).
    """

    photo_local_dir: Path = Path("./var/photos")
    """Root directory for local photo storage.

    Only used when ``photo_storage_backend == "local"``.
    The directory (and per-patient subdirectories) is created on first write.
    """

    photo_gcs_bucket: str | None = None
    """GCS bucket name for production photo storage.

    Required (and validated at runtime) when ``photo_storage_backend == "gcs"``.
    Must **not** include the ``gs://`` prefix — just the bare bucket name.
    """


def get_settings() -> Settings:
    """Return a fresh Settings instance.

    Call this at module-level in components that need access to settings.
    Tests can override env vars with ``monkeypatch.setenv`` before constructing.
    """
    return Settings()
