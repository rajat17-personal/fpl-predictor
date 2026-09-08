"""Phase 2 feature engineering.

Turns the canonical `player_gw` table into a model-ready feature matrix, one row
per player-fixture. The golden rule is NO LEAKAGE: every feature for a fixture is
computed only from matches that kicked off *before* it.

Design:
  - Model granularity is the individual fixture (not the gameweek). A gameweek's
    expected points is later obtained by summing predicted fixture points across
    a player's fixtures that GW -> double GWs and blank GWs are handled for free.
  - Rolling form features are computed per (season, player_id), ordered by
    kickoff, and SHIFTED by one so a fixture never sees its own outcome.
  - Multiple horizons (config.WINDOWS = [3, 5, 10, "all"]) are all produced so the
    model can choose which matters (the "3 / 10 / all previous games" request).
  - Rows are kept even when a player played 0 minutes: that captures rotation risk
    and feeds the Phase-3 minutes model (a non-playing player scores exactly 0).

Run (after data.build_table):
  python -m features.engineer
"""
from __future__ import annotations

import sys

import pandas as pd

import config

# Per-match performance stats we roll into form features.
# config.UNDERSTAT_COLS is registered HERE, never in CONTEXT_COLS below: those
# columns (us_npxg/us_xgchain/us_xgbuildup/us_shots/us_key_passes) describe the
# MATCH THEY CAME FROM (a match outcome), exactly like xg/xa/xgi/xgc above --
# using them raw as a feature for that same match would hand the model the
# result. Registering them here means every one is only ever seen through
# _roll's shift(1)-then-rolling windows, the same leakage-safety argument as
# every other stat in this list.
ROLL_STATS = [
    "minutes", "starts", "total_points", "xp_fpl",
    "goals_scored", "assists", "clean_sheets", "goals_conceded", "saves",
    "bonus", "bps", "xg", "xa", "xgi", "xgc",
    "influence", "creativity", "threat", "ict_index",
] + config.UNDERSTAT_COLS

# Fixture-context features known BEFORE kickoff (safe to use as-is).
# Optional cols (e.g. FBREF_COLS) are filtered to those actually present at runtime.
# TEAM_STRENGTH_COLS is included unconditionally here (like every other optional
# source) even though EXPERIMENTS["team_strength"] can be off -- the flag only
# controls whether backtest/walk_forward.py's harness drops these columns before
# handing the frame to train_predict, so an A/B is a flag away and never forces a
# features.parquet rebuild. Do not "fix" this by gating inclusion here.
CONTEXT_COLS = (["was_home", "fdr_self", "fdr_opp", "is_dgw", "price_m",
                 "selected", "transfers_balance"]
                + config.SET_PIECE_COLS + config.ODDS_COLS + config.FBREF_COLS
                + config.TEAM_STRENGTH_COLS)

ID_COLS = ["season", "player_key", "player_code", "player_id", "name", "team",
           "position", "gw", "fixture_id", "kickoff_time"]


def _roll(g: pd.core.groupby.DataFrameGroupBy, stat: str, window) -> pd.Series:
    """Leakage-safe rolling mean of `stat`: shift(1) then roll over `window`.

    `window` is an int number of prior appearances, or "all" (expanding).
    """
    if window == "all":
        return g[stat].transform(lambda s: s.shift(1).expanding().mean())
    return g[stat].transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["season", "player_id", "kickoff_time"]).reset_index(drop=True)
    g = df.groupby(["season", "player_id"], sort=False)

    ctx = [c for c in CONTEXT_COLS if c in df.columns]   # skip optional cols if absent
    feat = df[ID_COLS + ctx].copy()

    # --- rolling form over every horizon ---
    # Skip a ROLL_STATS entry absent from df (e.g. config.UNDERSTAT_COLS when
    # data/processed/understat.parquet doesn't exist / attach() never ran) --
    # the same "optional col, no-op if missing" contract CONTEXT_COLS already
    # has via `ctx` above; ROLL_STATS had no optional members before this.
    roll_stats = [s for s in ROLL_STATS if s in df.columns]
    for stat in roll_stats:
        for w in config.WINDOWS:
            feat[f"{stat}_r{w}"] = _roll(g, stat, w)

    # --- volatility / risk (points spread over last 5) ---
    feat["points_std_r5"] = g["total_points"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=2).std())

    # --- experience & congestion (all pre-match) ---
    feat["apps_prior"] = g.cumcount()                       # prior appearances this season
    feat["days_rest"] = (g["kickoff_time"].diff().dt.total_seconds() / 86400)

    # --- targets (passthrough; Phase 3 picks which to use) ---
    feat["y_points"] = df["total_points"]
    feat["y_minutes"] = df["minutes"]
    feat["y_played"] = (df["minutes"] > 0).astype("int8")       # played at all
    feat["y_started"] = (df["minutes"] >= 60).astype("int8")    # got 2 appearance pts
    feat["y_clean_sheets"] = df["clean_sheets"].fillna(0).astype("int8")  # for CS sub-model

    return feat


def summarise(feat: pd.DataFrame) -> None:
    print("\n=== features summary ===")
    print(f"rows      : {len(feat):,}")
    print(f"columns   : {feat.shape[1]}")
    feat_cols = [c for c in feat.columns if c not in ID_COLS and not c.startswith("y_")]
    print(f"features  : {len(feat_cols)}  (context + rolling + experience)")
    print("targets   : y_points, y_minutes, y_played, y_started")

    # Early-season rows have NaN rolling form by design; report how much.
    ex = ["minutes_r5", "total_points_r5", "ict_index_rall", "days_rest"]
    print("\nNaN share of sample features (expected high in GW1-ish):")
    print(feat[ex].isna().mean().mul(100).round(1).to_string())

    print("\nsample player trace (leakage check) — Haaland 2022-23 first 6 fixtures:")
    h = feat[(feat.season == "2022-23") & feat.name.str.contains("Haaland", na=False)]
    cols = ["gw", "was_home", "fdr_opp", "total_points_r3", "minutes_r3", "y_points"]
    print(h[cols].head(6).to_string(index=False))


def main() -> int:
    src = config.PROCESSED_DIR / "player_gw.parquet"
    if not src.exists():
        raise SystemExit("Missing player_gw.parquet. Run `python -m data.build_table`.")
    df = pd.read_parquet(src)
    feat = add_features(df)
    out = config.PROCESSED_DIR / "features.parquet"
    feat.to_parquet(out, index=False)
    summarise(feat)
    print(f"\nwrote {out.relative_to(config.ROOT)}")
    print("Next: Phase 3 model training (models/train.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
