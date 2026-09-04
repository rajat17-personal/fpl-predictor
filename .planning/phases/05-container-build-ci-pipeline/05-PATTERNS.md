# Phase 5: Container Build & CI Pipeline - Pattern Map

**Mapped:** 2026-09-04
**Files analyzed:** 9
**Analogs found:** 6 / 9 (3 are genuinely novel — no existing analog, RESEARCH.md Code Examples are primary source)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `requirements.in` | config | batch (dependency resolution) | `requirements.txt` (current) | exact — direct source split |
| `requirements-dev.in` | config | batch | `requirements.txt` (`responses` line) | role-match |
| `requirements.txt` (regenerated, hashed) | config | batch | `requirements.txt` (current) | exact — regeneration of same file |
| `.github/workflows/ci.yml` | config (CI workflow) | event-driven | `.github/workflows/daily.yml` / `weekly.yml` | role-match (workflow shape), no chained-job analog exists |
| `.github/workflows/daily.yml` (modernized) | config (CI workflow) | event-driven | itself (existing file, in-place modernization) | exact |
| `.github/workflows/weekly.yml` (modernized) | config (CI workflow) | event-driven | itself (existing file, in-place modernization) | exact |
| `Dockerfile` | config (build) | batch | none in-repo | no analog — novel infra file |
| `.dockerignore` | config | batch | `.gitignore` | role-match (ignore-list conventions, same repo layout) |
| `scripts/smoke_test.sh` | utility (shell script) | request-response (curl against running service) | `scripts/verify_frontend_build.sh` | role-match — closest shell-script convention in repo |

## Pattern Assignments

### `requirements.in` / `requirements-dev.in` (config, batch)

**Analog:** `requirements.txt` (current, root)

Full file content (source for the D-02 split):
```
# Phase 0-1 (ingestion/build) — already present in conda env `python314`
pandas>=2.2
numpy>=1.26
pyarrow>=15
requests>=2.31

# Phase 2-3 (features/model) — install when you reach modelling
scikit-learn>=1.4
lightgbm>=4.3
understatapi>=0.5   # free Understat xG/xA scraping

# Phase 4 (optimization)
pulp>=2.8           # or: ortools>=9.9

# Product layer (site export, scoreboard, solver API)
scipy>=1.12         # Spearman on the scoreboard
fastapi>=0.110
uvicorn>=0.29
httpx>=0.27         # FastAPI TestClient
joblib>=1.3

# Test-only
responses>=0.25,<0.27   # FPL API HTTP mocking in tests
```

**Split pattern (D-02):**
- `requirements.in`: everything above except the `# Test-only` block. Per RESEARCH.md D-03/Pitfall 3, pin `understatapi==0.7.1` explicitly (not `>=0.5`) and `pulp>=3.3,<4.0` explicitly (not the current `>=2.8`).
- `requirements-dev.in`: `-r requirements.in` (or repeat runtime deps per uv convention) plus `responses==0.25.x`, `pytest`, `ruff` (new lint tool, package-legitimacy gated).

**Comment style to preserve:** grouped-by-phase comments with a trailing inline rationale comment on non-obvious pins (e.g., `# free Understat xG/xA scraping`) — keep this convention in the `.in` files so the "why this pin" context isn't lost when the loose `requirements.txt` is replaced by the hashed lock.

**Compile command** (RESEARCH.md, verified live this session):
```bash
uv pip compile requirements.in --generate-hashes --python-version 3.14 -o requirements.txt
uv pip compile requirements-dev.in --generate-hashes --python-version 3.14 -o requirements-dev.txt
```

---

### `.github/workflows/daily.yml` and `weekly.yml` (config, event-driven) — modernize in place

**Analog:** the files themselves (current content shown below) — this is an edit, not a new-file pattern.

**Current `daily.yml` full content:**
```yaml
name: daily
on:
  schedule:
    - cron: "30 2 * * *"
  workflow_dispatch:
jobs:
  daily:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - name: Run daily jobs
        env:
          PYTHONPATH: .
        run: |
          python -m data.snapshot
          python -m models.price --train || true
          python -m models.price
          python -m predict.scoreboard
      - name: Commit outputs
        run: |
          git config user.name "fpl-bot"
          git config user.email "actions@users.noreply.github.com"
          git add data/snapshots web/data models/artifacts/price_model.joblib || true
          git diff --cached --quiet || git commit -m "daily: snapshot + watchlist $(date -u +%F)"
          git push
```

**Current `weekly.yml` full content:**
```yaml
# Weekly pre-deadline export: predictions + site JSON + digest. Dormant until
# this repo is pushed to GitHub. Requires models/artifacts/xp_model.joblib in
# the repo (7 MB — under GitHub's limits, no LFS needed).
name: weekly
on:
  schedule:
    - cron: "0 8 * * 5"
  workflow_dispatch:
jobs:
  weekly:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - name: Export predictions + digest
        env:
          PYTHONPATH: .
        run: |
          python -m data.live_history
          python -m predict.export
          python -m models.price
          python -m predict.digest
      - name: Commit outputs
        run: |
          git config user.name "rajat sharma"
          git config user.email "<redacted-personal-email>"
          git add web/data data/raw/live || true
          git diff --cached --quiet || git commit -m "weekly: GW export $(date -u +%F)"
          git push
```

**Required modernization diffs (D-11/D-12/D-16):**
1. `on:` — drop the `schedule:` block entirely (D-12: dispatch-only), keep `workflow_dispatch:`.
2. `actions/checkout@v4` → SHA-pinned per RESEARCH.md's action version table (`actions/checkout@<sha>  # v7.0.1`).
3. `actions/setup-python@v5` with `python-version: "3.12"` → SHA-pinned `actions/setup-python@<sha>  # v7.0.0` with `python-version: "3.14"`.
4. `pip install -r requirements.txt` → `pip install --require-hashes -r requirements.txt` (D-04).
5. `weekly.yml`'s header comment ("Requires models/artifacts/xp_model.joblib in the repo") is a known-false assumption (D-05) — correct or delete it, do not preserve.
6. Git identity block — replace both the `fpl-bot`/`actions@users.noreply.github.com` (already close to correct) and especially `weekly.yml`'s hardcoded personal `"rajat sharma"` / `<redacted-personal-email>` with the github-actions bot identity:
   ```yaml
   git config user.name "github-actions[bot]"
   git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
   ```
7. Everything else (job structure, `env: PYTHONPATH: .`, `git add ... || true` + `git diff --cached --quiet ||` commit-if-changed idiom) is the established pattern — keep it verbatim as the shape for any new scheduled-job step.

---

### `.github/workflows/ci.yml` (config, event-driven) — new file

**Analog:** `daily.yml`/`weekly.yml` for single-job YAML shape (checkout → setup-python → pip install → run steps), but the multi-job chained-artifact graph itself has no in-repo analog — build from RESEARCH.md's Architecture Patterns diagram and Code Examples verbatim (GHCR publish block, Trivy block, action SHAs are pre-resolved there).

**Reusable conventions to carry over from daily/weekly.yml:**
- `permissions:` scoped per job (daily/weekly use `contents: write` only for the job that needs it — same discipline applies to ci.yml's `packages: write` on the publish job only, per RESEARCH.md Security Domain).
- `env: PYTHONPATH: .` for any step invoking `python -m ...` directly (not needed if only `pytest`/`uvicorn` are invoked, since those already resolve the package via `pytest.ini`/being run from repo root — check per-step whether `python -m` is used).
- `runs-on: ubuntu-latest` — consistent across all three workflows.

**Pytest invocation must match `pytest.ini`:**
```ini
[pytest]
addopts = -p no:playwright -p no:seleniumbase
testpaths = tests
```
No extra CLI flags needed beyond what's in `pytest.ini`; `pytest tests/` (or bare `pytest`) picks this up automatically since `pytest.ini` lives at repo root.

**Frontend build command (the real typecheck, per RESEARCH.md anti-pattern note):**
```json
"build": "tsc -b && vite build",
"postbuild": "cp dist/index.html dist/404.html"
```
Use `npm --prefix frontend run build` — never `npm run typecheck` (confirmed no-op, `tsc --noEmit` with empty root `tsconfig.json`).

**Frontend test command:**
```json
"test": "node scripts/check-tokens.mjs && vitest run"
```
`npm --prefix frontend test`.

**E2E install + run commands (from `e2e/package.json`, reuse verbatim):**
```json
"test": "playwright test",
"install:browser": "playwright install --with-deps chromium"
```
`npm --prefix e2e run install:browser && npx --prefix e2e playwright test` — this reuses `e2e/playwright.config.ts`'s `webServer` array unchanged (per D-08/CONTEXT.md), which already chains `npm --prefix frontend run build && uvicorn ...` and sets `FPL_FIXTURE_DIR` — CI must NOT reimplement any of that server-boot logic, just invoke `playwright test` and let the config own it. Set `CI=true` (Playwright auto-detects this via `process.env.CI`, controlling `reuseExistingServer` and `retries`).

---

### `Dockerfile` (config, batch) — new file, no in-repo analog

No existing Dockerfile in this repo. Use RESEARCH.md's Pattern 1 skeleton verbatim as the starting structure (multi-stage `python:3.14-slim`, builder installs hashed lock via `--prefix=/install`, runtime stage adds `libstdc++6` for the bundled CBC binary, `COPY . .` for app code, `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`). Add non-root `USER` per RESEARCH.md Security Domain (no existing UID/GID convention in repo — new territory, planner's/executor's discretion).

**Relevant `api/main.py` facts that shape the Dockerfile/smoke test (verified in RESEARCH.md, not re-read here since RESEARCH.md already quotes exact line numbers):**
- `/api/health` never calls `_refresh()` — boots without a model artifact present.
- `_refresh()` only does `joblib.load(...)` when `_FIXTURE_ROOT` is falsy — set `FPL_FIXTURE_DIR` and the model load is skipped entirely.
- Static mount serves `web/` by default, `frontend/dist` in some fixture-mode path — D-06 requires the image to `COPY` both trees so `api/main.py`'s existing mount logic (unchanged this phase) has both available.

---

### `.dockerignore` (config) — new file

**Analog:** `.gitignore` (root) — mirror its exclusion categories, since the same repo layout applies, but `.dockerignore` additionally must exclude things `.gitignore` correctly keeps tracked (e.g. `.git/`, `.planning/`, `tests/`, `e2e/`, `.github/`) because those are irrelevant to the image per CONTEXT.md's "excluding tests/e2e/.planning is expected."

**Full current `.gitignore` content (base to extend from):**
```
# Python artifacts
__pycache__/
*.py[cod]
.pytest_cache/

# Node artifacts
node_modules/
frontend/node_modules/
frontend/dist/
dist/
*.tsbuildinfo

# Pipeline data (rebuilt by data/ingest.py, data/build_table.py)
data/raw/
data/processed/
data/cron.log

# model output (rebuilt by models/train.py, models/price.py)
models/artifacts/

# miscellaneous
downloaded_files/
google-chrome-stable_current_amd64.deb
*.deb

# Playwright E2E run output
e2e/test-results/
e2e/playwright-report/
e2e/blob-report/

# Secrets
.env
.env.*
!.env.example

# --- Irreplaceable daily price-snapshot history ---
!data/snapshots/
!data/snapshots/**
```

**Important divergence:** `.gitignore` has `!data/snapshots/` (re-included, tracked in git) — `.dockerignore` should NOT re-include it; snapshot history has no business inside a stateless image. Also note `.gitignore` deliberately does NOT ignore `frontend/dist/` from the *build context* sense — `.dockerignore` must NOT exclude `frontend/dist/` (needed per D-06, it's produced by CI before `docker build` runs) even though `.gitignore` ignores it from git tracking. This is the one place the two ignore-files must diverge, not mirror.

**`.dockerignore` should add (beyond `.gitignore`'s list):** `.git/`, `.planning/`, `tests/`, `e2e/` (except nothing needed at build time — bind-mounted at smoke-test time per RESEARCH.md, not COPY'd), `.github/`, `*.md`, `.claude/`, `.gsd/`.

---

### `scripts/smoke_test.sh` (utility, request-response) — new file

**Analog:** `scripts/verify_frontend_build.sh`

**Shell-script conventions to copy (full analog file, 42 lines):**
```bash
#!/usr/bin/env bash
# Production build purity gate: proves no pipeline export (web/data/*.json) was
# copied or bundled into the frontend build output. Filename comparison rather
# than a content grep on purpose — it cannot be defeated by minification and
# does not depend on any particular field name surviving the bundler.
#
# Usage: bash scripts/verify_frontend_build.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d frontend/public/data ]; then
  echo "FAILED: frontend/public/data exists — pipeline data must never be copied into the build"
  exit 1
fi

echo "[verify_frontend_build] running npm --prefix frontend run build"
npm --prefix frontend run build
...
```

**Pattern to replicate in `smoke_test.sh`:**
- `#!/usr/bin/env bash` shebang + purpose comment block at top (module-docstring-equivalent convention this repo uses everywhere, including shell).
- `set -euo pipefail` — fail-fast, matches repo's error-handling convention (raise on failure, no silent continue) applied to shell.
- `cd "$(dirname "$0")/.."` to make the script runnable from any cwd (repo root relative).
- Bracketed `echo "[smoke_test] ..."` status tags — matches the `[price]`/`[odds]` module-tagged print convention from Python (`data/live_odds.py`, `models/price.py`), applied consistently to shell.
- `echo "FAILED: <reason>"` + `exit 1` on failure — matches this repo's explicit, message-carrying failure convention (`raise SystemExit("Missing ...")` in Python) translated to shell idiom.

**Combine with RESEARCH.md's smoke-test payload (Pattern 3 / Code Examples):**
```bash
docker run -d --name fpl-smoke -p 8000:8000 \
  -e FPL_FIXTURE_DIR=/fixtures/v1/normal \
  -v "$(pwd)/e2e/fixtures:/fixtures:ro" \
  ghcr.io/sraja/fpl:smoke-test
# poll /api/health until ready (verify_frontend_build.sh's style: fail loud, no silent retries-forever)
curl -f http://localhost:8000/api/health
curl -f -X POST http://localhost:8000/api/solve -H 'Content-Type: application/json' -d '{}'
docker stop fpl-smoke
```

---

## Shared Patterns

### Comment/documentation header convention
**Source:** every Python module in the repo (docstring-first), `e2e/playwright.config.ts` (long rationale block), `scripts/verify_frontend_build.sh` (comment block above shebang)
**Apply to:** `Dockerfile`, `ci.yml`, `.dockerignore`, `smoke_test.sh` — every new file in this phase should open with a short "what this does and why" comment block, matching the repo-wide convention of explaining design decisions inline rather than relying on external docs.

### Fail-fast / explicit-error convention
**Source:** `features/engineer.py:110` (`raise SystemExit("Missing player_gw.parquet. Run ...")`), `scripts/verify_frontend_build.sh` (`echo "FAILED: ..."; exit 1`)
**Apply to:** `smoke_test.sh`, any inline CI `run:` blocks — errors should be loud, specific, and named (which check failed, what to run to fix it), not bare non-zero exits with no message.

### GitHub Actions job/step shape
**Source:** `.github/workflows/daily.yml`, `.github/workflows/weekly.yml` (current, pre-modernization)
**Apply to:** `ci.yml`'s job definitions
```yaml
jobs:
  <job-name>:
    runs-on: ubuntu-latest
    permissions:
      <scoped-permission>: <read|write>
    steps:
      - uses: actions/checkout@<sha>
      - uses: actions/setup-python@<sha>
        with:
          python-version: "3.14"
          cache: pip
      - run: pip install --require-hashes -r requirements.txt -r requirements-dev.txt
      - name: <step description>
        env:
          PYTHONPATH: .
        run: |
          <commands>
```
Every `uses:` line must be SHA-pinned per D-04/CI-04 (daily/weekly.yml's current `@v4`/`@v5` tags are themselves an artifact of the pre-hardening state and must be replaced too, not just ci.yml written correctly from scratch).

### Commit-if-changed idiom (daily.yml/weekly.yml only, not ci.yml)
**Source:** `.github/workflows/daily.yml` lines 24-28
```bash
git add data/snapshots web/data models/artifacts/price_model.joblib || true
git diff --cached --quiet || git commit -m "daily: snapshot + watchlist $(date -u +%F)"
git push
```
Keep this idiom unchanged when modernizing daily/weekly.yml — only the identity block and action pins change, not this control flow.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `Dockerfile` | config | batch | Repo has never had a container build; no multi-stage build precedent anywhere. Use RESEARCH.md Pattern 1 skeleton as primary source. |
| `.github/workflows/ci.yml` job-chaining/artifact-passing structure | config | event-driven | `daily.yml`/`weekly.yml` are both single flat jobs with no `needs:`/`upload-artifact`/`download-artifact` — the chained multi-job graph (D-08) has no precedent. Use RESEARCH.md Architecture Patterns diagram + Code Examples. |
| Trivy scan step / GHCR publish step | config | event-driven | No scanning or registry-publish step exists anywhere in the repo today. Use RESEARCH.md Code Examples verbatim (SHA-pinned actions already resolved there). |

## Metadata

**Analog search scope:** repo root (`requirements.txt`, `.gitignore`), `.github/workflows/`, `scripts/`, `e2e/` (`package.json`, `playwright.config.ts`), `frontend/package.json`, `pytest.ini`
**Files scanned:** 9 (all read in full — none exceeded 2,000 lines)
**Pattern extraction date:** 2026-09-04
