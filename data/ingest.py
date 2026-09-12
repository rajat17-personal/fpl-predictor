"""Phase 1 ingestion: download raw data and cache it locally.

Sources (all free):
  - Official FPL API                -> the CURRENT season's per-player per-gameweek
    rows, captured by `data.gw_capture` (NOT this module -- see below), plus live
    players/teams/fixtures for inference (`fetch_fpl_live`, unchanged by Phase 8).
  - vaastav/Fantasy-Premier-League  -> the PAST seasons' merged_gw.csv, fixtures.csv
    and players_raw.csv (the training set), cached here and never re-fetched for
    the current season.

`fetch_vaastav_season` declines to download `config.CURRENT_SEASON`'s three files
under any flag, including `--force`: vaastav's own copy of the current season
stalled at a single published gameweek (confirmed 2026-09-08,
.planning/research/DATA-SOURCE-RESILIENCE.md), so `data.gw_capture` now owns
those three on-disk paths outright, and the re-download flag's whole effect on
the current season would be to replace a full multi-gameweek capture with the
one gameweek the stalled source still serves. Pass `cross_check=True` to fetch
the published current-season copy anyway, written to a distinguishable filename
alongside the captured one -- never over it -- for verifying the capture
module's own schema mapping against an independent source (the check Phase 8
plan 08-03 hand-rolled outside the repository).

Run:
  python -m data.ingest              # download configured seasons + live API
  python -m data.ingest --force      # re-download cached PAST seasons (current season still skipped)
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
def _crosscheck_path(dest: Path) -> Path:
    """The distinguishable filename `fetch_vaastav_season`'s `cross_check`
    escape hatch writes to -- same directory as the captured file, never the
    captured file's own path."""
    return dest.with_name(f"{dest.stem}.vaastav-crosscheck{dest.suffix}")


def fetch_vaastav_season(season: str, *, force: bool = False,
                          cross_check: bool = False) -> dict[str, Path | None | str]:
    """Download merged_gw.csv + fixtures.csv + players_raw.csv for one season.

    `config.CURRENT_SEASON` is owned by `data.gw_capture`, not this function:
    every download for that season is skipped here, regardless of `force` --
    see the module docstring for why. The returned dict keeps the same three
    keys callers already rely on (`main`'s loop, in particular); the skipped
    season's values record the skip rather than a downloaded path.

    Pass `cross_check=True` to fetch the published current-season copy
    anyway, written to a `.vaastav-crosscheck`-suffixed filename in the same
    season directory rather than the path `data.gw_capture` owns. Has no
    effect for a past season, which is always fetched to its normal path.
    """
    print(f"[vaastav] {season}")
    is_current = season == config.CURRENT_SEASON

    dests = {
        "merged_gw": config.RAW_DIR / season / "merged_gw.csv",
        "fixtures": config.RAW_DIR / season / "fixtures.csv",
        # players_raw.csv carries both season-local `id` and the stable global
        # `code`, giving us the (season, element) -> code mapping used across
        # seasons + live.
        "players_raw": config.RAW_DIR / season / "players_raw.csv",
    }
    urls = {
        "merged_gw": f"{config.VAASTAV_RAW}/{season}/gws/merged_gw.csv",
        "fixtures": f"{config.VAASTAV_RAW}/{season}/fixtures.csv",
        "players_raw": f"{config.VAASTAV_RAW}/{season}/players_raw.csv",
    }

    if is_current and not cross_check:
        out: dict[str, Path | None | str] = {}
        for key, dest in dests.items():
            print(f"  SKIP     {dest.relative_to(config.ROOT)} -- {season} is the current "
                  "season, owned by data.gw_capture (vaastav's own copy stalled at one gameweek)")
            out[key] = f"skipped: {season} owned by data.gw_capture"
        return out

    out = {}
    for key, dest in dests.items():
        target = _crosscheck_path(dest) if (is_current and cross_check) else dest
        out[key] = _download(urls[key], target, force=force)

    if not is_current:
        missing = [key for key in dests if out[key] is None]
        if missing:
            names = ", ".join(dests[key].name for key in missing)
            print(f"[ingest] WARNING season {season}: {len(missing)} file(s) came back absent "
                  f"from vaastav -- {names}. A previously-served past season has vanished; "
                  "check whether the upstream repo still publishes it.")

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
