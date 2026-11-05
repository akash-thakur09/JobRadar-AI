"""Structured logging configuration with correlation ID tracing."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable for request correlation tracing
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")


def get_correlation_id() -> str:
    """Return the current context correlation ID."""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the context correlation ID."""
    correlation_id_ctx.set(correlation_id)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that injects correlation_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JSONLogFormatter(logging.Formatter):
    """Machine-readable JSON log formatter for structured logging."""

    def __init__(self, environment: str = "development") -> None:
        super().__init__()
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": self.environment,
            "correlation_id": getattr(record, "correlation_id", "system"),
        }

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


class DevelopmentLogFormatter(logging.Formatter):
    """Human-readable console formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        correlation_id = getattr(record, "correlation_id", "system")
        base = f"[{timestamp}] [{record.levelname:<8}] [{record.name}] [corr_id={correlation_id}] {record.getMessage()}"
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(
    log_level: str = "INFO", is_production: bool = False, environment: str = "development"
) -> None:
    """Configure the root logger with appropriate formatters and filters."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to prevent duplicate logs
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.addFilter(CorrelationIdFilter())

    if is_production:
        console_handler.setFormatter(JSONLogFormatter(environment=environment))
    else:
        console_handler.setFormatter(DevelopmentLogFormatter())

    root_logger.addHandler(console_handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
