"""fplreview.com free-model weekly manual capture -- diagnostic scoreboard benchmark.

DIAGNOSTIC ONLY: fplreview's own point projections are never a model input
and are never redistributed (their ToS). Their site returns HTTP 403 to
automated access (confirmed live, 2026-09-10 -- 10-RESEARCH.md Pitfall 5), so
this module has NO fetcher and imports NO HTTP client at all -- that absence
IS the ToS mitigation, enforced by this plan's own verify (a `requests`/
`httpx`/`urllib` import here would mean an automated-fetch path was added
against a 403-ing, ToS-restricted target).

The capture is genuinely manual: before each gameweek deadline, a human
visits https://app.fplreview.com/free, exports or copies the current
gameweek's projection table, and saves it as
`data/external/fplreview/fplreview_<season>_gw<NN>.csv` -- see
`data/external/fplreview/README.md` for the full destination/regeneration
contract and required column list.

`load_gw` resolves each captured row to a `player_code` exclusively through
`data.id_crosswalk.resolve_by_name` -- never a second name matcher
(10-PATTERNS.md's mandatory-reuse rule).

Run:
  python -m data.fplreview --season 2026-27 --gw 4    # validate a fresh capture
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

import config
from data import id_crosswalk

FPLREVIEW_DIR = config.DATA_DIR / "external" / "fplreview"

# The four columns kept after normalization -- name / team / position /
# projected-points -- see data/external/fplreview/README.md's "Reduction
# applied" section for the exact weekly capture contract.
_REQUIRED_COLS = ["name", "team", "position", "proj_pts"]


def validate(df: pd.DataFrame, path: Path) -> None:
    """Raise `ValueError` naming every missing required column at once (not
    just the first), or when the projected-points column is entirely
    non-numeric -- a copy-paste that captured only the header row."""
    missing = [c for c in _REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"{path}: missing required column(s) {missing} (need {_REQUIRED_COLS})")
    if len(df):
        numeric = pd.to_numeric(df["proj_pts"], errors="coerce")
        if numeric.notna().sum() == 0:
            raise ValueError(
                f"{path}: 'proj_pts' column is entirely non-numeric -- "
                f"looks like a header-only paste")


def _path(season: str, gw: int) -> Path:
    return FPLREVIEW_DIR / f"fplreview_{season}_gw{gw:02d}.csv"


def load_gw(season: str, gw: int) -> pd.DataFrame | None:
    """Read, validate, and resolve one captured fplreview projection file.

    Returns `None` when no capture exists for this gameweek -- an
    uncaptured gameweek is simply absent from the scoreboard, never an
    error. Lower-cases and strips header whitespace before matching, so a
    hand-pasted header still resolves.
    """
    path = _path(season, gw)
    if not path.exists():
        return None

    raw = pd.read_csv(path)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    validate(raw, path)

    df = raw.copy()
    df["proj_pts"] = pd.to_numeric(df["proj_pts"], errors="coerce")
    df["player_code"] = id_crosswalk.resolve_by_name(df["name"])
    n_total = len(df)
    df = df.dropna(subset=["player_code"])
    df["player_code"] = df["player_code"].astype("Int64")
    pct = (len(df) / n_total) if n_total else 0.0
    print(f"[fplreview] gw{gw:02d}: {n_total} rows, {pct:.1%} names resolved")

    dup = df[df.duplicated(subset="player_code", keep=False)]
    if not dup.empty:
        names = sorted(dup["name"].astype(str).unique().tolist())
        raise AssertionError(
            f"{path}: duplicate player_code within one gameweek for names "
            f"{names} -- would multiply rows in the downstream join")

    return df.reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", required=True)
    ap.add_argument("--gw", type=int, required=True)
    args = ap.parse_args(argv)

    out = load_gw(args.season, args.gw)
    if out is None:
        print(f"[fplreview] no capture found for {args.season} gw{args.gw:02d} "
              f"(expected {_path(args.season, args.gw)})")
        return 1
    print(f"[fplreview] {len(out)} rows resolved and validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
