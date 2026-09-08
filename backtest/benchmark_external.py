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

import config

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true",
                    help="download + reduce the theFPLkiwi snapshot (needs network)")
    args = ap.parse_args(argv)
    if args.fetch:
        return fetch()
    print("[benchmark] no --fetch given and scoring mode is not yet available "
          "(lands in a later task of this plan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
