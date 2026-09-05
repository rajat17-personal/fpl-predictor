"""Structured (single-line JSON) logging for long-lived processes.

`configure_logging` installs one JSON-formatting `StreamHandler` on the root
logger, idempotently (a second call replaces the tagged handler rather than
adding a duplicate, so uvicorn reloads and pytest re-imports never multiply
lines). `log_event` is the call-site helper every failure path uses to emit
exactly one structured event. `redact` guarantees no secret value reaches a
log line.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

_HANDLER_ATTR = "_ops_jsonlog_handler"
_REDACT_KEY_MARKERS = ("key", "token", "secret", "password", "authorization", "webhook")

# Standard attributes every stdlib LogRecord carries — anything else on a
# record's __dict__ is a caller-supplied extra field.
_RESERVED_RECORD_ATTRS = set(
    vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()
) | {"message", "asctime"}


def redact(value):
    """Recursively redact secret-shaped data.

    Any dict key that case-insensitively contains "key", "token", "secret",
    "password", "authorization" or "webhook" has its value replaced with the
    literal string "[redacted]". Any string value anywhere in the structure
    that exactly matches one of the comma-separated entries of the
    FPL_API_KEYS environment variable is also replaced, regardless of its key.
    """
    secrets = {k.strip() for k in os.environ.get("FPL_API_KEYS", "").split(",") if k.strip()}
    return _redact(value, secrets)


def _redact(value, secrets: set[str]):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and any(m in k.lower() for m in _REDACT_KEY_MARKERS):
                out[k] = "[redacted]"
            else:
                out[k] = _redact(v, secrets)
        return out
    if isinstance(value, list):
        return [_redact(v, secrets) for v in value]
    if isinstance(value, str) and secrets and value in secrets:
        return "[redacted]"
    return value


class JsonFormatter(logging.Formatter):
    """Emits exactly one `json.dumps` object per record."""

    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        extra = {k: v for k, v in record.__dict__.items() if k not in _RESERVED_RECORD_ATTRS}
        event = extra.pop("event", None) or record.name
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "service": self.service,
            "event": event,
            "msg": record.getMessage(),
        }
        payload.update(extra)
        return json.dumps(redact(payload), default=str)


def configure_logging(service: str, *, level: int = logging.INFO, stream=None) -> logging.Logger:
    """Install a JSON-formatting StreamHandler on the root logger.

    Idempotent: a second call in the same process replaces the previously
    installed handler rather than appending a second one.
    """
    root = logging.getLogger()
    root.setLevel(level)
    existing = getattr(root, _HANDLER_ATTR, None)
    if existing is not None and existing in root.handlers:
        root.removeHandler(existing)
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonFormatter(service))
    root.addHandler(handler)
    setattr(root, _HANDLER_ATTR, handler)
    return root


def log_event(logger: logging.Logger, event: str, *, level: str = "info", **fields) -> None:
    """Log one structured event with `event` plus any extra `fields`."""
    lvl = getattr(logging, level.upper(), logging.INFO)
    logger.log(lvl, event, extra={"event": event, **fields})
