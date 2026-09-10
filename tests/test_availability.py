"""Phase 10 plan 10-01 Task 2: locks the as-of-deadline leakage rule, the
D-10 safe-fallback contract, and the extended daily-capture columns.

Isolation discipline mirrors tests/test_cron.py: every test in this module
must never touch the real (irreplaceable) `data/snapshots/` archive.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest
import responses

import config
import data.snapshot as snapshot
from data import availability
from test_api import fake_boot

FEATURES = config.PROCESSED_DIR / "features.parquet"
RAW = config.PROCESSED_DIR / "player_gw.parquet"
AVAILABILITY = config.PROCESSED_DIR / "availability.parquet"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")

_BOOT_URL = f"{config.FPL_API}/bootstrap-static/"


@pytest.fixture(autouse=True)
def _isolate_snapshot(tmp_path, monkeypatch):
    """No test in this module may write into or read from the real (SNAP_DIR)
    archive -- matches tests/test_cron.py's own isolation discipline."""
    monkeypatch.setattr(snapshot, "SNAP_DIR", tmp_path / "snapshots")
    return tmp_path


# --- snapshot_frame's extended availability columns (data/snapshot.py) ------


@responses.activate
def test_snapshot_frame_carries_new_availability_columns():
    boot = fake_boot()
    for el in boot["elements"][:3]:
        el["chance_of_playing_this_round"] = "75"
        el["news"] = "Knock - 75% chance of playing"
        el["news_added"] = "2026-09-10T09:00:00Z"
    ts = dt.datetime(2026, 9, 10, 9, 30, tzinfo=dt.timezone.utc)

    df = snapshot.snapshot_frame(boot, ts)

    for col in ("chance_of_playing_this_round", "news", "news_added"):
        assert col in df.columns
    # Numerically coerced like its next_round sibling.
    assert pd.api.types.is_numeric_dtype(df["chance_of_playing_this_round"])
    assert df["chance_of_playing_this_round"].iloc[0] == pytest.approx(75.0)
    # news/news_added stay as captured strings (news_added is parsed downstream).
    assert df["news"].iloc[0] == "Knock - 75% chance of playing"
    assert df["news_added"].iloc[0] == "2026-09-10T09:00:00Z"


@responses.activate
def test_take_snapshot_persists_new_columns_end_to_end(_isolate_snapshot):
    tmp_path = _isolate_snapshot
    boot = fake_boot()
    boot["elements"][0]["chance_of_playing_this_round"] = "50"
    boot["elements"][0]["news"] = "Ankle injury - 50% chance of playing"
    responses.add(responses.GET, _BOOT_URL, json=boot, status=200)

    df = snapshot.take_snapshot()

    assert df is not None
    for col in ("chance_of_playing_this_round", "news", "news_added"):
        assert col in df.columns
    reloaded = snapshot.load_snapshots()
    for col in ("chance_of_playing_this_round", "news", "news_added"):
        assert col in reloaded.columns
    assert (tmp_path / "snapshots").exists()


# --- data/availability.py::_require_columns ---------------------------------


def test_require_columns_raises_naming_missing_column():
    with pytest.raises(ValueError, match="snapshot_ts"):
        availability._require_columns(
            pd.DataFrame({"player_code": [1]}), ["player_code", "snapshot_ts"], "probe")


# --- data/availability.py::resolve_as_of -- the as-of-deadline invariant ----


def _deadlines_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "season": ["2099-00"],
        "gw": [5],
        "deadline_ts": [pd.Timestamp("2099-01-05 17:30", tz="UTC")],
        "kickoff_max": [pd.Timestamp("2099-01-05 20:00", tz="UTC")],
    })


def test_resolve_as_of_post_deadline_row_excluded():
    """Direct anti-leakage case: a source row dated strictly AFTER the
    deadline must never resolve for that gameweek."""
    snaps = pd.DataFrame({
        "season": ["2099-00"], "player_code": [1],
        "snapshot_ts": [pd.Timestamp("2099-01-05 18:00", tz="UTC")],  # after deadline_ts
        "status": ["a"], "chance_of_playing_next_round": [100.0], "source": ["test"],
    })
    out = availability.resolve_as_of(snaps, _deadlines_frame())
    assert out.empty


def test_resolve_as_of_pre_deadline_row_included():
    """The mirror-image positive case: a row strictly before both boundaries
    resolves for that gameweek."""
    snaps = pd.DataFrame({
        "season": ["2099-00"], "player_code": [1],
        "snapshot_ts": [pd.Timestamp("2099-01-04 12:00", tz="UTC")],  # before deadline_ts
        "status": ["a"], "chance_of_playing_next_round": [100.0], "source": ["test"],
    })
    out = availability.resolve_as_of(snaps, _deadlines_frame())
    assert len(out) == 1
    assert out.iloc[0]["gw"] == 5
    assert out.iloc[0]["player_code"] == 1


def test_missing_snapshot_degrades_to_nan_not_raise(monkeypatch):
    """D-10's mandatory safe-fallback assertion: a gameweek with no
    qualifying prior source row -- here, a two-row synthetic source frame
    whose only rows POSTDATE the deadline -- yields the gameweek ABSENT from
    resolve_as_of's output (never a raise, never a forward fill), and the
    real attach() against a one-row `full` frame leaves the row count
    unchanged with `av_chance_pct` NaN."""
    deadlines = _deadlines_frame()
    snaps = pd.DataFrame({
        "season": ["2099-00", "2099-00"],
        "player_code": [1, 1],
        "snapshot_ts": [
            pd.Timestamp("2099-01-05 19:00", tz="UTC"),   # after deadline_ts -- ineligible
            pd.Timestamp("2099-01-06 09:00", tz="UTC"),   # after kickoff_max too -- ineligible
        ],
        "status": ["a", "a"],
        "chance_of_playing_next_round": [100.0, 100.0],
        "source": ["test", "test"],
    })

    resolved = availability.resolve_as_of(snaps, deadlines)
    assert resolved.empty, "no qualifying row -- the gameweek must be entirely absent"

    # The on-disk equivalent of "no qualifying row anywhere for this
    # (season, gw, player_code)": an availability table with no matching row.
    # Exercise the REAL attach() (never a hand-rolled merge) via
    # load_availability, monkeypatched so no real cache is touched.
    empty_avail = pd.DataFrame(columns=["season", "gw", "player_code", "av_chance_pct"])
    monkeypatch.setattr(availability, "load_availability", lambda: empty_avail)

    full = pd.DataFrame({"season": ["2099-00"], "gw": [5], "player_code": [1],
                         "other_col": ["x"]})
    merged = availability.attach(full)
    assert len(merged) == len(full)
    assert merged["av_chance_pct"].isna().all()


@needs_data
def test_every_source_row_predates_its_gw_deadline():
    """The invariant test named in this plan's assumption-delta block: for
    EVERY distinct `source` value present in a resolved run, every resolved
    row's `snapshot_ts` must be strictly before BOTH that gameweek's
    `deadline_ts` and its `kickoff_max` -- so a newly registered provider
    cannot bypass the rule."""
    deadlines = availability.gw_deadlines()
    snaps = availability.load_sources()
    if snaps.empty:
        pytest.skip("no availability source data present")
    resolved = availability.resolve_as_of(snaps, deadlines)
    assert not resolved.empty, "expected at least one resolved row from real source data"

    dl_idx = deadlines.set_index(["season", "gw"])
    for source_name, sub in resolved.groupby("source"):
        joined = sub.join(dl_idx, on=["season", "gw"])
        assert (joined["snapshot_ts"] < joined["deadline_ts"]).all(), \
            f"source '{source_name}' has a row at/after its gw deadline"
        assert (joined["snapshot_ts"] < joined["kickoff_max"]).all(), \
            f"source '{source_name}' has a row at/after a kickoff in its gw"


# --- features.parquet: raw, never rolled (mirrors test_leakage.py's family
# classification precedent; a stronger companion test lives there too) ------


@needs_data
def test_availability_column_present_and_not_rolled_in_features():
    feat = pd.read_parquet(FEATURES)
    assert "av_chance_pct" in feat.columns
    rolled = [c for c in feat.columns
             if c.startswith("av_chance_pct_r")]
    assert not rolled, f"av_chance_pct must never be rolled: found {rolled}"
