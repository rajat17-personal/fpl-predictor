"""Stable player identity mapping across seasons and the live FPL API.

Problem: the FPL `element`/`id` is reassigned every season (id=19 is Saka one
season, someone else the next), so it cannot link a player across seasons or to
live data. The FPL `code` IS stable and global (Saka is always 223340).

This module builds a lookup:  (season, element) -> player_code (+ names, position)
from each season's cached players_raw.csv, plus the live bootstrap for the
current season. Everything else joins on `player_code` for cross-season identity.

Run:
  python -m data.id_map          # (re)build data/processed/id_map.parquet
"""
from __future__ import annotations

import sys

import pandas as pd

import config
from ops.jsonio import read_json

_OUT = config.PROCESSED_DIR / "id_map.parquet"
_COLS = ["season", "player_id", "player_code", "web_name",
         "first_name", "second_name", "element_type"] + config.SET_PIECE_COLS
_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def _finalise(df: pd.DataFrame, season: str) -> pd.DataFrame:
    df = df.rename(columns={"id": "player_id", "code": "player_code"})
    for c in config.SET_PIECE_COLS:          # absent in pre-2022 snapshots
        if c not in df.columns:
            df[c] = pd.NA
    df.insert(0, "season", season)
    return df[_COLS]


def _from_players_raw(season: str) -> pd.DataFrame | None:
    path = config.RAW_DIR / season / "players_raw.csv"
    if not path.exists():
        return None
    avail = pd.read_csv(path, nrows=0).columns
    base = ["id", "code", "web_name", "first_name", "second_name", "element_type"]
    use = base + [c for c in config.SET_PIECE_COLS if c in avail]
    return _finalise(pd.read_csv(path, usecols=use), season)


def _from_live_bootstrap(season: str) -> pd.DataFrame | None:
    """Fallback for a season with no players_raw.csv yet (e.g. current season)."""
    path = config.RAW_DIR / "live" / "bootstrap-static.json"
    if not path.exists():
        return None
    boot = read_json(path, what="FPL bootstrap-static payload (id map)",
                      remedy="python -m data.ingest")
    df = pd.DataFrame(boot["elements"])
    keep = ["id", "code", "web_name", "first_name", "second_name", "element_type"]
    keep += [c for c in config.SET_PIECE_COLS if c in df.columns]
    return _finalise(df[keep], season)


def build() -> pd.DataFrame:
    frames = []
    for season in config.SEASONS:
        df = _from_players_raw(season)
        src = "players_raw"
        if df is None and season == config.CURRENT_SEASON:
            df = _from_live_bootstrap(season)
            src = "live bootstrap"
        if df is None:
            print(f"  [skip] {season}: no players_raw or live bootstrap")
            continue
        print(f"  [ok]   {season}: {len(df):>4} players ({src})")
        frames.append(df)

    out = pd.concat(frames, ignore_index=True).drop_duplicates(["season", "player_id"])
    out["position"] = out["element_type"].map(_POS)
    return out


def load_id_map(rebuild: bool = False) -> pd.DataFrame:
    """Return the id map, building + caching it on first use."""
    if _OUT.exists() and not rebuild:
        return pd.read_parquet(_OUT)
    print("Building id_map:")
    m = build()
    m.to_parquet(_OUT, index=False)
    return m


def attach_code(df: pd.DataFrame) -> pd.DataFrame:
    """Add `player_code` to a frame that has (season, player_id)."""
    m = load_id_map()[["season", "player_id", "player_code"]]
    merged = df.merge(m, on=["season", "player_id"], how="left")
    missing = merged["player_code"].isna().mean()
    if missing:
        print(f"  [warn] {missing:.1%} of rows had no player_code match")
    return merged


def main() -> int:
    m = load_id_map(rebuild=True)
    print(f"\nid_map: {len(m):,} (season, player) rows, "
          f"{m['player_code'].nunique():,} unique player codes")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
