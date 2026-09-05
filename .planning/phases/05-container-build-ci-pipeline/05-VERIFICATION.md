---
phase: 05-container-build-ci-pipeline
verified: 2026-09-05T07:21:02Z
status: human_needed
score: 6/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Confirm branch protection on `main` in GitHub repo Settings > Branches: require a pull request before merging, and require the `lint-build`, `test`, `e2e`, `image` status checks (not `publish`) to pass before merge."
    expected: "Branch protection rule exists on `main` naming those four jobs as required status checks."
    why_human: "No `gh` CLI or API token is available in this environment; the D-14/D-15 checkpoint instructed the developer to configure this but the developer's reported checkpoint items (05-05-SUMMARY.md, coverage item D4) did not explicitly confirm it, and a green main-branch run is consistent with either a protected merge or a direct push — it does not by itself prove protection is active."
  - test: "Open the repository's Packages (GHCR) listing and note the tags present on the published image and its reported size."
    expected: "One tag derived from the commit SHA and one `latest` tag are visible; image size is recorded so the 500MB private-tier GHCR budget can be sized against it (T-05-05-05)."
    why_human: "No `gh` CLI, no API token, and no container runtime exist in this environment to query GHCR directly. 05-05-SUMMARY.md explicitly records that the developer's report did not include these two data points verbatim."
---

# Phase 5: Container Build & CI Pipeline Verification Report

**Phase Goal:** Every push is automatically verified and produces a publishable, scanned container image
**Verified:** 2026-09-05T07:21:02Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dependencies are locked and verified installable from scratch in a clean environment, with cp314 wheels confirmed available for every ML dependency | ✓ VERIFIED | `requirements.txt` (531 `--hash=sha256:` lines) and `requirements-dev.txt` (634) exist, every non-comment/non-directive line carries `==`, no `selenium/trio/wsproto/websocket-client` present. 05-01-SUMMARY.md documents a from-scratch venv `pip install --require-hashes` with zero source compilation and the full 77-test suite green; re-ran `pytest --collect-only` today and confirmed 77 tests collect cleanly against the current tree. |
| 2 | The repo is CI-ready: the 134MB Chrome `.deb` is gone, `.gitignore` covers generated artifacts, and the workflows are tracked in git | ✓ VERIFIED | `google-chrome-stable_current_amd64.deb` absent from disk and from `git log --all` (confirmed independently). `.gitignore` covers Python/Node caches, pipeline data, model output, secrets, `.gsd/`, `.venv/`/`venv/`, `.docker/`, with the snapshot-history re-inclusion (`!data/snapshots/`) intact. All three workflow files (`ci.yml`, `daily.yml`, `weekly.yml`) are tracked (`git log` shows their commits). |
| 3 | Every push and PR runs lint, typecheck, pytest + API tests, and a frontend-build + Playwright job against uvicorn serving the built frontend with fixture data — and the build fails on any regression | ✓ VERIFIED | `ci.yml` parses with `push`+`pull_request` triggers, a `concurrency` group with `cancel-in-progress: true`, and workflow-default `permissions: contents: read`. `lint-build` runs `ruff check .` (independently re-run: "All checks passed!") then `npm --prefix frontend run build` as the real typecheck gate (the inert `npm run typecheck` script is never invoked — confirmed by grep). `test` (`needs: lint-build`) downloads the `frontend-dist` artifact, guards on `frontend/dist/index.html`/`404.html`, then runs `python -m pytest` (fixed from bare `pytest` in commit `11cd68e` after the first real CI run failed on `ModuleNotFoundError`) and `npm --prefix frontend test`. `e2e` (`needs: test`) delegates the full three-variant server lifecycle to `e2e/playwright.config.ts` with no `E2E_PYTHON`/`E2E_VARIANTS` override. No step in the chain carries `continue-on-error` except the Security-tab SARIF upload. Human-reported: PR run passed on the third attempt (two real, root-caused fixes applied), all jobs green. |
| 4 | A multi-stage `python:3.14-slim` image builds, passes a smoke test proving the CBC solver is available and `/health` responds, and publishes to GHCR with SHA-pinned actions and a scoped `GITHUB_TOKEN` (deploy step stubbed) | ✓ VERIFIED | `Dockerfile` has exactly two `FROM python:3.14-slim` stages (`builder`, `runtime`); builder installs `requirements.txt` with `--require-hashes`; runtime installs `libstdc++6` (CBC) and `libgomp1` (LightGBM's OpenMP dlopen — added in commit `65cd2e7` after the first real image-job failure), creates a non-root `appuser` before `CMD`, and starts `uvicorn api.main:app`. No model-artifact reference anywhere in the file. `scripts/smoke_test.sh` boots the image against the frozen `e2e/fixtures/v1/normal` set, polls `/api/health`, then POSTs to `/api/solve` and asserts exactly 15 `player_code` entries — a real CBC solve, not an import check. `ci.yml`'s `image` job (`needs: e2e`, `security-events: write`, no `packages` permission) builds with `push: false`/`load: true` and runs the smoke test before Trivy. `publish` (`needs: image`, `packages: write`, `if: github.ref == 'refs/heads/main'`) logs in to `ghcr.io` with `secrets.GITHUB_TOKEN`, derives `type=sha`+`latest` tags via `docker/metadata-action`, and ends with a no-op "Deploy placeholder" step that performs no deployment. Every one of 30 `uses:` lines across all three workflow files is pinned to a 40-character commit SHA (repo-wide count verified: `uses=30 sha_pinned=30`). Human-reported: main-branch run passed **including** `publish`, evidenced by a linked GitHub Actions run URL (`.../actions/runs/33950933101/job/101266347373`). |
| 5 | A Trivy vulnerability scan reports on the image on every build | ✓ VERIFIED | `image` job runs `aquasecurity/trivy-action` against `local/fpl:ci` with no `exit-code` input (report-only by the action's own default), uploads the SARIF as a build artifact unconditionally, then attempts the Security-tab `codeql-action/upload-sarif` with `continue-on-error: true` (the only step in the workflow permitted that flag). Human-reported: 187 open, report-only findings are visible in the repository's Security tab after the green run. |
| 6 | Requirement traceability: CI-01 through CI-05, SEC-02 and SEC-04 are each satisfied by a plan in this phase and marked complete in REQUIREMENTS.md with no orphans | ✓ VERIFIED | Every one of the 7 requirement IDs appears in exactly one plan's `requirements:` frontmatter (05-01: SEC-02, CI-01; 05-02: CI-03; 05-03: CI-01, CI-02, CI-04, CI-05; 05-04: SEC-04; 05-05: CI-04) and all 7 rows in REQUIREMENTS.md's traceability table read "Phase 5 / Complete". No Phase-5-mapped requirement is missing from a plan's `requirements:` list. |
| 7 | Branch protection on `main` requires the `ci.yml` verification jobs to pass before a merge (D-15), so a red run cannot publish a broken `latest` tag | ⚠️ UNCERTAIN | 05-05-PLAN.md's Task 2 checkpoint explicitly instructed the developer to configure this (Stage 2), and it is one of this plan's own `must_haves.truths` (`verification: backstop`). 05-05-SUMMARY.md's own coverage table (item D4) records `verification: []` and states the developer's reported checkpoint items did not explicitly confirm it — "cannot be verified locally (no gh CLI, no API access)... Carry into `/gsd-verify-work` or a manual repo-settings check." No override was recorded. Routed to human verification below. |
| 8 | An image tagged with the commit SHA and `latest` is visible in the repository's GHCR package listing, with its size recorded for GHCR budget sizing | ⚠️ UNCERTAIN | The main-branch `publish` job is confirmed green (truth #4), which structurally implies an image was pushed, but 05-05-SUMMARY.md explicitly states the exact tag names and image size were "not captured verbatim" by the developer's report and "should be pulled from the Actions run UI" before a retention-policy decision. Not independently queryable from this environment (no `gh` CLI, no GHCR API token). Routed to human verification below. |

**Score:** 6/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.in` / `requirements-dev.in` | Runtime/dev dependency sources | ✓ VERIFIED | Present, `requirements-dev.in` line 1 is `-r requirements.in`, `uv` absent from both |
| `requirements.txt` / `requirements-dev.txt` | Hash-verified compiled locks | ✓ VERIFIED | 531 / 634 `--hash=sha256:` lines, no unpinned line, no browser-automation chain |
| `ruff.toml` | Python lint config | ✓ VERIFIED | `select = ["E4","E7","E9","F"]`, empty `ignore`; `ruff check .` exits 0 |
| `Dockerfile` | Multi-stage image | ✓ VERIFIED | Two named stages, hashed install, `libstdc++6`+`libgomp1`, non-root `USER`, `uvicorn` `CMD`, no model reference |
| `.dockerignore` | Build-context exclusions | ✓ VERIFIED | All required exclusions present; `!frontend/dist`/`!frontend/dist/**` re-included; `data/snapshots` not re-included |
| `scripts/smoke_test.sh` | Container smoke test | ✓ VERIFIED | Executable, `bash -n` clean, both fail-fast guards present, asserts 15 `player_code` entries |
| `scripts/preflight.sh` | Local CI reproduction | ✓ VERIFIED | Executable, present, ephemeral-venv install pattern confirmed by inspection; human-reported `PREFLIGHT PASSED` after the redaction fix |
| `.github/workflows/ci.yml` | Chained 5-job workflow | ✓ VERIFIED | Parses; jobs in order `lint-build → test → e2e → image → publish`; every scoping/permission/trigger assertion holds |
| `.github/workflows/daily.yml` / `weekly.yml` | Modernized, disarmed schedulers | ✓ VERIFIED | No `schedule:` trigger, `workflow_dispatch` present, py3.14, `--require-hashes`, bot identity, SHA-pinned |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `ci.yml` `lint-build` | `ci.yml` `test` | `frontend-dist` artifact upload/download | ✓ WIRED | Confirmed both `upload-artifact`/`download-artifact` steps present with matching artifact name; existence guard on `index.html`/`404.html` present |
| `ci.yml` `test` | `requirements.txt`/`requirements-dev.txt` | `--require-hashes` install | ✓ WIRED | Confirmed on a non-comment line |
| `ci.yml` `e2e` | `e2e/playwright.config.ts` | delegated server lifecycle, no `E2E_PYTHON`/`E2E_VARIANTS` override | ✓ WIRED | Confirmed absent from the job body |
| `ci.yml` `image` | `scripts/smoke_test.sh` | `bash scripts/smoke_test.sh local/fpl:ci` before Trivy | ✓ WIRED | Confirmed step present and ordered before the Trivy step |
| `ci.yml` `publish` | GHCR | `docker/login-action` + `secrets.GITHUB_TOKEN` + `docker/build-push-action` (`push: true`) | ✓ WIRED | Confirmed; gated on `refs/heads/main`; human-reported the real push succeeded |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Lint gate is green on the current tree | `ruff check .` | "All checks passed!" | ✓ PASS |
| Backend test suite still collects at the documented count | `python -m pytest --collect-only -q` | "77 tests collected in 0.63s" | ✓ PASS |
| Every lock line is pinned | grep-based hash/pin count | 531 / 634 hash lines, 0 unpinned lines | ✓ PASS |
| Repo-wide action SHA pinning | grep-based `uses:`/SHA count across `.github/workflows/` | `uses=30 sha_pinned=30` | ✓ PASS |
| No tracked personal-email/credential literal | `git ls-files` + pattern scan | "scanned 427 files", 0 hits | ✓ PASS |
| Real CI run end to end (build, smoke, scan, publish) | N/A — no container runtime, no `gh` CLI in this environment | Human-reported, with a linked run URL | ? SKIP (see human verification) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention exists in this repository and none is declared in any Phase 5 PLAN/SUMMARY. Step 7c: SKIPPED (no probes declared).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| CI-01 | 05-01, 05-03 | GitHub Actions workflow — lint, typecheck, pytest + API tests on every push/PR | ✓ SATISFIED | `ci.yml` `lint-build`+`test` jobs; ruff + build-as-typecheck + pytest confirmed |
| CI-02 | 05-03 | Frontend build + Playwright E2E job, cached browsers, against uvicorn serving built frontend + fixture data | ✓ SATISFIED | `ci.yml` `e2e` job delegates to `playwright.config.ts`; browser cache present |
| CI-03 | 05-02 | Multi-stage Dockerfile on `python:3.14-slim`, locked deps, CBC installed, container smoke test | ✓ SATISFIED | `Dockerfile` + `scripts/smoke_test.sh`; human-reported smoke pass in the real run |
| CI-04 | 05-03, 05-05 | Image published to GHCR, SHA-pinned actions, scoped `GITHUB_TOKEN`, deploy stubbed | ✓ SATISFIED | `publish` job; 30/30 SHA-pinned; real green main-branch run with publish, per human report |
| CI-05 | 05-03 | Trivy image vulnerability scan job | ✓ SATISFIED | `image` job's Trivy step; 187 findings human-reported in Security tab |
| SEC-02 | 05-01 | Dependencies pinned/locked, verified installable in a fresh environment with cp314 wheels | ✓ SATISFIED | Hash-locked, clean-venv install, zero source compilation (05-01-SUMMARY.md) |
| SEC-04 | 05-04 | Repo hygiene — Chrome `.deb` removed, proper `.gitignore`, workflows tracked | ✓ SATISFIED | `.deb` confirmed absent from disk/history; `.gitignore` reconciled; workflows tracked |

No orphaned requirements: all 7 IDs mapped to Phase 5 in REQUIREMENTS.md appear in at least one plan's `requirements:` frontmatter, and no plan claims a requirement not listed under Phase 5.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` markers found in any Phase-5-modified file. The one `# Deploy placeholder (stub, CI-04)` comment in `ci.yml` is an intentional, requirement-mandated stub (CI-04 explicitly asks for a stubbed deploy step), not a debt marker.

The independent 05-REVIEW.md (standard depth, 20 files, 0 critical / 5 warnings / 4 info) surfaced five warnings worth carrying forward as advisory, none of which block this phase's success criteria for a private, solo-dev repository at its current stage:

| File | Issue | Severity | Impact on this phase's goal |
|------|-------|----------|------------------------------|
| `ci.yml:23-25` (WR-01) | `pull_request` types exclude `synchronize` — follow-up commits on a **forked** PR get no CI run | ⚠️ Warning | Low impact today (private repo, no external forks); a real gap if the repo opens to outside contributors |
| `ci.yml` image/publish jobs, `Dockerfile` (WR-02) | The image smoke-tested/scanned and the image published are two independent `docker build` invocations sharing a GHA cache, not provably identical bits | ⚠️ Warning | The mutable `FROM python:3.14-slim` tag and unpinned apt packages mean a cache-miss could push an image that was never smoke-tested |
| `Dockerfile:14,25,38` (WR-03) | Base image and apt packages (`libstdc++6`, `libgomp1`) are unpinned, unlike the hash-locked Python deps | ⚠️ Warning | Undermines the reproducibility goal SEC-02 established for the rest of the stack |
| `weekly.yml:26-33` (WR-04) | Will crash with a raw traceback if dispatched today — no model artifact exists or is fetched | ⚠️ Warning | Out of Phase 5's scope by design (D-12: model delivery is next milestone); still a rough edge for a dispatch-only workflow |
| `scripts/preflight.sh:120` (WR-05) | Credential-scan regex requires both-side quoting, missing unquoted `KEY=value` secret shapes | ⚠️ Warning | Reduces (does not eliminate) the local pre-push safety net's coverage |

These are pre-existing/adjacent findings surfaced by an independent code review, not newly discovered gaps in this verification pass, and are advisory rather than blocking — none contradicts a roadmap Success Criterion or a plan's `must_haves`.

## Deferred Items

None identified — no later-phase goal or success criteria explicitly covers the two UNCERTAIN items (branch protection, GHCR tag/size capture); they are genuine open items for this phase, not intentionally scheduled future work.

### Human Verification Required

### 1. Branch protection on `main`

**Test:** Open the GitHub repository's Settings > Branches page for `main`.
**Expected:** A protection rule requiring a pull request before merging, with `lint-build`, `test`, `e2e`, and `image` (not `publish`) listed as required status checks.
**Why human:** No `gh` CLI or API token exists in this environment to query repository settings; the developer's checkpoint report (05-05-SUMMARY.md) did not explicitly confirm this configuration step, and a green main-branch run alone does not distinguish a protected merge from a direct push.

### 2. GHCR image tags and size

**Test:** Open the repository's Packages tab on GitHub and view the published image's tags and reported size.
**Expected:** One tag derived from the commit SHA and one `latest` tag are both present; the size is noted for future 500MB private-tier budget planning.
**Why human:** No `gh` CLI, API token, or container runtime exists in this environment to query GHCR directly, and 05-05-SUMMARY.md records that these specific data points were not captured verbatim from the developer's report.

### Gaps Summary

No FAILED truths and no blocking anti-patterns were found — every structural, lint, build, dependency-lock, and workflow-wiring claim this phase makes is independently verified against the current codebase, and the phase's own SUMMARY documents a real, human-observed green CI run (including the `publish` job) reached only after two genuine CI-environment bugs (bare `pytest` on the runner, missing `libgomp1` in the runtime image) were found and fixed — exactly the outcome the D-14 human-gated first push exists to surface, not a simulated pass.

The phase is held at `human_needed` rather than `passed` for two items the phase's own plan (05-05) explicitly flagged as `verification: backstop` and its own SUMMARY explicitly could not confirm: (1) whether branch protection was actually configured on `main`, and (2) the exact GHCR tag names and image size. Both are cheap for the developer to check directly in the GitHub UI and do not indicate the pipeline itself is broken — they indicate two loose ends in what could be *observed* about the pipeline from this environment. Given SEC-04's own T-05-03-03/T-05-05-02 threat mitigation depends specifically on branch protection standing between a red run and a moved `latest` tag, item 1 is worth confirming before treating CI-04's publish-safety guarantee as fully closed.

---

_Verified: 2026-09-05T07:21:02Z_
_Verifier: Claude (gsd-verifier)_
