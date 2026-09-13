"""Current-season per-GW history from the FPL API -> live rolling-form features.

Fixes the train/serve skew where live predictions ran with NaN rolling features:
`element-summary/{id}/` returns each player's completed gameweeks this season, and
from those we compute "form as of now" — the same rolling stats the model was
trained on. No shift is needed here: for an UPCOMING fixture every completed match
is prior information, so tail(w).mean() over completed matches is leakage-free.

Two-step:
  python -m data.live_history            # fetch + cache (one API call per player)
  predict.live merges `current_form()` automatically when the cache exists.

Early season the history is short (or empty preseason) — features degrade
gracefully to NaN exactly as in training cold-start rows.
"""
from __future__ import annotations

import argparse
import sys
import time

import pandas as pd
import requests

import config
from features.engineer import ROLL_STATS
from ops.jsonio import read_json

_CACHE = config.RAW_DIR / "live" / "element_history.parquet"
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}

# element-summary field -> our canonical stat name (ROLL_STATS vocabulary).
_FIELD_MAP = {
    "minutes": "minutes", "starts": "starts", "total_points": "total_points",
    "goals_scored": "goals_scored", "assists": "assists",
    "clean_sheets": "clean_sheets", "goals_conceded": "goals_conceded",
    "saves": "saves", "bonus": "bonus", "bps": "bps",
    "expected_goals": "xg", "expected_assists": "xa",
    "expected_goal_involvements": "xgi", "expected_goals_conceded": "xgc",
    "influence": "influence", "creativity": "creativity", "threat": "threat",
    "ict_index": "ict_index",
}


def fetch(force: bool = False, sleep: float = 0.08) -> pd.DataFrame:
    """Download every player's current-season history and cache it."""
    boot_path = config.RAW_DIR / "live" / "bootstrap-static.json"
    boot = read_json(boot_path, what="FPL bootstrap-static payload (live history)",
                      remedy="python -m data.ingest")
    ids = [el["id"] for el in boot["elements"]]
    if _CACHE.exists() and not force:
        return pd.read_parquet(_CACHE)

    rows = []
    for i, pid in enumerate(ids):
        try:
            r = requests.get(f"{config.FPL_API}/element-summary/{pid}/",
                             headers=_HEADERS, timeout=20)
            r.raise_for_status()
            hist = r.json().get("history", [])
        except requests.RequestException as exc:
            print(f"  [warn] element {pid}: {exc}")
            continue
        for h in hist:
            row = {"player_id": pid, "gw": h.get("round"),
                   "kickoff_time": h.get("kickoff_time")}
            row.update({dst: h.get(src) for src, dst in _FIELD_MAP.items()})
            rows.append(row)
        if i % 100 == 0:
            print(f"  fetched {i}/{len(ids)} players ({len(rows)} match rows)")
        time.sleep(sleep)

    df = pd.DataFrame(rows)
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_CACHE, index=False)
    print(f"cached {len(df):,} match rows for {len(ids)} players -> "
          f"{_CACHE.relative_to(config.ROOT)}")
    return df


def current_form(hist: pd.DataFrame | None = None) -> pd.DataFrame | None:
    """Rolling-form features 'as of now' per player_id, matching training names.

    Returns None when no history exists yet (preseason) so callers can no-op.
    """
    if hist is None:
        if not _CACHE.exists():
            return None
        hist = pd.read_parquet(_CACHE)
    if hist.empty:
        return None
    hist = hist.copy()
    # The API pre-creates upcoming-fixture rows with zeros; counting those as real
    # 0-minute appearances would poison early-season form. Only kicked-off games.
    ko = pd.to_datetime(hist["kickoff_time"], utc=True, errors="coerce")
    hist = hist[ko < pd.Timestamp.now(tz="UTC")]
    if hist.empty:
        return None
    for c in set(_FIELD_MAP.values()) & set(hist.columns):
        hist[c] = pd.to_numeric(hist[c], errors="coerce")
    hist = hist.sort_values(["player_id", "kickoff_time"])
    g = hist.groupby("player_id")

    feats = {}
    for stat in ROLL_STATS:
        if stat not in hist.columns:          # e.g. xp_fpl: not in the live API
            continue
        for w in config.WINDOWS:
            name = f"{stat}_r{w}"
            feats[name] = (g[stat].apply(lambda s: s.mean()) if w == "all"
                           else g[stat].apply(lambda s: s.tail(w).mean()))
    feats["points_std_r5"] = g["total_points"].apply(
        lambda s: s.tail(5).std() if len(s) >= 2 else float("nan"))
    feats["apps_prior"] = g.size().astype(float)
    return pd.DataFrame(feats).reset_index()   # player_id as a column for merging


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download history")
    args = ap.parse_args(argv)
    df = fetch(force=args.force)
    form = current_form(df if len(df) else None)
    if form is None:
        print("no completed gameweeks yet (preseason) — live runner stays on priors")
    else:
        print(f"form features for {len(form):,} players, "
              f"{form.shape[1]} columns (median apps: {form.apps_prior.median():.0f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
