"""FotMob per-match defensive statistics -- direct unofficial JSON endpoints.

FPL's defensive-contribution points reward tackles/interceptions/blocks/
clearances/recoveries, and neither vaastav's merged_gw.csv nor Understat
carries per-match defensive-action counts. FotMob's own match-center page
does, via a reverse-engineered JSON API (D-11: direct endpoints, no browser
automation, no wrapper package -- a thin `requests.get()` around two
undocumented paths, discovered this plan by inspecting live responses):

  - `GET /api/data/leagues?id=47&season={YYYY/YYYY}` -- one season's fixture
    list (`fixtures.allMatches`), giving match ids + finished/cancelled state.
    League id 47 = Premier League (verified 2026-09-08).
  - `GET /api/data/matchDetails?matchId={id}` -- one match's full payload,
    including `content.playerStats` keyed by FotMob player id, each carrying
    a list of labelled stat blocks (`Tackles`, `Interceptions`, `Blocks`,
    `Clearances`, `Recoveries`, `Duels won`, among others). Verified live
    2026-09-08: all 6 sampled matches in each of the 6 walk-forward test
    seasons (2020-21..2025-26) carried these labels; seasons before 2020-21
    frequently do not (FotMob's own historical coverage tier drops from
    "xG" to "ratings"/"lower" -- no defensive-action labels present), which
    this module treats as ordinary missing data (NaN), not an error.

D-11 explicitly accepts this may break upstream with no warning -- the
`FOTMOB_ENABLED` kill switch, the on-disk cache, and the coverage-percentage
print in `attach()` are how a break shows up as a visible coverage cliff
between pipeline runs (09-RESEARCH.md Pitfall 3), never a silently NaN-filled
column nobody notices.

Two-step, matching data/understat.py's shape:
  1. python -m data.fotmob            # (re)build data/processed/fotmob.parquet
  2. python -m data.build_table       # auto-joins the file if present
     (adds config.FOTMOB_COLS); without it, nothing changes.

IMPORTANT -- leakage: these columns describe the match they came from (a
MATCH OUTCOME), not pre-match context. See config.FOTMOB_COLS's comment and
features/engineer.py's ROLL_STATS registration: they reach the model only
through the shift(1)-then-rolling path, never raw.

NOTE: joined by normalised player name (FotMob has no FPL id) via the shared
`data.id_crosswalk.resolve_by_name` -- extend `data.id_crosswalk._NAME_FIXUPS`
(not a second dict here) for misses. Check the printed coverage on first run.

Run:
  python -m data.fotmob            # (re)build data/processed/fotmob.parquet
  python -m data.fotmob --force    # ignore all caches, refetch everything
"""
from __future__ import annotations

import argparse
import sys
import time

import pandas as pd
import requests

import config
from ops.jsonio import PayloadError, read_json, write_json

# Module-level kill switch (09-PATTERNS.md convention): flipping this to False
# makes every public entry point below a no-op without touching a call site.
FOTMOB_ENABLED = True

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
}
TIMEOUT = 30

_MIN_INTERVAL_S = 1.5     # conservative rate limit -- unofficial endpoint, D-11
_LEAGUE_ID = 47           # Premier League
_RAW_DIR = config.RAW_DIR / "fotmob"
_OUT = config.PROCESSED_DIR / "fotmob.parquet"

# Endpoints reverse-engineered and verified live against fotmob.com on
# 2026-09-08. No stability contract -- a future break is expected (D-11); the
# kill switch above and the coverage print in attach() are the mitigation.
_ENDPOINTS = {
    "leagues": "https://www.fotmob.com/api/data/leagues?id={league_id}&season={season}",
    "match_details": "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}",
}

# Local literal, not config.FOTMOB_COLS: this module (Task 1) is fetched and
# cached before config.py declares that constant (Task 2). The six names are
# identical to config.FOTMOB_COLS once it exists -- attach()'s own coverage
# print and data/build_table.py's guarded join are what make the two names
# line up in practice; nothing here needs to import config for that to hold.
_RAW_COLS = ["fm_tackles", "fm_interceptions", "fm_blocks", "fm_clearances",
             "fm_recoveries", "fm_duels_won"]
_TIDY_COLS = ["season", "fotmob_player_id", "player_name", "match_date"] + _RAW_COLS

# FotMob's own display labels for each stat, verified live 2026-09-08. Match
# by label (what the page itself shows), not by FotMob's internal `key` field
# -- one of the six (Tackles) carries an unstable-looking internal key
# ("matchstats.headers.tackles", an apparent raw i18n string), while every
# label observed was stable across players and matches.
_STAT_LABELS = {
    "fm_tackles": "Tackles",
    "fm_interceptions": "Interceptions",
    "fm_blocks": "Blocks",
    "fm_clearances": "Clearances",
    "fm_recoveries": "Recoveries",
    "fm_duels_won": "Duels won",
}

_last_call_ts = 0.0


def _fotmob_season(season: str) -> str:
    """'2022-23' -> '2022/2023' (FotMob's own season label format)."""
    a, b = season.split("-")
    return f"{a}/20{b}"


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
    rather than letting a schema change propagate as NaN (T-09-09-01: an
    unofficial API has no stability contract -- this is the security control
    for that)."""
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


def _fetch(url: str, cache_path, *, what: str, force: bool = False) -> dict | None:
    """GET `url`, caching the raw JSON payload under `cache_path` via
    ops.jsonio. Returns None with a printed reason on any `requests` failure
    or non-JSON body -- optional enrichment must never break the pipeline
    (matches data/odds.py::_download's cache-then-parse contract)."""
    if cache_path.exists() and not force:
        try:
            return read_json(cache_path, what=what)
        except PayloadError as exc:
            print(f"  [fotmob] {what} cache unreadable, refetching: {exc}")
    try:
        _throttle()
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        print(f"  [fotmob] fetch failed for {what}: {exc}")
        return None
    except ValueError as exc:   # response body was not valid JSON
        print(f"  [fotmob] non-JSON response for {what}: {exc}")
        return None
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(payload, cache_path)
    return payload


def _fetch_season_matches(season: str, *, force: bool = False) -> list[dict] | None:
    """One season's fixture list (match id + finished state), cached under
    data/raw/fotmob/leagues/<season>.json."""
    cache_path = _RAW_DIR / "leagues" / f"{season}.json"
    what = f"FotMob leagues {season}"
    payload = _fetch(_ENDPOINTS["leagues"].format(
        league_id=_LEAGUE_ID, season=_fotmob_season(season)), cache_path,
        what=what, force=force)
    if payload is None:
        return None
    try:
        return _require(payload, ["fixtures", "allMatches"], list, what)
    except ValueError as exc:
        print(f"  [fotmob] {exc}")
        return None


def _stat_value(player: dict, label: str) -> float:
    """Find `label`'s numeric value across a player's stat blocks (search all
    blocks, not just "defense"/"duels" -- resilient to FotMob reordering or
    renaming a block key while keeping the same on-page label). NaN when the
    label is absent (a real "not measured" for this player/match, distinct
    from a legitimate zero -- Pitfall 3's coverage print depends on this
    distinction to catch a silent break)."""
    for block in player.get("stats", []):
        stat = block.get("stats", {}).get(label)
        if stat is None:
            continue
        val = stat.get("stat", {}).get("value")
        if val is not None:
            return float(val)
    return float("nan")


def _extract_player_rows(match_payload: dict, season: str, match_date: str) -> list[dict]:
    player_stats = _require(match_payload, ["content", "playerStats"], dict,
                            "FotMob matchDetails")
    rows = []
    for pid, p in player_stats.items():
        name = p.get("name")
        if name is None:
            continue
        row = {"season": season, "fotmob_player_id": pid, "player_name": name,
              "match_date": match_date}
        for col, label in _STAT_LABELS.items():
            row[col] = _stat_value(p, label)
        rows.append(row)
    return rows


def build(*, force: bool = False) -> pd.DataFrame:
    """Fetch every season in `config.SEASONS`, write the tidy union to
    `data/processed/fotmob.parquet`. Prints per-season row count and date
    range."""
    if not FOTMOB_ENABLED:
        print("  [fotmob] disabled (FOTMOB_ENABLED=False)")
        return pd.DataFrame(columns=_TIDY_COLS)

    frames = []
    for season in config.SEASONS:
        matches = _fetch_season_matches(season, force=force)
        if not matches:
            print(f"  [skip] {season}: no FotMob fixture list")
            continue
        finished = [m for m in matches
                   if isinstance(m, dict) and m.get("status", {}).get("finished")]
        rows: list[dict] = []
        for m in finished:
            mid = m.get("id")
            if mid is None:
                continue
            cache_path = _RAW_DIR / "matches" / f"{mid}.json"
            payload = _fetch(_ENDPOINTS["match_details"].format(match_id=mid),
                             cache_path, what=f"FotMob matchDetails {mid}", force=force)
            if payload is None:
                continue
            try:
                match_date = _require(payload, ["general", "matchTimeUTCDate"], str,
                                      "FotMob matchDetails")
                rows.extend(_extract_player_rows(payload, season, match_date))
            except ValueError as exc:
                print(f"  [fotmob] {exc}")
                continue
        if not rows:
            print(f"  [skip] {season}: no FotMob player rows")
            continue
        df = pd.DataFrame(rows, columns=_TIDY_COLS)
        frames.append(df)
        print(f"  [ok]   {season}: {len(df):,} rows, "
              f"dates {df.match_date.min()} - {df.match_date.max()}")

    if not frames:
        raise SystemExit("No FotMob data fetched.")
    out = pd.concat(frames, ignore_index=True)
    # Never let a name/id collision (or a re-fetch race) multiply rows on the join key.
    out = out.drop_duplicates(subset=["season", "player_name", "match_date"])
    out.to_parquet(_OUT, index=False)
    return out


def load_fotmob() -> pd.DataFrame | None:
    """Return the cached table, or None when absent -- matching
    `data/understat.py::load_understat`'s no-op-if-absent contract."""
    return pd.read_parquet(_OUT) if _OUT.exists() else None


def attach(full: pd.DataFrame) -> pd.DataFrame:
    """Join cached FotMob per-match defensive stats onto a player_gw-shaped
    frame by (season, player_code, match date). No-op if the kill switch is
    off or the cache is absent -- optional enrichment must never break the
    pipeline.

    IMPORTANT: these columns describe the match they came from (a MATCH
    OUTCOME, not pre-match context) -- see config.FOTMOB_COLS's comment.
    """
    if not FOTMOB_ENABLED:
        return full
    fm = load_fotmob()
    if fm is None:
        return full

    from data import id_crosswalk

    fm = fm.copy()
    fm["player_code"] = id_crosswalk.resolve_by_name(fm["player_name"])
    fm = fm.dropna(subset=["player_code"])
    fm["player_code"] = fm["player_code"].astype("Int64")
    fm["_match_date"] = pd.to_datetime(fm["match_date"], errors="coerce").dt.date.astype(str)
    fm["_key"] = (fm["season"].astype(str) + "|" + fm["player_code"].astype(str)
                  + "|" + fm["_match_date"])
    fm = fm.drop_duplicates(subset="_key")   # never let the join multiply rows

    full = full.copy()
    full["_match_date"] = full["kickoff_time"].dt.date.astype(str)
    full["_key"] = (full["season"].astype(str) + "|"
                    + full["player_code"].astype("Int64").astype(str)
                    + "|" + full["_match_date"])

    merged = full.merge(fm[["_key"] + _RAW_COLS], on="_key", how="left")
    merged = merged.drop(columns=["_match_date", "_key"])
    if len(merged) != len(full):   # a many-to-many join here corrupts every backtest
        raise AssertionError(
            f"fotmob join changed row count {len(full)} -> {len(merged)}")
    cov = merged[_RAW_COLS[0]].notna().mean()
    print(f"  [fotmob] joined; coverage {cov:.1%}"
          + ("  (low -> extend data.id_crosswalk._NAME_FIXUPS)" if cov < 0.5 else ""))
    return merged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore all caches, refetch everything")
    args = ap.parse_args(argv)

    if not FOTMOB_ENABLED:
        print("[fotmob] disabled (FOTMOB_ENABLED=False)")
        return 0
    out = build(force=args.force)
    print(f"fotmob: {len(out):,} player-match rows over "
          f"{out.season.nunique()} seasons; cols={_RAW_COLS}")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
