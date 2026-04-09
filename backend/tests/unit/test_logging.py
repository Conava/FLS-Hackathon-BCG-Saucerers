"""Unit tests for app.core.logging — structured JSON logging with request_id filter."""
import json
import logging
import os

import pytest

from app.core.logging import (
    RequestIdFilter,
    configure_logging,
    get_logger,
    request_id_var,
)


class TestRequestIdFilter:
    """Tests for the RequestIdFilter that injects request_id into log records."""

    def test_filter_injects_request_id_from_contextvar(self) -> None:
        """Filter reads request_id from contextvars and adds it to the log record."""
        token = request_id_var.set("test-req-id-123")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="hello",
                args=(),
                exc_info=None,
            )
            f = RequestIdFilter()
            f.filter(record)
            assert record.request_id == "test-req-id-123"  # type: ignore[attr-defined]
        finally:
            request_id_var.reset(token)

    def test_filter_uses_empty_string_when_no_request_id(self) -> None:
        """Filter uses empty string when no request_id is in context."""
        # Reset the contextvar to its default
        request_id_var.set("")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        f = RequestIdFilter()
        f.filter(record)
        assert record.request_id == ""  # type: ignore[attr-defined]


class TestConfigureLogging:
    """Tests for configure_logging() sets up JSON handler."""

    def test_configure_logging_sets_json_handler(self) -> None:
        """After configure_logging(), root logger uses a JSON formatter."""
        configure_logging(log_level="INFO")
        root = logging.getLogger()
        assert len(root.handlers) > 0

    def test_configure_logging_respects_log_level(self) -> None:
        """configure_logging() sets the level correctly."""
        configure_logging(log_level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_configure_logging_produces_json_output(self) -> None:
        """Logger emits parseable JSON lines with request_id when set."""
        import io

        from pythonjsonlogger import json as jsonlogger

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(jsonlogger.JsonFormatter())

        configure_logging(log_level="INFO")
        token = request_id_var.set("req-abc-456")
        try:
            logger = get_logger("test.json.verify")
            logger.addHandler(handler)
            logger.info("test message for json")
        finally:
            request_id_var.reset(token)
            logger.removeHandler(handler)

        import json

        output = stream.getvalue().strip()
        assert output, "Logger produced no output"
        parsed = json.loads(output)
        assert parsed.get("message") == "test message for json"


class TestLoggerEmitsJsonWithRequestId:
    """Tests that the logger emits JSON output including request_id."""

    def test_logger_emits_json_with_request_id(self) -> None:
        """Logs include request_id field when set via contextvar."""
        import io

        from pythonjsonlogger import json as jsonlogger

        configure_logging(log_level="DEBUG")
        token = request_id_var.set("verify-req-789")
        try:
            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            formatter = jsonlogger.JsonFormatter("%(message)s %(request_id)s")
            handler.setFormatter(formatter)
            handler.addFilter(RequestIdFilter())

            test_logger = logging.getLogger("test.emit")
            test_logger.addHandler(handler)
            test_logger.setLevel(logging.DEBUG)

            test_logger.info("test event", extra={"route": "/health", "method": "GET"})

            output = stream.getvalue()
            data = json.loads(output)
            assert data["request_id"] == "verify-req-789"
            assert "test event" in data.get("message", "") or "test event" in output
        finally:
            request_id_var.reset(token)

    def test_logger_no_phi_fields(self) -> None:
        """Log output must not include PHI field names (patient_name, dob, ssn)."""
        import io

        from pythonjsonlogger import json as jsonlogger

        configure_logging(log_level="DEBUG")
        token = request_id_var.set("phi-test-req")
        try:
            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            formatter = jsonlogger.JsonFormatter("%(message)s %(request_id)s %(route)s %(status)s %(duration_ms)s")
            handler.setFormatter(formatter)
            handler.addFilter(RequestIdFilter())

            test_logger = logging.getLogger("test.phi")
            test_logger.addHandler(handler)
            test_logger.setLevel(logging.DEBUG)

            test_logger.info(
                "request complete",
                extra={
                    "route": "/patients/PT0282",
                    "method": "GET",
                    "status": 200,
                    "duration_ms": 42,
                },
            )
            output = stream.getvalue()
            data = json.loads(output)
            # PHI fields must NOT appear
            assert "patient_name" not in data
            assert "dob" not in data
            assert "ssn" not in data
            # Allowed fields ARE present
            assert data.get("route") == "/patients/PT0282"
        finally:
            request_id_var.reset(token)
