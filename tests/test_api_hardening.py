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
import threading
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
        return m.PoolSnapshot(pool, 1, boot, 0)

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


# ------------------------------------------------ REL-05 TOCTOU regression (06-07)
#
# Every test above that touches `_pool` replaces it with a version-independent
# stub -- exactly why none of them can see the race this section closes.
# 06-04-SUMMARY.md recorded reading `_state['pool_version']` under a SEPARATE,
# later `with _lock` block inside `solve()`/`plan()` as a deliberate decision;
# 06-VERIFICATION.md confirmed that shape lets a refresh landing in the gap
# tag a pre-refresh payload with the post-refresh version. These tests drive
# the REAL `_pool()`/`_gw_pools_meta()`/`_refresh()` interleaving instead of
# replacing any of them with a stub.


class _WindowLock:
    """Wraps a real `threading.Lock`, exposing exactly the `__enter__`/
    `__exit__` protocol `api/main.py` uses on `_lock` -- nothing else is
    added to the interface `_pool()`/`_gw_pools_meta()`/`_refresh()` rely on.

    Reproduces the interleaving the pre-fix, two-acquisition handler was
    vulnerable to, deterministically and with no sleep: `on_window` fires at
    the exact instant the old code had its window open -- the lock just
    released, a second reader about to re-acquire it. The `fired` latch
    stops the callback recursing when `on_window` itself takes this same
    lock (as `_refresh` does): the first firing sets `fired`, so every later
    `__exit__` -- including ones nested inside `on_window` -- computes
    `armed and not fired` as `False` and never fires again.
    """

    def __init__(self, on_window):
        self._real = threading.Lock()
        self.on_window = on_window
        self.armed = False
        self.fired = False

    def __enter__(self):
        self._real.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        fire = self.armed and not self.fired
        if fire:
            self.fired = True
        self._real.release()
        if fire:
            self.on_window()
        return False


def _install_race_window(monkeypatch, m):
    """Shared setup for this section's tests. Patches exactly three names on
    `api.main` and returns the installed `_WindowLock`:

      - `_load_live`: a generation-tagged loader. Each call increments a
        counter and rewrites every element's `web_name` to `f"G{gen}-
        {code}"`, so a pool's generation is visible in a response body.
        Generation 0 is what a request starts with; generation 1 is what
        the window's injected refresh installs.
      - `_intervals_artifact`: returns None, so `_with_bands` is a no-op and
        the response body never depends on whether a developer machine
        happens to have a real intervals artifact on disk.
      - `_lock`: a fresh `_WindowLock` whose `on_window` calls
        `m._refresh(force=True)`.

    Deliberately does NOT monkeypatch `_pool`, `_gw_pools_meta`,
    `_gw_pools_locked`, `_refresh`, `_cache_get` or `_cache_put` -- those are
    the code paths under test. A test that replaces the module's own pool
    accessor with a version-independent stub proves nothing about the code
    path this bug lives in, which is exactly why five pre-existing
    concurrency tests in this repository never saw it.
    """
    from test_api import fake_boot

    n = {"gen": -1}

    def _generation_tagged_load_live(force=True):
        n["gen"] += 1
        boot = fake_boot()
        for el in boot["elements"]:
            el["web_name"] = f"G{n['gen']}-{el['code']}"
        return boot, []

    monkeypatch.setattr(m, "_load_live", _generation_tagged_load_live)
    monkeypatch.setattr(m, "_intervals_artifact", lambda: None)
    window = _WindowLock(lambda: m._refresh(force=True))
    monkeypatch.setattr(m, "_lock", window)
    return window


def _arming_pool_builder(window, fake_pool):
    """A wrapper around a pool builder (`build_pool`/`_gw_pool`) that arms
    `window` on its first call while the window has not yet fired -- a
    dependency of `_pool()`/`_gw_pools_locked()`, never `_pool`,
    `_gw_pools_meta` or `_gw_pools_locked` themselves. Arming from inside the
    builder is what guarantees the callback fires on the exit of the
    snapshot helper's own critical section, not some earlier one."""
    def build(boot, fixtures, gw, artifact):
        if not window.fired:
            window.armed = True
        return fake_pool(boot)
    return build


def test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key(monkeypatch):
    """The stub-free REL-05 regression proof. Two byte-identical /api/solve
    requests, with a refresh injected exactly where the pre-fix, two-
    acquisition handler left its window open between fetching the pool and
    separately re-reading `_state['pool_version']` for the cache key.

    Run against the pre-fix implementation, this test failed with:
      STALE PAYLOAD SERVED AFTER A REFRESH: ['G0-1001', 'G0-1002', ...]
    -- the first request's generation-0 payload was cached under the
    post-refresh (generation-1) version, so the second, byte-identical
    request hit that stale entry instead of computing generation 1. Post-fix,
    the first request's payload is tagged with the PRE-refresh version, the
    second request's key misses, and generation 1 is computed and returned.
    """
    from fastapi.testclient import TestClient
    from test_api import fake_pool

    import api.main as m

    window = _install_race_window(monkeypatch, m)
    monkeypatch.setattr(m, "build_pool", _arming_pool_builder(window, fake_pool))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)

    # The gate's own guarantee that it is driving the real accessor, not a
    # stub replacing it -- the difference between this test and every
    # concurrency test that came before it.
    assert m._pool.__name__ == "_pool"
    assert m._pool.__module__ == "api.main"

    c = TestClient(m.app)
    body = {"horizon": 1}

    first = c.post("/api/solve", json=body)
    assert first.status_code == 200, first.text
    first_names = [p["name"] for p in first.json()["squad"]]
    assert first_names and all(n.startswith("G0-") for n in first_names), first_names

    second = c.post("/api/solve", json=body)
    assert second.status_code == 200, second.text
    second_names = [p["name"] for p in second.json()["squad"]]
    assert all(n.startswith("G1-") for n in second_names), (
        f"STALE PAYLOAD SERVED AFTER A REFRESH: {second_names}"
    )


def test_the_window_hook_opens_a_real_gap_for_a_two_acquisition_reader(monkeypatch):
    """Non-vacuity control. The window hook is proven to genuinely open the
    race window: a reader that deliberately performs the OLD two-acquisition
    shape the production code no longer performs -- read the pool via
    `_pool()`, then separately re-acquire the lock to read `pool_version` and
    `boot` from `_state` -- observes a version exactly one greater than the
    snapshot's and a different bootstrap object. If this test ever stops
    observing a difference, the gate above has gone vacuous: the window
    never opened, and a green result there would mean nothing.
    """
    from test_api import fake_pool

    import api.main as m

    window = _install_race_window(monkeypatch, m)
    monkeypatch.setattr(m, "build_pool", _arming_pool_builder(window, fake_pool))

    snap = m._pool(1)

    # Deliberately reproduce the pre-fix two-acquisition read shape the
    # production code no longer performs.
    with m._lock:
        later_version = m._state["pool_version"]
        later_boot = m._state["boot"]

    assert later_version == snap.version + 1, (snap.version, later_version)
    assert later_boot is not snap.boot
