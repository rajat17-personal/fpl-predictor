---
phase: 05-container-build-ci-pipeline
plan: 03
subsystem: infra
tags: [github-actions, ci, docker, trivy, ghcr, playwright, sha-pinning]

# Dependency graph
requires:
  - phase: 05-01
    provides: "requirements.txt / requirements-dev.txt — hash-verified locks both lint-build and test install with --require-hashes"
  - phase: 05-02
    provides: "Dockerfile, .dockerignore, scripts/smoke_test.sh — the image job builds and smoke-tests exactly these artifacts"
provides:
  - ".github/workflows/ci.yml — the single chained lint/typecheck -> backend+frontend test -> Playwright E2E -> image build+smoke+scan -> GHCR publish job graph"
  - "five job names (lint-build, test, e2e, image, publish) other phase artifacts/plans reference"
  - "the frontend-dist artifact handoff pattern (upload-artifact in lint-build, download-artifact in test/image/publish) that closes the Phase 4 -> Phase 5 SPA-fallback 500 blocker"
affects: [05-05-first-ci-run, 07-cutover]

# Actuals (#2632)
actuals:
  tokens: 3200
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One linear needs chain (lint-build -> test -> e2e -> image -> publish) instead of parallel jobs, so a broken earlier stage never wastes minutes on a docker build+scan of code that hasn't passed pytest/vitest/Playwright yet"
    - "Named existence-guard step (frontend/dist/index.html + 404.html checked individually, each with its own FAILED: message) between download-artifact and pytest, rather than trusting a bare directory presence check"
    - "Artifact-first, Security-tab-second SARIF sink ordering: the upload-artifact step for trivy-results.sarif runs unconditionally before the codeql-action/upload-sarif step, which alone carries continue-on-error: true"

key-files:
  created:
    - .github/workflows/ci.yml
  modified: []

key-decisions:
  - "Re-resolved all 12 distinct actions used in this plan (26 uses: lines total) live against the GitHub API at execution time rather than trusting 05-RESEARCH.md's table verbatim, per this plan's own SHA-resolution procedure. Every one matched RESEARCH.md's published SHA exactly -- zero drift, including the six 05-04 had already independently re-resolved (actions/checkout, actions/setup-python)."
  - "Built the file in three additive stages (lint-build+test, then +e2e, then +image+publish) with a commit after each task's <verify> block passed, rather than writing the whole 257-line file once and committing it as a single task-3 commit -- honors the per-task atomic-commit contract even though all three tasks share one files_modified entry."
  - "e2e job installs only the runtime lock (requirements.txt), not requirements-dev.txt -- it never invokes pytest/ruff, only python (via PATH) to let playwright.config.ts's webServer boot uvicorn."
  - "Playwright browser cache keyed on runner.os + hashFiles('e2e/package-lock.json') via actions/cache, matching the plan's stated cache-miss-not-failure semantics (npm run install:browser always runs regardless of cache hit/miss)."

patterns-established:
  - "SHA-pinned uses: line format with trailing '# vX.Y.Z' comment, applied uniformly across all five jobs -- the same convention 05-04 established for daily.yml/weekly.yml, now extended to ci.yml's larger action surface (checkout, setup-python, setup-node, cache, upload/download-artifact, docker/* x4, trivy-action, codeql-action)."

requirements-completed: [CI-01, CI-02, CI-04, CI-05]

coverage:
  - id: D1
    description: "ci.yml skeleton (name, push+pull_request triggers, workflow-level concurrency+cancel-in-progress, contents:read default permissions) plus lint-build (ruff check ., npm run build as the real typecheck gate, frontend-dist artifact upload) and test (frontend-dist download, bundle-existence guard, pytest, vitest) jobs"
    requirement: CI-01
    verification:
      - kind: unit
        ref: "plan 05-03 task 1 automated <verify> block (4 python/yaml assertion commands): trigger+concurrency+permissions+needs-chain gate, lint-build content gate, test job content gate, no-continue-on-error-except-sarif gate"
        status: pass
    human_judgment: false
  - id: D2
    description: "e2e job (needs: test): runtime-lock install, both npm ci installs, Playwright browser cache, npm run install:browser + npm run test with no project/variant filter, E2E_PYTHON/E2E_VARIANTS both absent, HTML report uploaded on always()"
    requirement: CI-02
    verification:
      - kind: unit
        ref: "plan 05-03 task 2 automated <verify> block (2 python/yaml assertion commands) plus a real `cd e2e && npx tsc --noEmit -p tsconfig.json` run (exit 0, confirms the suite this job invokes was not disturbed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "image job (needs: e2e, security-events:write, no packages permission): docker build with push:false/load:true, scripts/smoke_test.sh run before Trivy, Trivy with no exit-code input, artifact-first + continue-on-error-second SARIF sinks; publish job (needs: image, packages:write, if: refs/heads/main): GHCR login via GITHUB_TOKEN, metadata-action tags, real push, named no-op deploy placeholder"
    requirement: "CI-04, CI-05"
    verification:
      - kind: unit
        ref: "plan 05-03 task 3 automated <verify> block (5 commands): scoping gate, Trivy-ordering gate, push:false/load:true gate, 26/26 SHA-pin counting gate, no-shell-short-circuit gate"
        status: pass
    human_judgment: true
    rationale: "No container runtime exists in this execution environment (confirmed absent, matching 05-02's stated constraint), so the real `docker build` + `scripts/smoke_test.sh` + Trivy scan + GHCR push were validated by structural gates and cross-checks against 05-02's actual Dockerfile/smoke-test interface, not by an executed run. The authoritative end-to-end proof (real CI run goes green, image appears in GHCR) is the D-14 human-gated checkpoint owned by plan 05-05."

duration: ~18min
completed: 2026-09-04
status: complete
---

# Phase 5 Plan 3: Chained CI Workflow (Lint/Test/E2E/Image/Publish) Summary

**Single `.github/workflows/ci.yml` chaining lint/typecheck, backend+frontend tests against the built bundle, the existing Playwright E2E suite, a Docker build with a real-solve smoke test and report-only Trivy scan, and a main-only GHCR publish with a stubbed deploy step — every `uses:` line SHA-pinned and re-verified against the live GitHub API.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-09-04
- **Completed:** 2026-09-04
- **Tasks:** 3
- **Files modified:** 1 (created)

## Accomplishments
- `.github/workflows/ci.yml` skeleton: `push` (no branch filter) + `pull_request` (narrowed to `opened`/`reopened`/`ready_for_review`) triggers, a workflow-level `concurrency` group keyed on PR number or ref with `cancel-in-progress: true`, and `permissions: contents: read` as the least-privilege default.
- `lint-build`: installs both hash-locked locks with `--require-hashes`, runs `ruff check .`, then `npm --prefix frontend run build` as the real typecheck gate (the repo's own `npm run typecheck` script is a confirmed no-op per 05-RESEARCH.md — never used), uploading `frontend/dist` as the `frontend-dist` artifact.
- `test` (`needs: lint-build`): downloads `frontend-dist`, runs a named guard step asserting `frontend/dist/index.html` and `frontend/dist/404.html` both exist (closing the Phase 4 → Phase 5 SPA-fallback-500 handoff blocker from 04-REVIEW.md), then bare `pytest` (picks up `pytest.ini`'s plugin disables automatically) and `npm --prefix frontend test`.
- `e2e` (`needs: test`): runtime-lock-only install, both `npm ci` installs, a `~/.cache/ms-playwright` cache keyed on the E2E lockfile hash (miss-not-failure), `npm --prefix e2e run install:browser`, then `npm --prefix e2e run test` with no project or variant filter — `E2E_PYTHON` and `E2E_VARIANTS` both stay unset so `e2e/playwright.config.ts` owns the entire build+boot+health-check server lifecycle for all three fixture variants unmodified.
- `image` (`needs: e2e`, `security-events: write`, no `packages` permission): builds with `push: false`/`load: true`, runs `bash scripts/smoke_test.sh local/fpl:ci` (a real CBC solve through the container) before Trivy scans the same tag with no `exit-code` input (report-only), uploads the raw SARIF as a build artifact first, then attempts the Security-tab upload with `continue-on-error: true` — the only step in the entire workflow permitted that flag.
- `publish` (`needs: image`, `packages: write`, `if: github.ref == 'refs/heads/main'`): logs in to `ghcr.io` with the workflow's own scoped `GITHUB_TOKEN`, derives `type=sha` + default-branch-gated `latest` tags via `docker/metadata-action`, pushes for real, and closes with a named no-op deploy-placeholder step that performs no deployment and holds no credentials.
- Every one of the 12 distinct actions used (26 `uses:` lines total) was re-resolved live against the GitHub API this session per the plan's own resolution procedure; every resolved SHA matched 05-RESEARCH.md's published table exactly — zero drift, including the two (`actions/checkout`, `actions/setup-python`) that 05-04 had already independently re-resolved for the scheduler workflows.

## Task Commits

Each task was committed atomically:

1. **Task 1: ci.yml skeleton plus the lint/typecheck and backend+frontend test jobs** - `3056734` (feat)
2. **Task 2: Playwright E2E job against fixture-fed uvicorn** - `1c8bfbd` (feat)
3. **Task 3: Image build with smoke test and Trivy scan, then the main-only GHCR publish** - `6ae0c02` (feat)

_Note: all three tasks share the same `files_modified` entry (`.github/workflows/ci.yml`); the file was built in three additive stages (lint-build+test, then +e2e, then +image+publish) so each task's own `<verify>` block ran and passed against the file state at that point before its commit, preserving per-task atomicity within a single-file plan._

## Files Created/Modified
- `.github/workflows/ci.yml` - New: 5-job chained CI workflow (lint-build, test, e2e, image, publish), 257 lines, every `uses:` line SHA-pinned

## Decisions Made
- Built the file incrementally (three commits against the same file) rather than one commit for the whole thing, so the per-task acceptance-criteria gate and the atomic-commit contract both hold meaningfully even though the plan's `files_modified` lists only one file.
- `e2e` job installs `requirements.txt` only (not `requirements-dev.txt`) — it never runs `pytest`/`ruff`, it only needs `python` on `PATH` for `playwright.config.ts`'s `webServer` to spawn `uvicorn`.
- Kept the Playwright browser cache keyed on `runner.os` + the E2E lockfile hash exactly as RESEARCH.md/PATTERNS.md specified — a cache miss re-downloads Chromium via the unconditional `install:browser` step regardless, matching the plan's "never a failure" requirement.
- No `actionlint` binary was available in this execution environment; verification relied entirely on the plan's own Python/YAML structural assertion gates (all passed) plus a real `cd e2e && npx tsc --noEmit` run to confirm the E2E suite this job invokes was not disturbed.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' `<action>` and `<verify>` blocks were followed directly; every automated `<verify>` command from all three tasks passed on the first attempt with zero re-resolved-SHA drift from 05-RESEARCH.md.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required by this plan. The D-14 human-gated checkpoint (user pushes → real CI run goes green end-to-end → image visible in GHCR) is owned by plan 05-05, not this plan.

## Next Phase Readiness
- `.github/workflows/ci.yml` is complete and ready to be pushed alongside the modernized `daily.yml`/`weekly.yml` (05-04) in plan 05-05
- Every structural claim this plan's own `<verification>` and `<must_haves>` make is asserted by a gate that ran without a GitHub runner or container runtime; the claims that only a real run can settle (the chain going green end-to-end, an image appearing in GHCR) are explicitly carried forward to plan 05-05's D-14 human-gated checkpoint, per this plan's own `<success_criteria>`
- No blockers for 05-05

---
*Phase: 05-container-build-ci-pipeline*
*Completed: 2026-09-04*

## Self-Check: PASSED

`.github/workflows/ci.yml` verified present on disk (257 lines, 5 jobs in the expected `lint-build -> test -> e2e -> image -> publish` order). All three task commits (`3056734`, `1c8bfbd`, `6ae0c02`) verified present in `git log --oneline`. Every automated `<verify>` command from all three tasks, plus the plan-level `<verification>` checks (job graph shape, trigger/concurrency/permissions defaults, artifact handoff, E2E delegation, image/publish gating, SHA-pin count 26/26, zero shell short-circuits), re-ran successfully against the final committed file.
