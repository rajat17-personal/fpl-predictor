---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 07
subsystem: ml-experimentation
tags: [reinforcement-learning, maskable-ppo, sb3-contrib, chip-scheduling, walk-forward, adoption-decision]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-06's dependency-isolated RL dependency stack (torch/gymnasium/stable-baselines3/sb3-contrib) and optimize/rl_env.py::FplStrategyEnv (masked action space, realised-points reward); plan 09-01's experiment spine (config.EXPERIMENTS, --experiments/--seasons/--tag CLI, tracked 6-season baseline 2262); plan 09-04's chips_v2 verdict (rejected, v1 stays shipped default, and the chips_v2 model+chips figure this plan's D-02 gate is judged against)"
provides:
  - "backtest/season.py::run_season(scheduler=) three-way toggle: v1 (causal_schedule, unchanged), v2 (scored_schedule, plan 09-04), rl (replays a trained MaskablePPO policy per gameweek, deciding both chip and transfer count)"
  - "optimize/rl_env.py: build_observation()/build_action_mask() factored out of FplStrategyEnv so training and the season-loop replay path see byte-identical state; load_policy()/decide_action() for the replay path"
  - "optimize/rl_train.py: python -m optimize.rl_train time-boxed MaskablePPO trainer with pinned hyperparameters, a train-before-evaluate season split, an enforced wall-clock cap, and per-season leakage-safe predictions cached under data/processed/experiments/rl_train_preds/"
  - "backtest/walk_forward.py::resolve_scheduler() -- rl_strategy/chips_v2 flags resolved to exactly one scheduler, hard-exiting if both are on; --rl-seed CLI flag"
  - "D-02 verdict for rl_strategy: REJECTED (seed-mean model+chips 2020 vs chips_v2's 2192 on the same 5 seasons, a -172/season regression), flag stays default-off, code stays merged (D-08)"
affects: [09-08, 09-09, 09-10]

actuals:
  tokens: 11237
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Deferred (function-body) import of optimize.rl_env inside backtest/season.py::run_season's scheduler='rl' branch -- avoids both a circular import (rl_env imports backtest.season at its own top level) and any RL dependency requirement on the weekly product's normal v1/v2 path"
    - "Shared observation/mask builder functions (build_observation/build_action_mask) called by both FplStrategyEnv's own methods and the run_season replay path, so a policy sees byte-identical state whether training or being replayed through the honest harness"
    - "Per-season leakage-safe predictions cache (data/processed/experiments/rl_train_preds/<season>.parquet) so N seeds x M seasons of training never redundantly retrains the same per-season LightGBM model"
    - "Plain-object callback (_TimeBoxCallback) wrapped in a thin BaseCallback adapter, keeping the wall-clock-cap/eval-logging logic free of any stable-baselines3 import of its own"

key-files:
  created:
    - optimize/rl_train.py
  modified:
    - backtest/season.py
    - backtest/walk_forward.py
    - config.py
    - optimize/rl_env.py
    - tests/test_experiments.py
    - IMPROVEMENTS.md

key-decisions:
  - "2020-21 (TEST_SEASONS' own earliest member) is permanently excluded from the RL experiment: features.parquet's team column is 100% null for 2016-17 through 2019-20 and 0% null from 2020-21 onward (verified empirically), so no season before 2020-21 can produce a build_gw_pool-usable squad pool -- exactly why TEST_SEASONS itself has always started there. train_seasons_for(T) therefore only accepts TEST_SEASONS members strictly before T, and the D-02 comparison runs over the 5 seasons that DO have a usable prior season (2021-22..2025-26), not the plan's literal '6 test seasons x 3 seeds = 18 policies' -- 15 policies (5x3) were trained instead, and both rl_strategy and chips_v2 were freshly re-measured on that same 5-season basis for an apples-to-apples comparison"
  - "The two 5-season comparison walk_forward runs (chips_v2_5season, baseline_5season) were killed and re-run sequentially after they stalled for over an hour under CPU oversubscription (load average ~59 on 28 cores) from running concurrently with the 3 parallel RL training processes -- re-running them sequentially after training finished completed in a normal few minutes each"
  - "rl_strategy REJECTED per D-07/D-16's mechanical rule: seed-mean model+chips (2020) falls short of the chips_v2 comparison figure (2192) on every individual seed (1847/2069/2144), not just the mean -- config.EXPERIMENTS['rl_strategy'] stays False, no additional seeds or extended timestep budget were spent chasing the result"

requirements-completed: []

coverage:
  - id: D1
    description: "Three-way v1/v2/rl scheduler toggle on backtest/season.py::run_season and backtest/walk_forward.py, with a hard exit when rl_strategy and chips_v2 are both requested"
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_run_season_bogus_scheduler_raises_naming_all_three"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_scheduler_defaults_to_v1"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_scheduler_chips_v2_flag_maps_to_v2"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_scheduler_rl_strategy_flag_maps_to_rl"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_scheduler_rl_and_chips_v2_together_exits_naming_both"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --experiments rl_strategy,chips_v2 --tag rl_conflict -- exits 1 naming both flags"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag sched_default -- [wf] line echoes scheduler=v1, identical model+chips (2237) on pre- and post-change code (confirmed via git stash -- the 2172 figure in the plan's own acceptance criteria is now stale due to a new gameweek (GW4) landing in test_predictions.parquet since the plan was authored, not a regression)"
        status: pass
    human_judgment: false
  - id: D2
    description: "optimize/rl_train.py: time-boxed MaskablePPO trainer with pinned hyperparameters, train-before-evaluate split, enforced wall-clock cap"
    verification:
      - kind: other
        ref: "python -m optimize.rl_train --help -- lists --test-season/--seed/--timesteps/--max-minutes/--out"
        status: pass
      - kind: other
        ref: "train_seasons_for('2016-17') and train_seasons_for('2020-21') both raise ValueError; train_seasons_for(T) for the 5 trainable TEST_SEASONS returns only strictly-earlier TEST_SEASONS members"
        status: pass
      - kind: integration
        ref: "python -m optimize.rl_train --test-season 2025-26 --seed 0 --timesteps 2000 --max-minutes 2 -- produced rl_policy_2025-26_0.zip + sidecar json, capped at 2.06 elapsed minutes"
        status: pass
      - kind: other
        ref: "sidecar json contains seed/timesteps/elapsed_minutes/capped/hyperparameters/train_seasons; train_seasons excludes 2025-26; elapsed_minutes <= 3"
        status: pass
      - kind: other
        ref: "ruff check . -- all checks passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-02 gate spent and applied: 15 policies trained (5 seasons x 3 seeds) at the 30-minute cap, adoption runs measured against a freshly re-measured 5-season chips_v2 figure, verdict recorded in IMPROVEMENTS.md with no pending cell"
    verification:
      - kind: other
        ref: "3 adoption runs (wf_rl_adopt_seed{0,1,2}.json), each 5 seasons x 5 replicas, scheduler=rl, chips_v2=false -- model+chips 1847/2069/2144, mean 2020, spread 297"
        status: pass
      - kind: other
        ref: "wf_chips_v2_5season.json model+chips=2192 (5-season basis) vs rl seed-mean 2020 -- config.EXPERIMENTS['rl_strategy'] confirmed False, consistent with the regression"
        status: pass
      - kind: other
        ref: "IMPROVEMENTS.md rl_strategy row has no 'pending' cell; Phase F records the declared time-box, actual spend, seed spread, isolated-chip comparison, and the training-vs-held-out curve reading (no Pitfall-4 divergence observed)"
        status: pass
      - kind: unit
        ref: "python -m pytest -q -- 210 passed, 1 skipped; ruff check . green"
        status: pass
    human_judgment: false

duration: 3h 30min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 7: RL-for-Strategy Time-Box -- Trained, Measured, Rejected Against the Solver-Scored Scheduler Summary

**Built a three-way v1/v2/rl chip-scheduler toggle, trained 15 MaskablePPO policies (5 trainable seasons x 3 seeds) inside a declared 30-minute-per-policy wall-clock cap, and REJECTED the RL layer per D-02: seed-mean model+chips (2020) loses to plan 09-04's solver-scored scheduler (2192, re-measured on the same 5-season basis) by -172/season, with 2020-21 permanently excluded from the experiment because its earliest-season data has no usable prior-season squad pool.**

## Performance

- **Duration:** 3h 30min (dominated by ~3 hours of real RL training wall-clock, run in the background with periodic polling)
- **Started:** 2026-09-08T14:52:00Z (approx.)
- **Completed:** 2026-09-08T18:20:43Z
- **Tasks:** 3
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- **Task 1 -- Three-way scheduler toggle.** `backtest/season.py::run_season` now accepts `scheduler="v1"|"v2"|"rl"`, raising `ValueError` naming all three otherwise. The `"rl"` path replays a trained policy gameweek-by-gameweek, deciding BOTH the chip and the transfer count (unlike v1/v2, which only decide chip timing) -- decoded via `optimize/rl_env.py`'s newly-factored `build_observation()`/`build_action_mask()`/`decide_action()` helpers, which are also now used by `FplStrategyEnv` itself so training and replay see byte-identical state. `backtest/walk_forward.py::resolve_scheduler()` maps `rl_strategy`/`chips_v2` flags to exactly one scheduler and hard-exits (`SystemExit`) if both are requested together, since D-02 requires RL to beat chips_v2 on its own, not stacked on it. `config.RL_SEEDS`/`RL_POLICY_DIR` added (the latter inside the already-gitignored `models/artifacts/`). Confirmed the unflagged v1 path is byte-identical before and after this change (`git stash` comparison on the same data).
- **Task 2 -- MaskablePPO trainer.** `optimize/rl_train.py` (`python -m optimize.rl_train --test-season --seed --timesteps --max-minutes --out`): hyperparameters pinned in an `ALL_CAPS` module dict (D-16); `train_seasons_for(T)` enforces the train-before-evaluate split; `MultiSeasonEnv` wraps multiple per-season `FplStrategyEnv` instances behind one action/observation space, picking a training season uniformly at random each reset; `_TimeBoxCallback` enforces the declared wall-clock cap (verified: a 2-minute-capped run stopped at 2.06 elapsed minutes) and prints the training-reward-vs-held-out-score pair each rollout, the anti-Pitfall-4 diagnostic. Per-season leakage-safe predictions are cached on disk so the planned 15-run sweep never redundantly retrains the same per-season LightGBM model.
- **Task 3 -- Spent the box, ran the gate, recorded the verdict.** Declared the time-box in `IMPROVEMENTS.md` before training started (committed separately). Discovered mid-execution that `features.parquet`'s `team` column is 100% null for 2016-17..2019-20 and 0% null from 2020-21 onward -- exactly why `TEST_SEASONS` has always started at 2020-21 -- meaning 2020-21 itself has no earlier `TEST_SEASONS` member to train a policy on. Trained **15 policies** (5 trainable seasons x 3 seeds, not the plan's literal 18) as 3 parallel per-seed background runs (~2.5 real-clock hours); every one hit the 30-minute cap. Ran the D-02 gate: 3 adoption-deciding harness runs (5 seasons x 5 replicas each, `scheduler=rl`) measured `model+chips` **1847 / 2069 / 2144** (seed-mean **2020**, spread 297) against a freshly re-measured 5-season `chips_v2` figure of **2192** -- every individual seed, not just the mean, falls short. **Verdict: REJECTED.** `config.EXPERIMENTS['rl_strategy']` stays `False`; no additional seeds or extended budget were spent per D-16's stop rule.

## Task Commits

Each task was committed atomically:

1. **Task 1: Three-way v1/v2/rl scheduler toggle on the harness** - `1ec8cb8` (feat)
2. **Task 2: MaskablePPO trainer with fixed seeds, pinned config, wall-clock cap** - `819bcaa` (feat)
3. **Task 3a: Declare the time-box before training** - `6e2a95f` (docs)
4. **Task 3b: Spend the box, run the D-02 gate, record the verdict** - `c407053` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `backtest/season.py` - `run_season(scheduler="v1"|"v2"|"rl", rl_seed=)`; `_half_of()` helper; per-gameweek RL decision + chip-used bookkeeping
- `backtest/walk_forward.py` - `resolve_scheduler()`, `--rl-seed` CLI flag, `scheduler`/`rl_seed` echoed in the `[wf]` line and tagged JSON
- `config.py` - `RL_SEEDS`, `RL_POLICY_DIR` (gitignored `models/artifacts/`)
- `optimize/rl_env.py` - `build_observation()`, `build_action_mask()`, `load_policy()`, `decide_action()`; `FplStrategyEnv._observe`/`action_masks` refactored to call the shared builders
- `optimize/rl_train.py` (new) - `train_seasons_for()`, `MultiSeasonEnv`, `HYPERPARAMS`, `_TimeBoxCallback`, `main()`
- `tests/test_experiments.py` - bogus-scheduler `ValueError`, `resolve_scheduler` flag-combination mapping, rl+chips_v2 conflict `SystemExit`
- `IMPROVEMENTS.md` - Phase F `rl_strategy` row + full results subsection (time-box, spend, per-seed/mean model+chips, isolated-chip table, curve reading, verdict)

## Decisions Made

- **2020-21 permanently excluded from the RL experiment.** `features.parquet`'s `team` column is 100% null for 2016-17 through 2019-20 and 0% null from 2020-21 onward (verified empirically this session) -- the same reason `backtest.walk_forward.TEST_SEASONS` has always started at 2020-21 rather than `DATA_SEASONS`' 2016-17 floor. `train_seasons_for(T)` therefore only accepts `TEST_SEASONS` members strictly before T, which is empty for T=2020-21 itself. The D-02 comparison consequently runs over the 5 seasons that DO have a usable prior season (2021-22 through 2025-26) -- 15 policies (5 seasons x 3 seeds), not the plan's literal 18 -- and both `rl_strategy` and `chips_v2` were freshly re-measured on that same 5-season basis so the comparison stays apples-to-apples rather than comparing a 5-season RL number against the previously-recorded 6-season `chips_v2` figure (2214, which includes 2020-21).
- **Killed and re-ran the 5-season comparison baselines sequentially.** Running `chips_v2_5season`/`baseline_5season` walk-forward comparison runs concurrently with the 3 parallel RL training processes drove the machine to a load average of ~59 on 28 cores; both comparison runs stalled for over an hour without completing even the first season. Killed them and re-ran sequentially after RL training finished -- each completed normally within a few minutes, and RL training itself sped back up once the contention was removed.
- **rl_strategy REJECTED per D-07/D-16's mechanical rule.** Seed-mean `model+chips` (2020) falls short of the `chips_v2` comparison figure (2192) on every individual seed (1847/2069/2144), not just the mean. `config.EXPERIMENTS['rl_strategy']` stays `False`; the training-vs-held-out curves showed no Pitfall-4 divergence (both stayed flat/noisy) -- the honest reading is that ~5,000-14,000 timesteps over 2-4 training seasons is not enough experience for the masked chip/transfer-count policy to beat a deterministic heuristic, not that the reward signal was dishonest.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `train_seasons_for()`'s literal `DATA_SEASONS[:idx]` slice cannot produce usable training environments**
- **Found during:** Task 2's own verify (a short capped training run crashed with `RuntimeError: solver status: Infeasible` when building a squad pool for 2018-19/2019-20)
- **Issue:** The plan's own action text specifies `train_seasons_for(T)` should return `DATA_SEASONS[:DATA_SEASONS.index(T)]`, but `features.parquet`'s `team` column is 100% null for 2016-17 through 2019-20 -- `build_gw_pool`'s `groupby(["player_code","name","team","position"])` silently drops every row when `team` is entirely NaN (pandas' default `dropna=True`), producing an empty pool and an infeasible ILP.
- **Fix:** Redefined `train_seasons_for(T)` to return only `TEST_SEASONS` members strictly before T (the only seasons with a populated `team` column and a real `_preds_for`-produced predictions frame), raising `ValueError` when that set is empty -- true for 2020-21 itself. Documented as a permanent, structural constraint (not a workaround) in the module docstring and `IMPROVEMENTS.md`.
- **Files modified:** `optimize/rl_train.py`
- **Verification:** `train_seasons_for('2020-21')` and `train_seasons_for('2016-17')` both raise; the 5 remaining test seasons return only strictly-earlier `TEST_SEASONS` members; a real capped training run for each of the 5 seasons completed without an infeasible-squad crash.
- **Committed in:** `819bcaa` (Task 2 commit)

**2. [Rule 3 - Blocking] `_preds_for` retraining is too expensive to run 15+ times without caching**
- **Found during:** Task 2 design, before the first real training run
- **Issue:** Each `optimize.rl_train` invocation needs per-season leakage-safe predictions (`backtest.walk_forward._preds_for`, a full LightGBM retrain) for every training season in its `MultiSeasonEnv`; with 5 seeds/seasons combinations sharing overlapping training-season sets, redundant retraining would have meant 50+ retrains instead of 5.
- **Fix:** Added an on-disk cache (`data/processed/experiments/rl_train_preds/<season>.parquet`) computed once per season and reused across every seed/test-season invocation that needs it.
- **Files modified:** `optimize/rl_train.py`
- **Verification:** All 15 real training runs completed using the shared cache; only 5 distinct `_preds_for` retrains occurred total (verified by cache file count).
- **Committed in:** `819bcaa` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 -- blocking issues necessary for the trainer to run at all against real data)
**Impact on plan:** Both fixes were necessary for Task 2/3 to function; the first also permanently shrinks the RL experiment's season coverage from 6 to 5 seasons, documented as a Decision Made and reflected honestly in the D-02 comparison (chips_v2 re-measured on the matching 5-season basis, not compared against its stale 6-season figure). No scope creep -- the RL layer's D-02 hybrid-split premise (ILP still does player selection) and D-16's fixed-seed/pinned-config requirements are unaffected.

## Issues Encountered

- Running the 5-season `chips_v2`/v1-baseline comparison walk-forward jobs concurrently with the 3 parallel RL training processes oversubscribed the 28-core machine (load average ~59) badly enough that both comparison jobs stalled for over an hour without completing a single season's output. Resolved by killing them and re-running sequentially after RL training finished; no data was lost since neither had written a result file yet.
- The plan's own Task 1 acceptance criterion ("reproduces the 2025-26 total of 2172") is now stale: a new gameweek (GW4) landed in `test_predictions.parquet` since the plan was authored (visible as an untracked `web/data/history/gw4.json` at session start), shifting the frozen 2025-26 total to 2237. Confirmed via `git stash` that this number is identical on the pre- and post-Task-1 code -- an environmental data-drift artifact of the season progressing in real time, not a regression introduced by this plan.

## User Setup Required

None - no external service configuration required. All RL training ran in the developer's own `python314` conda environment per D-09; policies and their sidecars live under gitignored `models/artifacts/`.

## Next Phase Readiness

- Experiment 5 (RL-for-strategy) is fully closed: measured under its declared time-box (adapted honestly to 5 trainable seasons rather than 6, with the reason documented), decided REJECTED with numbers on every seed.
- `predict/live.py`, `predict/export.py`, `api/`, and `web/` remain untouched across all four commits in this plan (verified via `git diff --name-only`) -- the weekly product surface is unaffected, and it stays torch-free (the RL dependency stack is only ever imported behind the deferred, opt-in `scheduler="rl"` code path).
- The v1 and v2 schedulers are unchanged (byte-identical v1 output confirmed via `git stash` comparison; chips_v2's own rejected verdict from plan 09-04 is untouched).
- Plan 09-10 (results table finalization) has the `rl_strategy` row ready with no `pending` cell remaining -- this closes D-01's full six-experiment sequence.
- No blockers.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (optimize/rl_train.py, optimize/rl_env.py, backtest/season.py, backtest/walk_forward.py, config.py) exist on disk; all four commits (1ec8cb8, 819bcaa, 6e2a95f, c407053) found in `git log`; full pytest suite (210 passed, 1 skipped) and `ruff check .` both green after the final commit; `config.EXPERIMENTS['rl_strategy']` confirmed `False`; `predict/`, `api/`, `web/` confirmed untouched via `git diff --name-only` across all four commits; 15 trained policies + sidecars and 4 adoption/comparison JSON artifacts (`wf_rl_adopt_seed{0,1,2}.json`, `wf_chips_v2_5season.json`) all present with the expected `replicas`/`seasons`/`scheduler`/`model+chips` shape.
