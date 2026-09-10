"""Cron reliability + secrets gates (REL-02, OBS-03, SEC-03).

Task 1: retry/backoff and atomic writes on `data.snapshot.take_snapshot`, and
`ops.notify.report`'s never-raise / redaction contract.
Task 2 extends this module with the cron-script failure-path tests.
Task 3 extends this module with the `.env` / `config.load_dotenv` gates.
"""
from __future__ import annotations

import json
import os

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


# ------------------------------------------------------- snapshot catch-up (D-08)


def test_catchup_script_is_syntactically_valid():
    import subprocess

    script = config.ROOT / "scripts" / "snapshot_catchup.sh"
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0
    assert os.access(script, os.X_OK)


def test_catchup_reports_missing_days_without_capturing(tmp_path):
    import datetime as dt
    import subprocess

    today = dt.datetime.now(dt.timezone.utc).date()
    d1 = (today - dt.timedelta(days=5)).isoformat()
    d2 = (today - dt.timedelta(days=2)).isoformat()
    (tmp_path / f"{d1}.parquet").write_bytes(b"not a real parquet, existence is all that matters")
    (tmp_path / f"{d2}.parquet").write_bytes(b"not a real parquet, existence is all that matters")

    env = dict(os.environ)
    env["FPL_SNAPSHOT_DIR"] = str(tmp_path)

    result = subprocess.run(
        ["bash", str(config.ROOT / "scripts" / "snapshot_catchup.sh"), "--report-only"],
        cwd=str(config.ROOT), env=env, capture_output=True, text=True,
    )

    assert result.returncode == 0
    span_days = (today - dt.date.fromisoformat(d1)).days + 1
    missing_days = span_days - 2
    assert "days missing" in result.stdout
    assert f"({missing_days} days missing)" in result.stdout
    parquets = sorted(p.name for p in tmp_path.glob("*.parquet"))
    assert parquets == [f"{d1}.parquet", f"{d2}.parquet"]


def test_catchup_is_a_noop_when_today_exists(tmp_path):
    import datetime as dt
    import subprocess

    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    (tmp_path / f"{today}.parquet").write_bytes(b"not a real parquet, existence is all that matters")

    env = dict(os.environ)
    env["FPL_SNAPSHOT_DIR"] = str(tmp_path)

    result = subprocess.run(
        ["bash", str(config.ROOT / "scripts" / "snapshot_catchup.sh")],
        cwd=str(config.ROOT), env=env, capture_output=True, text=True,
    )

    assert result.returncode == 0
    assert "already present" in result.stdout
    parquets = list(tmp_path.glob("*.parquet"))
    assert len(parquets) == 1
    assert parquets[0].name == f"{today}.parquet"


# --------------------------------------------------------------- cron scripts


def test_daily_and_weekly_scripts_parse_and_are_executable():
    import subprocess

    for name in ("daily.sh", "weekly.sh"):
        script = config.ROOT / "scripts" / name
        assert subprocess.run(["bash", "-n", str(script)]).returncode == 0
        assert os.access(script, os.X_OK)


def test_daily_sh_failure_is_non_zero_notifies_once_and_lets_later_steps_run(tmp_path, monkeypatch):
    """A stub interpreter fails only the price-training step; the script must
    still exit non-zero, the two later independent steps must still run, and
    exactly one alert record must name the failing step."""
    import stat
    import subprocess

    real_python = "/home/sraja/miniconda3/envs/python314/bin/python"
    invocation_log = tmp_path / "invocations.log"
    alert_log = tmp_path / "alerts.jsonl"

    stub = tmp_path / "stub_python"
    stub.write_text(f"""#!/usr/bin/env bash
echo "$@" >> "{invocation_log}"
if [ "$1" = "-m" ] && [ "$2" = "models.price" ] && [ "$3" = "--train" ]; then
  exit 3
fi
if [ "$1" = "-m" ] && [ "$2" = "ops.notify" ]; then
  exec {real_python} "$@"
fi
exit 0
""")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)

    env = dict(os.environ)
    env["PYTHON"] = str(stub)
    env["FPL_ALERT_LOG"] = str(alert_log)
    env.pop("FPL_ALERT_WEBHOOK", None)
    env["PYTHONPATH"] = str(config.ROOT)

    result = subprocess.run(
        ["bash", str(config.ROOT / "scripts" / "daily.sh")],
        cwd=str(config.ROOT), env=env, capture_output=True, text=True,
    )

    assert result.returncode != 0
    lines = [line for line in invocation_log.read_text().splitlines() if line.strip()]
    assert "-m models.price --train" in lines
    assert "-m models.price" in lines
    assert "-m predict.scoreboard" in lines
    alerts = _read_alerts(tmp_path)
    assert len(alerts) == 1
    assert alerts[0]["step"] == "models.price-train"


# ------------------------------------------------------------- SEC-03: .env


def test_env_example_is_tracked_and_env_is_ignored():
    import subprocess

    env_example = config.ROOT / ".env.example"
    assert env_example.exists()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env.example"],
        cwd=str(config.ROOT), capture_output=True,
    )
    assert tracked.returncode == 0
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=str(config.ROOT))
    assert ignored.returncode == 0


def test_env_example_lines_are_keys_with_no_assigned_value():
    import re

    env_example = config.ROOT / ".env.example"
    with open(env_example, encoding="utf-8") as f:
        lines = f.read().splitlines()
    key_line_re = re.compile(r"^[A-Z_][A-Z0-9_]*=$")
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert key_line_re.match(stripped), f"not a bare KEY= line: {stripped!r}"


def test_env_example_names_every_expected_key():
    env_example = config.ROOT / ".env.example"
    with open(env_example, encoding="utf-8") as f:
        text = f.read()
    for key in (
        "FPL_API_KEYS", "ODDS_API_KEY", "FPL_CORS_ORIGINS", "FPL_ALERT_WEBHOOK",
        "FPL_ALERT_LOG", "FPL_FIXTURE_DIR", "FPL_FIXTURE_DATA_DIR",
    ):
        assert f"{key}=" in text, f"{key} missing from .env.example"


def test_load_dotenv_sets_an_unset_key(tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text("SOME_NEW_VAR=hello\n")
    envfile.chmod(0o600)
    monkeypatch.delenv("SOME_NEW_VAR", raising=False)

    count = config.load_dotenv(envfile)

    assert count == 1
    assert os.environ["SOME_NEW_VAR"] == "hello"


def test_load_dotenv_never_overwrites_an_already_set_key(tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text("ALREADY_SET_VAR=from_file\n")
    envfile.chmod(0o600)
    monkeypatch.setenv("ALREADY_SET_VAR", "from_process_env")

    count = config.load_dotenv(envfile)

    assert count == 0
    assert os.environ["ALREADY_SET_VAR"] == "from_process_env"


def test_load_dotenv_skips_a_malformed_line_without_raising(tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text("this line has no equals sign\nGOOD_VAR=value\n")
    envfile.chmod(0o600)
    monkeypatch.delenv("GOOD_VAR", raising=False)

    count = config.load_dotenv(envfile)

    assert count == 1
    assert os.environ["GOOD_VAR"] == "value"


def test_load_dotenv_warns_on_mode_0644_but_not_on_mode_0600(tmp_path, capsys, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text("X=1\n")
    monkeypatch.delenv("X", raising=False)

    envfile.chmod(0o644)
    config.load_dotenv(envfile)
    assert "0o644" in capsys.readouterr().err

    envfile.chmod(0o600)
    config.load_dotenv(envfile)
    assert capsys.readouterr().err == ""


def test_load_dotenv_strips_one_layer_of_matching_quotes(tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text('QUOTED_VAR="quoted value"\n')
    envfile.chmod(0o600)
    monkeypatch.delenv("QUOTED_VAR", raising=False)

    config.load_dotenv(envfile)

    assert os.environ["QUOTED_VAR"] == "quoted value"


def test_load_dotenv_missing_file_returns_zero_and_does_not_raise(tmp_path):
    missing = tmp_path / "does-not-exist" / ".env"
    assert config.load_dotenv(missing) == 0


@pytest.mark.skipif(not (config.ROOT / ".env").exists(), reason="no .env at repo root")
def test_real_dotenv_if_present_is_mode_0600():
    import stat as stat_mod

    mode = stat_mod.S_IMODE((config.ROOT / ".env").stat().st_mode)
    assert mode == 0o600


def test_workflow_secret_assignments_all_use_a_secrets_expression():
    """Every workflow line that assigns a project secret-carrying env var must
    do so via a GitHub `secrets.` expression, never an inline literal. Counts
    the assigning lines and the subset referencing `secrets.` and asserts the
    two counts are equal, so the assertion holds vacuously (and correctly)
    when there are none."""
    import re

    secret_names = (
        "FPL_API_KEYS", "ODDS_API_KEY", "FPL_CORS_ORIGINS", "FPL_ALERT_WEBHOOK",
    )
    assign_re = re.compile(
        r"^\s*(" + "|".join(secret_names) + r")\s*:\s*(.+)$"
    )
    workflow_dir = config.ROOT / ".github" / "workflows"
    total_assignments = 0
    secrets_assignments = 0
    for path in sorted(workflow_dir.glob("*.yml")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = assign_re.match(line)
                if not m:
                    continue
                total_assignments += 1
                if "secrets." in m.group(2):
                    secrets_assignments += 1
    assert total_assignments == secrets_assignments
