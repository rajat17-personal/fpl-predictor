"""End-to-end + schema-convention tests for data.gw_capture (Phase 8).

Task 1 opens this file with the single end-to-end test proving the whole
capture path -- FPL API to build_table -- on one finished gameweek. Task 2
extends it with the gates that lock the four schema conventions (club-name,
player-name, position, completion) plus the layout and atomicity properties.

Plan 08-02 Task 1 extends this file further: the players_raw.csv /
fixtures.csv refresh and the payload field guard.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest
import responses

import config
import data.build_table as build_table
import data.gw_capture as gw_capture
from test_api import fake_boot

_BOOT_URL = f"{config.FPL_API}/bootstrap-static/"
_FIXTURES_URL = f"{config.FPL_API}/fixtures/"


@pytest.fixture(autouse=True)
def _isolate_raw_dir(tmp_path, monkeypatch):
    """Every test in this module must never touch the real (irreplaceable)
    data/raw/2026-27/ tree, must never make a real HTTP call, and must never
    leak an alert into the real alerts file -- mirrors tests/test_cron.py's
    shared bootstrap-fixture and alert-log isolation idiom."""
    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(gw_capture.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setenv("FPL_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    monkeypatch.delenv("FPL_ALERT_WEBHOOK", raising=False)
    return tmp_path


def _alerts_path(tmp_path):
    return tmp_path / "alerts.jsonl"


def _read_alerts(tmp_path):
    path = _alerts_path(tmp_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _elem_summary_url(pid: int) -> str:
    return f"{config.FPL_API}/element-summary/{pid}/"


def _history_row(pid: int, round_: int, **overrides) -> dict:
    """A fabricated element-summary history row carrying all 41 keys."""
    row = {k: 0 for k in gw_capture._HISTORY_KEYS}
    row.update({
        "element": pid,
        "round": round_,
        "fixture": 1000 + round_,
        "opponent_team": 2,
        "was_home": True,
        "kickoff_time": f"2026-08-{14 + round_:02d}T14:00:00Z",
        "value": 55,
        "selected": 100000,
    })
    row.update(overrides)
    return row


def _boot_with_finished_events(n_events: int = 3, *, data_checked: bool | None = None) -> dict:
    """fake_boot() with its single placeholder event replaced by `n_events`
    real finished + data-checked events carrying real deadline timestamps."""
    boot = fake_boot()
    dc = data_checked if data_checked is not None else True
    boot["events"] = [
        {"id": i, "finished": True, "data_checked": dc, "is_next": False,
         "deadline_time": f"2026-08-{14 + i:02d}T17:30:00Z"}
        for i in range(1, n_events + 1)
    ]
    return boot


def _register_bootstrap(boot: dict) -> None:
    responses.add(responses.GET, _BOOT_URL, json=boot, status=200)


def _fake_fixtures() -> list[dict]:
    """A minimal fixtures/ payload carrying the three columns
    build_table._join_fixture_difficulty reads, plus id."""
    return [
        {"id": 1, "event": 1, "team_h": 1, "team_a": 2,
         "team_h_difficulty": 3, "team_a_difficulty": 2,
         "kickoff_time": "2026-08-15T14:00:00Z", "finished": True},
    ]


def _register_fixtures(fixtures: list[dict] | None = None) -> list[dict]:
    fx = fixtures if fixtures is not None else _fake_fixtures()
    responses.add(responses.GET, _FIXTURES_URL, json=fx, status=200)
    return fx


def _register_histories(boot: dict, histories: dict) -> None:
    for el in boot["elements"]:
        responses.add(responses.GET, _elem_summary_url(el["id"]),
                       json={"history": histories.get(el["id"], [])}, status=200)


@responses.activate
def test_end_to_end_capture_reads_back_through_build_table():
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    summary = gw_capture.capture(gws=[1])

    assert summary == {1: len(boot["elements"])}

    out = config.RAW_DIR / config.CURRENT_SEASON / "merged_gw.csv"
    assert out.exists()
    assert out.parent == config.RAW_DIR / config.CURRENT_SEASON
    assert not (out.parent / "gws" / "merged_gw.csv").exists()

    df = build_table._load_merged_gw(config.CURRENT_SEASON)
    assert df is not None
    assert not df.empty
    for col in ("gw", "player_id", "team", "position", "total_points", "fixture_id"):
        assert col in df.columns
    assert (df["gw"] == 1).all()


# --------------------------------------------------------- schema convention gates


@responses.activate
def test_team_column_uses_full_club_name_never_short_code():
    """Task 2 gate 1: `team` is drawn only from teams[].name, never short_name."""
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture(gws=[1])

    merged = pd.read_csv(config.RAW_DIR / config.CURRENT_SEASON / "merged_gw.csv")
    club_names = {t["name"] for t in boot["teams"]}
    short_codes = {t["short_name"] for t in boot["teams"]}
    captured_teams = set(merged["team"].dropna())
    assert captured_teams <= club_names
    assert captured_teams & short_codes == set()


@responses.activate
def test_name_is_first_name_space_second_name_not_web_name():
    """Task 2 gate 2: `name` is first_name + ' ' + second_name, never web_name."""
    boot = _boot_with_finished_events(n_events=1)
    target = boot["elements"][0]
    target["first_name"] = "David"
    target["second_name"] = "Raya Martín"
    target["web_name"] = "Raya"
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture(gws=[1])

    merged = pd.read_csv(config.RAW_DIR / config.CURRENT_SEASON / "merged_gw.csv")
    row = merged[merged["element"] == target["id"]]
    assert row["name"].iloc[0] == "David Raya Martín"


@responses.activate
def test_position_labels_gk_def_mid_fwd_never_gkp():
    """Task 2 gate 3: emitted position labels are GK/DEF/MID/FWD, never GKP."""
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture(gws=[1])

    merged = pd.read_csv(config.RAW_DIR / config.CURRENT_SEASON / "merged_gw.csv")
    captured_positions = set(merged["position"].dropna())
    assert captured_positions == {"GK", "DEF", "MID", "FWD"}
    assert "GKP" not in captured_positions


@responses.activate
def test_round_not_finished_and_data_checked_excluded_from_merged():
    """Task 2 gate 4a: a round present in histories but absent from the
    finished-and-data-checked set produces no rows in merged_gw.csv."""
    boot = _boot_with_finished_events(n_events=3)  # GW1-3 finished + data-checked
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], r) for r in (1, 2, 3, 4)]
                 for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture()  # no explicit gws -> resolved via finished_gws(boot)

    merged = pd.read_csv(config.RAW_DIR / config.CURRENT_SEASON / "merged_gw.csv")
    assert set(merged["round"]) == {1, 2, 3}
    assert 4 not in set(merged["round"])


def test_finished_gws_excludes_finished_but_not_data_checked():
    """Task 2 gate 4b: an event reporting finished with data_checked still
    false must not appear in finished_gws's result."""
    boot = fake_boot()
    boot["events"] = [
        {"id": 1, "finished": True, "data_checked": True, "is_next": False,
         "deadline_time": "2026-08-15T17:30:00Z"},
        {"id": 2, "finished": True, "data_checked": True, "is_next": False,
         "deadline_time": "2026-08-22T17:30:00Z"},
        {"id": 3, "finished": True, "data_checked": False, "is_next": True,
         "deadline_time": "2026-08-29T17:30:00Z"},
    ]

    assert gw_capture.finished_gws(boot) == [1, 2]


@responses.activate
def test_ledger_files_live_under_gws_child_not_merged_file():
    """Task 2 gate 5: the ledger file for each captured GW exists under the
    `gws` child directory of the season directory, and merged_gw.csv does not."""
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture(gws=[1])

    ledger_dir = config.RAW_DIR / config.CURRENT_SEASON / "gws"
    assert (ledger_dir / "gw1.csv").exists()
    assert not (ledger_dir / "merged_gw.csv").exists()


def test_write_csv_atomic_leaves_no_partial_file_on_failure(tmp_path, monkeypatch):
    """Task 2 gate 6: when the CSV writer raises partway, no file exists at
    the destination path and no temp file is left beside it."""
    df = pd.DataFrame({"a": [1, 2]})
    out = tmp_path / "out.csv"

    def _raise(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_csv", _raise)

    with pytest.raises(RuntimeError):
        gw_capture.write_csv_atomic(df, out)

    assert not out.exists()
    assert list(tmp_path.glob("*.tmp")) == []


# ============================================================= 08-02 Task 1
# players_raw.csv / fixtures.csv refresh + payload field guards


@responses.activate
def test_capture_writes_players_raw_and_fixtures_readable_by_id_map():
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture(gws=[1])

    players_raw = config.RAW_DIR / config.CURRENT_SEASON / "players_raw.csv"
    fixtures_csv = config.RAW_DIR / config.CURRENT_SEASON / "fixtures.csv"
    assert players_raw.exists()
    assert fixtures_csv.exists()

    import data.id_map as id_map
    df = id_map._from_players_raw(config.CURRENT_SEASON)
    assert df is not None
    assert not df.empty
    for col in ("player_id", "player_code", "web_name", "first_name", "second_name", "element_type"):
        assert df[col].notna().all()


@responses.activate
def test_players_raw_header_sorted_and_complete():
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture(gws=[1])

    players_raw = config.RAW_DIR / config.CURRENT_SEASON / "players_raw.csv"
    header = players_raw.read_text().splitlines()[0].split(",")
    assert header == sorted(header)
    expected_keys = set(boot["elements"][0].keys())
    assert expected_keys <= set(header)


@responses.activate
def test_fixtures_csv_carries_difficulty_join_columns():
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    _register_histories(boot, histories)

    gw_capture.capture(gws=[1])

    fx = pd.read_csv(config.RAW_DIR / config.CURRENT_SEASON / "fixtures.csv")
    for col in ("id", "team_h_difficulty", "team_a_difficulty"):
        assert col in fx.columns


@responses.activate
def test_second_capture_run_overwrites_both_mutable_files_unconditionally():
    boot1 = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot1)
    _register_fixtures([{"id": 1, "team_h_difficulty": 2, "team_a_difficulty": 2}])
    histories1 = {el["id"]: [_history_row(el["id"], 1)] for el in boot1["elements"]}
    _register_histories(boot1, histories1)
    gw_capture.capture(gws=[1])

    players_path = config.RAW_DIR / config.CURRENT_SEASON / "players_raw.csv"
    fixtures_path = config.RAW_DIR / config.CURRENT_SEASON / "fixtures.csv"
    size1_fixtures = fixtures_path.stat().st_size

    boot2 = _boot_with_finished_events(n_events=1)
    changed_cost = boot2["elements"][0]["now_cost"] + 5
    boot2["elements"][0]["now_cost"] = changed_cost
    _register_bootstrap(boot2)
    _register_fixtures([{"id": 1, "team_h_difficulty": 2, "team_a_difficulty": 2},
                         {"id": 2, "team_h_difficulty": 4, "team_a_difficulty": 1}])
    histories2 = {el["id"]: [_history_row(el["id"], 1)] for el in boot2["elements"]}
    _register_histories(boot2, histories2)
    gw_capture.capture(gws=[1])

    players_after = pd.read_csv(players_path)
    row = players_after[players_after["id"] == boot2["elements"][0]["id"]]
    assert row["now_cost"].iloc[0] == changed_cost
    assert fixtures_path.stat().st_size != size1_fixtures


@responses.activate
def test_element_missing_identity_key_raises_and_alerts(_isolate_raw_dir):
    tmp_path = _isolate_raw_dir
    boot = _boot_with_finished_events(n_events=1)
    del boot["elements"][0]["code"]
    _register_bootstrap(boot)

    with pytest.raises(ValueError, match="code"):
        gw_capture.capture(gws=[1])

    alerts = _read_alerts(tmp_path)
    assert len(alerts) == 1
    assert alerts[0]["job"] == "gw_capture"
    assert alerts[0]["step"] == "schema"


@responses.activate
def test_history_row_missing_required_key_raises_naming_it():
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
    _register_fixtures()
    histories = {el["id"]: [_history_row(el["id"], 1)] for el in boot["elements"]}
    bad_id = boot["elements"][0]["id"]
    bad_row = dict(histories[bad_id][0])
    del bad_row["bps"]
    histories[bad_id] = [bad_row]
    _register_histories(boot, histories)

    with pytest.raises(ValueError, match="bps"):
        gw_capture.capture(gws=[1])
