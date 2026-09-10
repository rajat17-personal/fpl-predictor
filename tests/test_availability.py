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
from data import availability, id_map
from data import fpl_core_insights
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

    # `resolved` already carries its own per-row `deadline_ts` (plan 10-04's
    # Task 1 pass-through addition) -- only `kickoff_max` still needs joining
    # from `deadlines` separately.
    dl_idx = deadlines.set_index(["season", "gw"])[["kickoff_max"]]
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


# --- data/availability.py::encode_availability -- plan 10-04 ----------------


def _resolved_frame(**overrides) -> pd.DataFrame:
    """A minimal synthetic `resolved`-shaped frame for `encode_availability`
    tests -- one row, every column the function requires, overridable per
    test via keyword."""
    base = {
        "season": ["2099-00"], "gw": [5], "player_code": [1],
        "snapshot_ts": [pd.Timestamp("2099-01-04 12:00", tz="UTC")],
        "deadline_ts": [pd.Timestamp("2099-01-05 17:30", tz="UTC")],
        "status": ["a"], "chance_of_playing_next_round": [100.0],
        "news_added": [pd.NaT],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_status_one_hot_covers_every_fpl_code():
    codes = ["a", "d", "i", "s", "u"]
    resolved = pd.DataFrame({
        "season": ["2099-00"] * 5, "gw": [5] * 5, "player_code": list(range(1, 6)),
        "snapshot_ts": [pd.Timestamp("2099-01-04 12:00", tz="UTC")] * 5,
        "deadline_ts": [pd.Timestamp("2099-01-05 17:30", tz="UTC")] * 5,
        "status": codes,
        "chance_of_playing_next_round": [100.0] * 5,
        "news_added": [pd.NaT] * 5,
    })
    out = availability.encode_availability(resolved)

    status_cols = [c for c in config.AVAILABILITY_COLS if c.startswith("av_status_")]
    assert status_cols == ["av_status_a", "av_status_d", "av_status_i",
                            "av_status_s", "av_status_u"]
    for i, code in enumerate(codes):
        row = out.iloc[i]
        ones = [c for c in status_cols if row[c] == 1.0]
        assert ones == [f"av_status_{code}"], (code, ones)
        others = [c for c in status_cols if c != f"av_status_{code}"]
        assert row[others].sum() == 0.0


def test_snapshot_age_days_is_deadline_minus_snapshot_ts():
    resolved = _resolved_frame(
        snapshot_ts=[pd.Timestamp("2099-01-02 17:30", tz="UTC")],
        deadline_ts=[pd.Timestamp("2099-01-05 17:30", tz="UTC")],
    )
    out = availability.encode_availability(resolved)
    assert out.iloc[0]["av_snapshot_age_days"] == pytest.approx(3.0, abs=1e-9)


def test_whole_family_is_nan_when_no_snapshot_qualifies(monkeypatch):
    """Extends 10-01's D-10 fallback scenario to the FULL eight-column
    family: with an EMPTY availability cache, attach() must leave ALL EIGHT
    columns NaN together for the unmatched key -- never a partial fill
    (T-10-04-02), which is the specific failure a `fillna(0)` upstream or a
    partially-populated cache would produce."""
    empty_avail = pd.DataFrame(columns=["season", "gw", "player_code"] + config.AVAILABILITY_COLS)
    monkeypatch.setattr(availability, "load_availability", lambda: empty_avail)

    full = pd.DataFrame({"season": ["2099-00"], "gw": [5], "player_code": [1],
                         "other_col": ["x"]})
    merged = availability.attach(full)
    assert len(merged) == len(full)
    for col in config.AVAILABILITY_COLS:
        assert merged[col].isna().all(), f"{col} should be NaN, not partially filled"


def test_unknown_status_code_raises_not_silently_dropped():
    resolved = _resolved_frame(status=["x"])
    with pytest.raises(ValueError, match="x"):
        availability.encode_availability(resolved)


def test_news_added_postdating_deadline_raises_naming_the_row():
    """T-10-04-03's escape hatch: a news_added value AFTER the gw deadline
    means resolve_as_of admitted a row it should have excluded -- raise
    naming the offending (season, gw, player_code), never clip."""
    resolved = _resolved_frame(
        deadline_ts=[pd.Timestamp("2099-01-05 17:30", tz="UTC")],
        news_added=[pd.Timestamp("2099-01-05 18:00", tz="UTC")],   # after deadline_ts
    )
    with pytest.raises(AssertionError, match=r"2099-00"):
        availability.encode_availability(resolved)


@needs_data
def test_availability_family_present_and_not_rolled_in_features():
    """The family-classification regression gate (plan 10-04's own
    must_have), now covering all eight columns rather than 10-01's single
    `av_chance_pct`: every column must reach features.parquet raw, never
    through the ROLL_STATS shift-then-roll machinery."""
    feat = pd.read_parquet(FEATURES)
    missing = [c for c in config.AVAILABILITY_COLS if c not in feat.columns]
    assert not missing, f"missing from features.parquet: {missing}"
    rolled = [c for c in feat.columns
             if c.startswith("av_") and c.endswith(("_r3", "_r5", "_r10", "_rall"))]
    assert not rolled, f"availability columns must never be rolled: found {rolled}"


# --- data/fpl_core_insights.py -- plan 10-06's committed vendoring ----------


def test_reduce_gw_csv_raises_on_missing_availability_column():
    """T-10-06-02: a vendor schema break must raise loudly, never silently
    produce an all-NaN availability column. Synthetic CSV omits `news`
    (one of `_KEEP_COLS`'s six members) -- the raise must name it."""
    csv_bytes = (
        b"id,status,chance_of_playing_next_round,chance_of_playing_this_round,news_added\n"
        b"1,a,100,100,\n"
    )
    with pytest.raises(ValueError, match="news"):
        fpl_core_insights._reduce_gw_csv(csv_bytes, "2025-26", 7)


@needs_data
def test_vendored_provider_uses_prior_gw_folder(tmp_path, monkeypatch):
    """T-10-06-01 / D-05's leakage rule, made executable: a vendored folder
    labelled gameweek N freezes at gameweek N's END, so it is only ever
    eligible for gameweek N+1 onward. Build a synthetic vendored directory
    carrying ONLY a GW1 folder (real season 2025-26, so `gw_deadlines()` has
    real kickoff data to resolve against) and prove GW2 resolves from that
    frozen GW1 folder while GW1 itself resolves to nothing (no GW0 folder
    exists -- the D-10 NaN-fallback case)."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    base = tmp_path / "external" / "fpl_core_insights" / "2025-2026"
    base.mkdir(parents=True)

    id_map_df = id_map.load_id_map()
    season_rows = id_map_df[id_map_df["season"] == "2025-26"]
    if season_rows.empty:
        pytest.skip("no 2025-26 rows in id_map -- run the data pipeline first")
    row = season_rows.iloc[0]
    player_id, player_code = int(row["player_id"]), row["player_code"]

    pd.DataFrame({
        "id": [player_id], "status": ["a"], "chance_of_playing_next_round": [100.0],
        "chance_of_playing_this_round": [100.0], "news": [""], "news_added": [None],
    }).to_csv(base / "GW1_playerstats.csv", index=False)

    deadlines = availability.gw_deadlines()
    deadlines = deadlines[deadlines["season"] == "2025-26"]
    if deadlines.empty:
        pytest.skip("no 2025-26 deadlines derivable -- run the data pipeline first")

    snaps = availability._fpl_core_insights_source()
    assert not snaps.empty, "expected the synthetic GW1 file to be picked up"

    resolved = availability.resolve_as_of(snaps, deadlines)
    gw1_rows = resolved[(resolved["gw"] == 1) & (resolved["player_code"] == player_code)]
    gw2_rows = resolved[(resolved["gw"] == 2) & (resolved["player_code"] == player_code)]

    assert gw1_rows.empty, "GW1 has no prior (GW0) folder -- must resolve to nothing"
    assert len(gw2_rows) == 1, "GW2 must resolve from the frozen GW1 folder"
    assert gw2_rows.iloc[0]["status"] == "a"
