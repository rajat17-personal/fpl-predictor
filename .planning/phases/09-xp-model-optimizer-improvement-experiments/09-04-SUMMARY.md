---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 04
subsystem: ml-experimentation
tags: [chip-scheduling, walk-forward, wildcard, hysteresis-sweep, adoption-decision]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, backtest/walk_forward.py --experiments/--seasons/--tag CLI, the tracked 6-season baseline in IMPROVEMENTS.md Phase F); plan 09-03's captaincy ceiling-EV verdict (rejected, flag off) as the current-default configuration this plan's A/B is judged against"
provides:
  - "optimize/chips.py::scored_schedule() -- xP-scored causal chip scheduler (chips_v2), preserving causal_schedule's g..g+visibility windowing shell"
  - "backtest/season.py::run_season(scheduler=, chips_hysteresis=) -- v1/v2 scheduler selection, chip application unchanged either way"
  - "backtest/season.py -- Wildcard's isolated chip_deltas measurement (same-gameweek, zero-transfer-hold baseline), the first-ever measurement of WC's isolated value"
  - "backtest/walk_forward.py --chips-hysteresis CLI override, and a chip_deltas (mean/std/count per chip) block in every tagged JSON summary"
  - "D-06/D-07 adoption verdict for chips_v2: REJECTED (model+chips -48/season regression, bb isolated value regressed outside its v1 CI), flag stays default-off, v1 scheduler stays the shipped default"
affects: [09-10]

actuals:
  tokens: 7037
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Scheduler selection via a run_season(scheduler=) keyword, never a bespoke ad-hoc switch -- mirrors the capt_col/experiment-flag seams from plans 09-01/09-03"
    - "Same-gameweek chip isolation (zero-transfer-hold or same-team with/without) extended to a fourth chip (wc) using the exact FH construction, so all four chips are directly comparable"
    - "Hysteresis sweep via a single CLI override thread (--chips-hysteresis -> config default override -> scored_schedule(hysteresis=)), same pattern as plan 09-03's --capt-lambda"

key-files:
  created: []
  modified:
    - optimize/chips.py
    - backtest/season.py
    - backtest/walk_forward.py
    - config.py
    - tests/test_chips.py
    - IMPROVEMENTS.md

key-decisions:
  - "Collapsed backtest/season.py's duplicated `if chip == 'wc'` squad-reset block into one occurrence, placed AFTER the new wc delta measurement -- the pre-existing duplication was provably redundant (nothing between the two occurrences ever read the reset squad/bank), and the wc baseline needs the PRE-reset squad, so ordering the single occurrence after the measurement is both correctness-required and behaviour-preserving (2025-26 v1 total confirmed unchanged at 2172)"
  - "chips_v2 REJECTED per D-07's mechanical rule: the adoption-deciding run (6 seasons, 5 replicas) measured model+chips 2214 vs the plan 09-01 baseline's 2262 -- a -48/season regression, not an improvement -- and bb's isolated value (8.5+-6.5, n=12) fell below its v1 CI floor (10.0-0.0=10.0). Both pre-declared conditions fail; the code stays merged behind the default-off flag (D-08) and v1 (causal_schedule) remains the shipped scheduler"
  - "Hysteresis pinned to 0 (already config's default) after sweeping {0,1,2,3} at 6 seasons/1 replica each -- 0 measured the strictly-highest 6-season-mean model+chips (2214), matching 09-RESEARCH.md's own recommendation to start at zero"

requirements-completed: []

coverage:
  - id: D1
    description: "xP-scored causal chip scheduler (scored_schedule) behind the chips_v2 flag, provably blind to realised points and to anything beyond its visibility window"
    verification:
      - kind: unit
        ref: "tests/test_chips.py#test_scored_schedule_one_chip_per_gw_and_per_half"
        status: pass
      - kind: unit
        ref: "tests/test_chips.py#test_scored_schedule_ignores_shuffled_y_points"
        status: pass
      - kind: unit
        ref: "tests/test_chips.py#test_scored_schedule_blind_to_next_half"
        status: pass
      - kind: unit
        ref: "tests/test_chips.py#test_scored_schedule_blind_beyond_visibility_window"
        status: pass
      - kind: unit
        ref: "tests/test_chips.py#test_hysteresis_huge_fires_earliest_possible_for_every_chip"
        status: pass
      - kind: unit
        ref: "tests/test_chips.py#test_causal_schedule_unchanged_regression_guard"
        status: pass
      - kind: unit
        ref: "tests/test_chips.py#test_scored_schedule_differs_from_causal_schedule"
        status: pass
      - kind: integration
        ref: "live 2025-26 comparison: v1={8:'wc',14:'tc',26:'bb',28:'wc',33:'tc',34:'fh'} vs v2={1:'fh',2:'wc',3:'bb',8:'tc',20:'fh',21:'bb',26:'wc',36:'tc'} -- different schedules, no duplicate chip within a half"
        status: pass
    human_judgment: false
  - id: D2
    description: "Wildcard's isolated chip_deltas value measured for the first time, without changing v1's realised season total"
    verification:
      - kind: unit
        ref: "tests/test_chips.py#test_wc_chip_delta_recorded_against_zero_transfer_hold"
        status: pass
      - kind: integration
        ref: "python -c: run_season(..., record_chips=True) on real 2025-26 data -- chips measured includes 'wc', season total unchanged at 2172"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2024-25,2025-26 --replicas 1 --tag wc_measure -- wf_wc_measure.json chip_deltas carries wc/fh/bb/tc each with mean/std/count"
        status: pass
    human_judgment: false
  - id: D3
    description: "Hysteresis sweep, full-replica adoption-deciding run, and the mechanical D-07 verdict applied against the pre-declared D-06 criteria"
    verification:
      - kind: integration
        ref: "python -c assertion: 4 sweep summaries (wf_chips_hys_0..3.json) each over 6 seasons; config.CHIPS_V2_HYSTERESIS in the swept set"
        status: pass
      - kind: integration
        ref: "python -c assertion: wf_chips_v2_adopt.json has replicas=5, 6 seasons, chips_v2=true, chip_deltas for all 4 chips; config.EXPERIMENTS['chips_v2'] is False, consistent with the regression found"
        status: pass
      - kind: other
        ref: "IMPROVEMENTS.md chips_v2 row: no 'pending' cell, Wildcard's first-measured value named explicitly"
        status: pass
      - kind: other
        ref: "python -m pytest -q (198 passed, 1 skipped) and ruff check . both green after all three commits"
        status: pass
    human_judgment: false

duration: 37min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 4: Chip Scheduler v2 — xP-Scored Causal Timing and Wildcard's First Measurement Summary

**Built an xP-scored causal chip scheduler (chips_v2) behind a flag, measured Wildcard's isolated value for the first time (+14.2±9.0 pts/gw), and REJECTED chips_v2 at adoption: the full-replica run measured a -48/season regression against the plan 09-01 baseline, with Bench Boost's isolated value also regressing outside its v1 confidence interval.**

## Performance

- **Duration:** 37 min
- **Started:** 2026-09-08T13:00:00Z (approx.)
- **Completed:** 2026-09-08T13:36:56Z
- **Tasks:** 3
- **Files modified:** 6 (0 created, 6 modified)

## Accomplishments

- **`optimize/chips.py::scored_schedule()`** added alongside (never replacing) `causal_schedule`/`default_schedule`. Keeps the exact `g <= w <= g + visibility` windowing shell (the B3 causal fix) and replaces the fixture-structure if/elif body with a common "fire now vs. best visible later" scoring rule: `tc` = best single captain (from `capt_col` when given, else `xp_col`); `bb` = bench of a top-15 proxy squad (ranks 12-15); `fh` = top-11 sum scaled by the share of clubs blanking; `wc` = 0.84-decayed forward sum of top-11 across the visibility window (matching `backtest/walk_forward.py::_plan_col`'s own decay). An end-of-half forcing rule fires any still-unused chip at the latest free gameweek rather than wasting it.
- **`backtest/season.py::run_season`** gained `scheduler: str = "v1"` and `chips_hysteresis: float | None = None` keywords; chip *application* is byte-identical between v1/v2, only the schedule source changes. Wired into `backtest/walk_forward.py`'s chips-recording call: `scheduler="v2" if exp["chips_v2"] else "v1"`.
- **Wildcard's isolated value measured for the first time.** Collapsed the pre-existing duplicated `if chip == "wc"` squad-reset block into one occurrence, placed AFTER a new delta measurement (wc's realised score vs a zero-transfer hold on the PRE-reset squad — the same construction FH already used). Verified behaviour-preserving: 2025-26's v1 season total stayed exactly 2172. On the `wf_wc_measure` run (2 seasons, 1 replica): **wc = +14.2±9.0 pts/gw (n=4)**.
- **`backtest/walk_forward.py`** tagged JSON summaries now carry a `chip_deltas` block (mean/std/count per chip, ddof=1-NaN guarded to 0.0 for single-observation chips) so later runs compare confidence intervals mechanically. Added `--chips-hysteresis FLOAT`, echoed in the `[wf]` line and JSON, mirroring plan 09-03's `--capt-lambda`.
- **Hysteresis swept** over {0, 1, 2, 3} at 6 seasons/1 replica each: model+chips {0: 2214, 1: 2205, 2: 2198, 3: 2169}. Hysteresis 0 won outright (no tie-break needed) and was pinned to `config.CHIPS_V2_HYSTERESIS` (already 0.0 by default) with an inline sweep-provenance comment.
- **Adoption-deciding run** (6 seasons, 5 replicas, `chips_v2` forced on, `wf_chips_v2_adopt.json`): `model+chips` **2214** vs the plan 09-01 baseline's **2262** — a **-48/season regression**. `bb`'s isolated value also regressed outside its v1 confidence interval (v1: 10.0±0.0 n=2 from `wf_wc_measure`; v2: 8.5±6.5 n=12). Both pre-declared D-06 conditions fail.
- **D-07 auto-adopt verdict: REJECTED.** `config.EXPERIMENTS['chips_v2']` stays `False`. Per D-08 all new code (`scored_schedule`, the `scheduler`/`chips_hysteresis` keywords, the `--chips-hysteresis` flag, the wc measurement) stays merged, nothing deleted. `tests/test_experiments.py`'s all-flags-default-off assertion needed no change since the default set is unchanged. `IMPROVEMENTS.md` Phase F's `chips_v2` row filled with the sweep table, the four-chip v1-vs-v2 isolated table, and Wildcard's first-measured value called out explicitly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Solver-scored causal chip scheduler behind the chips_v2 flag** - `d0cf8fe` (feat)
2. **Task 2: Measure Wildcard's isolated value for the first time** - `9e1de5c` (feat)
3. **Task 3: Hysteresis sweep, adoption-deciding run, and verdict** - `8a311db` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `optimize/chips.py` - `scored_schedule()` (xP-scored causal chip scheduler, chips_v2), `SCORED_DECAY` constant; `causal_schedule`/`default_schedule` untouched
- `backtest/season.py` - `run_season(scheduler=, chips_hysteresis=)` keywords; collapsed the duplicated `wc` squad-reset block into one, placed after the new wc/fh isolated-delta measurement
- `backtest/walk_forward.py` - `scheduler="v2" if exp["chips_v2"] else "v1"` wiring, `--chips-hysteresis` CLI option, `chip_deltas` block in the tagged JSON summary
- `config.py` - `CHIPS_V2_HYSTERESIS` inline comment updated with the sweep provenance (value unchanged at 0.0)
- `tests/test_chips.py` (new file, created in Task 1, extended in Task 2) - 8 tests: scored_schedule structural/leakage/visibility/hysteresis/regression-guard tests plus the wc isolated-delta test
- `IMPROVEMENTS.md` - Phase F `chips_v2` results row filled (non-pending), new `chips_v2` prose sub-section with the hysteresis sweep table, the four-chip v1-vs-v2 isolated table, and the adoption verdict

## Decisions Made

- Collapsed the pre-existing duplicated `if chip == 'wc'` squad-reset block into one occurrence, placed AFTER the new wc delta measurement — the duplication was provably redundant in the old code (nothing between the two occurrences ever read the reset `squad`/`bank`), and the wc baseline specifically needs the pre-reset squad, so this ordering is both correctness-required and behaviour-preserving (verified: 2025-26 v1 total unchanged at 2172).
- chips_v2 REJECTED per D-07's mechanical rule: the adoption run's `model+chips` (2214) regressed -48/season against the plan 09-01 baseline (2262), and `bb`'s isolated value fell below its v1 CI floor. The code stays merged behind the default-off flag (D-08); the heuristic v1 scheduler remains the shipped default.
- Hysteresis pinned to 0 (unchanged from config's existing default) after sweeping {0,1,2,3} — 0 measured the strictly-highest 6-season-mean `model+chips`, matching 09-RESEARCH.md's own recommendation to start at zero before considering a wider margin.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Threaded `chips_hysteresis` through `backtest/season.py::run_season`**
- **Found during:** Task 3 (adding the `--chips-hysteresis` CLI flag)
- **Issue:** Task 3's `files_modified` list names `config.py`, `backtest/walk_forward.py`, `tests/test_experiments.py`, `IMPROVEMENTS.md` — but the new CLI override has no path to `optimize.chips.scored_schedule`'s `hysteresis` parameter without a keyword on `run_season` itself (the function that calls `scored_schedule`).
- **Fix:** Added a `chips_hysteresis: float | None = None` keyword to `run_season`, passed through to `chips.scored_schedule(..., hysteresis=chips_hysteresis)` only when `scheduler == "v2"`. No behaviour change for `scheduler == "v1"` or any existing caller that omits the new keyword.
- **Files modified:** `backtest/season.py`
- **Verification:** `--chips-hysteresis 2.0 --experiments chips_v2` produced a visibly different schedule/points total (2179) than the hysteresis=0 run (2188) on the same 2025-26 smoke run; full pytest suite green.
- **Committed in:** `8a311db` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — file-list gap needed for the task's own stated CLI behaviour)
**Impact on plan:** Necessary for `--chips-hysteresis` to actually affect anything; no scope creep — the change only threads an existing parameter one level up the call stack `scored_schedule` already exposed since Task 1.

## Issues Encountered

None. `tests/test_experiments.py` needed no edit since `chips_v2`'s default stayed `False` (the flag did not flip).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Experiment 3 (chip scheduler v2) is fully closed: measured, decided REJECTED, and Wildcard has a number for the first time (+14.2±9.0 pts/gw isolated), closing D-06's "isolated WC value measured" criterion for good regardless of any future scheduler's fate.
- `predict/live.py` and `predict/export.py` remain untouched (verified via `git log --name-only` across this plan's three commits) — the weekly product surface is unaffected, matching this plan's own success criteria.
- Plan 09-10 (results table finalization) has the `chips_v2` row ready with no `pending` cells remaining.
- No blockers.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (optimize/chips.py, backtest/season.py, backtest/walk_forward.py, config.py, tests/test_chips.py, IMPROVEMENTS.md) exist on disk and carry the expected changes; all three task commits (d0cf8fe, 9e1de5c, 8a311db) found in `git log`; full pytest suite (198 passed, 1 skipped) and `ruff check .` both green after the final commit; `config.EXPERIMENTS['chips_v2']` confirmed `False` matching the measured regression verdict; `data/processed/experiments/wf_wc_measure.json`, `wf_chips_hys_{0,1,2,3}.json`, and `wf_chips_v2_adopt.json` all present with the expected `chip_deltas`/`replicas`/`seasons` shape.
