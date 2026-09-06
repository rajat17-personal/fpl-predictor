"""Phase 1 ingestion: download raw data and cache it locally.

Sources (all free):
  - vaastav/Fantasy-Premier-League  -> historical per-GW CSVs (training set)
  - Official FPL API                -> live players/teams/fixtures (inference)

Run:
  python -m data.ingest              # download configured seasons + live API
  python -m data.ingest --force      # re-download even if cached
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

import config

HEADERS = {"User-Agent": "fpl-ml-project/0.1 (data ingestion)"}
TIMEOUT = 30


def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def _download(url: str, dest: Path, *, force: bool = False, binary: bool = False) -> Path | None:
    """Download `url` to `dest`, skipping if already cached. Returns path or None."""
    if dest.exists() and not force:
        print(f"  cached   {dest.relative_to(config.ROOT)}")
        return dest
    try:
        resp = _get(url)
    except requests.HTTPError as exc:
        print(f"  MISS     {url} ({exc.response.status_code})")
        return None
    except requests.RequestException as exc:
        print(f"  ERROR    {url} ({exc})")
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content) if binary else dest.write_text(resp.text, encoding="utf-8")
    print(f"  saved    {dest.relative_to(config.ROOT)} ({len(resp.content):,} bytes)")
    return dest


# --- vaastav historical -----------------------------------------------------
def fetch_vaastav_season(season: str, *, force: bool = False) -> dict[str, Path | None]:
    """Download merged_gw.csv + fixtures.csv for one season."""
    print(f"[vaastav] {season}")
    out: dict[str, Path | None] = {}
    out["merged_gw"] = _download(
        f"{config.VAASTAV_RAW}/{season}/gws/merged_gw.csv",
        config.RAW_DIR / season / "merged_gw.csv",
        force=force,
    )
    out["fixtures"] = _download(
        f"{config.VAASTAV_RAW}/{season}/fixtures.csv",
        config.RAW_DIR / season / "fixtures.csv",
        force=force,
    )
    # players_raw.csv carries both season-local `id` and the stable global `code`,
    # giving us the (season, element) -> code mapping used across seasons + live.
    out["players_raw"] = _download(
        f"{config.VAASTAV_RAW}/{season}/players_raw.csv",
        config.RAW_DIR / season / "players_raw.csv",
        force=force,
    )
    return out


# --- live FPL API -----------------------------------------------------------
def fetch_fpl_live(*, force: bool = False) -> dict[str, Path | None]:
    """Download current bootstrap-static (players/teams/positions) + fixtures."""
    print("[fpl-api] live")
    out: dict[str, Path | None] = {}
    out["bootstrap"] = _download(
        f"{config.FPL_API}/bootstrap-static/",
        config.RAW_DIR / "live" / "bootstrap-static.json",
        force=force,
    )
    out["fixtures"] = _download(
        f"{config.FPL_API}/fixtures/",
        config.RAW_DIR / "live" / "fixtures.json",
        force=force,
    )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest FPL raw data.")
    ap.add_argument("--force", action="store_true", help="re-download cached files")
    ap.add_argument("--seasons", nargs="*", default=config.SEASONS,
                    help="seasons to fetch (default: config.SEASONS)")
    ap.add_argument("--no-live", action="store_true", help="skip live FPL API")
    args = ap.parse_args(argv)

    for season in args.seasons:
        fetch_vaastav_season(season, force=args.force)
        time.sleep(0.3)  # be polite to GitHub raw

    if not args.no_live:
        fetch_fpl_live(force=args.force)

    print("\nDone. Next: python -m data.build_table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
