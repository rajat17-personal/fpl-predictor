---
phase: 01-test-base-layer-app-skeleton
plan: 02
subsystem: testing
tags: [pytest, fastapi, testclient, monkeypatch, di-seam, api]

# Dependency graph
requires:
  - phase: 01-01
    provides: Tracked source tree (api/main.py, config.py, pytest.ini, tests/test_product.py) and package-legitimacy sign-off
provides:
  - "_initial_state() DI seam in api/main.py — the phase's only production-code change"
  - "tests/conftest.py — autouse fixture resetting api.main module globals + artifact sentinel before/after every test"
  - "tests/test_api.py — APIT-01 contract tests for /api/health, /api/meta, /api/solve (bounds, precision, name resolution)"
affects: [01-03, 01-04, 01-05]

# Actuals (#2632)
actuals:
  tokens: 2364
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level state factory (_initial_state()) as single source of truth for a dict's pristine shape, consumed by both production cold-start logic and test fixtures"
    - "Autouse pytest fixture in conftest.py resetting shared module globals (_state, _solve_cache) before and after every test, seeding a non-None sentinel to short-circuit a real joblib.load"
    - "monkeypatch.setattr(m, \"_pool\"/\"_load_live\", ...) to bypass _refresh() entirely in every TestClient test — no outbound network, no model-artifact read"

key-files:
  created:
    - tests/conftest.py
    - tests/test_api.py
  modified:
    - api/main.py

key-decisions:
  - "Task 2 (tdd=\"true\") writes tests against an unmodified, already-correct production endpoint (files: tests/test_api.py only, per the plan's own file list) — no RED phase was forced by breaking working code. All 17 new tests passed on first run, characterizing existing behavior rather than driving new implementation. See TDD Gate Compliance section below."
  - "Duplicated TEAMS/fake_boot/fake_pool builders into tests/test_api.py rather than importing from tests/test_product.py, per repo convention (small pure builders, no shared fixture module for data across test files) and the plan's explicit instruction."

patterns-established:
  - "_initial_state() factory pattern: any future module-global dict needing test-resettability should follow this same factory-plus-assignment shape."

requirements-completed: [APIT-01]

coverage:
  - id: D1
    description: "_initial_state() DI seam extracted in api/main.py as a pure refactor (same six keys/defaults/order)"
    requirement: "APIT-01"
    verification:
      - kind: unit
        ref: "grep -c 'def _initial_state' api/main.py"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_state_isolation_and_no_artifact_load"
        status: pass
    human_judgment: true
    rationale: "Plan-level <human-check> requires a human to read the api/main.py diff and confirm it changes nothing beyond the _state initialisation block — this module runs the live weekly recommendation cycle and a behavioural regression here is undetectable from inside the test suite itself. Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase."
  - id: D2
    description: "/api/health and /api/meta full response-contract tests, with a joblib.load tripwire proving the untracked model artifact is never read"
    requirement: "APIT-01"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_health_and_meta_contract"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_state_isolation_and_no_artifact_load"
        status: pass
    human_judgment: false
  - id: D3
    description: "/api/solve from-scratch squad contract (15 squad, 11 starting, 1 captain, lock honoured, bad lock -> 422)"
    requirement: "APIT-01"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_solve_squad_contract"
        status: pass
    human_judgment: false
  - id: D4
    description: "SolveRequest numeric/enum bounds asserted at every edge and one step outside (free_transfers, horizon, max_transfers, mode)"
    requirement: "APIT-01"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_solve_request_bounds (15 parametrized cases)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Exact price_m/xp rounding equality and _resolve's exact-beats-substring / highest-xp tie-break rules"
    requirement: "APIT-01"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_solve_resolution_and_rounding"
        status: pass
    human_judgment: false

# Metrics
duration: 14min
completed: 2026-08-31
status: complete
---

# Phase 1 Plan 2: Test Base Layer & App Skeleton — API Test Seam & Contract Tests Summary

**`_initial_state()` DI seam extracted in `api/main.py`, an autouse `conftest.py` fixture that resets module globals and seeds a non-None artifact sentinel, and 19 passing contract tests in `tests/test_api.py` covering `/api/health`, `/api/meta`, and `/api/solve` (bounds, precision, name resolution) — zero outbound network, zero model-artifact reads.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-31 (Plan 01-02 start)
- **Completed:** 2026-08-31
- **Tasks:** 2
- **Files modified:** 3 (`api/main.py`, `tests/conftest.py` new, `tests/test_api.py` new)

## Accomplishments

- Extracted `_initial_state()` in `api/main.py` — the phase's only production-code
  change, verified as a pure refactor (`git diff` confined exactly to the `_state`
  initialisation block: same six keys, same defaults, same order).
- Built `tests/conftest.py`: an autouse fixture that rebuilds `api.main._state` from
  `_initial_state()` and clears `_solve_cache` before and after every test, seeding
  a non-`None` artifact sentinel so `_refresh()`'s cold-start guard never reaches
  `joblib.load(models/artifacts/xp_model.joblib)` — that file is untracked and
  absent on a clean checkout.
- Proved the harness end-to-end (Task 1, `type="tracer"`) on `/api/health` and
  `/api/meta` before extending it: full response-contract assertions, plus a
  `joblib.load` tripwire (monkeypatched to raise `AssertionError`) confirming the
  artifact is never loaded even when both endpoints run.
- Extended the same harness (Task 2) to `/api/solve`: full response contract for
  the from-scratch squad path, all `SolveRequest` numeric/enum bounds at their
  edges and one step outside (15 parametrized cases), exact `price_m`/`xp`
  equality against the pool, and `_resolve`'s exact-beats-substring (the
  "saka" vs "wan-bissaka" danger) and highest-xp tie-break rules.
- Ran the exact `pytest` invocation Phase 5's CI job will inherit:
  `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_api.py -x -q`
  → **19 passed**. Whole suite: `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q`
  → **45 passed** (26 pre-existing + 19 new), confirming the `api/main.py` refactor
  breaks nothing.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "a mocked-FPL contract test runs green"** — `7313446` (feat)
2. **Task 2: /api/solve contract, request bounds, and numeric precision** — `dee426a` (test)

**Plan metadata:** committed alongside this SUMMARY (see below).

## Files Created/Modified

- `api/main.py` — `_initial_state()` factory extracted; `_state` now initialised
  from it. No other line changed (`_refresh`, `_pool`, `_solve_cache` locking,
  `CORSMiddleware` untouched).
- `tests/conftest.py` (new, 21 lines) — autouse `_reset_api_state` fixture.
- `tests/test_api.py` (new, 202 lines) — `TEAMS`/`fake_boot`/`fake_pool` builders
  plus 5 test functions (`test_health_and_meta_contract`,
  `test_state_isolation_and_no_artifact_load`, `test_solve_squad_contract`,
  `test_solve_request_bounds` [15 parametrized cases], `test_solve_resolution_and_rounding`).

## Decisions Made

- Duplicated `TEAMS`/`fake_boot`/`fake_pool` into `tests/test_api.py` rather than
  importing from `tests/test_product.py` — matches this repo's existing convention
  of not sharing data builders across test files, and was the plan's explicit
  instruction.
- Seeded the artifact sentinel (`m._state["artifact"] = object()`) inside the
  autouse fixture itself (both setup and teardown) rather than per-test, so every
  test in the file — not just the two written for Task 1 — starts and ends with
  `_refresh()`'s cold-start guard already satisfied.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' `<action>` content, file
lists, and acceptance criteria matched what was implemented.

## TDD Gate Compliance

Task 2 carried `tdd="true"` but its `<files>` list names only `tests/test_api.py`
(no production source file), and its explicit prohibition forbids any further
change to `api/main.py` beyond Task 1's `_initial_state()` extraction. There was
no feature to drive into existence via RED→GREEN: `/api/solve`'s contract already
existed, unmodified, in production. All 17 new tests in Task 2 passed on first
run — this is expected and correct for a **characterization-testing** task (locking
down pre-existing, already-correct behavior), not a violation of the RED-first
rule, which exists to catch tests that pass vacuously against code that doesn't
exist yet. No RED or GREEN gate commits exist for Task 2 by design; Task 1 (which
did add the `_initial_state()` seam) has a single `feat` commit rather than a
test/feat pair, since the seam itself is a mechanical refactor with tests asserting
its consequences (not new business logic needing RED-first).

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `tests/conftest.py` and `tests/test_api.py` are now the established test base
  layer for the rest of Phase 1 — plan 01-03 extends `tests/test_api.py` with
  auth-stub (APIT-02) and concurrency (APIT-03) coverage using the same
  `_pool`-monkeypatch and autouse-reset patterns.
- Full pytest command for CI (Phase 5) confirmed:
  `/home/sraja/miniconda3/envs/python314/bin/python -m pytest` — 45 passed, 0 failed.
- **Human verification pending (deferred to end-of-phase per `workflow.human_verify_mode: end-of-phase`):**
  read the `api/main.py` diff (`git show 7313446 -- api/main.py`) and confirm it
  is a pure refactor with no behavioral change to `_refresh`, `_pool`,
  `_solve_cache`, or `CORSMiddleware`. This is the one failure mode this plan's
  own test suite cannot detect from inside itself.
- No blockers. Ready for 01-03.

---
*Phase: 01-test-base-layer-app-skeleton*
*Completed: 2026-08-31*

## Self-Check: PASSED

- FOUND: api/main.py
- FOUND: tests/conftest.py
- FOUND: tests/test_api.py
- FOUND commit: 7313446
- FOUND commit: dee426a
