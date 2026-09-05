# Phase 5: Container Build & CI Pipeline - Research

**Researched:** 2026-09-04
**Domain:** Python dependency locking, GitHub Actions CI, multi-stage Docker builds, GHCR publishing, container vulnerability scanning
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dependency locking (SEC-02)**
- **D-01:** uv with pip-compatible output. uv compiles `requirements.in` → fully-pinned `requirements.txt` with `--hash` lines. CI and Docker consume it with plain `pip install` — uv is a lockfile compiler, never a runtime dependency. (uv itself is a new tool → route through the package-legitimacy gate.)
- **D-02:** Runtime + dev split: `requirements.in` (API/pipeline runtime) and `requirements-dev.in` (pytest, responses, lint tooling). The Docker image installs the runtime lock only; CI installs both. Pin from a clean venv, never `pip freeze` inside the conda env.
- **D-03:** cp314 wheel-gap fallback is pre-authorized: if any ML dep (LightGBM, scikit-learn, PyArrow, PuLP) lacks a cp314 wheel, compile it from source in the Docker builder stage (compilers in builder only; runtime stage stays `python:3.14-slim`). Dropping to 3.13 and blocking the phase were both rejected.
- **D-04:** Hash enforcement everywhere: installs in CI and Docker run with `--require-hashes` against the compiled lockfiles. Reversibility: reversible.

**Docker image contents (CI-03)**
- **D-05:** No model artifact in the image (or in git). Image = code + locked deps + static assets. The model is supplied at deploy time (volume/bind) next milestone; committing the 7MB `xp_model.joblib` and CI-artifact/Release delivery were both rejected. Reversibility: costly — the smoke test (D-07), the modernized weekly.yml posture (D-12), and the deploy story next milestone are all built on "model arrives at runtime"; baking it later reopens git-churn and image-rebuild-per-retrain questions.
- **D-06:** Both static frontends baked in: COPY vanilla `web/` (with its tracked `web/data/*.json`) and the CI-built `frontend/dist/`. The serving default stays whatever `api/main.py` does (vanilla until CUT-01); Phase 7's cutover becomes a config/env flip with no image rework.
- **D-07:** Smoke test = /health + a real fixture-mode solve. Run the container with `FPL_FIXTURE_DIR` pointing at the v1 e2e fixtures, curl `/api/health`, then POST a real `/api/solve` — the actual ILP runs through CBC inside the container. This is the proof of "CBC solver is available", not a mere presence check.

**CI workflow shape & publish policy (CI-01/CI-02/CI-04/CI-05)**
- **D-08:** One `ci.yml`, chained jobs: lint/typecheck → backend + frontend tests → Playwright E2E → docker build + smoke + Trivy → publish. Jobs share the built `frontend/dist` as an artifact (the pytest SPA-fallback test REQUIRES dist to exist before the backend suite — 04-REVIEW critical finding).
- **D-09:** Publish on main only, tags = commit SHA + moving `latest`. PR/branch builds run the full verification including docker build + smoke + scan, but never push to GHCR.
- **D-10:** Trivy is report-only: SARIF uploaded to the GitHub Security tab, never blocks the build. Tighten to a severity gate next milestone when deploys exist.
- **D-11:** daily.yml / weekly.yml are modernized in this phase: py3.14, hashed lockfile installs, correct git identity (drop the hardcoded personal email; use the github-actions bot pattern).
- **D-12:** …but their schedules stay OFF: `workflow_dispatch`-only until the model-delivery question is settled next milestone alongside hosting. The local WSL cron remains the one production scheduler for the time-critical daily snapshot — nothing in this phase may disturb it. Reversibility: reversible (arming is a one-line cron trigger later).

**GitHub repo setup & push**
- **D-13:** Private repo now; revisit visibility at launch (e.g. open-sourcing the frontend only). Predictions data (`web/data`) and model/optimizer code stay private pre-monetization. Budget accordingly: 2000 Actions min/month, 500MB GHCR private storage — image size and registry retention matter.
- **D-14:** All pushes to GitHub are executed manually by the user. Claude prepares everything (workflows, Dockerfile, lockfiles, hygiene) but repo creation and every `git push` is a human action. Phase verification still includes "user pushes → real CI run goes green end-to-end → image visible in GHCR" as a blocking human checkpoint; plans must model this as a `checkpoint:human` gate, not an automated step.
- **D-15:** PRs + required checks on main: branch protection requiring the ci.yml verify jobs before merge, matching the existing feature-branch habit. A red main must not publish a broken `:latest`.
- **D-16:** Pre-push hygiene pass is an in-phase task: grep tracked files for emails/keys/tokens, swap workflow git identity to the actions bot, confirm `.env`/`.deb`/`models/artifacts` ignored. No history rewrite — repo is young and going up private.

### Claude's Discretion
- CBC installation method (apt `coinor-cbc` vs PuLP's bundled binary) — whatever survives the fixture-solve smoke test on slim.
- Which Python packages/dirs get COPY'd into the image (excluding tests/e2e/.planning is expected); .dockerignore contents.
- CI caching strategy (pip/npm/Playwright browsers/docker layer cache), job names, concurrency groups, timeout values.
- Exact uv invocation and lockfile file names; how the two locks map onto Docker layers.
- Lint/typecheck tooling for the Python side (none is configured today — ruff or similar is the planner/researcher's call, routed through the package-legitimacy gate).
- GHCR retention/cleanup policy within the 500MB private free tier.

### Deferred Ideas (OUT OF SCOPE)
- Arming daily/weekly Actions schedules + model delivery to CI — next milestone, alongside hosting; local WSL cron is production until then (D-12)
- Trivy severity gating (fail on CRITICAL) — next milestone, when deploys exist (D-10)
- Repo visibility revisit at launch — possibly open-sourcing the frontend only (D-13)
- Semver/release tagging ceremony for blessed images — when real deploys start consuming the registry (D-09)
- pip-audit / dependency-CVE job — natural Phase 6 observability/security companion; not required by SEC-02
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| CI-01 | GitHub Actions workflow — lint, typecheck, pytest + API tests on every push/PR | Standard Stack (ruff), Architecture Patterns diagram, Validation Architecture test map |
| CI-02 | Frontend build + Playwright E2E job with cached browsers, run against uvicorn serving the built frontend + fixture data | Architecture Patterns diagram (job chaining + `frontend/dist` artifact sharing), reuses Phase 4's `e2e/playwright.config.ts` verbatim (verified read) |
| CI-03 | Multi-stage Dockerfile on `python:3.14-slim` with locked deps, CBC solver installed, and a container smoke test | Pattern 1 (Dockerfile skeleton), Pattern 2 (model-less boot), Pattern 3 (smoke-test payload), Pitfall 2 (libstdc++6) |
| CI-04 | Image published to GHCR with SHA-pinned actions and scoped `GITHUB_TOKEN`; deploy step stubbed | Standard Stack (Supporting) table with resolved SHAs, Code Examples "GHCR publish" |
| CI-05 | Trivy image vulnerability scan job | Code Examples "Trivy scan, report-only, artifact-safe", Pitfall 4 (private-repo SARIF gate) |
| SEC-02 | Dependencies pinned/locked (uv lock or equivalent), verified installable in a fresh environment with cp314 wheels | Summary + Standard Stack (Runtime stack table) — directly, verified live this session via `pip install --require-hashes` |
| SEC-04 | Repo hygiene — Chrome .deb removed, proper `.gitignore`, workflows tracked in git | Validation Architecture test map (SEC-04 row), repo-scout facts corroborated by direct `.gitignore`/`ls` reads |
</phase_requirements>

## Summary

The phase's headline risk — cp314 wheel availability for LightGBM, scikit-learn, PyArrow, and PuLP — is **resolved, not open**. A real `pip install --require-hashes` round trip in a clean Python 3.14.3 venv (not the conda env) succeeded for the entire ML+API stack with zero source compilation: `lightgbm==4.7.0`, `scikit-learn==1.9.0`, `pyarrow==25.0.1`, `pulp==3.3.2`, plus `pandas==3.0.5`, `numpy==2.5.2`, `scipy==1.18.1`, `fastapi==0.141.1`, `uvicorn==0.52.4`. D-03's from-source builder-stage fallback is pre-authorized but will not be needed for the current pin set. The one real wheel-format nuance: LightGBM ships `py3-none-*` wheels (its extension is loaded via ctypes, not a compiled CPython module), so it is Python-ABI-agnostic and was never actually at risk — the risk lived entirely in scikit-learn and PyArrow, both of which publish real `cp314` wheels as of their current releases.

PuLP's `pulp.PULP_CBC_CMD` — exactly what `optimize/squad_ilp.py`, `optimize/transfers.py`, and `optimize/multi_period.py` already call — still bundles a working Linux x86_64 CBC binary inside the wheel (verified by unzipping it and running a real solve). The container therefore needs **zero code changes and no `coinor-cbc` apt package** — just one small `apt-get install libstdc++6` in the runtime stage, because `python:3.14-slim`'s own build process strips every apt-managed library that CPython itself doesn't dynamically link, and CPython doesn't need libstdc++ (the CBC binary does). This directly resolves the CONTEXT.md Claude's-Discretion item on CBC installation method.

Two findings actively change the CONTEXT.md decisions as written: (1) `understatapi` unpinned resolves to an old release that pulls in `selenium` + `trio` + `websocket-client` (a real image-size and attack-surface cost); pinning `understatapi==0.7.1` removes that entire chain with no behavior loss. (2) D-10's plan to upload Trivy's SARIF to the GitHub Security tab is in tension with D-13's private-repo decision — GitHub's private-repo code-scanning gate is documented inconsistently for third-party (non-CodeQL) SARIF, so the safe, D-10-compliant design is to make the Security-tab upload `continue-on-error: true` and *also* always upload the raw SARIF as a build artifact, so CI-05's requirement is met regardless of which behavior GitHub actually exhibits on this account.

**Primary recommendation:** Pin runtime deps to the exact versions verified below via `uv pip compile --generate-hashes --python-version 3.14`, keep `PULP_CBC_CMD` as-is and add `libstdc++6` to the Docker runtime stage, pin `understatapi==0.7.1`, and make the Trivy Security-tab upload non-blocking with an artifact fallback.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dependency locking/hashing | Build tooling (uv, dev-time only) | CI / Docker (consume via pip) | uv never ships in the runtime image; it only compiles the lockfile (D-01) |
| Lint/typecheck | CI (GitHub Actions job) | — | Static analysis gates the push, no runtime component |
| Backend/API tests | CI (GitHub Actions job) | API tier (code under test) | pytest exercises `api/`, `optimize/`, `models/` in-process |
| Frontend build + E2E | CI (GitHub Actions job) | Browser (Playwright drives Chromium) | `webServer` in `playwright.config.ts` owns build+serve; CI reproduces it verbatim |
| Container image build | CI / Docker | API tier (what the image runs) | Multi-stage: builder compiles/resolves, runtime serves `uvicorn api.main:app` |
| CBC solver availability | Container runtime (OS libs + bundled binary) | API tier (PuLP call site) | Solve happens in-process via subprocess to the bundled `cbc` executable |
| Vulnerability scanning | CI (GitHub Actions job) | GitHub Security tab (best-effort) | Trivy scans the built image; SARIF upload is best-effort per the private-repo gate |
| Image publish | CI (GitHub Actions job) → GHCR | — | `docker/build-push-action` + `docker/login-action` with scoped `GITHUB_TOKEN` |

## Package Legitimacy Audit

| Package | Registry | Age (repo) | Downloads/Stars | Source Repo | Verdict | Disposition |
|---------|----------|-----------|-----------------|-------------|---------|-------------|
| `uv` | PyPI | repo created 2023-10-02 [VERIFIED: GitHub API `api.github.com/repos/astral-sh/uv`], 89,430 stars | weekly downloads unavailable from this environment | github.com/astral-sh/uv | `[SUS]` (gate signal: `too-new` + `unknown-downloads` — measures latest **release** date, not project age) [VERIFIED: `gsd-tools query package-legitimacy check`] | Flagged — planner must add `checkpoint:human-verify` before install. Package name `[ASSUMED]` (training knowledge, not official-docs-sourced) despite registry confirmation. |
| `ruff` | PyPI | repo created 2022-08-09 [VERIFIED: GitHub API `api.github.com/repos/astral-sh/ruff`], 49,471 stars | weekly downloads unavailable from this environment | github.com/astral-sh/ruff | `[SUS]` (same `too-new`/`unknown-downloads` signal pattern) [VERIFIED: `gsd-tools query package-legitimacy check`] | Flagged — planner must add `checkpoint:human-verify` before install. Package name `[ASSUMED]`. |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `uv`, `ruff`. Both are extremely well-established Astral tools (this is a false-positive pattern for fast-release-cadence CLI tools: the gate's "too-new" signal keys off the latest published release, not project maturity) — still route through the human checkpoint per protocol, this note is context for that human, not a substitute for it.

No other new packages are introduced by this phase. Every ML/API dependency (`pandas`, `numpy`, `pyarrow`, `requests`, `scikit-learn`, `lightgbm`, `understatapi`, `pulp`, `scipy`, `fastapi`, `uvicorn`, `httpx`, `joblib`) is already an approved, in-use dependency from `requirements.txt` — this phase re-pins/hashes them, it does not introduce them.

## Standard Stack

### Core (dependency locking)

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|---------------|
| `uv` | 0.12.9 [ASSUMED — see legitimacy audit] | Compiles `requirements.in` → hashed `requirements.txt` | D-01 locked decision; fastest resolver, native `--generate-hashes` support [VERIFIED: `uv pip compile --help` output, run directly] |
| `pip` (stdlib, ≥24) | bundled with `python:3.14-slim` | Installs from the hashed lockfile in CI/Docker | D-01: uv is dev-time only, plain `pip install --require-hashes` is the runtime installer |

### Runtime stack — versions verified installable under Python 3.14.3 [VERIFIED: `pip install --require-hashes` succeeded end-to-end in a clean venv built from `/home/sraja/miniconda3/envs/python314/bin/python -m venv`, no source compiles]

| Library | Version | Wheel evidence |
|---------|---------|-----------------|
| pandas | 3.0.5 | `cp314` wheel on PyPI; this is what the project's own `python314` conda env already runs (`pip show pandas` → `3.0.2`, close patch) [VERIFIED: `pip show` in `/home/sraja/miniconda3/envs/python314`] |
| numpy | 2.5.2 | `cp314-manylinux_2_27_x86_64` wheel [VERIFIED: PyPI JSON API `pypi.org/pypi/numpy/json` file listing via the resolved lock] |
| pyarrow | 25.0.1 | `cp314-manylinux_2_28_x86_64` + `musllinux` wheels present [VERIFIED: PyPI JSON API, 6 cp314-linux-x86_64 files found directly] |
| scikit-learn | 1.9.0 | `cp314-cp314-manylinux_2_27_x86_64.manylinux_2_28_x86_64` + `cp314t` (free-threaded) wheels present [VERIFIED: PyPI JSON API, 4 cp314-linux-x86_64 files found directly] |
| lightgbm | 4.7.0 | `py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64` — **not** cp314-tagged because LightGBM's extension loads via `ctypes`, not the CPython C-API; it is Python-ABI-agnostic and satisfies any Python ≥3.10 [VERIFIED: PyPI JSON API file listing + `import lightgbm` succeeded directly in the python314 conda env] |
| pulp | 3.3.2 | `py3-none-any` (pure Python + bundled per-platform binaries); `requires_python >=3.10` [VERIFIED: PyPI JSON API + direct wheel inspection, see Common Pitfalls] |
| scipy | 1.18.1 | `cp314` wheel resolved cleanly as a lightgbm/API transitive dep |
| fastapi / uvicorn / httpx / joblib | 0.141.1 / 0.52.4 / 0.28.1 / 1.6.0 | pure-Python wheels, no ABI concern |
| understatapi | **0.7.1 (pin explicitly — see Common Pitfalls)** | pure-Python sdist, builds a wheel in <1s, no compiler needed [VERIFIED: `pip install --require-hashes` build log] |

### Supporting (CI/CD tooling)

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `ruff` | 0.16.6 [ASSUMED — see legitimacy audit] | Python lint | CI-01's "lint" step; zero-config default ruleset is sufficient, no `pyproject.toml`/`.flake8` exists today [VERIFIED: repo grep found no lint config] |
| `astral-sh/setup-uv` | v10.0.1 | Installs `uv` fast in a maintenance/lockfile-regeneration workflow (NOT needed in `ci.yml` itself — CI only runs `pip install --require-hashes`, never `uv`) | Optional — only if the planner wants a dedicated "regenerate lockfile" CI job |
| `aquasecurity/trivy-action` | v0.36.0 | Container image vulnerability scan (CI-05) | Scans the locally-built image tag before any GHCR push |
| `docker/build-push-action` | v7.3.0 | Builds and (main-only) pushes the image | Standard action for multi-stage Docker builds in Actions |
| `docker/login-action` | v4.6.0 | Authenticates to `ghcr.io` with `GITHUB_TOKEN` | D-04's scoped-token requirement |
| `docker/metadata-action` | v6.2.0 | Derives SHA + `latest` tags, lowercases repo/owner automatically | D-09's tagging policy |
| `docker/setup-buildx-action` | v4.3.0 | Enables BuildKit + GHA layer caching | Needed for `cache-from`/`cache-to: type=gha` |
| `github/codeql-action/upload-sarif` | v4.37.9 | Uploads Trivy's SARIF to the Security tab | **Must be `continue-on-error: true`** — see Common Pitfalls |
| `actions/checkout` | v7.0.1 | Repo checkout | — |
| `actions/setup-python` | v7.0.0 | Installs Python 3.14 (resolves to 3.14.7) [VERIFIED: `actions/python-versions` manifest lists `3.14.7`] | Backend jobs |
| `actions/setup-node` | v7.0.0 | Installs Node for `frontend/` + `e2e/` | Frontend/E2E jobs |
| `actions/cache` | v6.1.0 | Playwright browser cache, npm/pip caches beyond `setup-*`'s built-in cache | Speed |
| `actions/upload-artifact` / `download-artifact` | v7.0.1 / v8.0.1 | Shares `frontend/dist` between jobs (D-08 requirement) | Cross-job artifact passing |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Bundled `PULP_CBC_CMD` + `apt-get install libstdc++6` | `pulp[cbc]` extra (installs `cbcbox`, a newer COIN_CMD-based CBC) | Requires changing all 3 call sites (`squad_ilp.py`, `transfers.py`, `multi_period.py`) from `PULP_CBC_CMD` to `COIN_CMD`; zero benefit today since the bundled binary already works and is what's tested. Reject for this phase. |
| `apt-get install coinor-cbc` (system package) | same as above | PuLP's `PULP_CBC_CMD` would still use its own bundled binary, not the apt one, unless code changes to `pulp.COIN_CMD()`. Pulls in more transitive apt packages than just `libstdc++6`. Reject. |
| `ruff` for Python lint | `flake8` + `black` | Slower, two tools instead of one, no existing config to preserve either way. `ruff` is Claude's Discretion per CONTEXT.md — recommend `ruff`. |
| `python:3.14-slim` (→ `slim-trixie`) | `python:3.14-slim-bookworm` | Both work (glibc 2.36+/2.39+, both exceed the `manylinux_2_28` floor); `slim` tracks the newest Debian, use it unless a specific package proves unavailable on trixie during Docker build (fallback documented, not expected to be needed). |

**Installation:**
```bash
# Dev-time lockfile compile (never runs in CI/Docker)
uv pip compile requirements.in --generate-hashes --python-version 3.14 -o requirements.txt
uv pip compile requirements-dev.in --generate-hashes --python-version 3.14 -o requirements-dev.txt

# CI / Docker runtime install
pip install --require-hashes -r requirements.txt
pip install --require-hashes -r requirements-dev.txt   # CI only, not Docker
```

**Version verification:** All versions above were confirmed live against PyPI (`pypi.org/pypi/<pkg>/json`) and by a real `pip install --require-hashes` execution in a clean Python 3.14.3 venv on 2026-09-04 — not from training-data recollection. Re-run the same compile command at plan-execution time since these are fast-moving projects (`pandas`/`numpy`/`scikit-learn` all ship monthly-ish); if resolved versions differ from this table, that's expected and fine — the smoke test (D-07) is the real gate, not this table.

## Architecture Patterns

### System Architecture Diagram

```
push/PR ──▶ ci.yml
              │
              ├─▶ [lint/typecheck job] ─┬─▶ ruff check .                (Python lint)
              │                          └─▶ npm --prefix frontend run build   (tsc -b + vite build; "the real typecheck")
              │                                   │
              │                                   └─▶ upload-artifact: frontend/dist
              │
              ├─▶ [backend+frontend tests job] (needs: lint/typecheck)
              │       ├─▶ download-artifact: frontend/dist  (tests/test_fixture_mode.py's
              │       │                                       SPA-fallback test 500s without it)
              │       ├─▶ pip install --require-hashes -r requirements.txt -r requirements-dev.txt
              │       ├─▶ pytest tests/            (APIT-01/02/03, legality, leakage, autosub)
              │       └─▶ npm --prefix frontend test   (vitest)
              │
              ├─▶ [playwright e2e job] (needs: backend+frontend tests)
              │       ├─▶ download-artifact: frontend/dist
              │       ├─▶ npm --prefix e2e run install:browser  (chromium + --with-deps)
              │       └─▶ npx playwright test   (webServer builds dist again + boots fixture uvicorn — D-01..D-05 of Phase 4)
              │
              └─▶ [docker build+smoke+scan job] (needs: playwright e2e)
                      ├─▶ docker buildx build -t local-tag .   (multi-stage: builder resolves+installs, runtime copies venv+code)
                      ├─▶ docker run -d --env FPL_FIXTURE_DIR=/fixtures/v1/normal \
                      │       -v $(pwd)/e2e/fixtures:/fixtures:ro -p 8000:8000 local-tag
                      ├─▶ curl -f http://localhost:8000/api/health
                      ├─▶ curl -f -X POST http://localhost:8000/api/solve -d '{}'   (real CBC solve)
                      ├─▶ aquasecurity/trivy-action  (scan local-tag, format=sarif)
                      ├─▶ upload-artifact: trivy-results.sarif           (always succeeds)
                      ├─▶ codeql-action/upload-sarif  (continue-on-error: true — see Pitfalls)
                      └─▶ [main branch only] docker/login-action + build-push-action --push
                                   └─▶ ghcr.io/sraja/fpl:<sha> , ghcr.io/sraja/fpl:latest
```

### Recommended Project Structure

```
requirements.in            # NEW — API/pipeline runtime deps (source for the lock)
requirements-dev.in        # NEW — pytest, responses, ruff (source for the dev lock)
requirements.txt           # REGENERATED — hashed lock, uv output (was >= constraints)
requirements-dev.txt       # NEW — hashed dev lock
Dockerfile                 # NEW — multi-stage, python:3.14-slim
.dockerignore               # NEW
.github/workflows/
├── ci.yml                 # NEW — the chained job graph above
├── daily.yml               # MODERNIZED — py3.14, hashed installs, bot identity, dispatch-only
└── weekly.yml              # MODERNIZED — same, plus false "model in repo" comment corrected
scripts/
└── smoke_test.sh           # NEW — docker run + curl health + curl solve (D-07), reusable locally
```

### Pattern 1: Multi-stage Dockerfile, no model artifact

**What:** Builder stage resolves/installs the hashed lockfile (may need `gcc`/`g++`/`libc6-dev` per D-03's pre-authorized fallback, though none of the current pins need it); runtime stage is `python:3.14-slim` + `libstdc++6` + the installed site-packages copied over + application code + `web/` + `frontend/dist`. No `models/artifacts/xp_model.joblib` is ever `COPY`'d in (D-05) — the code already tolerates this (see Pattern 2).

**When to use:** Every image build in this phase — this is the only Dockerfile the phase produces.

**Example (skeleton — exact package list is the planner's/executor's job, not re-derived here):**
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.14-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --require-hashes --prefix=/install -r requirements.txt

FROM python:3.14-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
WORKDIR /app
COPY . .
# frontend/dist is expected to already exist in the build context (produced by the
# CI job's "npm run build" step before `docker build` runs — see D-06/architecture diagram)
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Add a non-root `USER` in the runtime stage (Security Domain, below) — not shown here since the exact UID/GID scheme is Claude's Discretion.

### Pattern 2: Model-less container boots and answers health

**What:** `/api/health` reads `_state` without calling `_refresh()` [VERIFIED: `api/main.py:379-382`, quoted verbatim: `return {"ok": True, "gw": _state["gw"], "pool_age_s": round(time.time() - _state["loaded_at"])}`]. `_refresh()` only calls `joblib.load(...)` when `_state["artifact"] is None` **and** `_FIXTURE_ROOT` is falsy [VERIFIED: `api/main.py:156-167`, quoted verbatim: `_state["artifact"] = ("fixture-mode" if _FIXTURE_ROOT else joblib.load(config.ROOT / "models" / "artifacts" / "xp_model.joblib"))`]. With `FPL_FIXTURE_DIR` set, the smoke test never touches `joblib.load` — this is why D-07's smoke test can prove a real CBC solve without ever shipping a model artifact.

**When to use:** Designing the container smoke test.

### Pattern 3: The smoke-test payload

`POST /api/solve` with body `{}` is valid — every field on `SolveRequest` has a default [VERIFIED: `api/main.py:367-375`, quoted verbatim: `entry: int | None = None`, `free_transfers: int = Field(1, ge=0, le=config.MAX_FREE_TRANSFERS)`, `horizon: int = Field(1, ge=1, le=6)`, `mode: str = Field("normal", pattern="^(normal|tc|bb)$")`, `budget: float | None = None`, `max_transfers: int | None = Field(None, ge=0, le=15)`, `locks: list[int | str] = []`, `excludes: list[int | str] = []`]. This triggers a genuine from-scratch ILP solve through the bundled CBC binary — the strongest possible smoke test, not `import pulp`.

```bash
# scripts/smoke_test.sh sketch
docker run -d --name fpl-smoke -p 8000:8000 \
  -e FPL_FIXTURE_DIR=/fixtures/v1/normal \
  -v "$(pwd)/e2e/fixtures:/fixtures:ro" \
  ghcr.io/sraja/fpl:smoke-test
sleep 2   # or poll until /api/health responds
curl -f http://localhost:8000/api/health
curl -f -X POST http://localhost:8000/api/solve -H 'Content-Type: application/json' -d '{}'
docker stop fpl-smoke
```
Note: `e2e/fixtures/` is **bind-mounted at smoke-test time from the CI checkout**, not `COPY`'d into the image — D-05's "code + locked deps + static assets" scope excludes test-only fixtures from the shipped artifact.

### Anti-Patterns to Avoid

- **Baking `e2e/fixtures/` into the Dockerfile:** bloats the production image with test data that's already available on the CI runner's checkout; bind-mount it for the smoke-test step only.
- **Using `npm run typecheck` as a CI gate:** it is a genuine no-op. `frontend/tsconfig.json`'s root config is `{"files": [], "references": [...]}` [VERIFIED: `frontend/tsconfig.json:1-5`] — running plain `tsc --noEmit` with no `-b` flag never expands the project references, so it type-checks zero files and exits 0 regardless of real errors. Only `npm run build` (`tsc -b && vite build`) enforces the real check.
- **Trusting `pip freeze` from the conda env for the lockfile:** D-02 already forbids this; confirmed necessary because the conda env's `numpy==2.4.4` differs from the clean-venv pip resolution of `numpy==2.5.2` — not wrong, just a reminder that conda-forge and PyPI wheel graphs diverge slightly and only the PyPI-resolved lock is what CI/Docker will actually install.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Dependency hash pinning | A custom script hashing wheel downloads | `uv pip compile --generate-hashes` | Already produces PEP 508-compliant `--hash` lines pip's `--require-hashes` understands natively; verified working end-to-end this session |
| Docker layer caching in CI | Manual `docker save`/`load` between jobs | `docker/build-push-action` with `cache-from`/`cache-to: type=gha` | Native GHA cache backend, no extra storage/artifact bookkeeping |
| SARIF upload to Security tab | Custom API call to the code-scanning REST endpoint | `github/codeql-action/upload-sarif` | Handles auth/permissions/format correctly; still needs `continue-on-error` per the Pitfalls section, but that's a one-line fix, not a reason to hand-roll |
| CBC solver installation | Compiling COIN-OR CBC from source in the builder stage | PuLP's already-bundled `linux/i64/cbc` binary + `apt-get install libstdc++6` | Verified working via direct wheel extraction + a real `.solve()` call; compiling CBC from source would be significant unneeded effort |

**Key insight:** every piece of "new infrastructure" this phase seems to need (CBC availability, cp314 wheels, hash-locked installs) was already solvable with the exact tools D-01–D-16 chose — the risk was in *verifying* it, not in needing new tooling.

## Common Pitfalls

### Pitfall 1: `understatapi` unpinned drags in `selenium`
**What goes wrong:** `uv pip compile` with a bare `understatapi` line (matching `requirements.txt`'s current `understatapi>=0.5` constraint) resolves to `understatapi==0.5.2`, which pulls in `selenium==4.48.0`, `trio`, `trio-websocket`, `websocket-client`, `wsproto`, `sortedcontainers` — a large, unnecessary dependency chain for a scraping library the runtime API never calls.
**Why it happens:** `understatapi`'s own dependency declaration changed between releases; the currently-installed dev-env version (not checked — this was discovered via a fresh resolve) predates the cleanup. PyPI's latest `understatapi==0.7.1` declares only `certifi`, `charset-normalizer`, `idna`, `requests`, `urllib3` [VERIFIED: `pypi.org/pypi/understatapi/json`, `requires_dist` field].
**How to avoid:** Pin `understatapi==0.7.1` explicitly in `requirements.in` (not a bare/floating constraint). Verified via a second `uv pip compile` run: zero selenium/trio packages appear in the resulting lock.
**Warning signs:** If the compiled lockfile contains `selenium`, `trio`, or `wsproto`, the pin regressed.

### Pitfall 2: `libstdc++6` is not present in `python:3.14-slim` by default
**What goes wrong:** The bundled CBC binary (`pulp/solverdir/cbc/linux/i64/cbc`) is a C++ binary requiring `libstdc++.so.6`, `libgcc_s.so.1`, `libpthread`, `librt`, `libdl`, `libm`, `libc` [VERIFIED: `ldd` on the extracted binary]. `python:3.14-slim`'s own Dockerfile builds CPython from source, then explicitly purges every apt-installed library except ones CPython's *own* compiled artifacts `ldd`-require [VERIFIED: `docker-library/python` GitHub, `3.14/slim-trixie/Dockerfile`, the `apt-get purge -y --auto-remove` + `ldd`-scan block]. CPython itself never links `libstdc++`, so it is not kept — the CBC subprocess will fail with a missing-shared-library error unless explicitly reinstalled.
**Why it happens:** The slim image's minimization logic is scoped to "what Python needs," not "what any bundled binary a Python package ships might need."
**How to avoid:** `apt-get install -y --no-install-recommends libstdc++6` in the runtime stage (confirmed small: ~800KB download / ~3MB installed on the closest available reference, Ubuntu 24.04's package of the same name and purpose [VERIFIED: `apt-cache show libstdc++6` — Debian trixie's exact package wasn't directly inspectable from this environment, but the package serves an identical, size-class-equivalent purpose across the Debian family]).
**Warning signs:** the smoke test's `POST /api/solve` step fails with a subprocess/`OSError`/"cannot execute binary file" or a `libstdc++.so.6: cannot open shared object file` message.

### Pitfall 3: PuLP 4.x will remove the bundled CBC entirely — pin `<4.0`
**What goes wrong:** PuLP's own upcoming major version (currently at prerelease `4.0.0a12`) removes the legacy bundled-CBC code path that `PULP_CBC_CMD` uses; its docs describe the current `3.3.2` bundled solver as "legacy" already [VERIFIED: `raw.githubusercontent.com/coin-or/pulp/3.3.2/README.rst`, quoted: "If CBC is not available on your system, PuLP falls back to other solvers such as the legacy bundled CBC (`PULP_CBC_CMD`) or GLPK."]. If a future dependency bump lands on PuLP 4.x without a corresponding code change to `pulp.COIN_CMD()` / `pulp[cbc]`, every solve breaks.
**Why it happens:** Upstream is actively deprecating the bundled-binary approach in favor of the `pulp[cbc]`/`cbcbox` installable extra.
**How to avoid:** Pin `pulp>=3.3,<4.0` in `requirements.in` for this phase; leave the PuLP 4.x migration (switching call sites to `COIN_CMD`) as an explicit future task, not something this phase's lockfile should silently walk into.
**Warning signs:** any future `uv pip compile` re-run that resolves `pulp==4.x` should be treated as a breaking change requiring code review, not accepted silently.

### Pitfall 4: SARIF upload to the Security tab may fail on this private-repo/Free-plan combination
**What goes wrong:** GitHub's own documentation is internally inconsistent on this point. The general "About code scanning" doc states plainly that private-repo code scanning "needs a GitHub Code Security license" [CITED: docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning]. The dedicated troubleshooting page for the specific `upload-sarif` failure mode states the opposite for third-party tools: "You will only see this error for SARIF files that contain results created using CodeQL" [CITED: docs.github.com/en/code-security/code-scanning/troubleshooting-sarif-uploads/ghas-required] — implying Trivy's (non-CodeQL) SARIF might upload fine even without a paid plan. Two independent web summaries cross-checking the Free-plan pricing page and community discussions both concluded code scanning generally requires GitHub Team/Advanced Security for private repos [VERIFIED: two independent sources, cross-checked]. D-13 locks in "Private repo now."
**Why it happens:** GitHub's docs distinguish "code scanning" (the general feature, gated on private repos) from "the specific `upload-sarif` action's GHAS-required error" (allegedly CodeQL-only) — these two framings are not obviously reconciled in the public docs, and this environment cannot create a real private repo + push a workflow to test it directly (D-14: only the user pushes).
**How to avoid:** Don't bet CI-05 on this ambiguity. Set `continue-on-error: true` on the `upload-sarif` step, and *unconditionally* run `actions/upload-artifact` on the raw `trivy-results.sarif` file first (before the upload-sarif step), so CI-05's "Trivy scan reports on the image on every build" is satisfied by the artifact even if the Security-tab upload silently fails or errors. This is also consistent with D-10 ("Trivy is report-only... never blocks the build") regardless of which GitHub behavior is real.
**Warning signs:** the `upload-sarif` step shows a red X but the job/workflow still shows green (expected, harmless) — if the whole *job* goes red, `continue-on-error` wasn't applied to the right step.

### Pitfall 5: pytest's SPA-fallback test needs `frontend/dist/` built *first*
**What goes wrong:** `tests/test_fixture_mode.py::test_client_side_route_falls_back_to_the_spa_shell_not_json` GETs `/team` and asserts `"text/html" in r.headers["content-type"]` [VERIFIED: `tests/test_fixture_mode.py:144-149`]. In fixture mode this route resolves through `StaticFiles(directory=config.ROOT / "frontend" / "dist", html=True, check_dir=False)` [VERIFIED: `api/main.py:549-550`]. `check_dir=False` lets the mount register even if `frontend/dist/` doesn't exist on disk yet — but the first real request 500s if it's still missing, because there's no `404.html` to fall back to.
**Why it happens:** `frontend/dist/` is gitignored and only produced by `npm run build`; a naive `ci.yml` that runs `pip install && pytest` before any frontend build step will hit this.
**How to avoid:** The `lint/typecheck` job already runs `npm run build` (Pattern in Architecture diagram) — upload its `frontend/dist/` as an artifact and `download-artifact` it before the pytest job runs. This was already flagged as a Phase 4→5 handoff blocker in STATE.md; this research confirms the exact test name and exact code path.
**Warning signs:** `test_client_side_route_falls_back_to_the_spa_shell_not_json` fails with a 500, or any fixture-mode test fails with a directory-not-found-adjacent error.

## Code Examples

### GHCR publish (verified action versions + SHA pins)
```yaml
permissions:
  contents: read
  packages: write
steps:
  - uses: docker/login-action@dbcb813823bdd20940b903addbd779551569679f   # v4.6.0
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
  - uses: docker/metadata-action@dc802804100637a589fabce1cb79ff13a1411302   # v6.2.0
    id: meta
    with:
      images: ghcr.io/${{ github.repository }}
      tags: |
        type=sha
        type=raw,value=latest,enable={{is_default_branch}}
  - uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a   # v7.3.0
    with:
      context: .
      push: ${{ github.ref == 'refs/heads/main' }}   # D-09: never push from PR/branch builds
      tags: ${{ steps.meta.outputs.tags }}
      cache-from: type=gha
      cache-to: type=gha,mode=max
```
Source pattern: [CITED: docs.github.com/en/actions/publishing-packages/publishing-docker-images], SHA pins independently re-resolved via the GitHub API against each action's current release tag on 2026-09-04 [VERIFIED: `api.github.com/repos/<owner>/<repo>/git/ref/tags/<tag>`], not copied from the docs page's own (differently-versioned) example.

### Trivy scan, report-only, artifact-safe (CI-05 / D-10)
```yaml
  - name: Build Trivy is scanning
    run: docker build -t local/fpl:scan .
  - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25   # v0.36.0
    with:
      image-ref: local/fpl:scan
      format: sarif
      output: trivy-results.sarif
      # no exit-code set => defaults to 0, never fails the build (D-10)
  - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a   # v7.0.1
    if: always()
    with:
      name: trivy-results
      path: trivy-results.sarif
  - uses: github/codeql-action/upload-sarif@cdf488f595d80d6e07e03d4674febd5ab45fa938   # v4.37.9
    if: always()
    continue-on-error: true   # Pitfall 4 — private-repo GHAS gate is ambiguous, don't let it redden the job
    with:
      sarif_file: trivy-results.sarif
```
Base usage pattern: [VERIFIED: `raw.githubusercontent.com/aquasecurity/trivy-action/v0.36.0/README.md`, "Scan CI Pipeline" and "Using Trivy with GitHub Code Scanning" sections, fetched directly this session].

### uv lockfile compile (verified live)
```bash
uv pip compile requirements.in --generate-hashes --python-version 3.14 -o requirements.txt
```
[VERIFIED: `uv --help`/`uv pip compile --help` run directly against `uv==0.12.9`; the exact command above was executed this session against a representative `requirements.in` and the resulting lockfile was successfully consumed by `pip install --require-hashes` in a clean Python 3.14.3 venv with zero errors]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| `requirements.txt` with `>=` constraints | `requirements.in` (source) → `uv pip compile --generate-hashes` → hashed `requirements.txt` | This phase (D-01/D-02) | Reproducible, hash-verified installs; `pip install --require-hashes` rejects anything not in the lock |
| PuLP's `PULP_CBC_CMD` as the primary API | PuLP 4.x moves to `pulp[cbc]`/`COIN_CMD` as primary, demotes `PULP_CBC_CMD` to "legacy" fallback | Upstream, ongoing as of PuLP `4.0.0a12` prerelease | Not yet forced — `3.3.2` (current stable) still ships and uses the bundled binary; see Pitfall 3 for the pin discipline needed to avoid an unplanned break |
| `pip freeze` for lockfiles | `uv pip compile --generate-hashes` from a minimal `.in` source file | Broadly, uv's adoption over the last ~2 years | Explicit top-level deps stay readable; transitive pins + hashes live in the generated file, not hand-edited |

**Deprecated/outdated:** `npm run typecheck` (`tsc --noEmit` with no `-b`) was likely never a meaningful gate given the project reference structure — not a regression, just confirms the existing CONTEXT.md guidance with a direct source read.

## Runtime State Inventory

Not applicable — this is a build/CI/infrastructure phase adding new files (`Dockerfile`, `ci.yml`, `requirements.in`), not a rename/refactor/migration. No stored data, live service config, OS-registered state, or renamed secrets are touched by this phase's scope.

**Nothing found in any category** — verified by reading CONTEXT.md's own repo-scout facts (the Chrome `.deb` was never committed, so its removal is a working-tree delete, not a data migration) and by this session's direct inspection of `.gitignore`, `requirements.txt`, and the workflow files, none of which reference any datastore, cron-registered task, or secret key that this phase renames or relocates.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `uv` package name/tool identity, version `0.12.9` | Standard Stack (Core) | Low — registry-confirmed to exist and resolve; risk is scoped to the package-legitimacy human checkpoint already required by CONTEXT.md, not to this research |
| A2 | `ruff` package name/tool identity, version `0.16.6` | Standard Stack (Supporting) | Low — same as A1 |
| A3 | Debian trixie's `libstdc++6` package matches Ubuntu 24.04's in size class (~800KB/~3MB) | Common Pitfalls / Docker Architecture | Low — even a 10x size difference is immaterial to the image-size budget; only the *existence* of the package matters, which is a near-certainty for any Debian derivative |
| A4 | GitHub's private-repo SARIF-upload gate behavior for non-CodeQL tools (Pitfall 4) | Common Pitfalls, Code Examples | Medium if unaddressed — but the recommended `continue-on-error: true` + artifact-fallback pattern makes the plan correct regardless of which behavior is real, so the *actionable* risk is fully mitigated even though the underlying fact is unresolved |
| A5 | github-actions bot commit identity (`github-actions[bot]` / `41898282+github-actions[bot]@users.noreply.github.com`) is the correct D-11 replacement identity | Common Pitfalls (daily/weekly.yml modernization) | Low — de-facto GitHub-wide convention, not officially documented but extremely widely adopted [CITED: community discussion cross-referencing 15,000+ code-search hits] |

## Open Questions

1. **Does the private-repo SARIF upload actually succeed or fail on this specific GitHub account?**
   - What we know: GitHub's own docs give two different framings (Pitfall 4); this environment cannot create the real private repo and push a workflow to observe ground truth (D-14 reserves all pushes for the user).
   - What's unclear: whether `upload-sarif` will error, silently no-op, or fully succeed for a personal-account private repo on the Free plan.
   - Recommendation: Ship the `continue-on-error: true` + artifact-fallback design (Code Examples) so the plan's correctness doesn't depend on resolving this — the first real CI run (D-14's human-gated checkpoint) will reveal the true behavior at zero cost to the plan.

2. **Exact final `requirements.in` package set for the Docker image's runtime stage**
   - What we know: `requirements.in` (per D-02) covers "API/pipeline runtime" — i.e., everything currently in `requirements.txt` minus `responses` (test-only). CI-01's pytest job needs the full stack (tests exercise `models/`, `optimize/`, `features/`, not just `api/`).
   - What's unclear: whether the *Docker image specifically* should ship `lightgbm`/`scikit-learn`/`understatapi` if the only thing D-07's smoke test proves is `/api/health` + `/api/solve` (which need `pulp`/`pandas`/`fastapi`/`joblib`, not necessarily the training stack).
   - Recommendation: Ship the full `requirements.in` set in the image (simpler: one lockfile, one image, matches "requirements.in (API/pipeline runtime)" wording literally) unless the planner has a specific reason to split further. This phase's image-size budget (see below) comfortably absorbs it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python 3.14 (conda `python314`) | Dev-time lockfile generation, local testing | ✓ | 3.14.3 [VERIFIED: `python --version`] | — |
| Docker | Building/testing the image locally | ✗ (not installed in this research environment) | — | Image build/smoke-test correctness verified via clean-venv `pip install --require-hashes` (proves dependency-layer correctness) + direct wheel/binary inspection (proves CBC availability); the actual `docker build` must be exercised for the first time during CI (D-14 human-gated checkpoint) or by the executor if Docker is available in the execution environment |
| GitHub Actions runners (`ubuntu-latest`) | CI-01..CI-05 | N/A (verified via GitHub's own published manifests, not locally) | `actions/setup-python` resolves `3.14` → `3.14.7` [VERIFIED: `actions/python-versions` manifest] | — |
| Network access to PyPI, GitHub API, Docker Hub API | This research session | ✓ | — | — |

**Missing dependencies with no fallback:** none — Docker's absence is covered by the fallback above (dependency-layer + binary-layer verification done independently; the container-build step itself is inherently something only CI or a Docker-equipped executor can prove, unrelated to this research gap).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest (installed: `pytest==9.1.1` in the dev conda env) [VERIFIED: `pip list` in `python314` env] |
| Backend config | `pytest.ini` — `addopts = -p no:playwright -p no:seleniumbase`, `testpaths = tests` [VERIFIED: `pytest.ini`, read directly] |
| Frontend framework | Vitest (`frontend/package.json`: `"test": "node scripts/check-tokens.mjs && vitest run"`) |
| E2E framework | Playwright (`e2e/package.json`: `"test": "playwright test"`, `@playwright/test@1.62.1`) |
| Quick backend run | `pytest tests/ -x` |
| Quick E2E run | `E2E_VARIANTS=0 npx playwright test` (skips blank/DGW variant servers) [VERIFIED: `e2e/playwright.config.ts:58`] |
| Full suite | `pytest tests/` + `npm --prefix frontend test` + `npx playwright test` (all three variant servers) |

### Phase Requirements → Test Map

This phase's requirements are almost entirely CI/infra-level, not application-behavior-level — "tests" here means workflow steps and one new smoke-test script, not new pytest cases.

| Req ID | Behavior | Verification Type | Command | File Exists? |
|--------|----------|--------------------|---------|-------------|
| CI-01 | ci.yml runs lint+typecheck+pytest+API tests on push/PR | workflow (CI-level) | `ruff check .` then `pytest tests/` in `ci.yml` | ❌ Wave 0 — `ci.yml` is new |
| CI-02 | Frontend build + Playwright job vs uvicorn+fixture data | workflow (CI-level) | `npx playwright test` in `ci.yml`, reusing `e2e/playwright.config.ts` verbatim | ✅ config exists (Phase 4); ❌ the CI job wiring is new |
| CI-03 | Multi-stage Dockerfile, CBC + `/health` smoke test | smoke script | `bash scripts/smoke_test.sh` (new) | ❌ Wave 0 — `Dockerfile`, `scripts/smoke_test.sh` are new |
| CI-04 | GHCR publish, SHA-pinned actions, scoped token | workflow inspection | grep `ci.yml` for `uses: .*@[0-9a-f]{40}` on every line; real push → image visible in GHCR (human-gated, D-14) | ❌ Wave 0 |
| CI-05 | Trivy scan every build | workflow (CI-level) | `aquasecurity/trivy-action` step present + `trivy-results.sarif` artifact uploaded | ❌ Wave 0 |
| SEC-02 | Deps locked/hashed, installable fresh with cp314 wheels | automated command | `pip install --require-hashes -r requirements.txt` in a clean venv — **already verified working this session** | ❌ `requirements.in`/`.txt` regeneration is new; the *capability* is proven |
| SEC-04 | Chrome `.deb` gone, `.gitignore` complete, workflows tracked | automated command | `test ! -f google-chrome-stable_current_amd64.deb`, `git ls-files .github/workflows/` non-empty | Partially — `.gitignore` already covers `*.deb`/`.env`/`models/artifacts` [VERIFIED: `.gitignore`, read directly]; the `.deb` file itself still exists on disk (`ls -la` confirmed 140MB file present) and must be deleted as a working-tree op |

### Sampling Rate
- **Per task commit:** run the specific new/changed step in isolation where possible (e.g., `ruff check .` alone, `pytest tests/ -x` alone) — full `docker build` is slow, don't run it on every commit.
- **Per wave merge:** full local dry run if Docker is available in the executor's environment; otherwise defer to the first real CI run.
- **Phase gate:** the D-14 human-gated checkpoint ("user pushes → real CI run goes green end-to-end → image visible in GHCR") is the authoritative full-suite gate for this phase — no amount of local simulation substitutes for it, since Docker was unavailable in this research environment.

### Wave 0 Gaps
- [ ] `requirements.in` / `requirements-dev.in` — source files for the lock, don't exist yet
- [ ] `Dockerfile` / `.dockerignore` — don't exist yet
- [ ] `.github/workflows/ci.yml` — doesn't exist yet
- [ ] `scripts/smoke_test.sh` (or equivalent inline CI steps) — doesn't exist yet
- [ ] `pyproject.toml` or `ruff.toml` — minimal ruff config, doesn't exist yet (ruff works with zero config, but an explicit minimal config avoids surprise strictness on `data/raw`-adjacent generated-looking paths — recommend excluding `data/`, `models/artifacts/`, `frontend/`, `e2e/node_modules/`)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V1 Architecture | yes | Multi-stage build separates build-time secrets/tools (pip cache, compilers if ever needed) from the shipped runtime image; no model artifact or credentials baked into any layer (D-05) |
| V14 Configuration/Deployment | yes | Pinned + hash-verified dependencies (SEC-02); minimal `python:3.14-slim` base; SHA-pinned GitHub Actions (CI-04) prevents a compromised upstream Action tag from silently changing behavior; scoped `GITHUB_TOKEN` (`contents:read`, `packages:write` only, not a broad PAT) |
| V2 Authentication / V3 Session | no | Unchanged by this phase — `require_key()` stub logic is untouched; SEC-01/SEC-03 (CORS, `.env` mode 600) are explicitly Phase 6 scope per CONTEXT.md |
| V4 Access Control | no | Same as above |
| V5 Input Validation | no (pre-existing) | Already covered by `SolveRequest`'s pydantic `Field` bounds (`APIT-01` tests from Phase 1); this phase doesn't touch request-handling code |
| V6 Cryptography | no | No new crypto surface introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Typosquatted/compromised PyPI package silently installed | Tampering | Hash-locked installs (`pip install --require-hashes`) reject anything not byte-identical to what was resolved at lock time; new tools (`uv`, `ruff`) route through the package-legitimacy gate before being added to any lockfile |
| Mutable Action tag (e.g. `@v4`) repointed upstream to malicious code | Tampering | SHA-pinning every `uses:` line (CI-04) — this research resolved and verified the exact commit SHA for every action recommended above |
| Container running as root, unnecessary attack surface if compromised | Elevation of Privilege | Add a non-root `USER` in the Dockerfile's runtime stage (Claude's Discretion on exact UID scheme — not currently present anywhere in the repo, this is new guidance from this research, not a locked decision) |
| Secrets/tokens leaking into a Docker image layer | Information Disclosure | No `.env`, API keys, or model artifact is ever `COPY`'d into the image (D-05); confirm via `.dockerignore` explicitly excluding `.env*`, `*.deb`, `data/raw/`, `data/processed/`, `models/artifacts/` |
| Overly-broad `GITHUB_TOKEN` scope enabling unintended repo/package writes | Elevation of Privilege | Explicit `permissions:` block per job (`contents: read`, `packages: write` only on the publish job; `security-events: write` only on the Trivy-upload step) rather than the default (broader) token scope |

## Sources

### Primary (HIGH confidence — direct tool execution or authoritative registry API, this session)
- PyPI JSON API (`pypi.org/pypi/<pkg>/json`) — version/wheel-tag verification for pulp, lightgbm, scikit-learn, pyarrow, pandas, understatapi
- Direct `pip install --require-hashes` execution in a clean Python 3.14.3 venv (built from the conda `python314` interpreter's own `-m venv`, not reused conda packages)
- Direct `unzip`/`ldd`/`file` inspection of the `pulp-3.3.2` wheel's bundled CBC binary, and a real `pulp.LpProblem(...).solve(pulp.PULP_CBC_CMD())` execution
- GitHub REST API (`api.github.com/repos/<owner>/<repo>/...`) — release tags, commit SHAs, repo creation dates/stars for every Action and for `uv`/`ruff` legitimacy cross-check
- `docker-library/python` GitHub repo, `3.14/slim-trixie/Dockerfile` — direct read of the official image's build/purge logic
- `docker hub v2 API` — confirmed `python:3.14-slim` tag exists (2026-09-01) and aliases `slim-trixie`
- `actions/python-versions` manifest — confirmed `3.14.7` available to `actions/setup-python`
- Direct reads of this repo's own source: `api/main.py`, `config.py`, `frontend/tsconfig.json`, `frontend/package.json`, `e2e/playwright.config.ts`, `e2e/package.json`, `pytest.ini`, `.gitignore`, `.github/workflows/{daily,weekly}.yml`, `tests/test_fixture_mode.py`, `tests/test_api.py`, `scripts/verify_frontend_build.sh`

### Secondary (MEDIUM confidence — official docs, single-source)
- `raw.githubusercontent.com/aquasecurity/trivy-action/v0.36.0/README.md` and `action.yaml`
- `raw.githubusercontent.com/coin-or/pulp/3.3.2/README.rst`
- `docs.github.com/en/actions/publishing-packages/publishing-docker-images`
- `docs.github.com/en/code-security/code-scanning/*` (two pages, internally inconsistent — see Pitfall 4)

### Tertiary (LOW confidence — WebSearch summaries, cross-checked where load-bearing)
- github-actions bot identity convention (community discussions, not official docs)
- Debian trixie `libstdc++6` package size (approximated from Ubuntu 24.04's `apt-cache show`, not Debian's own repos — this environment has no `apt` access to Debian trixie directly)

## Metadata

**Confidence breakdown:**
- Standard stack (cp314 wheels, versions): HIGH — every version was live-verified via PyPI JSON API and/or a real `pip install --require-hashes` execution this session, not training-data recollection
- CBC/CI-03 architecture: HIGH — verified via direct binary inspection, `ldd`, and a real `.solve()` call, plus the official `python:3.14-slim` Dockerfile source
- CI Actions versions/SHAs: HIGH — every SHA independently resolved from the GitHub API against the current release tag
- Trivy/GHAS private-repo interaction (Pitfall 4): MEDIUM — the underlying GitHub behavior is genuinely ambiguous from available docs, but the recommended mitigation is robust regardless
- `uv`/`ruff` legitimacy: per-gate SUS verdict, human-checkpoint-gated (not a research confidence question — this is by design)

**Research date:** 2026-09-04
**Valid until:** ~14 days for the ML dependency versions (pandas/numpy/scikit-learn ship frequently; re-run `uv pip compile` at plan-execution time rather than trusting this table's exact patch versions), ~30 days for the Action SHA pins (re-resolve if the plan isn't executed promptly — GitHub Actions release cadence is roughly monthly per action)
