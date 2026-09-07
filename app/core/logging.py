"""System Design Interview Simulator - Structured Logging Infrastructure.

Provides contextual structured logging with correlation ID and interview session ID
propagation across asynchronous request lifecycles and background worker tasks.
"""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Context variables for distributed request and session tracing
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
session_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None
)


def get_correlation_id() -> str | None:
    """Retrieve the current request correlation ID from context."""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: str | None) -> None:
    """Bind a correlation ID to the current asynchronous context."""
    correlation_id_ctx.set(correlation_id)


def get_session_id() -> str | None:
    """Retrieve the current interview session ID from context."""
    return session_id_ctx.get()


def set_session_id(session_id: str | None) -> None:
    """Bind an interview session ID to the current asynchronous context."""
    session_id_ctx.set(session_id)


class ContextFilter(logging.Filter):
    """Injects contextual metadata (correlation_id, session_id) into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"  # type: ignore[attr-defined]
        record.session_id = get_session_id() or "-"  # type: ignore[attr-defined]
        return True


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects for production log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
            "session_id": getattr(record, "session_id", "-"),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, default=str)


class ConsoleFormatter(logging.Formatter):
    """Formatted human-readable console output for local development."""

    COLOR_CODES = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET_CODE = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLOR_CODES.get(record.levelname, self.RESET_CODE)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        corr = getattr(record, "correlation_id", "-")
        sess = getattr(record, "session_id", "-")
        context_str = f"[corr={corr} sess={sess}]" if corr != "-" or sess != "-" else ""

        formatted_msg = (
            f"{color}[{timestamp}] [{record.levelname:<8}]{self.RESET_CODE} "
            f"[{record.name}] {context_str} {record.getMessage()}"
        )
        if record.exc_info:
            formatted_msg += f"\n{self.formatException(record.exc_info)}"
        return formatted_msg


def setup_logging(is_production: bool = False, debug: bool = False) -> None:
    """Configure root logger, handler, and formatting based on environment flags."""
    log_level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.addFilter(ContextFilter())

    if is_production:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """Factory function for retrieving named application loggers."""
    return logging.getLogger(name or "system_design_interviewer")
