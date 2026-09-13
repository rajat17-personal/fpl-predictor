"""Daily FPL bootstrap snapshot (price-model training data + scoreboard inputs).

The price-change model (models/price.py) learns from day-over-day deltas in
transfer momentum and ownership — history the FPL API does not serve, so it must
be collected as it happens. Every day not collected is training data lost;
run this on a daily cron from day one (see scripts/daily.sh).

One slim parquet per UTC day in data/snapshots/. Re-running on the same day is a
no-op unless --force (the API updates continuously; one stable daily point beats
a random intraday mix).

Run:
  python -m data.snapshot            # write today's snapshot if missing
  python -m data.snapshot --force    # overwrite today's
  python -m data.snapshot --retries 5 --backoff 3   # tune outage tolerance
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import sys
import time

import pandas as pd
import requests

import config
from ops.notify import report

SNAP_DIR = config.DATA_DIR / "snapshots"
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}
_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
_JOB = "snapshot"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Everything the price model or scoreboard could plausibly want, kept slim.
# ep_next is FPL's own expected points — captured now so the scoreboard can
# compare "us vs FPL" for gameweeks that hadn't started yet at snapshot time.
_ELEMENT_COLS = [
    "id", "code", "web_name", "team", "element_type", "status",
    "chance_of_playing_next_round", "now_cost", "cost_change_event",
    "cost_change_start", "selected_by_percent", "transfers_in_event",
    "transfers_out_event", "ep_next", "ep_this", "event_points",
    "form", "total_points", "minutes",
    # Official price-change predictor (new in 2026/27): progress % toward the
    # next change, momentum, and per-player locks — ground truth for the watch.
    "price_change_percent", "price_change_hourly_rate",
    "price_change_locked_until", "price_change_calibrating",
    # Phase 10 (data/availability.py): the P(play) stage has never seen these
    # three. The FPL API exposes only CURRENT state, never history -- a day
    # not captured is a day permanently lost, the same argument the price
    # snapshot already rests on, so capture starts accruing them from today
    # rather than waiting for the first plan that consumes them.
    # chance_of_playing_this_round is numerically coerced below, like its
    # next_round sibling; news/news_added stay as captured strings --
    # news_added is an ISO timestamp string, parsed downstream, not at capture.
    "chance_of_playing_this_round", "news", "news_added",
]


def _next_gw(boot: dict) -> int | None:
    for e in boot["events"]:
        if e.get("is_next"):
            return e["id"]
    unfinished = [e["id"] for e in boot["events"] if not e["finished"]]
    return unfinished[0] if unfinished else None


def snapshot_frame(boot: dict, ts: dt.datetime) -> pd.DataFrame:
    """Flatten bootstrap-static into one row per player."""
    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    df = pd.DataFrame([{c: el.get(c) for c in _ELEMENT_COLS} for el in boot["elements"]])
    df = df.rename(columns={"id": "player_id", "code": "player_code",
                            "team": "team_id", "web_name": "name"})
    df["team"] = df.team_id.map(teams)
    df["position"] = df.element_type.map(_POS)
    df = df.drop(columns=["element_type"])
    for c in ("selected_by_percent", "ep_next", "ep_this", "form",
              "price_change_percent", "price_change_hourly_rate",
              "chance_of_playing_this_round"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # First projection step (tonight's update): FPL's own projected % and its
    # -5..+5 likelihood band.
    proj = [next((p for p in (el.get("price_change_projections") or [])
                  if p.get("offset") == 0), {}) for el in boot["elements"]]
    df["proj0_percent"] = pd.to_numeric(
        pd.Series([p.get("projected_percent") for p in proj]), errors="coerce")
    df["proj0_likelihood"] = pd.to_numeric(
        pd.Series([p.get("likelihood") for p in proj]), errors="coerce")
    df["price_m"] = df.now_cost / 10.0
    df["date"] = ts.date().isoformat()
    df["ts_utc"] = ts.isoformat(timespec="seconds")
    df["next_gw"] = _next_gw(boot)
    df["total_players"] = boot.get("total_players")
    return df


def _fetch_bootstrap(*, retries: int, backoff: float) -> dict:
    """GET bootstrap-static with bounded retry + exponential backoff + jitter.

    Retries on a transport-level `requests.RequestException` or a retryable
    5xx/429 status. A non-retryable 4xx is not retried (a client error will
    not fix itself) and raises immediately on the first attempt. After the
    final failed attempt, reports the failure and re-raises so the caller's
    exit code is non-zero.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(f"{config.FPL_API}/bootstrap-static/", headers=_HEADERS, timeout=30)
            if r.status_code in _RETRYABLE_STATUS:
                raise requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            last_exc = exc
            is_last = attempt == retries
            reason = str(exc)
            if is_last:
                report(_JOB, "fetch", f"bootstrap-static fetch failed after {attempt} attempt(s): {reason}")
                raise
            # Non-retryable 4xx (other than the retryable set above) should
            # not be retried — a client error will not fix itself.
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in _RETRYABLE_STATUS and 400 <= status < 500:
                report(_JOB, "fetch", f"bootstrap-static fetch failed (non-retryable {status}): {reason}")
                raise
            sleep_s = backoff ** (attempt - 1) + random.random()
            print(f"[snapshot] attempt {attempt}/{retries} failed ({reason}) — retrying in {sleep_s:.1f}s")
            time.sleep(sleep_s)
    # Unreachable in practice (loop always returns or raises), but keeps mypy/lint happy.
    raise last_exc if last_exc is not None else RuntimeError("bootstrap-static fetch failed")


def take_snapshot(*, force: bool = False, retries: int = 3, backoff: float = 2.0) -> "pd.DataFrame | None":
    """Fetch bootstrap-static and persist today's snapshot. None if already done."""
    ts = dt.datetime.now(dt.timezone.utc)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAP_DIR / f"{ts.date().isoformat()}.parquet"
    if out.exists() and not force:
        print(f"[snapshot] {out.name} already exists (use --force to overwrite)")
        return None
    boot = _fetch_bootstrap(retries=retries, backoff=backoff)
    df = snapshot_frame(boot, ts)
    tmp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
    try:
        df.to_parquet(tmp, index=False)
        os.replace(tmp, out)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    print(f"[snapshot] {out.name}: {len(df)} players, next GW {df.next_gw.iloc[0]}")
    return df


def load_snapshots() -> pd.DataFrame:
    """All snapshots concatenated, sorted by (player_id, date). Empty if none."""
    files = sorted(SNAP_DIR.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    return (pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
            .sort_values(["player_id", "date"]).reset_index(drop=True))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retries", type=int, default=3,
                     help="max fetch attempts before giving up (default: 3)")
    ap.add_argument("--backoff", type=float, default=2.0,
                     help="exponential backoff base in seconds (default: 2.0)")
    args = ap.parse_args(argv)
    take_snapshot(force=args.force, retries=args.retries, backoff=args.backoff)
    return 0


if __name__ == "__main__":
    sys.exit(main())
