---
phase: 05-container-build-ci-pipeline
plan: 02
subsystem: infra
tags: [docker, dockerfile, cbc, pulp, smoke-test, dockerignore]

# Dependency graph
requires:
  - phase: 05-container-build-ci-pipeline (plan 01)
    provides: "requirements.txt — hash-verified compiled runtime lock the builder stage installs with --require-hashes"
provides:
  - "Dockerfile — multi-stage python:3.14-slim image (builder installs hashed lock, runtime adds libstdc++6 + non-root user + uvicorn entrypoint)"
  - ".dockerignore — build-context exclusion list keeping secrets/model/pipeline-data/test-fixtures out of every layer while re-including frontend/dist"
  - "scripts/smoke_test.sh — CI-03/D-07 container smoke test: fixture-mode boot, /api/health, then a real /api/solve CBC solve; SMOKE_DOCKER/SMOKE_PORT env seams"
affects: [05-03-ci-workflow, 05-05-first-ci-run, 07-cutover]

# Actuals (#2632)
actuals:
  tokens: 2282
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Two-stage Dockerfile: builder installs the hashed lock into --prefix=/install, runtime COPY --from=builder /install /usr/local so no compiler/pip-cache crosses into the shipped image"
    - "Shell smoke-test convention (scripts/verify_frontend_build.sh's shape): shebang + purpose comment block, set -euo pipefail, cd to repo root, bracketed [smoke_test] status echoes, FAILED: <reason> + exit 1 on every failure path"
    - "Env-seam pattern mirroring E2E_PYTHON: SMOKE_DOCKER/SMOKE_PORT read with defaults, override-friendly, never silently falling back to a developer's live port"

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - scripts/smoke_test.sh
  modified: []

key-decisions:
  - "No build-essential/compiler added to the builder stage — plan 05-01's SUMMARY recorded a clean-venv install with zero source compilation across the whole lock, so D-03's from-source fallback stays dormant rather than pre-emptively added."
  - "Bundled PULP_CBC_CMD kept as-is; only apt-get install libstdc++6 added to runtime (per RESEARCH.md's verified finding that the CBC binary inside the PuLP wheel needs no coinor-cbc apt package, just the missing C++ runtime library python:3.14-slim strips by default)."
  - "smoke_test.sh's two fail-fast guards are strictly ordered (missing image-tag argument, then absent SMOKE_DOCKER binary) so the missing-argument gate is provable without any container runtime present in this execution environment."

patterns-established:
  - "Container smoke test proves a real integer program runs (POST /api/solve, assert exactly 15 player_code entries) rather than a presence check like `import pulp` — establishes the bar for what 'the solver is available' means in this repo's CI."

requirements-completed: [CI-03]

coverage:
  - id: D1
    description: "Multi-stage Dockerfile (python:3.14-slim builder + runtime) with hash-locked install, CBC runtime library, non-root user, uvicorn entrypoint; .dockerignore excludes every secret/model/pipeline-data/test category while re-including frontend/dist for D-06's dual-static-tree requirement"
    requirement: CI-03
    verification:
      - kind: other
        ref: "grep-based structural gates: two named FROM python:3.14-slim stages; --require-hashes + libstdc++6 + non-root USER + uvicorn CMD all present on non-comment lines; zero model-artifact reference anywhere; all 19 required .dockerignore exclusions present as exact lines; !frontend/dist re-included and !data/snapshots not re-included"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/smoke_test.sh: fixture-mode container boot, /api/health poll, then a real POST /api/solve exercising the bundled CBC binary via an actual ILP solve (15 player_code entries), with two ordered fail-fast guards and an EXIT trap"
    requirement: CI-03
    verification:
      - kind: other
        ref: "bash -n scripts/smoke_test.sh && test -x; missing-argument guard (no args -> FAILED: line, exit non-zero); runtime-absent guard (SMOKE_DOCKER=__no_such_container_cli__ -> FAILED: line naming the binary); D-07 payload wiring grep (FPL_FIXTURE_DIR=/fixtures/v1/normal, /api/health, /api/solve, player_code all present)"
        status: pass
    human_judgment: true
    rationale: "No container runtime exists in this execution environment (docker/podman/buildah and /var/run/docker.sock all absent, matching the plan's stated constraint) — the actual docker build + smoke run (real /api/health response, real CBC solve, exactly 15 player_code entries) cannot be executed here. Deferred to the D-14 human-gated checkpoint in plan 05-05: user runs `docker build -t local/fpl:smoke .` then `bash scripts/smoke_test.sh local/fpl:smoke` as part of the first real CI run."

duration: ~5min
completed: 2026-09-04
status: complete
---

# Phase 5 Plan 2: Multi-Stage Dockerfile & Container Smoke Test Summary

**Two-stage python:3.14-slim Dockerfile (hashed install + libstdc++6 for PuLP's bundled CBC binary + non-root user) and a fixture-mode smoke test that proves a real ILP solve, not just a health check, ready for the D-14 human-gated first CI run.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-09-04
- **Completed:** 2026-09-04
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments
- `Dockerfile`: builder stage installs `requirements.txt` with `pip install --require-hashes --prefix=/install` (D-04); runtime stage is a fresh `python:3.14-slim` with `libstdc++6` added (the one line that makes PuLP's bundled CBC binary executable, since the slim base strips every apt library CPython itself doesn't link), a non-root `appuser` before `CMD`, and `uvicorn api.main:app --host 0.0.0.0 --port 8000` as the entrypoint. No model artifact, `.env`, or pipeline data is ever `COPY`'d or referenced anywhere in the file (D-05).
- `.dockerignore`: mirrors `.gitignore`'s exclusion categories (Python/Node artifacts, pipeline data, model output, secrets) plus everything `.gitignore` deliberately keeps tracked but the image has no use for (`.git`, `.github`, `.planning`, `.claude`, `.gsd`, `tests`, `e2e`, `scripts`, `docs`). Two deliberate divergences from `.gitignore`, each commented inline: `data/snapshots` stays excluded (never re-included, unlike git's irreplaceable-history rule) and `frontend/dist` stays *included* in the build context via `frontend/** ` + `!frontend/dist` + `!frontend/dist/**` (D-06 — CI builds it before `docker build` runs).
- `scripts/smoke_test.sh`: boots the image with `FPL_FIXTURE_DIR=/fixtures/v1/normal` and the `e2e/fixtures` tree bind-mounted read-only (never baked into the image), polls `/api/health` on a bounded 30-attempt/1s loop dumping container logs on timeout, then POSTs an empty JSON body to `/api/solve` — every field on `SolveRequest` defaults, so this triggers a genuine from-scratch squad solve — and asserts exactly 15 `player_code` entries in the response, the strongest possible proof the bundled CBC binary actually ran. Two ordered fail-fast guards (missing image tag, then an absent `SMOKE_DOCKER` binary) each print a distinct `FAILED:` line; an `EXIT` trap force-removes the container on every path; the default host port is 8200, never 8000.
- All automated `<verify>` gates from both tasks passed in this execution environment (grep-based structural checks); the real `docker build` + smoke run is not possible here (no container runtime present) and is explicitly queued for the D-14 human-gated checkpoint in plan 05-05, per the plan's stated execution-environment constraint.

## Task Commits

Each task was committed atomically:

1. **Task 1: Multi-stage Dockerfile and the build-context exclusion list** - `bbbcb90` (feat)
2. **Task 2: Container smoke test: health check plus a real CBC solve on the frozen fixture set** - `bca411f` (feat)

## Files Created/Modified
- `Dockerfile` - Two-stage build: hashed dependency install, CBC-capable runtime, non-root user, uvicorn entrypoint, HEALTHCHECK via stdlib urllib
- `.dockerignore` - Exclusion list for the build context; keeps `frontend/dist` reachable, keeps `data/snapshots` excluded
- `scripts/smoke_test.sh` - Executable smoke test: fixture-mode boot, health poll, real CBC solve assertion, two fail-fast guards, EXIT-trapped cleanup

## Decisions Made
- No compiler added to the builder stage — plan 05-01's SUMMARY confirmed every pin in the current lock installs as a clean wheel with zero source compilation, so D-03's pre-authorized fallback (`build-essential` in the builder stage only) stays unused rather than added defensively.
- Kept `PULP_CBC_CMD` (the bundled CBC binary) rather than switching to `pulp[cbc]`/`COIN_CMD` — RESEARCH.md's alternatives-considered analysis rejected the switch for this phase (would require touching three call sites for zero benefit); `apt-get install libstdc++6` alone resolves the actual gap.
- `scripts/smoke_test.sh`'s two guards are strictly ordered (argument check before runtime check) specifically so the missing-argument path is provable in an environment with no container CLI at all — matches this execution environment's actual constraints.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<verify>` blocks were followed directly; the plan itself pre-authorized and anticipated the no-container-runtime environment constraint, so the human-check deferral is expected behavior, not a deviation.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required by this plan. The D-14 human-gated checkpoint (real `docker build` + `bash scripts/smoke_test.sh`) is owned by plan 05-05, not this plan.

## Next Phase Readiness
- `Dockerfile` and `.dockerignore` are ready for `ci.yml`'s docker-build-and-smoke job in plan 05-03 to consume directly (`docker build -t <tag> .` then `bash scripts/smoke_test.sh <tag>`)
- `scripts/smoke_test.sh`'s `SMOKE_DOCKER`/`SMOKE_PORT` env seams are ready for CI to override if needed (defaults are CI-safe: `docker`, port `8200`)
- No blockers for 05-03; the real container build/smoke run remains queued for plan 05-05's D-14 human-gated checkpoint

---
*Phase: 05-container-build-ci-pipeline*
*Completed: 2026-09-04*

## Self-Check: PASSED

All created files verified present on disk (`Dockerfile`, `.dockerignore`, `scripts/smoke_test.sh`, executable); both task commits (`bbbcb90`, `bca411f`) verified present in `git log`. All plan-level `<verification>` automated commands re-run successfully in this session.
