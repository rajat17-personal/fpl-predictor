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
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

import pandas as pd
import requests

import config

SNAP_DIR = config.DATA_DIR / "snapshots"
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}
_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

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
              "price_change_percent", "price_change_hourly_rate"):
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


def take_snapshot(*, force: bool = False) -> "pd.DataFrame | None":
    """Fetch bootstrap-static and persist today's snapshot. None if already done."""
    ts = dt.datetime.now(dt.timezone.utc)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAP_DIR / f"{ts.date().isoformat()}.parquet"
    if out.exists() and not force:
        print(f"[snapshot] {out.name} already exists (use --force to overwrite)")
        return None
    r = requests.get(f"{config.FPL_API}/bootstrap-static/", headers=_HEADERS, timeout=30)
    r.raise_for_status()
    df = snapshot_frame(r.json(), ts)
    df.to_parquet(out, index=False)
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
    args = ap.parse_args(argv)
    take_snapshot(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
