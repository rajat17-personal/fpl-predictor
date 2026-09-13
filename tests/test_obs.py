"""Locks the OBS-02 liveness/readiness contract: `/api/health` never blocks on
the pool lock and always answers the same three-key body regardless of pool
state; `/api/ready` is a distinct, tested probe that is 503 until a pool has
actually loaded. Also proves structured logging never garbles a line under
concurrent failure."""
from __future__ import annotations

import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import pytest
import responses

from test_api import (_SYNTHETIC_MANAGER, _team_urls, fake_boot, fake_picks,
                      fake_pool)


def _raise_payload_error(force=True):
    from ops.jsonio import PayloadError
    raise PayloadError("FPL bootstrap-static payload: /fake/path: file not found")


@pytest.fixture
def log_capture():
    """Attach a plain logging.StreamHandler over an io.StringIO carrying
    ops.jsonlog.JsonFormatter for the duration of one test, rather than
    relying on pytest's capsys -- the assertions then work identically
    whether or not pytest is capturing stderr. Removed at teardown; leaves
    api.main's own module-level configure_logging("api") handler untouched.

    Attached to the "api.main" logger specifically (the logger api/main.py's
    `_logger` and every `log_event` call use), not the root logger -- httpx
    (TestClient's transport) logs its own "HTTP Request: ..." access line,
    query string and all, on a sibling "httpx" logger, and a root-attached
    handler would pick that noise up too, contaminating substring assertions
    on the captured buffer with a line this plan's middleware never wrote.
    """
    from ops.jsonlog import JsonFormatter

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter("api"))
    logger = logging.getLogger("api.main")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield buf
    logger.removeHandler(handler)


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


# ---------------------------------------------------------------- http.request (OBS-01)
#
# One structured, secret-free JSON record per HTTP request, with a
# correlatable X-Request-ID echoed back to the caller. Captured via a plain
# StreamHandler over an io.StringIO carrying JsonFormatter (the log_capture
# fixture above), not capsys, so these assertions work identically whether or
# not pytest is capturing.


def _http_records(buf: io.StringIO) -> list[dict]:
    lines = [line for line in buf.getvalue().splitlines() if line.strip()]
    recs = [json.loads(line) for line in lines]  # raises on any garbled record
    return [r for r in recs if r.get("event") == "http.request"]


def test_single_request_produces_one_parseable_http_request_record(log_capture):
    from fastapi.testclient import TestClient

    import api.main as m

    c = TestClient(m.app)
    r = c.get("/api/health")
    assert r.status_code == 200

    recs = _http_records(log_capture)
    assert len(recs) == 1
    rec = recs[0]
    assert {"request_id", "method", "path", "status", "duration_ms"} <= rec.keys()
    assert rec["duration_ms"] >= 0
    assert rec["method"] == "GET"
    assert rec["path"] == "/api/health"
    assert rec["status"] == 200


def test_x_request_id_header_matches_the_logged_request_id(log_capture):
    from fastapi.testclient import TestClient

    import api.main as m

    c = TestClient(m.app)
    r = c.get("/api/health")
    header_id = r.headers.get("x-request-id")
    assert header_id

    rec = _http_records(log_capture)[0]
    assert rec["request_id"] == header_id


@responses.activate
def test_team_endpoint_logs_the_route_template_not_the_entry_id(monkeypatch, log_capture):
    from fastapi.testclient import TestClient

    import api.main as m

    entry = 6980093  # PROJECT.md: user's own FPL team id, used across fixtures
    boot = fake_boot()
    pool = fake_pool(boot)
    monkeypatch.setattr(m, "_pool", lambda horizon=1: m.PoolSnapshot(pool, 1, boot, 0))

    picks_url, summary_url, _ = _team_urls(entry, 1)
    responses.add(responses.GET, picks_url, json=fake_picks(boot), status=200)
    responses.add(responses.GET, summary_url, json=_SYNTHETIC_MANAGER, status=200)

    c = TestClient(m.app)
    r = c.get(f"/api/team/{entry}")
    assert r.status_code == 200

    rec = next(x for x in _http_records(log_capture) if x["status"] == 200)
    assert rec["path"] == "/api/team/{entry}"
    assert str(entry) not in rec["path"]


def test_query_string_is_never_logged(log_capture):
    from fastapi.testclient import TestClient

    import api.main as m

    c = TestClient(m.app)
    r = c.get("/api/health?foo=bar&api_key=totally-secret-token")
    assert r.status_code == 200

    out = log_capture.getvalue()
    assert "foo=bar" not in out
    assert "totally-secret-token" not in out


def test_api_key_never_appears_in_the_log_output(monkeypatch, log_capture):
    from fastapi.testclient import TestClient

    import api.main as m

    monkeypatch.setenv("FPL_API_KEYS", "sentinel-key-do-not-log")
    c = TestClient(m.app)
    r = c.get("/api/health", headers={"X-API-Key": "sentinel-key-do-not-log"})
    assert r.status_code == 200

    assert "sentinel-key-do-not-log" not in log_capture.getvalue()
    recs = _http_records(log_capture)
    assert any(rec["status"] == 200 for rec in recs)


def test_raising_route_logs_500_with_error_and_still_propagates(monkeypatch, log_capture):
    from fastapi.testclient import TestClient

    import api.main as m

    def _boom(force=True):
        raise RuntimeError("boom")

    monkeypatch.setattr(m, "_load_live", _boom)
    c = TestClient(m.app)
    with pytest.raises(RuntimeError, match="boom"):
        c.get("/api/meta")

    recs = [r for r in _http_records(log_capture) if r["status"] == 500]
    assert len(recs) == 1
    assert "error" in recs[0]


def test_20_concurrent_requests_yield_20_distinct_request_ids(log_capture):
    from fastapi.testclient import TestClient

    import api.main as m

    c = TestClient(m.app)
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(c.get, "/api/health") for _ in range(20)]
        results = [f.result(timeout=5) for f in futures]

    assert len(results) == 20
    assert all(r.status_code == 200 for r in results)

    recs = _http_records(log_capture)
    assert len(recs) == 20
    ids = {rec["request_id"] for rec in recs}
    assert len(ids) == 20
