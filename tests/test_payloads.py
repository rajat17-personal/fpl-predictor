"""Proof of the fail-loudly spine: a missing/corrupt/schema-drifted FPL payload
must produce one actionable message, one parseable JSON log line, and a 503 on
/api/ready while /api/health keeps answering 200. Task 2 extends this module
with pydantic schema-validation behavior cases."""
from __future__ import annotations

import copy
import json
import logging
import pathlib
import sys

import pytest

import config
from ops.jsonio import PayloadError, read_json, write_json
from ops.payloads import validate_bootstrap, validate_fixtures

# tests/ has no __init__.py -- pytest's default prepend import mode makes
# `from test_api import fake_boot` resolve.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_api import fake_boot  # noqa: E402

_NORMAL_FIXTURE_DIR = config.ROOT / "e2e" / "fixtures" / "v1" / "normal" / "api"


def _load_committed_bootstrap() -> dict:
    return read_json(_NORMAL_FIXTURE_DIR / "bootstrap-static.json", what="committed fixture bootstrap")


def _load_committed_fixtures() -> list:
    return read_json(_NORMAL_FIXTURE_DIR / "fixtures.json", what="committed fixture fixtures")

# ---------------------------------------------------------------- read_json


def test_missing_file_raises_payload_error_with_path_and_remedy(tmp_path):
    missing = tmp_path / "bootstrap-static.json"
    with pytest.raises(PayloadError) as exc_info:
        read_json(missing, what="FPL bootstrap-static payload", remedy="run `python -m data.ingest`")
    msg = str(exc_info.value)
    assert str(missing.resolve()) in msg
    assert "run `python -m data.ingest`" in msg
    assert "\n" not in msg


def test_zero_byte_file_raises_payload_error_with_path_and_position(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("")
    with pytest.raises(PayloadError) as exc_info:
        read_json(empty, what="FPL bootstrap-static payload", remedy="run `python -m data.ingest`")
    msg = str(exc_info.value)
    assert str(empty.resolve()) in msg
    assert "line" in msg.lower()
    assert "run `python -m data.ingest`" in msg


def test_truncated_file_raises_payload_error_with_line_and_column(tmp_path):
    truncated = tmp_path / "truncated.json"
    truncated.write_text('{"elements": [{"id": 1,')
    with pytest.raises(PayloadError) as exc_info:
        read_json(truncated, what="FPL bootstrap-static payload", remedy="run `python -m data.ingest`")
    msg = str(exc_info.value)
    assert str(truncated.resolve()) in msg
    assert "line" in msg.lower() and "column" in msg.lower()


def test_read_json_no_remedy_still_gives_actionable_message(tmp_path):
    missing = tmp_path / "gone.json"
    with pytest.raises(PayloadError) as exc_info:
        read_json(missing, what="some payload")
    msg = str(exc_info.value)
    assert str(missing.resolve()) in msg
    assert "some payload" in msg


def test_read_json_closes_the_file_descriptor_even_on_decode_failure(tmp_path):
    """Binding via `with` means the descriptor is released even when json.load
    raises — provable by successfully deleting the file right after (Windows
    would refuse to delete an open file; on POSIX this at least proves no
    lingering handle keeps the file busy for subsequent writers)."""
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(PayloadError):
        read_json(bad, what="test payload")
    bad.unlink()  # would fail if a descriptor were still open on some platforms
    assert not bad.exists()


# ---------------------------------------------------------------- write_json


def test_write_json_round_trips(tmp_path):
    target = tmp_path / "out.json"
    write_json({"a": 1, "b": [1, 2, 3]}, target)
    assert json.loads(target.read_text()) == {"a": 1, "b": [1, 2, 3]}


def test_write_json_leaves_prior_content_intact_on_simulated_mid_write_crash(tmp_path, monkeypatch):
    target = tmp_path / "out.json"
    target.write_text(json.dumps({"prior": True}))

    import json as _json_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated mid-write crash")

    monkeypatch.setattr(_json_module, "dump", _boom)
    with pytest.raises(RuntimeError):
        write_json({"new": True}, target)

    # Prior content survived; no stray temp file left behind.
    assert json.loads(target.read_text()) == {"prior": True}
    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_write_json_last_writer_wins_whole_no_truncated_file(tmp_path):
    """Two 'writers' targeting the same path: the last os.replace wins whole,
    never a truncated/interleaved file."""
    target = tmp_path / "shared.json"
    write_json({"writer": 1, "payload": list(range(200))}, target)
    write_json({"writer": 2, "payload": list(range(500))}, target)
    body = json.loads(target.read_text())
    assert body["writer"] == 2
    assert len(body["payload"]) == 500


# ---------------------------------------------------------------- end-to-end


def _fake_boot_missing_file_load(*args, **kwargs):
    from ops.jsonio import PayloadError as _PE
    raise _PE("FPL bootstrap-static payload: /fake/path/bootstrap-static.json: "
             "file not found: run `python -m data.ingest` to regenerate the live cache")


def test_health_stays_up_and_ready_returns_503_on_payload_failure(monkeypatch, capsys):
    from fastapi.testclient import TestClient

    import api.main as m
    from ops.jsonlog import configure_logging

    # api.main.configure_logging("api") already ran once at module-import time,
    # binding the handler's stream to the real sys.stderr in effect back then —
    # which predates (and bypasses) capsys's own stderr swap. Re-run it now,
    # with capsys active, so the handler writes to the fixture-captured stream.
    configure_logging("api")
    monkeypatch.setattr(m, "_load_live", _fake_boot_missing_file_load)
    c = TestClient(m.app)

    health = c.get("/api/health")
    assert health.status_code == 200
    assert set(health.json().keys()) == {"ok", "gw", "pool_age_s"}

    ready = c.get("/api/ready")
    assert ready.status_code == 503
    body = ready.json()
    assert body["ready"] is False
    assert "bootstrap-static.json" in body["reason"]

    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert lines, "expected at least one structured log line on stderr"
    parsed = [json.loads(line) for line in lines]
    assert any(obj.get("event") == "pool.refresh_failed" for obj in parsed)


def test_jsonlog_configure_logging_is_idempotent(capsys):
    from ops.jsonlog import configure_logging, log_event

    root = logging.getLogger()
    configure_logging("test-service")
    configure_logging("test-service")  # second call must not duplicate the handler

    handler_count = sum(1 for h in root.handlers if getattr(h, "formatter", None)
                        and h.formatter.__class__.__name__ == "JsonFormatter")
    assert handler_count == 1

    log_event(logging.getLogger("test.idempotent"), "test.event")
    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["event"] == "test.event"


# ---------------------------------------------------------------- ops.payloads (Task 2)


def test_validate_bootstrap_synthetic_live_payload_passes():
    validate_bootstrap(fake_boot(), source="synthetic", profile="live")


def test_validate_bootstrap_committed_fixture_passes_under_fixture_profile():
    validate_bootstrap(_load_committed_bootstrap(), source="committed-fixture", profile="fixture")


def test_validate_bootstrap_committed_fixture_fails_under_live_profile():
    with pytest.raises(PayloadError) as exc_info:
        validate_bootstrap(_load_committed_bootstrap(), source="committed-fixture", profile="live")
    assert "transfers_in_event" in str(exc_info.value)


def test_validate_fixtures_committed_fixture_passes_all_380_entries():
    fixtures = _load_committed_fixtures()
    assert len(fixtures) == 380
    validate_fixtures(fixtures, source="committed-fixture")


def test_validate_bootstrap_missing_now_cost_names_elements_and_field():
    boot = copy.deepcopy(fake_boot())
    del boot["elements"][0]["now_cost"]
    with pytest.raises(PayloadError) as exc_info:
        validate_bootstrap(boot, source="mutated", profile="live")
    msg = str(exc_info.value)
    assert "elements" in msg
    assert "now_cost" in msg


def test_validate_bootstrap_empty_elements_list_names_elements():
    boot = copy.deepcopy(fake_boot())
    boot["elements"] = []
    with pytest.raises(PayloadError) as exc_info:
        validate_bootstrap(boot, source="mutated", profile="fixture")
    assert "elements" in str(exc_info.value)


def test_validate_bootstrap_list_input_raises_payload_error_not_type_error():
    with pytest.raises(PayloadError):
        validate_bootstrap([1, 2, 3], source="mutated", profile="fixture")


def test_validate_fixtures_uncoercible_difficulty_names_index_and_field():
    fixtures = copy.deepcopy(_load_committed_fixtures())
    fixtures[0]["team_h_difficulty"] = "not-a-number"
    with pytest.raises(PayloadError) as exc_info:
        validate_fixtures(fixtures, source="mutated")
    msg = str(exc_info.value)
    assert "0" in msg
    assert "team_h_difficulty" in msg


def test_validate_bootstrap_rejects_unknown_profile():
    with pytest.raises(ValueError):
        validate_bootstrap(fake_boot(), source="synthetic", profile="bogus")


def test_predict_live_wires_validators(monkeypatch):
    import predict.live as live
    assert "validate_bootstrap" in live.__dict__
    assert "validate_fixtures" in live.__dict__


def test_api_main_fixture_loader_uses_fixture_profile():
    import inspect

    import api.main as m
    src = inspect.getsource(m._load_live_fixture)
    assert 'profile="fixture"' in src
