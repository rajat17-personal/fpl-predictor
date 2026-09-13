---
phase: quick-260909-elx
plan: 01
subsystem: ml-experiments
tags: [lightgbm, feature-engineering, leakage-testing, provenance, statistics]

# Dependency graph
requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: config.EXPERIMENTS registry, apply_experiment_feature_gating,
      backtest.walk_forward harness, backtest.benchmark_external module,
      the 09-02 external-benchmark reading (xp_fpl outranks our model)
provides:
  - backtest/ep_next_provenance.py — measurement-only decision-time provenance
    test for FPL's own ep_this/ep_next figure, using data/snapshots/*.parquet
    as a known-pre-deadline control
  - Two new default-off config.EXPERIMENTS flags (ep_next_lag, ep_next_now)
    and their gating branch in apply_experiment_feature_gating (the function's
    first column-ADDING branch)
  - backtest/benchmark_external.py --experiments option (closes the F7 gap
    that the benchmark never gated feature families at all)
  - IMPROVEMENTS.md Phase F addendum recording the rejection of both flags,
    the third instalment on "What this phase did not resolve"
affects: [phase-10-xp-experiment-follow-ups]

# Actuals (#2632)
actuals:
  tokens: 12750
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Decision-time provenance testing: compare a historical column's
      conditional statistic against a KNOWN-pre-deadline control (an
      independently-timestamped snapshot) rather than asserting safety from
      the data's shape alone."
    - "Feature-gating branch that ADDS a derived column (not just drops one)
      while masking outage-as-zero groups to null before deriving anything."

key-files:
  created:
    - backtest/ep_next_provenance.py
  modified:
    - config.py
    - backtest/walk_forward.py
    - backtest/benchmark_external.py
    - tests/test_leakage.py
    - tests/test_experiments.py
    - IMPROVEMENTS.md

key-decisions:
  - "ep_next_lag (strict previous-fixture xp_fpl) REJECTED: mean model+chips
    2223 vs the >=2,280 D-05 bar, and D-07 fails outright (model+chips
    regresses -39/season, multi_safe flat)."
  - "ep_next_now (same-fixture xp_fpl) REJECTED despite mechanically clearing
    D-05 (mean model+chips 3049) and D-07 (multi_safe 2905) by a wide margin
    — backtest/ep_next_provenance.py's control found the historical column's
    P(played|xp_fpl==0)=0.0229 [0.0216,0.0243] materially LOWER (more
    confident) than a known-pre-deadline capture's own 0.0815 [0.0544,0.1203],
    non-overlapping 95% CIs — consistent with hindsight contamination, not a
    genuine forward-looking figure. Per the plan's pre-declared threat
    mitigation (T-elx-01), this disqualifies the arm regardless of the
    mechanical result."
  - "Both flags stay False; no product code touched."

requirements-completed: [TODO-2026-09-09-ep-next-as-feature-minutes-signals]

coverage:
  - id: D1
    description: "Provenance verdict on whether FPL's same-fixture xp_fpl is
      decision-time-known, using a known-pre-deadline control from this
      repo's own daily-cron snapshots"
    verification:
      - kind: other
        ref: "python -m backtest.ep_next_provenance (verified against manual
          re-derivation of every statistic before trusting the module output)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two default-off ep_next_lag/ep_next_now flags added to
      config.EXPERIMENTS with a gating branch in
      apply_experiment_feature_gating that adds derived columns without
      disturbing the literal xp_fpl column or the pre-existing drop-only
      branches"
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_ep_next_flags_off_no_op,
          test_ep_next_lag_column_matches_prior_fixture_no_bleed,
          test_ep_next_now_masks_outage_but_not_mixed_gameweek,
          test_ep_next_xp_fpl_literal_survives_every_flag_combination"
        status: pass
      - kind: integration
        ref: "tests/test_leakage.py#test_ep_next_lag_gate_matches_independent_masked_shift"
        status: pass
    human_judgment: false
  - id: D3
    description: "Six-season adoption measurement for both arms with
      season-clustered paired intervals against the pre-declared D-05/D-07
      bar, reusing backtest.capt_ceiling_ci's interval helper"
    verification:
      - kind: other
        ref: "python -m backtest.walk_forward --experiments ep_next_lag
          --tag ep_next_lag / --experiments ep_next_lag,ep_next_now --tag
          ep_next_now, both 6 seasons x 5 replicas; paired_t_interval() run
          against wf_baseline_phase9.csv"
        status: pass
    human_judgment: true
    rationale: "The mechanical D-05/D-07 outcome for ep_next_now (clears
      both bars) is overridden by a provenance judgment call this task made
      explicit but that a human should be able to review — the interaction
      between a huge point estimate and a wide, zero-straddling
      season-clustered CI is exactly the kind of reading a human sanity check
      protects against."
  - id: D4
    description: "backtest/benchmark_external.py gated through
      apply_experiment_feature_gating via a new --experiments option,
      default behaviour unchanged"
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_benchmark_experiments_arg_none_preserves_ungated_default,
          test_benchmark_experiments_arg_forces_named_flags"
        status: pass
      - kind: other
        ref: "three tagged benchmark runs (ep_next_base/ep_next_lag/ep_next_now)
          diffed against each other and against the previously published
          benchmark_phase9.json numbers"
        status: pass
    human_judgment: false
  - id: D5
    description: "IMPROVEMENTS.md Phase F addendum inlining every decisive
      number so a reader can verify the verdict without the gitignored
      artifacts"
    verification: []
    human_judgment: true
    rationale: "Prose/table addendum quality and completeness against the
      plan's seven required points is a judgment call, not something a test
      asserts."

duration: 58min
completed: 2026-09-09
status: complete
---

# Quick Task 260909-elx: FPL's own ep_this/ep_next figure as a model feature — both arms rejected Summary

**Built a decision-time provenance test using this repo's own daily-cron snapshots as a known-pre-deadline control, found FPL's same-fixture expected-points figure behaves like it knows the outcome before it happens, and rejected both new experiment flags — one for genuinely not helping, the other for mechanically "winning" via leakage.**

## Performance

- **Duration:** 58 min
- **Started:** 2026-09-09T15:38:00Z (approx.)
- **Completed:** 2026-09-09T16:36:23Z
- **Tasks:** 3
- **Files modified:** 7 (1 created: `backtest/ep_next_provenance.py`)

## Accomplishments

- Corrected the originating todo's own premise: FPL's lagged expected-points rolling means (`xp_fpl_r3/r5/r10/rall`) have been live model features via `features/engineer.py`'s `ROLL_STATS` all along — "feed lagged ep_next" needed no new code.
- Built `backtest/ep_next_provenance.py`, a measurement-only module that settles whether FPL's same-fixture `ep_this`/`ep_next` value is decision-time-known, using a control this repo uniquely has: `data/snapshots/*.parquet` (the daily cron, captured at a known `ts_utc` strictly between gameweeks) joined to `data/raw/live/element_history.parquet`'s realised minutes. Verdict: **NOT exonerated** — the historical column's `P(played|xp_fpl==0)=0.0229` `[0.0216, 0.0243]` sits entirely below the control's `0.0815` `[0.0544, 0.1203]` (non-overlapping 95% Wilson intervals), consistent with hindsight contamination.
- Added two default-off `config.EXPERIMENTS` flags (`ep_next_lag`, `ep_next_now`) and `apply_experiment_feature_gating`'s first column-*adding* branch: an outage-masking rule (any (season, gw) group that is 0.0/null for every row is nulled before deriving anything) feeding a strict previous-fixture lag (`xp_fpl_lag1`) and/or the masked same-fixture value (`xp_fpl_now`), with the literal `xp_fpl` baseline column untouched under every combination.
- Measured both arms over the full 6-season harness (5 replicas) against the Phase 9 baseline (`model+chips` 2262): `ep_next_lag` regresses to 2223 (fails the >=2,280 D-05 bar outright); `ep_next_now` mechanically explodes to 3049 (clears D-05/D-07 by a wide margin) but only once the training window first includes a season with real `xp_fpl` coverage — the same mechanism the provenance test flagged, not a separate finding.
- Closed a real gap in `backtest/benchmark_external.py`: it never gated feature families at all (F7). Added an `--experiments` option (default preserves today's ungated behaviour byte-for-byte) and re-scored theFPLkiwi benchmark three ways; the same-fixture arm moves pooled Spearman 0.383→0.516 but 2022-23 alone hits 0.688 — *surpassing* `xp_fpl`'s own 0.558 for that season, the same leakage signature as the season-points result.
- Wrote the IMPROVEMENTS.md Phase F addendum (the third instalment on "What this phase did not resolve"'s external-benchmark puzzle) inlining every decisive number, since `data/processed/experiments/` is gitignored.

## Task Commits

1. **Task 1: Provenance verdict, default-off flags, and one season end to end** - `a7cdb03` (feat)
2. **Task 2: Six-season adoption measurement and the gated benchmark re-score** - `fcba981` (feat)
3. **Task 3: Record the Phase F addendum and guard the untouched flags** - `d48432e` (docs)

_Note: Task 2's per-season paired-interval computation and the six-season/benchmark harness runs were measurement steps (ad-hoc `python -c`/CLI invocations writing gitignored artifacts under `data/processed/experiments/`), not separate code commits — consistent with the plan's own `files_modified` list for that task._

## Files Created/Modified

- `backtest/ep_next_provenance.py` - Measurement-only decision-time provenance test (coverage census, historical conditional stats, known-pre-deadline control, verdict)
- `config.py` - Two new default-off `EXPERIMENTS` keys with a comment block explaining scope and the provenance conditionality of `ep_next_now`
- `backtest/walk_forward.py` - `_masked_xp_fpl`/`_prev_fixture_lag` helpers plus the new column-adding branch in `apply_experiment_feature_gating`
- `backtest/benchmark_external.py` - New `--experiments` option; `score()` accepts an optional `experiments` dict; `_resolve_gate_experiments` preserves the ungated default
- `tests/test_leakage.py` - Decision-time leakage test recomputing the lag column independently for a real player on 2023-24 (intact coverage)
- `tests/test_experiments.py` - Pure-function gating tests (no-op off, no-bleed lag, outage masking both directions, xp_fpl survival, registry keys) plus benchmark CLI resolution tests and the flags-stay-off regression guard
- `IMPROVEMENTS.md` - Phase F addendum with the full provenance verdict, adoption table, benchmark re-score, and availability-half scoping
- `.planning/todos/completed/2026-09-09-ep-next-as-feature-minutes-signals.md` - Moved out of `pending/`

## Decisions Made

- **`ep_next_lag` REJECTED**: mean `model+chips` 2223 vs the pre-declared >=2,280 D-05 bar; D-07 also fails (model+chips regresses -39/season, multi_safe flat at -0.7/season). The decision-time-safe half of the todo's ask genuinely does not help.
- **`ep_next_now` REJECTED despite mechanically clearing both bars** (`model+chips` 3049, `multi_safe` 2905): the provenance test's non-overlapping control interval disqualifies it per the plan's pre-declared T-elx-01 threat mitigation. A number this large, appearing only once the training window contains real (leakage-consistent) coverage, is the signature the threat register was written to catch, not a genuine improvement.
- Both `config.EXPERIMENTS['ep_next_lag']` and `['ep_next_now']` stay `False` under every reading; no product code (`predict/`, `api/`, `web/`, `features/`, `data/`) was touched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in the plan's own literal verify command] Task 1's `off.columns == df.columns` assertion doesn't hold against real data**
- **Found during:** Task 1 verification
- **Issue:** The plan's own `<verify>` block asserted `list(gate(df, {}).columns) == list(df.columns)` for `df = load_features()`. Against the real `features.parquet` (which already carries `ts_*`/`us_*`/`fm_*` columns per Phase 9), `apply_experiment_feature_gating`'s PRE-EXISTING team_strength/understat/fotmob branches correctly DROP those 52 columns when their own flags are off by default (`{}`'s `.get(..., False)` contract) — this is intentional, unchanged behaviour matching the shipped Phase-9 default, not something this task's new `ep_next_lag`/`ep_next_now` branch touches.
- **Fix:** Ran the actually-meaningful equivalent instead: confirmed `off` (a) adds neither derived column and (b) matches the pre-existing drop-only column set exactly (`[c for c in df.columns if not c.startswith(('ts_','us_','fm_'))]`). Confirmed with `df cols: 161 off cols: 109` and an exact match against the expected pre-existing-behaviour column list.
- **Files modified:** None (verification-only; no implementation change).
- **Verification:** See Task 1 verify transcript above; also confirmed via `on = gate(df, {all True})` adding exactly `['xp_fpl_lag1', 'xp_fpl_now']` and both reaching `feature_cols`.
- **Committed in:** a7cdb03 (implementation unaffected; this is a verify-methodology correction only)

**2. [Rule 3 - Blocking, CPU contention] Two duplicate unpinned pytest invocations spiked load to ~65 on a 28-core, oversubscribed machine**
- **Found during:** Task 1 verification
- **Issue:** Before applying the environment's `taskset -c 0-17` guidance, I launched `pytest tests/test_experiments.py tests/test_leakage.py` twice (once via a 120s-timeout auto-backgrounded call, once explicitly backgrounded) without CPU pinning. Both invocations' `needs_data`-marked tests call LightGBM with `n_jobs=-1`, and a live `backtest.walk_forward --experiments rl_strategy` process (an unrelated, concurrent quick task's run, not this plan's own process) was already using significant CPU — the combination drove load average to ~65 and both duplicate pytest runs stalled for 25+ minutes without completing.
- **Fix:** Terminated only the two duplicate self-launched pytest processes via `pkill -9 -f "pytest tests/test_experiments.py tests/test_leakage.py"` (an exact match on my own redundant command, touching nothing else), then re-ran the test suite once, pinned with `taskset -c 0-17` as the environment constraints specify. All subsequent commands in this task were run pinned.
- **Files modified:** None.
- **Verification:** Re-run completed in 15.67s (43 passed) once pinned, vs never completing unpinned under contention.
- **Committed in:** N/A (process management only, not a code change)

**3. [Rule 1 - Bug in the plan's own literal verify command] Task 3's product-surface check flags pre-existing, unrelated cron artifacts**
- **Found during:** Task 3 verification
- **Issue:** `test -z "$(git status --porcelain -- predict api web features data)"` is non-empty because of two UNTRACKED files — `data/snapshots/2026-09-07.parquet` (mtime Sep 7 02:19) and `web/data/history/gw4.json` (mtime Sep 8 22:41) — both confirmed present in the original conversation-start `git status` snapshot, i.e. daily-cron/weekly-export artifacts that predate this session by one to two days, not files this task created or modified.
- **Fix:** Verified the actual invariant the check exists to protect — no TRACKED file under `predict/`, `api/`, `web/`, `features/`, `data/` was modified, and no new file was added by this task's own work — by excluding those two known pre-existing entries and confirming zero remaining matches (`git diff --stat HEAD -- predict api web features data` is empty).
- **Files modified:** None.
- **Verification:** `git status --porcelain -- predict api web features data | grep -v` (the two known pre-existing files) returns nothing.
- **Committed in:** N/A (verification-methodology correction only)

---

**Total deviations:** 3 (2 verify-methodology corrections for plan assertions that assumed a clean tree/no pre-existing feature columns; 1 blocking CPU-contention cleanup of my own redundant processes). **Impact:** None on implementation — all three are documentation/verification corrections. No scope creep; no architectural change.

## Issues Encountered

- The environment ran a concurrent, unrelated quick task (an `rl_strategy` v2 re-run, visible as `backtest.walk_forward --experiments rl_strategy` processes and a `docs: rl_strategy v2 rejected...` commit that landed on `feat/init-code` partway through this session). This task's own commits are unaffected (linear history, no conflicts) — noted here only because it explains the CPU contention in Deviation 2 above and the extra file mentioned in Deviation 1's/3's staging area. All three `optimize.rl_train`-family processes referenced in this task's environment constraints were left untouched throughout; the concurrent `rl_strategy` process completed normally (evidenced by its own commit landing successfully), not because of anything this task did.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both `ep_next_lag` and `ep_next_now` are fully measured, documented, and rejected — closes the ep_next branch of Phase 10's follow-up todo list.
- `backtest/ep_next_provenance.py`'s control is currently n=270 from a single covered snapshot (2026-08-31, since the 2026-09-07 snapshot's gw4 has no realised minutes yet). As the daily cron accumulates more snapshots over the 2026-27 season, a future revisit could narrow this interval — the addendum names this as the thing to re-check first if the verdict is ever worth revisiting.
- No blockers for the remaining Phase 10 follow-up todos (per-position enrichment re-measure already done via 260909-5vx; manual FBref snapshot and RL reward-shaping notes remain pending, unrelated to this task).

## Self-Check: PASSED

All 9 key files found on disk (backtest/ep_next_provenance.py, config.py, backtest/walk_forward.py, backtest/benchmark_external.py, tests/test_leakage.py, tests/test_experiments.py, IMPROVEMENTS.md, the moved todo file, this SUMMARY). All 3 task commits (a7cdb03, fcba981, d48432e) found in git log. Plan-level `<verification>` bullets re-run: provenance control reported with n/interval/ts_utc/next_gw (pass); unflagged 2025-26 run reproduces `wf_baseline_phase9.csv`'s row exactly on model+chips/multi_safe/capt_capture (pass); outage masking tested both directions in `tests/test_experiments.py` (pass); both adoption arms judged against the pre-declared D-05/D-07 bar with season-clustered intervals (pass); benchmark re-score carries its own fresh all-off baseline and states F7 (pass); availability half recorded as measured-absent with a dated forward path (pass); `config.EXPERIMENTS` all-False confirmed via `python -c` (pass); no tracked file under predict/api/web/features/data modified (pass, with the pre-existing-untracked-file caveat documented in Deviation 3); `tests/test_experiments.py tests/test_leakage.py tests/test_legality.py` — 55 passed (pass).

---
*Phase: quick-260909-elx*
*Completed: 2026-09-09*
