"""Phase 9 regression tests: the experiment flag registry and captaincy
ceiling EV every later experiment plan builds on top of."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
from backtest.capt_ceiling_ci import (capture_ratio, paired_cluster_bootstrap,
                                      paired_t_interval)
from backtest.enrichment_slices import cell_stats
from backtest.season import run_season
from backtest.walk_forward import apply_experiment_feature_gating, resolve_scheduler
from models import captaincy

FEATURES = config.PROCESSED_DIR / "features.parquet"
RAW = config.PROCESSED_DIR / "player_gw.parquet"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")

_EXPERIMENT_KEYS = {"capt_ceiling", "capt_mc", "chips_v2", "team_strength",
                    "rl_strategy", "understat", "fotmob", "fbref_v2",
                    "ep_next_lag", "ep_next_now", "availability_flags",
                    "transfermarkt_injury"}


# --- config.EXPERIMENTS / resolve_experiments() -----------------------------

def test_experiments_registry_default_off():
    """D-08: every experiment defaults off. A default flip must be a
    deliberate edit to this test, not an accident."""
    assert set(config.EXPERIMENTS) == _EXPERIMENT_KEYS
    assert not any(config.EXPERIMENTS.values())


def test_resolve_experiments_none_spec_no_env_matches_default(monkeypatch):
    monkeypatch.delenv("FPL_EXPERIMENTS", raising=False)
    assert config.resolve_experiments(None) == config.EXPERIMENTS


def test_resolve_experiments_single_flag_leaves_registry_unmutated():
    result = config.resolve_experiments("capt_ceiling")
    assert result["capt_ceiling"] is True
    assert sum(result.values()) == 1
    # module-level dict must never be mutated by a resolve_experiments() call
    assert not any(config.EXPERIMENTS.values())


def test_resolve_experiments_multi_flag_with_space():
    result = config.resolve_experiments("capt_ceiling, chips_v2")
    assert sum(result.values()) == 2
    assert result["capt_ceiling"] is True
    assert result["chips_v2"] is True


def test_resolve_experiments_none_token_is_all_off():
    result = config.resolve_experiments("none")
    assert not any(result.values())


def test_resolve_experiments_all_token_is_all_on():
    result = config.resolve_experiments("all")
    assert all(result.values())


def test_resolve_experiments_bogus_token_raises():
    with pytest.raises(ValueError, match="bogus"):
        config.resolve_experiments("bogus")


# --- backtest/season.py::run_season scheduler toggle (plan 09-07 Task 1) ----

def test_run_season_bogus_scheduler_raises_naming_all_three():
    """Pure-logic test: the ValueError fires before any pool/model/policy I/O,
    so a minimal one-row frame is enough."""
    preds = pd.DataFrame({"gw": [1], "player_code": [1]})
    with pytest.raises(ValueError) as exc:
        run_season(preds, "xp_med", scheduler="bogus")
    msg = str(exc.value)
    assert "v1" in msg and "v2" in msg and "rl" in msg


# --- backtest/walk_forward.py::resolve_scheduler (plan 09-07 Task 1) --------

def _exp(**overrides) -> dict:
    base = dict(config.EXPERIMENTS)
    base.update(overrides)
    return base


def test_resolve_scheduler_defaults_to_v1():
    assert resolve_scheduler(_exp()) == "v1"


def test_resolve_scheduler_chips_v2_flag_maps_to_v2():
    assert resolve_scheduler(_exp(chips_v2=True)) == "v2"


def test_resolve_scheduler_rl_strategy_flag_maps_to_rl():
    assert resolve_scheduler(_exp(rl_strategy=True)) == "rl"


def test_resolve_scheduler_rl_and_chips_v2_together_exits_naming_both():
    with pytest.raises(SystemExit) as exc:
        resolve_scheduler(_exp(rl_strategy=True, chips_v2=True))
    msg = str(exc.value)
    assert "rl_strategy" in msg and "chips_v2" in msg


# --- backtest/walk_forward.py::apply_experiment_feature_gating (plan 09-08) --

def test_feature_gating_drops_ts_and_us_families_when_off():
    df = pd.DataFrame({
        "ts_attack_self": [1.0], "ts_pcs": [0.5],
        "us_npxg_r5": [0.2], "us_shots_r3": [1.0],
        "minutes_r5": [90.0],
    })
    out = apply_experiment_feature_gating(df, {"team_strength": False, "understat": False})
    assert not any(c.startswith("ts_") for c in out.columns)
    assert not any(c.startswith("us_") for c in out.columns)
    assert "minutes_r5" in out.columns


def test_feature_gating_keeps_family_when_flag_on():
    df = pd.DataFrame({"ts_attack_self": [1.0], "us_npxg_r5": [0.2], "minutes_r5": [90.0]})
    out = apply_experiment_feature_gating(df, {"team_strength": True, "understat": True})
    assert "ts_attack_self" in out.columns
    assert "us_npxg_r5" in out.columns


def test_feature_gating_missing_key_defaults_to_off():
    """Callers may pass a partial dict -- an absent key must behave as False,
    not KeyError, since `.get()` is the documented contract."""
    df = pd.DataFrame({"ts_attack_self": [1.0], "us_npxg_r5": [0.2]})
    out = apply_experiment_feature_gating(df, {})
    assert list(out.columns) == [] and len(out) == 1


# --- backtest/walk_forward.py::apply_experiment_feature_gating (plan 10-07) --

def test_feature_gating_drops_tm_family_when_off():
    df = pd.DataFrame({"tm_injured": [1.0], "tm_days_out_so_far": [3.0],
                       "minutes_r5": [90.0]})
    out = apply_experiment_feature_gating(df, {"transfermarkt_injury": False})
    assert not any(c.startswith("tm_") for c in out.columns)
    assert "minutes_r5" in out.columns


def test_feature_gating_keeps_tm_family_when_on():
    df = pd.DataFrame({"tm_injured": [1.0], "tm_days_out_so_far": [3.0]})
    out = apply_experiment_feature_gating(df, {"transfermarkt_injury": True})
    assert "tm_injured" in out.columns and "tm_days_out_so_far" in out.columns


TRANSFERMARKT = config.DATA_DIR / "external" / "transfermarkt" / "injury_spells.csv"


@pytest.mark.skipif(not (FEATURES.exists() and RAW.exists() and TRANSFERMARKT.exists()),
                    reason="run the data pipeline then `python -m data.transfermarkt "
                          "--build` first")
def test_transfermarkt_injury_gate_drops_or_keeps_all_four_on_real_attach():
    """The Task 3 gate proof against REAL data, using `data.transfermarkt.attach`
    directly rather than `models.train.load_features()` -- plan 10-07's own
    Task 2 states the `data/build_table.py` wiring that would put `tm_*`
    columns into a real `features.parquet` lands in plan 10-08 Task 1, not
    here (deliberate sequencing, not an oversight). This test exercises the
    real `attach()` + real `apply_experiment_feature_gating` together so the
    gate is proven end to end without depending on that later wiring commit."""
    import data.transfermarkt as tm
    from models.train import load_features

    d = load_features()
    with_tm = tm.attach(d)

    off = apply_experiment_feature_gating(with_tm, config.resolve_experiments("none"))
    left = [c for c in off.columns if c.startswith("tm_")]
    assert not left, left

    on = apply_experiment_feature_gating(with_tm, config.resolve_experiments("transfermarkt_injury"))
    kept = [c for c in on.columns if c.startswith("tm_")]
    assert len(kept) == len(config.INJURY_COLS), kept


# --- backtest/walk_forward.py::apply_experiment_feature_gating (quick 260909-elx) --

def _ep_next_frame() -> pd.DataFrame:
    """Two players, one player spanning two seasons, kickoff-ordered but
    deliberately shuffled in the input frame -- exercises the sort-before-
    shift path, not luck. Season A / player 1 has a genuine outage gameweek
    (gw=1, xp_fpl=0.0 for BOTH players -- an all-zero group) whose null must
    propagate forward as a null lag on player 1's gw=2 fixture, never a
    confident 0.0. Season A / gw=3 is a MIXED zero/non-zero gameweek (player 1
    real 0.0, player 2 real 4.0) and must NOT be masked."""
    return pd.DataFrame({
        "season":       ["A", "A", "A", "A", "B", "A", "A"],
        "player_id":    [1,   2,   1,   2,   1,   1,   2],
        "gw":           [1,   1,   2,   2,   1,   3,   3],
        "kickoff_time": pd.to_datetime([
            "2020-01-08", "2020-01-08", "2020-01-15", "2020-01-15",
            "2021-01-01", "2020-01-22", "2020-01-22",
        ]),
        "xp_fpl":       [0.0, 0.0, 5.0, 3.0, 9.0, 0.0, 4.0],
    })


def test_ep_next_flags_off_no_op():
    df = _ep_next_frame()
    out = apply_experiment_feature_gating(df, {})
    assert list(out.columns) == list(df.columns)
    assert "xp_fpl_lag1" not in out.columns
    assert "xp_fpl_now" not in out.columns


def test_ep_next_lag_column_matches_prior_fixture_no_bleed():
    """Season B / player 1's first appearance is null even though player_id 1
    already has a season-A history -- seasons must not bleed. Player 2's
    lag values never see player 1's history -- players must not bleed."""
    df = _ep_next_frame()
    out = apply_experiment_feature_gating(df, {"ep_next_lag": True})
    assert "xp_fpl_lag1" in out.columns

    got = out.set_index(["season", "player_id", "gw"])["xp_fpl_lag1"]
    # Season A player 1: gw1 first appearance -> null; gw2 -> null (gw1 was
    # an all-zero OUTAGE group, masked to null before the shift); gw3 -> 5.0
    # (gw2's real, unmasked value).
    assert pd.isna(got[("A", 1, 1)])
    assert pd.isna(got[("A", 1, 2)])
    assert got[("A", 1, 3)] == pytest.approx(5.0)
    # Season A player 2: gw1 first appearance -> null (own outage-masked
    # value never appears as ITS OWN lag); gw2 -> null (gw1 masked); gw3 ->
    # 3.0 (gw2's real value).
    assert pd.isna(got[("A", 2, 1)])
    assert pd.isna(got[("A", 2, 2)])
    assert got[("A", 2, 3)] == pytest.approx(3.0)
    # Season B player 1: first appearance in a NEW season -> null, even
    # though player 1 has season-A history right before it chronologically.
    assert pd.isna(got[("B", 1, 1)])


def test_ep_next_now_masks_outage_but_not_mixed_gameweek():
    df = _ep_next_frame()
    out = apply_experiment_feature_gating(df, {"ep_next_now": True})
    assert "xp_fpl_now" in out.columns
    assert "xp_fpl_lag1" not in out.columns  # own flag was off

    got = out.set_index(["season", "player_id", "gw"])["xp_fpl_now"]
    # gw1 (season A): both players' xp_fpl are 0.0 -> an ALL-ZERO group ->
    # masked to null for both.
    assert pd.isna(got[("A", 1, 1)])
    assert pd.isna(got[("A", 2, 1)])
    # gw3 (season A): player 1 is a genuine 0.0, player 2 is 4.0 -> a MIXED
    # group -> NOT masked; player 1's real zero survives as 0.0.
    assert got[("A", 1, 3)] == 0.0
    assert got[("A", 2, 3)] == pytest.approx(4.0)
    # gw2 (season A) and season B's row never touch an all-zero group.
    assert got[("A", 1, 2)] == pytest.approx(5.0)
    assert got[("A", 2, 2)] == pytest.approx(3.0)
    assert got[("B", 1, 1)] == pytest.approx(9.0)


def test_ep_next_xp_fpl_literal_survives_every_flag_combination():
    """xp_fpl and benchmark_external/walk_forward both score it as the FPL
    baseline -- it must never be dropped or renamed by this gate."""
    df = _ep_next_frame()
    for flags in ({}, {"ep_next_lag": True}, {"ep_next_now": True},
                  {"ep_next_lag": True, "ep_next_now": True}):
        out = apply_experiment_feature_gating(df, flags)
        assert "xp_fpl" in out.columns
        assert (out["xp_fpl"].to_numpy() == df["xp_fpl"].to_numpy()).all()


def test_ep_next_registry_keys_present_and_off():
    assert {"ep_next_lag", "ep_next_now"} <= set(config.EXPERIMENTS)
    assert config.EXPERIMENTS["ep_next_lag"] is False
    assert config.EXPERIMENTS["ep_next_now"] is False
    assert {"ep_next_lag", "ep_next_now"} <= _EXPERIMENT_KEYS


def test_ep_next_flags_stay_off_after_measurement():
    """Quick task 260909-elx's addendum found ep_next_lag doesn't clear the
    D-05 bar (2223 vs >=2280) and ep_next_now clears it only via a
    provenance-tainted signal (backtest/ep_next_provenance.py's control
    found the historical column materially more confident than a genuine
    pre-deadline capture could honestly be, non-overlapping 95% intervals) --
    REJECTED both ways. This pins both flags off explicitly so a future
    change that silently adopts either fails a test, not a diff review."""
    assert config.EXPERIMENTS["ep_next_lag"] is False
    assert config.EXPERIMENTS["ep_next_now"] is False


# --- backtest/benchmark_external.py::_resolve_gate_experiments (quick 260909-elx Task 2) --

def test_benchmark_experiments_arg_none_preserves_ungated_default():
    """Omitting --experiments must resolve to None (score() skips gating
    entirely, reproducing this module's pre-existing ungated behaviour --
    F7), while the explicit 'none' token resolves to a real all-False dict
    that DOES gate (dropping ts_/us_/fm_ at all-off, unlike the omitted
    case, which never gates at all)."""
    from backtest.benchmark_external import _resolve_gate_experiments

    assert _resolve_gate_experiments(None) is None

    resolved = _resolve_gate_experiments("none")
    assert resolved is not None
    assert not any(resolved.values())


def test_benchmark_experiments_arg_forces_named_flags():
    from backtest.benchmark_external import _resolve_gate_experiments

    resolved = _resolve_gate_experiments("ep_next_lag")
    assert resolved is not None
    assert resolved["ep_next_lag"] is True
    assert sum(resolved.values()) == 1


# --- models.captaincy --------------------------------------------------------

def _hand_built_artifact() -> dict:
    """Same shape models.intervals.fit_intervals() produces: one bin per
    position covering the whole xp_med range used below."""
    positions = {}
    for pos, q90 in (("GK", 1.0), ("DEF", 1.5), ("MID", 2.0), ("FWD", 2.5)):
        positions[pos] = {
            "edges": [0.0, 10.0],
            "bins": [{"q10": -1.0, "q25": -0.5, "q75": 0.5, "q90": q90}],
        }
    return {"xp_col": "xp_med", "n_bins": 1, "positions": positions}


def test_add_ceiling_ev_matches_formula_row_by_row():
    artifact = _hand_built_artifact()
    preds = pd.DataFrame({
        "position": ["GK", "DEF", "MID", "FWD"],
        "xp_med": [2.0, 3.0, 4.0, 5.0],
        "xp_mean": [2.5, 3.5, 4.5, 5.5],
    })
    lam = 0.5
    out = captaincy.add_ceiling_ev(preds, artifact, lam=lam)
    expected = out["xp_mean"] + lam * (out["p90"] - out["xp_med"])
    assert np.allclose(out["xp_capt_ceiling"].to_numpy(), expected.to_numpy())


def test_add_ceiling_ev_lam_zero_reproduces_xp_mean():
    artifact = _hand_built_artifact()
    preds = pd.DataFrame({
        "position": ["GK", "DEF", "MID", "FWD"],
        "xp_med": [2.0, 3.0, 4.0, 5.0],
        "xp_mean": [2.5, 3.5, 4.5, 5.5],
    })
    out = captaincy.add_ceiling_ev(preds, artifact, lam=0.0)
    assert np.allclose(out["xp_capt_ceiling"].to_numpy(), out["xp_mean"].to_numpy())


# --- backtest.enrichment_slices.cell_stats (quick 260909-5vx) ---------------

def test_cell_stats_identical_predictions_zero_delta():
    """off == on -> zero MAE delta with a zero-width interval, no signal."""
    gen = np.random.default_rng(0)
    n = 250
    y = gen.normal(size=n)
    off = y + gen.normal(0, 1.0, size=n)
    on = off.copy()
    out = cell_stats(off, on, y, np.random.default_rng(1))
    assert out["d_mae"] == 0.0
    assert out["d_mae_lo"] == 0.0
    assert out["d_mae_hi"] == 0.0
    assert out["signal"] is False


def test_cell_stats_detects_strictly_better_on_column():
    """on == y exactly (zero error); off carries a large offset + noise error
    (worse MAE and a materially disrupted rank order) -> a detected signal."""
    gen = np.random.default_rng(2)
    n = 250
    y = gen.normal(size=n)
    on = y.copy()
    off = y + 5.0 + gen.normal(0, 3.0, size=n)
    out = cell_stats(off, on, y, np.random.default_rng(3))
    assert out["d_mae"] < 0.0
    assert out["d_mae_hi"] < 0.0
    assert out["signal"] is True


def test_cell_stats_strictly_worse_on_column_never_signals():
    """Same columns as the previous test, swapped: a strictly worse `on`
    column must never be reported as a signal, regardless of Spearman."""
    gen = np.random.default_rng(2)
    n = 250
    y = gen.normal(size=n)
    off = y.copy()
    on = y + 5.0 + gen.normal(0, 3.0, size=n)
    out = cell_stats(off, on, y, np.random.default_rng(3))
    assert out["d_mae"] > 0.0
    assert out["signal"] is False


def test_cell_stats_small_n_guard():
    """Fewer than MIN_CELL_N rows -> full key set present, signal False, and
    a note naming the small-sample reason; the bootstrap is skipped."""
    gen = np.random.default_rng(4)
    n = 50
    y = gen.normal(size=n)
    off = y.copy()
    on = y.copy()
    out = cell_stats(off, on, y, np.random.default_rng(5))
    for key in ("n", "mae_off", "mae_on", "d_mae", "d_mae_lo", "d_mae_hi",
                "spearman_off", "spearman_on", "d_spearman", "d_spearman_lo",
                "d_spearman_hi", "signal", "note"):
        assert key in out, key
    assert out["n"] == n
    assert out["signal"] is False
    assert out["note"] != "" and "200" in out["note"]


@needs_data
def test_fit_ceiling_artifact_shape():
    """Uses a real (small, single-season) train_predict run rather than
    stubbing models.train -- fit_ceiling_artifact's contract is that it can
    consume a real per-position model dict, not a mock. No full walk-forward
    is invoked; only the models the harness itself would produce."""
    from backtest.walk_forward import DATA_SEASONS, _preds_for
    from models.train import load_features

    df = load_features()
    test_season = "2025-26"
    _te, models, cols = _preds_for(df, test_season)
    val_season = DATA_SEASONS[DATA_SEASONS.index(test_season) - 1]

    artifact = captaincy.fit_ceiling_artifact(models, df, val_season, cols)
    assert "positions" in artifact
    assert len(artifact["positions"]) > 0
    for spec in artifact["positions"].values():
        assert "edges" in spec
        assert "bins" in spec


# --- backtest.capt_ceiling_ci (quick 260909-dga) -----------------------------


def test_capture_ratio_is_ratio_of_sums_not_mean_of_ratios():
    """best_pts varies across gameweeks -> ratio-of-sums must differ from the
    mean of per-gameweek ratios, and capture_ratio must match the former."""
    capt_pts = np.array([1.0, 8.0])
    best_pts = np.array([2.0, 8.0])
    ratio_of_sums = capture_ratio(capt_pts, best_pts)          # (1+8)/(2+8) = 0.9
    mean_of_ratios = float(np.mean(capt_pts / best_pts))        # (0.5+1.0)/2 = 0.75
    assert ratio_of_sums != pytest.approx(mean_of_ratios)
    assert ratio_of_sums == pytest.approx(0.9)


def test_capture_ratio_zero_denominator_guard():
    """All-zero best_pts must return a finite value, not inf/nan/raise --
    mirrors walk_forward.py:308's max(sum(best_pts), 1) guard."""
    out = capture_ratio(np.array([0.0, 0.0]), np.array([0.0, 0.0]))
    assert np.isfinite(out)
    assert out == 0.0


def test_paired_t_interval_reproduces_f3_capt_capture():
    """The six capt_capture deltas from the plan's measured_facts F3 (baseline
    vs capt_ceiling, wf_baseline_phase9.csv / wf_capt_ceiling_adopt.csv) must
    reproduce F3's published mean and 95% CI to 4 decimal places."""
    deltas = [0.026, -0.014, -0.012, 0.008, 0.056, 0.024]
    out = paired_t_interval(deltas)
    assert out["mean"] == pytest.approx(0.0147, abs=1e-4)
    assert out["ci_lo"] == pytest.approx(-0.0131, abs=1e-4)
    assert out["ci_hi"] == pytest.approx(0.0424, abs=1e-4)


def test_paired_t_interval_reproduces_f3_model_chips():
    """Same reproduction check for the model+chips deltas in F3."""
    deltas = [56, -28, -30, -8, -18, 121]
    out = paired_t_interval(deltas)
    assert out["mean"] == pytest.approx(15.5, abs=0.05)
    assert out["se"] == pytest.approx(24.77, abs=0.05)
    assert out["ci_lo"] == pytest.approx(-48.2, abs=0.1)
    assert out["ci_hi"] == pytest.approx(79.2, abs=0.1)


def test_paired_cluster_bootstrap_degenerate_sum_metric_collapses_to_point():
    """Clusters (seasons) whose gameweek rows are all identical within the
    season -> resampling with replacement cannot change either arm's sum, so
    the returned interval collapses to a point at the observed delta."""
    off_df = pd.DataFrame({"season": ["2020-21"] * 4 + ["2021-22"] * 4,
                           "gw": list(range(4)) * 2,
                           "points": [10.0] * 4 + [20.0] * 4})
    on_df = off_df.copy()
    on_df["points"] = off_df["points"] + 2.0   # constant per-row offset
    out = paired_cluster_bootstrap(off_df, on_df, ["points"], False, 500, seed=0)
    observed = float(on_df["points"].sum() - off_df["points"].sum())
    assert out["ci_lo"] == pytest.approx(observed)
    assert out["ci_hi"] == pytest.approx(observed)


def test_capt_ceiling_and_capt_mc_flags_stay_off():
    """Quick task 260909-dga's addendum found no season-clustered signal for
    capt_ceiling (95% CI straddles zero on capt_capture/capt_mean/model+chips)
    -- REJECTION CONFIRMED. This pins both captaincy flags off explicitly so
    a future change that silently adopts either fails a test, not a diff
    review, matching the plan's own guard requirement."""
    assert config.EXPERIMENTS["capt_ceiling"] is False
    assert config.EXPERIMENTS["capt_mc"] is False


def test_paired_cluster_bootstrap_degenerate_ratio_metric_collapses_to_point():
    """Same degenerate-cluster property for the ratio-of-sums path (the one
    capt_capture actually uses) -- resampling identical-within-season rows
    cannot move either arm's ratio."""
    off_df = pd.DataFrame({"season": ["2020-21"] * 3 + ["2021-22"] * 3,
                           "gw": list(range(3)) * 2,
                           "capt_pts": [4.0, 4.0, 4.0, 6.0, 6.0, 6.0],
                           "best_pts": [8.0, 8.0, 8.0, 10.0, 10.0, 10.0]})
    on_df = off_df.copy()
    on_df["capt_pts"] = off_df["capt_pts"] + 1.0
    out = paired_cluster_bootstrap(off_df, on_df, ["capt_pts", "best_pts"], True, 500, seed=0)
    off_ratio = off_df["capt_pts"].sum() / off_df["best_pts"].sum()
    on_ratio = on_df["capt_pts"].sum() / on_df["best_pts"].sum()
    observed = float(on_ratio - off_ratio)
    assert out["ci_lo"] == pytest.approx(observed)
    assert out["ci_hi"] == pytest.approx(observed)
