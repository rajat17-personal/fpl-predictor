"""Cron reliability + secrets gates (REL-02, OBS-03, SEC-03).

Task 1: retry/backoff and atomic writes on `data.snapshot.take_snapshot`, and
`ops.notify.report`'s never-raise / redaction contract.
Task 2 extends this module with the cron-script failure-path tests.
Task 3 extends this module with the `.env` / `config.load_dotenv` gates.
"""
from __future__ import annotations

import json

import pytest
import responses

import config
import data.snapshot as snapshot
from ops.notify import report
from test_api import fake_boot

_BOOT_URL = f"{config.FPL_API}/bootstrap-static/"


@pytest.fixture(autouse=True)
def _isolate_snapshot_and_alerts(tmp_path, monkeypatch):
    """Every test in this module must never touch the real (irreplaceable)
    `data/snapshots/` archive, and must never append to the real alerts file."""
    monkeypatch.setattr(snapshot, "SNAP_DIR", tmp_path / "snapshots")
    monkeypatch.setenv("FPL_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    monkeypatch.delenv("FPL_ALERT_WEBHOOK", raising=False)
    monkeypatch.setattr(snapshot.time, "sleep", lambda *_a, **_k: None)
    return tmp_path


def _alerts_path(tmp_path):
    return tmp_path / "alerts.jsonl"


def _read_alerts(tmp_path):
    path = _alerts_path(tmp_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ------------------------------------------------------------- take_snapshot


@responses.activate
def test_snapshot_retries_503_503_then_succeeds(_isolate_snapshot_and_alerts):
    tmp_path = _isolate_snapshot_and_alerts
    boot = fake_boot()
    responses.add(responses.GET, _BOOT_URL, status=503)
    responses.add(responses.GET, _BOOT_URL, status=503)
    responses.add(responses.GET, _BOOT_URL, json=boot, status=200)

    df = snapshot.take_snapshot()

    assert len(responses.calls) == 3
    assert df is not None
    parquets = list((tmp_path / "snapshots").glob("*.parquet"))
    assert len(parquets) == 1
    assert _read_alerts(tmp_path) == []


@responses.activate
def test_snapshot_exhausts_retries_and_raises_without_writing_parquet(_isolate_snapshot_and_alerts):
    tmp_path = _isolate_snapshot_and_alerts
    responses.add(responses.GET, _BOOT_URL, status=503)
    responses.add(responses.GET, _BOOT_URL, status=503)

    with pytest.raises(Exception):
        snapshot.take_snapshot(retries=2)

    assert len(responses.calls) == 2
    parquets = list((tmp_path / "snapshots").glob("*.parquet"))
    assert parquets == []
    tmp_files = list((tmp_path / "snapshots").glob("*.tmp"))
    assert tmp_files == []


@responses.activate
def test_snapshot_404_is_not_retried(_isolate_snapshot_and_alerts):
    responses.add(responses.GET, _BOOT_URL, status=404)

    with pytest.raises(Exception):
        snapshot.take_snapshot()

    assert len(responses.calls) == 1


@responses.activate
def test_snapshot_existing_same_day_file_is_a_zero_request_noop(_isolate_snapshot_and_alerts):
    tmp_path = _isolate_snapshot_and_alerts
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir(parents=True)
    import datetime as dt
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    (snap_dir / f"{today}.parquet").write_bytes(b"not a real parquet, existence is all that matters")

    result = snapshot.take_snapshot()

    assert result is None
    assert len(responses.calls) == 0
    assert _read_alerts(tmp_path) == []


@responses.activate
def test_snapshot_force_true_overwrites_existing_same_day_file(_isolate_snapshot_and_alerts):
    tmp_path = _isolate_snapshot_and_alerts
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir(parents=True)
    import datetime as dt
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    out = snap_dir / f"{today}.parquet"
    out.write_bytes(b"stale")
    boot = fake_boot()
    responses.add(responses.GET, _BOOT_URL, json=boot, status=200)

    df = snapshot.take_snapshot(force=True)

    assert len(responses.calls) == 1
    assert df is not None
    assert out.stat().st_size > len(b"stale")


@responses.activate
def test_snapshot_final_failure_appends_exactly_one_alert_naming_the_job(_isolate_snapshot_and_alerts):
    tmp_path = _isolate_snapshot_and_alerts
    responses.add(responses.GET, _BOOT_URL, status=503)
    responses.add(responses.GET, _BOOT_URL, status=503)

    with pytest.raises(Exception):
        snapshot.take_snapshot(retries=2)

    alerts = _read_alerts(tmp_path)
    assert len(alerts) == 1
    assert alerts[0]["job"] == "snapshot"
    assert alerts[0]["step"] == "fetch"


# ------------------------------------------------------------------ ops.notify


def test_report_swallows_a_raising_webhook_and_still_writes_the_record(tmp_path, monkeypatch):
    monkeypatch.setenv("FPL_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setenv("FPL_ALERT_WEBHOOK", "https://example.invalid/hook")

    def _raise_post(*_a, **_k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("ops.notify.requests.post", _raise_post)

    result = report("daily", "price-train", "boom")

    assert result is None
    records = _read_alerts(tmp_path)
    assert len(records) == 1
    assert records[0]["step"] == "price-train"


def test_report_redacts_a_value_matching_an_fpl_api_keys_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("FPL_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    monkeypatch.delenv("FPL_ALERT_WEBHOOK", raising=False)
    monkeypatch.setenv("FPL_API_KEYS", "supersecretkey123")

    report("daily", "fetch", "failed", detail="supersecretkey123")

    records = _read_alerts(tmp_path)
    assert len(records) == 1
    assert records[0]["detail"] == "[redacted]"
    assert "supersecretkey123" not in json.dumps(records[0])


def test_report_never_raises_even_when_everything_is_broken(tmp_path, monkeypatch):
    monkeypatch.setenv("FPL_ALERT_LOG", str(tmp_path / "nonexistent" / "sub" / "alerts.jsonl"))
    monkeypatch.delenv("FPL_ALERT_WEBHOOK", raising=False)

    def _raise(*_a, **_k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("ops.notify.redact", _raise)

    result = report("daily", "fetch", "failed")

    assert result is None
