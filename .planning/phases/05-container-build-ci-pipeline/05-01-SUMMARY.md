---
phase: 05-container-build-ci-pipeline
plan: 01
subsystem: infra
tags: [uv, ruff, pip, dependency-locking, lint, requirements]

# Dependency graph
requires: []
provides:
  - "requirements.in / requirements-dev.in — human-readable dependency sources (D-02 runtime/dev split)"
  - "requirements.txt / requirements-dev.txt — hash-verified compiled locks consumed by CI and the Dockerfile in 05-02/05-03"
  - "ruff.toml — Python lint configuration CI-01's lint step will invoke"
  - "understatapi==0.7.1 and pulp>=3.3,<4.0 pins carried forward into every later lock recompile"
affects: [05-02-container-build, 05-03-ci-workflow]

# Actuals (#2632)
actuals:
  tokens: 28718
  tasks: 3
  commits: 2

tech-stack:
  added: [uv==0.12.9 (dev-only lockfile compiler), ruff==0.16.6 (Python lint)]
  patterns:
    - "requirements.in (runtime) + requirements-dev.in (-r requirements.in + test/lint deps) split, compiled with uv --generate-hashes into hash-verified locks consumed via pip install --require-hashes"
    - "ruff.toml with an explicit select list (E4/E7/E9/F) and empty ignore, so the lint gate cannot silently change meaning as ruff's own defaults move"

key-files:
  created:
    - requirements.in
    - requirements-dev.in
    - requirements-dev.txt
    - ruff.toml
  modified:
    - requirements.txt
    - backtest/season.py
    - features/engineer.py
    - models/train.py
    - models/tune.py
    - optimize/chips.py
    - predict/export.py
    - tests/test_product.py

key-decisions:
  - "Human approved installing both [SUS]-verdict tools (uv==0.12.9, ruff==0.16.6) via the Task 1 blocking-human package-legitimacy checkpoint — verbatim answer: approve-both. Both pins re-verified against the live PyPI registry immediately before install with zero drift."
  - "uv installed into the conda python314 dev environment only, never added to either .in file (D-01) — it never enters CI's or the container's install path."
  - "ruff pinned in requirements-dev.in only, so it ships to CI's dev lock but not the runtime lock the Docker image installs."

patterns-established:
  - "Dependency lock compile-and-verify loop: uv pip compile --generate-hashes --python-version 3.14, then a from-scratch venv install with --require-hashes + full pytest run, before trusting the lock is committed."
  - "ruff findings are fixed at the source (no ignore-list suppressions) — multi-statement semicolon/colon lines split into real statements, unused imports removed, f-strings without placeholders de-f'd, lambda-assignment rewritten as def."

requirements-completed: [SEC-02, CI-01]

coverage:
  - id: D1
    description: "Hash-locked requirements.in/requirements-dev.in compiled and verified installable in a clean Python 3.14 venv, full existing pytest suite green"
    requirement: SEC-02
    verification:
      - kind: integration
        ref: "clean-venv pip install --require-hashes -r requirements.txt -r requirements-dev.txt && python -m pytest -q (77 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ruff.toml lint configuration added; ruff check . exits 0 across the tracked Python tree with no suppressions"
    requirement: CI-01
    verification:
      - kind: unit
        ref: "ruff check . (All checks passed!)"
        status: pass
    human_judgment: false

duration: ~10min
completed: 2026-09-04
status: complete
---

# Phase 5 Plan 1: Hash-Locked Dependencies & Lint Configuration Summary

**Compiled requirements.in/requirements-dev.in into hash-verified uv-generated locks (understatapi==0.7.1, pulp<4.0 pins), verified end-to-end in a clean Python 3.14 venv against the full 77-test suite, and drove `ruff check .` to zero findings via ruff.toml.**

## Performance

- **Duration:** ~10 min (continuation agent; Task 1's checkpoint had already been resolved by the user before this session started)
- **Completed:** 2026-09-04
- **Tasks:** 3 (1 checkpoint:decision, 1 tracer, 1 auto)
- **Files modified:** 12 (4 created, 8 modified)

## Accomplishments
- Split the loose `requirements.txt` into `requirements.in` (runtime) and `requirements-dev.in` (`-r requirements.in` + `responses`/`pytest`/`ruff`), pinning `understatapi==0.7.1` (drops the selenium/trio browser-automation chain the old floating `>=0.5` constraint pulled in) and `pulp>=3.3,<4.0` (PuLP 4.x removes the bundled CBC binary `PULP_CBC_CMD` depends on)
- Compiled both `.in` sources into hash-verified locks with `uv pip compile --generate-hashes --python-version 3.14`, `requirements-dev.txt` constrained against `requirements.txt` (`-c`) for byte-identical shared pins (verified: `pandas==3.0.5` identical in both)
- Proved the whole install path end to end: a from-scratch venv built from the conda `python314` interpreter (no inherited site-packages) installed both locks with `pip install --require-hashes`, zero source compilation, and the full existing pytest suite passed (77/77)
- Added `ruff.toml` (target-version `py314`, line-length 100, explicit `select = ["E4","E7","E9","F"]`, empty `ignore`) and fixed all 23 findings at the source with no behaviour change — verified by re-running the full pytest suite after the fixes (still 77 passed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Approve `uv`/`ruff` package-legitimacy checkpoint** — no commit (env-only conda install, no repository files changed)
2. **Task 2: End-to-end hash-locked clean environment runs the whole existing test suite** — `e1a3f3e` (feat)
3. **Task 3: Add ruff.toml and drive `ruff check .` to zero findings** — `82177e7` (feat)

_Note: Task 1 is a checkpoint:decision task with no file output of its own — the approved packages were installed into the dev conda environment only._

## Files Created/Modified
- `requirements.in` - New: runtime dependency source, `understatapi==0.7.1` and `pulp>=3.3,<4.0` pins
- `requirements-dev.in` - New: `-r requirements.in` plus `responses`, `pytest>=8`, `ruff==0.16.6`
- `requirements.txt` - Regenerated: hash-verified compiled runtime lock (was loose `>=` constraints)
- `requirements-dev.txt` - New: hash-verified compiled dev/CI lock
- `ruff.toml` - New: Python lint configuration for CI-01's lint step
- `backtest/season.py` - Split 2 semicolon-joined statement lines (E702) into real statements
- `features/engineer.py` - Removed unused `numpy` import (F401), de-f'd a placeholder-free f-string (F541)
- `models/train.py` - De-f'd a placeholder-free f-string (F541)
- `models/tune.py` - Removed unused `numpy` import (F401)
- `optimize/chips.py` - Split 3 semicolon-joined statement lines (E702) into real statements
- `predict/export.py` - Split 5 lines mixing E701 (colon) and E702 (semicolon) compound statements into real statement blocks
- `tests/test_product.py` - Removed unused `pytest` import (F401), rewrote a `lambda`-assignment as a `def` (E731)

## Decisions Made
- Human approved installing both `[SUS]`-verdict tools (`uv==0.12.9`, `ruff==0.16.6`) via the Task 1 blocking-human package-legitimacy checkpoint — verbatim answer: "approve-both". Both pins re-verified against the live PyPI registry immediately before install (`pypi.org/pypi/uv/json` and `pypi.org/pypi/ruff/json`) with zero drift — each was confirmed the current latest release.
- `uv` installed into the conda `python314` dev environment only, deliberately excluded from both `.in` files per D-01 (lockfile compiler, never a runtime or CI dependency).
- `-c requirements.txt` alongside `--generate-hashes` worked without needing the plan's documented fallback (drop `-c`, rely on same-session resolution) — the shared-pin parity gate confirmed byte-identical `pandas==3.0.5` in both locks on the first attempt.

## Deviations from Plan

None - plan executed exactly as written. All 23 ruff findings were fixed via the plan's own prescribed method (delete dead code / correct invalid constructs, no ignore-list suppressions, no fix that changes a function's inputs/outputs/control flow) — these are Task 3's designated action, not unplanned deviations.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `requirements.txt` / `requirements-dev.txt` are ready to be the exact files 05-02's Dockerfile builder stage and 05-03's `ci.yml` install from with `pip install --require-hashes`
- `ruff.toml` is ready for 05-03's `ci.yml` lint step (`ruff check .`)
- No blockers for 05-02/05-03

---
*Phase: 05-container-build-ci-pipeline*
*Completed: 2026-09-04*

## Self-Check: PASSED

All created files verified present on disk (`requirements.in`, `requirements-dev.in`, `requirements.txt`, `requirements-dev.txt`, `ruff.toml`); both task commits (`e1a3f3e`, `82177e7`) verified present in `git log`.
