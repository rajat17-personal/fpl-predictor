---
phase: 04-e2e-regression-suite
plan: 07
subsystem: testing
tags: [fixture-mode, api, regression-fix, pytest, module-globals]

# Dependency graph
requires:
  - phase: 04-e2e-regression-suite (plans 01-06)
    provides: the FPL_FIXTURE_DIR seam in api/main.py (D-01) and the frozen v1 fixture set (D-08) this gap closure operates on
provides:
  - "api/main.py's else-branch that restores predict.live._gw_pool, api.main._gw_pool, and api.main._load_live to their original production objects when FPL_FIXTURE_DIR is unset"
  - "tests/test_fixture_mode.py's proof (per-test teardown assertion + one dedicated test) that the restore actually happens"
affects: [04-08 (remaining phase-wide gap-closure plan), any future phase that reloads api.main more than once in-process]

# Actuals (#2632)
actuals:
  tokens: 3200
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Capture-once module attribute (hasattr-guarded, placed ahead of the branch it protects) as the standard shape for surviving repeated importlib.reload cycles in this codebase"

key-files:
  created: []
  modified:
    - api/main.py
    - tests/test_fixture_mode.py

key-decisions:
  - "Restore all three bindings (api.main._gw_pool, predict.live._gw_pool, api.main._load_live) in the else-branch rather than relying on api.main's own re-import at module top, since that re-import itself reads predict.live's already-polluted global on a second reload."
  - "Discriminate the test's captured original reference by __module__ ('predict.live' vs 'api.main') rather than comparing it against live._gw_pool_production, so the regression proof cannot be satisfied by comparing the production code's own write against itself."

patterns-established:
  - "Capture-once guard: `if not hasattr(module, 'attr_production'): module.attr_production = module.attr`, placed immediately before the conditional branch that would otherwise overwrite the attribute -- prevents a second reload from freezing a polluted value in as the new baseline."

requirements-completed: [E2E-01]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "api/main.py restores predict.live._gw_pool, api.main._gw_pool, and api.main._load_live to the original production objects after any set/unset FPL_FIXTURE_DIR reload cycle (object identity)"
    requirement: "E2E-01"
    verification:
      - kind: unit
        ref: "Task 1 verify command 1 -- CR-01 repro script, printed RESTORE OK"
        status: pass
      - kind: unit
        ref: "Task 1 verify command 2 -- capture-once guard defeat script, printed CAPTURE-ONCE IS LOAD-BEARING"
        status: pass
      - kind: unit
        ref: "tests/test_fixture_mode.py::test_unset_env_restores_the_production_gw_pool"
        status: pass
      - kind: unit
        ref: "python -m pytest -q -- 77 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "predict.live._gw_pool_production is captured exactly once per process, before any fixture-mode branch can execute, and is never rebound by a later reload"
    requirement: "E2E-01"
    verification:
      - kind: unit
        ref: "Task 1 verify command 2 -- delattr(live, '_gw_pool_production') between reloads, still restores incorrectly (proves the guard is load-bearing, not decorative)"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/test_fixture_mode.py's fixture_app teardown asserts the restore on every fixture-mode test, and its docstring accurately describes what performs the restore (api/main.py's else-branch, not the reload alone)"
    requirement: "E2E-01"
    verification:
      - kind: unit
        ref: "python -m pytest tests/test_fixture_mode.py -q -- 10 passed"
        status: pass
      - kind: other
        ref: "grep -c 'reload back to the unset-env module' tests/test_fixture_mode.py -- 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "E2E-02 solver-flow coverage and E2E-05 fixtures/prices coverage stay green and unmodified (backstop truths, no new criterion authored in this plan)"
    requirement: ""
    verification:
      - kind: e2e
        ref: "04-VERIFICATION.md truths 2 and 5 (previously VERIFIED); this plan touched neither e2e/specs/team-solver.spec.ts nor e2e/specs/fixtures-prices.spec.ts nor its 4 variants"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-09-04
status: complete
---

# Phase 4 Plan 07: CR-01 fixture-mode restore Summary

**Closed the CR-01 regression where `api/main.py`'s FPL_FIXTURE_DIR seam permanently polluted `predict.live._gw_pool` after any fixture-mode reload cycle: added a capture-once production reference and an explicit else-branch restore, then made `tests/test_fixture_mode.py` prove the restore on every test instead of silently assuming it.**

## Performance
- **Duration:** 12min
- **Started:** 2026-09-04T05:32:00Z
- **Completed:** 2026-09-04T05:44:17Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `api/main.py` now captures `predict.live._gw_pool` exactly once per process (hasattr-guarded, ahead of the fixture-mode branch) and restores all three affected bindings (`api.main._gw_pool`, `predict.live._gw_pool`, `api.main._load_live`) whenever `FPL_FIXTURE_DIR` is unset — closing the path to the 500 `TypeError` CR-01 reproduced.
- `tests/test_fixture_mode.py` captures its own independent `_ORIGINAL_GW_POOL` reference (discriminated by `__module__`, not by comparing against the production code's own write), asserts the restore in every one of the 8 pre-existing fixture-mode tests' teardown, and adds a dedicated `test_unset_env_restores_the_production_gw_pool` that fails on a pre-Task-1 codebase.
- The module's docstring for `fixture_app` no longer credits the teardown reload alone with restoring production state — it now correctly attributes the restore to `api.main`'s own env-unset else-branch and cites CR-01.
- Full suite: 76 → 77 passed (one new test), zero regressions. Fixture-mode-ON path unchanged (`capture_fixtures.py --verify` still exits 0; `requests.get`/`joblib.load` still poisoned and unreached in fixture-mode tests).

## Task Commits
Each task was committed atomically:
1. **Task 1: Capture-once production reference and explicit else-branch restore in api/main.py** - `b03a411` (fix)
2. **Task 2: Make tests/test_fixture_mode.py assert the restore and stop claiming what the reload alone does** - `09c924d` (test)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `api/main.py` - Added the capture-once `live._gw_pool_production` block ahead of the `if _FIXTURE_ROOT:` branch, and an `else:` arm restoring `_gw_pool`, `live._gw_pool`, and `_load_live` from that captured reference.
- `tests/test_fixture_mode.py` - Added `_ORIGINAL_GW_POOL` module-level capture + `__module__` discriminator assertion, a teardown identity assertion in `fixture_app`, a corrected fixture docstring, and the new `test_unset_env_restores_the_production_gw_pool` test.

## Decisions Made
- Restored all three bindings explicitly in the else-branch rather than relying on `api.main`'s own top-of-module re-import to self-correct, because that re-import (`from predict.live import _gw_pool, ...`) reads `predict.live`'s module global at import time — on a second reload following fixture mode, that global would already be the polluted fixture replacement, making the re-import alone insufficient.
- Used a `__module__` check (`"predict.live"` vs `"api.main"`) rather than an equality/identity check against `live._gw_pool_production` to keep the test's proof of restoration independent of the very attribute the production fix writes — a broken restore that happened to also break the capture would otherwise be able to pass a self-referential check.

## Deviations from Plan
None — plan executed exactly as written. Both tasks' actions, verify commands, and acceptance criteria were followed and passed without modification.

**Total deviations:** 0.
**Impact on plan:** None.

## Issues Encountered
None. All verify commands and acceptance criteria passed on first attempt. Pre-existing uncommitted drift in `.planning/STATE.md`, `.planning/config.json`, and `.gitignore` (present before this plan started, unrelated to either task's file scope) was left untouched per the scope-boundary rule; `.planning/STATE.md` is expected to be further updated by this same execution's own state-update step.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
CR-01 (04-VERIFICATION.md Gap 1) is closed. Remaining phase-wide gap-closure work (04-VERIFICATION.md Gap 2 and the 6 other flagged probe items) is carried by plan 04-08, unaffected by this plan's changes (files_modified for 04-08 do not include `api/main.py` or `tests/test_fixture_mode.py`).

---
*Phase: 04-e2e-regression-suite*
*Completed: 2026-09-04*

## Self-Check: PASSED

- FOUND: api/main.py
- FOUND: tests/test_fixture_mode.py
- FOUND: .planning/phases/04-e2e-regression-suite/04-07-SUMMARY.md
- FOUND: commit b03a411
- FOUND: commit 09c924d
