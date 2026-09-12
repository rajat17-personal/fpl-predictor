"""Self-hosted per-gameweek data capture from the official FPL API.

vaastav's Fantasy-Premier-League repo has stalled at 2026-27 GW1 (confirmed
2026-09-08, .planning/research/DATA-SOURCE-RESILIENCE.md). The official FPL
API is now the source of truth for the CURRENT season's per-gameweek rows;
vaastav is demoted to past seasons only, which stay fully cached and unchanged
under data/raw/. Every file this module writes lands in vaastav's own
merged_gw schema and at vaastav's own flat on-disk paths, so
data/build_table.py and data/id_map.py consume the captured rows with zero
code changes.

xP resolution (config.MERGED_GW_COLUMNS's "xP" -> "xp_fpl") is not implemented
in this plan -- every captured row emits `xP` as a missing value until a later
plan wires it from data/snapshot.py's daily archive. This is a real,
documented data gap for the earliest gameweeks (no pre-deadline snapshot
exists for GW1/GW2 -- the earliest snapshot is 2026-08-31), never a value
invented to fill the column.

Run:
  python -m data.gw_capture                          # capture every finished GW
  python -m data.gw_capture --gw 3 4                  # capture specific GWs only
  python -m data.gw_capture --force                   # re-sweep already-captured GWs
  python -m data.gw_capture --retries 5 --backoff 3    # tune outage tolerance
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests

import config
from ops.notify import report

_JOB = "gw_capture"
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}
_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_SLEEP = 0.08

# The 41 `element-summary` `history` keys, copied straight through under their
# own names -- no renames happen on this side of the boundary. `build_gw_frame`
# adds the five columns that need a join or a derivation on top of these:
# `name`, `position`, `team`, `xP`, `GW`.
_HISTORY_KEYS = [
    "element", "fixture", "opponent_team", "total_points", "was_home",
    "kickoff_time", "team_h_score", "team_a_score", "round", "minutes",
    "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals",
    "penalties_saved", "penalties_missed", "yellow_cards", "red_cards",
    "saves", "bonus", "bps", "influence", "creativity", "threat", "ict_index",
    "starts", "expected_goals", "expected_assists",
    "expected_goal_involvements", "expected_goals_conceded", "value",
    "transfers_balance", "selected", "transfers_in", "transfers_out",
    "modified", "clearances_blocks_interceptions", "recoveries", "tackles",
    "defensive_contribution",
]

# The ordered, complete output column set -- vaastav's real 46-column
# merged_gw.csv schema. Every left-hand key of config.MERGED_GW_COLUMNS must
# be a member of this set; asserted at import time so a dropped upstream
# field surfaces as an import-time failure, not a silently all-NaN column.
MERGED_GW_HEADER = _HISTORY_KEYS + ["name", "position", "team", "xP", "GW"]

assert set(config.MERGED_GW_COLUMNS) <= set(MERGED_GW_HEADER), (
    "MERGED_GW_HEADER is missing a config.MERGED_GW_COLUMNS source key: "
    f"{sorted(set(config.MERGED_GW_COLUMNS) - set(MERGED_GW_HEADER))}"
)


def season_dir(season: str | None = None) -> Path:
    """The flat season directory `build_table.py`/`id_map.py` actually open.

    Resolved at call time (not import time) so redirecting `config.RAW_DIR`
    in a test redirects both the producer and the consumer together.
    """
    return config.RAW_DIR / (season or config.CURRENT_SEASON)


def finished_gws(boot: dict) -> list[int]:
    """Sorted event ids the payload reports as both finished AND data-checked.

    Both conditions, not just the first: an event can flip to `finished`
    before its bonus points and defensive-contribution stats are settled, and
    a row captured in that window is wrong in a way no later run would
    notice, because the ledger file for that GW would already exist.
    """
    return sorted(
        e["id"] for e in boot["events"]
        if e.get("finished") and e.get("data_checked")
    )


def _fetch_bootstrap(*, retries: int, backoff: float) -> dict:
    """GET bootstrap-static with bounded retry + exponential backoff + jitter.

    Shape copied from data/snapshot.py's `_fetch_bootstrap`: a retryable
    5xx/429 status raised as an HTTPError so it lands in the same handler, an
    immediate non-retried raise for a non-retryable 4xx, and a `report(...)`
    call immediately before the final re-raise so the failure both alerts and
    exits non-zero.
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
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in _RETRYABLE_STATUS and 400 <= status < 500:
                report(_JOB, "fetch", f"bootstrap-static fetch failed (non-retryable {status}): {reason}")
                raise
            sleep_s = backoff ** (attempt - 1) + random.random()
            print(f"[gw_capture] attempt {attempt}/{retries} failed ({reason}) -- retrying in {sleep_s:.1f}s")
            time.sleep(sleep_s)
    raise last_exc if last_exc is not None else RuntimeError("bootstrap-static fetch failed")


def fetch_history(pid: int) -> list[dict]:
    """GET element-summary/{pid}/ and return its `history` list."""
    r = requests.get(f"{config.FPL_API}/element-summary/{pid}/", headers=_HEADERS, timeout=20)
    r.raise_for_status()
    return r.json().get("history", [])


def sweep_histories(ids: list[int], *, sleep: float = _SLEEP) -> dict[int, list[dict]]:
    """Per-player element-summary sweep: one player's transport failure warns
    and continues rather than aborting the whole sweep (per data/live_history.py)."""
    histories: dict[int, list[dict]] = {}
    for i, pid in enumerate(ids):
        try:
            histories[pid] = fetch_history(pid)
        except requests.RequestException as exc:
            print(f"  [warn] element {pid}: {exc}")
            continue
        if i % 100 == 0:
            print(f"  fetched {i}/{len(ids)} players")
        time.sleep(sleep)
    return histories


def build_gw_frame(histories: dict[int, list[dict]], boot: dict, gw: int) -> pd.DataFrame:
    """Pure transform: histories + bootstrap -> one GW's rows in the output schema.

    Keeps only rows whose `round` equals `gw`. Every history key is copied
    through under its own name. `team` is joined via `teams[].name` -- the
    full club name, which is the key data/odds.py's join and build_table.py's
    odds merge both expect (never `short_name`, which build_table.py's own
    watchlist-facing sibling data/snapshot.py uses for a different consumer).
    `xP` is emitted as a missing value -- resolved by a later plan.
    """
    elements = {el["id"]: el for el in boot["elements"]}
    teams = {t["id"]: t["name"] for t in boot["teams"]}
    rows = []
    for pid, hist in histories.items():
        el = elements.get(pid)
        if el is None:
            continue
        for h in hist:
            if h.get("round") != gw:
                continue
            row = {k: h.get(k) for k in _HISTORY_KEYS}
            row["GW"] = h.get("round")
            row["name"] = f"{el.get('first_name', '')} {el.get('second_name', '')}"
            row["team"] = teams.get(el.get("team"))
            row["position"] = _POS.get(el.get("element_type"))
            row["xP"] = pd.NA
            rows.append(row)
    df = pd.DataFrame(rows)
    return df.reindex(columns=MERGED_GW_HEADER)


def write_csv_atomic(df: pd.DataFrame, path: Path) -> None:
    """Write `df` to `path` via a sibling temp file + os.replace. On any
    exception the temp file is removed before re-raising -- no consumer ever
    sees a partially-written CSV at a final output path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def _ledger_dir(season: str | None = None) -> Path:
    return season_dir(season) / "gws"


def write_merged(season: str | None = None) -> pd.DataFrame:
    """Concatenate every `gws/gw*.csv` ledger file (in GW order) and write the
    result to the flat merged_gw.csv path. Regenerating from the ledger rather
    than appending is what makes a re-run safe."""
    ledger_dir = _ledger_dir(season)
    files = sorted(ledger_dir.glob("gw*.csv"), key=lambda p: int(p.stem[len("gw"):]))
    frames = [pd.read_csv(f) for f in files]
    merged = (pd.concat(frames, ignore_index=True) if frames
              else pd.DataFrame(columns=MERGED_GW_HEADER))
    out = season_dir(season) / "merged_gw.csv"
    write_csv_atomic(merged, out)
    return merged


def capture(*, gws: list[int] | None = None, force: bool = False,
            retries: int = 3, backoff: float = 2.0) -> dict[int, int]:
    """Fetch bootstrap, resolve target GWs, sweep, write per-GW ledgers,
    regenerate merged_gw.csv, and return a {gw: row_count} summary."""
    boot = _fetch_bootstrap(retries=retries, backoff=backoff)
    targets = gws if gws is not None else finished_gws(boot)
    ledger_dir = _ledger_dir()

    to_fetch = [gw for gw in targets if force or not (ledger_dir / f"gw{gw}.csv").exists()]
    if to_fetch:
        ids = [el["id"] for el in boot["elements"]]
        histories = sweep_histories(ids)
        for gw in to_fetch:
            frame = build_gw_frame(histories, boot, gw)
            write_csv_atomic(frame, ledger_dir / f"gw{gw}.csv")

    summary: dict[int, int] = {}
    for gw in targets:
        ledger_path = ledger_dir / f"gw{gw}.csv"
        summary[gw] = len(pd.read_csv(ledger_path)) if ledger_path.exists() else 0

    write_merged()
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-sweep already-captured GWs")
    ap.add_argument("--gw", type=int, nargs="+", default=None,
                     help="capture only these gameweeks (default: every finished+data-checked GW)")
    ap.add_argument("--retries", type=int, default=3,
                     help="max fetch attempts before giving up (default: 3)")
    ap.add_argument("--backoff", type=float, default=2.0,
                     help="exponential backoff base in seconds (default: 2.0)")
    args = ap.parse_args(argv)
    summary = capture(gws=args.gw, force=args.force, retries=args.retries, backoff=args.backoff)
    for gw, n in sorted(summary.items()):
        print(f"[gw_capture] GW{gw}: {n} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
