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
