"""Structured logging setup for ARIADNE.

Provides a ``logger`` factory that emits JSON lines in production and
human-readable lines during local development. Each record carries the
application name and environment so logs are greppable across services.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

from ariadne.config import get_settings


class JsonFormatter(logging.Formatter):
    """Serialize log records to a single line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


class ExtraFilter(logging.Filter):
    """Move ``extra=...`` kwargs passed to ``logger.info`` into the record."""

    def filter(self, record: logging.LogRecord) -> bool:
        extra = getattr(record, "extra_fields", None)
        if extra is None:
            return True
        # A dict nested under a single keyword argument.
        for value in record.args:
            if isinstance(value, dict):
                record.extra_fields = value
                break
        return True


def _build_handler(environment: str) -> logging.Handler:
    stream = logging.StreamHandler(sys.stdout)
    if environment == "development":
        stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s | %(message)s"))
    else:
        stream.setFormatter(JsonFormatter())
    stream.addFilter(ExtraFilter())
    return stream


def configure_logging() -> None:
    """Configure root logging based on application settings."""
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    if not root.handlers:
        root.addHandler(_build_handler(settings.environment))


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger bound to the calling module name."""
    settings = get_settings()
    logger = logging.getLogger(f"ariadne.{name}")
    logger.setLevel(settings.log_level.upper())
    return logger
