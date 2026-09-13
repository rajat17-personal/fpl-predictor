"""Backfill missing daily FPL bootstrap snapshots from the Wayback Machine.

WSL cron only fires while the machine is actually running (see
scripts/snapshot_catchup.sh); nine days between 2026-08-31 and 2026-09-13 were
silently skipped. The price-change model (models/price.py) learns from
day-over-day deltas the live FPL API never serves historically, so a missed
day is training data lost -- unless a capture of `bootstrap-static` survives
somewhere else. The Internet Archive's Wayback Machine crawls the endpoint and
holds at least one status-200 capture on every day this tool has been asked to
recover, so this module discovers a capture for each missing day, replays it
through the exact same `snapshot_frame()` normalization `data/snapshot.py`
uses for a live cron run, and writes it into the same `data/snapshots/`
archive -- schema-identical to a cron-captured file, distinguishable only by
parquet key-value metadata (`fpl_snapshot_source=wayback`).

This module never modifies `data/snapshot.py`: it imports `snapshot_frame`
and `SNAP_DIR` from it so the slim-column schema exists in exactly one place.

Run:
  python -m data.backfill_snapshot --days 2026-09-10    # backfill one or more explicit days
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import sys
import time

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from data.snapshot import SNAP_DIR, snapshot_frame

_CDX = "https://web.archive.org/cdx/search/cdx"
_WAYBACK = "https://web.archive.org/web/{ts}id_/https://fantasy.premierleague.com/api/bootstrap-static/"
_TARGET_URL = "fantasy.premierleague.com/api/bootstrap-static*"
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}
_TIMEOUT = 60
_TARGET_MIN = 150  # 02:30 UTC, matching the daily cron's capture minute
_JOB = "backfill"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _get(url: str, params: dict | None = None, *, retries: int = 5, backoff: float = 10.0) -> requests.Response:
    """One shared archive.org GET honouring rate limits.

    Retries on a retryable 429/5xx status with a `Retry-After`-aware sleep
    (falling back to exponential backoff + jitter). A non-retryable 4xx
    raises immediately. Exhausting retries re-raises the last exception so
    the caller's exit code is non-zero.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
            if r.status_code in _RETRYABLE_STATUS:
                raise requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            last_exc = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            is_last = attempt == retries
            non_retryable_4xx = status is not None and status not in _RETRYABLE_STATUS and 400 <= status < 500
            if non_retryable_4xx:
                raise
            if is_last:
                raise
            sleep_s = backoff * 2 ** (attempt - 1) + random.random()
            resp = getattr(exc, "response", None)
            retry_after = resp.headers.get("Retry-After") if resp is not None else None
            if retry_after:
                try:
                    sleep_s = float(retry_after)
                except ValueError:
                    pass
            print(f"[backfill] attempt {attempt}/{retries} failed ({exc}) -- retrying in {sleep_s:.1f}s")
            time.sleep(sleep_s)
    raise last_exc if last_exc is not None else RuntimeError("archive.org fetch failed")


def cdx_captures(day: dt.date) -> list[str]:
    """Status-200 capture timestamps (`YYYYMMDDhhmmss`) of bootstrap-static for `day`."""
    ymd = day.strftime("%Y%m%d")
    resp = _get(_CDX, params={
        "url": _TARGET_URL,
        "from": ymd,
        "to": ymd,
        "output": "text",
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
    })
    out = []
    for line in resp.text.splitlines():
        parts = line.split()
        if parts and len(parts[0]) == 14 and parts[0].isdigit():
            out.append(parts[0])
    return sorted(out)


def pick_capture(timestamps: list[str], target_min: int = _TARGET_MIN) -> list[str]:
    """Order `timestamps` by closeness to `target_min` minutes past midnight UTC.

    Pure, no I/O. Ties broken by earlier timestamp. Returns the full ordered
    list (best first) so a caller can fall through to the next-best capture
    when the best one fails to parse as bootstrap JSON.
    """
    def _key(ts: str) -> tuple[int, str]:
        hh, mm = int(ts[8:10]), int(ts[10:12])
        minutes = hh * 60 + mm
        return (abs(minutes - target_min), ts)

    return sorted(timestamps, key=_key)


def fetch_capture(timestamp: str) -> dict:
    """Fetch and validate one Wayback capture's bootstrap-static JSON."""
    resp = _get(_WAYBACK.format(ts=timestamp))
    try:
        boot = resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"capture {timestamp}: not valid JSON ({exc})") from exc
    if not boot.get("elements") or not boot.get("events"):
        raise ValueError(f"capture {timestamp}: missing/empty 'elements' or 'events'")
    return boot


def _ts_to_datetime(timestamp: str) -> dt.datetime:
    return dt.datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)


def backfill_day(day: dt.date, *, max_candidates: int = 3) -> bool:
    """Backfill one UTC day from its best available Wayback capture.

    Returns False (no-op, printed as a skip) when the day's parquet already
    exists -- idempotent per day, no --force in v1. Returns True on a
    successful write. Raises if every candidate capture fails or none exist.
    """
    out = SNAP_DIR / f"{day.isoformat()}.parquet"
    if out.exists():
        print(f"[backfill] {out.name} already exists -- skipping")
        return False

    timestamps = cdx_captures(day)
    if not timestamps:
        raise RuntimeError(f"{day.isoformat()}: no Wayback capture available")

    candidates = pick_capture(timestamps)[:max_candidates]
    last_exc: Exception | None = None
    for timestamp in candidates:
        try:
            boot = fetch_capture(timestamp)
        except (ValueError, requests.RequestException) as exc:
            print(f"[backfill] {day.isoformat()}: candidate {timestamp} failed ({exc}) -- trying next")
            last_exc = exc
            continue

        ts = _ts_to_datetime(timestamp)
        df = snapshot_frame(boot, ts)
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
        try:
            table = pa.Table.from_pandas(df, preserve_index=False)
            meta = dict(table.schema.metadata or {})
            meta[b"fpl_snapshot_source"] = b"wayback"
            meta[b"fpl_wayback_timestamp"] = timestamp.encode()
            table = table.replace_schema_metadata(meta)
            pq.write_table(table, tmp)
            os.replace(tmp, out)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise
        print(f"[backfill] {out.name}: {len(df)} players, next GW {df.next_gw.iloc[0]}, capture {timestamp}")
        return True

    raise RuntimeError(f"{day.isoformat()}: all {len(candidates)} candidate captures failed") from last_exc


def parse_days(spec: str) -> list[dt.date]:
    """Parse a comma-separated list of ISO dates. Raises SystemExit naming the bad token."""
    days = []
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            days.append(dt.date.fromisoformat(token))
        except ValueError:
            raise SystemExit(f"backfill_snapshot: invalid date '{token}' in --days (expected YYYY-MM-DD)")
    return days


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=str, default=None,
                     help="comma-separated list of ISO dates to backfill")
    ap.add_argument("--sleep", type=float, default=6.0,
                     help="seconds to sleep between days that hit the network (default: 6.0)")
    ap.add_argument("--max-candidates", type=int, default=3,
                     help="candidate captures to try per day before giving up (default: 3)")
    args = ap.parse_args(argv)

    days = parse_days(args.days) if args.days else []
    if not days:
        print("[backfill] no days requested -- pass --days")
        return 0

    written = skipped = failed = 0
    for i, day in enumerate(days):
        if i > 0:
            time.sleep(args.sleep)
        try:
            if backfill_day(day, max_candidates=args.max_candidates):
                written += 1
            else:
                skipped += 1
        except (RuntimeError, requests.RequestException) as exc:
            print(f"[backfill] {day.isoformat()}: FAILED ({exc})")
            failed += 1

    print(f"[backfill] done: {written} written, {skipped} skipped (already present), {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
