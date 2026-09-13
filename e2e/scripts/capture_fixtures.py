"""Capture (and verify) the immutable v1 "normal" E2E fixture set.

Freezes one real gameweek of both the FPL-upstream payloads `api/main.py`'s
fixture-mode seam reads from disk (`FPL_FIXTURE_DIR`) and the `web/data/*.json`
product export, so `/api` and `/data` describe one coherent gameweek universe
(D-07). The captured pool is the real model's output at capture time (D-10) —
fixture mode never re-runs model inference, it replays this frozen pool.

v1 is immutable once committed: a contract change cuts v2 alongside it, never
edits v1 in place (see MANIFEST.md).

Run:
  python e2e/scripts/capture_fixtures.py              # capture (writes the set)
  python e2e/scripts/capture_fixtures.py --verify      # verify the committed set
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

import config  # noqa: E402
from ops.jsonio import read_json, write_json  # noqa: E402
from predict.export import (build_captains, build_chips, build_meta,  # noqa: E402
                            build_squad, build_standings, build_table,
                            build_ticker, build_leaders)
from predict.live import _gw_pool, _next_gw  # noqa: E402

ENTRY = 6980093
POOL_HORIZON = 6
FIXTURE_ROOT = _REPO_ROOT / "e2e" / "fixtures" / "v1" / "normal"
API_DIR = FIXTURE_ROOT / "api"
WEB_DATA_DIR = FIXTURE_ROOT / "web-data"
MANIFEST_PATH = _REPO_ROOT / "e2e" / "fixtures" / "v1" / "MANIFEST.md"
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}

BOOTSTRAP_ELEMENT_KEEP = [
    "id", "code", "web_name", "team", "element_type", "now_cost", "status",
    "chance_of_playing_next_round", "selected_by_percent", "ep_next", "news",
]
BOOTSTRAP_EVENT_KEEP = ["id", "is_next", "finished", "deadline_time"]
BOOTSTRAP_TEAM_KEEP = ["id", "name", "short_name"]
FIXTURE_KEEP = ["event", "team_h", "team_a", "kickoff_time", "finished",
                "team_h_difficulty", "team_a_difficulty"]
PICKS_PICK_KEEP = ["element"]
PICKS_HISTORY_KEEP = ["bank", "value"]
SUMMARY_KEEP = ["name", "player_first_name", "player_last_name",
                "summary_overall_points", "summary_overall_rank",
                "summary_event_points"]
HISTORY_CHIP_KEEP = ["name", "event"]
HISTORY_CURRENT_KEEP = ["event", "event_transfers"]

REQUIRED_POOL_KEYS = {"player_code", "name", "team", "position", "price_m",
                      "xp", "xp_capt"}


def _trim_bootstrap(boot: dict) -> dict:
    return {
        "total_players": boot["total_players"],
        "events": [{k: e.get(k) for k in BOOTSTRAP_EVENT_KEEP} for e in boot["events"]],
        "teams": [{k: t.get(k) for k in BOOTSTRAP_TEAM_KEEP} for t in boot["teams"]],
        "elements": [{k: el.get(k) for k in BOOTSTRAP_ELEMENT_KEEP}
                    for el in boot["elements"]],
    }


def _trim_fixtures(fixtures: list) -> list:
    return [{k: f.get(k) for k in FIXTURE_KEEP} for f in fixtures]


def _trim_picks(data: dict) -> dict:
    return {
        "picks": [{k: p.get(k) for k in PICKS_PICK_KEEP} for p in data["picks"]],
        "entry_history": {k: data["entry_history"].get(k) for k in PICKS_HISTORY_KEEP},
    }


def _trim_summary(data: dict, *, scrub_names: bool) -> dict:
    trimmed = {k: data.get(k) for k in SUMMARY_KEEP}
    if scrub_names:
        # Task 1 checkpoint decision: "scrub-names" — the two free-text manager
        # name fields never enter git history; the team name (`name`) and every
        # numeric season figure are captured verbatim.
        trimmed["player_first_name"] = ""
        trimmed["player_last_name"] = ""
    return trimmed


def _trim_history(data: dict) -> dict:
    return {
        "chips": [{k: c.get(k) for k in HISTORY_CHIP_KEEP}
                 for c in data.get("chips", [])],
        "current": [{k: c.get(k) for k in HISTORY_CURRENT_KEEP}
                   for c in data.get("current", [])],
    }


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(payload, path, indent=1)


def _capture() -> int:
    import joblib
    import requests

    print("[capture] reading cached upstream payloads from data/raw/live/")
    boot_path = config.RAW_DIR / "live" / "bootstrap-static.json"
    fixtures_path = config.RAW_DIR / "live" / "fixtures.json"
    boot = read_json(boot_path, what="FPL bootstrap-static payload (capture)",
                     remedy="python -m data.ingest")
    fixtures = read_json(fixtures_path, what="FPL fixtures payload (capture)",
                         remedy="python -m data.ingest")
    gw = _next_gw(boot)
    print(f"[capture] derived gw={gw} from data/raw/live/bootstrap-static.json")

    print("[capture] writing trimmed api/bootstrap-static.json + api/fixtures.json")
    _write_json(API_DIR / "bootstrap-static.json", _trim_bootstrap(boot))
    _write_json(API_DIR / "fixtures.json", _trim_fixtures(fixtures))

    print("[capture] loading models/artifacts/xp_model.joblib")
    artifact = joblib.load(config.ROOT / "models" / "artifacts" / "xp_model.joblib")

    pool_gws = list(range(gw, gw + POOL_HORIZON))
    for g in pool_gws:
        print(f"[capture] freezing per-player pool for gw={g}")
        pool = _gw_pool(boot, fixtures, g, artifact)
        records = json.loads(pool.to_json(orient="records"))
        _write_json(API_DIR / "pools" / f"gw{g}.json", records)

    print("[capture] copying models/artifacts/intervals.json -> api/intervals.json")
    (API_DIR).mkdir(parents=True, exist_ok=True)
    shutil.copy(config.ROOT / "models" / "artifacts" / "intervals.json",
                API_DIR / "intervals.json")

    print(f"[capture] fetching entry {ENTRY}'s three endpoints live, once each")
    picks_url = f"{config.FPL_API}/entry/{ENTRY}/event/{gw - 1}/picks/"
    summary_url = f"{config.FPL_API}/entry/{ENTRY}/"
    history_url = f"{config.FPL_API}/entry/{ENTRY}/history/"

    r = requests.get(picks_url, headers=_HEADERS, timeout=30)
    if r.status_code != 200:
        print(f"[capture] FATAL: picks endpoint returned {r.status_code}: {picks_url}")
        return 1
    _write_json(API_DIR / "entries" / str(ENTRY) / f"picks_event{gw - 1}.json",
               _trim_picks(r.json()))

    s = requests.get(summary_url, headers=_HEADERS, timeout=15)
    s.raise_for_status()
    _write_json(API_DIR / "entries" / str(ENTRY) / "summary.json",
               _trim_summary(s.json(), scrub_names=True))

    h = requests.get(history_url, headers=_HEADERS, timeout=15)
    h.raise_for_status()
    _write_json(API_DIR / "entries" / str(ENTRY) / "history.json",
               _trim_history(h.json()))

    print("[capture] building web-data/ from the real export builders")
    pool = _gw_pool(boot, fixtures, gw, artifact)
    pool["actual"] = 0.0
    table = build_table(pool, boot)
    web_data = {
        "meta.json": build_meta(boot, gw, 1),
        "xp_table.json": table,
        "captains.json": build_captains(table),
        "squad.json": build_squad(pool),
        "fixtures.json": build_ticker(boot, fixtures, gw),
        "chips.json": build_chips(fixtures, gw),
        "standings.json": build_standings(boot, fixtures),
        "leaders.json": build_leaders(boot),
    }
    for name, payload in web_data.items():
        _write_json(WEB_DATA_DIR / name, payload)
    print("[capture] copying web/data/watchlist.json -> web-data/watchlist.json verbatim")
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(config.ROOT / "web" / "data" / "watchlist.json",
                WEB_DATA_DIR / "watchlist.json")

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    capture = {
        "fixture_version": "v1",
        "captured_utc": now,
        "frozen_now_utc": now,
        "gw": gw,
        "picks_event": gw - 1,
        "entry": ENTRY,
        "season": config.CURRENT_SEASON,
        "pool_gws": pool_gws,
    }
    _write_json(API_DIR / "capture.json", capture)
    print(f"[capture] wrote api/capture.json: gw={gw}, frozen_now_utc={now}")
    print(f"[capture] done -> {FIXTURE_ROOT.relative_to(_REPO_ROOT)}")
    return 0


def _verify() -> int:
    errors: list[str] = []

    def require_file(path: Path) -> bool:
        if not path.exists():
            errors.append(f"missing file: {path.relative_to(_REPO_ROOT)}")
            return False
        return True

    boot_path = API_DIR / "bootstrap-static.json"
    capture_path = API_DIR / "capture.json"
    meta_path = WEB_DATA_DIR / "meta.json"

    required = [
        boot_path, API_DIR / "fixtures.json", API_DIR / "intervals.json",
        capture_path,
        API_DIR / "entries" / str(ENTRY) / "summary.json",
        API_DIR / "entries" / str(ENTRY) / "history.json",
        WEB_DATA_DIR / "watchlist.json",
    ]
    for name in ("meta.json", "xp_table.json", "captains.json", "squad.json",
                 "fixtures.json", "chips.json", "standings.json", "leaders.json"):
        required.append(WEB_DATA_DIR / name)
    for path in required:
        require_file(path)

    if errors:
        for e in errors:
            print(f"[verify] {e}")
        return 1

    boot = read_json(boot_path, what="captured api/bootstrap-static.json fixture")
    gw = _next_gw(boot)
    capture = read_json(capture_path, what="captured api/capture.json fixture")
    meta = read_json(meta_path, what="captured web-data/meta.json fixture")

    if meta.get("gw") != gw:
        errors.append(f"web-data/meta.json gw={meta.get('gw')} != "
                       f"_next_gw(api/bootstrap-static.json)={gw}")
    if capture.get("gw") != gw:
        errors.append(f"api/capture.json gw={capture.get('gw')} != {gw}")

    for g in range(gw, gw + POOL_HORIZON):
        pool_path = API_DIR / "pools" / f"gw{g}.json"
        if not require_file(pool_path):
            continue
        records = read_json(pool_path, what="captured api/pools fixture")
        if not isinstance(records, list) or len(records) == 0:
            errors.append(f"pool file gw{g}.json is empty or not a list")
            continue
        missing_keys = REQUIRED_POOL_KEYS - set(records[0].keys())
        if missing_keys:
            errors.append(f"pool file gw{g}.json first record missing keys: "
                          f"{sorted(missing_keys)}")

    xp_table_path = WEB_DATA_DIR / "xp_table.json"
    xp_table = read_json(xp_table_path, what="captured web-data/xp_table.json fixture")
    if not isinstance(xp_table, list) or len(xp_table) == 0:
        errors.append("web-data/xp_table.json is empty or not a list")

    picks_path = API_DIR / "entries" / str(ENTRY) / f"picks_event{gw - 1}.json"
    if require_file(picks_path):
        picks = read_json(picks_path, what="captured picks fixture")
        if len(picks.get("picks", [])) != 15:
            errors.append(f"{picks_path.name} has "
                          f"{len(picks.get('picks', []))} picks, expected 15")

    for path in FIXTURE_ROOT.parent.rglob("*"):
        if path.is_file():
            try:
                text = path.read_text(errors="ignore")
            except (UnicodeDecodeError, OSError):
                continue
            if "fantasy.premierleague.com" in text:
                errors.append(f"{path.relative_to(_REPO_ROOT)} contains "
                              "fantasy.premierleague.com")

    if errors:
        for e in errors:
            print(f"[verify] FAIL: {e}")
        return 1

    print(f"[verify] OK: gw={gw}, {POOL_HORIZON} pool files, xp_table non-empty, "
          f"picks_event{gw - 1}.json has 15 picks, no upstream URLs")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true",
                    help="capture the v1 normal fixture set (default action)")
    ap.add_argument("--verify", action="store_true",
                    help="verify the committed v1 normal fixture set")
    args = ap.parse_args(argv)

    if args.verify:
        return _verify()
    return _capture()


if __name__ == "__main__":
    sys.exit(main())
