"""Solver API: the dynamic (paid) layer behind the static site.

Endpoints
  GET  /api/health          liveness + pool freshness
  GET  /api/meta            gameweek, deadline, model stamp
  GET  /api/team/{entry}    a manager's current squad + bank from the FPL API
  POST /api/solve           transfer/squad ILP with locks, excludes, horizon, chips
  GET  /api/rate/{entry}    rate-my-team: squad xP vs the optimum, one best move

Design notes
  - The player pool is computed once per (gameweek, horizon) and cached; a solve
    request only runs the ILP (seconds). Deadline-hour traffic hits the cache.
  - Entitlements are a stub: if FPL_API_KEYS (comma-separated) is set, /solve and
    /rate require X-API-Key. Swap `require_key` for real auth (Supabase JWT +
    subscriptions table) when payments are wired — single choke point by design.
  - Solve responses are cached by (gw, entry, params-hash) until the pool refreshes.

Run:
  uvicorn api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import NamedTuple

import joblib
import pandas as pd
import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
import predict.live as live
from models import intervals
from ops.jsonio import read_json
from ops.jsonlog import configure_logging, log_event, redact
from ops.payloads import validate_bootstrap, validate_fixtures
from optimize.multi_period import solve_multi_period
from optimize.squad_ilp import pick_squad
from optimize.transfers import optimize_gw
from predict.live import (_gw_pool, _load_live, _next_gw, build_horizon_pool,
                          build_pool, _POS)

POOL_TTL_S = 3600
SOLVE_CACHE_MAX = 256      # hard entry ceiling on _solve_cache (REL-05)
SOLVE_CACHE_TTL_S = POOL_TTL_S
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}

# --- E2E fixture-mode seam (Phase 4, E2E-01) --------------------------------
# FPL_FIXTURE_DIR points at a captured fixture set (see e2e/fixtures/v1/MANIFEST.md).
# When set, every outbound-network / model-artifact call site below branches to
# read committed JSON from disk instead — no call to fantasy.premierleague.com,
# no joblib.load. FPL_FIXTURE_DATA_DIR independently overrides where the site's
# /data mount reads from, so a blank/DGW variant server can reuse this same
# api-side capture while serving a different /data set. Production (the unset
# default) is untouched by any of this — see the mount split at the bottom of
# this file and tests/test_fixture_mode.py's unset-env assertion.
_FIXTURE_ROOT = (Path(os.environ["FPL_FIXTURE_DIR"]).resolve()
                if os.environ.get("FPL_FIXTURE_DIR") else None)
_FIXTURE_API = _FIXTURE_ROOT / "api" if _FIXTURE_ROOT else None
_FIXTURE_DATA = (Path(os.environ["FPL_FIXTURE_DATA_DIR"]).resolve()
                if os.environ.get("FPL_FIXTURE_DATA_DIR")
                else (_FIXTURE_ROOT / "web-data" if _FIXTURE_ROOT else None))
if _FIXTURE_ROOT:
    print(f"[fixture-mode] FPL_FIXTURE_DIR={_FIXTURE_API} "
          f"FPL_FIXTURE_DATA_DIR={_FIXTURE_DATA} -- serving frozen fixtures, "
          "no live FPL API calls, no model artifact load. This must never be "
          "set in a production/deploy configuration.")


def _fixture_json(*parts: str):
    return read_json(_FIXTURE_API.joinpath(*parts), what="frozen fixture payload",
                     remedy="see e2e/fixtures/v1/MANIFEST.md")


def _cors_origins() -> list[str]:
    """Resolve the browser trust boundary from FPL_CORS_ORIGINS (SEC-01).

    Splits the comma-separated env var, strips whitespace, drops empty
    entries. Unset or resolving to an empty list falls back to the local
    development origins -- the Vite dev server and the uvicorn-served build,
    on both localhost and 127.0.0.1 -- that Phases 1 and 4 already depend on.
    A wildcard entry anywhere in the resolved list is a boot failure: an
    unrestricted origin list is not an accepted configuration, so the process
    refuses to start rather than defaulting wide open.
    """
    raw = os.environ.get("FPL_CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if "*" in origins:
        raise RuntimeError(
            "FPL_CORS_ORIGINS must not contain '*' -- an unrestricted CORS "
            "origin list is not an accepted configuration. Set one or more "
            "explicit origins (comma-separated) instead."
        )
    if not origins:
        return ["http://localhost:5173", "http://127.0.0.1:5173",
                "http://localhost:8000", "http://127.0.0.1:8000"]
    return origins


app = FastAPI(title="FPL ML API", version="0.1")
_cors_origin_list = _cors_origins()
app.add_middleware(CORSMiddleware, allow_origins=_cors_origin_list,
                   allow_methods=["GET", "POST", "OPTIONS"],
                   allow_headers=["Content-Type", "X-API-Key"],
                   allow_credentials=False, max_age=600)
configure_logging("api")
_logger = logging.getLogger(__name__)
log_event(_logger, "cors.configured", origin_count=len(_cors_origin_list),
          origins=_cors_origin_list)


def _route_template(request: Request) -> str:
    """The matched route's path template (e.g. "/api/team/{entry}") when one
    matched this request, falling back to the concrete URL path only for
    unrouted 404s. This is what keeps a manager's numeric entry id out of
    the request log for /api/team/{entry} and /api/rate/{entry} (OBS-01)."""
    route = request.scope.get("route")
    return route.path if route is not None else request.url.path


def _request_log_fields(request: Request, request_id: str, status: int,
                        duration_ms: float, **extra) -> dict:
    """Assemble the fixed field set for one `http.request` record. Never
    reads the request body, the query string, or any header value -- only
    method, matched route template, status, duration and client address.
    Passed through `redact` before being handed to `log_event`, which itself
    redacts again on format -- belt and suspenders, so a secret that reaches
    this dict by any future route is still blanked twice over."""
    fields = {"request_id": request_id, "method": request.method,
              "path": _route_template(request), "status": status,
              "duration_ms": duration_ms}
    if request.client is not None:
        fields["client"] = request.client.host
    fields.update(extra)
    return redact(fields)


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    """Emit exactly one structured, secret-free `http.request` record per
    HTTP request (OBS-01), with a correlatable id echoed back to the caller
    via the X-Request-ID response header."""
    request_id = uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        fields = _request_log_fields(request, request_id, 500, duration_ms,
                                     error=f"{type(exc).__name__}: {exc}")
        log_event(_logger, "http.request", level="error", **fields)
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    fields = _request_log_fields(request, request_id, response.status_code, duration_ms)
    log_event(_logger, "http.request", **fields)
    response.headers["X-Request-ID"] = request_id
    return response


_lock = threading.Lock()


def _initial_state() -> dict:
    """Factory for _state's pristine shape — single source of truth so tests
    (and _refresh's cold-start check) never hardcode the dict's keys.

    `pool_version` is a monotonic counter bumped by `_refresh` on every
    successful reload; it is folded into every solve-cache key so a payload
    computed against an older pool can never be served after a refresh
    (REL-05) — the version bump, not the cache clear, is what makes that
    unreachable.
    """
    return {"artifact": None, "boot": None, "fixtures": None, "gw": None,
            "pools": {}, "loaded_at": 0.0, "ready": False, "last_error": None,
            "pool_version": 0}


class PoolSnapshot(NamedTuple):
    """The pool `_pool()` built plus the gameweek, bootstrap payload and
    `pool_version` it was built under -- all four read inside the SAME
    critical section. 06-VERIFICATION.md recorded pairing any one of these
    with a separately-read `version` (a second, later lock acquisition) as
    the REL-05 TOCTOU defect: a refresh landing between the two reads tags a
    pre-refresh pool with a post-refresh version, serving stale data under a
    key that claims to be current. Consume this as one value, never split
    across two lock acquisitions.
    """
    pool: object
    gw: int
    boot: dict
    version: int


class GwPoolsSnapshot(NamedTuple):
    """The multi-gameweek analogue of `PoolSnapshot`, for the `/api/plan`
    path: the per-gameweek pools plus the gameweek, bootstrap payload and
    `pool_version` they were built under, all read inside the SAME critical
    section. Same rule as `PoolSnapshot` -- pairing any field here with a
    separately-read version is the REL-05 defect re-introduced.
    """
    pools: list
    gw: int
    boot: dict
    version: int


_state: dict = _initial_state()

# Bounded LRU + TTL cache of solve/plan responses, keyed by a hash of the
# request (including the pool version). Entries are `(stored_at, payload)`
# tuples. `_cache_get`/`_cache_put` below are the ONLY two doors into this
# structure — every access happens under `_lock` (REL-05).
_solve_cache: "OrderedDict[str, tuple[float, dict]]" = OrderedDict()


def _cache_get(key: str):
    """The only read door into `_solve_cache`.

    Locked for its whole body. Returns None on a miss. An entry older than
    SOLVE_CACHE_TTL_S is discarded and treated as a miss. A live hit is moved
    to the end of the ordering before being returned — that move is what
    makes eviction least-recently-*used* rather than least-recently-inserted.
    """
    with _lock:
        entry = _solve_cache.get(key)
        if entry is None:
            return None
        stored_at, payload = entry
        if time.time() - stored_at > SOLVE_CACHE_TTL_S:
            _solve_cache.pop(key, None)
            return None
        _solve_cache.move_to_end(key)
        return payload


def _cache_put(key: str, payload) -> None:
    """The only write door into `_solve_cache`.

    Locked for its whole body. Stores the entry, moves it to the end, then
    evicts from the front with `popitem(last=False)` while the cache exceeds
    SOLVE_CACHE_MAX — per-entry eviction, never a full clear.
    """
    with _lock:
        _solve_cache.update({key: (time.time(), payload)})
        _solve_cache.move_to_end(key)
        while len(_solve_cache) > SOLVE_CACHE_MAX:
            _solve_cache.popitem(last=False)


def _load_live_fixture(force: bool = True):
    """Fixture-mode replacement for predict.live._load_live: reads the
    committed, trimmed bootstrap-static.json/fixtures.json from disk instead
    of predict.live._load_live's unconditional fetch_fpl_live download. Runs
    the same validators as the live path, in the "fixture" profile, so the
    frozen E2E capture is exercised by the same validator on every fixture-mode
    boot and the validator can never drift untested."""
    boot = _fixture_json("bootstrap-static.json")
    fixtures = _fixture_json("fixtures.json")
    validate_bootstrap(boot, source=str(_FIXTURE_API / "bootstrap-static.json"), profile="fixture")
    validate_fixtures(fixtures, source=str(_FIXTURE_API / "fixtures.json"))
    return boot, fixtures


def _gw_pool_fixture(boot: dict, fixtures: list, gw: int, artifact) -> pd.DataFrame:
    """Fixture-mode replacement for predict.live._gw_pool: the single
    model-inference leaf. Reads the frozen per-gameweek pool captured at
    e2e/scripts/capture_fixtures.py time instead of running LightGBM inference
    (D-10) — build_pool/build_horizon_pool's own aggregation and decay math
    still run for real over this frozen input."""
    path = _FIXTURE_API / "pools" / f"gw{gw}.json"
    if not path.exists():
        raise HTTPException(503, f"no frozen pool for gw{gw} in fixture set "
                                 f"{_FIXTURE_API}")
    return pd.DataFrame(read_json(path, what="frozen per-gameweek pool"))


# CR-01 fix (04-VERIFICATION.md Gap 1): capture the production `_gw_pool`
# reference exactly once per process, before the fixture-mode branch below
# ever runs, so a later env-unset reload can restore it. The `hasattr` guard
# is load-bearing: on a second+ `importlib.reload(api.main)` of a process that
# has already been in fixture mode, `live._gw_pool` is the fixture
# replacement, so an unguarded re-capture would freeze the polluted value in
# as "production" and the restore below would be a no-op. Placement ahead of
# the `if _FIXTURE_ROOT:` branch is equally load-bearing: run after it, the
# first fixture-mode import would capture the replacement it just installed.
if not hasattr(live, "_gw_pool_production"):
    live._gw_pool_production = live._gw_pool

if _FIXTURE_ROOT:
    _load_live = _load_live_fixture
    # build_pool/build_horizon_pool resolve `_gw_pool` from predict.live's own
    # module globals at call time, so rebinding only api.main's imported name
    # would not affect them — both bindings must be rebound (RESEARCH.md
    # Pattern 1, Pitfall 1).
    _gw_pool = _gw_pool_fixture
    live._gw_pool = _gw_pool_fixture
else:
    # Restore all three bindings from the captured production reference
    # (CR-01). Without this, `predict.live._gw_pool` stays permanently
    # rebound to `_gw_pool_fixture` for the rest of the process once fixture
    # mode has ever been entered, since `predict.live` is never itself
    # reloaded and api.main's own re-import at module top pulls the already-
    # polluted value back in on the next reload.
    _gw_pool = live._gw_pool_production
    live._gw_pool = live._gw_pool_production
    _load_live = live._load_live


def _intervals_artifact() -> dict | None:
    """intervals.load_artifact() in production; the committed intervals.json
    copy in fixture mode. Without this branch, p10/p90 bands would appear on a
    developer machine (where models/artifacts/intervals.json exists) and
    vanish in CI (where it does not) — a machine-dependent response body."""
    if _FIXTURE_ROOT:
        return _fixture_json("intervals.json")
    return intervals.load_artifact()


def _refresh(force: bool = False) -> None:
    with _lock:
        stale = time.time() - _state["loaded_at"] > POOL_TTL_S
        if not (force or stale or _state["boot"] is None):
            return
        try:
            if _state["artifact"] is None:
                # Fixture mode: a non-None sentinel, never the real (gitignored,
                # absent-on-clean-checkout) joblib artifact (D-10, Pitfall 3).
                _state["artifact"] = ("fixture-mode" if _FIXTURE_ROOT else joblib.load(
                    config.ROOT / "models" / "artifacts" / "xp_model.joblib"))
            boot, fixtures = _load_live()
            _state.update(boot=boot, fixtures=fixtures, gw=_next_gw(boot),
                          pools={}, loaded_at=time.time(), ready=True, last_error=None,
                          pool_version=_state["pool_version"] + 1)
            _solve_cache.clear()
        except Exception as exc:
            _state["ready"] = False
            _state["last_error"] = str(exc)
            log_event(_logger, "pool.refresh_failed", level="error", error=str(exc))
            raise


def _with_bands(pool):
    """Attach p10/p90 interval columns when the artifact exists."""
    art = _intervals_artifact()
    return pool if art is None else intervals.apply_intervals(pool, art)


def _pool(horizon: int = 1) -> PoolSnapshot:
    _refresh()
    with _lock:
        key = horizon
        if key not in _state["pools"]:
            build = (build_horizon_pool if horizon > 1 else build_pool)
            args = (_state["boot"], _state["fixtures"], _state["gw"],
                    _state["artifact"])
            _state["pools"][key] = _with_bands(build(*args, horizon)
                                               if horizon > 1 else build(*args))
        return PoolSnapshot(_state["pools"][key], _state["gw"], _state["boot"],
                            _state["pool_version"])


def _gw_pools_locked(start_gw: int, horizon: int) -> list:
    """One pool per gameweek in [start_gw, start_gw+horizon), cached.

    Caller must already hold `_lock`. This function takes no lock of its own
    -- `_lock` is a plain `threading.Lock` (not reentrant), and this now runs
    entirely inside `_gw_pools_meta`'s single critical section so the pools,
    the gameweek, the bootstrap payload and the pool version all come from
    one atomic read (REL-05).
    """
    out = []
    for g in range(start_gw, start_gw + horizon):
        key = f"gw{g}"
        if key not in _state["pools"]:
            p = _gw_pool(_state["boot"], _state["fixtures"], g,
                         _state["artifact"])
            p["actual"] = 0.0
            _state["pools"][key] = _with_bands(p)
        out.append(_state["pools"][key])
    return out


def _xi_band(pool, starters, captain_code, xi_xp) -> tuple[float, float] | None:
    """XI-level 10-90% band from per-player bands, assuming independence.

    Per-player p10/p90 ≈ ±1.28σ, so σ_i = (p90-p10)/2.56; the captain's points
    double, doubling their σ. XI band = xi_xp ± 1.28·sqrt(Σσ²). Player scores
    correlate a little (teammates share matches), so the true band is slightly
    wider — treat as a floor, not gospel.
    """
    if "p10" not in pool.columns:
        return None
    P = pool.set_index("player_code")
    var = 0.0
    for c in starters:
        if c not in P.index:
            continue
        sigma = (float(P.p90[c]) - float(P.p10[c])) / 2.56
        if c == captain_code:
            sigma *= 2
        var += sigma * sigma
    half = 1.28 * var ** 0.5
    return round(max(xi_xp - half, 0.0), 1), round(xi_xp + half, 1)


def ft_from_history(history: dict, next_gw: int) -> int:
    """Free transfers available at `next_gw` from an /entry/{id}/history/ body.

    Rules (2026/27): 1 FT from GW2, +1 per gameweek, roll up to 5, each
    transfer spends one (hits can't push the stock below 0); wildcard /
    free-hit weeks neither spend nor lose the stock.
    """
    chip_gws = {c["event"] for c in history.get("chips", [])
                if c.get("name") in ("wildcard", "freehit")}
    ft = 1
    for ev in sorted(history.get("current", []), key=lambda e: e["event"]):
        g = ev["event"]
        if g < 2 or g >= next_gw:
            continue
        spent = 0 if g in chip_gws else ev.get("event_transfers", 0)
        ft = min(config.MAX_FREE_TRANSFERS, max(ft - spent, 0) + 1)
    return ft


def _fetch_entry_history(entry: int) -> dict | None:
    """The one requests.get call site for GET /entry/{entry}/history/.

    Fixture mode reads entries/{entry}/history.json; a missing file degrades to
    the same None/best-effort behaviour as a live requests.RequestException, so
    an unknown entry id exercises the same error path in both modes.
    """
    if _FIXTURE_ROOT:
        path = _FIXTURE_API / "entries" / str(entry) / "history.json"
        return read_json(path, what="frozen entry history") if path.exists() else None
    try:
        r = requests.get(f"{config.FPL_API}/entry/{entry}/history/",
                         headers=_HEADERS, timeout=15)
        return r.json() if r.status_code == 200 else None
    except requests.RequestException:
        return None


def _free_transfers(entry: int, next_gw: int) -> int | None:
    history = _fetch_entry_history(entry)
    return None if history is None else ft_from_history(history, next_gw)


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    keys = {k.strip() for k in os.environ.get("FPL_API_KEYS", "").split(",")
            if k.strip()}
    if keys and x_api_key not in keys:
        raise HTTPException(401, "missing or invalid API key")


def _fetch_entry_picks(entry: int, gw: int) -> dict:
    """The one requests.get call site for GET /entry/{entry}/event/{gw}/picks/.

    Fixture mode reads entries/{entry}/picks_event{gw-1}.json; a missing file
    raises the identical HTTPException(404, ...) the live 404 path raises, so a
    bad entry id exercises the same error path in both modes.
    """
    if _FIXTURE_ROOT:
        path = _FIXTURE_API / "entries" / str(entry) / f"picks_event{gw - 1}.json"
        if not path.exists():
            raise HTTPException(404, f"entry {entry}: no picks for GW{gw - 1} "
                                     "(bad id, or the season hasn't started)")
        return read_json(path, what="frozen entry picks")
    r = requests.get(f"{config.FPL_API}/entry/{entry}/event/{gw - 1}/picks/",
                     headers=_HEADERS, timeout=30)
    if r.status_code == 404:
        raise HTTPException(404, f"entry {entry}: no picks for GW{gw - 1} "
                                 "(bad id, or the season hasn't started)")
    r.raise_for_status()
    return r.json()


def _fetch_entry_summary(entry: int) -> dict | None:
    """The one requests.get call site for GET /entry/{entry}/.

    Fixture mode reads entries/{entry}/summary.json; a missing file degrades to
    the same best-effort None as a live requests.RequestException/non-200.
    """
    if _FIXTURE_ROOT:
        path = _FIXTURE_API / "entries" / str(entry) / "summary.json"
        return read_json(path, what="frozen entry summary") if path.exists() else None
    try:
        s = requests.get(f"{config.FPL_API}/entry/{entry}/",
                         headers=_HEADERS, timeout=15)
        return s.json() if s.status_code == 200 else None
    except requests.RequestException:
        return None


def _fetch_team(entry: int, gw: int, boot: dict) -> dict:
    data = _fetch_entry_picks(entry, gw)
    # Manager summary (team name, overall points/rank) — best-effort.
    manager = {}
    sj = _fetch_entry_summary(entry)
    if sj is not None:
        manager = {"team_name": sj.get("name"),
                   "manager": f"{sj.get('player_first_name', '')} "
                              f"{sj.get('player_last_name', '')}".strip(),
                   "overall_points": sj.get("summary_overall_points"),
                   "overall_rank": sj.get("summary_overall_rank"),
                   "gw_points": sj.get("summary_event_points")}
    meta = {el["id"]: el for el in boot["elements"]}
    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    picks = [{
        "player_code": meta[p["element"]]["code"],
        "name": meta[p["element"]]["web_name"],
        "team": teams[meta[p["element"]]["team"]],
        "position": _POS[meta[p["element"]]["element_type"]],
        "price_m": meta[p["element"]]["now_cost"] / 10.0,
    } for p in data["picks"]]
    return {"entry": entry, "picks": picks,
            "bank": data["entry_history"]["bank"] / 10.0,
            "value": data["entry_history"]["value"] / 10.0,
            "manager": manager}


def _resolve(pool, items: list) -> list[int]:
    """Locks/excludes as player_codes (int) or name fragments (str).

    Name matching: exact beats prefix beats substring ('Saka' must not resolve
    to Wan-Bissaka); ties go to the highest-xP player.
    """
    codes = []
    for it in items or []:
        if isinstance(it, int):
            codes.append(it)
            continue
        q = str(it).lower()
        names = pool.name.str.lower()
        m = pool[names.str.contains(q, regex=False, na=False)].copy()
        if not len(m):
            raise HTTPException(422, f"player not found in this gameweek: {it!r}")
        low = m.name.str.lower()
        m["rank"] = 2 - (low == q) * 2 - (low.str.startswith(q) & (low != q)) * 1
        codes.append(int(m.sort_values(["rank", "xp"],
                                       ascending=[True, False]).iloc[0].player_code))
    return codes


class SolveRequest(BaseModel):
    entry: int | None = None
    free_transfers: int = Field(1, ge=0, le=config.MAX_FREE_TRANSFERS)
    horizon: int = Field(1, ge=1, le=6)
    mode: str = Field("normal", pattern="^(normal|tc|bb)$")
    budget: float | None = None
    max_transfers: int | None = Field(None, ge=0, le=15)
    locks: list[int | str] = []
    excludes: list[int | str] = []


@app.get("/api/health")
def health():
    return {"ok": True, "gw": _state["gw"],
            "pool_age_s": round(time.time() - _state["loaded_at"])}


@app.get("/api/ready")
def ready():
    """Readiness probe, distinct from liveness: 200 only once a pool has
    actually loaded; 503 with an actionable `reason` otherwise. Unlike
    `/api/health`, this calls `_refresh()` and so may block on `_lock`."""
    try:
        _refresh()
        return {"ready": True, "gw": _state["gw"],
                "pool_age_s": round(time.time() - _state["loaded_at"])}
    except Exception as exc:
        return JSONResponse(status_code=503, content={
            "ready": False, "reason": str(exc), "gw": None,
            "pool_age_s": round(time.time() - _state["loaded_at"])})


@app.get("/api/meta")
def meta():
    _refresh()
    ev = next((e for e in _state["boot"]["events"] if e["id"] == _state["gw"]), {})
    return {"gw": _state["gw"], "deadline_utc": ev.get("deadline_time"),
            "season": config.CURRENT_SEASON}


@app.get("/api/team/{entry}")
def team(entry: int):
    snap = _pool()
    return _fetch_team(entry, snap.gw, snap.boot)


def _squad_rows(pool, squad_codes, starters, captain_code):
    P = pool.set_index("player_code")
    rows = []
    for c in squad_codes:
        if c not in P.index:
            continue
        r = P.loc[c]
        rows.append({"player_code": int(c), "name": r["name"], "team": r.team,
                     "position": r.position, "price_m": float(r.price_m),
                     "xp": round(float(r.xp), 2),
                     "starting": c in set(starters),
                     "captain": c == captain_code})
    return rows


@app.post("/api/solve", dependencies=[Depends(require_key)])
def solve(req: SolveRequest):
    snap = _pool(req.horizon)
    pool, gw, boot, pool_version = snap.pool, snap.gw, snap.boot, snap.version
    key = hashlib.sha1(json.dumps({"gw": gw, "pool_version": pool_version,
                                  **req.model_dump()},
                                  sort_keys=True, default=str).encode()).hexdigest()
    cached = _cache_get(key)
    if cached is not None:
        return cached
    locks = _resolve(pool, req.locks)
    excludes = _resolve(pool, req.excludes)

    if req.entry is None:
        # From-scratch squad (wildcard / preseason view).
        p = pool[~pool.player_code.isin(excludes)]
        res = pick_squad(p, budget=req.budget or config.BUDGET, force=locks)
        ch = res["squad"]
        out = {"gw": gw, "kind": "squad",
               "squad": [{"player_code": int(r.player_code), "name": r["name"],
                          "team": r.team, "position": r.position,
                          "price_m": float(r.price_m), "xp": round(float(r.xp), 2),
                          "starting": bool(r.starting), "captain": bool(r.is_captain)}
                         for _, r in ch.iterrows()],
               "captain": res["captain"], "formation": res["formation"],
               "cost": round(float(res["cost"]), 1),
               "xi_xp": round(float(res["xp_xi"]), 2)}
    else:
        t = _fetch_team(req.entry, gw, boot)
        squad = {p["player_code"]: p["price_m"] for p in t["picks"]}
        held_meta = {p["player_code"]: p for p in t["picks"]}
        before = set(squad)
        r = optimize_gw(pool, squad, t["bank"], req.free_transfers,
                        mode=req.mode, max_transfers=req.max_transfers,
                        holdings_meta=held_meta, force=locks, exclude=excludes)
        after = set(r["squad"])
        P = pool.set_index("player_code")
        buys = [{"name": P.name[c], "position": P.position[c],
                 "price_m": float(P.price_m[c])} for c in sorted(after - before)]
        sells = [{"name": held_meta[c]["name"],
                  "position": held_meta[c]["position"],
                  "price_m": held_meta[c]["price_m"]}
                 for c in sorted(before - after)]
        out = {"gw": gw, "kind": "transfers", "entry": req.entry,
               "transfers": r["transfers"], "hits": r["hits"],
               "buys": buys, "sells": sells,
               "captain": r["captain"], "bank_after": r["bank"],
               "xi_xp": r["xi_xp"],
               "squad": _squad_rows(pool, r["squad"], r["starters"],
                                    r["captain_code"])}
    _cache_put(key, out)
    return out


class PlanRequest(BaseModel):
    entry: int
    horizon: int = Field(3, ge=1, le=6)
    free_transfers: int | None = Field(None, ge=0, le=config.MAX_FREE_TRANSFERS)


@app.post("/api/plan", dependencies=[Depends(require_key)])
def plan(req: PlanRequest):
    """True multi-week transfer plan: jointly optimises when to move, bank a
    free transfer, or take a hit over the horizon. Week 0 is the executable
    decision; later weeks are the current plan (re-solve each week)."""
    snap = _gw_pools_meta(req.horizon)
    pools, gw, boot, pool_version = snap.pools, snap.gw, snap.boot, snap.version
    key = hashlib.sha1(json.dumps({"plan": True, "gw": gw, "pool_version": pool_version,
                                  **req.model_dump()},
                                  sort_keys=True).encode()).hexdigest()
    cached = _cache_get(key)
    if cached is not None:
        return cached
    t = _fetch_team(req.entry, gw, boot)
    ft = req.free_transfers
    if ft is None:
        ft = _free_transfers(req.entry, gw) or 1
    squad = {p["player_code"]: p["price_m"] for p in t["picks"]}
    r = solve_multi_period(pools, squad, t["bank"], ft)
    weeks = []
    for i, w in enumerate(r["plan"]):
        starters = [p["player_code"] for p in w["squad"] if p["starting"]]
        capt = next((p["player_code"] for p in w["squad"] if p["captain"]), None)
        band = _xi_band(pools[i], starters, capt, w["xi_xp"])
        weeks.append({"gw": gw + i, **w,
                      "xi_p10": band[0] if band else None,
                      "xi_p90": band[1] if band else None})
    out = {"entry": req.entry, "gw": gw, "horizon": req.horizon,
           "free_transfers_used": ft, "manager": t["manager"],
           "weeks": weeks}
    _cache_put(key, out)
    return out


def _gw_pools_meta(horizon: int) -> GwPoolsSnapshot:
    """Read the gameweek, build/fetch the per-gameweek pools, and read the
    bootstrap payload and pool version -- all inside ONE locked block. Prior
    to this fix, the gameweek and bootstrap reads happened with NO lock held
    at all, on either side of a `_gw_pools()` call that took the lock for
    itself: three separate views of `_state` in one expression. This is the
    single critical section `/api/plan`'s cache key now depends on (REL-05).
    """
    _refresh()
    with _lock:
        gw = _state["gw"]
        pools = _gw_pools_locked(gw, horizon)
        return GwPoolsSnapshot(pools, gw, _state["boot"], _state["pool_version"])


@app.get("/api/rate/{entry}", dependencies=[Depends(require_key)])
def rate(entry: int):
    snap = _pool()
    pool, gw, boot = snap.pool, snap.gw, snap.boot
    t = _fetch_team(entry, gw, boot)
    squad = {p["player_code"]: p["price_m"] for p in t["picks"]}
    held_meta = {p["player_code"]: p for p in t["picks"]}
    hold = optimize_gw(pool, squad, t["bank"], 1, max_transfers=0,
                       holdings_meta=held_meta)
    one = optimize_gw(pool, squad, t["bank"], 1, max_transfers=1,
                      holdings_meta=held_meta)
    ideal = pick_squad(pool, budget=t["value"] + t["bank"])
    score = round(100 * hold["xi_xp"] / max(float(ideal["xp_xi"]), 1e-9))
    move = None
    if one["transfers"]:
        before, after = set(squad), set(one["squad"])
        names = pool.set_index("player_code")["name"]
        move = {"sell": [held_meta[c]["name"] for c in before - after],
                "buy": [names.get(c, str(c)) for c in after - before],
                "xp_gain": round(one["xi_xp"] - hold["xi_xp"], 2)}
    band = _xi_band(pool, hold["starters"], hold["captain_code"], hold["xi_xp"])
    return {"entry": entry, "gw": gw, "score": min(score, 100),
            "xi_xp": hold["xi_xp"],
            "xi_p10": band[0] if band else None,
            "xi_p90": band[1] if band else None,
            "ideal_xi_xp": round(float(ideal["xp_xi"]), 2),
            "captain": hold["captain"], "best_move": move,
            "manager": t["manager"],
            "free_transfers": _free_transfers(entry, gw),
            "xi": _squad_rows(pool, hold["squad"], hold["starters"],
                              hold["captain_code"])}


# Fixture mode (E2E-01): serve the built React app + the frozen /data set
# instead of vanilla web/. check_dir=False lets this server boot before the
# frontend build has finished (plan 04-03's extra blank/DGW servers start in
# parallel with the one that owns the build). /data MUST be registered before
# the catch-all "/" mount below — Starlette matches mounts in registration
# order, and the more general "/" mount would otherwise swallow JSON requests
# and answer them with 404.html.
if _FIXTURE_ROOT:
    app.mount("/data", StaticFiles(directory=_FIXTURE_DATA, check_dir=False),
              name="fixture-data")
    app.mount("/", StaticFiles(directory=config.ROOT / "frontend" / "dist",
                               html=True, check_dir=False), name="site")
else:
    # Serve the static site from the same process, so a single
    #   uvicorn api.main:app --port 8000
    # runs everything at http://localhost:8000/ . API routes above win over the
    # mount; deploys that host web/ elsewhere (Cloudflare Pages) just ignore this.
    app.mount("/", StaticFiles(directory=config.ROOT / "web", html=True), name="site")
