"""Fail-loudly JSON file I/O: context-manager reads/writes with actionable errors.

`read_json` never leaves a descriptor open (even on a raise) and never converts a
missing/corrupt file into an empty default — it re-raises `PayloadError` with a
one-line, actionable message. `write_json` writes to a sibling temp file and
`os.replace`s it into place, so a crash mid-write leaves the previous file whole
and two concurrent writers can never interleave a truncated result.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class PayloadError(RuntimeError):
    """Raised when a JSON payload cannot be read, parsed, or is otherwise unusable."""


def read_json(path: Path, *, what: str, remedy: str | None = None):
    """Read and parse a JSON file, wrapping any failure in `PayloadError`.

    `what` is a human label for the payload (e.g. "FPL bootstrap-static payload").
    `remedy` is an optional command/description telling the operator how to fix it.
    """
    path = Path(path)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise PayloadError(_message(what, path, "file not found", remedy)) from exc
    except json.JSONDecodeError as exc:
        cause = f"{exc.msg} (line {exc.lineno}, column {exc.colno})"
        raise PayloadError(_message(what, path, cause, remedy)) from exc
    except (PermissionError, IsADirectoryError) as exc:
        raise PayloadError(_message(what, path, str(exc), remedy)) from exc


def _message(what: str, path: Path, cause: str, remedy: str | None) -> str:
    parts = [what, str(path.resolve()), cause]
    if remedy:
        parts.append(remedy)
    return ": ".join(parts)


def write_json(obj, path: Path, *, indent: int | None = None) -> None:
    """Write `obj` as JSON to `path` atomically: write to a sibling temp file,
    then `os.replace` it into place. On any failure the temp file is removed
    and the original exception re-raised.
    """
    path = Path(path)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, delete=False, suffix=".tmp", encoding="utf-8"
    )
    try:
        with tmp:
            json.dump(obj, tmp, indent=indent)
        os.replace(tmp.name, path)
    except Exception:
        try:
            os.remove(tmp.name)
        except OSError:
            pass
        raise
