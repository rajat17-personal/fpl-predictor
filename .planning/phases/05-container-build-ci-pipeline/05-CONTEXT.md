# Phase 5: Container Build & CI Pipeline - Context

**Gathered:** 2026-09-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Every push is automatically verified and produces a publishable, scanned container image: dependencies locked and hash-verified (CI-01/SEC-02), repo made CI-ready (SEC-04 — Chrome `.deb` deleted, `.gitignore` complete, workflows tracked), a single GitHub Actions workflow running lint/typecheck/pytest+API tests/frontend build/Playwright-vs-fixture-uvicorn on every push and PR (CI-01/CI-02), a multi-stage `python:3.14-slim` image with CBC that passes a fixture-mode smoke test and publishes to GHCR with SHA-pinned actions and a scoped `GITHUB_TOKEN` (CI-03/CI-04), and a Trivy scan reporting on every build (CI-05).

Out of this phase: live deployment (next milestone), Phase 6's security/reliability/observability fixes (CORS, file handles, cron retries, schema validation), and arming the Actions schedulers for daily/weekly pipeline runs — the local WSL cron stays production for the time-critical daily snapshot.

**Repo scout facts the planner can rely on:** the 134MB Chrome `.deb` was never committed (`.git` is 10MB; `*.deb` is gitignored) — removal is a working-tree delete, no history rewrite. `web/` and `web/data/*.json` ARE tracked. `models/artifacts/` is gitignored — `xp_model.joblib` is NOT in any checkout. No git remote exists yet. `/api/health` reads `_state` without `_refresh()`, so a model-less container boots and answers health; fixture mode (`FPL_FIXTURE_DIR`) skips the `joblib.load` entirely.

</domain>

<decisions>
## Implementation Decisions

### Dependency locking (SEC-02)
- **D-01:** **uv with pip-compatible output.** uv compiles `requirements.in` → fully-pinned `requirements.txt` with `--hash` lines. CI and Docker consume it with plain `pip install` — uv is a lockfile compiler, never a runtime dependency. (uv itself is a new tool → route through the package-legitimacy gate.)
- **D-02:** **Runtime + dev split:** `requirements.in` (API/pipeline runtime) and `requirements-dev.in` (pytest, responses, lint tooling). The Docker image installs the runtime lock only; CI installs both. Pin from a clean venv, never `pip freeze` inside the conda env.
- **D-03:** **cp314 wheel-gap fallback is pre-authorized:** if any ML dep (LightGBM, scikit-learn, PyArrow, PuLP) lacks a cp314 wheel, compile it from source in the Docker **builder stage** (compilers in builder only; runtime stage stays `python:3.14-slim`). Dropping to 3.13 and blocking the phase were both rejected.
- **D-04:** **Hash enforcement everywhere:** installs in CI and Docker run with `--require-hashes` against the compiled lockfiles. — **Reversibility:** reversible.

### Docker image contents (CI-03)
- **D-05:** **No model artifact in the image (or in git).** Image = code + locked deps + static assets. The model is supplied at deploy time (volume/bind) next milestone; committing the 7MB `xp_model.joblib` and CI-artifact/Release delivery were both rejected. — **Reversibility:** costly — the smoke test (D-07), the modernized weekly.yml posture (D-12), and the deploy story next milestone are all built on "model arrives at runtime"; baking it later reopens git-churn and image-rebuild-per-retrain questions.
- **D-06:** **Both static frontends baked in:** COPY vanilla `web/` (with its tracked `web/data/*.json`) and the CI-built `frontend/dist/`. The serving default stays whatever `api/main.py` does (vanilla until CUT-01); Phase 7's cutover becomes a config/env flip with no image rework.
- **D-07:** **Smoke test = /health + a real fixture-mode solve.** Run the container with `FPL_FIXTURE_DIR` pointing at the v1 e2e fixtures, curl `/api/health`, then POST a real `/api/solve` — the actual ILP runs through CBC inside the container. This is the proof of "CBC solver is available", not a mere presence check.

### CI workflow shape & publish policy (CI-01/CI-02/CI-04/CI-05)
- **D-08:** **One `ci.yml`, chained jobs:** lint/typecheck → backend + frontend tests → Playwright E2E → docker build + smoke + Trivy → publish. Jobs share the built `frontend/dist` as an artifact (the pytest SPA-fallback test REQUIRES dist to exist before the backend suite — 04-REVIEW critical finding).
- **D-09:** **Publish on main only, tags = commit SHA + moving `latest`.** PR/branch builds run the full verification including docker build + smoke + scan, but never push to GHCR.
- **D-10:** **Trivy is report-only:** SARIF uploaded to the GitHub Security tab, never blocks the build. Tighten to a severity gate next milestone when deploys exist.
- **D-11:** **daily.yml / weekly.yml are modernized in this phase:** py3.14, hashed lockfile installs, correct git identity (drop the hardcoded personal email; use the github-actions bot pattern).
- **D-12:** **…but their schedules stay OFF:** `workflow_dispatch`-only until the model-delivery question is settled next milestone alongside hosting. The local WSL cron remains the one production scheduler for the time-critical daily snapshot — nothing in this phase may disturb it. — **Reversibility:** reversible (arming is a one-line cron trigger later).

### GitHub repo setup & push
- **D-13:** **Private repo now; revisit visibility at launch** (e.g. open-sourcing the frontend only). Predictions data (`web/data`) and model/optimizer code stay private pre-monetization. Budget accordingly: 2000 Actions min/month, 500MB GHCR private storage — image size and registry retention matter.
- **D-14:** **All pushes to GitHub are executed manually by the user.** Claude prepares everything (workflows, Dockerfile, lockfiles, hygiene) but repo creation and every `git push` is a human action. Phase verification still includes "user pushes → real CI run goes green end-to-end → image visible in GHCR" as a blocking human checkpoint; plans must model this as a `checkpoint:human` gate, not an automated step.
- **D-15:** **PRs + required checks on main:** branch protection requiring the ci.yml verify jobs before merge, matching the existing feature-branch habit. A red main must not publish a broken `:latest`.
- **D-16:** **Pre-push hygiene pass is an in-phase task:** grep tracked files for emails/keys/tokens, swap workflow git identity to the actions bot, confirm `.env`/`.deb`/`models/artifacts` ignored. No history rewrite — repo is young and going up private.

### Claude's Discretion
- CBC installation method (apt `coinor-cbc` vs PuLP's bundled binary) — whatever survives the fixture-solve smoke test on slim.
- Which Python packages/dirs get COPY'd into the image (excluding tests/e2e/.planning is expected); .dockerignore contents.
- CI caching strategy (pip/npm/Playwright browsers/docker layer cache), job names, concurrency groups, timeout values.
- Exact uv invocation and lockfile file names; how the two locks map onto Docker layers.
- Lint/typecheck tooling for the Python side (none is configured today — ruff or similar is the planner/researcher's call, routed through the package-legitimacy gate).
- GHCR retention/cleanup policy within the 500MB private free tier.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & constraints
- `.planning/ROADMAP.md` §Phase 5 — goal, success criteria, research flags (cp314 wheels; pin from clean venv; image-size warning)
- `.planning/REQUIREMENTS.md` — CI-01…CI-05, SEC-02, SEC-04 texts
- `.planning/STATE.md` §Blockers/Concerns — Phase 4→5 handoff: CI must build `frontend/dist/` before the backend pytest suite; cp314 wheel availability unknown

### The E2E/CI seam (Phase 4 built it for this phase)
- `.planning/phases/04-e2e-regression-suite/04-CONTEXT.md` — D-01…D-05: fixture-mode topology, `webServer` owns build+uvicorn, local runs are CI-identical; CI-02 consumes the suite verbatim
- `e2e/playwright.config.ts` — the exact build+serve commands and `FPL_FIXTURE_DIR`/`FPL_FIXTURE_DATA_DIR` env seam CI must reproduce; locale/timezone pinning rationale
- `e2e/fixtures/` + `MANIFEST.md` — the immutable v1 fixture sets; the container smoke test (D-07) reuses these
- `api/main.py` — fixture seam, `/api/health` (no `_refresh`), static mount logic (`web/` default vs `frontend/dist` fixture mode), model load in `_refresh()`
- `tests/test_fixture_mode.py` — the SPA-fallback test that 500s without a built `frontend/dist/`
- `pytest.ini` — plugin disables (`-p no:playwright -p no:seleniumbase`) the CI pytest invocation must respect

### Current CI/dependency surface (what this phase replaces/extends)
- `requirements.txt` — today's `>=` constraints; source material for `requirements.in` split
- `.github/workflows/daily.yml`, `.github/workflows/weekly.yml` — dormant schedulers to modernize (D-11/D-12); note weekly.yml's false "model in repo" assumption and hardcoded git identity (working tree has uncommitted edits to weekly.yml + .gitignore — reconcile, don't clobber)
- `frontend/package.json`, `frontend/package-lock.json` — Node-side pins; `npm run build` (`tsc -b`) is the real typecheck (`npm run typecheck` is a no-op — never use it as a gate)
- `.gitignore` — already covers `.env`/`*.deb`/`models/artifacts`/`frontend/dist`; keeps `data/snapshots/` re-included (irreplaceable)
- `.planning/codebase/CONCERNS.md` — unpinned-deps, Chrome-.deb, and supply-chain items this phase closes (SEC-02/SEC-04 slice only; the rest is Phase 6)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 4's fixture-mode topology is the entire CI-02 and smoke-test story: `npx playwright test` is the single entry point; `webServer` builds dist and boots fixture-fed uvicorn itself
- `web/` + `web/data/*.json` tracked in git — free to COPY into the image; `frontend/dist` already produced by CI test jobs, reusable as the image's second static payload
- `/api/health` works with no model artifact present — the model-less image (D-05) can still prove liveness
- `scripts/verify_frontend_build.sh` — existing build-verification precedent

### Established Patterns
- Package-legitimacy gate: uv, ruff (or chosen lint tool), and any new Action beyond the SHA-pinned core set go through blocking human approval with exact pins
- Actions SHA-pinning is a locked roadmap requirement (CI-04) — applies to every `uses:` line in all three workflows
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD` / pytest.ini plugin disables must carry into the CI pytest step
- Conda env `python314` is dev-only; CI and Docker use clean python:3.14 environments with the pip lockfiles

### Integration Points
- `ci.yml` (new) + modernized `daily.yml`/`weekly.yml` in `.github/workflows/`
- `Dockerfile` + `.dockerignore` (new, repo root); smoke-test script wiring into the docker job
- `requirements.in`/`requirements-dev.in` → compiled, hashed locks consumed by CI jobs and the Dockerfile
- Phase 6 inherits: Trivy gate tightening, cron retry/alerting for the modernized workflows, CORS/env hardening inside the image's runtime config
- Phase 7 (CUT-01) inherits: the D-06 image already contains `frontend/dist`, so cutover is the `api/main.py` mount flip only
- Next milestone inherits: model-delivery-at-deploy decision (D-05/D-12), branch-protection is already in place for collaboration

</code_context>

<specifics>
## Specific Ideas

- "The phase's own success criteria become literally verified, not simulated" — but with D-14's constraint: Claude stages everything, the **user personally runs every push**, then the green run + GHCR image is checked as a human-gated verification step
- The smoke test should be the real thing: an actual ILP solve through CBC inside the running container on the frozen v1 pool — not `import pulp`
- weekly.yml's "requires xp_model.joblib in the repo" comment is a known false assumption to be corrected during modernization, not preserved

</specifics>

<deferred>
## Deferred Ideas

- **Arming daily/weekly Actions schedules + model delivery to CI** — next milestone, alongside hosting; local WSL cron is production until then (D-12)
- **Trivy severity gating (fail on CRITICAL)** — next milestone, when deploys exist (D-10)
- **Repo visibility revisit at launch** — possibly open-sourcing the frontend only (D-13)
- **Semver/release tagging ceremony for blessed images** — when real deploys start consuming the registry (D-09)
- **pip-audit / dependency-CVE job** — natural Phase 6 observability/security companion; not required by SEC-02

</deferred>

---

*Phase: 5-Container Build & CI Pipeline*
*Context gathered: 2026-09-04*
