"""Transfermarkt injury-history backfill and player-GW feature join.

Two-plan spike-first contract: this module was BUILT across two plans. Plan
10-05 built the probe-only surface (a figshare pre-scraped-dataset shortcut
check, a bounded real-page access probe, and a one-page HTML parser) and
recorded a go/no-go verdict in IMPROVEMENTS.md: **Option A -- full backfill,
all seasons 2016-17+, background killable job**. Plan 10-07 (this plan) adds
the bulk backfill (`build`/`resolve_tm_id`), the committed normalized spell
table, and the date-range overlap join into the pre-match context feature
family (`injury_status_as_of`/`attach`), authorised by that decision.

Why the extra caution: 10-RESEARCH.md's own evidence on Transfermarkt access
is genuinely contradictory (some 2026 guides say plain `requests` + a
User-Agent works; others describe DataDome JA3/HTTP-2 fingerprinting that
blocks bare `requests`), and `worldfootballR` -- the reference implementation
the originating todo cites -- has been archived read-only since 2025-09-18.
Phase 9 spent three real Chrome spike attempts on FBref before recording it
as not-acquirable (IMPROVEMENTS.md's `### fbref_v2` entry); paying a bounded
probe FIRST, before any fetcher infrastructure, is the whole lesson of that
entry (D-04). Plan 10-05's real 8-page probe measured access as mostly-open
(7/8 pages parsed, 0 challenges) -- see `IMPROVEMENTS.md`'s
`### transfermarkt_injury: go/no-go decision` entry for the full evidence.

Run:
  python -m data.transfermarkt --figshare-check   # ~10min: does a pre-scraped
                                                     # dataset make the scraper unnecessary?
  python -m data.transfermarkt --probe --n 8       # 8-page real access probe (plan 10-05)
  python -m data.transfermarkt --build             # full backfill (plan 10-07). Deliberate,
                                                     # human-run, network-using, NEVER wired into
                                                     # cron or CI. Safe to kill -- resumable.
  python -m data.transfermarkt --build --seasons 2024-25,2025-26   # restrict the scope
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import time

import numpy as np
import pandas as pd
import requests

import config
from ops.jsonio import write_json

# Module-level kill switch (established convention, e.g. data/fotmob.py):
# flipping this to False makes every public entry point below a no-op.
TRANSFERMARKT_ENABLED = True

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 30

# Deliberately double data/fotmob.py's 1.5s -- Transfermarkt is unofficial AND
# anti-bot-protected (T-10-05-04); D-06 explicitly accepts rate-limit-bound
# wall clock for the eventual backfill over risking a block on this machine.
_MIN_INTERVAL_S = 3.0

_RAW_DIR = config.RAW_DIR / "transfermarkt"
_OUT = config.PROCESSED_DIR / "transfermarkt.parquet"
_PROBE_OUT = config.EXPERIMENTS_DIR / "transfermarkt_probe.json"

_FIGSHARE_SEARCH_URL = "https://api.figshare.com/v2/articles/search"
_FIGSHARE_ARTICLE_URL = "https://api.figshare.com/v2/articles/{article_id}"

# Transfermarkt's own public search (unofficial, undocumented) and the
# injury-history profile URL pattern 10-RESEARCH.md's Assumption A4 names as
# unverified -- this probe is precisely what confirms or corrects it.
_SEARCH_URL = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche"
_INJURY_URL = "https://www.transfermarkt.com/spieler/verletzungen/spieler/{tm_id}"
_PLAYER_PROFILE_RE = re.compile(r"/profil/spieler/(\d+)")

_last_call_ts = 0.0


def _throttle() -> None:
    """Block until at least `_MIN_INTERVAL_S` has elapsed since the last call."""
    global _last_call_ts
    now = time.monotonic()
    wait = _MIN_INTERVAL_S - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()


def _slug(url: str) -> str:
    """Turn a URL into a filesystem-safe cache key."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")[:150]


def _fetch_page(url: str, *, what: str, result: dict | None = None) -> str | None:
    """GET `url` with throttling and a realistic browser header set, caching
    the raw HTML under `_RAW_DIR` keyed by a slug of the URL so a probe is
    re-analysable offline and re-running it never re-hits the site. Catches
    `requests.RequestException` and returns None after a printed diagnostic
    -- probe access must never raise on a network failure (the whole value
    of `probe()` is recording every page's verdict, including a total block).

    `result`, if given, is a plain dict populated with
    `http_status_or_exception` and `bytes` as a side channel so callers like
    `probe()` can record per-page diagnostics without widening this
    function's own `str | None` return contract.
    """
    cache_path = _RAW_DIR / f"{_slug(url)}.html"
    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="replace")
        if result is not None:
            result["http_status_or_exception"] = "cached"
            result["bytes"] = len(text.encode("utf-8"))
        return text

    try:
        _throttle()
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if result is not None:
            result["http_status_or_exception"] = resp.status_code
        resp.raise_for_status()
        text = resp.text
    except requests.RequestException as exc:
        print(f"  [transfermarkt] fetch failed for {what}: {exc}")
        if result is not None:
            result.setdefault("http_status_or_exception", str(exc))
        return None

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    if result is not None:
        result["bytes"] = len(text.encode("utf-8"))
    return text


# Anti-bot / challenge-page markers checked against a fetched page's raw HTML
# BEFORE any parse is attempted (T-10-05-01) -- an interstitial must never
# parse into an empty-but-valid frame that then reads downstream as "this
# player was never injured", the exact failure mode that would silently
# poison the whole experiment.
_CHALLENGE_PAGE_MARKERS = ("Just a moment", "DataDome", "captcha-delivery", "Attention Required")

# Injury-table column shape per 10-RESEARCH.md Assumption A4 (unverified
# until this probe runs): season, injury type, from, until, days out, games
# missed. Matched by substring against the page's own served header text
# (never by exact name -- Transfermarkt's own label wording is unconfirmed).
_INJURY_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "season": ("season",),
    "injury": ("injury",),
    "from_date": ("from",),
    "until_date": ("until",),
    "days_out": ("days",),
    "games_missed": ("missed", "games"),
}


def _match_injury_columns(columns: list) -> dict[str, str] | None:
    """Map a parsed table's own column labels onto the six-column contract,
    by substring against each label lowered. Returns None if any of the six
    concepts has no matching column -- this table is not the injury table."""
    lowered = {c: str(c).strip().lower() for c in columns}
    mapping: dict[str, str] = {}
    for canonical, aliases in _INJURY_COLUMN_ALIASES.items():
        found = next((col for col, low in lowered.items()
                      if any(alias in low for alias in aliases)), None)
        if found is None:
            return None
        mapping[canonical] = found
    return mapping


def parse_injury_table(html: str, *, what: str) -> pd.DataFrame:
    """Parse a Transfermarkt injury-history page's table into the six-column
    contract `season, injury, from_date, until_date, days_out, games_missed`.

    Raises `ValueError` naming the detected marker if `html` is an anti-bot
    challenge page (T-10-05-01 mitigation) -- checked BEFORE any parse
    attempt. Raises `ValueError` if no table on the page matches the
    expected column shape (T-10-05-03: a schema break must surface loudly,
    not silently produce a wrong or empty frame).
    """
    for marker in _CHALLENGE_PAGE_MARKERS:
        if marker in html:
            raise ValueError(f"{what}: anti-bot challenge page detected (marker: {marker!r})")

    try:
        tables = pd.read_html(io.StringIO(html))
    except ValueError as exc:
        raise ValueError(f"{what}: no HTML tables found ({exc})") from exc

    for table in tables:
        mapping = _match_injury_columns(list(table.columns))
        if mapping is None:
            continue
        out = table.rename(columns={v: k for k, v in mapping.items()})
        return out[list(_INJURY_COLUMN_ALIASES.keys())].copy()

    raise ValueError(
        f"{what}: no table matching the injury-history column shape "
        f"(season/injury/from/until/days/games missed) was found")


def _select_probe_players(n: int) -> pd.DataFrame:
    """Deterministically select the top-n players by `selected_by_percent`
    from the most recent daily snapshot, resolved through the shared
    `data.id_crosswalk.resolve_by_name` identity resolver (Pattern 3 --
    never grow a second name matcher, the FBref many-to-many join
    corruption lesson)."""
    from data import id_crosswalk

    snap_dir = config.ROOT / "data" / "snapshots"
    files = sorted(snap_dir.glob("*.parquet"))
    if not files:
        raise SystemExit(
            "No snapshot files found under data/snapshots/. Run `python -m data.snapshot`.")
    snap = pd.read_parquet(files[-1])
    top = (snap.sort_values("selected_by_percent", ascending=False)
           .head(n)[["name", "player_code"]].reset_index(drop=True))
    top["resolved_player_code"] = id_crosswalk.resolve_by_name(top["name"])
    return top


def _resolve_tm_player_id(name: str) -> str | None:
    """Resolve a player's Transfermarkt id via Transfermarkt's own public
    search endpoint, taking the first player-profile link found. No
    persistent id cache is built here -- that is 10-07's job, and only if
    the checkpoint says go; every probe call re-searches."""
    url = f"{_SEARCH_URL}?query={requests.utils.quote(str(name))}"
    html = _fetch_page(url, what=f"search for {name!r}")
    if html is None:
        return None
    match = _PLAYER_PROFILE_RE.search(html)
    return match.group(1) if match else None


def probe(n: int = 8) -> list[dict]:
    """Bounded, real n-page access probe against transfermarkt.com. Selects
    `n` real players, resolves each to a Transfermarkt player id via their
    search endpoint, fetches that player's injury-history page, and records
    a per-page verdict in `{"ok", "challenge", "http_error", "parse_error",
    "id_unresolved"}`.

    NEVER raises -- a total block must produce `n` `challenge` (or
    `id_unresolved`, if even the search endpoint is blocked) verdicts and a
    clean return, because the whole value of this probe is the verdict
    table, not a successful parse.
    """
    players = _select_probe_players(n)
    rows: list[dict] = []

    for _, player in players.iterrows():
        name = str(player["name"])
        row: dict = {
            "name": name,
            "tm_player_id": None,
            "url": None,
            "http_status_or_exception": None,
            "bytes": None,
            "challenge_marker_detected": None,
            "rows_parsed": 0,
            "verdict": None,
        }

        tm_id = _resolve_tm_player_id(name)
        if tm_id is None:
            row["verdict"] = "id_unresolved"
            rows.append(row)
            continue
        row["tm_player_id"] = tm_id

        url = _INJURY_URL.format(tm_id=tm_id)
        row["url"] = url
        fetch_result: dict = {}
        html = _fetch_page(url, what=f"injury history for {name!r}", result=fetch_result)
        row["http_status_or_exception"] = fetch_result.get("http_status_or_exception")
        row["bytes"] = fetch_result.get("bytes")
        if html is None:
            row["verdict"] = "http_error"
            rows.append(row)
            continue

        try:
            parsed = parse_injury_table(html, what=f"injury history for {name!r}")
            row["rows_parsed"] = len(parsed)
            row["challenge_marker_detected"] = False
            row["verdict"] = "ok"
        except ValueError as exc:
            msg = str(exc)
            row["challenge_marker_detected"] = "anti-bot challenge page detected" in msg
            row["verdict"] = "challenge" if row["challenge_marker_detected"] else "parse_error"
            print(f"  [transfermarkt] {msg}")
        rows.append(row)

    ok = sum(1 for r in rows if r["verdict"] == "ok")
    challenge = sum(1 for r in rows if r["verdict"] == "challenge")
    errors = sum(1 for r in rows if r["verdict"] in ("http_error", "parse_error", "id_unresolved"))
    print(f"[transfermarkt] probe: {ok}/{len(rows)} pages parsed, {challenge} challenged, "
          f"{errors} errored")
    write_json(rows, _PROBE_OUT, indent=2)
    return rows


# --- Plan 10-07: resumable killable backfill + normalized spell table ------

# Committed eight-column contract (must_haves' "data/external/transfermarkt/
# injury_spells.csv"). `season_label` (not `season`) deliberately -- this is
# Transfermarkt's OWN "24/25"-style season label as served, not this
# project's "2024-25" convention, kept verbatim as provenance since the two
# never need to be joined directly (the feature join in `attach` below keys
# purely on `player_code` + date-range overlap, never on season).
_SPELL_COLS = ["player_code", "tm_player_id", "season_label", "injury",
              "from_date", "until_date", "days_out", "games_missed"]

_OUT_CSV = config.DATA_DIR / "external" / "transfermarkt" / "injury_spells.csv"

# Transfermarkt serves injury-history dates as 'DD/MM/YYYY' (verified live
# 2026-09-10 against the 8 real pages plan 10-05's probe already cached under
# data/raw/transfermarkt/) -- NOT the 'Mon D, YYYY' shape this plan's own
# action text assumed (Rule 1 deviation, corrected here after inspecting real
# cached pages rather than guessing).
_TM_DATE_FORMAT = "%d/%m/%Y"

# On-disk-only bookkeeping (never committed -- lives under data/raw/, which
# is wholly gitignored): which player_codes have already been fully
# attempted (success OR failure) this backfill, so a `resume=True` run never
# re-issues a network request for a player already accounted for.
_PROCESSED_LOG = _RAW_DIR / "_processed.csv"

# Flush to disk (spell table + processed log) every N players -- bounds how
# much work a kill can lose. At _MIN_INTERVAL_S=3.0 and two throttled
# requests per player (id-resolution search + injury-history fetch), N=10
# loses at most about a minute (T-10-07-07).
_APPEND_EVERY = 10


def resolve_tm_id(player_code: int, name: str, *, force: bool = False) -> str | None:
    """Resolve `name` to a Transfermarkt player id, cached against
    `player_code` via `data.id_crosswalk.tm_id_cache()`/`write_tm_id_cache_entry`
    (T-10-07-05's dedup discipline, applied to id resolution rather than
    spells). A cache hit (with `force=False`) returns immediately and issues
    ZERO HTTP requests -- a second call for the same player never re-searches
    (T-10-07-01's own acceptance criterion). A miss issues one throttled
    search request via the shared `_resolve_tm_player_id` helper (plan
    10-05's own search-endpoint lookup, never a second name matcher --
    10-RESEARCH.md Pattern 3), writes the cache (including a `None` result,
    so an unresolvable name is not re-searched every run either), and prints
    a one-line resolution record for human eyeball (the SUMMARY's required
    sample of 10).
    """
    from data import id_crosswalk

    cache = id_crosswalk.tm_id_cache()
    if not force and player_code in cache:
        cached = cache[player_code]
        return None if pd.isna(cached) else str(cached)

    tm_id = _resolve_tm_player_id(name)
    id_crosswalk.write_tm_id_cache_entry(player_code, tm_id)
    print(f"  [transfermarkt] resolved {name!r} (player_code={player_code}) -> "
          f"tm_id={tm_id!r}")
    return tm_id


def _parse_tm_date(s: pd.Series) -> pd.Series:
    """Parse a Transfermarkt date column ('23/09/2024', or '-'/blank for an
    ongoing spell's `until_date`) to `datetime64`. Anything that doesn't
    match `_TM_DATE_FORMAT` becomes `NaT` -- never silently admitted."""
    cleaned = s.astype(str).str.strip().replace({"-": None, "nan": None,
                                                  "": None, "None": None})
    return pd.to_datetime(cleaned, format=_TM_DATE_FORMAT, errors="coerce")


def _parse_days_out(s: pd.Series) -> pd.Series:
    """'5 days' -> 5; '-'/blank/unparsable -> <NA>."""
    extracted = s.astype(str).str.extract(r"(\d+)", expand=False)
    return pd.to_numeric(extracted, errors="coerce").astype("Int64")


def _parse_games_missed(s: pd.Series) -> pd.Series:
    """An int already, or the literal '-' for a still-ongoing spell -> <NA>."""
    cleaned = s.astype(str).str.strip().replace({"-": None, "nan": None})
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def _normalize_spells(parsed: pd.DataFrame, *, player_code: int,
                      tm_player_id: str) -> tuple[pd.DataFrame, int]:
    """Normalize one player's raw `parse_injury_table` output to the
    committed eight-column contract. Drops (with a counted return value, so
    the caller can print a warning) any row whose `from_date` will not parse,
    rather than admitting `NaT` into a date-range comparison (T-10-07-03).
    Deduplicates on `(player_code, from_date)` (T-10-07-05).
    """
    out = pd.DataFrame({
        "player_code": int(player_code),
        "tm_player_id": str(tm_player_id),
        "season_label": parsed["season"].astype(str),
        "injury": parsed["injury"].astype(str),
        "from_date": _parse_tm_date(parsed["from_date"]),
        "until_date": _parse_tm_date(parsed["until_date"]),
        "days_out": _parse_days_out(parsed["days_out"]),
        "games_missed": _parse_games_missed(parsed["games_missed"]),
    })
    bad = out["from_date"].isna()
    n_dropped = int(bad.sum())
    out = out.loc[~bad].copy()
    out["from_date"] = out["from_date"].dt.date
    out["until_date"] = out["until_date"].dt.date
    out = out.drop_duplicates(subset=["player_code", "from_date"])
    return out[_SPELL_COLS], n_dropped


def _load_spells_raw() -> pd.DataFrame:
    """The committed spell table exactly as stored on disk (string/object
    dtypes), or an empty frame with the right columns if absent."""
    if not _OUT_CSV.exists():
        return pd.DataFrame(columns=_SPELL_COLS)
    return pd.read_csv(_OUT_CSV)


def _append_spells(frames: list[pd.DataFrame]) -> None:
    """Append newly-normalized spell frames to the committed CSV, re-applying
    the `(player_code, from_date)` dedup across the WHOLE table (not just the
    new batch) so a resumed run can never double-count a spell
    (T-10-07-05)."""
    if not frames:
        return
    new = pd.concat(frames, ignore_index=True)
    existing = _load_spells_raw()
    combined = pd.concat([existing, new], ignore_index=True)
    combined["from_date"] = pd.to_datetime(combined["from_date"]).dt.date
    combined["until_date"] = pd.to_datetime(combined["until_date"], errors="coerce").dt.date
    combined = combined.drop_duplicates(subset=["player_code", "from_date"], keep="last")
    combined = combined.sort_values(["player_code", "from_date"]).reset_index(drop=True)
    _OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(_OUT_CSV, index=False)


def _load_processed() -> pd.DataFrame:
    if _PROCESSED_LOG.exists():
        return pd.read_csv(_PROCESSED_LOG)
    return pd.DataFrame(columns=["player_code", "status", "n_spells"])


def _record_processed(rows: list[dict]) -> None:
    if not rows:
        return
    existing = _load_processed()
    combined = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    combined = combined.drop_duplicates(subset="player_code", keep="last")
    _PROCESSED_LOG.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(_PROCESSED_LOG, index=False)


def build(*, resume: bool = True, seasons: list[str] | None = None,
         force: bool = False) -> pd.DataFrame:
    """Resumable, killable full injury-history backfill (plan 10-07,
    authorised by plan 10-05's checkpoint decision A: all seasons 2016-17+,
    background killable job). Deliberate, human-run, network-using step --
    NEVER wired into cron or CI. Safe to kill: HTML pages are cached per-URL
    by `_fetch_page`, resolved ids are cached per-`player_code` by
    `resolve_tm_id`, and a player already recorded in the on-disk
    `_processed.csv` log (gitignored, under `data/raw/transfermarkt/`) is
    skipped entirely on the next `resume=True` run -- a kill loses at most
    `_APPEND_EVERY` players' worth of work.

    Enumerates the distinct `(player_code, name)` pairs from
    `data/processed/player_gw.parquet`, restricted to `seasons` (default:
    every `config.SEASONS` -- the full authorised scope; do not widen beyond
    what plan 10-05's checkpoint authorised). For each: resolve a
    Transfermarkt id (`resolve_tm_id`), fetch their injury-history page
    (`_fetch_page`), parse it (`parse_injury_table`), normalize
    (`_normalize_spells`), and append incrementally to the committed spell
    table. A challenge-page `ValueError`, a `requests.RequestException`, or a
    parse failure increments the failure counter and continues -- one bad
    page never ends a multi-hour run (T-10-07-07). A player whose id never
    resolves, or whose fetch/parse fails, is recorded in `_processed.csv` too
    (so a plain `resume=True` run does not retry it forever); pass
    `--force`/`force=True` to retry everyone, including prior failures.
    """
    if not TRANSFERMARKT_ENABLED:
        print("  [transfermarkt] disabled (TRANSFERMARKT_ENABLED=False)")
        return pd.DataFrame(columns=_SPELL_COLS)

    target_seasons = list(seasons) if seasons else list(config.SEASONS)
    pg = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                         columns=["season", "player_code", "name"])
    pg = pg[pg["season"].isin(target_seasons)]
    players = (pg.drop_duplicates(subset="player_code")[["player_code", "name"]]
              .sort_values("player_code").reset_index(drop=True))

    processed = _load_processed()
    done_codes = set(processed["player_code"]) if (resume and not force) else set()
    n_failed = int((processed["status"] == "failed").sum()) if not processed.empty else 0

    total = len(players)
    n_spells_total = len(_load_spells_raw())
    n_skipped = 0
    processed_this_run = 0
    buffer_frames: list[pd.DataFrame] = []
    log_rows: list[dict] = []
    t0 = time.monotonic()

    for row in players.itertuples(index=False):
        player_code = int(row.player_code)
        name = str(row.name)

        if player_code in done_codes:
            n_skipped += 1
            continue

        status = "failed"
        n_new_spells = 0
        try:
            tm_id = resolve_tm_id(player_code, name)
            if tm_id is None:
                raise ValueError(f"{name!r}: id not resolved")
            url = _INJURY_URL.format(tm_id=tm_id)
            html = _fetch_page(url, what=f"injury history for {name!r} "
                                          f"(player_code={player_code})")
            if html is None:
                raise ValueError(f"{name!r}: fetch failed")
            parsed = parse_injury_table(
                html, what=f"injury history for {name!r} (player_code={player_code})")
            norm, n_dropped = _normalize_spells(parsed, player_code=player_code,
                                                tm_player_id=tm_id)
            if n_dropped:
                print(f"  [transfermarkt] dropped {n_dropped} unparsable-date "
                      f"row(s) for {name!r} (player_code={player_code})")
            if not norm.empty:
                buffer_frames.append(norm)
            n_new_spells = len(norm)
            status = "ok"
        except (ValueError, requests.RequestException) as exc:
            print(f"  [transfermarkt] failed for {name!r} (player_code={player_code}): {exc}")
            n_failed += 1

        n_spells_total += n_new_spells
        processed_this_run += 1
        log_rows.append({"player_code": player_code, "status": status,
                         "n_spells": n_new_spells})

        if len(log_rows) >= _APPEND_EVERY:
            _append_spells(buffer_frames)
            _record_processed(log_rows)
            buffer_frames, log_rows = [], []

        n_done_total = len(done_codes) + processed_this_run
        remaining = max(0, total - n_done_total)
        elapsed = time.monotonic() - t0
        rate = elapsed / processed_this_run if processed_this_run else 0.0
        eta_min = (remaining * rate) / 60.0
        print(f"[transfermarkt] {n_done_total}/{total} players, "
              f"{n_spells_total} spells, {n_failed} failed, eta {eta_min:.0f}m")

    if buffer_frames or log_rows:
        _append_spells(buffer_frames)
        _record_processed(log_rows)

    if n_skipped:
        print(f"[transfermarkt] resumed: skipped {n_skipped} already-processed player(s)")

    loaded = load_transfermarkt()
    return loaded if loaded is not None else pd.DataFrame(columns=_SPELL_COLS)


def load_transfermarkt() -> pd.DataFrame | None:
    """Return the committed normalized injury-spell table, or `None` when
    absent -- matching `data/fotmob.py::load_fotmob`'s no-op-if-absent
    contract. Never raises."""
    if not _OUT_CSV.exists():
        return None
    df = pd.read_csv(_OUT_CSV)
    df["from_date"] = pd.to_datetime(df["from_date"], errors="coerce")
    df["until_date"] = pd.to_datetime(df["until_date"], errors="coerce")
    return df


# --- Plan 10-07 Task 2: injury-spell overlap join ---------------------------

def _covered_player_codes() -> set[int]:
    """`player_code` values with a RESOLVED Transfermarkt id -- the id map's
    OWN membership, not the spell table's. This is the line that
    distinguishes a covered player with zero recorded spells (genuinely not
    injured -- 0.0) from a player whose identity never resolved (genuinely
    unknown -- NaN); stated once here so `attach` doesn't have to re-derive
    it (T-10-07's own must_have)."""
    from data import id_crosswalk

    cache = id_crosswalk.tm_id_cache()
    return {int(pc) for pc, tid in cache.items()
           if pd.notna(tid) and str(tid).strip() not in ("", "None")}


def injury_status_as_of(spells: pd.DataFrame, player_code: int, as_of) -> dict:
    """Point-in-time injury status for `player_code` as of `as_of` (a
    gameweek's deadline, never the fixture kickoff -- 10-RESEARCH.md's Code
    Examples sketch). A spell is active when `from_date <= as_of` and either
    `until_date` is null (an ONGOING spell counts as active for any `as_of`
    at or after its `from_date`) or `until_date >= as_of`. Returns
    `{"injured": False, "days_out_so_far": 0}` when no spell is active.
    """
    spells = spells[spells["player_code"] == player_code]
    active = spells[(spells["from_date"] <= as_of)
                    & (spells["until_date"].isna() | (spells["until_date"] >= as_of))]
    if active.empty:
        return {"injured": False, "days_out_so_far": 0}
    row = active.sort_values("from_date").iloc[-1]
    return {"injured": True, "days_out_so_far": (as_of - row["from_date"]).days}


def _to_naive_utc(s: pd.Series) -> pd.Series:
    """Normalize a timestamp-like Series to naive UTC `datetime64[ns]` so
    numpy broadcasting arithmetic below never has to reason about tz."""
    return pd.to_datetime(s, utc=True, errors="coerce").dt.tz_localize(None)


def attach(full: pd.DataFrame) -> pd.DataFrame:
    """Left-join the four `config.INJURY_COLS` injury features onto a
    player_gw-shaped frame by DATE-RANGE OVERLAP against each gameweek's
    deadline (`data.availability.gw_deadlines()`, reused -- one definition,
    one place). No-op if the kill switch is off, or if neither the id map
    nor the spell table exist -- optional enrichment must never break the
    pipeline. Preserves `full`'s row count exactly (`AssertionError`
    otherwise) and prints a coverage line naming both the id-resolved
    fraction and the active-spell rate among resolved rows.

    NOT YET WIRED into `data/build_table.py`'s pipeline rebuild -- that
    lands in **plan 10-08 Task 1**, which owns that file (this plan's own
    file set does not include it). This function is exercised directly
    against a real `player_gw.parquet` frame in this plan's own `<verify>`,
    which proves the join is correct without needing the wiring commit. A
    reader who finds `tm_*` columns absent from a real `features.parquet`
    before 10-08 lands should read that as deliberate sequencing, not a bug.
    """
    if not TRANSFERMARKT_ENABLED:
        return full

    covered = _covered_player_codes()
    spells = load_transfermarkt()
    if not covered and spells is None:
        return full

    need = ["season", "gw", "player_code"]
    missing = [c for c in need if c not in full.columns]
    if missing:
        raise AssertionError(f"attach(): full is missing required columns {missing}")

    before = len(full)
    from data.availability import gw_deadlines

    deadlines = gw_deadlines()[["season", "gw", "deadline_ts"]].drop_duplicates(
        subset=["season", "gw"])

    out = full.copy()
    for col in config.INJURY_COLS:
        out[col] = np.nan

    merged_dl = out[need].merge(deadlines, on=["season", "gw"], how="left")
    if len(merged_dl) != before:
        raise AssertionError(
            f"transfermarkt injury join changed row count {before} -> {len(merged_dl)}")
    deadline_ts = _to_naive_utc(merged_dl["deadline_ts"]).to_numpy()

    covered_mask = out["player_code"].astype("Int64").isin(covered).to_numpy()
    out.loc[covered_mask, "tm_injured"] = 0.0
    out.loc[covered_mask, "tm_days_out_so_far"] = 0.0
    out.loc[covered_mask, "tm_spells_prior_365d"] = 0.0
    out.loc[covered_mask, "tm_days_out_prior_365d"] = 0.0

    if spells is not None and not spells.empty:
        spells = spells.dropna(subset=["player_code", "from_date"]).copy()
        spells["player_code"] = spells["player_code"].astype("Int64")
        spells["from_date"] = _to_naive_utc(spells["from_date"])
        spells["until_date"] = _to_naive_utc(spells["until_date"])

        col_injured = out.columns.get_loc("tm_injured")
        col_days_so_far = out.columns.get_loc("tm_days_out_so_far")
        col_spells_365 = out.columns.get_loc("tm_spells_prior_365d")
        col_days_365 = out.columns.get_loc("tm_days_out_prior_365d")

        for player_code, sp in spells.groupby("player_code"):
            rows_mask = (out["player_code"].astype("Int64") == player_code).to_numpy()
            idx = np.flatnonzero(rows_mask)
            if idx.size == 0:
                continue
            as_of = deadline_ts[idx]
            valid = ~pd.isna(as_of)
            if not valid.any():
                continue
            idx = idx[valid]
            as_of = as_of[valid][:, None]                      # (N, 1)

            from_arr = sp["from_date"].to_numpy()[None, :]     # (1, M)
            until_arr = sp["until_date"].to_numpy()[None, :]   # (1, M)
            until_nat = pd.isna(until_arr)

            active = (as_of >= from_arr) & (until_nat | (as_of <= until_arr))
            injured = active.any(axis=1)
            # Matches injury_status_as_of's own "latest active spell wins"
            # tie-break (sort_values("from_date").iloc[-1]): among active
            # spells the one with the LATEST from_date -- i.e. the SMALLEST
            # days-since-start -- is the one reported, so a rare pair of
            # overlapping spells doesn't silently disagree with the scalar
            # reference implementation the leakage test also exercises.
            days_since_start = (as_of - from_arr) / np.timedelta64(1, "D")
            days_out_so_far = np.where(active, days_since_start, np.inf).min(axis=1)
            days_out_so_far = np.where(injured, days_out_so_far, 0.0)

            window_start = as_of - np.timedelta64(365, "D")
            prior = (from_arr < as_of) & (from_arr >= window_start)
            n_prior = prior.sum(axis=1)

            until_filled = np.where(until_nat, as_of, until_arr)
            effective_end = np.minimum(as_of, until_filled)
            days_per_spell = np.clip((effective_end - from_arr) / np.timedelta64(1, "D"), 0, None)
            days_out_prior = np.where(prior, days_per_spell, 0.0).sum(axis=1)

            out.iloc[idx, col_injured] = injured.astype(float)
            out.iloc[idx, col_days_so_far] = days_out_so_far
            out.iloc[idx, col_spells_365] = n_prior.astype(float)
            out.iloc[idx, col_days_365] = days_out_prior

    resolved_cov = float(covered_mask.mean()) if len(covered_mask) else 0.0
    injured_rate = (float(out.loc[covered_mask, "tm_injured"].mean())
                    if covered_mask.any() else 0.0)
    print(f"  [transfermarkt] joined; id-resolved coverage {resolved_cov:.1%}, "
          f"active-spell rate (of resolved) {injured_rate:.1%}")
    return out


def _figshare_article_detail(article_id: int) -> dict | None:
    """Fetch one figshare article's detail payload (license, files, dates).
    Returns None on any failure -- this is a bounded discovery check, not a
    pipeline dependency, so a single unreachable hit must never abort the
    whole scan."""
    try:
        resp = requests.get(_FIGSHARE_ARTICLE_URL.format(article_id=article_id),
                             headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"  [transfermarkt] figshare article {article_id} detail fetch failed: {exc}")
        return None


# Anti-bot / challenge-page markers checked against BOTH a candidate file
# sample's body and its response headers -- discovered live against this
# exact dataset (id=32351964): every ndownloader.figshare.com file download
# from this machine returned HTTP 202, `Content-Type: text/html`, and an
# `x-amzn-waf-action: challenge` header instead of real file bytes. An
# earlier version of this function sampled the first (image) file and
# matched "en" fragments inside the WAF's JS challenge body against a naive
# EPL-keyword check, producing a false USABLE verdict -- fixed by requiring
# BOTH a real-looking content-type AND no challenge marker before trusting
# a sample's content at all (Rule 1 bug fix, found running this task).
_CHALLENGE_MARKERS = ("Just a moment", "DataDome", "captcha-delivery",
                      "Attention Required", "awsWafCookieDomainList")


def _pick_data_file(files: list[dict]) -> dict | None:
    """Prefer a text/data file (csv/tsv/txt/json) over an image -- the first
    file in a figshare article's file list is not necessarily the data
    table (this dataset's own file list starts with PNG figures)."""
    data_files = [f for f in files
                  if f.get("name", "").lower().endswith((".csv", ".tsv", ".txt", ".json"))]
    candidates = data_files or files
    return candidates[0] if candidates else None


def _figshare_sample_first_file(files: list[dict]) -> tuple[str | None, str]:
    """Fetch only the first ~64KB of a data file so the column set and
    season/league coverage are visible without a full download. Returns
    `(None, reason)` on any failure, unreachable content, or a detected
    anti-bot challenge page -- never raises (this is a bounded discovery
    check, not a pipeline dependency)."""
    target = _pick_data_file(files)
    if target is None:
        return None, "no files listed"
    dl_url = target.get("download_url")
    if not dl_url:
        return None, f"{target.get('name')}: no download_url"
    try:
        _throttle()
        resp = requests.get(dl_url, headers={**HEADERS, "Range": "bytes=0-65535"},
                             timeout=TIMEOUT, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        waf_action = resp.headers.get("x-amzn-waf-action", "")
        chunk = next(resp.iter_content(chunk_size=65536), b"")
        text = chunk.decode("utf-8", errors="replace")
    except requests.RequestException as exc:
        return None, f"{target.get('name')}: fetch failed: {exc}"
    if waf_action:
        return None, (f"{target.get('name')}: blocked by an anti-bot challenge "
                      f"(x-amzn-waf-action={waf_action!r}, status={resp.status_code})")
    if any(marker in text for marker in _CHALLENGE_MARKERS):
        return None, f"{target.get('name')}: response body contains an anti-bot challenge marker"
    if "text/html" in content_type.lower() and not target.get("name", "").lower().endswith(".html"):
        return None, (f"{target.get('name')}: expected a data file but got "
                      f"Content-Type={content_type!r} (likely an interstitial page)")
    return text, ""


def figshare_check() -> str:
    """Bounded (~10min) check of the figshare "Injuries from Transfermarkt.com"
    pre-scraped dataset (10-RESEARCH.md Open Question 2) -- could remove the
    entire scraper need. Prints one of three explicit verdict lines and
    returns the verdict token; never raises (a 403 here is an expected,
    recorded outcome, not a task failure -- this session's own prior research
    pass got exactly that)."""
    try:
        _throttle()
        resp = requests.post(_FIGSHARE_SEARCH_URL,
                              json={"search_for": "Injuries from Transfermarkt"},
                              headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        hits = resp.json()
    except requests.RequestException as exc:
        print(f"[transfermarkt] figshare: UNREACHABLE — {exc}")
        return "UNREACHABLE"

    if not hits:
        print("[transfermarkt] figshare: INSUFFICIENT — no matching articles found")
        return "INSUFFICIENT"

    reasons: list[str] = []
    for hit in hits:
        article_id = hit.get("id")
        title = hit.get("title")
        detail = _figshare_article_detail(article_id) if article_id is not None else None
        if detail is None:
            reasons.append(f"id={article_id}: detail fetch failed")
            continue
        license_name = (detail.get("license") or {}).get("name", "unknown")
        pub_date = detail.get("published_date", "unknown")
        files = detail.get("files", [])
        print(f"  [transfermarkt] figshare hit: id={article_id} title={title!r} "
              f"license={license_name} published={pub_date}")
        for f in files:
            print(f"    file: {f.get('name')} ({f.get('size')} bytes)")
        sample, reason = _figshare_sample_first_file(files)
        if sample is None:
            print(f"    sample unavailable: {reason}")
            reasons.append(f"id={article_id} ({title}): {reason}")
            continue
        lines = sample.splitlines()
        header = lines[0] if lines else ""
        print(f"    header: {header}")
        for row in lines[1:3]:
            print(f"    sample row: {row}")
        lower = sample.lower()
        if "epl" in lower or "premier league" in lower or "england" in lower:
            print(f"[transfermarkt] figshare: USABLE — covers EPL (header/sample match), "
                  f"license {license_name}")
            return "USABLE"
        reasons.append(f"id={article_id} ({title}): sampled, no EPL/Premier League/England "
                       "match in header or first rows")

    reason_str = "; ".join(reasons) if reasons else "no reachable hit confirmed EPL coverage"
    print(f"[transfermarkt] figshare: INSUFFICIENT — {reason_str}")
    return "INSUFFICIENT"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figshare-check", action="store_true",
                     help="check the figshare pre-scraped injury dataset (~10min, no scraper)")
    ap.add_argument("--probe", action="store_true",
                     help="run a bounded real-page access probe against transfermarkt.com")
    ap.add_argument("--n", type=int, default=8, help="number of players to probe (default 8)")
    ap.add_argument("--build", action="store_true",
                     help="run the full injury-history backfill (plan 10-07, authorised "
                          "scope: all config.SEASONS). Deliberate, human-run, "
                          "network-using step -- NEVER wired into cron or CI. Safe to "
                          "kill: resumable via cached HTML pages, the tm_id cache, and "
                          "the committed spell table.")
    ap.add_argument("--resume", dest="resume", action="store_true", default=True,
                     help="skip already-processed players (default)")
    ap.add_argument("--no-resume", dest="resume", action="store_false",
                     help="re-attempt every player, including prior failures")
    ap.add_argument("--seasons", type=str, default=None,
                     help="comma-separated season list to restrict --build to "
                          "(default: every config.SEASONS -- the full authorised scope; "
                          "do not widen beyond what plan 10-05's checkpoint authorised)")
    ap.add_argument("--force", action="store_true",
                     help="--build only: ignore the tm_id cache too, re-resolve every id")
    args = ap.parse_args(argv)

    if args.figshare_check:
        figshare_check()
        return 0
    if args.probe:
        probe(n=args.n)
        return 0
    if args.build:
        seasons = [s.strip() for s in args.seasons.split(",")] if args.seasons else None
        out = build(resume=args.resume, seasons=seasons, force=args.force)
        print(f"[transfermarkt] build complete: {len(out):,} spells, "
              f"{out['player_code'].nunique() if not out.empty else 0} players covered")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
