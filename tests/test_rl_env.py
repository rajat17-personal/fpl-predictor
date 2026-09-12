"""Phase 9 plan 09-06 regression tests: `optimize.rl_env.FplStrategyEnv`, the
Gymnasium environment for the RL chip-timing/transfer-count experiment
(D-02). None of these tests train anything -- they only exercise reset(),
step(), and action_masks() against the frozen 2025-26 test predictions.

The anti-Pitfall-4 test (`test_reward_matches_run_season_hold_policy`) is the
most important one in this file: it proves the environment's cumulative
reward reproduces `backtest.season.run_season`'s own realised-points total
for an equivalent configuration, closing off the exact honest-vs-optimistic
gap that made FPL-RL's own headline number in-sample.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from gymnasium import spaces

import config
from backtest import season as season_mod
from optimize.rl_env import CHIPS_ORDER, TRANSFER_CAPS, FplStrategyEnv

FEATURES = config.PROCESSED_DIR / "features.parquet"
TEST_PREDS = config.PROCESSED_DIR / "test_predictions.parquet"
needs_data = pytest.mark.skipif(
    not (FEATURES.exists() and TEST_PREDS.exists()),
    reason="run the data pipeline + walk-forward backtest first")

HOLD_ACTION = CHIPS_ORDER.index("-") * len(TRANSFER_CAPS) + TRANSFER_CAPS.index(0)


@needs_data
def test_reset_returns_valid_observation():
    env = FplStrategyEnv(season="2025-26")
    obs, info = env.reset(seed=0)
    assert obs.shape == env.observation_space.shape
    assert env.observation_space.contains(obs)
    assert info == {}


@needs_data
def test_action_masks_marks_used_chip_illegal_after_use():
    env = FplStrategyEnv(season="2025-26")
    env.reset(seed=0)
    wc_action = CHIPS_ORDER.index("wc") * len(TRANSFER_CAPS) + TRANSFER_CAPS.index(0)

    mask_before = env.action_masks()
    assert mask_before[wc_action], "wc should be legal before it has ever been played"
    assert mask_before.any(), "every action masked out is never expected before any chip is used"

    env.step(wc_action)
    mask_after = env.action_masks()
    assert not mask_after[wc_action], "wc must be masked out immediately after being played"
    assert mask_after.any(), "using one chip must not mask every remaining action"


@needs_data
def test_action_masks_masks_transfer_above_budget():
    env = FplStrategyEnv(season="2025-26")
    env.reset(seed=0)
    # free_transfers=1 at kickoff -> legal cap ceiling is 1 + HIT_BUDGET(2) = 3.
    over_budget = (CHIPS_ORDER.index("-") * len(TRANSFER_CAPS)
                  + TRANSFER_CAPS.index(TRANSFER_CAPS[-1]))
    mask = env.action_masks()
    assert not mask[over_budget], "a transfer count above free transfers + hit budget must be masked"


@needs_data
def test_action_space_one_dim_and_bounded():
    env = FplStrategyEnv(season="2025-26")
    assert isinstance(env.action_space, spaces.Discrete)
    assert env.action_space.n == len(CHIPS_ORDER) * len(TRANSFER_CAPS)
    assert env.action_space.n < 200


@needs_data
def test_reset_seed_reproducible():
    env = FplStrategyEnv(season="2025-26")
    o1, _ = env.reset(seed=7)
    o2, _ = env.reset(seed=7)
    assert np.allclose(o1, o2)
    assert env.observation_space.contains(o1)


@needs_data
def test_reward_matches_run_season_hold_policy():
    """The anti-Pitfall-4 test: a full-season 'never transfer, never use a
    chip' policy stepped through the environment must sum to exactly what
    `run_season` scores for the same configuration -- both call the identical
    `build_gw_pool`/`optimize_gw`/`_score` chain with identical inputs, so
    the two trajectories (squad, bank, free transfers) evolve identically."""
    preds = pd.read_parquet(TEST_PREDS)
    if "season" in preds.columns:
        preds = preds[preds.season == "2025-26"]

    expected = season_mod.run_season(preds, "xp_med", use_chips=False,
                                     max_transfers=0, capt_col="xp_mean")
    expected_total = float(expected.points.sum())

    env = FplStrategyEnv(season="2025-26")
    env.reset(seed=0)
    total = env.initial_points
    terminated = False
    while not terminated:
        _, reward, terminated, _, _ = env.step(HOLD_ACTION)
        total += reward

    assert abs(total - expected_total) < 1e-6, (
        f"env cumulative reward {total} != run_season total {expected_total}")


# --- optimize/rl_train.py::train_seasons_for (plan 09-07 D2) -----------

def test_train_seasons_for_returns_only_prior_test_seasons():
    """Plan 09-07 D2: train_seasons_for(T) returns only TEST_SEASONS members
    strictly before T. Matches TEST_SEASONS' own first-class position in the
    harness: team-attribution data is only populated from 2020-21 onward,
    so no usable squad pool exists for seasons before that."""
    pytest.importorskip("sb3_contrib", minversion=None)
    from optimize.rl_train import train_seasons_for, TEST_SEASONS

    result = train_seasons_for("2025-26")
    # Should be all test seasons except the latest
    expected = TEST_SEASONS[:-1]
    assert result == expected
    # Verify they are strictly less than the test season
    for s in result:
        assert s < "2025-26"


def test_train_seasons_for_raises_for_earliest_test_season():
    """Plan 09-07 D2: train_seasons_for('2020-21') raises ValueError because
    there is no earlier TEST_SEASONS member to train on. The 2020-21 season is
    the first test season (where team data becomes available), so it has no
    prior usable training season."""
    pytest.importorskip("sb3_contrib", minversion=None)
    from optimize.rl_train import train_seasons_for

    with pytest.raises(ValueError) as exc:
        train_seasons_for("2020-21")
    msg = str(exc.value)
    assert "2020-21" in msg
    assert "no earlier" in msg.lower()


def test_train_seasons_for_raises_for_non_test_season():
    """Plan 09-07 D2: train_seasons_for(T) raises ValueError when T is not
    a valid TEST_SEASONS member, even if T is in DATA_SEASONS."""
    pytest.importorskip("sb3_contrib", minversion=None)
    from optimize.rl_train import train_seasons_for

    with pytest.raises(ValueError) as exc:
        train_seasons_for("2016-17")
    msg = str(exc.value)
    assert "2016-17" in msg
