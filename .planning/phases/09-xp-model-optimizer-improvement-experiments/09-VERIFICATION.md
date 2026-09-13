---
phase: 09-xp-model-optimizer-improvement-experiments
verified: 2026-09-09T04:00:00Z
status: passed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 9: xP Model & Optimizer Improvement Experiments Verification Report

**Phase Goal:** Raise honest walk-forward season points from the current ~2,105–2,256 core toward the realistic automated frontier (~2,300+), judged exclusively by the existing leakage-safe 6-season harness (`backtest/walk_forward.py`) — never by optimistic backtests. Six candidate experiments (benchmark, captaincy ceiling, chip scheduler v2, team-strength, RL-for-strategy gated on chips, three enrichment sources) run in order, each measured honestly and mechanically adopted or rejected per pre-declared criteria (D-05/D-07/D-08).
**Verified:** 2026-09-09
**Status:** passed
**Re-verification:** No — initial verification

## Interpretive Note on the Numeric Ambition vs. the Measured Outcome

This phase's goal statement sets an ambition ("toward ~2,300+", primary adoption bar ≥2,280) but its actual deliverable, as scoped by the phase's own pre-declared decisions (`09-CONTEXT.md` D-05 through D-08), is a **mechanical, honest experiment process**, not a guaranteed points gain. All six recommended experiments (eight flags, since captaincy split into two and enrichment split into three) were built, run on the real leakage-safe 6-season harness, and independently measured against a bar declared *before* the run. The measured outcome: **every experiment was REJECTED** — `model+chips` closed the phase at 2,262, identical (by construction — a fresh independent run, not a copy) to the phase's own freshly-measured opening baseline, 18 points short of the 2,280 bar and comfortably inside the harness's own season-to-season noise band (SE≈52 over n=6). The phase's own instructions and this verifier's brief agree: a phase that runs experiments honestly and lets a pre-declared criterion decide is achieved even when nothing is adopted. That is what the evidence below confirms happened — no experiment's rejection was fabricated, avoided, or measured on a softer bar than declared, and no code was silently dropped.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All 8 experiment flags exist in `config.EXPERIMENTS`, default off, and an unflagged run reproduces the pre-phase baseline (D-07/D-08) | ✓ VERIFIED | `config.py:183-192` — all 8 keys (`capt_ceiling`, `capt_mc`, `chips_v2`, `team_strength`, `rl_strategy`, `understat`, `fotmob`, `fbref_v2`) present, all `False`; `wf_final_combined.json.experiments == wf_baseline_phase9.json.experiments` (both all-False), and `model+chips` bit-for-bit identical (2262 == 2262) |
| 2 | `backtest/walk_forward.py` supports season-subset + flag-subset + tagged output for fast iteration (D-14) | ✓ VERIFIED | `backtest/walk_forward.py:239-260` — `argparse` flags `--experiments`, `--seasons`, `--tag`, `--capt-lambda`, `--chips-hysteresis`, `--rl-seed`, `--optimistic-plan` all present and used across the phase's sweep files (`wf_capt_lam_0.0.json` … `wf_capt_lam_1.0.json`, `wf_chips_hys_0.json` … `_3.json`) |
| 3 | Turning `capt_ceiling` on changes the armband, visible as a different `capt_capture` (D-06) | ✓ VERIFIED | `wf_baseline_phase9.json.capt_capture = 0.563` vs `wf_capt_ceiling_adopt.json.capt_capture = 0.578` — real, measured difference, not asserted |
| 4 | The captaincy ceiling artifact for test season T is fit only on seasons strictly before T (leakage-safe) | ✓ VERIFIED | `backtest/walk_forward.py:294-295`: `val_season = DATA_SEASONS[DATA_SEASONS.index(T) - 1]` then `captaincy.fit_ceiling_artifact(models, df, val_season, cols)` — the artifact is refit per test season on the immediately-prior season, never the shipped 2025-26 artifact |
| 5 | The 6-season baseline the 2,280 bar is judged against was measured fresh on this machine, not inherited from a cached CSV | ✓ VERIFIED | `data/processed/experiments/wf_baseline_phase9.json` exists, dated 2026-09-08 07:22, `model+chips=2262`, matches IMPROVEMENTS.md's documented reconciliation against both prior cached estimates (2256/2263) |
| 6 | The external-projection benchmark (theFPLkiwi) is reproducible from committed data with zero network access (D-10) | ✓ VERIFIED | `data/external/kiwi/ID_Dictionary.csv` (467 lines) + 3 season CSVs + `data/external/README.md` committed; `backtest/benchmark_external.py` reads only these plus `features.parquet`; result recorded in `benchmark_phase9.json` |
| 7 | One shared player-identity crosswalk serves every enrichment source (D-03) | ✓ VERIFIED | `data/id_crosswalk.py` (`resolve_by_name`) is imported and used identically by `data/understat.py` and `data/fotmob.py`; `tests/test_crosswalk.py` (6 tests) passes |
| 8 | Chip timing is decided by an xP-scored comparison, causal (only sees g..g+visibility), and provably independent of realised points | ✓ VERIFIED | `optimize/chips.py::scored_schedule` reads only `xp_col`/`capt_col`/`gw`/`player_code`/`team`; `tests/test_chips.py::test_scored_schedule_ignores_shuffled_y_points`, `test_scored_schedule_blind_beyond_visibility_window` both pass |
| 9 | Wildcard's isolated marginal value is measured for the first time, and no chip's isolated value regresses unnoticed under `chips_v2` (D-06) | ✓ VERIFIED | `wf_wc_measure.json`/IMPROVEMENTS.md: WC = +14.2±9.0 pts/gw (n=4), first measurement; `chips_v2`'s own regression run correctly flags `bb` regressing outside its v1 CI (10.0±0.0 → 8.5±6.5) — the regression check functioned and fed into the REJECTED verdict, not silently passed |
| 10 | Team-strength ratings cover every season including 2016-19 (where odds are null), and ratings for GW g reproduce from matches strictly before g (D-06) | ✓ VERIFIED | `tests/test_leakage.py::test_team_strength_ratings_reproducible_from_prior_matches` passes (ran directly, 1 of 3 in the leakage subset); `data/team_strength.py` builds numeric-side fixtures independent of the odds join's `team` column |
| 11 | Any horizon-touching change reports both an optimistic and a frozen-form number (D-06) | ✓ VERIFIED | `--optimistic-plan` flag exists and was exercised in `wf_team_strength_adopt.json`; IMPROVEMENTS.md documents both `multi_safe` (2135) and `multi_optimistic` (2527) side by side |
| 12 | RL: illegal actions are masked, not merely penalized; reward is realised points net of hits, never raw xP; ILP still selects players (D-02) | ✓ VERIFIED | `optimize/rl_env.py` — `action_masks()`; `tests/test_rl_env.py::test_action_masks_marks_used_chip_illegal_after_use`, `test_action_masks_masks_transfer_above_budget`, `test_reward_matches_run_season_hold_policy` all pass (6/6 in module) |
| 13 | RL dependency stack is isolated in its own lockfile, absent from every production install path (D-09) | ✓ VERIFIED | `requirements-rl.in`/`.txt` exist; `grep` for `requirements-rl`/`torch`/`gymnasium`/`stable.baselines` across `Dockerfile`, `.github/workflows/`, `scripts/` returns zero hits |
| 14 | RL is adopted only if it beats the solver-scored chip scheduler on the same harness, else rejected with numbers (D-02) | ✓ VERIFIED | `wf_rl_adopt_seed{0,1,2}.json`: 1847/2069/2144 (mean 2020) vs `chips_v2`'s same-5-season 2192 (`wf_chips_v2_5season.json`) — a real, measured −172/season shortfall on every seed |
| 15 | Understat/FotMob enter only through leakage-safe rolled features, never raw context; coverage percentage reported; row count of canonical table unchanged | ✓ VERIFIED | `tests/test_leakage.py::test_understat_features_are_rolled_not_raw`, `test_fotmob_features_are_rolled_not_raw` both pass; `UNDERSTAT_COLS`/`FOTMOB_COLS` registered in `features/engineer.py::ROLL_STATS` (not `CONTEXT_COLS` — spot-checked in `config.py` comments); IMPROVEMENTS.md documents `player_gw.parquet` staying at 253,509 rows after each rebuild |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config.py` | `EXPERIMENTS` registry, tuned constants | ✓ VERIFIED | 8-key dict, all False; `CAPT_CEILING_LAMBDA=0.5`, `CHIPS_V2_HYSTERESIS=0.0`, `RL_SEEDS=(0,1,2)` — all match sweep-winning values in IMPROVEMENTS.md |
| `models/captaincy.py` | leakage-safe `xp_capt_ceiling` column | ✓ VERIFIED | 91 lines, formula matches docstring, refits per-season artifact |
| `models/simulate.py` | Monte-Carlo captaincy variant (conditional) | ✓ VERIFIED (correctly absent) | Not built — matches the recorded, numbered decision that the +0.02 trigger (measured +0.015) was never crossed; `config.EXPERIMENTS['capt_mc']` stays False |
| `optimize/chips.py` | `scored_schedule` behind `chips_v2` | ✓ VERIFIED | present, wired, tested (6 chip tests pass) |
| `data/team_strength.py` | Dixon-Coles ratings | ✓ VERIFIED | 316 lines, ridge-regularized, leakage test passes |
| `optimize/rl_env.py` / `rl_train.py` | Gymnasium env + time-boxed trainer | ✓ VERIFIED | 309 / 304 lines; 6/6 env tests pass; sidecar JSONs confirm `capped: true` on all 15 policies |
| `data/understat.py` / `data/fotmob.py` | enrichment fetchers with cache/kill-switch | ✓ VERIFIED | 304 / 337 lines; leakage tests pass; parquet caches present under `data/raw/` |
| `data/id_crosswalk.py` | shared name resolver | ✓ VERIFIED | 284 lines, used by both enrichment sources, 6 crosswalk tests pass |
| `scripts/experiment_run.sh` | unattended launcher | ✓ VERIFIED | 33 lines, referenced by name in every adoption-run log/tag pattern found on disk |
| `tests/test_experiments.py` | flag-registry + scheduler-resolution regression tests | ✓ VERIFIED | 192 lines, 17 test functions, all pass |
| `tests/test_product.py` new tests | export-contract + no-adopted-flags guard | ✓ VERIFIED | `test_export_contract_file_set_and_key_sets`, `test_no_adopted_experiment_flags_needed_product_wiring` both present and pass |
| `IMPROVEMENTS.md` Phase F | complete ledger, no pending cells | ✓ VERIFIED | All 8 flag rows carry a number/verdict; only occurrence of the string "pending" is prose describing the process, not a literal unfilled cell |
| `predict/live.py` / `predict/export.py` | product wiring for whatever was adopted | ✓ VERIFIED (correctly unchanged) | No `config.EXPERIMENTS` reference in either file — correct, since nothing was adopted; confirmed by a real end-to-end `python -m predict.export` run refreshing `web/data/*.json` with zero schema change (per 09-10-SUMMARY and spot-checked file presence) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `config.resolve_experiments()` | `backtest/walk_forward.py main()` | `--experiments` CLI arg | ✓ WIRED | confirmed in argparse + runtime JSON `experiments` field matching requested flags |
| `models/intervals.py` | `models/captaincy.py` | `fit_ceiling_artifact`/`add_ceiling_ev` | ✓ WIRED | direct import, formula verified in source |
| `config.EXPERIMENTS['chips_v2']` | `optimize/chips.py::scored_schedule` | `backtest/season.py` scheduler resolution | ✓ WIRED | `tests/test_experiments.py::test_resolve_scheduler_chips_v2_flag_maps_to_v2` passes |
| `data/team_strength.ratings_as_of()` | `backtest/walk_forward.py::leakage_safe_plan()` | decision-time horizon graft | ✓ WIRED | confirmed via `test_team_strength_ratings_reproducible_from_prior_matches` and IMPROVEMENTS.md's stated absence of any `ts_*` name in `FIXTURE_CTX` |
| `requirements-rl.txt` | (nothing) | manual dev-only install | ✓ VERIFIED ABSENT | zero references in Dockerfile/CI/scripts, as required by D-09 |
| `config.EXPERIMENTS` adopted set | `predict/live.py`/`predict/export.py` | product wiring | ✓ VERIFIED (vacuous — no adopted flags) | zero flags True; zero wiring present; correct per D-13/plan 09-10's own instruction |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted phase-9 test modules pass | `pytest -q tests/test_experiments.py tests/test_chips.py tests/test_crosswalk.py` | 32 passed | ✓ PASS |
| Phase-9 leakage assertions pass | `pytest -q tests/test_leakage.py -k "team_strength or understat or fotmob"` | 3 passed | ✓ PASS |
| New product-contract regression tests pass | `pytest -q tests/test_product.py -k "export_contract or no_adopted"` | 2 passed | ✓ PASS |
| RL environment tests pass | `pytest -q tests/test_rl_env.py` | 6 passed | ✓ PASS |
| Full project test suite | `pytest -q` (run once) | 217 passed, 1 skipped | ✓ PASS (matches SUMMARY's claimed count exactly) |
| Lint | `ruff check .` | All checks passed | ✓ PASS |
| Baseline vs final-combined determinism | `python3 -c` JSON diff of `wf_baseline_phase9.json` vs `wf_final_combined.json` | `model+chips` 2262 == 2262, `experiments` dicts identical | ✓ PASS |
| capt_ceiling actually changes armband | JSON diff of `capt_capture` field | 0.563 (off) vs 0.578 (on) | ✓ PASS |

### Requirements Coverage

No requirement IDs are declared for this phase (ROADMAP.md: "Requirements: TBD") and no plan's frontmatter lists any requirement ID. `REQUIREMENTS.md` has no Phase 9 entries. **No orphaned requirements found** — nothing to trace.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD`/`FIXME`/`XXX` scan across all 24 phase-modified files | none found | — |
| — | — | `TODO`/`HACK`/"not implemented"/"placeholder" scan | 1 hit, benign | ℹ️ Info — `backtest/benchmark_external.py:138` says "placeholder entries" describing theFPLkiwi's own external data semantics (ID==0 rows), not a stub in this project's code |
| `data/understat.py` | ~160 | Documented "never raises" contract has one line (`match_ids = {m["id"] for m in matches}`) outside its guarding try/except | ⚠️ Warning (pre-existing, from `09-REVIEW.md` WR-01) | Low — optional enrichment defaults off; a malformed upstream payload could raise instead of degrading gracefully |
| `optimize/rl_env.py` | 78-84 | Horizon observation reuses current-GW xP for all future fixtures instead of each future GW's own prediction (from `09-REVIEW.md` WR-04) | ⚠️ Warning (pre-existing) | Low — `rl_strategy` defaults off and was independently rejected on its own numbers regardless of this bug; noted for any future revisit |
| `optimize/rl_env.py` | 100-101 | `TRANSFER_CAPS` magic-number offset decoupled from `HIT_BUDGET` (from `09-REVIEW.md` WR-03) | ⚠️ Warning (pre-existing) | Low — same default-off blast-radius limit |

These three warnings were already surfaced by this phase's own `09-REVIEW.md` (code review, `status: issues_found`, 0 critical / 6 warning / 3 info) and are carried forward here for completeness rather than re-discovered. None blocks the phase goal: all affected code paths are behind default-off flags with zero product-path exposure, and the goal ("run these experiments honestly on the harness") does not depend on these code-quality issues being fixed.

### Human Verification Required

None. All must-haves were verifiable programmatically: numeric claims were cross-checked against the actual JSON result files (not just IMPROVEMENTS.md prose), code implementing the described formulas/gating/masking was read directly, and the specific named tests each SUMMARY cites were run and confirmed passing.

### Gaps Summary

No gaps. Every one of the 10 plans' must-haves is backed by artifacts that exist, are substantive (not stubs — formulas, gating logic, and masking logic were read and match their documentation), are wired (flags reach the harness, the harness reaches the scheduler/captaincy/RL/enrichment seams), and — where the must-have was a specific number — that number was independently re-derived from the raw JSON result files rather than trusted from IMPROVEMENTS.md prose. The phase's ambition (raise season points toward 2,300+) was not achieved — the harness closed at 2,262, unchanged from where it opened, 18 points short of the 2,280 adoption bar — but the phase's actual contract (run every candidate experiment honestly on the leakage-safe harness, apply a mechanical pre-declared adoption rule, never drop a result silently) was fully delivered and is verified true in the codebase, not just claimed in prose.

---

_Verified: 2026-09-09_
_Verifier: Claude (gsd-verifier)_
