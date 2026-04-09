"""Unit tests for app.core.security — X-API-Key FastAPI dependency."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.security import api_key_auth


def _build_app(env_api_key: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Build a TestClient with the api_key_auth dependency and given configured key."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/test")
    monkeypatch.setenv("API_KEY", env_api_key)

    app = FastAPI()

    @app.get("/guarded")
    async def guarded(auth: None = Depends(api_key_auth)) -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app, raise_server_exceptions=False)


class TestApiKeyDep:
    """Tests for the api_key_auth FastAPI dependency."""

    def test_api_key_dep_rejects_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dependency raises 401 when X-API-Key header is absent."""
        client = _build_app("correct-key", monkeypatch)
        response = client.get("/guarded")
        assert response.status_code == 401

    def test_api_key_dep_rejects_wrong_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dependency raises 401 when X-API-Key header has the wrong value."""
        client = _build_app("correct-key", monkeypatch)
        response = client.get("/guarded", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401

    def test_api_key_dep_accepts_correct_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dependency passes (200) when X-API-Key matches the configured API_KEY."""
        client = _build_app("correct-key", monkeypatch)
        response = client.get("/guarded", headers={"X-API-Key": "correct-key"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_api_key_dep_rejects_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dependency raises 401 when X-API-Key header is an empty string."""
        client = _build_app("correct-key", monkeypatch)
        response = client.get("/guarded", headers={"X-API-Key": ""})
        assert response.status_code == 401
