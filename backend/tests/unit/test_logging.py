"""Unit tests for structured logging and correlation ID tracing."""

import json
import logging

import pytest

from app.core.logging import (
    DevelopmentLogFormatter,
    JSONLogFormatter,
    get_correlation_id,
    set_correlation_id,
)


@pytest.mark.unit
def test_correlation_id_context() -> None:
    """Verify setting and retrieving correlation ID."""
    set_correlation_id("test-corr-1234")
    assert get_correlation_id() == "test-corr-1234"


@pytest.mark.unit
def test_json_formatter() -> None:
    """Verify machine-readable JSON log formatter output."""
    formatter = JSONLogFormatter(environment="test")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test structured log message",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-xyz-999"  # type: ignore[attr-defined]

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test structured log message"
    assert parsed["environment"] == "test"
    assert parsed["correlation_id"] == "corr-xyz-999"
    assert "timestamp" in parsed


@pytest.mark.unit
def test_development_formatter() -> None:
    """Verify human-readable development log formatter."""
    formatter = DevelopmentLogFormatter()
    record = logging.LogRecord(
        name="dev_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=20,
        msg="Warning message",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-dev-123"  # type: ignore[attr-defined]

    output = formatter.format(record)
    assert "[WARNING ]" in output
    assert "[dev_logger]" in output
    assert "corr_id=corr-dev-123" in output
    assert "Warning message" in output
