"""Fail-loudly alerting for cron and pipeline steps.

`report` is the single call site every cron script and pipeline step uses to
record a failure: one structured log line, one appended JSON Lines record on
disk, and (when configured) one webhook POST. `report` deliberately never
raises — alerting that can fail the pipeline it observes is worse than no
alerting at all, so every failure inside `report` itself is caught, logged,
and swallowed.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

import config
from ops.jsonlog import log_event, redact

_logger = logging.getLogger("ops.notify")


def report(job: str, step: str, message: str, *, level: str = "error", **fields) -> None:
    """Record a cron/pipeline failure (or other notable event).

    Builds one record (ts, job, step, level, message, host, plus any extra
    `fields`), redacts it, logs it as a structured `alert` event, appends it
    as one JSON Lines record to `FPL_ALERT_LOG` (default
    `config.DATA_DIR / "alerts.jsonl"`), and — when `FPL_ALERT_WEBHOOK` is
    set — POSTs it there too. Never raises: this function's entire body is
    guarded so a broken alerting path can never abort the run it observes.
    """
    try:
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "job": job,
            "step": step,
            "level": level,
            "message": message,
            "host": socket.gethostname(),
            **fields,
        }
        record = redact(record)

        # LogRecord reserves the attribute name "message" for its own
        # formatted-message slot, so the record's own "message" field is
        # passed through under "alert_message" for the structured log line
        # only; the on-disk/POSTed record keeps the original "message" key.
        log_fields = {k: v for k, v in record.items() if k != "message"}
        log_event(_logger, "alert", alert_message=record["message"], **log_fields)

        alert_log = Path(os.environ.get("FPL_ALERT_LOG", str(config.DATA_DIR / "alerts.jsonl")))
        alert_log.parent.mkdir(parents=True, exist_ok=True)
        with open(alert_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        webhook = os.environ.get("FPL_ALERT_WEBHOOK")
        if webhook:
            try:
                requests.post(webhook, json=record, timeout=10)
            except Exception as exc:
                log_event(_logger, "alert.webhook_failed", level="warning", error=str(exc))
    except Exception as exc:
        log_event(_logger, "alert.failed", level="error", error=str(exc))
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--step", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--level", default="error")
    args = ap.parse_args(argv)
    report(args.job, args.step, args.message, level=args.level)
    return 0


if __name__ == "__main__":
    sys.exit(main())
