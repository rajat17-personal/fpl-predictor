"""Understat non-penalty xG + involvement-chain metrics -- per-match, cached.

FPL's own feed already carries xG/xA (see config.MERGED_GW_COLUMNS: `xg`, `xa`,
`xgi`, `xgc`). Understat adds two things FPL's feed lacks: the NON-PENALTY
separation (`npxG`) and the involvement-IN-THE-MOVE metrics (`xGChain`,
`xGBuildup`) -- OpenFPL's published result (position-specific ensembles
trained on FPL + Understat alone matching FPL Review's accuracy) is why this
source is worth joining at all.

Understat's public API (`understatapi`) is per-PLAYER, not per-league-season:
there is no single endpoint that returns "every EPL player's every match" in
one call. `fetch_season()` therefore makes two cheap league-level calls (the
season's EPL fixture list -> match ids, and the season's EPL player index ->
Understat player ids/names), then walks every player in that index calling
the per-player match-history endpoint (one request per player, their WHOLE
career in one shot) and keeps only the rows whose match id is one of this
season's EPL fixtures -- which cleanly excludes cup/European/other-league
rows a player's raw history also carries. Per-player histories are cached
separately (`data/raw/understat/players/<id>.json`) so a player who appears
in multiple seasons' indices is fetched from the network only once ever.

Two-step, matching data/fbref.py's shape:
  1. python -m data.understat            # (re)build data/processed/understat.parquet
  2. python -m data.build_table           # auto-joins the file if present
     (adds config.UNDERSTAT_COLS); without it, nothing changes.

IMPORTANT -- leakage: these columns describe the match they came from (a MATCH
OUTCOME), not pre-match context. See config.UNDERSTAT_COLS's comment and
features/engineer.py's ROLL_STATS registration: they reach the model only
through the shift(1)-then-rolling path, never raw.

NOTE: joined by normalised player name (Understat has no FPL id) via the
shared `data.id_crosswalk.resolve_by_name` -- extend
`data.id_crosswalk._NAME_FIXUPS` (not a second dict here) for misses. Check
the printed coverage on first run.

Run:
  python -m data.understat        # (re)build data/processed/understat.parquet
  python -m data.understat --force  # ignore all caches, refetch everything
"""
from __future__ import annotations

import argparse
import html
import sys
import time

import pandas as pd

import config
from ops.jsonio import PayloadError, read_json, write_json

# Module-level kill switch (09-PATTERNS.md convention): flipping this to False
# makes every public entry point below a no-op without touching a call site.
UNDERSTAT_ENABLED = True

_MIN_INTERVAL_S = 1.0     # courtesy rate limit -- free community source
_LEAGUE = "EPL"
_RAW_DIR = config.RAW_DIR / "understat"
_PLAYERS_DIR = _RAW_DIR / "players"
_OUT = config.PROCESSED_DIR / "understat.parquet"

# Local literal, not config.UNDERSTAT_COLS: this module (Task 1) is fetched and
# cached before config.py declares that constant (Task 2). The five names are
# identical to config.UNDERSTAT_COLS once it exists -- attach()'s own coverage
# print and data/build_table.py's guarded join are what make the two names
# line up in practice; nothing here needs to import config for that to hold.
_RAW_COLS = ["us_npxg", "us_xgchain", "us_xgbuildup", "us_shots", "us_key_passes"]

_TIDY_COLS = ["season", "understat_player_id", "player_name", "match_date"] + _RAW_COLS

_last_call_ts = 0.0


def _season_label(season: str) -> str:
    """'2021-22' -> '2021' (Understat labels a season by its starting year)."""
    return season.split("-")[0]


def _throttle() -> None:
    """Block until at least `_MIN_INTERVAL_S` has elapsed since the last call."""
    global _last_call_ts
    now = time.monotonic()
    wait = _MIN_INTERVAL_S - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()


def _num(rec: dict, key: str) -> float:
    v = rec.get(key)
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _player_match_history(pid: str, client) -> list[dict] | None:
    """One player's whole per-match history (any league/season), cached
    forever under data/raw/understat/players/<id>.json. Returns None (never
    raises) on a network failure for this one player -- a single flaky
    player must never abort the whole season's fetch."""
    cache_path = _PLAYERS_DIR / f"{pid}.json"
    if cache_path.exists():
        try:
            payload = read_json(cache_path, what=f"Understat player {pid} cache")
            return payload.get("matches", [])
        except PayloadError as exc:
            print(f"  [understat] player {pid} cache unreadable, refetching: {exc}")
    try:
        _throttle()
        matches = client.player(player=str(pid)).get_match_data()
    except Exception as exc:
        print(f"  [understat] player {pid} miss: {exc}")
        return None
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    write_json({"player_id": pid, "matches": matches}, cache_path)
    return matches


def fetch_season(season: str, *, force: bool = False, _client=None) -> pd.DataFrame | None:
    """Fetch (and cache) one EPL season's per-player, per-match Understat rows.

    Cached under `data/raw/understat/<season>.json` as the fully-resolved tidy
    rows for that season (not the raw league payload) -- a cache-warm rerun
    touches the network zero times, matching data/odds.py's `_download`
    cache-then-parse contract. Returns None on total failure; never raises
    (optional enrichment must never break the pipeline).
    """
    if not UNDERSTAT_ENABLED:
        return None
    cache_path = _RAW_DIR / f"{season}.json"
    if cache_path.exists() and not force:
        try:
            payload = read_json(cache_path, what=f"Understat {season} cache")
        except PayloadError as exc:
            print(f"  [miss] {season}: cache unreadable ({exc})")
            return None
        rows = payload.get("rows", [])
        return pd.DataFrame(rows, columns=_TIDY_COLS) if rows else pd.DataFrame(columns=_TIDY_COLS)

    label = _season_label(season)
    owns_client = _client is None
    client = _client
    try:
        if owns_client:
            from understatapi import UnderstatClient
            client = UnderstatClient()
        _throttle()
        matches = client.league(league=_LEAGUE).get_match_data(season=label)
        _throttle()
        players = client.league(league=_LEAGUE).get_player_data(season=label)
    except Exception as exc:
        print(f"  [miss] {season}: {exc}")
        return None
    finally:
        if owns_client and client is not None:
            client.session.close()

    match_ids = {m["id"] for m in matches}
    rows: list[dict] = []
    # Re-open (or reuse) a client for the per-player fetch loop below.
    owns_client2 = _client is None
    client2 = _client
    try:
        if owns_client2:
            from understatapi import UnderstatClient
            client2 = UnderstatClient()
        for p in players:
            pid, pname = p.get("id"), p.get("player_name")
            if pid is None or pname is None:
                continue
            # Understat's JSON leaves apostrophes HTML-entity-escaped (e.g.
            # "N&#039;Golo Kanté") -- unescape before storing, or every
            # such name silently fails id_crosswalk.resolve_by_name's
            # normalised-string-equality match.
            pname = html.unescape(pname)
            hist = _player_match_history(pid, client2)
            if not hist:
                continue
            for rec in hist:
                if rec.get("id") not in match_ids:
                    continue   # cup/European/other-league row in this player's history
                rows.append({
                    "season": season,
                    "understat_player_id": pid,
                    "player_name": pname,
                    "match_date": rec.get("date"),
                    "us_npxg": _num(rec, "npxG"),
                    "us_xgchain": _num(rec, "xGChain"),
                    "us_xgbuildup": _num(rec, "xGBuildup"),
                    "us_shots": _num(rec, "shots"),
                    "us_key_passes": _num(rec, "key_passes"),
                })
    finally:
        if owns_client2 and client2 is not None:
            client2.session.close()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    write_json({"season": season, "rows": rows}, cache_path)
    return pd.DataFrame(rows, columns=_TIDY_COLS) if rows else pd.DataFrame(columns=_TIDY_COLS)


def build(*, force: bool = False) -> pd.DataFrame:
    """Fetch every season in `config.SEASONS` Understat covers, write the
    tidy union to `data/processed/understat.parquet`. Prints per-season row
    count and date range."""
    if not UNDERSTAT_ENABLED:
        print("  [understat] disabled (UNDERSTAT_ENABLED=False)")
        return pd.DataFrame(columns=_TIDY_COLS)

    from understatapi import UnderstatClient

    client = UnderstatClient()
    frames = []
    try:
        for season in config.SEASONS:
            if int(_season_label(season)) < 2014:   # Understat's own coverage floor
                print(f"  [skip] {season}: before Understat's coverage window")
                continue
            df = fetch_season(season, force=force, _client=client)
            if df is None or df.empty:
                print(f"  [skip] {season}: no Understat rows")
                continue
            frames.append(df)
            print(f"  [ok]   {season}: {len(df):,} rows, "
                  f"dates {df.match_date.min()} - {df.match_date.max()}")
    finally:
        client.session.close()

    if not frames:
        raise SystemExit("No Understat data fetched.")
    out = pd.concat(frames, ignore_index=True)
    # Never let a name/id collision (or a re-fetch race) multiply rows on the join key.
    out = out.drop_duplicates(subset=["season", "player_name", "match_date"])
    out.to_parquet(_OUT, index=False)
    return out


def load_understat() -> pd.DataFrame | None:
    """Return the cached table, or None when absent -- matching
    `data/fbref.py::load_fbref`'s no-op-if-absent contract."""
    return pd.read_parquet(_OUT) if _OUT.exists() else None


def attach(full: pd.DataFrame) -> pd.DataFrame:
    """Join cached Understat per-match stats onto a player_gw-shaped frame by
    (season, player_code, match date). No-op if the kill switch is off or the
    cache is absent -- optional enrichment must never break the pipeline.

    IMPORTANT: these columns describe the match they came from (a MATCH
    OUTCOME, not pre-match context) -- see config.UNDERSTAT_COLS's comment.
    """
    if not UNDERSTAT_ENABLED:
        return full
    us = load_understat()
    if us is None:
        return full

    from data import id_crosswalk

    us = us.copy()
    us["player_code"] = id_crosswalk.resolve_by_name(us["player_name"])
    us = us.dropna(subset=["player_code"])
    us["player_code"] = us["player_code"].astype("Int64")
    us["_match_date"] = pd.to_datetime(us["match_date"], errors="coerce").dt.date.astype(str)
    us["_key"] = (us["season"].astype(str) + "|" + us["player_code"].astype(str)
                  + "|" + us["_match_date"])
    us = us.drop_duplicates(subset="_key")   # never let the join multiply rows

    full = full.copy()
    full["_match_date"] = full["kickoff_time"].dt.date.astype(str)
    full["_key"] = (full["season"].astype(str) + "|"
                    + full["player_code"].astype("Int64").astype(str)
                    + "|" + full["_match_date"])

    merged = full.merge(us[["_key"] + _RAW_COLS], on="_key", how="left")
    merged = merged.drop(columns=["_match_date", "_key"])
    if len(merged) != len(full):   # a many-to-many join here corrupts every backtest
        raise AssertionError(
            f"understat join changed row count {len(full)} -> {len(merged)}")
    cov = merged[_RAW_COLS[0]].notna().mean()
    print(f"  [understat] joined; coverage {cov:.1%}"
          + ("  (low -> extend data.id_crosswalk._NAME_FIXUPS)" if cov < 0.5 else ""))
    return merged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore all caches, refetch everything")
    args = ap.parse_args(argv)

    if not UNDERSTAT_ENABLED:
        print("[understat] disabled (UNDERSTAT_ENABLED=False)")
        return 0
    out = build(force=args.force)
    print(f"understat: {len(out):,} player-match rows over "
          f"{out.season.nunique()} seasons; cols={_RAW_COLS}")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
