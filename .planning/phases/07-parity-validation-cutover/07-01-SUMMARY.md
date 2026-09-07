---
phase: 07-parity-validation-cutover
plan: 01
subsystem: infra
tags: [fastapi, starlette, uvicorn, playwright, docker, ci, react]

# Dependency graph
requires:
  - phase: 04-e2e-regression-suite
    provides: the FPL_FIXTURE_DIR mount-split pattern in api/main.py and the
      installed @playwright/test@1.62.1 toolchain this plan reuses unmodified
  - phase: 05-container-build-ci-pipeline
    provides: the multi-stage Docker image, scripts/smoke_test.sh, and the
      chained ci.yml image job this plan extends
provides:
  - "FPL_FRONTEND=react production serving branch in api/main.py (D-01)"
  - "scripts/dual_site.sh -- on-demand two-uvicorn start/stop/status runner (D-03)"
  - "e2e/parity/parity-diff.mjs -- cross-origin live-data xP-table comparison CLI (D-05)"
  - "tests/test_react_seam.py -- mount-branch coverage for all three serving modes"
  - "react-mode container smoke assertion wired into the CI image job (D-04)"
affects: [07-02, 07-03, 07-04, 07-05, 07-06]

actuals:
  tokens: 6503
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Third sibling mount branch (elif _REACT_MODE) added beside the untouched
      _FIXTURE_ROOT branch in api/main.py's env-seam + mount-split shape,
      never folded together -- the two seams compose independently."
    - "Loopback-only, on-demand process pair (scripts/dual_site.sh) with a
      refuse-on-foreign-port guard, mirroring scripts/verify_hardening.sh's
      boot-a-real-uvicorn-and-poll shape."
    - "Live-data comparison CLI guards freshness by byte-comparing
      /data/meta.json across both origins and the on-disk export before
      trusting any page content -- the anti-spoofing gate for a
      same-live-instant comparison."

key-files:
  created:
    - scripts/dual_site.sh
    - e2e/parity/parity-diff.mjs
    - tests/test_react_seam.py
  modified:
    - api/main.py
    - scripts/smoke_test.sh
    - .github/workflows/ci.yml
    - .gitignore

key-decisions:
  - "Verified scripts/dual_site.sh's happy path (start/parity-diff/stop) with
    DUAL_SITE_VANILLA_PORT=8010/DUAL_SITE_REACT_PORT=8011 instead of the
    literal 8000/8001 defaults, because port 8000 was already occupied by a
    pre-existing, long-running vanilla uvicorn process on this host (started
    ~5h before this session, unrelated to this plan). Separately verified the
    default-port path directly: `bash scripts/dual_site.sh start` with no
    overrides correctly printed `FAILED: port 8000 is already listening --
    refusing to adopt a foreign process` and exited non-zero, proving the
    required do-not-adopt-a-foreign-process guard against a genuine occupied
    port rather than a synthetic one. The pre-existing process on :8000 was
    never touched, signalled, or restarted."
  - "scripts/smoke_test.sh's react-mode branch was verified statically only
    (bash -n, plus a dry run with SMOKE_DOCKER pointed at a nonexistent
    binary to prove the branch is reached and fails loudly) -- no container
    runtime exists on this host. The real gate is the CI image job's second
    smoke_test.sh invocation on the next push, exactly as the plan's own
    action text specifies."

requirements-completed: [CUT-01]

coverage:
  - id: D1
    description: "Production react-mode serving seam: FPL_FRONTEND=react mounts /data from live web/data and / from frontend/dist, registered in that order, as a third branch beside the untouched fixture and vanilla branches"
    requirement: CUT-01
    verification:
      - kind: unit
        ref: "tests/test_react_seam.py#test_react_mode_mounts_live_data_then_dist"
        status: pass
      - kind: unit
        ref: "tests/test_react_seam.py#test_unset_frontend_env_leaves_the_production_default"
        status: pass
      - kind: unit
        ref: "tests/test_react_seam.py#test_vanilla_literal_value_behaves_identically_to_unset"
        status: pass
      - kind: unit
        ref: "tests/test_react_seam.py#test_fixture_mode_wins_over_react_mode"
        status: pass
      - kind: integration
        ref: "tests/test_fixture_mode.py::test_unset_env_leaves_a_single_root_mount"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/dual_site.sh: on-demand start/stop/status for two loopback-only uvicorns against the live export, refuses to adopt a foreign process on either port"
    requirement: CUT-01
    verification:
      - kind: other
        ref: "bash scripts/dual_site.sh start (default ports, port 8000 occupied) -> FAILED: refuses foreign process, exit 1"
        status: pass
      - kind: other
        ref: "DUAL_SITE_VANILLA_PORT=8010 DUAL_SITE_REACT_PORT=8011 bash scripts/dual_site.sh start -> both up, then stop -> stopped, no lingering listeners"
        status: pass
    human_judgment: false
  - id: D3
    description: "e2e/parity/parity-diff.mjs: cross-origin xP-table row comparison with a same-live-export freshness guard on /data/meta.json"
    requirement: CUT-01
    verification:
      - kind: e2e
        ref: "node e2e/parity/parity-diff.mjs --page / --vanilla-origin http://127.0.0.1:8010 --react-origin http://127.0.0.1:8011 -> rows compared: 50, exit 0, zero mismatches"
        status: pass
      - kind: e2e
        ref: "node e2e/parity/parity-diff.mjs --page / --react-origin http://127.0.0.1:9999 -> fetch failure, exit 1 (fails loudly, never vacuous)"
        status: pass
    human_judgment: false
  - id: D4
    description: "tests/test_react_seam.py: mount-name AND resolved-directory coverage for all four FPL_FRONTEND/FPL_FIXTURE_DIR combinations, order-independent against tests/test_fixture_mode.py"
    requirement: CUT-01
    verification:
      - kind: unit
        ref: "python -m pytest tests/test_react_seam.py -q -> 4 passed"
        status: pass
      - kind: unit
        ref: "python -m pytest tests/test_react_seam.py tests/test_fixture_mode.py -q (both orders) -> 14 passed each"
        status: pass
    human_judgment: false
  - id: D5
    description: "React-mode assertion inside the built container image, wired into the CI image job before the Trivy scanner (D-04)"
    requirement: CUT-01
    verification:
      - kind: other
        ref: "bash -n scripts/smoke_test.sh; SMOKE_DOCKER=definitely-not-a-real-runtime SMOKE_REACT_MODE=1 bash scripts/smoke_test.sh local/fpl:ci -> FAILED: runtime not found, exit 1"
        status: pass
    human_judgment: true
    rationale: "No container runtime (docker/podman) exists on this dev host, so the react-mode container boot itself was never exercised end to end here -- only syntax and the reached-and-fails-loudly dry run were proven locally. The real gate is the CI image job's second smoke_test.sh invocation (SMOKE_REACT_MODE=1) on the next push."

duration: 46min
completed: 2026-09-07
status: complete
---

# Phase 7 Plan 1: Production Serving Seam Summary

**FPL_FRONTEND=react production mount branch in api/main.py, an on-demand dual-uvicorn runner (scripts/dual_site.sh), a live-export-guarded cross-origin xP-table diff CLI (e2e/parity/parity-diff.mjs), and a CI container smoke assertion — the concrete "config/env flip" Phase 5's D-06 promised, now real and end-to-end proven against 50 live rows with zero mismatches.**

## Performance

- **Duration:** 46 min
- **Started:** 2026-09-07T11:05:00Z (approx.)
- **Completed:** 2026-09-07T11:50:54Z
- **Tasks:** 3 completed
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments

- Added a third, sibling mount branch to `api/main.py`'s existing fixture-mode env seam: `FPL_FRONTEND=react` mounts the live `web/data` export at `/data` and the built React app at `/`, in that registration order, while leaving the fixture and vanilla branches character-for-character unchanged.
- Built `scripts/dual_site.sh` (start/stop/status): boots vanilla and react uvicorns side by side on loopback-only ports against the same live export, refuses to adopt any process already bound to either port, and refuses to signal a stale PID that isn't actually a uvicorn.
- Built `e2e/parity/parity-diff.mjs`: reuses the already-approved `@playwright/test@1.62.1` install (zero new packages) to open both sites in one browser, guards freshness by byte-comparing `/data/meta.json` across both origins and the on-disk export first, then extracts and compares the xP table's name/team/price columns row by row.
- Added `tests/test_react_seam.py`: four characterization tests asserting mount name AND resolved on-disk directory for all four `FPL_FRONTEND`/`FPL_FIXTURE_DIR` combinations, proven order-independent against the untouched `tests/test_fixture_mode.py`.
- Extended `scripts/smoke_test.sh` with a `SMOKE_REACT_MODE=1` branch and wired a second invocation into `.github/workflows/ci.yml`'s `image` job (before the Trivy scanner), so the env flip is proven inside the actual built container image, not just against a local interpreter.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "both sites, same live data, machine-compared"** - `c34ad39` (feat)
2. **Task 2: Mount-branch test coverage for all three serving modes** - `c61023c` (test)
3. **Task 3: Prove the react-mode seam inside the built container image in CI** - `8c3e19b` (feat)

**Plan metadata:** _pending_ (docs: complete plan)

## Files Created/Modified

- `api/main.py` - Third mount branch (`elif _REACT_MODE`) plus the `_REACT_MODE` env-seam declaration, both purely additive
- `scripts/dual_site.sh` - New: start/stop/status for two side-by-side loopback uvicorns against the live export
- `e2e/parity/parity-diff.mjs` - New: cross-origin xP-table row comparison CLI with a live-export freshness guard
- `tests/test_react_seam.py` - New: mount-branch coverage for all three (four, counting the fixture-precedence case) serving modes
- `scripts/smoke_test.sh` - Added `SMOKE_REACT_MODE`/`SMOKE_REACT_PORT` branch; fixture-mode path stays byte-identical and unconditional
- `.github/workflows/ci.yml` - Second `smoke_test.sh` invocation (`SMOKE_REACT_MODE: 1`) in the `image` job, before the Trivy scan step
- `.gitignore` - Added the three `data/dual_site.*` runtime files under the existing regenerable-pipeline-data section

## Decisions Made

- Verified `scripts/dual_site.sh`'s full happy path using override ports (8010/8011) instead of the literal 8000/8001 defaults, because port 8000 was already bound by a pre-existing, long-running vanilla `uvicorn` process on this host (PID 2914, started ~5 hours before this session — unrelated to this plan, presumably a developer reference session). Separately proved the default-port refusal behavior directly against that real occupied port: `bash scripts/dual_site.sh start` with no overrides printed `FAILED: port 8000 is already listening -- refusing to adopt a foreign process` and exited non-zero, which is a stronger proof of the "never adopt a foreign process" requirement than a synthetic port conflict would have been. The pre-existing process was never signalled, stopped, or otherwise touched — confirmed still running and healthy after the full test sequence.
- `scripts/smoke_test.sh`'s new react-mode branch could only be verified statically (`bash -n` plus a dry run against a nonexistent `SMOKE_DOCKER` binary, proving the branch is reached and fails loudly rather than silently skipping) — no container runtime exists on this development host. This matches the plan's own action text, which explicitly anticipates this and names the CI `image:` job as the real gate.

## Deviations from Plan

None - plan executed exactly as written. The two "Decisions Made" above are execution-environment adaptations (an already-occupied port; no local container runtime) explicitly anticipated or accommodated by the plan's own `<action>` text and env-var override seams, not departures from it.

## Issues Encountered

- **Port 8000 already in use.** Discovered before running any verification: a pre-existing vanilla `uvicorn api.main:app --host 127.0.0.1 --port 8000` process (PID 2914) was already running on this host, started well before this session. Resolved by using `DUAL_SITE_VANILLA_PORT`/`DUAL_SITE_REACT_PORT` overrides for the full-mechanism verification pass and by directly exercising the default-port refuse-on-occupied-port path against the real process (see Decisions Made). No production impact — the process was never touched.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The production `FPL_FRONTEND=react` seam, the on-demand dual-site runner, and the one-page parity diff CLI are all live and proven against 50 real rows with zero mismatches — the foundation Phase 7's remaining plans (comparison-method expansion, the three-stage validation cycle, and the eventual human-gated cutover flip) build on.
- `e2e/parity/parity-diff.mjs` currently supports only `--page /`; the artifacts table for this phase notes `--all`/`--stage`/`--out` flags land in 07-02 T2 alongside `extract.mjs` and `ledger.mjs` — no blocker, just scoped as planned.
- The CI `image:` job's new react-mode smoke step has not yet run in CI (no push since this commit) — first real gate is the next push to this branch/PR.
- No blockers for 07-02.

---
*Phase: 07-parity-validation-cutover*
*Completed: 2026-09-07*

## Self-Check: PASSED

- FOUND: scripts/dual_site.sh
- FOUND: e2e/parity/parity-diff.mjs
- FOUND: tests/test_react_seam.py
- FOUND commit: c34ad39
- FOUND commit: c61023c
- FOUND commit: 8c3e19b
