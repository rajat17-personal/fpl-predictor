---
phase: 06-security-reliability-observability-hardening
plan: 06
subsystem: testing
tags: [ruff, lint, ci, pytest, ci-01, cr-01, fixture-capture]

# Dependency graph
requires:
  - phase: 06-security-reliability-observability-hardening
    provides: "06-02's ops.jsonio bare-file-handle migration and tests/test_reliability.py's self-tested repository-wide scanner, which this plan extends"
  - phase: 06-security-reliability-observability-hardening
    provides: "06-05's preflight.sh Gate 2/8 (ruff check .) and Gate 7/8 hardening gates, whose file-scope this plan corrects"
provides:
  - "e2e/scripts/capture_fixtures.py's fixture-capture path is no longer a NameError on its default (non---verify) invocation"
  - "ruff.toml's exclude list is subtree-scoped, bringing all 54 (now 55) tracked Python files inside the CI lint gate and preflight Gate 2/8"
  - "a self-tested lint-coverage gate (tests/test_reliability.py) that turns the suite red and names the file if a future blanket exclude entry re-hides tracked source"
  - "a ruff-independent runtime-object gate (tests/test_capture_fixtures.py) that catches an undefined global on the capture path even if the lint configuration is later loosened"
affects: [lint, ci, e2e, fixture-capture, data-ingest]

# Actuals (#2632)
actuals:
  tokens: 2811
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ruff.toml exclusions are subtree-scoped (data/raw, data/snapshots, e2e/fixtures, etc.), never whole source directories, so `ruff check .` genuinely covers all tracked Python source"
    - "Lint-coverage gates are self-tested with paired positive/negative controls: one control proves the underlying rule detects the defect class (F821), a second proves the coverage gate itself reads a real exclusion rather than a hardcoded constant"
    - "A CLI script that lives outside any Python package (e2e/scripts/, no __init__.py) is exercised from pytest by loading it via importlib.util.spec_from_file_location rather than an import statement"

key-files:
  created:
    - tests/test_capture_fixtures.py
  modified:
    - e2e/scripts/capture_fixtures.py
    - ruff.toml
    - data/ingest.py
    - tests/test_reliability.py

key-decisions:
  - "Positive/negative control synthetic modules for the F821 rule mirror the actual CR-01 defect shape (a used-but-never-imported `json` name) rather than a generic undefined-name example, for maximum fidelity to the regression being guarded against."
  - "Used a module-level `functools.lru_cache`-wrapped loader (not a pytest fixture) to load capture_fixtures.py by path once per session — the module import pulls in predict.live, which is not free, and this matches the plan's explicitly offered alternative."
  - "The plan's own acceptance criteria claims capture_fixtures.py has 'five `# noqa: E402` comments'; the file has and always had four (config, ops.jsonio, predict.export, predict.live). Left as an inherited plan miscount rather than adding a fabricated fifth comment — the criterion's real intent (the noqa comments are unchanged by this plan) is satisfied and verified directly."

patterns-established:
  - "Repository-wide lint/test gates in this project pair every scanner with positive and negative control tests (established in 06-02, extended here to ruff-based gates) so a gate can never silently stop detecting the defect class it exists for."

requirements-completed: [REL-01, REL-04]

coverage:
  - id: D1
    description: "e2e/scripts/capture_fixtures.py's missing `import json` is restored and ruff.toml's exclude list is narrowed to subtrees, bringing all tracked Python files (including the previously-hidden data/*.py and e2e/scripts/capture_fixtures.py) inside the CI lint gate"
    requirement: REL-01
    verification:
      - kind: integration
        ref: "ruff check --no-cache e2e/scripts/capture_fixtures.py (no F821)"
        status: pass
      - kind: integration
        ref: "ruff check . (All checks passed!)"
        status: pass
      - kind: integration
        ref: "ruff check --show-files . filtered to .py == git ls-files '*.py'"
        status: pass
    human_judgment: false
  - id: D2
    description: "Self-tested lint-coverage gate in tests/test_reliability.py: a future blanket ruff.toml exclude entry turns the suite red and names the hidden file, rather than silently re-opening the blind spot"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "tests/test_reliability.py#test_ruff_check_covers_every_tracked_python_file"
        status: pass
      - kind: unit
        ref: "tests/test_reliability.py#test_coverage_gate_notices_a_reinstated_blanket_exclude"
        status: pass
      - kind: unit
        ref: "tests/test_reliability.py#test_ruff_detects_an_undefined_name"
        status: pass
      - kind: unit
        ref: "tests/test_reliability.py#test_ruff_reports_nothing_for_a_clean_module"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/test_capture_fixtures.py exercises the capture script from pytest for the first time: module import, read-only --verify CLI path, and a ruff-independent undefined-global check on the capture path, all without writing into the frozen v1 fixture set"
    requirement: REL-04
    verification:
      - kind: unit
        ref: "tests/test_capture_fixtures.py#test_capture_fixtures_module_imports"
        status: pass
      - kind: unit
        ref: "tests/test_capture_fixtures.py#test_capture_path_loads_no_undefined_global"
        status: pass
      - kind: integration
        ref: "tests/test_capture_fixtures.py#test_verify_path_returns_zero"
        status: pass
      - kind: unit
        ref: "tests/test_capture_fixtures.py#test_the_gates_leave_the_frozen_fixture_set_untouched"
        status: pass
    human_judgment: false

# Metrics
duration: 8min
completed: 2026-09-06
status: complete
---

# Phase 06 Plan 06: Gap-Closure — CR-01 Fixture-Capture NameError and the Lint Blind Spot Summary

**Restored `capture_fixtures.py`'s missing `import json`, narrowed `ruff.toml`'s exclusions from whole directories to regenerable subtrees so `ruff check .` now covers all tracked Python source, and added two independent regression gates (a self-tested lint-coverage test and a ruff-independent runtime-object test) so this defect class cannot silently ship again.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-09-06T05:03:00Z (approx)
- **Completed:** 2026-09-06T05:11:38Z
- **Tasks:** 3
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- Restored `import json` in `e2e/scripts/capture_fixtures.py`, fixing the `NameError` on the fixture-capture tool's default (non-`--verify`) action — CR-01 closed at the source.
- Narrowed `ruff.toml`'s `data` and `e2e` blanket exclusions to 13 subtree-scoped entries (`data/raw`, `data/processed`, `data/snapshots`, `e2e/node_modules`, `e2e/fixtures`, `e2e/playwright-report`, `e2e/test-results`, plus the six untouched originals). `ruff check .` now inspects all 55 tracked Python files (54 pre-plan, plus this plan's own new test module) — 10 files that were previously invisible to CI's lint step and preflight Gate 2/8 are now covered.
- Removed the one finding the narrowed exclusion surfaced outside CR-01 itself: a dead module-level `import json` in `data/ingest.py`, unused since Phase 01.
- Added a self-tested lint-coverage gate to `tests/test_reliability.py` (`_ruff`/`_ruff_inspected_python_files` helpers plus 4 new tests) that asserts ruff's inspected file set exactly equals `git ls-files '*.py'`, with paired positive/negative controls proving the rule detects an undefined name and the gate detects a real re-exclusion.
- Added `tests/test_capture_fixtures.py`, a ruff-independent behavioural gate that loads the script by file path, walks its `LOAD_GLOBAL` opcodes to prove no undefined global remains, and exercises its `--verify` CLI path — all without ever calling `_capture` or touching the immutable v1 fixture set.

## Task Commits

Each task was committed atomically:

1. **Task 1: Restore the import and narrow the lint gate to cover every tracked Python file** - `5a093d7` (fix)
2. **Task 2: Self-tested lint-coverage gate in tests/test_reliability.py** - `b67904c` (test)
3. **Task 3: tests/test_capture_fixtures.py — exercise the capture script and its globals from pytest** - `4f5da63` (test)

**Plan metadata:** (this commit, immediately following)

## Files Created/Modified

- `e2e/scripts/capture_fixtures.py` - Restored `import json` in the stdlib import block
- `ruff.toml` - Replaced `data`/`e2e` blanket exclusions with 13 subtree-scoped entries; updated header comment
- `data/ingest.py` - Removed dead module-level `import json` (unused since Phase 01)
- `tests/test_reliability.py` - Added `_ruff`/`_ruff_inspected_python_files` helpers and 4 tests (lint-coverage gate + controls)
- `tests/test_capture_fixtures.py` - New: 4 tests exercising `capture_fixtures.py`'s import, undefined-global check, `--verify` path, and fixture-immutability

## Decisions Made

- Synthetic control modules for the F821 rule mirror the actual CR-01 defect shape (a used-but-never-imported `json` name) rather than a generic example, for direct fidelity to the regression being guarded against.
- Used a module-level `functools.lru_cache`-wrapped loader rather than a pytest fixture to load `capture_fixtures.py` by path once per session, per the plan's own offered alternative.
- The plan's acceptance criteria state capture_fixtures.py has "five `# noqa: E402` comments"; the file has (and always had) four. Documented as an inherited plan miscount rather than fabricating a fifth comment — the substantive requirement (comments unchanged by this plan) is met and directly verified.

## Deviations from Plan

None - plan executed exactly as written. The one discrepancy noted above (four vs. the plan's stated five `# noqa: E402` comments) is a pre-existing fact about the file, not a deviation in what was built — logged under Decisions Made rather than as a Rule 1-4 deviation since no code or test behavior depended on the number being five.

## Issues Encountered

- Task 3's initial full-suite run flagged `test_ruff_check_covers_every_tracked_python_file` as failing because the newly-created `tests/test_capture_fixtures.py` was on disk but not yet `git add`-ed, so `git ls-files '*.py'` (used by the coverage gate) didn't see it while ruff did. Resolved by staging the file before re-running — expected behavior of the gate working correctly, not a bug in the gate.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-01 is closed at the source, and the lint gate that missed it now covers every tracked Python file with a self-tested regression gate preventing silent regression.
- All plan-level `<verification>` checks pass: `ruff check .` (All checks passed!), full pytest suite (166 passed, 1 skipped — the plan's exact predicted total), `bash scripts/preflight.sh` (PREFLIGHT PASSED), fixture set untouched, hash-locked requirements untouched, `.github/workflows/ci.yml`/`scripts/preflight.sh` untouched.
- Phase 06 is now fully verified with all identified gaps (CR-01) closed. Ready for `/gsd-verify-work 06` or advancing to the next phase.

## Self-Check: PASSED

- FOUND: tests/test_capture_fixtures.py
- FOUND: tests/test_reliability.py
- FOUND: ruff.toml
- FOUND: e2e/scripts/capture_fixtures.py
- FOUND: data/ingest.py
- FOUND commit: 5a093d7
- FOUND commit: b67904c
- FOUND commit: 4f5da63
- Re-ran all plan-level `<verification>` commands: all pass (ruff check ., pytest -q => 166 passed/1 skipped, tests/test_reliability.py => 9 passed, tests/test_capture_fixtures.py => 4 passed, no bare noqa suppressions, e2e/fixtures untouched, requirements locks untouched, preflight.sh => PREFLIGHT PASSED)

---
*Phase: 06-security-reliability-observability-hardening*
*Completed: 2026-09-06*
