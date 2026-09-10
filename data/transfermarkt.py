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
import sys
import time

import requests

import config

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

_FIGSHARE_SEARCH_URL = "https://api.figshare.com/v2/articles/search"
_FIGSHARE_ARTICLE_URL = "https://api.figshare.com/v2/articles/{article_id}"

_last_call_ts = 0.0


def _throttle() -> None:
    """Block until at least `_MIN_INTERVAL_S` has elapsed since the last call."""
    global _last_call_ts
    now = time.monotonic()
    wait = _MIN_INTERVAL_S - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()


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
    args = ap.parse_args(argv)

    if args.figshare_check:
        figshare_check()
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
