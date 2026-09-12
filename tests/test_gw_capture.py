"""End-to-end + schema-convention tests for data.gw_capture (Phase 8).

Task 1 opens this file with the single end-to-end test proving the whole
capture path -- FPL API to build_table -- on one finished gameweek. Task 2
extends it with the gates that lock the four schema conventions (club-name,
player-name, position, completion) plus the layout and atomicity properties.
"""
from __future__ import annotations

import pytest
import responses

import config
import data.build_table as build_table
import data.gw_capture as gw_capture
from test_api import fake_boot

_BOOT_URL = f"{config.FPL_API}/bootstrap-static/"


@pytest.fixture(autouse=True)
def _isolate_raw_dir(tmp_path, monkeypatch):
    """Every test in this module must never touch the real (irreplaceable)
    data/raw/2026-27/ tree, and must never make a real HTTP call."""
    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(gw_capture.time, "sleep", lambda *_a, **_k: None)
    return tmp_path


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


def _register_histories(boot: dict, histories: dict) -> None:
    for el in boot["elements"]:
        responses.add(responses.GET, _elem_summary_url(el["id"]),
                       json={"history": histories.get(el["id"], [])}, status=200)


@responses.activate
def test_end_to_end_capture_reads_back_through_build_table():
    boot = _boot_with_finished_events(n_events=1)
    _register_bootstrap(boot)
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
