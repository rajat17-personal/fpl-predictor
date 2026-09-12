"""Self-hosted per-gameweek data capture from the official FPL API.

vaastav's Fantasy-Premier-League repo has stalled at 2026-27 GW1 (confirmed
2026-09-08, .planning/research/DATA-SOURCE-RESILIENCE.md). The official FPL
API is now the source of truth for the CURRENT season's per-gameweek rows;
vaastav is demoted to past seasons only, which stay fully cached and unchanged
under data/raw/. Every file this module writes lands in vaastav's own
merged_gw schema and at vaastav's own flat on-disk paths, so
data/build_table.py and data/id_map.py consume the captured rows with zero
code changes.

Every run also refreshes the two mutable current-season files -- players_raw.csv
and fixtures.csv -- unconditionally: prices, injury status, difficulty
re-ratings and newly-played fixtures change continuously, and a
skip-if-exists guard (the pattern data/ingest.py applies to frozen past
seasons) is exactly how a copy cached before the season started would stay
authoritative forever.

xP resolution (config.MERGED_GW_COLUMNS's "xP" -> "xp_fpl") reads
data/snapshot.py's daily archive via `resolve_xp_for_gw`: for the current
season, gameweeks whose deadline predates the first daily snapshot
(2026-08-31) have no expected-points figure and never will -- the column is
missing-valued for GW1/GW2 by design, a permanent data gap, not a bug a
future join fix would close. A future promotion of this season into the
training seasons must read that gap as real, not as evidence of a broken
join.

A plain run backfills every finished-and-data-checked gameweek that has no
ledger file yet -- there is no separate backfill flag to remember. A finished
gameweek left uncaptured is reported through `ops.notify.report` and makes
`main()` return non-zero, so a stalled capture is never silent.

Run:
  python -m data.gw_capture                          # capture every finished GW missing a ledger
  python -m data.gw_capture --gw 3 4                  # capture specific GWs only
  python -m data.gw_capture --force                   # re-sweep every finished GW regardless of ledger
  python -m data.gw_capture --retries 5 --backoff 3   # tune outage tolerance
  python -m data.gw_capture --sleep 0.2               # tune the element-summary sweep's request pacing
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
import data.snapshot as snapshot_mod
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

# The six identity keys data/id_map.py's `_from_players_raw` reads (id, code,
# web_name, first_name, second_name, element_type) plus `team`, the seventh
# field build_gw_frame joins the club name from. A payload missing any of
# these must stop the run before a written players_raw.csv silently drops the
# identity columns id_map.py's primary read path depends on.
_ELEMENT_IDENTITY_KEYS = ["id", "code", "web_name", "first_name", "second_name",
                          "element_type", "team"]
_TEAM_IDENTITY_KEYS = ["id", "name"]

# The ordered, complete output column set -- vaastav's real 46-column
# merged_gw.csv schema. Every left-hand key of config.MERGED_GW_COLUMNS must
# be a member of this set; asserted at import time so a dropped upstream
# field surfaces as an import-time failure, not a silently all-NaN column.
MERGED_GW_HEADER = _HISTORY_KEYS + ["name", "position", "team", "xP", "GW"]

assert set(config.MERGED_GW_COLUMNS) <= set(MERGED_GW_HEADER), (
    "MERGED_GW_HEADER is missing a config.MERGED_GW_COLUMNS source key: "
    f"{sorted(set(config.MERGED_GW_COLUMNS) - set(MERGED_GW_HEADER))}"
)


class CaptureSummary(dict):
    """`capture()`'s return value: a `{gw: row_count}` mapping -- 08-01's own
    contract, preserved exactly for dict equality (`summary == {1: n}`) --
    plus two extra attributes set after every run:

    - `missing_gws`: `check_freshness`'s result, so `main()` can decide the
      exit code from the SAME already-fetched bootstrap payload rather than
      spending a second bootstrap-static request just to re-derive it (which
      would break the "a quiet day costs two requests" budget).
    - `failures`: the element-summary sweep's per-player failure count, so a
      sweep that quietly lost players is visible even though the ledger file
      it wrote looks complete.

    Dict equality compares contents only and ignores these extra attributes,
    so 08-01's own assertions (`summary == {1: len(boot["elements"])}`) stay
    intact against this subclass.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.missing_gws: list[int] = []
        self.failures: int = 0


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


def _require_fields(payload_rows: list[dict], required: list[str], what: str) -> None:
    """Raise `ValueError` naming any of `required` missing from
    `payload_rows`'s first row, after alerting -- the payload-shape sibling
    of `data/availability.py`'s `_require_columns`, adapted from a DataFrame
    column check to a list of raw API payload dicts.

    Checked against the first row only: the FPL payload's schema is uniform
    across every row of a given endpoint response, so the first row's key set
    is representative, and checking only it avoids an O(n) scan across a
    656-player element-summary sweep. An upstream field vanishing must stop
    the run -- the alternative is a column of missing values a future
    retrain treats as real.
    """
    if not payload_rows:
        return
    missing = [f for f in required if f not in payload_rows[0]]
    if missing:
        message = f"{what}: missing required field(s) {missing}"
        report(_JOB, "schema", message)
        raise ValueError(message)


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


def _fetch_fixtures(*, retries: int, backoff: float) -> list[dict]:
    """GET fixtures/ with the same bounded retry/backoff/report shape as
    `_fetch_bootstrap` -- the same retryable status set, the same immediate
    raise on a non-retryable 4xx, the same `report` before the final re-raise.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(f"{config.FPL_API}/fixtures/", headers=_HEADERS, timeout=30)
            if r.status_code in _RETRYABLE_STATUS:
                raise requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            last_exc = exc
            is_last = attempt == retries
            reason = str(exc)
            if is_last:
                report(_JOB, "fetch", f"fixtures fetch failed after {attempt} attempt(s): {reason}")
                raise
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in _RETRYABLE_STATUS and 400 <= status < 500:
                report(_JOB, "fetch", f"fixtures fetch failed (non-retryable {status}): {reason}")
                raise
            sleep_s = backoff ** (attempt - 1) + random.random()
            print(f"[gw_capture] attempt {attempt}/{retries} failed ({reason}) -- retrying in {sleep_s:.1f}s")
            time.sleep(sleep_s)
    raise last_exc if last_exc is not None else RuntimeError("fixtures fetch failed")


def write_players_raw(boot: dict, season: str | None = None) -> None:
    """Write the bootstrap's full element list to the season directory's
    `players_raw.csv`, with columns sorted so the header order matches the
    published file's own alphabetical ordering.

    Writes the full element field set, not a selected subset:
    `data/id_map.py` reads with its own column selection so the extra fields
    cost nothing, while a narrowed file would silently drop the set-piece
    order columns `build_table.py`'s set-piece merge depends on. Called
    unconditionally on every run -- this file changes continuously (prices,
    injury news, difficulty re-ratings), and a guard that skips because the
    file already exists is how the copy now on disk stays frozen at its
    pre-season state.
    """
    df = pd.DataFrame(boot["elements"])
    df = df.reindex(columns=sorted(df.columns))
    write_csv_atomic(df, season_dir(season) / "players_raw.csv")


def write_fixtures(fixtures: list[dict], season: str | None = None) -> None:
    """Write the fixtures/ payload to the season directory's `fixtures.csv`,
    keeping the payload's own field names so `build_table._join_fixture_difficulty`'s
    expected columns (`id`, `team_h_difficulty`, `team_a_difficulty`) arrive
    unchanged. Called unconditionally on every run, like `write_players_raw`.
    """
    df = pd.DataFrame(fixtures)
    write_csv_atomic(df, season_dir(season) / "fixtures.csv")


def fetch_history(pid: int) -> list[dict]:
    """GET element-summary/{pid}/ and return its `history` list.

    Guards the payload shape before returning: a history row missing one of
    the 41 sourced keys raises naming it, because that field vanishing
    upstream is how a future retrain silently trusts an all-NaN column.
    """
    r = requests.get(f"{config.FPL_API}/element-summary/{pid}/", headers=_HEADERS, timeout=20)
    r.raise_for_status()
    hist = r.json().get("history", [])
    _require_fields(hist, _HISTORY_KEYS, "element-summary history")
    return hist


def sweep_histories(ids: list[int], *, sleep: float = _SLEEP) -> tuple[dict[int, list[dict]], int]:
    """Per-player element-summary sweep: one player's transport failure warns
    and continues rather than aborting the whole sweep (per
    data/live_history.py). Returns `(histories, failure_count)` so the
    caller can surface a partial sweep in the run summary rather than let a
    "complete-looking" ledger file hide it."""
    histories: dict[int, list[dict]] = {}
    failures = 0
    for i, pid in enumerate(ids):
        try:
            histories[pid] = fetch_history(pid)
        except requests.RequestException as exc:
            print(f"  [warn] element {pid}: {exc}")
            failures += 1
            continue
        if i % 100 == 0:
            print(f"  fetched {i}/{len(ids)} players")
        time.sleep(sleep)
    return histories, failures


def _to_utc_date(ts):
    """Coerce an ISO timestamp (or Timestamp) to its UTC calendar date."""
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return t.date()


def _select_xp_snapshot(deadline, snaps: pd.DataFrame):
    """Pick the single latest snapshot dated on or before `deadline`'s UTC
    calendar date, and that snapshot's own recorded next gameweek.

    Returns `(date, rows, recorded_next_gw)`, or `(None, None, None)` when no
    snapshot qualifies (empty archive, or nothing dated early enough).
    """
    if snaps is None or snaps.empty:
        return None, None, None
    deadline_date = _to_utc_date(deadline)
    snap_dates = pd.to_datetime(snaps["date"]).dt.date
    candidates = snaps[snap_dates <= deadline_date]
    if candidates.empty:
        return None, None, None
    candidate_dates = snap_dates[candidates.index]
    latest_date = candidate_dates.max()
    latest_rows = candidates[candidate_dates == latest_date]
    recorded_next_gw = latest_rows["next_gw"].iloc[0]
    return latest_date, latest_rows, recorded_next_gw


def resolve_xp_for_gw(gw: int, deadline, snaps: pd.DataFrame) -> dict[int, float]:
    """Resolve `xP` for gameweek `gw` from a preloaded daily-snapshot frame,
    returning a mapping from element id to expected-points value.

    Selects the single latest snapshot dated on or before the UTC calendar
    date of `deadline` (the gameweek's own deadline timestamp). With none
    qualifying, returns an empty mapping -- the caller writes missing values
    and the run still succeeds.

    Branches on that snapshot's own recorded next gameweek `S`, never on its
    date alone: `S == gw` means `gw` was still upcoming at capture time and
    its figure lives in the next-gameweek projection column (`ep_next`);
    `S == gw + 1` means `gw` was the event in progress at capture time and
    its figure lives in the current-gameweek projection column (`ep_this`);
    anything else means the snapshot is too far from `gw` to carry its
    expectation, and the result is an empty mapping. There is no fallback to
    the other column, no scan of an earlier snapshot, and no interpolation --
    these three outcomes are the whole function.

    A player present in the snapshot's chosen date but absent from the
    target gameweek's own captured rows is harmless (the caller never looks
    it up); a player captured in the gameweek but absent from the chosen
    snapshot resolves to missing via a plain dict lookup miss at the call
    site, while every other player in the same mapping keeps its own value.
    """
    latest_date, latest_rows, recorded_next_gw = _select_xp_snapshot(deadline, snaps)
    if latest_rows is None:
        print(f"[gw_capture] GW{gw} xP: no snapshot dated on or before the deadline -- missing for all players")
        return {}

    if recorded_next_gw == gw:
        col = "ep_next"
    elif recorded_next_gw == gw + 1:
        col = "ep_this"
    else:
        print(f"[gw_capture] GW{gw} xP: snapshot {latest_date} recorded next_gw={recorded_next_gw} "
              f"-- too far from GW{gw}, missing for all players")
        return {}

    mapping = {int(pid): val for pid, val in zip(latest_rows["player_id"], latest_rows[col])}
    resolved = sum(1 for v in mapping.values() if pd.notna(v))
    frac = (resolved / len(mapping)) if mapping else 0.0
    print(f"[gw_capture] GW{gw} xP: snapshot {latest_date} column {col} -- "
          f"{frac:.0%} resolved ({resolved}/{len(mapping)})")
    return mapping


def build_gw_frame(histories: dict[int, list[dict]], boot: dict, gw: int,
                    xp_map: dict[int, float] | None = None,
                    fixtures: list[dict] | None = None) -> pd.DataFrame:
    """Pure transform: histories + bootstrap -> one GW's rows in the output schema.

    Keeps only rows whose `round` equals `gw`. Every history key is copied
    through under its own name. `team` is joined via `teams[].name` -- the
    full club name, which is the key data/odds.py's join and build_table.py's
    odds merge both expect (never `short_name`, which build_table.py's own
    watchlist-facing sibling data/snapshot.py uses for a different consumer).

    `team` is resolved from the row's OWN fixture (`fixtures[].team_h`/`team_a`,
    keyed by `was_home`), never from the player's CURRENT bootstrap team
    assignment -- a player who has since transferred (discovered 2026-09-12,
    Phase 8 plan 08-03's GW1 cross-check: `bootstrap.elements[].team` reflects
    today's club, so a historical row joined against it silently retro-dates
    every one of that player's past fixtures to their new club) must still
    show the club they played for on the day of `gw`. Falls back to the
    current-bootstrap-team join only when `fixtures` is not supplied or the
    row's fixture id is absent from it, so existing direct callers (and the
    schema-convention tests that never register a matching fixture id) are
    unaffected.

    `xP` is resolved from `xp_map` (`resolve_xp_for_gw`'s output) by element
    id; a player absent from `xp_map` -- because the mapping is empty (no
    qualifying snapshot) or because that player's row was absent from the
    chosen snapshot -- gets a missing value, never a value invented or
    carried over from another player or gameweek.
    """
    xp_map = xp_map or {}
    elements = {el["id"]: el for el in boot["elements"]}
    teams = {t["id"]: t["name"] for t in boot["teams"]}
    fixture_teams = {f["id"]: (f.get("team_h"), f.get("team_a")) for f in (fixtures or [])}
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
            fx = fixture_teams.get(h.get("fixture"))
            team_id = (fx[0] if h.get("was_home") else fx[1]) if fx is not None else el.get("team")
            row["team"] = teams.get(team_id)
            row["position"] = _POS.get(el.get("element_type"))
            row["xP"] = xp_map.get(pid, pd.NA)
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


def captured_gws(season: str | None = None) -> set[int]:
    """Gameweek numbers that already have a ledger file under the season
    directory's `gws` child, parsed from `gw<n>.csv` filenames."""
    ledger_dir = _ledger_dir(season)
    if not ledger_dir.exists():
        return set()
    return {int(p.stem[len("gw"):]) for p in ledger_dir.glob("gw*.csv")}


def check_freshness(boot: dict, season: str | None = None) -> list[int]:
    """Sorted finished-and-data-checked gameweeks that have no ledger file.

    Called at the end of every run: this is the check whose absence let the
    previous (vaastav) source stall unnoticed for two gameweeks -- nothing
    told anyone. A non-empty result means a finished gameweek was never
    captured.
    """
    return sorted(set(finished_gws(boot)) - captured_gws(season))


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


def _event_deadline(boot: dict, gw: int) -> str | None:
    for e in boot["events"]:
        if e.get("id") == gw:
            return e.get("deadline_time")
    return None


def capture(*, gws: list[int] | None = None, force: bool = False,
            retries: int = 3, backoff: float = 2.0,
            sleep: float = _SLEEP) -> "CaptureSummary":
    """Fetch bootstrap + fixtures, refresh the two mutable current-season
    files, resolve target GWs, sweep, write per-GW ledgers, regenerate
    merged_gw.csv, alert on a freshness gap, and return a {gw: row_count}
    summary (plus the `missing_gws`/`failures` side-channel attributes; see
    `CaptureSummary`).

    Target-GW resolution: an explicit `gws` list always wins and is swept in
    full. Otherwise `--force` re-sweeps every finished-and-data-checked
    gameweek regardless of ledger presence. Otherwise (the default, plain
    run) the target set is exactly the finished-and-data-checked gameweeks
    with no ledger file yet -- so a first plain run IS the backfill the
    roadmap asks for, with no separate backfill flag to remember, and a
    quiet re-run (nothing new finished) resolves to an empty target set and
    skips the element-summary sweep entirely, costing only the two mutable
    file refreshes below.
    """
    boot = _fetch_bootstrap(retries=retries, backoff=backoff)
    _require_fields(boot["elements"], _ELEMENT_IDENTITY_KEYS, "bootstrap elements")
    _require_fields(boot["teams"], _TEAM_IDENTITY_KEYS, "bootstrap team entries")
    write_players_raw(boot)

    fixtures = _fetch_fixtures(retries=retries, backoff=backoff)
    write_fixtures(fixtures)

    finished = finished_gws(boot)
    if gws is not None:
        targets = list(gws)
    elif force:
        targets = finished
    else:
        already = captured_gws()
        targets = [gw for gw in finished if gw not in already]

    ledger_dir = _ledger_dir()
    failures = 0
    if targets:
        ids = [el["id"] for el in boot["elements"]]
        histories, failures = sweep_histories(ids, sleep=sleep)
        snaps = snapshot_mod.load_snapshots()
        for gw in targets:
            deadline = _event_deadline(boot, gw)
            xp_map = resolve_xp_for_gw(gw, deadline, snaps) if deadline else {}
            frame = build_gw_frame(histories, boot, gw, xp_map, fixtures)
            write_csv_atomic(frame, ledger_dir / f"gw{gw}.csv")
        if failures:
            print(f"[gw_capture] sweep completed with {failures} player fetch failure(s)")

    report_gws = finished if gws is None else targets
    summary = CaptureSummary()
    for gw in report_gws:
        ledger_path = ledger_dir / f"gw{gw}.csv"
        summary[gw] = len(pd.read_csv(ledger_path)) if ledger_path.exists() else 0
    summary.failures = failures

    write_merged()

    missing = check_freshness(boot)
    summary.missing_gws = missing
    if missing:
        report(_JOB, "freshness", f"finished, data-checked gameweek(s) with no captured ledger: {missing}")

    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-sweep every finished GW regardless of ledger")
    ap.add_argument("--gw", type=int, nargs="+", default=None,
                     help="capture only these gameweeks (default: every finished+data-checked GW with no ledger file)")
    ap.add_argument("--retries", type=int, default=3,
                     help="max fetch attempts before giving up (default: 3)")
    ap.add_argument("--backoff", type=float, default=2.0,
                     help="exponential backoff base in seconds (default: 2.0)")
    ap.add_argument("--sleep", type=float, default=_SLEEP,
                     help=f"delay between element-summary requests in seconds (default: {_SLEEP})")
    args = ap.parse_args(argv)
    summary = capture(gws=args.gw, force=args.force, retries=args.retries,
                       backoff=args.backoff, sleep=args.sleep)
    for gw, n in sorted(summary.items()):
        print(f"[gw_capture] GW{gw}: {n} rows")
    if summary.failures:
        print(f"[gw_capture] {summary.failures} player fetch failure(s) this run")
    if summary.missing_gws:
        print(f"[gw_capture] ALERT: finished gameweek(s) with no captured ledger: {summary.missing_gws}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
