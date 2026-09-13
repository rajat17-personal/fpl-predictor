"""In-process proof of the FPL_FIXTURE_DIR seam (Phase 4, E2E-01): with the env
var pointed at e2e/fixtures/v1/normal, every endpoint answers from committed
JSON with zero outbound HTTP and no model-artifact load. Mirrors
tests/test_api.py's TestClient + monkeypatch style, but drives the module's own
runtime branch (reload + env var) instead of per-test monkeypatch of _pool."""
from __future__ import annotations

import importlib

import pytest

import config
import predict.live as live
from ops.jsonio import read_json

FIXTURE_DIR = config.ROOT / "e2e" / "fixtures" / "v1" / "normal"
CAPTURE_PATH = FIXTURE_DIR / "api" / "capture.json"
CAPTURE = read_json(CAPTURE_PATH, what="frozen E2E capture.json fixture")
GW = CAPTURE["gw"]
ENTRY = CAPTURE["entry"]

# Captured at import, before any fixture-mode reload in this module or any
# other test module runs (CR-01 / 04-VERIFICATION.md Gap 1). The __module__
# check keeps this proof independent of live._gw_pool_production -- the very
# attribute api.main's own restore code writes -- so a broken restore can
# never be masked by comparing the captured reference against itself.
_ORIGINAL_GW_POOL = live._gw_pool
assert _ORIGINAL_GW_POOL.__module__ == "predict.live"


def _raise_if_called(*args, **kwargs):
    raise AssertionError("requests.get/joblib.load must never be called in fixture mode")


@pytest.fixture
def fixture_app(monkeypatch):
    """Reload api.main with FPL_FIXTURE_DIR set, requests.get and joblib.load
    poisoned to raise for the duration of the test. At teardown, delenv and
    reload again -- but the reload alone never restores production state: it
    only re-executes api.main, and predict.live is never itself reloaded. It
    is api.main's own env-unset else-branch, restoring from the
    capture-once-guarded predict.live._gw_pool_production reference, that
    actually puts predict.live._gw_pool back (CR-01 / 04-VERIFICATION.md
    Gap 1). The identity assertion below proves that restore ran, on every
    fixture-mode test in this file, rather than assuming it."""
    import api.main as m

    monkeypatch.setenv("FPL_FIXTURE_DIR", str(FIXTURE_DIR))
    reloaded = importlib.reload(m)
    monkeypatch.setattr(reloaded.requests, "get", _raise_if_called)
    monkeypatch.setattr(reloaded.joblib, "load", _raise_if_called)
    yield reloaded
    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    importlib.reload(reloaded)
    assert live._gw_pool is _ORIGINAL_GW_POOL


def test_health_and_meta_answer_with_fixture_gw_and_season(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)

    # /api/meta triggers _refresh() (loads boot/fixtures); /api/health does not
    # — call meta first so health reflects the loaded gw via shared module state,
    # matching tests/test_api.py's own health/meta ordering precedent.
    r = c.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["gw"] == GW
    assert body["season"] == CAPTURE["season"]

    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["gw"] == GW


def test_team_endpoint_returns_15_picks_and_a_manager_object(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)
    r = c.get(f"/api/team/{ENTRY}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["picks"]) == 15
    assert isinstance(body["manager"], dict)


def test_team_endpoint_unknown_entry_404s(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)
    r = c.get("/api/team/1")
    assert r.status_code == 404


def test_solve_transfers_response_is_a_legal_squad(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)
    r = c.post("/api/solve", json={"entry": ENTRY})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "transfers"
    squad = body["squad"]
    assert len(squad) == 15
    assert sum(p["starting"] for p in squad) == 11
    assert sum(p["captain"] for p in squad) == 1
    by_pos: dict[str, int] = {}
    for p in squad:
        by_pos[p["position"]] = by_pos.get(p["position"], 0) + 1
    assert by_pos == {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}


def test_rate_endpoint_score_and_xi(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)
    r = c.get(f"/api/rate/{ENTRY}")
    assert r.status_code == 200
    body = r.json()
    assert body["score"] <= 100
    assert len(body["xi"]) == 15


def test_plan_endpoint_returns_horizon_weeks(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)
    r = c.post("/api/plan", json={"entry": ENTRY, "horizon": 2})
    assert r.status_code == 200
    assert len(r.json()["weeks"]) == 2


def test_data_mount_serves_the_frozen_xp_table(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)
    r = c.get("/data/xp_table.json")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) > 0


def test_client_side_route_falls_back_to_the_spa_shell_not_json(fixture_app):
    from fastapi.testclient import TestClient

    c = TestClient(fixture_app.app)
    r = c.get("/team")
    assert "text/html" in r.headers["content-type"]


def test_unset_env_leaves_a_single_root_mount(monkeypatch):
    """The production default: with FPL_FIXTURE_DIR absent, api.main mounts
    exactly one path, "/" (vanilla web/), unchanged from before this seam."""
    from starlette.routing import Mount

    import api.main as m

    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    reloaded = importlib.reload(m)
    mounts = [route for route in reloaded.app.routes if isinstance(route, Mount)]
    assert len(mounts) == 1
    assert mounts[0].name == "site"
    importlib.reload(reloaded)


def test_unset_env_restores_the_production_gw_pool(monkeypatch):
    """Regression guard for CR-01 (04-VERIFICATION.md Gap 1): a fixture-mode
    reload followed by an env-unset reload must leave predict.live._gw_pool,
    api.main._gw_pool, and api.main._load_live pointing at the original
    production objects -- object identity, not equality. Drives both halves
    of the cycle directly (does not use the fixture_app fixture) so the
    assertions are legible as a single before/after/after proof, mirroring
    test_unset_env_leaves_a_single_root_mount's monkeypatch + reload shape."""
    import api.main as m

    monkeypatch.setenv("FPL_FIXTURE_DIR", str(FIXTURE_DIR))
    reloaded = importlib.reload(m)
    assert live._gw_pool is not _ORIGINAL_GW_POOL
    assert live._gw_pool.__module__ == "api.main"

    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    reloaded = importlib.reload(reloaded)
    assert live._gw_pool is _ORIGINAL_GW_POOL
    assert reloaded._gw_pool is _ORIGINAL_GW_POOL
    assert reloaded._load_live is live._load_live
