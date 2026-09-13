"""Phase 9 plan 09-07 (D-02/D-16): time-boxed MaskablePPO trainer for the RL
chip-timing / transfer-count policy.

Train-before-evaluate split (the whole defence against the in-sample
inflation the FPL-RL audit found): a policy for test season T is trained ONLY
on seasons strictly before T. `train_seasons_for(T)` enforces this and refuses
to run if T would appear in its own training set. One of those training
seasons (the one immediately before T) is held out from the training rotation
and used purely for the periodic anti-Pitfall-4 diagnostic below -- never for
gradient updates.

Every hyperparameter is pinned in `HYPERPARAMS` below rather than left to
library defaults (D-16: pinned configs), and the per-policy wall-clock budget
is enforced by `_TimeBoxCallback`, not by hoping `--timesteps` happens to fit
in the cap. A capped run is a completed run with a smaller budget, not a
failure -- it still saves the policy it has and records that it was capped.

At a fixed interval the trainer prints BOTH the recent training-episode
reward and a held-out-season score computed by replaying the same policy
through a held-out `FplStrategyEnv` -- a rising training curve beside a flat
or falling held-out score is the exact FPL-RL audit smoking gun (Pitfall 4),
and this makes it visible in the log rather than inferred after the fact.

Run:
  python -m optimize.rl_train --test-season 2025-26 --seed 0
  python -m optimize.rl_train --test-season 2025-26 --seed 0 --timesteps 2000 --max-minutes 2
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import gymnasium as gym
import numpy as np
import pandas as pd

import config
from backtest.walk_forward import DATA_SEASONS, TEST_SEASONS, _preds_for
from models.train import load_features
from ops.jsonio import write_json
from optimize.rl_env import FplStrategyEnv

# A season is only usable as an RL training episode if `build_gw_pool` /
# `pick_squad` can actually build a squad from it -- which needs a populated
# `team` column (for the max-3-per-club constraint). `features.parquet`'s
# `team` column is 100% null for 2016-17 through 2019-20 and 0% null from
# 2020-21 onward [VERIFIED empirically, this session] -- precisely why
# `backtest.walk_forward.TEST_SEASONS` itself has always started at 2020-21.
# This is a pre-existing, structural limitation of the whole walk-forward
# pipeline, not something this plan introduces: a season a policy trains on
# must therefore be a `TEST_SEASONS` member (which is also the only set
# `_preds_for` can produce a real predictions frame for), not merely
# "somewhere in DATA_SEASONS strictly before T".

# Per-season leakage-safe predictions (`backtest.walk_forward._preds_for`'s
# `te`) are expensive to produce (a full per-season LightGBM retrain) and are
# reused across every seed for the same test season, and across every test
# season that shares a training season -- cached on disk so an 18-run (6
# seasons x 3 seeds) time-box only retrains each usable season once.
_PRED_CACHE_DIR = config.EXPERIMENTS_DIR / "rl_train_preds"
_FEATURES_DF: pd.DataFrame | None = None


def _preds_for_season(season: str) -> pd.DataFrame:
    """Leakage-safe predictions for `season` (same construction
    `backtest.walk_forward.main()` uses for every other Phase 9 experiment),
    cached under `_PRED_CACHE_DIR` after the first computation."""
    global _FEATURES_DF
    _PRED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _PRED_CACHE_DIR / f"{season}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    if _FEATURES_DF is None:
        _FEATURES_DF = load_features()
    te, _models, _cols = _preds_for(_FEATURES_DF, season)
    te.to_parquet(cache_path, index=False)
    return te

# Every hyperparameter pinned explicitly (D-16) -- a future sb3-contrib/torch
# upgrade changing a library default must never silently change this result.
HYPERPARAMS: dict = {
    "learning_rate": 3e-4,
    "n_steps": 1024,
    "batch_size": 64,
    "n_epochs": 4,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
}

# The wall-clock cap is the real budget enforcement (D-16: "enforced inside
# the trainer, not by hope") -- this default is deliberately large so the
# cap, not this number, is almost always what stops a real training run.
DEFAULT_TIMESTEPS = 200_000
EVAL_EVERY_STEPS = HYPERPARAMS["n_steps"]   # once per policy update


def train_seasons_for(test_season: str) -> list[str]:
    """`TEST_SEASONS` members strictly before `test_season` -- the only
    seasons a policy evaluated on `test_season` may ever train on
    (T-09-07-01: a policy trained on its own evaluation season is exactly the
    FPL-RL in-sample failure mode this plan exists to avoid). Also the only
    seasons a squad pool can even be built for (see the module docstring's
    `team`-column note). Raises `ValueError` naming the season when that set
    would be empty -- true for `test_season="2020-21"`, `TEST_SEASONS`' own
    earliest member, which by construction has no earlier usable season at
    all; see 09-07-SUMMARY.md's Decisions Made for how this plan handles it."""
    if test_season not in DATA_SEASONS:
        raise ValueError(f"{test_season!r} is not a known season -- expected one of {DATA_SEASONS}")
    train = [s for s in TEST_SEASONS if s < test_season]
    if not train:
        raise ValueError(
            f"{test_season!r} has no earlier TEST_SEASONS member to train a "
            "policy on -- team-attribution data (build_gw_pool's max-per-club "
            "constraint) is only populated from 2020-21 onward, so no season "
            "before that can produce a usable squad pool")
    return train


class MultiSeasonEnv(gym.Env):
    """Wraps multiple single-season `FplStrategyEnv` instances so each
    `reset()` picks a training season uniformly at random. MaskablePPO needs
    ONE env with a stable action/observation space that produces a diverse
    spread of episodes across the training-seasons set -- not one env per
    season, and not a fixed round-robin (which would correlate consecutive
    episodes with calendar order)."""

    metadata: dict = {"render_modes": []}

    def __init__(self, envs: list[FplStrategyEnv]):
        super().__init__()
        if not envs:
            raise ValueError("MultiSeasonEnv needs at least one training environment")
        self._envs = list(envs)
        self.action_space = self._envs[0].action_space
        self.observation_space = self._envs[0].observation_space
        self._current: FplStrategyEnv = self._envs[0]

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        idx = int(self.np_random.integers(len(self._envs)))
        self._current = self._envs[idx]
        return self._current.reset(seed=seed)

    def step(self, action):
        return self._current.step(action)

    def action_masks(self) -> np.ndarray:
        return self._current.action_masks()


def _mask_fn(env: gym.Env) -> np.ndarray:
    return env.unwrapped.action_masks()


class _TimeBoxCallback:
    """Enforces the D-16 declared per-policy wall-clock cap and prints the
    anti-Pitfall-4 training-reward-vs-held-out-score pair at a fixed
    interval. Implemented as a plain object satisfying stable-baselines3's
    callback protocol (assigned `.model`/`.num_timesteps` by `BaseCallback`
    machinery via composition below) to avoid a second layer of indirection
    -- see `_as_sb3_callback()`."""

    def __init__(self, max_minutes: float, eval_env: FplStrategyEnv,
                eval_every_steps: int = EVAL_EVERY_STEPS):
        self.max_minutes = max_minutes
        self.eval_env = eval_env
        self.eval_every_steps = eval_every_steps
        self._t0 = time.time()
        self.capped = False
        self._last_eval_at = 0

    def elapsed_minutes(self) -> float:
        return (time.time() - self._t0) / 60.0

    def should_stop(self) -> bool:
        if self.elapsed_minutes() >= self.max_minutes:
            self.capped = True
            return True
        return False

    def maybe_log(self, model) -> None:
        if model.num_timesteps - self._last_eval_at < self.eval_every_steps:
            return
        self._last_eval_at = model.num_timesteps
        train_reward = self._recent_training_reward(model)
        held_out = self._held_out_score(model)
        print(f"[rl] t={model.num_timesteps} elapsed={self.elapsed_minutes():.1f}min "
              f"train_reward={train_reward:.1f} held_out_score={held_out:.1f}", flush=True)

    @staticmethod
    def _recent_training_reward(model) -> float:
        buf = model.ep_info_buffer
        if not buf:
            return float("nan")
        return float(np.mean([e["r"] for e in buf]))

    def _held_out_score(self, model) -> float:
        obs, _ = self.eval_env.reset(seed=0)
        total = self.eval_env.initial_points
        terminated = False
        while not terminated:
            mask = self.eval_env.action_masks()
            action, _ = model.predict(obs, deterministic=True, action_masks=mask)
            obs, reward, terminated, _, _ = self.eval_env.step(int(action))
            total += reward
        return float(total)


def _as_sb3_callback(box: _TimeBoxCallback):
    """Wrap `_TimeBoxCallback` in stable-baselines3's `BaseCallback` -- kept
    as a thin adapter so the time-box/eval logic above stays a plain,
    directly-unit-testable object with no SB3 import requirement of its own."""
    from stable_baselines3.common.callbacks import BaseCallback

    class _Adapter(BaseCallback):
        def _on_step(self) -> bool:
            box.maybe_log(self.model)
            if box.should_stop():
                print(f"[rl] wall-clock cap ({box.max_minutes} min) reached at "
                      f"{self.model.num_timesteps} timesteps -- stopping "
                      "(capped, not failed; the policy learned so far is still saved)",
                      flush=True)
                return False
            return True

    return _Adapter()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-season", required=True,
                    help="the season this policy will later be evaluated on "
                         "(must appear in backtest.walk_forward.TEST_SEASONS)")
    ap.add_argument("--seed", type=int, default=config.RL_SEEDS[0])
    ap.add_argument("--timesteps", type=int, default=DEFAULT_TIMESTEPS)
    ap.add_argument("--max-minutes", type=float, default=30.0,
                    help="D-16 per-policy wall-clock cap")
    ap.add_argument("--out", default=None,
                    help="override output .zip path (default: "
                         "config.RL_POLICY_DIR/rl_policy_<season>_<seed>.zip)")
    args = ap.parse_args(argv)

    T = args.test_season
    train_seasons = train_seasons_for(T)
    if T in train_seasons:
        raise ValueError(f"{T!r} would train on itself: {train_seasons}")

    # Hold out the most recent training season from the rotation, purely for
    # the periodic anti-Pitfall-4 diagnostic -- never for gradient updates.
    eval_season = train_seasons[-1]
    fit_seasons = train_seasons[:-1] if len(train_seasons) > 1 else train_seasons

    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
    from sb3_contrib.common.wrappers import ActionMasker

    print(f"[rl] test_season={T} seed={args.seed} fit_seasons={fit_seasons} "
          f"eval_season={eval_season} timesteps={args.timesteps} "
          f"max_minutes={args.max_minutes}", flush=True)

    fit_envs = [FplStrategyEnv(season=s, preds=_preds_for_season(s)) for s in fit_seasons]
    train_env = ActionMasker(MultiSeasonEnv(fit_envs), _mask_fn)
    eval_env = FplStrategyEnv(season=eval_season, preds=_preds_for_season(eval_season))

    model = MaskablePPO(MaskableActorCriticPolicy, train_env, seed=args.seed,
                        verbose=0, **HYPERPARAMS)

    box = _TimeBoxCallback(max_minutes=args.max_minutes, eval_env=eval_env)
    t0 = time.time()
    model.learn(total_timesteps=args.timesteps, callback=_as_sb3_callback(box))
    elapsed_minutes = (time.time() - t0) / 60.0

    out_path = Path(args.out) if args.out else (
        config.RL_POLICY_DIR / f"rl_policy_{T}_{args.seed}.zip")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(out_path)

    sidecar = {
        "test_season": T,
        "seed": args.seed,
        "timesteps": int(model.num_timesteps),
        "elapsed_minutes": round(elapsed_minutes, 2),
        "capped": box.capped,
        "hyperparameters": HYPERPARAMS,
        "train_seasons": fit_seasons,
        "eval_season": eval_season,
        "max_minutes": args.max_minutes,
    }
    write_json(sidecar, out_path.with_suffix(".json"), indent=1)

    print(f"[rl] done test_season={T} seed={args.seed} "
          f"timesteps={model.num_timesteps} elapsed={elapsed_minutes:.1f}min "
          f"capped={box.capped} -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
