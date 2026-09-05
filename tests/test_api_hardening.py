"""Production-readiness hardening tests for api/main.py (Phase 6 Plan 04):

- SEC-01: the CORS trust boundary is an explicit, configured origin allowlist.
- REL-05: the solve cache is bounded (LRU + TTL) and invalidated by pool version.

Mirrors tests/test_fixture_mode.py's importlib.reload + monkeypatch pattern for
the env-dependent CORS cases, reloading the module back to a clean (env-unset)
state in fixture teardown so no later test in the session inherits a reloaded
module and tests/conftest.py's autouse state reset keeps working afterwards.
"""
from __future__ import annotations

import importlib
import time as time_mod
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

# ---------------------------------------------------------------- CORS (SEC-01)


@pytest.fixture
def cors_reload(monkeypatch):
    """Set (or unset) FPL_CORS_ORIGINS and reload api.main under that value.

    Teardown always unsets the env var and reloads again, restoring the
    module to its clean, production-default state for whichever test runs
    next in the session.
    """
    import api.main as m

    def _reload(env_value):
        if env_value is None:
            monkeypatch.delenv("FPL_CORS_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("FPL_CORS_ORIGINS", env_value)
        return importlib.reload(m)

    yield _reload

    monkeypatch.delenv("FPL_CORS_ORIGINS", raising=False)
    importlib.reload(m)


def test_configured_origin_is_echoed_on_preflight(cors_reload):
    from fastapi.testclient import TestClient

    m = cors_reload("https://fpl.example.com")
    c = TestClient(m.app)
    r = c.options("/api/solve", headers={
        "Origin": "https://fpl.example.com",
        "Access-Control-Request-Method": "POST",
    })
    assert r.headers.get("access-control-allow-origin") == "https://fpl.example.com"


def test_unconfigured_origin_gets_no_allow_header_on_preflight(cors_reload):
    from fastapi.testclient import TestClient

    m = cors_reload("https://fpl.example.com")
    c = TestClient(m.app)
    r = c.options("/api/solve", headers={
        "Origin": "https://evil.example.net",
        "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in r.headers


def test_unconfigured_origin_gets_no_allow_header_on_plain_get(cors_reload):
    from fastapi.testclient import TestClient

    m = cors_reload("https://fpl.example.com")
    c = TestClient(m.app)
    r = c.get("/api/health", headers={"Origin": "https://evil.example.net"})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers


def test_preflight_allows_only_get_post_options(cors_reload):
    from fastapi.testclient import TestClient

    m = cors_reload("https://fpl.example.com")
    c = TestClient(m.app)
    r = c.options("/api/solve", headers={
        "Origin": "https://fpl.example.com",
        "Access-Control-Request-Method": "POST",
    })
    methods = {x.strip() for x in r.headers.get("access-control-allow-methods", "").split(",")}
    assert methods == {"GET", "POST", "OPTIONS"}


def test_preflight_allows_x_api_key_and_content_type_headers(cors_reload):
    from fastapi.testclient import TestClient

    m = cors_reload("https://fpl.example.com")
    c = TestClient(m.app)
    r = c.options("/api/solve", headers={
        "Origin": "https://fpl.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "x-api-key, content-type",
    })
    allowed = r.headers.get("access-control-allow-headers", "").lower()
    assert "x-api-key" in allowed
    assert "content-type" in allowed


def test_unset_env_allows_local_dev_origin_and_denies_others(cors_reload):
    from fastapi.testclient import TestClient

    m = cors_reload(None)
    c = TestClient(m.app)
    ok = c.options("/api/solve", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    })
    bad = c.options("/api/solve", headers={
        "Origin": "https://evil.example.net",
        "Access-Control-Request-Method": "POST",
    })
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


def test_wildcard_origin_refuses_to_boot(cors_reload):
    with pytest.raises(RuntimeError, match="FPL_CORS_ORIGINS"):
        cors_reload("*")


def test_wildcard_among_real_origins_also_refuses_to_boot(cors_reload):
    with pytest.raises(RuntimeError, match="FPL_CORS_ORIGINS"):
        cors_reload("https://fpl.example.com,*")


# ------------------------------------------------------------- solve cache (REL-05)
#
# `_cache_get`/`_cache_put` are exercised directly for the deterministic
# bounding/eviction/TTL/invalidation cases, and through TestClient for the
# overlapping-refresh case, per the plan's own division of labour.


def test_cache_bounded_at_max_entries():
    import api.main as m

    for i in range(m.SOLVE_CACHE_MAX + 10):
        m._cache_put(f"key-{i}", {"i": i})
    assert len(m._solve_cache) == m.SOLVE_CACHE_MAX


def test_cache_eviction_is_least_recently_used_not_least_recently_inserted():
    import api.main as m

    for i in range(m.SOLVE_CACHE_MAX):
        m._cache_put(f"key-{i}", {"i": i})

    # Touch the earliest key so it becomes the most-recently-used entry.
    assert m._cache_get("key-0") == {"i": 0}

    # One more distinct key overflows the cache by one.
    m._cache_put("key-overflow", {"i": "overflow"})

    assert len(m._solve_cache) == m.SOLVE_CACHE_MAX
    assert m._cache_get("key-0") == {"i": 0}      # survived -- was just touched
    assert m._cache_get("key-1") is None          # evicted -- oldest untouched entry


def test_cache_entry_older_than_ttl_is_a_miss(monkeypatch):
    import api.main as m

    fake_now = {"t": 1_000_000.0}
    monkeypatch.setattr(m.time, "time", lambda: fake_now["t"])
    m._cache_put("ttl-key", {"v": 1})

    fake_now["t"] += m.SOLVE_CACHE_TTL_S + 1
    assert m._cache_get("ttl-key") is None


def test_solve_cache_clear_still_empties_the_ordereddict():
    import api.main as m

    m._cache_put("k", {"v": 1})
    assert len(m._solve_cache) == 1
    m._solve_cache.clear()
    assert len(m._solve_cache) == 0


def _one_event_boot() -> dict:
    return {"events": [{"id": 1, "is_next": True, "finished": False,
                        "deadline_time": "2026-01-01T00:00:00Z"}]}


def test_pool_version_increments_by_one_per_successful_refresh(monkeypatch):
    import api.main as m

    boot = _one_event_boot()
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))

    before = m._state["pool_version"]
    m._refresh(force=True)
    assert m._state["pool_version"] == before + 1
    m._refresh(force=True)
    assert m._state["pool_version"] == before + 2


def test_pool_version_unchanged_when_refresh_short_circuits(monkeypatch):
    import api.main as m

    boot = _one_event_boot()
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))

    m._refresh(force=True)
    version_after_load = m._state["pool_version"]

    m._refresh()  # not forced, not stale, boot already loaded -> short-circuits
    assert m._state["pool_version"] == version_after_load


def test_payload_cached_before_a_refresh_is_unreachable_after_it(monkeypatch):
    """Direct proof of the invalidation guarantee: a payload stored under a
    key containing the pre-refresh pool version can never be returned once
    `_refresh` has bumped the version -- the clear empties it outright, and
    even if it hadn't, no post-refresh request could construct that key
    again, because every fresh key embeds the NEW pool_version."""
    import api.main as m

    boot = _one_event_boot()
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))

    pre_version = m._state["pool_version"]
    pre_key = f"gw1-v{pre_version}"
    m._cache_put(pre_key, {"stale": True})
    assert m._cache_get(pre_key) == {"stale": True}

    m._refresh(force=True)
    post_version = m._state["pool_version"]
    assert post_version == pre_version + 1

    assert m._cache_get(pre_key) is None
    post_key = f"gw1-v{post_version}"
    assert m._cache_get(post_key) is None  # never populated post-refresh


def test_concurrent_solve_overlapping_refresh_stays_within_bound(monkeypatch):
    from fastapi.testclient import TestClient
    from test_api import fake_boot, fake_pool

    import api.main as m

    boot = fake_boot()
    pool = fake_pool(boot)

    def slow_pool(horizon=1):
        time_mod.sleep(0.02)   # widen the overlap window deterministically
        return pool, 1, boot

    monkeypatch.setattr(m, "_pool", slow_pool)
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)

    c = TestClient(m.app)

    def worker(i: int):
        return c.post("/api/solve", json={"horizon": 1, "free_transfers": i % 2})

    def refresher():
        time_mod.sleep(0.01)  # let some solve() calls start before it lands
        m._refresh(force=True)

    with ThreadPoolExecutor(max_workers=9) as ex:
        futures = [ex.submit(worker, i) for i in range(20)]
        refresh_future = ex.submit(refresher)
        results = [f.result() for f in as_completed(futures)]
        refresh_future.result()

    assert len(results) == 20
    assert all(r.status_code == 200 for r in results)
    assert len(m._solve_cache) <= m.SOLVE_CACHE_MAX
