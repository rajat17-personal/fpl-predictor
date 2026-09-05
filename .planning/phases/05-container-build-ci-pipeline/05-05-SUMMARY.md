---
phase: 05-container-build-ci-pipeline
plan: 05
subsystem: infra
tags: [github-actions, docker, ghcr, trivy, ci-cd, preflight]

# Dependency graph
requires:
  - phase: 05-03
    provides: "ci.yml chained lint/typecheck -> tests -> e2e -> image build/smoke/scan -> main-only GHCR publish"
  - phase: 05-04
    provides: "SHA-pinned, hygiene-clean daily.yml/weekly.yml and a repo scan for personal-email/credential literals"
provides:
  - "scripts/preflight.sh — local reproduction of the CI verification chain (hash-locked install, lint, frontend build, backend+frontend tests, workflow hygiene, container gate)"
  - "The first real CI run on GitHub Actions, observed and reported by the developer, with two real red runs diagnosed and fixed"
  - "A published, SHA-pinned, scoped-token GHCR image reachable from a green main-branch run"
affects: [06-security-reliability-observability-hardening]

# Actuals (#2632)
actuals:
  tokens: 6300
  tasks: 2
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "preflight.sh: ephemeral venv + --require-hashes install, never the conda env, removed via trap on exit"
    - "python -m pytest (module form) everywhere pytest runs — bare `pytest` does not prepend CWD to sys.path"

key-files:
  created:
    - scripts/preflight.sh
  modified:
    - .github/workflows/ci.yml
    - Dockerfile
    - .planning/STATE.md
    - .planning/WINDOWS.md
    - .planning/phases/05-container-build-ci-pipeline/05-PATTERNS.md
    - .planning/phases/05-container-build-ci-pipeline/05-04-SUMMARY.md

key-decisions:
  - "Redacted the personal email found in 05-PATTERNS.md (WINDOWS.md entry 3) before the first push, per developer decision 'Redact' — closes the entry as fixed rather than waived."
  - "Fixed both real CI failures (pytest sys.path, missing libgomp1) as follow-up commits authored by the orchestrator and pushed by the developer, rather than reworking scope of Task 1's preflight script — both were genuine CI-runner-vs-local-environment deltas that preflight.sh could not have caught (CI runs bare `pytest` before the ci.yml fix; libgomp1 is a runtime-image-only dependency LightGBM dlopens at import, invisible to a script that never builds the image)."

patterns-established:
  - "Trivy SARIF upload to the Security tab is best-effort per GitHub's own documented inconsistency for private repos — the trivy-results build artifact is the durable sink; the Security-tab view is a bonus that worked on this run's third (green) attempt."

requirements-completed: [CI-04]

coverage:
  - id: D1
    description: "scripts/preflight.sh reproduces the CI verification chain locally (hash-locked install, lint, frontend build, backend+frontend tests, workflow hygiene, container gate) and exits 0 with PREFLIGHT PASSED"
    requirement: CI-04
    verification:
      - kind: other
        ref: "bash scripts/preflight.sh (re-run after e4f6ebf's redaction fix) — printed PREFLIGHT PASSED, 6 gates ran, container gate SKIPPED locally by design"
        status: pass
    human_judgment: false
  - id: D2
    description: "First real push, PR run, and main-branch run on GitHub Actions complete green, publishing a SHA-pinned, scoped-token image to GHCR"
    requirement: CI-04
    verification:
      - kind: other
        ref: "human-reported: PR run passed on third attempt after two real fixes (11cd68e, 65cd2e7); main-branch run passed including publish — https://github.com/rajat17-personal/fpl-predictor/actions/runs/33950933101/job/101266347373"
        status: pass
    human_judgment: true
    rationale: "The run happened on the developer's own GitHub account and credential (D-14); this agent has no gh CLI, no remote, and no push credential, so the outcome can only be recorded from the developer's report, not independently re-verified."
  - id: D3
    description: "Trivy vulnerability scan produces report-only findings visible at the repo Security tab (187 findings, expected under D-10/CI-05 scope)"
    requirement: CI-05
    verification:
      - kind: other
        ref: "human-reported: 187 open report-only Trivy findings visible at the repo Security tab after the third (green) PR run"
        status: pass
    human_judgment: true
    rationale: "Finding count and triage disposition live in GitHub's Security tab, which this agent cannot query (no gh CLI, no push credential) — recorded from developer report only."
  - id: D4
    description: "Branch protection on main requires the ci.yml verification jobs before merge (D-15)"
    requirement: CI-04
    verification: []
    human_judgment: true
    rationale: "Instructed in Stage 2 of the checkpoint but not explicitly confirmed back by the developer in the reported items — cannot be verified locally (no gh CLI, no API access) or inferred from the passing main-branch run alone, since that run could have landed via a direct push rather than a protected PR merge. Carry into /gsd-verify-work or a manual repo-settings check before Phase 6 closes out CI-04 for good."

duration: (spans human-checkpoint wall-clock time; agent-side work was two short follow-up commits plus this closeout)
completed: 2026-09-05
status: complete
---

# Phase 5 Plan 5: Local Preflight & First Real CI Run Summary

**scripts/preflight.sh reproduces the CI verification chain locally; the first real push produced two genuine CI failures (pytest sys.path, missing libgomp1) that were diagnosed and fixed, then a green PR run and a green main-branch run that published to GHCR.**

## Performance

- **Duration:** spans the D-14 human checkpoint (first push, PR iteration, branch protection, merge) plus two short agent-side fix commits and this closeout
- **Tasks:** 2/2 complete (Task 1 auto, Task 2 checkpoint:human-action)
- **Files modified:** 7 across the checkpoint window (preflight.sh created; ci.yml and Dockerfile fixed; 4 planning docs redacted)

## Accomplishments

- `scripts/preflight.sh` created and verified green on the working tree: hash-locked ephemeral-venv install, `ruff check .`, frontend build with the `dist/index.html`/`dist/404.html` guard, `python -m pytest`, `npm --prefix frontend test`, and a repo-wide workflow-hygiene gate (SHA-pin count, no `schedule:` trigger, tracked-file email/credential scan) — with a `SKIPPED`, still-exit-0 container gate on this docker-less machine.
- Personal email found by preflight's own hygiene gate (WINDOWS.md entry 3, `05-PATTERNS.md`) redacted per developer decision "Redact"; WINDOWS.md entry 3 closed via `gsd-tools windows fixed 3`. Preflight re-run afterward printed `PREFLIGHT PASSED`.
- First real push to the private GitHub repo (`rajat17-personal/fpl-predictor`) triggered two genuinely red CI runs, each diagnosed from the developer-pasted failing log and fixed in a follow-up commit:
  1. `test` job failed collection with `ModuleNotFoundError` (config/backtest) — bare `pytest` does not prepend the CWD to `sys.path`. Fixed in `11cd68e` by running `python -m pytest` in `ci.yml`, matching what `preflight.sh` already did.
  2. `image` job's smoke test failed at container boot with `OSError: libgomp.so.1: cannot open shared object file` — LightGBM dlopens GNU OpenMP at import, and `python:3.14-slim`'s runtime stage did not carry it. Fixed in `65cd2e7` by adding `libgomp1` alongside the existing `libstdc++6` apt-get line in the Dockerfile's runtime stage.
- Third PR run passed every job. The Trivy SARIF upload to the Security tab succeeded on this run: 187 open, report-only findings are now visible there (expected under CI-05/D-10 — scan is report-only this milestone; base-image and dependency CVE triage is explicitly deferred).
- Main-branch run passed including the `publish` job, producing a SHA-pinned, scoped-`GITHUB_TOKEN` GHCR image — developer-provided evidence: https://github.com/rajat17-personal/fpl-predictor/actions/runs/33950933101/job/101266347373

## Task Commits

Each task was committed atomically:

1. **Task 1: Local preflight: reproduce the CI verification chain** - `378f94f` (feat)
2. **Task 2: First push, branch protection, first real CI run (D-14, D-15)** - human-performed on the developer's own GitHub credential; the two resulting CI fixes were committed by the orchestrator as `11cd68e` (fix) and `65cd2e7` (fix); the redaction that unblocked the first push was committed as `e4f6ebf` (chore)

**Plan metadata:** (this commit) `docs(05-05): complete plan`

_Note: Task 2 is a `checkpoint:human-action` gate — its "commit" is the developer's own push/merge on GitHub, which this agent cannot see or verify directly (no `gh` CLI, no remote credential). The three commits listed above are the agent-side follow-up work the checkpoint's red runs required._

## Files Created/Modified

- `scripts/preflight.sh` - local reproduction of the CI verification chain (7 gates), created and verified green
- `.github/workflows/ci.yml` - `test` job now runs `python -m pytest` instead of bare `pytest`
- `Dockerfile` - runtime stage now installs `libgomp1` alongside `libstdc++6`
- `.planning/STATE.md`, `.planning/WINDOWS.md`, `.planning/phases/05-container-build-ci-pipeline/05-PATTERNS.md`, `.planning/phases/05-container-build-ci-pipeline/05-04-SUMMARY.md` - personal email redacted, WINDOWS entry 3 closed

## Decisions Made

- Redact (not waive) the personal-email finding before the first push — the developer's explicit verbatim decision at the checkpoint.
- Both real CI failures were fixed as narrow, targeted commits scoped to exactly the failing line (pytest invocation form; one missing apt package) rather than broader rework, since both were confirmed root causes from the actual failing CI logs, not speculative fixes.
- Trivy's Security-tab SARIF upload and its build-artifact sink are treated as independently-fine outcomes per the plan's own design (`05-05-PLAN.md` Stage 3) — both worked on this run, but only the artifact was guaranteed to.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test` job failed collection — bare `pytest` omits CWD from `sys.path`**
- **Found during:** Task 2 (first real CI run, PR pipeline, first attempt — red)
- **Issue:** `ci.yml`'s `test` job ran plain `pytest`, which does not add the current working directory to `sys.path`, so top-level imports (`config`, `backtest`) failed with `ModuleNotFoundError` on the CI runner even though the same suite passed locally under `python -m pytest`.
- **Fix:** Changed the `test` job's pytest invocation to `python -m pytest`, matching `scripts/preflight.sh` and the container smoke test's existing convention.
- **Files modified:** `.github/workflows/ci.yml`
- **Verification:** Second PR run's `test` job passed the same suite that had previously failed collection.
- **Committed in:** `11cd68e`

**2. [Rule 1 - Bug] `image` job smoke test failed at container boot — missing `libgomp1` in the runtime image**
- **Found during:** Task 2 (first real CI run, PR pipeline, second attempt — red)
- **Issue:** `python:3.14-slim`'s runtime stage installed `libstdc++6` for PuLP's bundled CBC solver but not `libgomp1`. LightGBM's compiled extension dlopens GNU OpenMP (`libgomp.so.1`) at `import lightgbm` time, so the container failed at boot with `OSError: libgomp.so.1: cannot open shared object file`, before the smoke test's solve step ever ran. The same run's Trivy artifact/SARIF errors were downstream of this failure (the scan step never ran) and needed no separate fix.
- **Fix:** Added `libgomp1` to the runtime stage's `apt-get install` line, alongside the existing `libstdc++6`.
- **Files modified:** `Dockerfile`
- **Verification:** Third PR run's `image` job passed the smoke test end to end; the run also passed Trivy's scan and SARIF upload.
- **Committed in:** `65cd2e7`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — genuine CI-environment bugs discovered only by the first real push, exactly the outcome D-14 exists to surface). No scope creep — both fixes are single-line, root-caused from the actual failing job logs the developer pasted back.
**Impact on plan:** Necessary corrections to reach a green pipeline; no architectural changes, no new dependencies, no change to the plan's designed scope.

## Issues Encountered

- The plan anticipated that a red run would require "a corrected commit to push" (Task 2's `<instructions>` closing line) — this happened twice, exactly as designed, and both fixes are the two auto-fixed issues documented above.
- Not independently re-verified by this agent (no `gh` CLI, no push credential — by design per D-14/T-05-05-04): the literal `SMOKE TEST PASSED` log line, the exact per-job conclusion for each of the five PR-run jobs individually, the GHCR tag names, and the published image size. The developer reported the pipeline outcome qualitatively (two red-then-fixed runs, then green; main run green including `publish`, evidenced by the linked Actions run) but did not report these specific data points verbatim, and this agent has no way to query GitHub directly to fill them in. Recorded here rather than invented.
- Branch protection (D-15, Stage 2 of the checkpoint) was instructed to the developer but its configuration was not explicitly confirmed back in the reported items. The green main-branch run is consistent with either a protected-PR merge or a direct push having occurred; it does not by itself prove protection is active. Flagged as coverage item D4 above (`human_judgment: true`) for `/gsd-verify-work` or a manual repo-settings check to close out before this is fully trusted for Phase 6.

## User Setup Required

None - no external service configuration required beyond what the developer already performed at the checkpoint (repository creation, push, branch-protection settings, PR merge — all D-14/D-15 by design).

## Next Phase Readiness

- CI-04 is now functionally complete: a real push produced a real CI run, two genuine environment bugs were found and fixed, and a green main-branch run published an image to GHCR under a SHA-pinned, scoped-token workflow, evidenced by the linked Actions run.
- Two loose ends carry forward rather than block: (1) branch-protection configuration (D-15) should be confirmed via the repo's Settings > Branches page or `gh api` once a `gh` CLI/token becomes available in this environment — see coverage item D4; (2) the exact per-job conclusion table, GHCR tag names, and image size were not captured verbatim and should be pulled from the Actions run UI if a retention-policy sizing decision (T-05-05-05) is needed before Phase 6.
- Phase 5's only remaining open WINDOWS.md item is id=1 (`npm run typecheck` type-checking 0 files), pre-existing from Phase 1 and explicitly flagged there as "fix before CI-01/CI-02 wire this script in" — CI-01/CI-02 are both complete, so this should be picked up early in Phase 6 rather than carried further.
- Phase 6 (Security, Reliability & Observability Hardening) can proceed: the CI pipeline that will gate every one of its commits is now proven end to end on real infrastructure, not simulated.

---
*Phase: 05-container-build-ci-pipeline*
*Completed: 2026-09-05*
