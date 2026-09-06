---
phase: 06-security-reliability-observability-hardening
plan: 07
subsystem: api
tags: [fastapi, concurrency, caching, toctou, ast, reliability]

# Dependency graph
requires:
  - phase: 06-04
    provides: "the bounded LRU/TTL solve cache, the monotonic pool_version counter, and the two-lock-acquisition shape (_pool()/_gw_pools() plus a separate solve()/plan() version read) that this plan closes"
  - phase: 06-06
    provides: "the clean 166-passed/1-skipped, ruff-clean baseline this plan's precondition checks against"
provides:
  - "PoolSnapshot/GwPoolsSnapshot NamedTuples carrying (pool[s], gw, boot, version) as one value from one critical section"
  - "_pool() and the rewritten _gw_pools_meta() reading the pool/pools, gameweek, bootstrap payload and pool_version inside ONE lock acquisition each"
  - "_gw_pools_locked() (renamed from _gw_pools, lock acquisition removed) running inside _gw_pools_meta()'s single critical section"
  - "team()/solve()/rate()/plan() holding no lock and touching no shared state dict -- solve()/plan()'s second, separate pool_version read deleted"
  - "A deterministic, stub-free regression test driving the real _pool()/_refresh() interleaving, proven non-vacuous by a control, plus the multi-gameweek analogue and a syntax-tree structural gate against regression"
affects: [any-future-plan-touching-api/main.py, 07-cutover]

actuals:
  tokens: 6255
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Atomic snapshot pattern: a NamedTuple (PoolSnapshot/GwPoolsSnapshot) carries every field a caller needs from one critical section, so a version can never be paired with a separately-read sibling field"
    - "Deterministic race reproduction: a lock wrapper (_WindowLock) whose __exit__ fires an injected side-effect at the exact instant a lock is released -- no sleep, no thread, no scheduling dependency -- reproducing a TOCTOU window on demand"
    - "Syntax-tree structural gate: parse inspect.getsource(module) with ast, assert on the parsed tree rather than raw text, so the gate is immune to anything written in a comment or docstring"

key-files:
  created: []
  modified:
    - api/main.py
    - tests/test_api_hardening.py
    - tests/test_api.py
    - tests/test_obs.py
    - tests/test_product.py

key-decisions:
  - "Reversed 06-04's own recorded decision to read pool_version under a separate, later `with _lock` block inside solve()/plan() -- that shape was exactly the TOCTOU defect 06-VERIFICATION.md recorded against REL-05, and 06-04-SUMMARY.md's own key-decisions text names it verbatim as the thing this plan undoes."
  - "_gw_pools renamed to _gw_pools_locked with its own lock acquisition removed, rather than making it reentrant-safe some other way -- threading.Lock is not reentrant, and _gw_pools_meta now needs to hold the lock across both the per-gameweek build loop and the gameweek/bootstrap/version reads, so the callee cannot take the lock itself."
  - "Split Tasks 2 and 3 into two commits despite writing both in one editing pass, to keep each commit's diff matching its own task's <files>/import list (threading only for Task 2; ast+inspect added in Task 3) and its own <verify> block's expected pass counts (168 then 170)."
  - "Empirically confirmed the Task 2 gate's pre-fix failure by creating a detached git worktree at the pre-Task-1 commit and running the new test against it there, rather than asserting the failure message from code-reading alone -- observed the exact predicted 'STALE PAYLOAD SERVED AFTER A REFRESH: [\"G0-1001\", \"G0-1002\", ...]' message, then removed the worktree."

requirements-completed: [REL-05]

coverage:
  - id: D1
    description: "_pool()/_gw_pools_meta() return one atomic (pool[s], gw, boot, pool_version) snapshot from a single critical section; the four handlers hold no lock and touch no shared state dict"
    requirement: "REL-05"
    verification:
      - kind: unit
        ref: "inline AST/attribute checks in Task 1's <verify> block (PoolSnapshot/GwPoolsSnapshot field shape, _gw_pools_locked presence, one-lock-per-helper census, zero-lock/zero-subscript handler census)"
        status: pass
      - kind: unit
        ref: "tests/test_api_hardening.py::test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict"
        status: pass
      - kind: integration
        ref: "tests/test_fixture_mode.py::test_plan_endpoint_returns_horizon_weeks (exercises the rewritten _gw_pools_meta end to end)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A deterministic, stub-free regression test drives the real _pool()/_refresh() interleaving and fails against the pre-fix implementation by serving a stale payload; a control proves the timing hook is non-vacuous"
    requirement: "REL-05"
    verification:
      - kind: unit
        ref: "tests/test_api_hardening.py::test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key"
        status: pass
      - kind: unit
        ref: "tests/test_api_hardening.py::test_the_window_hook_opens_a_real_gap_for_a_two_acquisition_reader"
        status: pass
    human_judgment: false
  - id: D3
    description: "The /api/plan path has the same atomicity proof as /api/solve, and the two-acquisition shape cannot silently return anywhere in the four handlers"
    requirement: "REL-05"
    verification:
      - kind: unit
        ref: "tests/test_api_hardening.py::test_gw_pools_meta_returns_the_version_its_pools_were_built_under"
        status: pass
      - kind: unit
        ref: "tests/test_api_hardening.py::test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-09-06
status: complete
---

# Phase 6 Plan 07: REL-05 TOCTOU Gap Closure Summary

**Closed the REL-05 cache-invalidation race by making `_pool()`/`_gw_pools_meta()` return the pool and the `pool_version` it was built under as one `NamedTuple` from a single critical section, then proved it with the first regression test in this repository to drive the real `_pool()`/`_refresh()` interleaving instead of a version-independent stub.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-09-06T09:45:00Z (approx.)
- **Completed:** 2026-09-06T10:20:00Z
- **Tasks:** 3
- **Files modified:** 5 (api/main.py, tests/test_api_hardening.py, tests/test_api.py, tests/test_obs.py, tests/test_product.py)

## Accomplishments

- **Task 1 — atomic snapshot.** Added `PoolSnapshot(pool, gw, boot, version)` and `GwPoolsSnapshot(pools, gw, boot, version)` `NamedTuple`s. `_pool()` now reads the pool AND `_state["pool_version"]` inside its one existing locked block and returns both as a `PoolSnapshot`. `_gw_pools` was renamed `_gw_pools_locked` with its own lock acquisition removed (`threading.Lock` is not reentrant), and now runs entirely inside a new single critical section owned by the rewritten `_gw_pools_meta()`, which also pulls the previously-**unlocked** gameweek and bootstrap reads inside that same block for the first time. `team()`, `solve()`, `rate()` and `plan()` now bind one snapshot each via attribute access; `solve()`'s and `plan()`'s second, separate `with _lock: pool_version = _state["pool_version"]` block — the exact shape 06-04-SUMMARY.md recorded choosing and 06-VERIFICATION.md later flagged as the REL-05 gap — is deleted. Fourteen test stubs across four test modules (ten lambdas + one `slow_pool` in `tests/test_api.py`, one lambda each in `tests/test_obs.py`/`tests/test_product.py`, one `slow_pool` in `tests/test_api_hardening.py`) were updated to return four-field `PoolSnapshot` instances; no other line in those tests changed.
- **Task 2 — stub-free race proof.** Added `_WindowLock`, a real-`threading.Lock` wrapper whose `__exit__` releases the lock and then fires an injected callback at the exact instant a two-acquisition reader's window used to open — deterministic, no sleep, no thread. `_install_race_window` patches only `_load_live` (a generation-tagged loader), `_intervals_artifact` (machine-independent) and `_lock`, never the code paths under test. `test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key` posts the same `/api/solve` body twice with a refresh injected in the window between the two requests, asserting the first response is generation 0 and the second is generation 1 — proving no stale payload survives under a post-refresh cache key. `test_the_window_hook_opens_a_real_gap_for_a_two_acquisition_reader` is the non-vacuity control: it deliberately reproduces the OLD two-acquisition read shape and asserts it really does observe a version bump and a different bootstrap object, so a green gate above means the race is closed, not that the window never opened.
- **Task 3 — multi-gameweek proof and the durable gate.** `test_gw_pools_meta_returns_the_version_its_pools_were_built_under` is the `/api/plan`-path analogue: it monkeypatches `_gw_pool` (the per-gameweek builder, never `_gw_pools_locked`/`_gw_pools_meta`), forces a generation-0 load, then asserts `_gw_pools_meta(2)`'s snapshot carries two generation-0 pools, a version exactly one less than the state dict's post-refresh version, and a distinct bootstrap object. `test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict` parses `api/main.py`'s syntax tree (never source text) and asserts `team`/`solve`/`rate`/`plan` hold no lock and subscript no shared state, plus the critical-section census (`_pool`==1, `_gw_pools_meta`==1, `_gw_pools_locked`==0) — the structural backstop that makes the two-acquisition shape impossible to silently re-introduce.

## Task Commits

1. **Task 1: End-to-end atomic (pool, version) snapshot** - `aae7503` (fix)
2. **Task 2: The stub-free race proof** - `4932b84` (test)
3. **Task 3: Multi-gameweek atomicity proof and the AST gate** - `c0b4f7a` (test)

**Plan metadata:** committed with this SUMMARY.

## Files Created/Modified

- `api/main.py` — `PoolSnapshot`/`GwPoolsSnapshot` `NamedTuple`s; `_pool()` returns a `PoolSnapshot`; `_gw_pools` renamed to `_gw_pools_locked` (lock removed); `_gw_pools_meta()` rewritten to own one critical section; `team()`/`solve()`/`rate()`/`plan()` use attribute access, second lock block deleted
- `tests/test_api_hardening.py` — `_WindowLock`, `_install_race_window`, `_arming_pool_builder`, and four new tests (the stub-free gate, its non-vacuity control, the multi-gameweek atomicity proof, the AST structural gate); one pre-existing `slow_pool` stub updated to the new snapshot shape
- `tests/test_api.py` — ten lambda stubs plus one `slow_pool` updated to return `PoolSnapshot`
- `tests/test_obs.py`, `tests/test_product.py` — one lambda stub each updated to return `PoolSnapshot`

## Decisions Made

See `key-decisions` in frontmatter.

## Deviations from Plan

None - plan executed exactly as written. The one notable extra step — creating a detached git worktree at the pre-Task-1 commit to empirically confirm the Task 2 gate's predicted pre-fix failure message — was explicitly called for by the plan's own acceptance criteria ("SUMMARY.md records the pre-fix failure this gate reproduces, quoting the observed stale-generation assertion message"), not an unplanned addition.

## Empirical Pre-Fix Reproduction

Before writing this summary, the Task 2 gate (`test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key`) plus its supporting hook/helpers were copied into a scratch `git worktree` checked out at `21cb2b9` (the commit immediately before this plan's Task 1 fix) and run there in isolation. It failed exactly as the plan predicted:

```
AssertionError: STALE PAYLOAD SERVED AFTER A REFRESH: ['G0-1001', 'G0-1002', 'G0-1005', 'G0-1006', 'G0-1007', 'G0-1008', 'G0-1010', 'G0-1011', 'G0-1013', 'G0-1015', 'G0-1016', 'G0-1017', 'G0-1018', 'G0-1019', 'G0-1020']
```

The worktree was removed immediately afterward (`git worktree remove --force`); no commit in this plan's history touches that state.

## Issues Encountered

None.

## User Setup Required

None — no new environment variables, no dependency changes (`git diff --quiet -- requirements.txt requirements-dev.txt requirements.in requirements-dev.in` confirmed byte-identical locks throughout).

## Known Stubs

None. This plan only changed the *return shape* of fourteen pre-existing test stubs (three-value tuple to four-field `PoolSnapshot`); it introduced no new stub, mock, or hardcoded empty value anywhere in production code.

## Next Phase Readiness

REL-05 is now structurally closed: the atomic-pair guarantee is enforced by a syntax-tree gate (`test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict`), not merely documented, and a deterministic regression test proves the race itself is closed rather than merely that a version bump between two separate requests invalidates correctly. Full suite: `170 passed, 1 skipped`. `ruff check .`: `All checks passed!`. `bash scripts/preflight.sh`: `PREFLIGHT PASSED`.

Per the plan's own "Flagged assumptions" section, REL-05's must-have text carried no auto-derivable acceptance criterion in the edge-probe report — the concrete criteria were authored directly into this plan's `must_haves.truths` from `06-VERIFICATION.md`'s gap block instead. All of them are now satisfied by the tests above; REL-05's residual surface (if any) should still be confirmed at end-of-phase UAT per the plan's own note, alongside the two carried-forward human-verification items from `06-VERIFICATION.md` (live-browser CORS check; cron install + webhook confirmation) that this plan did not touch.

No new security-relevant surface was introduced (no new endpoint, auth path, file access pattern, or schema change) — this plan's entire diff is two private return types, one lock-scope refactor, and four test functions in an existing module.

---
*Phase: 06-security-reliability-observability-hardening*
*Completed: 2026-09-06*
