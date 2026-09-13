---
phase: quick-260909-dga
plan: 01
subsystem: models
tags: [backtest, captaincy, statistics, bootstrap, lightgbm, pandas, scipy]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: capt_ceiling experiment (plan 09-03), walk-forward harness (backtest/walk_forward.py, backtest/season.py)
provides:
  - backtest/capt_ceiling_ci.py — cached, paired-interval measurement module for the capt_ceiling adoption comparison
  - Season-clustered and gameweek-bootstrap 95% CIs on capt_capture/capt_mean/model+chips
  - Empirical replica-invariance demonstration (25 replicas vs 5, both arms)
  - IMPROVEMENTS.md Phase F addendum recording REJECTION CONFIRMED on a stated statistical test
affects: [10-xp-experiment-follow-ups]

actuals:
  tokens: 7232
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Cached per-season shared-frame measurement module (backtest/*_ci.py, *_slices.py family): build the leakage-safe frame once, run multiple cheap arms off it, cache to config.EXPERIMENTS_DIR as parquet"
    - "Paired interval reporting with two labelled resampling-unit families (season-clustered governs, gameweek-bootstrap is optimistic context) so a verdict is never quoted without its unit"

key-files:
  created:
    - backtest/capt_ceiling_ci.py
  modified:
    - tests/test_experiments.py
    - IMPROVEMENTS.md
    - .planning/todos/completed/2026-09-09-capt-ceiling-high-replica-rerun.md (moved from pending)

key-decisions:
  - "Did not run the originating todo's proposed 25-replica x 6-season x 2-arm re-run in full -- ran it on ONE season only, since --replicas provably cannot move capt_capture/capt_mean/model+chips (F1), and the single-season run is sufficient to demonstrate that mechanism empirically."
  - "Season-clustered paired t-interval (n=6, df=5) governs the verdict; the gameweek-level paired cluster bootstrap (n=227) is reported as optimistic context only, since gameweeks within a season are not independent (squad state carries via transfers)."
  - "REJECTION CONFIRMED: capt_capture's 95% CI [-0.0131, +0.0423] straddles zero, and capt_mean (the captaincy arm's own season points) is negative in the mean (-11.2/season) -- config.EXPERIMENTS['capt_ceiling'] and ['capt_mc'] stay False."

requirements-completed: [TODO-2026-09-09-capt-ceiling-high-replica-rerun]

coverage:
  - id: D1
    description: "backtest/capt_ceiling_ci.py: cached shared-frame module reusing walk_forward's own _preds_for/apply_experiment_feature_gating, four run_season arms per season, two paired interval families"
    requirement: TODO-2026-09-09-capt-ceiling-high-replica-rerun
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_capture_ratio_is_ratio_of_sums_not_mean_of_ratios"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_capture_ratio_zero_denominator_guard"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_paired_t_interval_reproduces_f3_capt_capture"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_paired_t_interval_reproduces_f3_model_chips"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_paired_cluster_bootstrap_degenerate_sum_metric_collapses_to_point"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_paired_cluster_bootstrap_degenerate_ratio_metric_collapses_to_point"
        status: pass
      - kind: integration
        ref: "python -m backtest.capt_ceiling_ci --seasons 2025-26 (reproduces wf_baseline_phase9.csv/wf_capt_ceiling_adopt.csv 2025-26 row exactly)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full six-season measurement (data/processed/experiments/capt_ceiling_ci.json) with both interval families populated for all three metrics"
    requirement: TODO-2026-09-09-capt-ceiling-high-replica-rerun
    verification:
      - kind: other
        ref: "python -c \"...len(ps)>=5...\" against capt_ceiling_ci.json (6/6 seasons succeeded, zero failed_seasons)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Empirical replica-invariance demonstration: 25-replica vs 5-replica runs of the unmodified walk_forward harness for both arms"
    requirement: TODO-2026-09-09-capt-ceiling-high-replica-rerun
    verification:
      - kind: other
        ref: "pandas comparison of wf_base_r25.csv/wf_capt_r25.csv against wf_baseline_phase9.csv/wf_capt_ceiling_adopt.csv 2025-26 rows (model+chips/capt_mean/capt_capture identical; model_mean/model_std differ)"
        status: pass
    human_judgment: false
  - id: D4
    description: "IMPROVEMENTS.md Phase F addendum recording the verdict, with inlined tables so it is checkable without the gitignored JSON"
    requirement: TODO-2026-09-09-capt-ceiling-high-replica-rerun
    verification: []
    human_judgment: true
    rationale: "Prose/table quality and completeness against the plan's six required content points is a judgment call best confirmed by a human read, though every number in it is itself individually verifiable via the JSON/CSV commands above."
  - id: D5
    description: "config.py byte-unchanged and both captaincy flags pinned off by a regression test; no product surface (predict/api/web/features/data) touched"
    requirement: TODO-2026-09-09-capt-ceiling-high-replica-rerun
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_capt_ceiling_and_capt_mc_flags_stay_off"
        status: pass
      - kind: other
        ref: "git diff --quiet -- config.py && git diff --name-only -- predict api web features data (both empty)"
        status: pass
    human_judgment: false

duration: 27min
completed: 2026-09-09
status: complete
---

# Phase quick-260909-dga: High-Replica capt_ceiling Adoption Re-Measurement Summary

**Paired season-clustered and gameweek-bootstrap 95% CIs settle capt_ceiling's +1.5pt capture reading as measurement noise, and empirically prove `--replicas` was never the axis that could answer it.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-09-09T13:59:25Z
- **Completed:** 2026-09-09T14:26:00Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified/moved)

## Accomplishments

- Built `backtest/capt_ceiling_ci.py`, a cached, reusable measurement module: one shared leakage-safe frame per season (reusing `backtest.walk_forward`'s own `_preds_for`/`apply_experiment_feature_gating`, never a fork of the prediction path), four `run_season` arms mirroring `walk_forward.py:298-308` exactly, and two labelled interval families (season-clustered paired t-interval, which governs; gameweek-level paired cluster bootstrap, reported as optimistic context).
- Reproduced plan 09-03's published per-season CSV rows exactly before trusting any new number — 2025-26 off/on values matched `wf_baseline_phase9.csv`/`wf_capt_ceiling_adopt.csv` to the CSV's own rounding (capt_capture 0.595/0.619, model+chips 2172/2293 exact).
- Ran the full six-season measurement: `capt_capture` mean delta +0.0146, 95% CI [−0.0131, +0.0423] (straddles zero); `capt_mean` mean delta **−11.2** (negative — the captaincy arm's own season points went down on average); `model+chips` mean delta +15.5, CI [−48.2, +79.2].
- Executed the empirical replica-invariance demonstration the todo's own proposed method depended on being wrong about: re-ran both arms at 25 replicas (unmodified harness) and confirmed `model+chips`/`capt_mean`/`capt_capture` are byte-identical to the 5-replica results while `model_mean`/`model_std` move — proving `--replicas` cannot move any metric `capt_ceiling` is capable of affecting, exactly as F1 predicted from reading the code.
- Recorded a Phase F addendum in IMPROVEMENTS.md: REJECTION CONFIRMED on a stated statistical test (season-clustered CI straddles zero, `capt_mean` negative), replacing plan 09-03's eyeballed-SE≈16 verdict. `config.EXPERIMENTS['capt_ceiling']`/`['capt_mc']` stay False under every branch; `capt_mc` (`models/simulate.py`, still unbuilt) stays ungated.

## Task Commits

Each task was committed atomically (Task 1 followed TDD RED→GREEN):

1. **Task 1 RED: failing tests for capt_ceiling_ci helpers** - `dab0f7a` (test)
2. **Task 1 GREEN: implement capt_ceiling_ci.py** - `7691643` (feat)
3. **Task 2: full six-season run + 25-replica demonstration** - no code commit (data-only artifacts under gitignored `data/processed/experiments/`)
4. **Task 3: IMPROVEMENTS.md addendum + todo close** - `c61e2ab` (docs, todo rename) + `4eeabcd` (docs, addendum content + regression test — a stale pathspec in `c61e2ab`'s `git add` left these two files unstaged; corrected in the immediate follow-up commit)

**Plan metadata:** SUMMARY commit handled by the orchestrator (per this executor's constraints, docs artifacts are not committed here).

## Files Created/Modified

- `backtest/capt_ceiling_ci.py` - Cached paired-interval measurement module (capture_ratio, paired_t_interval, paired_cluster_bootstrap, build_shared_frame, measure_season, measure_all, CLI)
- `tests/test_experiments.py` - 6 new RED-first unit tests for the module's pure-function helpers + 1 regression test pinning `capt_ceiling`/`capt_mc` off
- `IMPROVEMENTS.md` - New "Addendum (2026-09-09): capt_ceiling paired intervals" section under Phase F, extending plan 09-03
- `.planning/todos/completed/2026-09-09-capt-ceiling-high-replica-rerun.md` - Moved from `pending/` (this plan resolves it)
- `data/processed/experiments/capt_ceiling_ci.json` (gitignored, not committed) - Full 6-season result artifact
- `data/processed/experiments/capt_ci_te_*.parquet` (gitignored, not committed) - Per-season cached shared frames
- `data/processed/experiments/wf_base_r25.csv/.json`, `wf_capt_r25.csv/.json` (gitignored, not committed) - 25-replica demonstration runs

## Decisions Made

- Ran the 25-replica demonstration on ONE season (2025-26) rather than the todo's proposed 6 seasons × 2 arms — `--replicas` provably cannot move any metric `capt_ceiling` touches (F1), so a single season fully exhibits the mechanism; spending 50-70 minutes reprinting numbers that cannot change would be the exact waste this plan exists to avoid. Stated explicitly in the addendum.
- Season-clustered interval (n=6) governs the verdict over the gameweek-level bootstrap (n=227) because gameweeks within a season are not independent (squad state carries via transfers) — the bootstrap is reported for context only, per the plan's own instruction.
- REJECTION CONFIRMED rather than presenting a bar-revision case to the user: the capt_capture CI straddles zero and `capt_mean` (season points) is negative in the mean, so the plan's "otherwise" branch applies.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed a double-prefix bug in Task 2's own literal verify command**
- **Found during:** Task 2 (25-replica demonstration comparison)
- **Issue:** The plan's verify command built the baseline CSV path as `E/f'wf_{ref}.csv'` where `ref='wf_baseline_phase9'` already carries the `wf_` prefix, producing a nonexistent `wf_wf_baseline_phase9.csv` and a `FileNotFoundError`.
- **Fix:** Corrected the ad-hoc verification command to `E/f'{ref}.csv'` (the file names on disk already carry the prefix). No implementation change — the module itself was unaffected.
- **Verification:** Corrected command ran successfully and printed the expected invariance table.
- **Committed in:** n/a (ad-hoc shell verification, not a source file)

**2. [Rule 1 - Bug] Fixed own git-staging bug that left two Task 3 files uncommitted in their first commit attempt**
- **Found during:** Task 3 (post-commit check)
- **Issue:** A `git add` invocation listed a pre-rename path (`.planning/todos/pending/...`) alongside `IMPROVEMENTS.md`/`tests/test_experiments.py`; the invalid pathspec failed the whole `git add` call, so only the already-staged todo rename made it into commit `c61e2ab`.
- **Fix:** Verified via `git show --stat HEAD` and `git status --short`, then staged and committed the two omitted files in a follow-up commit (`4eeabcd`) rather than amending `c61e2ab` (amend is disallowed by policy after a commit has landed).
- **Files modified:** IMPROVEMENTS.md, tests/test_experiments.py (already-written content; only the commit was fixed)
- **Verification:** `git show --stat HEAD` after the follow-up commit confirms both files present; full test_experiments.py suite (29 tests) re-run and passing.
- **Committed in:** 4eeabcd

**3. [Rule 3 - Blocking] Killed an unpinned pytest run that grabbed ~25 cores**
- **Found during:** Task 1 GREEN verification
- **Issue:** An early `pytest tests/test_experiments.py` invocation was launched without `taskset`, and LightGBM's default threading grabbed ~25 of 28 cores — a direct violation of the environment constraint to pin CPU-heavy runs and not starve the live `optimize.rl_train` processes.
- **Fix:** Killed the runaway pytest process immediately (confirmed all three `rl_train` PIDs survived), then re-ran every subsequent CPU-heavy command under `taskset -c 0-17`.
- **Verification:** `ps aux | grep rl_train` confirmed all three training processes alive and undisturbed throughout, before and after.
- **Committed in:** n/a (process hygiene, no file change)

---

**Total deviations:** 3 auto-fixed (1 verify-command bug, 1 self-inflicted commit-staging bug, 1 CPU-pinning correction)
**Impact on plan:** All three were caught and corrected within the same task before proceeding; no scope creep, no change to the module's actual behavior or the addendum's content.

## Issues Encountered

None beyond the three deviations above, all resolved inline.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `capt_mc` (Monte-Carlo captaincy variant, `models/simulate.py`) remains ungated and unbuilt — this plan's REJECTION CONFIRMED verdict is the same non-decision plan 09-03 already recorded, now on firmer statistical ground.
- The remaining Phase 10 follow-up todos (ep_next features, manual FBref snapshot, RL reward-shaping notes, RL v2 bigger-timestep run) are unaffected by this plan and still pending.
- The three live `optimize.rl_train` processes (seeds 0/1/2, `--test-season 2025-26 --max-minutes 120`) were left running undisturbed throughout this plan's execution.

---
*Phase: quick-260909-dga*
*Completed: 2026-09-09*

## Self-Check: PASSED

- Files verified present: `backtest/capt_ceiling_ci.py`, `tests/test_experiments.py`, `IMPROVEMENTS.md`, `.planning/todos/completed/2026-09-09-capt-ceiling-high-replica-rerun.md`; old `pending/` copy confirmed removed.
- Commits verified present in `git log`: `dab0f7a` (test), `7691643` (feat), `c61e2ab` (docs, todo rename), `4eeabcd` (docs, addendum + regression test).
- All plan `<acceptance_criteria>`/`<done>` gates re-checked: Task 1's pytest + CLI + JSON-reproduction commands pass; Task 2's `len(ps)>=5` and 25-replica invariance commands pass; Task 3's pytest, config.py-unchanged, no-product-surface, and leakage/legality commands all pass.
- `config.EXPERIMENTS['capt_ceiling']` confirmed `False`; `config.py` confirmed byte-unchanged (`git diff --quiet`); no file under `predict/`, `api/`, `web/`, `features/`, `data/` modified.
- All three `optimize.rl_train` processes (PIDs 802368/802371/802374) confirmed alive at every checkpoint during execution.
