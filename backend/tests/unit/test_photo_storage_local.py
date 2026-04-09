"""Unit tests for LocalFsPhotoStorage.

TDD red phase: tests are written before the implementation.
All tests exercise only the local filesystem backend via tmp_path.
The GCS backend is never constructed here (no GCP creds needed).
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

from app.adapters.photo_storage import LocalFsPhotoStorage


class TestLocalFsPhotoStoragePut:
    """put() stores bytes and returns a file:// URI."""

    def test_put_returns_file_uri(self, tmp_path: Path) -> None:
        """put() returns a URI that starts with file://."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uri = storage.put("PT0001", "photo.jpg", b"fake-image-data")
        assert uri.startswith("file://")

    def test_put_uri_contains_patient_id(self, tmp_path: Path) -> None:
        """put() embeds the patient_id in the URI path."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uri = storage.put("PT0001", "photo.jpg", b"fake-image-data")
        assert "PT0001" in uri

    def test_put_uri_preserves_extension(self, tmp_path: Path) -> None:
        """put() preserves the original file extension in the stored filename."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uri = storage.put("PT0001", "meal.jpg", b"fake-image-data")
        assert uri.endswith(".jpg")

    def test_put_uri_png_extension(self, tmp_path: Path) -> None:
        """put() preserves .png extension."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uri = storage.put("PT0001", "photo.png", b"png-bytes")
        assert uri.endswith(".png")

    def test_put_creates_patient_directory(self, tmp_path: Path) -> None:
        """put() creates the <base_dir>/<patient_id> directory if it doesn't exist."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        storage.put("PT0001", "photo.jpg", b"data")
        assert (tmp_path / "PT0001").is_dir()

    def test_put_writes_bytes_to_disk(self, tmp_path: Path) -> None:
        """put() writes the exact bytes to disk."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        payload = b"exact-bytes-content"
        uri = storage.put("PT0001", "photo.jpg", payload)
        # Extract path from URI and verify the file content
        file_path = Path(uri[len("file://"):])
        assert file_path.read_bytes() == payload

    def test_put_uses_uuid_for_filename(self, tmp_path: Path) -> None:
        """put() assigns a UUID-based filename, not the original name."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uri = storage.put("PT0001", "original_name.jpg", b"data")
        # The filename should not be 'original_name.jpg'
        stored_name = Path(uri).name
        assert stored_name != "original_name.jpg"

    def test_put_two_files_get_distinct_uris(self, tmp_path: Path) -> None:
        """put() assigns distinct URIs for each upload (UUID uniqueness)."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uri1 = storage.put("PT0001", "photo.jpg", b"bytes-1")
        uri2 = storage.put("PT0001", "photo.jpg", b"bytes-2")
        assert uri1 != uri2


class TestLocalFsPhotoStorageGetBytes:
    """get_bytes() round-trips data written by put()."""

    def test_get_bytes_round_trip(self, tmp_path: Path) -> None:
        """get_bytes(uri) returns the exact bytes previously stored via put()."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        payload = b"round-trip payload"
        uri = storage.put("PT0001", "photo.jpg", payload)
        result = storage.get_bytes(uri)
        assert result == payload

    def test_get_bytes_raises_on_missing_uri(self, tmp_path: Path) -> None:
        """get_bytes() raises FileNotFoundError when the URI points to no file."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        fake_uri = f"file://{tmp_path}/PT0001/nonexistent.jpg"
        with pytest.raises(FileNotFoundError):
            storage.get_bytes(fake_uri)


class TestLocalFsPhotoStorageDelete:
    """delete() removes a single file."""

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        """delete(uri) removes the file from disk."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uri = storage.put("PT0001", "photo.jpg", b"data")
        file_path = Path(uri[len("file://"):])
        assert file_path.exists()
        storage.delete(uri)
        assert not file_path.exists()

    def test_delete_nonexistent_is_silent(self, tmp_path: Path) -> None:
        """delete() does not raise when the URI points to a missing file."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        fake_uri = f"file://{tmp_path}/PT0001/nonexistent.jpg"
        # Should not raise
        storage.delete(fake_uri)


class TestLocalFsPhotoStorageDeleteAllForPatient:
    """delete_all_for_patient() removes all files for one patient, none for others."""

    def test_delete_all_removes_all_patient_files(self, tmp_path: Path) -> None:
        """delete_all_for_patient() removes every file for the given patient."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        uris = [
            storage.put("PT0001", f"photo{i}.jpg", f"data{i}".encode())
            for i in range(3)
        ]
        count = storage.delete_all_for_patient("PT0001")
        assert count == 3
        for uri in uris:
            assert not Path(uri[len("file://"):]).exists()

    def test_delete_all_returns_count(self, tmp_path: Path) -> None:
        """delete_all_for_patient() returns the number of files deleted."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        for i in range(5):
            storage.put("PT0001", f"photo{i}.jpg", b"data")
        count = storage.delete_all_for_patient("PT0001")
        assert count == 5

    def test_delete_all_does_not_touch_other_patient(self, tmp_path: Path) -> None:
        """delete_all_for_patient() leaves files for other patients intact."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        # Upload for two patients
        storage.put("PT0001", "photo1.jpg", b"data1")
        uri_pt2 = storage.put("PT0002", "photo2.jpg", b"data2")

        # Delete only PT0001
        storage.delete_all_for_patient("PT0001")

        # PT0002's file must still be readable
        assert storage.get_bytes(uri_pt2) == b"data2"

    def test_delete_all_for_missing_patient_returns_zero(self, tmp_path: Path) -> None:
        """delete_all_for_patient() returns 0 when the patient has no files."""
        storage = LocalFsPhotoStorage(base_dir=tmp_path)
        count = storage.delete_all_for_patient("PT9999")
        assert count == 0


class TestGetPhotoStorageFactory:
    """get_photo_storage() factory returns the right backend based on settings."""

    def test_factory_returns_local_backend_by_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """get_photo_storage returns LocalFsPhotoStorage when backend='local'."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "key")
        monkeypatch.setenv("PHOTO_STORAGE_BACKEND", "local")
        monkeypatch.setenv("PHOTO_LOCAL_DIR", str(tmp_path))

        from app.adapters.photo_storage import get_photo_storage
        from app.core.config import Settings

        settings = Settings()
        adapter = get_photo_storage(settings)
        assert isinstance(adapter, LocalFsPhotoStorage)

    def test_factory_gcs_backend_construction_mocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_photo_storage returns GcsPhotoStorage when backend='gcs' (Client mocked)."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "key")
        monkeypatch.setenv("PHOTO_STORAGE_BACKEND", "gcs")
        monkeypatch.setenv("PHOTO_GCS_BUCKET", "my-test-bucket")

        from app.adapters.photo_storage import GcsPhotoStorage, get_photo_storage
        from app.core.config import Settings

        # Patch the GCS Client so we never touch real GCP
        import unittest.mock as mock

        with mock.patch("app.adapters.photo_storage._get_gcs_client") as mock_client:
            mock_client.return_value = mock.MagicMock()
            settings = Settings()
            adapter = get_photo_storage(settings)
            assert isinstance(adapter, GcsPhotoStorage)


class TestRelativePathURIStability:
    """Regression: put() with a relative base_dir must produce stable URIs.

    Before the fix, ``LocalFsPhotoStorage(Path("rel/photos")).put(...)``
    returned a URI like ``file://rel/photos/PT0001/<uuid>.jpg``. After the
    process CWD changed, ``get_bytes()`` and ``delete()`` could no longer
    locate the file because ``Path("rel/photos/...")`` resolved to a different
    absolute path.
    """

    def test_relative_base_dir_round_trips_after_chdir(
        self, tmp_path: Path
    ) -> None:
        """get_bytes() and delete() work even after the CWD changes post-put().

        Scenario:
        1. CWD is set to ``tmp_path``.
        2. Storage is created with a relative directory ``rel/photos``.
        3. ``put()`` is called — the file is written.
        4. CWD is changed to a different directory (``tmp_path / "other"``).
        5. ``get_bytes()`` must return the same bytes.
        6. ``delete()`` must remove the file without raising.
        """
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            storage = LocalFsPhotoStorage(base_dir=Path("rel/photos"))
            payload = b"relative-path-roundtrip"
            uri = storage.put("PT0001", "photo.jpg", payload)

            # Confirm URI is absolute (starts with file:/// on POSIX)
            assert uri.startswith("file:///"), (
                f"URI must be absolute, got: {uri!r}"
            )

            # Move CWD so any relative resolution would break
            other_dir = tmp_path / "other"
            other_dir.mkdir()
            os.chdir(other_dir)

            # get_bytes must still work
            result = storage.get_bytes(uri)
            assert result == payload

            # delete must still work (idempotent on the now-present file)
            storage.delete(uri)
            # Calling get_bytes afterwards must raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                storage.get_bytes(uri)
        finally:
            os.chdir(original_cwd)


class TestFactoryImportErrorProbe:
    """Regression: get_photo_storage() must surface ImportError eagerly for GCS.

    Before the fix the ``try/except ImportError`` in the factory wrapped
    ``GcsPhotoStorage(bucket_name=bucket)`` — a call that never imports
    ``google.cloud.storage`` (the import is lazy inside ``_get_gcs_client``).
    As a result, a missing ``google-cloud-storage`` package was only detected
    on the first real upload, not at startup.

    After the fix the factory probes the import explicitly so the error is
    raised at ``get_photo_storage()`` time.
    """

    def test_import_error_raised_at_factory_when_gcs_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_photo_storage() raises ImportError immediately if google-cloud-storage is missing.

        The test must block the import at both levels:
        1. ``sys.modules["google.cloud.storage"] = None`` — blocks fresh imports.
        2. Remove the ``storage`` attribute from the ``google.cloud`` package
           object — necessary when the module was already imported earlier in
           the test session (Python resolves ``from google.cloud import storage``
           via the parent package's attribute cache, bypassing ``sys.modules``).
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "key")
        monkeypatch.setenv("PHOTO_STORAGE_BACKEND", "gcs")
        monkeypatch.setenv("PHOTO_GCS_BUCKET", "my-bucket")

        from app.adapters.photo_storage import get_photo_storage
        from app.core.config import Settings

        # Block the import at the sys.modules level.
        monkeypatch.setitem(sys.modules, "google.cloud.storage", None)  # type: ignore[arg-type]

        # Also remove the cached attribute from the parent package so that
        # ``from google.cloud import storage`` cannot bypass sys.modules.
        import google.cloud as _gc  # noqa: PLC0415
        monkeypatch.delattr(_gc, "storage", raising=False)

        settings = Settings()
        with pytest.raises(ImportError, match="google-cloud-storage is required"):
            get_photo_storage(settings)

    def test_factory_gcs_raises_value_error_when_bucket_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_photo_storage() raises ValueError when backend='gcs' but bucket is unset."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "key")
        monkeypatch.setenv("PHOTO_STORAGE_BACKEND", "gcs")
        # Explicitly unset the bucket variable
        monkeypatch.delenv("PHOTO_GCS_BUCKET", raising=False)

        from app.adapters.photo_storage import get_photo_storage
        from app.core.config import Settings

        settings = Settings()
        with pytest.raises(ValueError, match="photo_gcs_bucket"):
            get_photo_storage(settings)
