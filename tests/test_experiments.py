"""Phase 9 regression tests: the experiment flag registry and captaincy
ceiling EV every later experiment plan builds on top of."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
from backtest.season import run_season
from backtest.walk_forward import apply_experiment_feature_gating, resolve_scheduler
from models import captaincy

FEATURES = config.PROCESSED_DIR / "features.parquet"
RAW = config.PROCESSED_DIR / "player_gw.parquet"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")

_EXPERIMENT_KEYS = {"capt_ceiling", "capt_mc", "chips_v2", "team_strength",
                    "rl_strategy", "understat", "fotmob", "fbref_v2"}


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
