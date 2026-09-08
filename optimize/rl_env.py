"""Phase 9 plan 09-06 (D-02): Gymnasium environment for the RL chip-timing /
transfer-count experiment.

`FplStrategyEnv` steps one real season, one gameweek at a time. The policy
chooses ONLY which chip to play this gameweek (or none) and how many
transfers to make -- `optimize/squad_ilp.py` and `optimize/transfers.py`
remain the un-learned player-selection step, called from inside `step()`
exactly as `backtest/season.py::run_season` calls them. An action space that
also picked players would reinvent the ILP badly and throw away its
optimality guarantee (D-02's hybrid split).

The reward is the realised gameweek points net of transfer hits, computed by
REUSING `backtest.season`'s own scoring helpers directly (`_score`,
`_pad_holdings`, `_squad_from_pick`, `_team_value`, `_update_meta`) rather
than reimplementing autosubs or the captain multiplier -- the two can never
drift apart. FPL-RL's own audited 2,918-point headline turned out to be
in-sample precisely because it was judged on a different (optimistic) signal
than the honest walk-forward harness measures; this environment cannot
repeat that mistake because it steps through the harness's OWN scoring
function, never xP.

Run a quick smoke check (always plays the first legal action -> a full-season
hold with no chips):
  python -m optimize.rl_env
"""
from __future__ import annotations

import sys

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

import config
from backtest import season as season_mod
from optimize import chips
from optimize.squad_ilp import build_gw_pool, pick_squad
from optimize.transfers import optimize_gw

XP_COL = "xp_med"        # squad-selection objective (matches the shipped default)
CAPT_COL = "xp_mean"     # captain-slot objective (armband doubles points -> E[pts])

# Action space: a fixed (chip choice x transfer count) grid, independent of
# the player pool -- never large enough to imply player selection (D-02).
CHIPS_ORDER = ("-", "wc", "fh", "bb", "tc")                       # "-" = no chip this gw
TRANSFER_CAPS = tuple(range(0, config.MAX_FREE_TRANSFERS + 3))    # 0..7: FTs + a 2-hit budget
HIT_BUDGET = 2           # extra hits beyond free transfers a legal action may take

HORIZON = 4              # gameweeks of decay-forward "own form" horizon signal
DECAY = 0.84             # matches optimize/chips.py::SCORED_DECAY / _plan_col's own decay

OBS_DIM = 11


def _half_of(gw: int) -> str:
    for half, gws in chips.HALVES.items():
        if gw in gws:
            return half
    raise ValueError(f"gw {gw} is not in any half")


class FplStrategyEnv(gym.Env):
    """One season, one gameweek per `step()`.

    Action: a single `Discrete(len(CHIPS_ORDER) * len(TRANSFER_CAPS))` index,
    decoded as `(chip, transfer_cap) = divmod(action, len(TRANSFER_CAPS))`.
    Reward: `backtest.season`-style realised points net of transfer hits.

    No realised outcome (`y_points`/`y_minutes`/actual) ever appears in the
    observation -- only predictions (`xp_med`/`xp_mean`) and decision-time
    state (bank, free transfers, chips remaining, public fixture schedule).
    """

    metadata: dict = {"render_modes": []}

    def __init__(self, season: str = "2025-26", preds: pd.DataFrame | None = None):
        super().__init__()
        if preds is None:
            preds = pd.read_parquet(config.PROCESSED_DIR / "test_predictions.parquet")
        if "season" in preds.columns:
            preds = preds[preds.season == season]
        if preds.empty:
            raise ValueError(f"no rows for season={season!r} in test_predictions data")

        self.season = season
        self.preds = preds.reset_index(drop=True)
        self.gws = sorted(self.preds.gw.unique())
        # Public fixture schedule (which gws a player has any row in) -- knowable
        # ahead of time, never an outcome -- precomputed once for the horizon signal.
        self._gws_by_code: dict[int, set[int]] = (
            self.preds.groupby("player_code")["gw"].apply(set).to_dict())

        self.action_space = spaces.Discrete(len(CHIPS_ORDER) * len(TRANSFER_CAPS))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32)

        # Episode state, populated by reset().
        self._gw_i = 0
        self.squad: dict[int, float] = {}
        self.meta: dict[int, dict] = {}
        self.bank = 0.0
        self.free_transfers = 1
        self.initial_points = 0.0
        self._chip_used: dict[str, set[str]] = {"H1": set(), "H2": set()}

    # -- gymnasium.Env API --------------------------------------------------

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        g0 = self.gws[0]
        pool = build_gw_pool(self.preds, g0, XP_COL, CAPT_COL)
        res = pick_squad(pool, budget=config.BUDGET)
        self.squad, self.meta = season_mod._squad_from_pick(res)
        self.bank = round(config.BUDGET - res["cost"], 1)
        self.free_transfers = 1
        self._chip_used = {"H1": set(), "H2": set()}
        self._gw_i = 0

        pool_idx0 = pool.set_index("player_code")
        starters = list(res["squad"].loc[res["squad"].starting == 1, "player_code"])
        squad_codes = list(res["squad"].player_code)
        captain = int(res["squad"].loc[res["squad"].is_captain == 1, "player_code"].iloc[0])
        self.initial_points = season_mod._score(pool_idx0, starters, squad_codes, captain, "normal")

        return self._observe(), {}

    def step(self, action: int):
        if self._gw_i + 1 >= len(self.gws):
            raise RuntimeError("step() called after the season already ended")
        self._gw_i += 1
        gw = self.gws[self._gw_i]
        chip_idx, tr_idx = divmod(int(action), len(TRANSFER_CAPS))
        chip = CHIPS_ORDER[chip_idx]
        max_transfers = TRANSFER_CAPS[tr_idx]

        pool = build_gw_pool(self.preds, gw, XP_COL, CAPT_COL)
        pool = season_mod._pad_holdings(pool, self.squad, self.meta)
        pool_idx = pool.set_index("player_code")

        if chip in ("wc", "fh"):
            budget = season_mod._team_value(self.squad, pool, self.meta) + self.bank
            r = pick_squad(pool, budget=budget)
            starters, squad_codes, captain = season_mod._pick_lists(r)
            reward = season_mod._score(pool_idx, starters, squad_codes, captain, "normal")
            self.squad, self.meta = season_mod._squad_from_pick(r)
            self.bank = round(budget - r["cost"], 1)
            n_tr, n_hit = 0, 0
            self.free_transfers = min(config.MAX_FREE_TRANSFERS, self.free_transfers + 1)
        else:
            mode = chip if chip in ("tc", "bb") else "normal"
            r = optimize_gw(pool, self.squad, self.bank, self.free_transfers,
                            mode=mode, max_transfers=max_transfers)
            self.squad, self.bank = r["squad"], r["bank"]
            gross = season_mod._score(pool_idx, r["starters"], list(r["squad"]),
                                      r["captain_code"], mode)
            reward = gross - config.TRANSFER_HIT * r["hits"]
            n_tr, n_hit = r["transfers"], r["hits"]
            self.free_transfers = min(config.MAX_FREE_TRANSFERS,
                                      max(0, self.free_transfers - n_tr) + 1)

        if chip != "-":
            self._chip_used[_half_of(gw)].add(chip)
        season_mod._update_meta(self.meta, pool, self.squad)

        terminated = self._gw_i + 1 >= len(self.gws)
        info = {"gw": gw, "chip": chip, "transfers": n_tr, "hits": n_hit}
        return self._observe(), float(reward), terminated, False, info

    def action_masks(self) -> np.ndarray:
        """Boolean vector excluding every illegal action at the current state.

        Illegal: a chip already used in this half; a transfer count above the
        free-transfer + hit budget; any non-zero transfer count paired with a
        wildcard/free-hit (a full squad rebuild makes the count meaningless,
        so only the canonical `transfer_cap=0` pairing is kept for those two
        chips, avoiding redundant equivalent actions in the mask).
        """
        gw = self.gws[self._gw_i]
        half = _half_of(gw)
        used = self._chip_used[half]
        ft_cap = self.free_transfers + HIT_BUDGET
        mask = np.zeros(self.action_space.n, dtype=bool)
        for c_i, chip in enumerate(CHIPS_ORDER):
            if chip != "-" and chip in used:
                continue
            for t_i, cap in enumerate(TRANSFER_CAPS):
                if chip in ("wc", "fh"):
                    if t_i != 0:
                        continue
                elif cap > ft_cap:
                    continue
                mask[c_i * len(TRANSFER_CAPS) + t_i] = True
        return mask

    # -- observation ----------------------------------------------------------

    def _observe(self) -> np.ndarray:
        gw = self.gws[self._gw_i]
        half = _half_of(gw)
        half_gws = list(chips.HALVES[half])
        half_pos = (gw - half_gws[0]) / max(1, half_gws[-1] - half_gws[0])

        cur = self.preds[self.preds.gw == gw]
        by_code = cur.groupby("player_code")[XP_COL].sum()

        horizon_xp = 0.0
        for code in self.squad:
            base = float(by_code.get(code, 0.0))
            fixture_gws = self._gws_by_code.get(code, set())
            for k in range(HORIZON):
                if gw + k in fixture_gws:
                    horizon_xp += (DECAY ** k) * base
        capt_col_sum = cur.groupby("player_code")[CAPT_COL].sum()
        capt_ceiling = float(capt_col_sum.max()) if len(capt_col_sum) else 0.0

        team_value = season_mod._team_value(self.squad, cur, self.meta)
        used = self._chip_used[half]

        return np.array([
            gw / 38.0,
            half_pos,
            self.free_transfers / config.MAX_FREE_TRANSFERS,
            self.bank / config.BUDGET,
            team_value / config.BUDGET,
            0.0 if "wc" in used else 1.0,
            0.0 if "fh" in used else 1.0,
            0.0 if "bb" in used else 1.0,
            0.0 if "tc" in used else 1.0,
            horizon_xp / max(1, len(self.squad)),
            capt_ceiling,
        ], dtype=np.float32)


def main(argv: list[str] | None = None) -> int:
    env = FplStrategyEnv(season="2025-26")
    obs, _ = env.reset(seed=0)
    print(f"season {env.season}: obs shape {obs.shape}, "
          f"action_space.n={env.action_space.n}")
    total = env.initial_points
    terminated = False
    while not terminated:
        legal = np.flatnonzero(env.action_masks())
        action = int(legal[0])   # deterministic smoke: always the first legal action
        obs, reward, terminated, _, info = env.step(action)
        total += reward
    print(f"cumulative reward = {total:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
