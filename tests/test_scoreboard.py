"""Tests for the Tier-3 diagnostic scoreboard benchmarks (Phase 10-02):
top-100 consensus ownership (`data/fpl_standings.py`), the fplreview manual
capture (`data/fplreview.py`), and their scoring in
`predict/scoreboard.py::score_gw`/`running_summary`.

Every test in this module stubs the FPL API via `responses` (or avoids the
network entirely) -- zero live network access in the test suite.
"""
from __future__ import annotations

import pandas as pd
import pytest
import responses

import config
import data.fpl_standings as standings

_STANDINGS_URL = f"{config.FPL_API}/leagues-classic/{standings.OVERALL_LEAGUE_ID}/standings/"


def _picks_url(entry_id: int, gw: int) -> str:
    return f"{config.FPL_API}/entry/{entry_id}/event/{gw}/picks/"


@pytest.fixture(autouse=True)
def _isolate_standings_cache(tmp_path, monkeypatch):
    """Every test must never touch the real data/raw/standings/ cache or the
    real data/processed/consensus_*.parquet files."""
    monkeypatch.setattr(standings, "_RAW_DIR", tmp_path / "raw" / "standings")
    monkeypatch.setattr(standings.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path / "processed")
    (tmp_path / "processed").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _standings_page(results: list[dict]) -> dict:
    return {"standings": {"has_next": False, "page": 1, "results": results}}


def _entry(entry_id: int, rank: int) -> dict:
    return {"entry": entry_id, "entry_name": f"Team {entry_id}",
            "player_name": f"Manager {entry_id}", "rank": rank, "total": 1000 - rank}


# ------------------------------------------------------------------- _require


def test_require_raises_on_missing_standings_key():
    with pytest.raises(ValueError, match="standings"):
        standings._require({}, ["standings", "results"], list, "FPL standings gw1")


def test_require_raises_on_missing_results_key():
    with pytest.raises(ValueError, match="results"):
        standings._require({"standings": {}}, ["standings", "results"], list,
                            "FPL standings gw1")


# ------------------------------------------------------------ consensus_ownership


def test_consensus_ownership_counts_distinct_owners_never_double_counting():
    picks_by_entry = {
        1: [{"element": 10}, {"element": 11}, {"element": 10}],  # dup within one manager
        2: [{"element": 10}],
        3: [{"element": 12}],
    }
    out = standings.consensus_ownership(picks_by_entry)
    assert list(out.columns) == ["player_id", "n_owners", "consensus_pct", "consensus_rank"]
    row10 = out[out.player_id == 10].iloc[0]
    assert row10.n_owners == 2
    assert row10.consensus_pct == pytest.approx(2 / 3)
    assert row10.consensus_rank == 1  # most-owned, ranked first
    assert out.n_owners.is_monotonic_decreasing


def test_consensus_ownership_empty_input_returns_empty_frame_with_right_columns():
    out = standings.consensus_ownership({})
    assert list(out.columns) == ["player_id", "n_owners", "consensus_pct", "consensus_rank"]
    assert len(out) == 0


# --------------------------------------------------------------- fetch_standings


@responses.activate
def test_fetch_standings_stops_on_empty_page():
    page1 = [_entry(i, i) for i in range(1, 51)]
    responses.add(responses.GET, _STANDINGS_URL, json=_standings_page(page1), status=200)
    responses.add(responses.GET, _STANDINGS_URL, json=_standings_page([]), status=200)

    out = standings.fetch_standings(1, pages=3, top_n=100)

    assert len(responses.calls) == 2  # page 3 never fetched -- stopped on empty page 2
    assert len(out) == 50


@responses.activate
def test_fetch_standings_caps_at_top_n():
    page1 = [_entry(i, i) for i in range(1, 51)]
    page2 = [_entry(i, i) for i in range(51, 101)]
    responses.add(responses.GET, _STANDINGS_URL, json=_standings_page(page1), status=200)
    responses.add(responses.GET, _STANDINGS_URL, json=_standings_page(page2), status=200)

    out = standings.fetch_standings(1, pages=3, top_n=75)

    assert len(out) == 75


# ------------------------------------------------------------- fetch_entry_picks


@responses.activate
def test_fetch_entry_picks_returns_empty_list_on_404_not_raise():
    responses.add(responses.GET, _picks_url(999, 1), status=404)

    out = standings.fetch_entry_picks(999, 1)

    assert out == []


@responses.activate
def test_fetch_entry_picks_one_unavailable_manager_does_not_kill_the_others():
    responses.add(responses.GET, _picks_url(1, 1),
                   json={"picks": [{"element": 10}]}, status=200)
    responses.add(responses.GET, _picks_url(2, 1), status=404)
    responses.add(responses.GET, _picks_url(3, 1),
                   json={"picks": [{"element": 11}]}, status=200)

    picks_by_entry = {e: standings.fetch_entry_picks(e, 1) for e in (1, 2, 3)}
    consensus = standings.consensus_ownership(picks_by_entry)

    assert picks_by_entry[2] == []
    assert set(consensus.player_id) == {10, 11}


# --------------------------------------------------------------------- build


def test_build_writes_parquet_and_load_consensus_returns_it(monkeypatch, tmp_path):
    fake_consensus = pd.DataFrame({
        "player_id": [10, 11], "n_owners": [2, 1],
        "consensus_pct": [1.0, 0.5], "consensus_rank": [1, 2]})
    monkeypatch.setattr(standings, "fetch_standings", lambda gw, **kw: [_entry(1, 1)])
    monkeypatch.setattr(standings, "fetch_entry_picks", lambda entry_id, gw: [])
    monkeypatch.setattr(standings, "consensus_ownership", lambda picks: fake_consensus)

    out = standings.build(1)

    assert not out.empty
    season = config.SEASONS[-1]
    parquet_path = config.PROCESSED_DIR / f"consensus_{season}_gw01.parquet"
    assert parquet_path.exists()

    loaded = standings.load_consensus(1)
    assert loaded is not None
    assert list(loaded.player_id) == [10, 11]


def test_load_consensus_returns_none_when_absent():
    assert standings.load_consensus(99) is None
