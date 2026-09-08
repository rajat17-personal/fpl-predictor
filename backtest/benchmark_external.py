"""Phase 9: external-projection benchmark (D-01 experiment 1).

Nothing in this codebase knows whether our xP is already competitive with a
public projection set. theFPLkiwi (github.com/theFPLkiwi/theFPLkiwi) publishes
historical pre-deadline FPL point projections plus an ID dictionary crosswalk
that this module also needs for reading the committed snapshot. Two-step
design, mirroring `data/fbref.py`:

  1. `--fetch` (deliberate, human-run, needs network): downloads theFPLkiwi's
     ID_Dictionary and historical per-gameweek projection CSVs, reduces each
     projection file to eight tidy columns, and writes the small, permanently
     committed snapshot under `data/external/kiwi/` (D-10: reproducible
     forever with no network access; see data/external/README.md for
     attribution and the exact regeneration command).
  2. Default mode (no `--fetch`, no network): reads the committed snapshot
     plus our own leakage-safe walk-forward predictions and reports MAE and
     Spearman side by side, on played-only common rows, for our two
     objectives (xp_med, xp_mean), FPL's own ep_next-equivalent baseline
     (xp_fpl), and theFPLkiwi's projection (proj_pts).

This module is evaluation-only: it never retrains, never writes into
models/artifacts/, and never mutates the committed snapshot.

Run:
  python -m backtest.benchmark_external --fetch           # (re)download + reduce the snapshot
  python -m backtest.benchmark_external                   # score (no network)
  python -m backtest.benchmark_external --tag phase9       # score + write a tagged JSON summary
"""
from __future__ import annotations

import argparse
import io
import sys
import time

import pandas as pd
import requests
from scipy.stats import spearmanr

import config
from backtest.walk_forward import TEST_SEASONS, _preds_for
from models.train import load_features
from ops.jsonio import write_json

_RAW_BASE = "https://raw.githubusercontent.com/theFPLkiwi/theFPLkiwi/main/"
_API_CONTENTS = "https://api.github.com/repos/theFPLkiwi/theFPLkiwi/contents/{path}"
_OUT_DIR = config.DATA_DIR / "external" / "kiwi"
_ID_DICT_URL = _RAW_BASE + "ID_Dictionary.csv"
_ID_DICT_OUT = _OUT_DIR / "ID_Dictionary.csv"

# This project's season label -> theFPLkiwi's per-gameweek projection directory.
_SEASON_DIRS = {
    "2021-22": "Old_Seasons/FPL_projections_21_22",
    "2022-23": "Old_Seasons/FPL_projections_22_23",
    "2023-24": "FPL_projections_23_24",
}
# Mid-week re-issue duplicating GW14 of 2021-22 -- not a distinct gameweek.
_SKIP_FILES = {"FPL_GW14_2.csv"}
_TIDY_COLS = ["season", "gw", "fpl_id", "name", "pos", "team", "price", "proj_pts"]
_REQUEST_DELAY_S = 0.5   # polite pacing between requests, same courtesy as data/fbref.py

# --- scoring mode (Task 3) --------------------------------------------------
# 2023-24's committed snapshot only carries 4 gameweeks (GW1/GW3/GW4/GW18) --
# too thin to score; report it as explicitly skipped, never silently dropped.
_MIN_GWS_TO_SCORE = 20
_STATS_COLS = ["xp_med", "xp_mean", "xp_fpl", "proj_pts"]


def _list_gw_files(season_dir: str) -> tuple[list[str], list[str]]:
    """List `FPL_GW<n>.csv` files in an upstream season directory.

    Returns (files_to_fetch, skipped_files) -- skipped files are named ones in
    `_SKIP_FILES` that upstream actually has, so the caller can print an
    honest record of what was deliberately excluded.
    """
    r = requests.get(_API_CONTENTS.format(path=season_dir), timeout=30)
    r.raise_for_status()
    names = sorted(e["name"] for e in r.json()
                   if e["name"].startswith("FPL_GW") and e["name"].endswith(".csv"))
    skipped = [n for n in names if n in _SKIP_FILES]
    keep = [n for n in names if n not in _SKIP_FILES]
    return keep, skipped


def _gw_from_filename(name: str) -> int:
    """'FPL_GW10.csv' -> 10."""
    return int(name[len("FPL_GW"):-len(".csv")])


def _is_numeric_label(col) -> bool:
    try:
        float(str(col).strip())
        return True
    except ValueError:
        return False


def _reduce_projection_csv(raw: bytes, season: str, gw: int) -> pd.DataFrame:
    """Positionally reduce one theFPLkiwi per-gameweek projection CSV.

    Column layout (both label vintages -- 2021-22/2022-23 use `GW xMins`,
    `xPts if play`, `Probability to play`, `xPts`, `Goals`/`npG`; 2023-24 uses
    `DGWHive`, `GWpts|p`, `GW P(p)`, `GW pts`, `Gwgoals`): 5 identity columns
    (ID, Name, Pos, Price, Team), 3 summary columns, then 5 repeated blocks of
    (one label column, then one numeric-named column per remaining
    gameweek) -- 13 non-numeric header columns in total, always in this
    order. The column names inside each block repeat across blocks (e.g. "10"
    appears once per block), so this MUST be located positionally, never by
    name. The 4th block is the per-gameweek points projection; its label
    column is always the 12th non-numeric header (index 11), and the first
    numeric column right after that label is this file's own gameweek --
    exactly the value we want.
    """
    df = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    cols = list(df.columns)
    label_idx = [i for i, c in enumerate(cols) if not _is_numeric_label(c)]
    # Usually 13 (5 identity + 3 summary + 5 block labels), but the very first
    # gameweek file of a season (e.g. 2021-22's FPL_GW1.csv) sometimes omits
    # the trailing Goals/npG block entirely -> 12. Either way the 4th block
    # (our target) is always the 12th non-numeric header column (index 11),
    # since it always follows the same fixed 5+3+3 columns before it.
    if len(label_idx) < 12:
        raise AssertionError(
            f"GW{gw} {season}: unexpected column layout "
            f"({len(label_idx)} non-numeric header columns, want >=12)")
    proj_col = cols[label_idx[11] + 1]

    out = pd.DataFrame({
        "season": season,
        "gw": gw,
        "fpl_id": pd.to_numeric(df["ID"], errors="coerce"),
        "name": df["Name"],
        "pos": df["Pos"],
        "team": df["Team"],
        "price": pd.to_numeric(df["Price"], errors="coerce"),
        "proj_pts": pd.to_numeric(df[proj_col], errors="coerce"),
    })
    # theFPLkiwi's own README: ID==0 rows are placeholder entries for players
    # not yet in the game (0 minutes/points by construction) -- not real data.
    return out[out.fpl_id != 0].reset_index(drop=True)


def fetch() -> int:
    """Download + reduce theFPLkiwi's ID dictionary and historical per-gameweek
    projections into the small, permanently committed data/external/kiwi/
    snapshot (D-10). Deliberately human-run; never wired into cron or CI."""
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[benchmark] fetching {_ID_DICT_URL}")
    r = requests.get(_ID_DICT_URL, timeout=30)
    r.raise_for_status()
    _ID_DICT_OUT.write_bytes(r.content)
    print(f"[benchmark] saved {_ID_DICT_OUT.relative_to(config.ROOT)} "
          f"({len(r.content):,} bytes)")
    time.sleep(_REQUEST_DELAY_S)

    for season, season_dir in _SEASON_DIRS.items():
        files, skipped = _list_gw_files(season_dir)
        for name in skipped:
            print(f"[benchmark] {season}: skipping {name} (mid-week re-issue, not a "
                  f"distinct gameweek)")
        frames = []
        for name in files:
            gw = _gw_from_filename(name)
            url = f"{_RAW_BASE}{season_dir}/{name}"
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            frames.append(_reduce_projection_csv(resp.content, season, gw))
            time.sleep(_REQUEST_DELAY_S)
        tidy = pd.concat(frames, ignore_index=True)[_TIDY_COLS] if frames else pd.DataFrame(
            columns=_TIDY_COLS)
        dest = _OUT_DIR / f"kiwi_projections_{season}.csv"
        tidy.to_csv(dest, index=False)
        gws = sorted(tidy.gw.unique())
        if gws:
            print(f"[benchmark] {season}: {len(files)} files -> {len(tidy):,} rows, "
                  f"{len(gws)} distinct gameweeks ({gws[0]}-{gws[-1]})")
        else:
            print(f"[benchmark] {season}: {len(files)} files -> 0 rows")
    return 0


def _scoreable_seasons() -> tuple[list[str], list[tuple[str, int]]]:
    """Intersection of `backtest.walk_forward.TEST_SEASONS` with committed
    snapshot seasons carrying >= `_MIN_GWS_TO_SCORE` gameweeks.

    Returns (scoreable, thin) -- `thin` pairs a season with its actual
    gameweek count, so the caller can report it as explicitly skipped rather
    than silently dropping it.
    """
    scoreable, thin = [], []
    for season in TEST_SEASONS:
        path = _OUT_DIR / f"kiwi_projections_{season}.csv"
        if not path.exists():
            continue
        n_gws = int(pd.read_csv(path, usecols=["gw"]).gw.nunique())
        if n_gws >= _MIN_GWS_TO_SCORE:
            scoreable.append(season)
        else:
            thin.append((season, n_gws))
    return scoreable, thin


def _our_preds_gw_level(df: pd.DataFrame, season: str) -> pd.DataFrame:
    """Leakage-safe predictions for `season` (via the same
    `backtest.walk_forward._preds_for` the real harness uses -- never
    `data/processed/test_predictions.parquet`, which only holds the
    2025-26 default test season), collapsed to one row per
    (season, player_id, gw) so double gameweeks line up with theFPLkiwi's
    one-row-per-gameweek shape."""
    te, _models, _cols = _preds_for(df, season)
    return (te.groupby(["season", "player_id", "gw"])
            .agg(xp_med=("xp_med", "sum"), xp_mean=("xp_mean", "sum"),
                 xp_fpl=("xp_fpl", "sum"), y_points=("y_points", "sum"),
                 y_minutes=("y_minutes", "sum"))
            .reset_index())


def _season_played_rows(df: pd.DataFrame, season: str) -> tuple[pd.DataFrame, dict]:
    """Inner-join our GW-level predictions to the committed tidy CSV on
    (season, player_id==fpl_id, gw), then filter to played-only rows
    (y_minutes > 0 -- the B8 fix). Returns (played rows, coverage info)."""
    ours = _our_preds_gw_level(df, season)
    kiwi = pd.read_csv(_OUT_DIR / f"kiwi_projections_{season}.csv")
    kiwi = (kiwi.rename(columns={"fpl_id": "player_id"})
            [["season", "player_id", "gw", "proj_pts"]])
    merged = ours.merge(kiwi, on=["season", "player_id", "gw"], how="inner")
    if len(merged) > len(ours):
        raise AssertionError(
            f"{season}: benchmark join increased row count {len(ours)} -> {len(merged)}")
    coverage = len(merged) / len(ours) if len(ours) else 0.0
    played = merged[merged.y_minutes > 0].reset_index(drop=True)
    info = {"n_rows_before_join": len(ours), "n_rows_common": len(merged),
            "join_coverage": round(coverage, 4), "n_rows_played_only": len(played)}
    return played, info


def _stats_block(played: pd.DataFrame) -> dict:
    """MAE + Spearman (same scipy call as predict/scoreboard.py) against
    y_points, for every column in `_STATS_COLS`."""
    out: dict = {"n_rows": len(played)}
    for col in _STATS_COLS:
        out[f"mae_{col}"] = round(float((played[col] - played.y_points).abs().mean()), 4)
        out[f"spearman_{col}"] = round(
            float(spearmanr(played[col], played.y_points).statistic), 4)
    return out


def score(seasons: list[str] | None = None) -> dict:
    """Score our xP against theFPLkiwi on played-only common rows, per season
    and pooled. Never retrains, never writes into models/artifacts/, never
    mutates the committed snapshot -- evaluation only."""
    scoreable, thin = _scoreable_seasons()
    chosen = seasons if seasons is not None else scoreable
    unknown = [s for s in chosen if s not in TEST_SEASONS]
    if unknown:
        raise SystemExit(f"unknown season(s) {unknown} -- valid: {TEST_SEASONS}")

    for thin_season, n_gws in thin:
        print(f"[benchmark] {thin_season}: skipped -- committed snapshot only carries "
              f"{n_gws} gameweeks (need >= {_MIN_GWS_TO_SCORE} to score)")

    df = load_features()
    per_season: dict = {}
    played_all = []
    for season in chosen:
        played, info = _season_played_rows(df, season)
        stats = _stats_block(played)
        per_season[season] = {**info, **stats}
        played_all.append(played)
        stats_str = " ".join(f"{c}: MAE={stats[f'mae_{c}']:.3f} "
                             f"Spearman={stats[f'spearman_{c}']:.3f}" for c in _STATS_COLS)
        print(f"[benchmark] {season}: n_common={info['n_rows_common']:,} "
              f"(coverage {info['join_coverage']:.1%}), played-only n={stats['n_rows']:,} "
              f"| {stats_str}")
        if info["join_coverage"] < 0.5:
            print(f"[benchmark] WARNING {season}: join coverage "
                  f"{info['join_coverage']:.1%} below 50% -- check the ID alignment "
                  f"before trusting this reading")

    pooled_played = (pd.concat(played_all, ignore_index=True) if played_all
                     else pd.DataFrame(columns=["y_points", *_STATS_COLS]))
    pooled = _stats_block(pooled_played)
    pooled_str = " ".join(f"{c}: MAE={pooled[f'mae_{c}']:.3f} "
                          f"Spearman={pooled[f'spearman_{c}']:.3f}" for c in _STATS_COLS)
    print(f"\n[benchmark] pooled ({', '.join(chosen)}): n={pooled['n_rows']:,} | {pooled_str}")

    return {"seasons": chosen, "skipped_thin": [{"season": s, "n_gws": n} for s, n in thin],
            "per_season": per_season, "pooled": pooled}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true",
                    help="download + reduce the theFPLkiwi snapshot (needs network)")
    ap.add_argument("--seasons", default=None,
                    help="comma-separated season override (default: TEST_SEASONS "
                         "intersected with committed snapshot seasons carrying "
                         f">= {_MIN_GWS_TO_SCORE} gameweeks)")
    ap.add_argument("--tag", default=None,
                    help="write a tagged data/processed/experiments/benchmark_<tag>.json "
                         "summary instead of only printing")
    args = ap.parse_args(argv)
    if args.fetch:
        return fetch()

    seasons = ([s.strip() for s in args.seasons.split(",") if s.strip()]
               if args.seasons else None)
    summary = score(seasons)
    if args.tag:
        config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        dest = config.EXPERIMENTS_DIR / f"benchmark_{args.tag}.json"
        write_json(summary, dest, indent=1)
        print(f"\n[benchmark] saved {dest.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
