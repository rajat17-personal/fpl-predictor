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
import data.fplreview as fplreview
import data.id_crosswalk as id_crosswalk
import predict.scoreboard as sb

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


# ======================================================= data/fplreview.py


@pytest.fixture(autouse=True)
def _isolate_fplreview_dir(tmp_path, monkeypatch):
    """Every fplreview test must never read a real capture file."""
    d = tmp_path / "fplreview_captures"
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(fplreview, "FPLREVIEW_DIR", d)
    return d


def _write_capture(dirpath, season, gw, csv_text):
    path = dirpath / f"fplreview_{season}_gw{gw:02d}.csv"
    path.write_text(csv_text)
    return path


def test_validate_raises_naming_all_missing_columns_at_once():
    df = pd.DataFrame({"name": ["A"], "proj_pts": [1.0]})  # missing team + position
    with pytest.raises(ValueError) as exc_info:
        fplreview.validate(df, "fake.csv")
    msg = str(exc_info.value)
    assert "team" in msg
    assert "position" in msg


def test_validate_raises_when_proj_pts_entirely_non_numeric():
    df = pd.DataFrame({"name": ["A", "B"], "team": ["X", "Y"], "position": ["MID", "DEF"],
                        "proj_pts": ["N/A", "n/a"]})
    with pytest.raises(ValueError, match="non-numeric"):
        fplreview.validate(df, "fake.csv")


def test_load_gw_returns_none_when_no_capture_file(_isolate_fplreview_dir):
    assert fplreview.load_gw("2026-27", 4) is None


def test_load_gw_resolves_names_and_drops_unresolved(_isolate_fplreview_dir, monkeypatch):
    monkeypatch.setattr(
        id_crosswalk, "resolve_by_name",
        lambda names: names.map({"Haaland": 223094}).astype("Int64"))
    _write_capture(_isolate_fplreview_dir, "2026-27", 4,
                    "name,team,position,proj_pts\n"
                    "Haaland,Man City,FWD,7.5\n"
                    "Some Unknown Player,Nowhere,MID,2.0\n")

    out = fplreview.load_gw("2026-27", 4)

    assert out is not None
    assert list(out.player_code) == [223094]
    assert "Some Unknown Player" not in out.name.values


def test_load_gw_duplicate_player_names_raises(_isolate_fplreview_dir, monkeypatch):
    monkeypatch.setattr(
        id_crosswalk, "resolve_by_name",
        lambda names: names.map({"Haaland": 223094, "E.Haaland": 223094}).astype("Int64"))
    _write_capture(_isolate_fplreview_dir, "2026-27", 4,
                    "name,team,position,proj_pts\n"
                    "Haaland,Man City,FWD,7.5\n"
                    "E.Haaland,Man City,FWD,7.5\n")

    with pytest.raises(AssertionError, match="duplicate"):
        fplreview.load_gw("2026-27", 4)


def test_load_gw_lowercases_and_strips_header_whitespace(_isolate_fplreview_dir, monkeypatch):
    monkeypatch.setattr(
        id_crosswalk, "resolve_by_name",
        lambda names: names.map({"Haaland": 223094}).astype("Int64"))
    _write_capture(_isolate_fplreview_dir, "2026-27", 4,
                    " Name , Team , Position , Proj_Pts \n"
                    "Haaland,Man City,FWD,7.5\n")

    out = fplreview.load_gw("2026-27", 4)

    assert out is not None
    assert list(out.player_code) == [223094]


# ================================================= predict/scoreboard.py


def _sample_players(n=5):
    return [
        {"player_id": i, "player_code": 100 + i, "name": f"P{i}", "team": "T",
         "position": "MID", "xp": float(i), "xp_capt": float(i) + 1,
         "ep_next": float(i) - 0.5}
        for i in range(1, n + 1)
    ]


def _sample_actuals(n=5, minutes=90):
    return pd.DataFrame([
        {"player_id": i, "actual": i * 2, "minutes": minutes} for i in range(1, n + 1)
    ])


def _frozen(gw, players, season="2026-27"):
    return {"gw": gw, "meta": {"gw": gw, "season": season,
                                "generated_utc": "2026-01-01T00:00:00Z"},
            "players": players}


def test_score_gw_both_absent_reproduces_todays_key_set():
    players = _sample_players(5)
    actuals = _sample_actuals(5)
    entry = sb.score_gw(_frozen(4, players), actuals)

    expected_keys = {"gw", "n_players", "generated_utc", "mae_model", "spearman_model",
                      "mae_fpl", "spearman_fpl", "captain", "top5", "best_player"}
    assert set(entry.keys()) == expected_keys


def test_score_gw_adds_consensus_keys_when_present(monkeypatch):
    consensus = pd.DataFrame({"player_id": [1, 2, 3], "n_owners": [90, 50, 10],
                               "consensus_pct": [0.9, 0.5, 0.1], "consensus_rank": [1, 2, 3]})
    monkeypatch.setattr(sb.data.fpl_standings, "load_consensus", lambda gw: consensus)

    entry = sb.score_gw(_frozen(4, _sample_players(5)), _sample_actuals(5))

    assert entry["n_consensus"] == 3
    assert "spearman_consensus" in entry
    assert "spearman_consensus_vs_model" in entry
    assert "mae_consensus" not in entry  # ownership is not in points units


def test_score_gw_omits_consensus_keys_when_absent():
    entry = sb.score_gw(_frozen(4, _sample_players(5)), _sample_actuals(5))
    for key in ("n_consensus", "spearman_consensus", "spearman_consensus_vs_model"):
        assert key not in entry


def test_score_gw_adds_fplreview_keys_on_played_rows_only(monkeypatch):
    fpr = pd.DataFrame({"player_code": [101, 102, 103], "proj_pts": [3.5, 4.0, 0.0]})
    monkeypatch.setattr(sb.data.fplreview, "load_gw", lambda season, gw: fpr)

    players = _sample_players(5)  # player_code 101..105
    actuals = pd.DataFrame([
        {"player_id": 1, "actual": 2, "minutes": 90},
        {"player_id": 2, "actual": 4, "minutes": 90},
        {"player_id": 3, "actual": 0, "minutes": 0},   # unplayed -- must be filtered
        {"player_id": 4, "actual": 6, "minutes": 90},
        {"player_id": 5, "actual": 8, "minutes": 90},
    ])
    entry = sb.score_gw(_frozen(4, players), actuals)

    assert entry["n_fplreview"] == 2   # only players 1,2 matched AND played
    assert "mae_fplreview" in entry
    assert "spearman_fplreview" in entry


def test_score_gw_omits_fplreview_keys_when_absent():
    entry = sb.score_gw(_frozen(4, _sample_players(5)), _sample_actuals(5))
    for key in ("n_fplreview", "mae_fplreview", "spearman_fplreview"):
        assert key not in entry


def test_running_summary_averages_each_new_key_only_over_carrying_entries(monkeypatch):
    consensus = pd.DataFrame({"player_id": [1, 2, 3], "n_owners": [90, 50, 10],
                               "consensus_pct": [0.9, 0.5, 0.1], "consensus_rank": [1, 2, 3]})
    monkeypatch.setattr(sb.data.fpl_standings, "load_consensus",
                        lambda gw: consensus if gw == 4 else None)
    fpr = pd.DataFrame({"player_code": [101, 102], "proj_pts": [3.5, 4.0]})
    monkeypatch.setattr(sb.data.fplreview, "load_gw",
                        lambda season, gw: fpr if gw == 5 else None)

    entry4 = sb.score_gw(_frozen(4, _sample_players(5)), _sample_actuals(5))
    entry5 = sb.score_gw(_frozen(5, _sample_players(5)), _sample_actuals(5))
    summary = sb.running_summary([entry4, entry5])

    assert "spearman_consensus" in summary   # entry4 carries it
    assert "mae_fplreview" in summary         # entry5 carries it


def test_rescore_with_force_gains_new_keys_without_losing_existing(monkeypatch):
    """A gameweek scored before either benchmark existed, then rescored once a
    benchmark becomes available, keeps every original key and gains the new
    ones."""
    first = sb.score_gw(_frozen(4, _sample_players(5)), _sample_actuals(5))

    consensus = pd.DataFrame({"player_id": [1, 2, 3], "n_owners": [90, 50, 10],
                               "consensus_pct": [0.9, 0.5, 0.1], "consensus_rank": [1, 2, 3]})
    monkeypatch.setattr(sb.data.fpl_standings, "load_consensus", lambda gw: consensus)
    second = sb.score_gw(_frozen(4, _sample_players(5)), _sample_actuals(5))

    assert set(first.keys()) <= set(second.keys())
    assert "spearman_consensus" in second
