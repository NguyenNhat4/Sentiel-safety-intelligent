"""Privacy-safe operational metrics writer backed by a rotated JSONL file."""

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOGGER_NAME = "backend.operational_metrics"
_HANDLER_MARKER = "_is_operational_metrics_handler"
_ALLOWED_FIELDS = {"method", "route", "status_class", "duration_ms", "outcome", "error_kind"}
_EVENT_TYPES = {
    "http_request_completed",
    "websocket_connection_opened",
    "websocket_connection_closed",
    "inference_completed",
    "inference_failed",
    "privacy_redaction_completed",
}


class OperationalMetricsFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(record.operational_event, separators=(",", ":"), ensure_ascii=False)


def configure_operational_metrics_logger(log_path: str | Path, *, max_bytes: int, backup_count: int) -> logging.Logger:
    """Configure exactly one dedicated JSONL handler for this process."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers:
        if getattr(handler, _HANDLER_MARKER, False) and Path(handler.baseFilename) == path.resolve():
            return logger
        if getattr(handler, _HANDLER_MARKER, False):
            logger.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    setattr(handler, _HANDLER_MARKER, True)
    handler.setFormatter(OperationalMetricsFormatter())
    logger.addHandler(handler)
    return logger


def record_operational_event(event_type: str, **fields: Any) -> None:
    """Append a finite, allowlisted event. Unknown fields are intentionally discarded."""
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"Unsupported operational metrics event type: {event_type}")
    event = {
        "schema_version": 1,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
    }
    event.update({key: value for key, value in fields.items() if key in _ALLOWED_FIELDS and value is not None})
    logging.getLogger(LOGGER_NAME).info("operational_metric", extra={"operational_event": event})
