"""Photo storage adapter with local-fs (dev) and GCS (prod) backends.

Provides a ``PhotoStorage`` Protocol and two concrete implementations:

* ``LocalFsPhotoStorage`` — stores photos under a local directory tree.
  Used in development and unit tests; requires no cloud credentials.
* ``GcsPhotoStorage`` — stores photos in a Google Cloud Storage bucket.
  GCS client is constructed lazily so importing this module never triggers a
  network call or credential lookup.

Usage
-----
Obtain the correct backend via the factory::

    from app.adapters.photo_storage import get_photo_storage
    from app.core.config import get_settings

    storage = get_photo_storage(get_settings())
    uri = storage.put("PT0001", "meal.jpg", image_bytes)
    data = storage.get_bytes(uri)
    storage.delete(uri)
    count = storage.delete_all_for_patient("PT0001")

GDPR note
---------
``delete_all_for_patient`` is the GDPR Art. 17 photo-deletion hook called by
the GDPR "right to erasure" endpoint in Slice 1. It must remove *every* photo
for a patient in a single atomic sweep.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.core.config import Settings


# ---------------------------------------------------------------------------
# Public Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PhotoStorage(Protocol):
    """Protocol satisfied by every photo-storage backend.

    Implementations must be safe to call from synchronous code (no async
    required for file I/O in the MVP — photos are small and the upload
    endpoint runs on a thread pool anyway).
    """

    def put(self, patient_id: str, filename: str, data: bytes) -> str:
        """Store *data* and return a canonical URI for later retrieval.

        Parameters
        ----------
        patient_id:
            Identifies the owning patient. Used to namespace storage so that
            GDPR deletion can sweep a single prefix.
        filename:
            Original filename supplied by the client (e.g. ``"photo.jpg"``).
            Only the extension is preserved; the stem is replaced with a UUID4.
        data:
            Raw image bytes.

        Returns
        -------
        str
            A URI uniquely identifying the stored object.
            Local backend: ``file:///absolute/path/PT0001/<uuid>.jpg``
            GCS backend:   ``gs://bucket/PT0001/<uuid>.jpg``
        """
        ...

    def get_bytes(self, uri: str) -> bytes:
        """Return the raw bytes for the object identified by *uri*.

        Raises
        ------
        FileNotFoundError
            If no object exists at the given URI.
        """
        ...

    def delete(self, uri: str) -> None:
        """Remove the object identified by *uri*.

        Silently succeeds when the object does not exist (idempotent).
        """
        ...

    def delete_all_for_patient(self, patient_id: str) -> int:
        """Remove every stored object belonging to *patient_id*.

        Parameters
        ----------
        patient_id:
            The patient whose objects should be purged.

        Returns
        -------
        int
            The number of objects deleted (0 when the patient had none).
        """
        ...


# ---------------------------------------------------------------------------
# Local filesystem backend
# ---------------------------------------------------------------------------


class LocalFsPhotoStorage:
    """Stores meal photos under ``<base_dir>/<patient_id>/<uuid><ext>``.

    Designed for local development and unit tests.  No external services or
    credentials are required.

    Parameters
    ----------
    base_dir:
        Root directory for all stored photos.  Created on first write.
        Defaults to ``./var/photos`` when constructed via the factory.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    # ------------------------------------------------------------------
    # PhotoStorage Protocol implementation
    # ------------------------------------------------------------------

    def put(self, patient_id: str, filename: str, data: bytes) -> str:
        """Write *data* to ``<base_dir>/<patient_id>/<uuid><ext>`` and return a ``file://`` URI.

        The path is resolved to an absolute form before constructing the URI so
        that the URI remains valid even if the process CWD changes between
        ``put()`` and a later ``get_bytes()`` / ``delete()`` call.
        """
        ext = Path(filename).suffix  # e.g. ".jpg"
        dest_dir = (self._base_dir / patient_id).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = (dest_dir / f"{uuid.uuid4()}{ext}").resolve()
        dest_path.write_bytes(data)
        return f"file://{dest_path}"

    def get_bytes(self, uri: str) -> bytes:
        """Return bytes stored at the ``file://`` URI.

        Raises
        ------
        FileNotFoundError
            When no file exists at the URI's path.
        """
        file_path = _local_path_from_uri(uri)
        if not file_path.exists():
            raise FileNotFoundError(f"No photo at URI: {uri!r}")
        return file_path.read_bytes()

    def delete(self, uri: str) -> None:
        """Remove the file at *uri*; silently ignores missing files."""
        file_path = _local_path_from_uri(uri)
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass

    def delete_all_for_patient(self, patient_id: str) -> int:
        """Delete every file in ``<base_dir>/<patient_id>/`` and return the count.

        Removes the patient directory itself afterwards if it is empty.
        Returns 0 when the patient has no directory or no files.
        """
        patient_dir = self._base_dir / patient_id
        if not patient_dir.is_dir():
            return 0

        count = 0
        for file_path in list(patient_dir.iterdir()):
            if file_path.is_file():
                file_path.unlink()
                count += 1

        # Clean up the now-empty directory (best-effort)
        try:
            patient_dir.rmdir()
        except OSError:
            pass

        return count


# ---------------------------------------------------------------------------
# GCS backend
# ---------------------------------------------------------------------------


def _get_gcs_client() -> Any:
    """Lazily import and return a ``google.cloud.storage.Client`` instance.

    The import is deferred so that ``photo_storage`` can be imported without
    ``google-cloud-storage`` being installed (e.g. during Wave 1 parallel
    execution when T5's dependency bump may not yet be merged).

    Raises
    ------
    ImportError
        If ``google-cloud-storage`` is not installed.
    """
    from google.cloud import storage as gcs  # type: ignore[import-untyped]

    return gcs.Client()


class GcsPhotoStorage:
    """Stores meal photos in a Google Cloud Storage bucket.

    Objects are stored at ``<bucket>/<patient_id>/<uuid><ext>``.

    The GCS client is constructed lazily on first use so that importing this
    module never triggers a network or credential lookup.

    Parameters
    ----------
    bucket_name:
        Name of the GCS bucket to use (without the ``gs://`` prefix).
    """

    def __init__(self, bucket_name: str) -> None:
        self._bucket_name = bucket_name
        # Lazy — populated on first call to _bucket()
        self._client: Any = None

    def _bucket(self) -> Any:
        """Return (and lazily create) the GCS Bucket object."""
        if self._client is None:
            self._client = _get_gcs_client()
        return self._client.bucket(self._bucket_name)

    def put(self, patient_id: str, filename: str, data: bytes) -> str:
        """Upload *data* to GCS and return a ``gs://`` URI."""
        ext = Path(filename).suffix
        blob_name = f"{patient_id}/{uuid.uuid4()}{ext}"
        blob = self._bucket().blob(blob_name)
        blob.upload_from_string(data)
        return f"gs://{self._bucket_name}/{blob_name}"

    def get_bytes(self, uri: str) -> bytes:
        """Download and return bytes for the object at *uri*.

        Raises
        ------
        FileNotFoundError
            When the blob does not exist.
        """
        blob_name = _gcs_blob_name_from_uri(uri, self._bucket_name)
        blob = self._bucket().blob(blob_name)
        if not blob.exists():
            raise FileNotFoundError(f"No GCS object at URI: {uri!r}")
        result: bytes = blob.download_as_bytes()
        return result

    def delete(self, uri: str) -> None:
        """Delete the GCS object at *uri*; silently ignores missing objects."""
        blob_name = _gcs_blob_name_from_uri(uri, self._bucket_name)
        blob = self._bucket().blob(blob_name)
        try:
            blob.delete()
        except Exception:  # noqa: BLE001
            pass

    def delete_all_for_patient(self, patient_id: str) -> int:
        """Delete every GCS object under the ``<patient_id>/`` prefix.

        Returns
        -------
        int
            Number of objects deleted.
        """
        prefix = f"{patient_id}/"
        blobs = list(self._bucket().list_blobs(prefix=prefix))
        for blob in blobs:
            blob.delete()
        return len(blobs)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_photo_storage(settings: "Settings") -> PhotoStorage:
    """Return the appropriate ``PhotoStorage`` backend based on settings.

    Parameters
    ----------
    settings:
        Application settings.  Reads ``photo_storage_backend``,
        ``photo_local_dir``, and ``photo_gcs_bucket``.

    Returns
    -------
    PhotoStorage
        A ``LocalFsPhotoStorage`` when ``photo_storage_backend == "local"``.
        A ``GcsPhotoStorage`` when ``photo_storage_backend == "gcs"``.

    Raises
    ------
    ValueError
        If ``photo_storage_backend == "gcs"`` but ``photo_gcs_bucket`` is not
        set.
    ImportError
        If ``photo_storage_backend == "gcs"`` but ``google-cloud-storage`` is
        not installed.
    """
    backend = settings.photo_storage_backend

    if backend == "local":
        return LocalFsPhotoStorage(base_dir=settings.photo_local_dir)

    if backend == "gcs":
        bucket = settings.photo_gcs_bucket
        if not bucket:
            raise ValueError(
                "photo_gcs_bucket must be set when photo_storage_backend='gcs'"
            )
        # Probe the import eagerly so that a missing dependency raises a clear
        # ImportError here in the factory, rather than on the first use of
        # _get_gcs_client() deep inside a request handler.
        try:
            from google.cloud import storage as _  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "google-cloud-storage is required for the GCS photo storage backend. "
                "Install it with: uv add google-cloud-storage"
            ) from exc
        return GcsPhotoStorage(bucket_name=bucket)

    raise ValueError(  # pragma: no cover
        f"Unknown photo_storage_backend: {backend!r}. Choose 'local' or 'gcs'."
    )


# ---------------------------------------------------------------------------
# Helpers (module-private)
# ---------------------------------------------------------------------------


def _local_path_from_uri(uri: str) -> Path:
    """Convert a ``file:///absolute/path`` URI to a :class:`pathlib.Path`."""
    if not uri.startswith("file://"):
        raise ValueError(f"Expected file:// URI, got: {uri!r}")
    return Path(uri[len("file://"):])


def _gcs_blob_name_from_uri(uri: str, bucket_name: str) -> str:
    """Extract the blob name from a ``gs://bucket/blob`` URI."""
    prefix = f"gs://{bucket_name}/"
    if not uri.startswith(prefix):
        raise ValueError(
            f"URI {uri!r} does not match bucket {bucket_name!r}"
        )
    return uri[len(prefix):]
