---
phase: quick-260909-5vx
plan: 01
subsystem: models
tags: [lightgbm, backtest, understat, fotmob, statistics, spearman, bootstrap]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: apply_experiment_feature_gating, _preds_for, config.EXPERIMENTS, the pooled understat/fotmob MAE comparison this plan re-slices
provides:
  - backtest/enrichment_slices.py — cached, position/coverage-sliced re-measurement of understat and fotmob xp_med accuracy, with paired 95% intervals
  - IMPROVEMENTS.md addendum recording a genuine null result (0/50 cells reach signal) plus a sharper coverage-premise correction
affects: [phase-10-xp-experiment-follow-ups]

actuals:
  tokens: 6700
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Paired-delta statistical testing for A/B feature experiments: normal interval on per-row abs-error difference for MAE, resample bootstrap on row indices for Spearman, signal requires BOTH interval bounds to clear zero"
    - "Two coverage definitions (raw per-match join vs. rolled-cumulative-feature presence) for any shift(1)-then-rolled enrichment source, since they can disagree in either direction"

key-files:
  created:
    - backtest/enrichment_slices.py
  modified:
    - tests/test_experiments.py
    - IMPROVEMENTS.md

key-decisions:
  - "Bound the training subprocess's CPU affinity with `taskset -c 0-17` (external invocation, no code change) after LightGBM's n_jobs=-1 default oversubscribed the 28-core box against the 3 running optimize.rl_train processes, driving load average to 31 and one season's training past 60 minutes; killing the stuck (non-RL) process and relaunching bound to 18 cores dropped it to ~13-20s/config."
  - "Reported an additional, sharper coverage-premise correction beyond what the plan anticipated: raw per-match join coverage measured over the WHOLE player_gw table (~41%/~40%) is diluted by non-playing bench rows that structurally cannot have Understat/FotMob data; restricted to the played-only rows this measurement (and 09-08's own MAE comparison) actually scores, raw join coverage is 96.2%/94.9% -- higher than the already-corrected 89.2%/88.1% rolled-feature figure."

requirements-completed: [TODO-2026-09-09-per-position-enrichment-remeasure]

coverage:
  - id: D1
    description: "backtest/enrichment_slices.py: cached, leakage-safe, position x coverage sliced re-measurement module reusing apply_experiment_feature_gating/_preds_for"
    requirement: "TODO-2026-09-09-per-position-enrichment-remeasure"
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_cell_stats_identical_predictions_zero_delta"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_cell_stats_detects_strictly_better_on_column"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_cell_stats_strictly_worse_on_column_never_signals"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_cell_stats_small_n_guard"
        status: pass
      - kind: integration
        ref: "python -m backtest.enrichment_slices (full 6-season run, n=66,665 in both pooled ALL/all cells)"
        status: pass
    human_judgment: false
  - id: D2
    description: "IMPROVEMENTS.md Phase F addendum recording the honest per-position/coverage verdict, the reproduction check, and the multiple-comparison caveat"
    requirement: "TODO-2026-09-09-per-position-enrichment-remeasure"
    verification:
      - kind: other
        ref: "grep + structural assertion script confirming the addendum sits above '## Reference findings', carries every required token, and >20 table pipes"
        status: pass
      - kind: unit
        ref: "python -m pytest -q (221 passed, 1 skipped)"
        status: pass
    human_judgment: false

duration: 2h 27min
completed: 2026-09-09
status: complete
---

# Quick Task 260909-5vx: Per-Position/Covered-Row Re-Measurement of Understat & FotMob Summary

**Built a cached, paired-interval re-measurement module and found a genuine null result: zero of 50 position x coverage cells show a real accuracy gain for either enrichment source, with the pooled understat numbers reproducing 09-08's published figures exactly.**

## Performance

- **Duration:** 2h 27min (wall clock; most of it was CPU-contention wait against 3 concurrent `optimize.rl_train` processes, not active work — see Deviations)
- **Started:** 2026-09-09T04:21:00-04:00
- **Completed:** 2026-09-09T06:53:27-04:00
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `backtest/enrichment_slices.py`: a measurement-only module that reuses `apply_experiment_feature_gating`/`_preds_for` from `backtest.walk_forward` (never reimplements gating or training), caches per-(config, season) predictions on disk so a re-slice never retrains, and computes a paired 95% interval on every MAE/Spearman delta between an enrichment-on and enrichment-off config — a normal interval on the per-row absolute-error difference for MAE, a 200-resample paired bootstrap for Spearman.
- Full 6-season run (2020-21..2025-26) produced the complete 50-cell grid (2 sources x 5 position slices x 5 coverage slices), with both pooled `ALL`/`all` cells landing on `n=66,665` — identical to 09-08's original row set — and the pooled understat numbers reproducing 09-08's published MAE (1.8751/1.8761) and Spearman (0.3620/0.3599) with **zero** absolute difference.
- The honest verdict: **no cell reaches signal** (`d_mae_hi < 0.0 AND d_spearman_lo > 0.0`) for either understat or fotmob, at any position or coverage slice. This is below the ~2-3 cells the multiple-comparison caveat would expect to reach "signal" by chance alone across 50 tests at 95% — a stronger null than a single non-significant test would be.
- Discovered and documented a sharper coverage-premise correction than the plan anticipated: 09-08's ~41%/~40% raw-join coverage figure is diluted by non-playing bench rows (Understat/FotMob structurally can't have data for a player who didn't feature); restricted to played-only rows, raw join coverage is actually 96.2%/94.9% — higher than the rolled-feature coverage (89.2%/88.1%). Both figures, and the per-position breakdown, are recorded in the IMPROVEMENTS.md addendum.
- IMPROVEMENTS.md Phase F addendum records all of the above inline (the JSON artifact is gitignored), including the pre-declared signal rule, both results tables, the multiple-comparison caveat, and a tie-back to the phase's own recorded open weakness (no pre-registered statistical test for REJECTED verdicts).

## Task Commits

Each task was committed atomically (TDD RED-then-GREEN for Task 1, per the tracer task's own instructions):

1. **Task 1 (RED): failing `cell_stats` tests** - `6d12c8a` (test) — module temporarily moved aside, confirmed `ModuleNotFoundError` on the four new `test_cell_stats_*` tests, committed.
2. **Task 1 (GREEN): `backtest/enrichment_slices.py` implementation** - `0f7afdb` (feat) — module restored, all four tests pass, verified end-to-end on 2025-26 alone (50 populated cells, three prediction caches, ruff clean).
3. **Task 2: full 6-season run** - no separate commit (writes only to gitignored `data/processed/experiments/`, per plan's own `files_modified` scope; results folded into Task 3's addendum).
4. **Task 3: IMPROVEMENTS.md addendum** - `41b08fb` (docs).

No separate plan-metadata commit — quick-task protocol excludes docs artifacts (SUMMARY.md, STATE.md) from the executor's own commits; the orchestrator handles that afterward.

## Files Created/Modified

- `backtest/enrichment_slices.py` - New module: `CONFIGS`/`POSITION_SLICES`/`COVERAGE_SLICES` constants, `preds_path`/`build_preds` (disk-cached predictions), `coverage_flags` (raw-join vs. rolled-feature-present flags), `cell_stats` (paired MAE/Spearman delta with 95% intervals and a small-n guard), `slice_all` (the 50-cell grid + reproduction check), and a `main()` CLI with `--seasons`/`--force`/`--bootstrap`/`--out-name` (path-escape-guarded per T-Q10-01).
- `tests/test_experiments.py` - Added four `test_cell_stats_*` unit tests (zero-delta, detected signal, never-signal-on-worse-column, small-n guard) plus the `cell_stats` import.
- `IMPROVEMENTS.md` - New `### Addendum (2026-09-09)` section under Phase F, above `## Reference findings`, with the corrected coverage premise, method, reproduction check, per-position results tables for both coverage definitions, the null verdict, the multiple-comparison caveat, and a closing tie-back to the phase's own recorded statistical-rigor gap.

## Decisions Made

- **CPU affinity fix (Rule 3 — blocking issue, environment):** The plan's measured_facts assumed ample CPU headroom for a CPU-only LightGBM run alongside 3 `optimize.rl_train` processes (load average ~3.1 at planning time). In practice, `models/train.py`'s `LGBMClassifier`/`LGBMRegressor` are constructed with `n_jobs=-1` (grab every core), which is out of this plan's file scope to change. Running the smoke test unbound drove the box to load average 31 on 28 cores and one season's training past 60 minutes (vs. the plan's ~40s estimate). Fixed by launching the training subprocess under `taskset -c 0-17` (an external invocation choice, zero code change, and never touches the three protected `optimize.rl_train` PIDs) — throughput recovered to ~13-20s/config immediately. Applied to the smoke run, the full 6-season run, and the final `pytest -q` run.
- **Killed and restarted the smoke-test process once:** The first (unbound) smoke-test invocation (PID 467300, not one of the three protected RL PIDs) was killed after confirming it was severely oversubscribed rather than making forward progress at a usable rate, then relaunched bound via `taskset`. No RL training process was touched at any point.
- **Extra coverage-premise finding surfaced in the addendum** (see Accomplishments): raw per-match join coverage on played-only rows is 96.2%/94.9%, not the ~41%/~40% whole-table figure — included alongside the plan's required rolled-feature correction (89.2%/88.1%) since both are true and together give the more complete picture the addendum's own "stated plainly" instruction calls for.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CPU affinity binding for the training subprocess**
- **Found during:** Task 1 (end-to-end smoke run on 2025-26)
- **Issue:** LightGBM's `n_jobs=-1` default (set in `models/train.py`, out of this plan's scope to change) tried to claim all 28 cores, oversubscribing the box against the 3 running `optimize.rl_train` processes and driving one season's training past 60 minutes instead of the plan's ~40s estimate.
- **Fix:** Launched the module under `taskset -c 0-17`, an external process-invocation choice with zero code change. No RL process was killed or modified; only the plan's own (non-protected) training subprocess was affected.
- **Files modified:** None (invocation-only change; no files touched).
- **Verification:** Load average dropped from 31 back toward normal within seconds of relaunch; per-(config, season) build time fell to ~13-20s; the full 6-season run (15 remaining trainings) completed in well under the bounded wait window.
- **Committed in:** N/A (no code change to commit; documented here per the deviation rule's audit-trail requirement).

---

**Total deviations:** 1 auto-fixed (1 blocking/environment).
**Impact on plan:** No production, test, or documentation content changed as a result — only how the CPU-bound training subprocess was invoked during execution. All of Task 1/2/3's actual deliverables and verify commands ran and passed exactly as specified in the plan.

## Issues Encountered

- Two background-task wait-loops (used to poll the detached training process without active polling) were killed by the harness's own background-task time limits before the underlying `nohup`+`disown`ed training process finished. This did not affect the training process itself (it survived independently), only required re-issuing a fresh bounded wait. No data loss or corrupted state resulted.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `understat` and `fotmob` leads from Phase 9/10's todo backlog are now closed with a pre-registered, interval-based null result — no per-position flag variant is motivated by this data. `config.EXPERIMENTS['understat']` and `config.EXPERIMENTS['fotmob']` both correctly remain `False`.
- `backtest/enrichment_slices.py` is a reusable, tested tool: any future enrichment source (e.g. a resolved FBref access path) can reuse `cell_stats`/`coverage_flags`/`slice_all` directly rather than writing a fourth ad-hoc slicing script.
- No blockers for Phase 10's remaining follow-up todos (ep_next features, manual FBref snapshot, high-replica capt_ceiling, RL reward-shaping notes) — none of them depend on this plan's output.

---
*Phase: quick-260909-5vx*
*Completed: 2026-09-09*

## Self-Check: PASSED

- FOUND: backtest/enrichment_slices.py
- FOUND: tests/test_experiments.py
- FOUND: IMPROVEMENTS.md
- FOUND: .planning/quick/260909-5vx-re-measure-understat-fotmob-accuracy-per/260909-5vx-SUMMARY.md
- FOUND commit: 6d12c8a (test)
- FOUND commit: 0f7afdb (feat)
- FOUND commit: 41b08fb (docs)
