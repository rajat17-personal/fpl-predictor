"""Locks the OBS-02 liveness/readiness contract: `/api/health` never blocks on
the pool lock and always answers the same three-key body regardless of pool
state; `/api/ready` is a distinct, tested probe that is 503 until a pool has
actually loaded. Also proves structured logging never garbles a line under
concurrent failure."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from test_api import fake_boot


def _raise_payload_error(force=True):
    from ops.jsonio import PayloadError
    raise PayloadError("FPL bootstrap-static payload: /fake/path: file not found")


# ---------------------------------------------------------------- liveness


def test_health_returns_three_keys_when_state_is_pristine():
    from fastapi.testclient import TestClient

    import api.main as m

    c = TestClient(m.app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert set(r.json().keys()) == {"ok", "gw", "pool_age_s"}


def test_health_returns_three_keys_after_a_failed_refresh(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as m

    monkeypatch.setattr(m, "_load_live", _raise_payload_error)
    c = TestClient(m.app)
    with pytest.raises(Exception):
        m._refresh()
    r = c.get("/api/health")
    assert r.status_code == 200
    assert set(r.json().keys()) == {"ok", "gw", "pool_age_s"}


def test_health_never_blocks_on_the_pool_lock():
    """A liveness probe that blocks on the pool lock would restart a healthy
    container under load — /api/health must answer even while another thread
    holds api.main._lock."""
    from fastapi.testclient import TestClient

    import api.main as m

    c = TestClient(m.app)
    with m._lock:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(c.get, "/api/health")
            r = future.result(timeout=2)
    assert r.status_code == 200
    assert set(r.json().keys()) == {"ok", "gw", "pool_age_s"}


# ---------------------------------------------------------------- readiness


def test_ready_returns_503_with_reason_before_any_successful_load(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as m

    monkeypatch.setattr(m, "_load_live", _raise_payload_error)
    c = TestClient(m.app)
    r = c.get("/api/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["ready"] is False
    assert body["reason"]


def test_ready_returns_503_after_a_failed_load(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as m

    monkeypatch.setattr(m, "_load_live", _raise_payload_error)
    c = TestClient(m.app)
    c.get("/api/ready")  # first failure
    r = c.get("/api/ready")  # still failing
    assert r.status_code == 503
    assert r.json()["reason"]


def test_ready_returns_200_with_ready_true_after_a_successful_refresh(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as m

    boot = fake_boot()
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))
    c = TestClient(m.app)
    r = c.get("/api/ready")
    assert r.status_code == 200
    assert r.json()["ready"] is True


def test_ready_and_health_return_different_status_codes_when_not_ready(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as m

    monkeypatch.setattr(m, "_load_live", _raise_payload_error)
    c = TestClient(m.app)
    ready = c.get("/api/ready")
    health = c.get("/api/health")
    assert ready.status_code == 503
    assert health.status_code == 200
    assert ready.status_code != health.status_code


# ---------------------------------------------------------------- logging concurrency


def test_concurrent_ready_failures_never_garble_a_log_line(monkeypatch, capsys):
    from fastapi.testclient import TestClient

    import api.main as m
    from ops.jsonlog import configure_logging

    # Re-bind the handler's stream to capsys's active stderr (api.main's own
    # module-level configure_logging("api") ran at import time, before this
    # fixture swapped sys.stderr).
    configure_logging("api")
    monkeypatch.setattr(m, "_load_live", _raise_payload_error)
    c = TestClient(m.app)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(c.get, "/api/ready") for _ in range(20)]
        results = [f.result(timeout=5) for f in futures]

    assert len(results) == 20
    assert all(r.status_code == 503 for r in results)

    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert lines
    for line in lines:
        obj = json.loads(line)  # would raise on any interleaved/garbled record
        assert "event" in obj
