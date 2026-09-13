"""Top-100 overall-league consensus ownership -- diagnostic scoreboard benchmark.

DIAGNOSTIC ONLY: this is never a model feature. It fetches the FPL "Overall"
classic league's top-N managers' picks and aggregates them to player
ownership counts, scored against our xP and actual points in
`predict/scoreboard.py`. No manager identity (name, team name, entry id) is
ever persisted to a parquet or to `web/data/scoreboard.json` -- only
`player_id` owner counts (Phase 4's own scrub-names precedent for
third-party manager identity, T-10-02-01).

Mirrors `data/fotmob.py`'s optional-enrichment skeleton: a kill switch, a
throttle, an on-disk JSON cache via `ops.jsonio`, explicit-shape validation
via `_require`, and a `build`/`load_<name>()` returns-None-if-absent pair.

`OVERALL_LEAGUE_ID = 314` is community-documented as the FPL global
"Overall" classic league id (10-RESEARCH.md Assumptions Log A3) -- NOT
independently verified against a live response before this plan. `build()`'s
first real run prints the top-3 entry names/points from page 1 so a human
can eyeball that this is genuinely the global Overall league, not an
arbitrary one; the id is an argument default, never hardcoded inside a URL
f-string, so a correction is a one-line change.

Run:
  python -m data.fpl_standings --gw <N>            # build the season's consensus parquet
  python -m data.fpl_standings --gw <N> --force     # ignore the cache, refetch everything
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

import config
from ops.jsonio import PayloadError, read_json, write_json

# Module-level kill switch (09-PATTERNS.md convention): flipping this to
# False makes every public entry point below a no-op without touching a
# call site.
STANDINGS_ENABLED = True

_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}
TIMEOUT = 30
_MIN_INTERVAL_S = 1.0

# Community-documented id for FPL's global "Overall" classic league (not
# independently verified against a live response until this plan's own
# --gw run -- 10-RESEARCH.md Assumptions Log A3). Kept as a keyword default,
# never hardcoded inside a URL string, so a correction is a one-line change.
OVERALL_LEAGUE_ID = 314

_RAW_DIR = config.RAW_DIR / "standings"

_last_call_ts = 0.0


def _throttle() -> None:
    """Block until at least `_MIN_INTERVAL_S` has elapsed since the last call."""
    global _last_call_ts
    now = time.monotonic()
    wait = _MIN_INTERVAL_S - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()


def _require(payload, path: list[str], expected_type: type, what: str):
    """Explicit shape validation: walk `path` through nested dict keys,
    raising a clear `ValueError` naming the first missing/mis-typed key
    rather than letting a schema change propagate silently."""
    cur = payload
    for key in path:
        if not isinstance(cur, dict):
            raise ValueError(
                f"{what}: expected a dict while walking to '{key}' "
                f"(path {'.'.join(path)}), got {type(cur).__name__}")
        if key not in cur:
            raise ValueError(f"{what}: missing key '{key}' (path {'.'.join(path)})")
        cur = cur[key]
    if not isinstance(cur, expected_type):
        raise ValueError(
            f"{what}: expected {expected_type.__name__} at path {'.'.join(path)}, "
            f"got {type(cur).__name__}")
    return cur


def _cache_path(what: str, gw: int, page: int | None = None) -> Path:
    name = f"{what}_gw{gw:02d}" + (f"_page{page}" if page is not None else "")
    return _RAW_DIR / f"{name}.json"


def fetch_standings(gw: int, *, league_id: int = OVERALL_LEAGUE_ID, pages: int = 3,
                     top_n: int = 100) -> list[dict]:
    """The top `top_n` entries from classic league `league_id`'s standings,
    paging `page_standings=1..pages` and stopping as soon as a page returns
    an empty `results` list."""
    rows: list[dict] = []
    for page in range(1, pages + 1):
        cache_path = _cache_path("standings", gw, page)
        payload = None
        if cache_path.exists():
            try:
                payload = read_json(cache_path, what=f"FPL standings gw{gw} page{page}")
            except PayloadError:
                payload = None
        if payload is None:
            _throttle()
            r = requests.get(
                f"{config.FPL_API}/leagues-classic/{league_id}/standings/",
                params={"page_standings": page}, headers=_HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            payload = r.json()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(payload, cache_path)
        results = _require(payload, ["standings", "results"], list,
                           f"FPL standings gw{gw} page {page}")
        if not results:
            break
        rows.extend(results)
    return rows[:top_n]


def fetch_entry_picks(entry_id: int, gw: int) -> list[dict]:
    """One manager's picks for `gw`. Returns `[]` (never raises) when the
    picks endpoint is unavailable for this entry -- one unavailable manager
    must not kill the whole consensus."""
    try:
        _throttle()
        r = requests.get(f"{config.FPL_API}/entry/{entry_id}/event/{gw}/picks/",
                         headers=_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        return _require(payload, ["picks"], list, f"FPL picks entry {entry_id} gw{gw}")
    except requests.RequestException as exc:
        print(f"  [standings] picks unavailable for entry {entry_id}: {exc}")
        return []
    except ValueError as exc:
        print(f"  [standings] {exc}")
        return []


def consensus_ownership(picks_by_entry: dict[int, list[dict]]) -> pd.DataFrame:
    """One row per `player_id` owned by at least one manager: `n_owners`,
    `consensus_pct` (`n_owners / N` managers), `consensus_rank` (1 = most
    owned), sorted descending by `n_owners`. Deduplicates within a single
    manager's picks first so a bench/captain duplicate can never double-count.
    """
    n = len(picks_by_entry)
    owners: dict[int, set[int]] = {}
    for entry_id, picks in picks_by_entry.items():
        seen = {p["element"] for p in picks}   # dedup this manager's own picks first
        for pid in seen:
            owners.setdefault(pid, set()).add(entry_id)

    cols = ["player_id", "n_owners", "consensus_pct", "consensus_rank"]
    if not owners:
        return pd.DataFrame(columns=cols)

    rows = [{"player_id": pid, "n_owners": len(entries)} for pid, entries in owners.items()]
    df = pd.DataFrame(rows)
    df["consensus_pct"] = df["n_owners"] / n if n else 0.0
    df = df.sort_values("n_owners", ascending=False).reset_index(drop=True)
    df["consensus_rank"] = df.index + 1
    return df[cols]


def build(gw: int, *, force: bool = False) -> pd.DataFrame:
    """Fetch the top-100 standings + each manager's picks, aggregate to
    consensus ownership, and write `data/processed/consensus_<season>_gw<NN>.parquet`.
    Prints total managers fetched plus distinct players owned."""
    cols = ["player_id", "n_owners", "consensus_pct", "consensus_rank"]
    if not STANDINGS_ENABLED:
        print("  [standings] disabled (STANDINGS_ENABLED=False)")
        return pd.DataFrame(columns=cols)

    season = config.SEASONS[-1]
    out = config.PROCESSED_DIR / f"consensus_{season}_gw{gw:02d}.parquet"
    if out.exists() and not force:
        print(f"  [standings] {out.name} already exists (use --force to overwrite)")
        return pd.read_parquet(out)

    standings = fetch_standings(gw)
    if standings:
        print("  [standings] top-3 spot-check (A3 -- eyeball this is the real Overall league):")
        for i, e in enumerate(standings[:3], 1):
            print(f"    {i}. {e.get('player_name')} ({e.get('entry_name')}) "
                  f"-- {e.get('total')} total pts")

    picks_by_entry = {e["entry"]: fetch_entry_picks(e["entry"], gw) for e in standings}
    consensus = consensus_ownership(picks_by_entry)
    consensus.to_parquet(out, index=False)
    n_players = int(consensus["player_id"].nunique()) if len(consensus) else 0
    print(f"  [standings] gw{gw}: {len(picks_by_entry)} managers fetched, "
          f"{n_players} distinct players owned")
    return consensus


def load_consensus(gw: int) -> pd.DataFrame | None:
    """Return the cached consensus parquet for `gw`, or `None` when absent."""
    season = config.SEASONS[-1]
    out = config.PROCESSED_DIR / f"consensus_{season}_gw{gw:02d}.parquet"
    return pd.read_parquet(out) if out.exists() else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gw", type=int, required=True)
    ap.add_argument("--force", action="store_true", help="ignore all caches, refetch everything")
    args = ap.parse_args(argv)

    if not STANDINGS_ENABLED:
        print("[standings] disabled (STANDINGS_ENABLED=False)")
        return 0
    consensus = build(args.gw, force=args.force)
    print(f"consensus: {len(consensus):,} distinct players; "
          f"top row: {consensus.iloc[0].to_dict() if len(consensus) else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
