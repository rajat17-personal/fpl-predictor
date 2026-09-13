---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 10
subsystem: ml-experimentation
tags: [walk-forward, final-combined-run, export-contract, phase-close, ledger]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, scripts/experiment_run.sh) and the measured 2262 model+chips baseline every later plan's adoption verdict — and this plan's own final combined run — is judged against"
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plans 09-03 through 09-09's D-07 adoption verdicts (all REJECTED/not-triggered/not-acquirable), which left config.EXPERIMENTS unchanged for this plan to measure and wire"
provides:
  - "data/processed/experiments/wf_final_combined.json -- the D-13 single final combined measurement (6 seasons, 5 replicas, config.EXPERIMENTS unchanged), model+chips 2262, identical to the plan 09-01 baseline"
  - "The D-05 verdict recorded arithmetically in IMPROVEMENTS.md Phase F: 2262 vs the >=2,280 bar, an 18-point shortfall well inside the harness's own noise band (SE~52 on model+chips)"
  - "tests/test_product.py::test_export_contract_file_set_and_key_sets + test_no_adopted_experiment_flags_needed_product_wiring -- a permanent regression guard on the web/data/*.json export contract (T-09-10-01) and on the no-adopted-flags invariant"
  - "IMPROVEMENTS.md Phase F closed: no pending cells, a Decisions audit walking D-01 through D-16, a 'What this phase did not resolve' section, and a Phase A-E cross-reference"
affects: []

actuals:
  tokens: 6600
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "D-13's final-combined-run protocol applied to a zero-winner phase: run it anyway with the shipped default config and record 'no change' as a legitimate, informative result rather than skipping the measurement"
    - "Export-contract regression test built from the same fixture helpers (fake_boot/fake_pool) as the phase's existing builder tests, with the pool's player_id column dropped to match the real predict.live._gw_pool shape exactly (avoids a merge-suffix false pass)"

key-files:
  created: []
  modified:
    - IMPROVEMENTS.md
    - tests/test_product.py
    - web/data/captains.json
    - web/data/meta.json
    - web/data/squad.json
    - web/data/xp_table.json

key-decisions:
  - "No product wiring was added to predict/live.py or predict/export.py: every one of Phase 9's eight experiment flags ended default-off (all REJECTED, not-triggered, or not-acquirable per plans 09-03 through 09-09), and the plan's own instruction is to wire nothing for a flag that stayed off"
  - "The final combined run was executed for real (not skipped) even though the phase adopted zero flags, per the plan's own instruction that an empty adopted set is a legitimate, informative phase outcome -- it reproduced the plan 09-01 baseline bit-for-bit (model+chips 2262, every per-season figure identical), confirming full determinism of the harness"
  - "D-05's ~2,280 bar was judged arithmetically and was not cleared (2262, -18) -- no flag was adjusted to chase it; every experiment's D-07 verdict was already locked in by the plan that measured it"

requirements-completed: []

coverage:
  - id: D1
    description: "D-13's single final combined walk-forward run, judged against the D-05 >=2,280 bar arithmetically, using the shipped default config (config.EXPERIMENTS unchanged)"
    verification:
      - kind: integration
        ref: "scripts/experiment_run.sh final_combined -> data/processed/experiments/wf_final_combined.json (6 seasons, 5 replicas, experiments == config.EXPERIMENTS, model+chips 2262)"
        status: pass
      - kind: other
        ref: "python -c assertion (Task 1's own verify): f['experiments'] == config.EXPERIMENTS and f['replicas']==5 and len(f['seasons'])==6"
        status: pass
      - kind: other
        ref: "IMPROVEMENTS.md 'Final combined run' block: command, adopted flag set (none), per-season table, 6-season means, delta vs both the measured baseline and the 2,280 bar, one-paragraph honest reading"
        status: pass
    human_judgment: false
  - id: D2
    description: "Product-path wiring: every flag that ended default-on gets wired into predict/live.py or predict/export.py; every flag that stayed off gets nothing"
    verification:
      - kind: other
        ref: "python -c assertion (Task 2's own verify): no config.EXPERIMENTS[flag] is True, so the per-flag captaincy/simulate/scored_schedule reference checks are all vacuously satisfied -- confirmed via inspect.getsource on predict.live and predict.export"
        status: pass
      - kind: integration
        ref: "python -m predict.export run end-to-end against the real FPL API + live model artifact -- completed, wrote the same 8-file/key-set contract, refreshed captains/meta/squad/xp_table.json for GW4 with zero schema change"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/test_product.py asserts the export contract's file set and per-file top-level key sets (T-09-10-01), and that no experiment flag needed product wiring"
    verification:
      - kind: unit
        ref: "tests/test_product.py#test_export_contract_file_set_and_key_sets"
        status: pass
      - kind: unit
        ref: "tests/test_product.py#test_no_adopted_experiment_flags_needed_product_wiring"
        status: pass
      - kind: integration
        ref: "python -m pytest -q -- 217 passed, 1 skipped; ruff check . -- all checks passed"
        status: pass
    human_judgment: false
  - id: D4
    description: "IMPROVEMENTS.md Phase F closed: every one of the eight experiment flags has a complete non-pending results row; a Decisions audit names D-01 through D-16; a 'What this phase did not resolve' section; config.EXPERIMENTS/tests/test_experiments.py stay in sync; every module this phase created still imports cleanly"
    verification:
      - kind: other
        ref: "python -c assertion (Task 3's own verify #1): no 'pending' in any flag row; 'Phase F'/'Decisions audit'/'What this phase did not resolve'/'Final combined' all present; D-01/D-05/D-06/D-07/D-08/D-09/D-12/D-13/D-16 all named"
        status: pass
      - kind: other
        ref: "python -c assertion (Task 3's own verify #2): config.EXPERIMENTS keys == the 8 pre-declared keys; models.captaincy/data.id_crosswalk/backtest.benchmark_external/data.team_strength/optimize.chips/backtest.walk_forward/backtest.season all import cleanly"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-09
status: complete
---

# Phase 9 Plan 10: Final Combined Run, Product Wiring Confirmation, and Phase F Close-Out Summary

**Ran D-13's single final combined walk-forward measurement (model+chips 2262, 18 points short of the D-05 ≥2,280 bar and identical to the phase-opening baseline), confirmed zero product wiring was needed since every one of Phase 9's eight experiment flags ended default-off, added a permanent export-contract regression test, and closed IMPROVEMENTS.md Phase F with a Decisions audit (D-01 through D-16) and an honest "what this phase did not resolve" ledger.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-09-09T02:20:00Z (approx.)
- **Completed:** 2026-09-09T02:49:39Z
- **Tasks:** 3
- **Files modified:** 6 (0 created, 6 modified)

## Accomplishments

- **Final combined run (D-13).** `scripts/experiment_run.sh final_combined` → `python -m backtest.walk_forward --tag final_combined` (6 seasons, 5 replicas, `--experiments` deliberately not passed) → `data/processed/experiments/wf_final_combined.json`. Result: **`model+chips` = 2262**, bit-for-bit identical to plan 09-01's `wf_baseline_phase9.json` on every season and every metric — confirming the harness is fully deterministic and that the phase's shipped default configuration is, by construction, unchanged from its opening baseline (zero flags adopted). Per-season deltas against the 2,280 bar ranged from −70 (2023-24) to +137 (2024-25); three of six seasons individually cleared the bar, three did not.
- **D-05 verdict recorded arithmetically.** 2262 vs the ≥2,280 primary bar = **−18**, and vs D-05's own quoted "current ≈2,256" = +6. Read against the harness's own season-to-season spread on `model+chips` (sample std ≈126, SE ≈52 over n=6), the −18 shortfall is well inside one standard error — the honest reading is "unchanged, not regressed," not "close but for bad luck." No flag was adjusted to chase the bar.
- **Zero product wiring needed.** Every one of the eight experiment flags (`capt_ceiling`, `capt_mc`, `chips_v2`, `team_strength`, `rl_strategy`, `understat`, `fotmob`, `fbref_v2`) ended this phase default-off — six REJECTED with numbers, one (`capt_mc`) never triggered, one (`fbref_v2`) never acquirable. Per the plan's own instruction ("wire nothing for a flag that stayed off"), `predict/live.py` and `predict/export.py` needed no behavioural changes; this task's only real work was the no-op verification the plan itself calls for.
- **Export contract locked with a permanent regression test.** `tests/test_product.py` gained `test_export_contract_file_set_and_key_sets` (asserts the exact `web/data/*.json` file set and every file's top-level key set, built from the same fixture helpers the file's existing builder tests already use) and `test_no_adopted_experiment_flags_needed_product_wiring` (asserts `config.EXPERIMENTS` stays all-off, so a future adoption must touch this test deliberately) — closing T-09-10-01.
- **`python -m predict.export` run end to end** against the real FPL API and the live model artifact: completed in ~2.5 minutes, wrote the identical 8-file/key-set contract, and refreshed `captains.json`/`meta.json`/`squad.json`/`xp_table.json` for the current GW4 with zero schema change (verified via `git diff` — only `generated_utc` changed in `meta.json`; the other three files were byte-identical in shape and content).
- **IMPROVEMENTS.md Phase F closed.** Every one of the eight flags already carried a non-`pending` results row from prior plans (confirmed, not re-filled); this plan added a **Decisions audit** walking D-01 through D-16 (two — D-01, D-12 — explicitly flagged as honoured in spirit/with a documented exception, not literally), a **"What this phase did not resolve"** section (the unclearded D-05 bar, `capt_mc`'s untriggered question, `fbref_v2`'s harder-than-before access failure, `rl_strategy`'s untested larger-budget ceiling, the eyeballed-noise-band judgment behind every REJECTED verdict, the unexplained `xp_fpl` benchmark gap, and the untouched model/decision layer), and a **Phase A–E cross-reference** tying this phase's results to captain-by-mean, the clean-sheet/ranking-loss/MILP "no added machinery beats the baseline" pattern, and Phase E's FBref/Understat findings.

## Task Commits

Each task was committed atomically:

1. **Task 1: The final combined run and the D-05 verdict** - `b833826` (docs)
2. **Task 2: Make the weekly product do what the harness adopted** - `6bdfbb9` (test)
3. **Task 3: Close the ledger with a complete, auditable Phase F** - `6926217` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `IMPROVEMENTS.md` - "Final combined run" block, "Decisions audit" (D-01–D-16), "What this phase did not resolve", "This phase in the project's continuous history (Phases A–E)"
- `tests/test_product.py` - `test_export_contract_file_set_and_key_sets`, `test_no_adopted_experiment_flags_needed_product_wiring`, `EXPORT_CONTRACT_*` constants, `_export_fixture_files()` helper
- `web/data/captains.json`, `web/data/meta.json`, `web/data/squad.json`, `web/data/xp_table.json` - refreshed by the real `python -m predict.export` verification run (GW4 content, no schema change)

## Decisions Made

- No product wiring was added to `predict/live.py` or `predict/export.py`: every one of Phase 9's eight experiment flags ended default-off, and the plan's own instruction is to wire nothing for a flag that stayed off.
- The final combined run was executed for real even though the phase adopted zero flags — an empty adopted set is a legitimate, informative phase outcome, not a reason to skip the measurement. It reproduced the plan 09-01 baseline bit-for-bit, confirming the harness's full determinism.
- D-05's ≥2,280 bar was judged arithmetically and was not cleared (2262, −18); no flag was adjusted to chase it.

## Deviations from Plan

None - plan executed exactly as written. Task 2's own precondition anticipated this exact outcome ("If nothing was adopted, this task's only work is the no-op verification described below — run it anyway") and that is exactly what happened.

## Issues Encountered

- The first `python -m predict.export` invocation (via the Bash tool's default 90s timeout) was killed mid-run by the tool's own timeout before the live FPL element-history fetch (654 players) completed — not a bug in the export path itself. Re-ran the identical command in the background with output logged to `data/processed/experiments/export_test_09-10.log` and polled for completion (finished in ~160s); no code change was needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 9 is fully closed: every one of the eight experiment flags has a measured number or an evidenced reason (D-08), `config.EXPERIMENTS` is unchanged from the phase's own pre-declared registry, and the weekly product (`predict/live.py`, `predict/export.py`, the `web/data/*.json` export contract) is confirmed unaffected and still flowing.
- `tests/test_product.py`'s new export-contract regression test is a permanent guard any future phase that does adopt a flag (or touches the export builders for any other reason) must pass — a schema change now fails by name rather than silently drifting.
- IMPROVEMENTS.md Phase F stands on its own for a reader who was not here: the results table, the Decisions audit, the open-items list, and the Phase A–E cross-reference are all in one section.
- No blockers. The phase's honest walk-forward frontier stays at `model+chips` 2262 — unchanged from where this phase started, with six real experiments now closed rather than open.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-09*

## Self-Check: PASSED

All key files (IMPROVEMENTS.md, tests/test_product.py) exist on disk with the expected changes; all three task commits (b833826, 6bdfbb9, 6926217) found in `git log`; full pytest suite (217 passed, 1 skipped) and `ruff check .` both green after the final commit; `data/processed/experiments/wf_final_combined.json` present with `experiments == config.EXPERIMENTS`, 6 seasons, 5 replicas, `model+chips` 2262; `web/data/*.json` export contract file set and key sets confirmed unchanged by both the new regression test and a real `python -m predict.export` run; `config.EXPERIMENTS` confirmed to hold exactly its original 8 keys, all `False`.
