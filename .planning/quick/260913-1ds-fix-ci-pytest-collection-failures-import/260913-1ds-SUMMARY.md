---
phase: quick
plan: 260913-1ds
subsystem: tests
tags: [ci, pytest, collection, gymnasium, torch, rl, bracket]
dependency-graph:
  requires: []
  provides: ["clean pytest collection under CI (no gymnasium/torch/sb3_contrib installed)"]
  affects: [tests/test_rl_env.py, tests/test_bracket.py, tests/test_bracket_deep.py]
tech-stack:
  added: []
  patterns: ["module-level pytest.importorskip before first import of an optional dev-only package, with # noqa: E402 on every import that follows"]
key-files:
  created:
    - tests/test_bracket_deep.py
    - .planning/quick/260913-1ds-fix-ci-pytest-collection-failures-import/deferred-items.md
  modified:
    - tests/test_rl_env.py
    - tests/test_bracket.py
decisions:
  - "Real split boundary in tests/test_bracket.py corrected to line 339 (banner) / line 342 (import torch), not the briefed line 375 -- the briefed line would have left the collection crash unfixed."
  - "Fixed the CI-sim blocker script (scratchpad, not a plan-scoped file) to raise ModuleNotFoundError instead of plain ImportError -- pytest 9.1's pytest.importorskip() defaults to catching only ModuleNotFoundError, and a genuinely-uninstalled package always raises ModuleNotFoundError (a subclass of ImportError) in real CI, so this makes the simulation match reality rather than working around a real gap."
  - "Pre-existing ruff F401 failures in tests/test_ci_cd_artifacts.py (unrelated to this plan, confirmed present at HEAD~2) logged as a deferred item and to WINDOWS.md (entry 7), not fixed -- out of this plan's three-file scope guard."
actuals:
  tokens: 6271
  tasks: 2
  commits: 2
status: complete
---

# Quick Task 260913-1ds: Fix CI pytest collection failures (import guards) Summary

Guarded `tests/test_rl_env.py` and split the torch region of `tests/test_bracket.py` into a new `tests/test_bracket_deep.py`, so pytest collection in CI (no gymnasium/torch/stable_baselines3/sb3_contrib installed, per Phase 9 decision D-09) no longer crashes the entire suite -- while all 16 torch-free bracket tests and all 9 rl_env tests keep running exactly as before wherever those packages ARE installed.

## Accomplishments

- **Task 1:** Added a module-level `pytest.importorskip("gymnasium")` to `tests/test_rl_env.py` before the first `gymnasium`/`optimize.rl_env` import, with `# noqa: E402` on every import that now follows the guard. CI (gymnasium absent) skips this module cleanly; locally (gymnasium installed) all 9 tests still pass, unchanged.
- **Task 2:** Split `tests/test_bracket.py` at the real torch boundary (line 339 banner / line 342 `import torch`, corrected from the plan brief's line 375) into:
  - `tests/test_bracket.py` — 16 torch-free tests, unchanged behavior, no module-level guard (so these keep running in CI).
  - `tests/test_bracket_deep.py` (new) — 10 torch-dependent tests behind a module-level `pytest.importorskip("torch")`, with its own `needs_data`/`df_full` fixtures re-established (not shared via conftest.py).
- Discovered and fixed a pytest-9.1-specific quirk in the CI simulation blocker script itself (`/tmp/.../scratchpad/block_rl.py`, not a plan-scoped file): `pytest.importorskip()` in pytest 9.1 defaults to catching only `ModuleNotFoundError`, not generic `ImportError`. The blocker's meta-path finder was raising plain `ImportError`, which real CI never produces (an absent package always raises `ModuleNotFoundError`, a subclass) -- changed the blocker to raise `ModuleNotFoundError` so the simulation matches real CI behavior.
- Logged a pre-existing, out-of-scope ruff F401 failure in `tests/test_ci_cd_artifacts.py` (3 unused imports: `pathlib`, `shutil`, `typing.Any`) to `deferred-items.md` and `WINDOWS.md` (entry 7) rather than fixing it -- confirmed present before this plan's commits and outside the plan's three-file scope guard.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Guard tests/test_rl_env.py behind gymnasium importorskip | `0d1934d` | tests/test_rl_env.py |
| 2 | Split torch region of tests/test_bracket.py into tests/test_bracket_deep.py | `6ab7716` | tests/test_bracket.py, tests/test_bracket_deep.py |

## Files Created

- `tests/test_bracket_deep.py` — the 10 torch-dependent bracket tests, guarded by `pytest.importorskip("torch")`.
- `.planning/quick/260913-1ds-fix-ci-pytest-collection-failures-import/deferred-items.md` — records the out-of-scope `tests/test_ci_cd_artifacts.py` ruff finding.

## Files Modified

- `tests/test_rl_env.py` — module-level `pytest.importorskip("gymnasium")` guard added before the gymnasium/optimize.rl_env imports.
- `tests/test_bracket.py` — torch region (former lines 339-559) removed; file now ends after `test_gate_records_the_in_sample_eval_split_label`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking issue] Fixed the CI-sim blocker script's exception type**
- **Found during:** Task 1 verification (Direction A CI simulation)
- **Issue:** The plan's own precondition-recreated blocker script raises plain `ImportError`. Under pytest 9.1.1 (installed in this env), `pytest.importorskip(modname)` defaults `exc_type` to `ModuleNotFoundError` only (a 9.1 behavior change), so it does NOT catch a plain `ImportError` -- the module-level guard added in Task 1 failed to suppress the simulated block, still showing as a collection error.
- **Fix:** Changed the blocker's `raise ImportError(...)` to `raise ModuleNotFoundError(...)` in `/tmp/claude-1000/-home-sraja-fpl/66e20341-54a2-459c-9b04-51955799196e/scratchpad/block_rl.py` (a local verification tool, not a repo file). This is not a workaround -- a package that is genuinely absent from the environment always raises `ModuleNotFoundError` in real CI, so the fix makes the simulation accurately model reality rather than papering over a gap in the actual fix.
- **Files modified:** none in the repo (scratchpad-only).
- **Verified:** Direction A re-run after the fix produced `409 tests collected` with zero `ERROR`/`Interrupted`/`errors in` lines.

### Deferred (Out of Scope)

**1. [Deferred] Pre-existing ruff F401 in tests/test_ci_cd_artifacts.py**
- **Found during:** Direction C verification (`ruff check .`)
- **Issue:** 3 unused imports (`pathlib`, `shutil`, `typing.Any`) fail ruff's F401 check. Confirmed pre-existing via `git show HEAD~2:tests/test_ci_cd_artifacts.py | ruff check -` — identical 3 errors present before this plan's commits.
- **Impact:** `.github/workflows/ci.yml`'s lint job runs bare `ruff check .`, so this file was already failing CI's lint gate independent of this plan.
- **Not fixed:** Outside this plan's three-file scope guard (`tests/test_rl_env.py`, `tests/test_bracket.py`, `tests/test_bracket_deep.py` only). Logged to `deferred-items.md` and `WINDOWS.md` entry 7 for a future task.

## Verification

**Direction A — CI simulation (packages ABSENT), final run:**
```
409 tests collected in 0.81s
```
Zero `ERROR tests/...` lines, zero `Interrupted`, zero `errors in` summary suffix. (Before the fix: `393 tests collected, 2 errors`.)

**Direction B — real local run (packages PRESENT):**
```
427 passed, 1 skipped, 1250 warnings in 307.96s (0:05:07)
```
Matches the pre-change baseline exactly (`427 passed, 1 skipped`) -- zero new skips, zero dropped/duplicated tests.

**Direction C — lint gate on the three in-scope files:**
```
$ ruff check tests/test_rl_env.py tests/test_bracket.py tests/test_bracket_deep.py
All checks passed!
```
(Whole-repo `ruff check .` reports 3 pre-existing F401 errors in the unrelated, out-of-scope `tests/test_ci_cd_artifacts.py` -- see Deferred section above. These predate this plan.)

**Per-task collection counts:**
```
tests/test_rl_env.py -q                        -> 9 passed
tests/test_bracket.py --collect-only -q        -> 16 tests collected
tests/test_bracket_deep.py --collect-only -q   -> 10 tests collected
```

**Scope guard:**
```
$ git status --porcelain -- tests/
 M tests/test_bracket.py
A  tests/test_bracket_deep.py
 M tests/test_rl_env.py   (already committed in Task 1)
```
Only the three plan-named files under `tests/` were modified/added.

## Self-Check: PASSED

- FOUND: tests/test_rl_env.py (modified, guard present)
- FOUND: tests/test_bracket.py (torch region removed)
- FOUND: tests/test_bracket_deep.py (created, 10 tests)
- FOUND: commit 0d1934d (`git log --oneline --all | grep 0d1934d`)
- FOUND: commit 6ab7716 (`git log --oneline --all | grep 6ab7716`)
