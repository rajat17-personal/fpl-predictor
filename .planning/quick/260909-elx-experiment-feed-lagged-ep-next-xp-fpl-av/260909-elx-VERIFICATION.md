---
phase: quick-260909-elx
verified: 2026-09-09T16:44:23Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Quick Task 260909-elx Verification Report

**Task Goal:** Experiment: feed lagged ep_next (xp_fpl) + availability-flag features into the
xP model behind a default-off flag; measure on the honest harness vs the 2262 baseline and
record the verdict.

**Verified:** 2026-09-09T16:44:23Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A developer can read one section of IMPROVEMENTS.md and get a plain answer on whether ep_next closes the played-only Spearman gap and whether it's safe to use | ✓ VERIFIED | `IMPROVEMENTS.md:1237-1398` addendum contains the provenance verdict, coverage census, adoption table, and benchmark re-score, all inlined |
| 2 | Record states the todo's headline proposal (lagged ep_next) was already shipped via ROLL_STATS, and only previous-fixture + same-fixture signals are genuinely new | ✓ VERIFIED | `IMPROVEMENTS.md:1239-1250` states this explicitly; confirmed `features/engineer.py` `ROLL_STATS` includes `"xp_fpl"` (produces `xp_fpl_r3/r5/r10/rall`) predates this task |
| 3 | Decision-time provenance of same-fixture xp_fpl settled by measurement against a KNOWN-pre-deadline control (data/snapshots/*.parquet), governing adoptability | ✓ VERIFIED | Re-ran `python -m backtest.ep_next_provenance` independently — reproduced historical P(played\|xp_fpl==0)=0.0229 [0.0216,0.0243] n=48671 vs control 0.0815 [0.0544,0.1203] n=270, exonerated=False, byte-identical to SUMMARY/addendum claims |
| 4 | Availability half answered with measured truth that no per-gameweek historical availability data exists, plus a dated forward path | ✓ VERIFIED | `IMPROVEMENTS.md:1365-1380` states the measured absence (checked `players_raw.csv`, `merged_gw.csv`, `element_history.parquet`) and the daily-cron forward path since 2026-08-31 |
| 5 | Every reported model+chips / multi_safe / Spearman delta is paired per season against a same-feature-matrix baseline | ✓ VERIFIED | Recomputed means from `wf_ep_next_lag.csv` (2223) and `wf_ep_next_now.csv` (3049) against `wf_baseline_phase9.csv` (2262) — match addendum table exactly; benchmark re-score carries its own fresh `ep_next_base` baseline (0.383) rather than reusing the stale published number, per F7 |
| 6 | Nothing about the shipped product changed: every config.EXPERIMENTS key is False; predict/, api/, web/, features/, data/ untouched | ✓ VERIFIED | `python -c "assert not any(config.EXPERIMENTS.values())"` passes (10 keys, all False); `git diff --stat a7cdb03~1..d48432e -- predict api web features data` is empty (only two pre-existing untracked cron files present, not tracked/modified by this task) |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backtest/ep_next_provenance.py` | measurement-only provenance module | ✓ VERIFIED | 315 lines, substantive (coverage census, historical stats, Wilson-CI control, verdict), executed successfully, output matches claims |
| `data/processed/experiments/ep_next_provenance.json` | provenance output | ✓ VERIFIED | Present on disk (gitignored per design), regenerated on re-run, contents match |
| `wf_ep_next_lag.csv` / `wf_ep_next_now.csv` | tagged adoption runs | ✓ VERIFIED | Both present, 6 seasons each, means recomputed and match addendum (2223 / 3049 model+chips) |
| `benchmark_ep_next_base.json` / `_lag.json` / `_now.json` | tagged benchmark re-score | ✓ VERIFIED | All three present, n_rows=17488 each, Spearman values (0.3832/0.3833/0.5158) match addendum's 0.383/0.383/0.516 |
| IMPROVEMENTS.md addendum | Phase F addendum under "ep_next as a model feature" | ✓ VERIFIED | Lines 1237-1398, covers all 7 required points (F1 correction, coverage/masking, provenance verdict, adoption table, benchmark re-score, availability half, caveats+closing) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `config.EXPERIMENTS["ep_next_lag"/"ep_next_now"]` | `apply_experiment_feature_gating` | flag-gated column-adding branch | ✓ WIRED | Confirmed: flags-off leaves frame at the pre-existing drop-only column set (109 of 161 cols, matching the ts_/us_/fm_ precedent exactly); flags-on adds exactly `xp_fpl_lag1`, `xp_fpl_now`, both reaching `feature_cols()`, neither leaking when off |
| `xp_fpl` literal column | `models.train._EXCLUDE` / walk_forward / benchmark_external scoring | survives gating unchanged | ✓ WIRED | `xp_fpl` present and byte-identical to input under all 4 flag combinations (verified via `test_ep_next_xp_fpl_literal_survives_every_flag_combination`, and independently via `on.columns` check) |
| `backtest/benchmark_external.py --experiments` | `apply_experiment_feature_gating` | new CLI option, default preserves ungated behaviour | ✓ WIRED | `_resolve_gate_experiments`/`score(experiments=None)` default path confirmed unchanged; gated three-way re-score produced distinct, internally-consistent numbers |
| `backtest.ep_next_provenance` | `data/snapshots/*.parquet` + `data/raw/live/element_history.parquet` | join on player_id/gw for known-pre-deadline control | ✓ WIRED | Re-run independently reproduces n=270, P=0.0815 [0.0544,0.1203] from the single covered snapshot (2026-08-31); 2026-09-07 correctly reported `covered: False` (gw4 has no realised minutes yet) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Provenance verdict reproducible | `python -m backtest.ep_next_provenance` | verdict: exonerated=False, numbers byte-identical to SUMMARY/addendum claims | ✓ PASS |
| Gate is a no-op with flags off | `gate(df, {})` vs pre-existing drop-only column set | identical (109 cols) | ✓ PASS |
| Gate adds exactly 2 columns with flags on | `gate(df, {all True})` | `['xp_fpl_lag1', 'xp_fpl_now']`, both in `feature_cols`, none leaking when off | ✓ PASS |
| Unflagged single-season run reproduces phase-9 baseline exactly | `wf_elx_default_check.csv[2025-26]` vs `wf_baseline_phase9.csv[2025-26]` | model+chips/multi_safe/capt_capture all equal (2172/2086/0.595) | ✓ PASS |
| Adoption CSV means match addendum table | recomputed mean(model+chips) from `wf_ep_next_lag.csv`/`wf_ep_next_now.csv` | 2223.2 / 3049.2, matches 2223/3049 in addendum | ✓ PASS |
| Benchmark re-score numbers match addendum | `benchmark_ep_next_{base,lag,now}.json` pooled Spearman | 0.3832/0.3833/0.5158, matches 0.383/0.383/0.516 | ✓ PASS |
| Named unit + leakage tests pass | `pytest tests/test_experiments.py tests/test_leakage.py -q` | 44 passed | ✓ PASS |
| Full regression (Task 3's declared set) passes | `pytest tests/test_experiments.py tests/test_leakage.py tests/test_legality.py -q` | 55 passed | ✓ PASS |
| Product surface untouched | `git diff --stat a7cdb03~1..d48432e -- predict api web features data` | empty | ✓ PASS |
| Todo moved to completed | `ls .planning/todos/completed/` | `2026-09-09-ep-next-as-feature-minutes-signals.md` present, absent from `pending/` | ✓ PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| TODO-2026-09-09-ep-next-as-feature-minutes-signals | Feed lagged ep_next + availability into xP model behind default-off flag, measure on honest harness | ✓ SATISFIED | Both arms measured, mechanically judged against D-05/D-07, provenance-gated per T-elx-01, availability half honestly scoped as measured-absent; flags stay False per the task's own non-goal |

### Anti-Patterns Found

None found. No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers in the modified files. No stub returns, no hardcoded empty data flowing to output — the provenance module's numeric outputs trace to real parquet reads and joins, verified by independent re-execution.

### Human Verification Required

None. All must-haves are objectively verifiable via reproducible computation (provenance module re-run, test suite, git diff), and all reproduced exactly.

### Gaps Summary

No gaps found. The task is a measurement/rejection quick task by design (its own non-goal states "this plan adopts nothing and flips no flag"), and every claim in SUMMARY.md was independently re-derived from committed code and on-disk artifacts rather than trusted at face value:

- The provenance verdict (the load-bearing claim of the whole task) was re-run from scratch and produced byte-identical numbers.
- The gating branch's no-op/add-two-columns/no-leak/xp_fpl-survives properties were independently re-checked against `load_features()`, not just via the test suite.
- The adoption and benchmark numbers quoted in IMPROVEMENTS.md were cross-checked against the actual CSV/JSON artifacts on disk.
- The "product surface untouched" claim was verified via `git diff --stat` across the task's full commit range, not just a working-tree `git status` snapshot.
- The three documented deviations in SUMMARY.md (assertion methodology corrections, CPU-contention process cleanup, and the pre-existing-file exclusion) are self-disclosed, verification-only, and correctly characterized — none understate scope or hide an implementation gap.

---

_Verified: 2026-09-09T16:44:23Z_
_Verifier: Claude (gsd-verifier)_
