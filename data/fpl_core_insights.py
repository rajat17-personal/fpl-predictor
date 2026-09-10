"""Phase 10 plan 10-06: committed vendoring of FPL-Core-Insights' per-gameweek
2025-26 availability data (D-05).

`backtest/walk_forward.py::DATA_SEASONS` drops the live season (2026-27), so
this project's own daily snapshots (first capture 2026-08-31) have ZERO
walk-forward coverage. D-09's covered-season criterion is stated on 2025-26,
which only this one-time vendoring reaches -- plan 10-01 recorded this as a
correction to D-05's "optional" wording.

Two-step design, mirroring `backtest/benchmark_external.py`:

  1. `--fetch` (deliberate, human-run, needs network): lists every gameweek
     folder FPL-Core-Insights publishes for 2025-26 via the GitHub contents
     API, downloads each `playerstats.csv`, reduces it to exactly the six
     availability columns approved at Task 1's blocking-human license
     checkpoint (`id, status, chance_of_playing_next_round,
     chance_of_playing_this_round, news, news_added` -- CSVs only, no
     parquet, no full-table copies), and writes the small, permanently
     committed snapshot under `data/external/fpl_core_insights/2025-2026/`
     (the vendor's own directory naming, matching
     `data/availability.py::_fpl_core_insights_source`'s existing read path
     and `_fci_season_label`'s translation -- see "Layout decision" below).
  2. `--verify` (read-only, no network): the D-05 gate. Compares the
     vendored snapshot's LATEST available gameweek against our own
     `data/snapshots/*.parquet` captures on the two dates we actually have
     (2026-08-31, 2026-09-07). Those two dates fall in season 2026-27, half
     a season after 2025-26 ended, so this is a SCHEMA AND VALUE-SEMANTICS
     check on the players resolvable in both sources -- never a season
     overlap, and a real disagreement rate (player status genuinely changes
     over months) is an expected, honest outcome, not a failure.
  3. `--license`: re-runs Task 1's checkpoint fetch (LICENSE/LICENSE.md/
     README.md plus the resolved `main` commit SHA) for reproducibility --
     the actual posture DECISION was already made and recorded at that
     checkpoint; this flag only re-fetches the same evidence.

Layout decision: `data/availability.py`'s `_fpl_core_insights_source()` (built
by plan 10-01, extended by 10-04) already reads
`config.DATA_DIR / "external" / "fpl_core_insights" / <season_dir> /
GW<n>_playerstats.csv` -- a nested, per-season-directory layout, with the
season directory named however the vendor itself names it ("2025-2026",
translated back to this project's "2025-26" label by
`_fci_season_label()`). This module's `fetch()` writes into EXACTLY that
existing, already-tested read path (`_SEASON_DIR` maps our "2025-26" label
onto the vendor's "2025-2026" directory name, used both for the remote
GitHub path and the local nested output directory) so that zero changes to
`data/availability.py` are needed and the full pipeline
(`data.build_table` -> `features.engineer` -> the `availability_flags` gate)
picks up the vendored data automatically on the next `--force` rebuild.

Identity: the committed CSV keeps the vendor's own raw `id` column
UNCHANGED (never translated to `player_code` at reduction time) --
`_fpl_core_insights_source()` already does that translation itself via
`data.id_map.load_id_map()`'s (season, player_id) -> player_code join, the
same mechanism this module's own `verify()` uses. No second name-based
matcher is introduced; the six-column footprint approved at Task 1's
checkpoint carries no name field, so `data.id_crosswalk.resolve_by_name`'s
fallback has no column to operate on here and is not invoked.

Run:
  python -m data.fpl_core_insights --fetch     # download + reduce (network)
  python -m data.fpl_core_insights --verify    # compare vs our own snapshots (no network)
  python -m data.fpl_core_insights --license   # re-fetch LICENSE/README evidence (network)
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.parse

import pandas as pd
import requests

import config
from data import id_map
from ops.jsonio import write_json

_RAW_BASE = "https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/"
_API_CONTENTS = "https://api.github.com/repos/olbauday/FPL-Core-Insights/contents/{path}"
_OUT_DIR = config.DATA_DIR / "external" / "fpl_core_insights"

# This project's season label -> the vendor's own season directory naming
# (probed live by plan 10-01, confirmed again at this plan's Task 1
# checkpoint: `data/2025-2026/By Gameweek/GW<n>/playerstats.csv`). Matches
# `data/availability.py::_fci_season_label`'s inverse translation exactly.
_SEASON_DIR = {"2025-26": "2025-2026"}

_REQUEST_DELAY_S = 0.5   # polite pacing, same courtesy as data/fbref.py and
                         # backtest/benchmark_external.py

# The six columns approved at Task 1's blocking-human license checkpoint --
# an allowlist, not a denylist (T-10-06-05): any column not named here is
# dropped by construction, regardless of what else the vendor's ~87-column
# playerstats.csv carries.
_KEEP_COLS = ["id", "status", "chance_of_playing_next_round",
              "chance_of_playing_this_round", "news", "news_added"]

_VERIFY_OUT = config.EXPERIMENTS_DIR / "fpl_core_insights_verify.json"

# The only two dates this project has actually captured under data/snapshots/
# at the time this plan runs (2026-08-31, 2026-09-07) -- both fall in season
# 2026-27, so `verify()`'s comparison is schema/value-semantics only.
_OVERLAP_DATES = ("2026-08-31", "2026-09-07")


def _gw_from_filename(name: str) -> int:
    """'GW10' -> 10, 'GW10_playerstats' -> 10, 'GW10_playerstats.csv' -> 10.
    Raises ValueError naming the input if it doesn't start with 'GW' followed
    by a run of digits -- never silently skips an unparseable name."""
    if not name.startswith("GW"):
        raise ValueError(f"cannot parse a gameweek number from {name!r} (must start with 'GW')")
    token = name[2:].split("_")[0]
    if not token.isdigit():
        raise ValueError(f"cannot parse a gameweek number from {name!r}")
    return int(token)


def _list_gw_files(season: str) -> tuple[list[str], list[str]]:
    """Hit the GitHub contents API for the vendor's 'By Gameweek' directory
    and return (gw_dir_names, skipped) -- mirrors
    `backtest/benchmark_external.py::_list_gw_files`'s two-tuple shape.
    `skipped` is always empty for this vendor (no known mid-week re-issue
    duplicate, unlike theFPLkiwi's `_SKIP_FILES`); kept for shape-parity so a
    future duplicate discovery has somewhere to go without changing the
    function's signature.
    """
    season_dir = _SEASON_DIR[season]
    path = f"data/{season_dir}/By Gameweek"
    r = requests.get(_API_CONTENTS.format(path=urllib.parse.quote(path)), timeout=30)
    r.raise_for_status()
    names = sorted(
        (e["name"] for e in r.json() if e.get("type") == "dir" and e["name"].startswith("GW")),
        key=_gw_from_filename,
    )
    return names, []


def _reduce_gw_csv(raw: bytes, season: str, gw: int) -> pd.DataFrame:
    """Reduce one raw `playerstats.csv` payload to exactly `_KEEP_COLS`.

    Validates BEFORE reducing: if any `_KEEP_COLS` member is absent, raises
    `ValueError` naming every missing column at once and the gameweek it came
    from (10-RESEARCH.md Pitfall 2 / T-10-06-02) -- never emits an all-NaN
    column for a missing source column, which would let a genuine vendor
    schema change look like a coverage problem instead of a loud failure.
    """
    df = pd.read_csv(io.BytesIO(raw))
    missing = [c for c in _KEEP_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"GW{gw} {season}: missing required column(s) {missing}")
    return df[_KEEP_COLS].copy()


def fetch(season: str = "2025-26") -> int:
    """Download + reduce every available 2025-26 gameweek from
    FPL-Core-Insights into the small, permanently committed
    `data/external/fpl_core_insights/<vendor season dir>/` snapshot.
    Deliberately human-run; never wired into cron or CI."""
    season_dir_name = _SEASON_DIR[season]
    dest_dir = _OUT_DIR / season_dir_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    gw_names, skipped = _list_gw_files(season)
    for name in skipped:
        print(f"[fpl_core_insights] {season}: skipping {name}")
    print(f"[fpl_core_insights] {season}: {len(gw_names)} gameweek folder(s) found upstream")

    total_bytes = 0
    n_written = 0
    for gw_dir_name in gw_names:
        gw = _gw_from_filename(gw_dir_name)
        url = (f"{_RAW_BASE}data/{urllib.parse.quote(season_dir_name)}/"
               f"By%20Gameweek/{gw_dir_name}/playerstats.csv")
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            print(f"[fpl_core_insights] GW{gw}: 404, skipping (not yet published upstream)")
            continue
        resp.raise_for_status()
        reduced = _reduce_gw_csv(resp.content, season, gw)
        dest = dest_dir / f"GW{gw}_playerstats.csv"
        reduced.to_csv(dest, index=False)
        size_kb = dest.stat().st_size / 1024
        total_bytes += dest.stat().st_size
        n_written += 1
        print(f"[fpl_core_insights] GW{gw}: {len(reduced):,} rows -> "
              f"{dest.relative_to(config.ROOT)} ({size_kb:.1f} KB)")
        time.sleep(_REQUEST_DELAY_S)

    print(f"[fpl_core_insights] wrote {n_written} gameweek file(s) for {season}, "
          f"total {total_bytes / 1024:.1f} KB")
    return 0


def license_check() -> int:
    """Fetch and print, verbatim, the vendor's LICENSE/LICENSE.md (or their
    404 absence), the README, and the resolved `main` commit SHA -- the same
    evidence Task 1's blocking-human checkpoint gathered manually. The
    posture DECISION was already made and recorded at that checkpoint; this
    flag exists only to let the same evidence be re-fetched for audit."""
    for name in ("LICENSE", "LICENSE.md"):
        r = requests.get(_RAW_BASE + name, timeout=30)
        if r.status_code == 404:
            print(f"[fpl_core_insights] {name}: 404 (not published upstream)")
        else:
            r.raise_for_status()
            print(f"[fpl_core_insights] {name}:\n{r.text}")
    r = requests.get(_RAW_BASE + "README.md", timeout=30)
    r.raise_for_status()
    print(f"[fpl_core_insights] README.md:\n{r.text}")
    sha_r = requests.get(
        "https://api.github.com/repos/olbauday/FPL-Core-Insights/commits/main", timeout=30)
    sha_r.raise_for_status()
    sha = sha_r.json()["sha"]
    print(f"[fpl_core_insights] resolved main commit SHA: {sha}")
    return 0


def _per_gw_stats(season: str) -> tuple[dict, pd.DataFrame]:
    """Read every committed gameweek CSV for `season`, returning
    (per_gw row-count/distinct-player stats, the concatenated frame with a
    `gw` column added)."""
    season_dir = _OUT_DIR / _SEASON_DIR[season]
    gw_paths = sorted(season_dir.glob("GW*_playerstats.csv"),
                      key=lambda p: _gw_from_filename(p.stem))
    if not gw_paths:
        raise SystemExit(
            f"[fpl_core_insights] no vendored files found under {season_dir} -- "
            f"run `python -m data.fpl_core_insights --fetch` first")

    per_gw: dict = {}
    frames = []
    for path in gw_paths:
        gw = _gw_from_filename(path.stem)
        df = pd.read_csv(path)
        df["gw"] = gw
        per_gw[str(gw)] = {
            "n_rows": int(len(df)),
            "n_distinct_players": int(df["id"].nunique()),
        }
        frames.append(df)
    return per_gw, pd.concat(frames, ignore_index=True)


def verify(season: str = "2025-26") -> dict:
    """The D-05 gate. Read-only, no network. Compares the vendored
    snapshot's LATEST committed gameweek against our own
    `data/snapshots/*.parquet` captures on the two overlapping dates
    (`_OVERLAP_DATES`) -- both of which fall in season 2026-27, so this is a
    SCHEMA AND VALUE-SEMANTICS check on the players resolvable in both
    sources, not a season overlap (see module docstring).

    Reports the intersecting/exclusive column sets, the pooled agreement
    rate on `status` (exact string match after lower-casing) and on
    `chance_of_playing_next_round` (exact numeric match, NaN==NaN counted as
    agreement), a disagreement sample of up to 10 rows, the vendored
    snapshot's own per-gameweek row/player counts, and per-date detail.
    Writes the full report to
    `config.EXPERIMENTS_DIR / "fpl_core_insights_verify.json"`.
    """
    per_gw, all_vendored = _per_gw_stats(season)
    latest_gw = max(int(k) for k in per_gw)
    latest = all_vendored[all_vendored["gw"] == latest_gw].copy()

    id_map_df = id_map.load_id_map()
    id_map_season = id_map_df[id_map_df["season"] == season][["player_id", "player_code"]]
    latest = latest.rename(columns={"id": "player_id"}).merge(
        id_map_season, on="player_id", how="left")
    unresolved = int(latest["player_code"].isna().sum())
    latest = latest.dropna(subset=["player_code"])

    # Our own data/snapshots/ captures (data/snapshot.py) carry this exact
    # same six-field availability family (chance_of_playing_this_round,
    # news, news_added added by plan 10-01 for this same reason) plus
    # player_code as the join key -- a true apples-to-apples column
    # comparison, not just the two fields the agreement rate is computed on.
    ours_cols = {"player_code", "status", "chance_of_playing_next_round",
                 "chance_of_playing_this_round", "news", "news_added"}
    theirs_cols = (set(_KEEP_COLS) - {"id"}) | {"player_code"}
    columns_ours_only = sorted(ours_cols - theirs_cols)
    columns_theirs_only = sorted(theirs_cols - ours_cols)

    by_date: dict = {}
    disagreements: list[dict] = []
    status_all = []
    chance_all = []
    for date_str in _OVERLAP_DATES:
        snap_path = config.DATA_DIR / "snapshots" / f"{date_str}.parquet"
        if not snap_path.exists():
            by_date[date_str] = {"error": "snapshot file not found"}
            continue
        snap = pd.read_parquet(
            snap_path, columns=["player_code", "status", "chance_of_playing_next_round"])
        merged = latest.merge(snap, on="player_code", how="inner",
                              suffixes=("_vendor", "_ours"))
        n = len(merged)
        status_ok = (merged["status_vendor"].astype(str).str.strip().str.lower()
                    == merged["status_ours"].astype(str).str.strip().str.lower())
        cv = pd.to_numeric(merged["chance_of_playing_next_round_vendor"], errors="coerce")
        co = pd.to_numeric(merged["chance_of_playing_next_round_ours"], errors="coerce")
        chance_ok = (cv == co) | (cv.isna() & co.isna())
        by_date[date_str] = {
            "n_players_compared": int(n),
            "status_agreement": float(status_ok.mean()) if n else None,
            "chance_agreement": float(chance_ok.mean()) if n else None,
        }
        status_all.append(status_ok)
        chance_all.append(chance_ok)
        mismatched = merged[~(status_ok & chance_ok)]
        for _, row in mismatched.iterrows():
            if len(disagreements) >= 10:
                break
            disagreements.append({
                "date": date_str,
                "player_code": int(row["player_code"]),
                "status_vendor": row["status_vendor"], "status_ours": row["status_ours"],
                "chance_vendor": None if pd.isna(row["chance_of_playing_next_round_vendor"])
                                else float(row["chance_of_playing_next_round_vendor"]),
                "chance_ours": None if pd.isna(row["chance_of_playing_next_round_ours"])
                              else float(row["chance_of_playing_next_round_ours"]),
            })

    status_pooled = pd.concat(status_all) if status_all else pd.Series(dtype=bool)
    chance_pooled = pd.concat(chance_all) if chance_all else pd.Series(dtype=bool)
    status_agreement = float(status_pooled.mean()) if len(status_pooled) else None
    chance_agreement = float(chance_pooled.mean()) if len(chance_pooled) else None
    n_compared = int(len(status_pooled))
    n_disagreements = int((~(status_pooled & chance_pooled)).sum()) if n_compared else 0

    payload = {
        "season": season,
        "latest_gw_used": latest_gw,
        "overlap_dates": list(_OVERLAP_DATES),
        "columns_ours_only": columns_ours_only,
        "columns_theirs_only": columns_theirs_only,
        "status_agreement": status_agreement,
        "chance_agreement": chance_agreement,
        "n_players_compared": n_compared,
        "n_unresolved_identity": unresolved,
        "n_disagreements": n_disagreements,
        "disagreement_sample": disagreements,
        "by_date": by_date,
        "per_gw": per_gw,
    }
    write_json(payload, _VERIFY_OUT, indent=2)

    if status_agreement is not None and status_agreement >= 0.95 and chance_agreement >= 0.95:
        print(f"[fpl_core_insights] verify: AGREES "
              f"({status_agreement:.1%} status, {chance_agreement:.1%} chance)")
    else:
        print(f"[fpl_core_insights] verify: DISAGREES -- {n_disagreements} mismatches, "
              f"see sample above")
        for d in disagreements:
            print(f"  {d}")
    print(f"[fpl_core_insights] wrote {_VERIFY_OUT.relative_to(config.ROOT)}")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fetch", action="store_true",
        help="download + reduce every available 2025-26 gameweek from "
             "FPL-Core-Insights (needs network); a deliberate, human-run, "
             "network-using step, never wired into cron or CI")
    ap.add_argument(
        "--verify", action="store_true",
        help="READ-ONLY: compare the committed vendored snapshot's latest "
             "gameweek against our own data/snapshots/ captures; no network")
    ap.add_argument(
        "--license", action="store_true",
        help="fetch and print the vendor's LICENSE/README and the resolved "
             "main commit SHA (needs network) -- audit re-fetch only, the "
             "posture decision itself was made at Task 1's checkpoint")
    args = ap.parse_args(argv)

    if args.license:
        return license_check()
    if args.fetch:
        return fetch()
    if args.verify:
        verify()
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
