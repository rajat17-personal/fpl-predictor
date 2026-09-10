"""Transfermarkt injury-history access probe (plan 10-05).

Two-plan spike-first contract: this module is built across TWO plans, not
one. Plan 10-05 (this plan) ONLY probes access -- a figshare pre-scraped
-dataset shortcut check, then a bounded real-page access probe and a
one-page HTML parser -- and records a go/no-go verdict in IMPROVEMENTS.md.
Plan 10-07 adds the bulk 6-season backfill, normalization, and join, and
ONLY if this plan's checkpoint decision says go (D-06/D-07). A reader who
finds this module with no `build()`/bulk-loop/`attach()` should read that as
deliberate scope, not as an abandoned fetcher -- mirroring Phase 9's
fbref_v2 not-acquirable precedent (IMPROVEMENTS.md).

Why the extra caution: 10-RESEARCH.md's own evidence on Transfermarkt access
is genuinely contradictory (some 2026 guides say plain `requests` + a
User-Agent works; others describe DataDome JA3/HTTP-2 fingerprinting that
blocks bare `requests`), and `worldfootballR` -- the reference implementation
the originating todo cites -- has been archived read-only since 2025-09-18.
Phase 9 spent three real Chrome spike attempts on FBref before recording it
as not-acquirable (IMPROVEMENTS.md's `### fbref_v2` entry); paying a bounded
probe FIRST, before any fetcher infrastructure, is the whole lesson of that
entry (D-04).

Run:
  python -m data.transfermarkt --figshare-check   # ~10min: does a pre-scraped
                                                     # dataset make the scraper unnecessary?
  python -m data.transfermarkt --probe --n 8       # 8-page real access probe (plan 10-05 Task 2)
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import time

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
    args = ap.parse_args(argv)

    if args.figshare_check:
        figshare_check()
        return 0
    if args.probe:
        probe(n=args.n)
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
