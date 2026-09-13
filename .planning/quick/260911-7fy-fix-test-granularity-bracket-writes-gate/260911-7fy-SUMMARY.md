---
phase: quick-260911-7fy
plan: 01
subsystem: testing
tags: [pytest, torch, mlp, bracket, test-isolation, monkeypatch]

requires:
  - phase: 10-11
    provides: "run_granularity_bracket('mlp') and the real pooled/0.3942 gate measurement"
  - phase: 10-13
    provides: "GRU/transformer candidates that depend on reading bracket_gate_mlp.json as an input ledger"
provides:
  - "tests/test_bracket.py: both MLP-writing tests (test_mlp_search_respects_budget, test_granularity_bracket_writes_gate_schema) redirect config.EXPERIMENTS_DIR to tmp_path"
  - "data/processed/experiments/bracket_gate_mlp.json restored to the real, measured plan 10-11 result (pooled, spearman_xp_med=0.3942)"
  - "WINDOWS.md entry 6 closed as fixed"
affects: [10-14-xp-experiment-follow-ups, models/bracket]

actuals:
  tokens: 1690
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "config.EXPERIMENTS_DIR monkeypatch-to-tmp_path is the standard isolation pattern for any test that calls a models/bracket/*.py writer function"

key-files:
  created: []
  modified:
    - tests/test_bracket.py
    - .planning/WINDOWS.md
    - data/processed/experiments/bracket_gate_mlp.json (gitignored, restored)
    - data/processed/experiments/bracket_search_mlp_pooled.json (gitignored, restored)
    - data/processed/experiments/bracket_search_mlp_per_position.json (gitignored, restored)

key-decisions:
  - "Restored bracket_gate_mlp.json by re-running run_granularity_bracket('mlp') for real rather than hand-writing the remembered numbers, per the plan's HALT-if-mismatch instruction (T-7fy-02) -- the re-run reproduced the plan 10-11 oracle exactly."
  - "Captured the bracket_gate_lgbm.json baseline read in test_granularity_bracket_writes_gate_schema BEFORE monkeypatching config.EXPERIMENTS_DIR, since that baseline file only exists in the live directory."

patterns-established:
  - "Pattern: config.EXPERIMENTS_DIR is resolved at CALL time inside models/bracket/deep.py, so monkeypatch.setattr(config, 'EXPERIMENTS_DIR', tmp_path) is sufficient to redirect all writer functions in that module without further plumbing."

requirements-completed: [WINDOW-6]

coverage:
  - id: D1
    description: "test_granularity_bracket_writes_gate_schema and test_mlp_search_respects_budget no longer write into the live data/processed/experiments/ directory"
    requirement: WINDOW-6
    verification:
      - kind: unit
        ref: "tests/test_bracket.py::test_granularity_bracket_writes_gate_schema and ::test_mlp_search_respects_budget"
        status: pass
      - kind: other
        ref: "sha256sum of bracket_gate_mlp.json / bracket_search_mlp_pooled.json / bracket_search_mlp_per_position.json unchanged before/after tests/test_bracket.py run"
        status: pass
    human_judgment: false
  - id: D2
    description: "bracket_gate_mlp.json holds a real measured gate result (pooled, spearman_xp_med=0.3942), reproduced by an actual run_granularity_bracket('mlp') call and matching the plan 10-11 oracle log"
    requirement: WINDOW-6
    verification:
      - kind: other
        ref: "python -c assertion block comparing bracket_gate_mlp.json fields to the plan 10-11 oracle (granularity, spearman_xp_med, mae_xp_med, n_played_rows, granularity_scores, val_season, train_seasons) — all matched"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full pytest suite (323 passed, 1 skipped) leaves the restored bracket_gate_mlp.json byte-identical, and WINDOWS.md entry 6 is marked fixed"
    requirement: WINDOW-6
    verification:
      - kind: unit
        ref: "python -m pytest -q (full suite, no path filter) from /home/sraja/fpl"
        status: pass
      - kind: other
        ref: "sha256sum of bracket_gate_mlp.json before/after full suite run — identical"
        status: pass
      - kind: other
        ref: "gsd-tools windows status --raw -> ledger.entries[id=6].status == 'fixed'"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-09-11
status: complete
---

# Quick Task 260911-7fy: Fix test granularity-bracket writes gate Summary

**Isolated the MLP bracket tests' artifact writes to tmp_path and re-measured the real plan 10-11 gate result (pooled, spearman_xp_med=0.3942) to restore the file the broken test had been clobbering.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-09-11T05:36:30-04:00 (first task commit)
- **Completed:** 2026-09-11T05:56:53-04:00
- **Tasks:** 3
- **Files modified:** 5 (2 tracked, 3 gitignored runtime artifacts)

## Accomplishments
- `test_granularity_bracket_writes_gate_schema` and `test_mlp_search_respects_budget` now both redirect `config.EXPERIMENTS_DIR` to `tmp_path`, so `pytest` never again overwrites the live, measured `bracket_gate_mlp.json`
- `bracket_gate_mlp.json` restored to the real, measured plan 10-11 result via an actual `run_granularity_bracket("mlp")` call — reproduced the oracle exactly: `granularity=pooled`, `spearman_xp_med=0.3942`, `mae_xp_med=1.7805`, `n_played_rows=11566`, winning config `hidden=(64,32) dropout=0.1 lr=0.002 weight_decay=0.0`
- Both real MLP search logs (`bracket_search_mlp_pooled.json`, `bracket_search_mlp_per_position.json`) hold their real 12-config searches again; the stray `bracket_search_mlp_unit_test.json` is deleted and cannot be recreated
- Full pytest suite (323 passed, 1 skipped, unrelated to this change) proven to leave `bracket_gate_mlp.json` byte-identical
- `.planning/WINDOWS.md` entry 6 marked `fixed` via `gsd-tools.cjs windows fixed 6`

## Task Commits

Each task was committed atomically:

1. **Task 1: Redirect the bracket tests' artifact writes to tmp_path, end-to-end** - `d8543ad` (fix)
2. **Task 2: Restore bracket_gate_mlp.json by re-running the real gate** - no commit (only gitignored `data/processed/` artifacts were modified; the real gate run itself produces no committable diff)
3. **Task 3: Prove suite-wide stability and close WINDOW-6** - `3099bf1` (fix)

_Note: Task 2 modified only gitignored runtime artifacts (`data/processed/experiments/*.json` and the timestamped restore log), so it has no separate git commit — its result is proven live by Task 3's byte-identity check and folded into the Task 3 commit message._

## Files Created/Modified
- `tests/test_bracket.py` - Added `config.EXPERIMENTS_DIR` -> `tmp_path` monkeypatch to `test_mlp_search_respects_budget` and `test_granularity_bracket_writes_gate_schema`; captured the `bracket_gate_lgbm.json` baseline read before the monkeypatch; added positive isolation assertions that the run's outputs land under `tmp_path`
- `.planning/WINDOWS.md` - Entry 6 marked `status: fixed`, `open_count` decremented via `gsd-tools windows fixed 6`
- `data/processed/experiments/bracket_gate_mlp.json` (gitignored) - Restored to the real plan 10-11 measurement (pooled, 0.3942)
- `data/processed/experiments/bracket_search_mlp_pooled.json` (gitignored) - Restored to the real 12-config search log
- `data/processed/experiments/bracket_search_mlp_per_position.json` (gitignored) - Restored to the real 12-config search log
- `data/processed/experiments/bracket_mlp_gate_restore-20260911T093642Z.log` (gitignored) - Tee'd stdout/stderr of the restore run, evidence beside the original `bracket_mlp_gate_final-20260910T190818Z.log`

## Decisions Made
- Restored `bracket_gate_mlp.json` by re-running the real `run_granularity_bracket("mlp")` call rather than hand-editing the JSON to the remembered numbers, per the plan's explicit halt-on-mismatch instruction (T-7fy-02). The re-run reproduced the plan 10-11 oracle exactly, confirming the environment still reproduces that measurement (no HALT needed).
- Captured the `bracket_gate_lgbm.json` baseline read in `test_granularity_bracket_writes_gate_schema` BEFORE applying the `config.EXPERIMENTS_DIR` monkeypatch, since that baseline file only exists in the real (unpatched) directory.
- Deleted the stray `bracket_search_mlp_unit_test.json` left by the pre-fix `test_mlp_search_respects_budget`; Task 1's isolation fix prevents it from ever being recreated.

## Deviations from Plan

None - plan executed exactly as written. All three tasks (isolate tests, restore real measurement, prove suite-wide stability + close ledger entry) completed with their `<verify>` blocks passing on the first attempt.

## Issues Encountered
None. The precondition check for Task 2 (`torch.cuda.is_available()` and `data/processed/features.parquet` present) passed immediately, and the GPU re-run reproduced the plan 10-11 oracle bit-for-bit on the compared fields on the first run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `bracket_gate_mlp.json` is now safe to read as an input to plan 10-14's candidate ledger without risk of it being silently overwritten by a future `pytest` run.
- The `config.EXPERIMENTS_DIR` -> `tmp_path` isolation pattern is now established in `tests/test_bracket.py` for any future test that exercises a `models/bracket/*.py` writer function.
- WINDOWS.md now has `open_count: 3` (was 4); entries 4 and 5 (unrelated `models/bracket/gate.py` train_seasons deviation and the `uv pip sync` env-damage incident) remain open, not addressed by this task.

---
*Phase: quick-260911-7fy*
*Completed: 2026-09-11*

## Self-Check: PASSED

All claimed files exist (tests/test_bracket.py, .planning/WINDOWS.md, three restored data/processed/experiments/*.json artifacts, restore log, this SUMMARY.md) and both task commit hashes (d8543ad, 3099bf1) are present in git log.
