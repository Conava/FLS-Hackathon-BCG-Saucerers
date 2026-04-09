"""Structured JSON logging with request-id injection.

PHI policy: logs MUST NOT contain patient names, dates of birth, or any
personally identifying information. Allowed fields: request_id, route,
method, status, duration_ms, model_name, token_count.

Usage::

    from app.core.logging import configure_logging, get_logger, request_id_var

    configure_logging(log_level="INFO")  # call once at startup
    logger = get_logger(__name__)
    logger.info("request finished", extra={"route": "/healthz", "status": 200})
"""
import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import json as jsonlogger

# -----------------------------------------------------------------------
# Context variable that carries the current request-id across async tasks.
# Set by RequestIdMiddleware; read by RequestIdFilter.
# -----------------------------------------------------------------------
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Injects ``request_id`` from the async context into every log record.

    Attach this filter to any handler that should include ``request_id``
    in its output.  The filter is idempotent — safe to call on the same
    record multiple times.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        """Add ``request_id`` attribute to *record* and return True."""
        record.request_id = request_id_var.get()
        return True


def configure_logging(log_level: str = "INFO") -> None:
    """Configure the root logger with a JSON handler and the RequestIdFilter.

    This function is idempotent by design: it clears existing handlers on
    the root logger before installing the JSON handler, so calling it
    multiple times in tests does not accumulate handlers.

    Args:
        log_level: A standard Python logging level name (DEBUG, INFO, …).
            Defaults to ``"INFO"``.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    # Remove any previously configured handlers to avoid duplicates.
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # JSON format includes the fields allowed by the PHI policy.
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s "
        "%(request_id)s %(route)s %(method)s %(status)s %(duration_ms)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger inheriting the root JSON configuration.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
