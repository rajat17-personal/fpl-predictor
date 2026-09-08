"""Phase 1 build: assemble the canonical `player_gw` table from cached raw data.

Reads the vaastav merged_gw.csv + fixtures.csv for each configured season,
standardises columns, joins fixture difficulty (FDR), flags double gameweeks,
and writes a single tidy parquet keyed by (season, player_id, gw, fixture_id).

Run (after `python -m data.ingest`):
  python -m data.build_table
"""
from __future__ import annotations

import sys

import pandas as pd

import config
from data import fbref as fbref_mod, id_map, odds as odds_mod, team_strength as ts_mod

# Columns coerced to numeric (everything measurable); the rest stay as-is.
_NUMERIC = {
    "gw", "player_id", "opponent_team_id", "fixture_id", "minutes", "starts",
    "total_points", "xp_fpl", "goals_scored", "assists", "clean_sheets",
    "goals_conceded", "own_goals", "penalties_missed", "penalties_saved", "saves",
    "yellow_cards", "red_cards", "bonus", "bps", "xg", "xa", "xgi", "xgc",
    "influence", "creativity", "threat", "ict_index", "value", "selected",
    "transfers_in", "transfers_out", "transfers_balance", "team_h_score",
    "team_a_score",
}


def _load_merged_gw(season: str) -> pd.DataFrame | None:
    path = config.RAW_DIR / season / "merged_gw.csv"
    if not path.exists():
        print(f"  [skip] {season}: no merged_gw.csv (run ingest first)")
        return None
    df = pd.read_csv(path, low_memory=False)

    # Keep + rename only the columns we know about; report any missing.
    present = {src: dst for src, dst in config.MERGED_GW_COLUMNS.items() if src in df.columns}
    missing = sorted(set(config.MERGED_GW_COLUMNS) - set(present))
    df = df[list(present)].rename(columns=present)
    df.insert(0, "season", season)

    for col in _NUMERIC & set(df.columns):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "was_home" in df.columns:
        df["was_home"] = df["was_home"].astype("boolean")
    if "kickoff_time" in df.columns:
        df["kickoff_time"] = pd.to_datetime(df["kickoff_time"], errors="coerce", utc=True)

    print(f"  [ok]   {season}: {len(df):>6,} rows"
          + (f"  (missing cols: {', '.join(missing)})" if missing else ""))
    return df


def _join_fixture_difficulty(df: pd.DataFrame, season: str) -> pd.DataFrame:
    """Attach FDR for the player's own team and the opponent, from fixtures.csv."""
    path = config.RAW_DIR / season / "fixtures.csv"
    if not path.exists() or "fixture_id" not in df.columns:
        df["fdr_self"] = pd.NA
        df["fdr_opp"] = pd.NA
        return df
    fx = pd.read_csv(path)[["id", "team_h_difficulty", "team_a_difficulty"]]
    fx = fx.rename(columns={"id": "fixture_id"})
    m = df.merge(fx, on="fixture_id", how="left")
    home = m["was_home"].fillna(False)
    m["fdr_self"] = m["team_a_difficulty"].where(~home, m["team_h_difficulty"])
    m["fdr_opp"] = m["team_h_difficulty"].where(~home, m["team_a_difficulty"])
    return m.drop(columns=["team_h_difficulty", "team_a_difficulty"])


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Drop non-player artifacts and exact duplicate rows."""
    # 'AM' = 2024/25 Assistant Manager chip "managers": not pickable players,
    # score points with 0 minutes, and the chip is gone for 2026/27. Remove.
    n_am = (df["position"] == "AM").sum()
    df = df[df["position"] != "AM"]

    # Exact duplicate fixture rows (vaastav merge artifact for players with two
    # element IDs). Deduplicate on the natural key, keeping the first.
    before = len(df)
    df = df.drop_duplicates(subset=["season", "player_id", "fixture_id"], keep="first")
    n_dupes = before - len(df)

    if n_am or n_dupes:
        print(f"  [clean] dropped {n_am} AM (manager) rows, {n_dupes} duplicate rows")
    return df.reset_index(drop=True)


def build() -> pd.DataFrame:
    frames = []
    print("Building canonical player_gw table:")
    for season in config.SEASONS:
        df = _load_merged_gw(season)
        if df is None or df.empty:
            continue
        df = _join_fixture_difficulty(df, season)
        frames.append(df)

    if not frames:
        raise SystemExit("No data loaded. Run `python -m data.ingest` first.")

    full = pd.concat(frames, ignore_index=True)
    full = _clean(full)

    # Season-local key (element IDs are NOT stable across seasons).
    full["player_key"] = full["season"] + "__" + full["player_id"].astype("Int64").astype(str)
    # Stable global player_code (Saka is always 223340) — links seasons + live data.
    full = id_map.attach_code(full)

    # Backfill position for older seasons whose merged_gw.csv lacks it (2016-2019).
    # Without this those seasons have NaN position and would be dropped from every
    # per-position model — i.e. contribute nothing to training.
    pos_map = (id_map.load_id_map()[["season", "player_id", "position"]]
               .rename(columns={"position": "_pos_map"}))
    full = full.merge(pos_map, on=["season", "player_id"], how="left")
    if "position" not in full.columns:
        full["position"] = pd.NA
    full["position"] = full["position"].fillna(full["_pos_map"])
    full = full.drop(columns=["_pos_map"])
    # Normalise goalkeeper label: some seasons use 'GKP' (vaastav quirk) vs 'GK'.
    full["position"] = full["position"].replace({"GKP": "GK"})

    # Set-piece / penalty taker order (season-level, from players_raw snapshot).
    sp = id_map.load_id_map()[["season", "player_id"] + config.SET_PIECE_COLS]
    full = full.merge(sp, on=["season", "player_id"], how="left")

    # Bookmaker-implied probabilities, joined by (season, date, team, was_home).
    try:
        od = odds_mod.load_odds()
        full["_date"] = full["kickoff_time"].dt.date
        od = od.rename(columns={"date": "_date"})
        full = full.merge(od, on=["season", "_date", "team", "was_home"], how="left")
        full = full.drop(columns=["_date"])
        cov = full["odds_pwin"].notna().mean()
        print(f"  [odds]  coverage: {cov:.1%}")
    except Exception as exc:                       # odds are optional enrichment
        print(f"  [odds]  skipped ({exc})")
        for c in config.ODDS_COLS:
            full[c] = pd.NA

    # Optional FBref advanced stats — no-op unless data/processed/fbref.parquet exists.
    try:
        full = fbref_mod.attach(full, id_map.load_id_map())
    except Exception as exc:
        print(f"  [fbref] skipped ({exc})")

    # Optional team-strength (Dixon-Coles) ratings — no-op unless
    # data/processed/team_strength.parquet exists. Always joined when present,
    # independent of EXPERIMENTS["team_strength"]; see config.py's
    # TEAM_STRENGTH_COLS comment for why the feature-selection gate lives in
    # backtest/walk_forward.py instead.
    try:
        full = ts_mod.attach(full)
    except Exception as exc:
        print(f"  [team_strength] skipped ({exc})")
    print(f"  [pos]   position coverage after backfill: "
          f"{full['position'].notna().mean():.1%}")

    # Double gameweek flag: a team playing >1 match in a GW => player has >1 row.
    counts = (full.groupby(["season", "player_id", "gw"], dropna=False)
              .size().rename("matches_in_gw").reset_index())
    full = full.merge(counts, on=["season", "player_id", "gw"], how="left")
    full["is_dgw"] = full["matches_in_gw"] > 1

    # Convenience price in £m.
    if "value" in full.columns:
        full["price_m"] = full["value"] / 10.0

    full = full.sort_values(["season", "player_id", "gw", "kickoff_time"]).reset_index(drop=True)
    return full


def summarise(df: pd.DataFrame) -> None:
    print("\n=== player_gw summary ===")
    print(f"rows        : {len(df):,}")
    print(f"seasons     : {', '.join(sorted(df['season'].unique()))}")
    print(f"players     : {df['player_key'].nunique():,} (player-seasons)")
    by_season = df.groupby("season").agg(
        rows=("player_id", "size"),
        gws=("gw", "nunique"),
        dgw_rows=("is_dgw", "sum"),
    )
    print("\nper season:")
    print(by_season.to_string())
    feat_cols = ["minutes", "total_points", "xp_fpl", "xg", "xa", "xgi",
                 "ict_index", "fdr_self", "price_m"]
    cov = df[[c for c in feat_cols if c in df.columns]].notna().mean().mul(100).round(1)
    print("\nkey column coverage (% non-null):")
    print(cov.to_string())


def main() -> int:
    df = build()
    out = config.PROCESSED_DIR / "player_gw.parquet"
    df.to_parquet(out, index=False)
    summarise(df)
    print(f"\nwrote {out.relative_to(config.ROOT)}")
    print("Next: Phase 2 feature engineering (features/engineer.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
