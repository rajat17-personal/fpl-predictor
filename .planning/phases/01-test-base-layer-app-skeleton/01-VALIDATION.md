---
phase: "1"
slug: "test-base-layer-app-skeleton"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-08-31"
updated: "2026-08-31"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

This phase has **two independent test tiers** with separate frameworks: a Python/pytest tier for the
API safety net (APIT-01/02/03) and a Node/Vitest tier for the React shell (UI-01). Both are built
from nothing in this phase — neither `tests/test_api.py` nor `frontend/` exists today — so every row
below starts as a Wave 0 gap.

---

## Test Infrastructure

### Backend (APIT-01, APIT-02, APIT-03)

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (installed in the `python314` conda env) |
| **Config file** | `pytest.ini` (repo root) — `testpaths = tests`, `addopts = -p no:playwright -p no:seleniumbase` |
| **Quick run command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_api.py -x -q` |
| **Full suite command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q` |
| **Estimated runtime** | ~30s quick / ~75s full (the concurrency test runs 20 real CBC solves) |

### Frontend (UI-01)

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.x + jsdom + @testing-library/react — **installed by plan 01-04 Task 3** |
| **Config file** | `frontend/vitest.config.ts` — created by plan 01-04 Task 3 |
| **Quick run command** | `npm --prefix frontend run test` |
| **Full suite command** | `npm --prefix frontend run test && npm --prefix frontend run typecheck && npm --prefix frontend run build` |
| **Estimated runtime** | ~10s test / ~25s full |

### Cross-tier integration harness (UI-01 runtime seam)

| Property | Value |
|----------|-------|
| **Framework** | Bash + Node `fetch` probes against live `uvicorn` + `vite dev` processes |
| **Config file** | `scripts/verify_dev_proxy.sh`, `scripts/verify_frontend_build.sh` — created by plan 01-04 |
| **Quick run command** | `bash scripts/verify_dev_proxy.sh` |
| **Estimated runtime** | ~20s (bounded 60s startup poll, then three probes, then teardown) |

**Working directory for every command above: the repo root** (`/home/sraja/fpl`). All commands use
`npm --prefix` or an absolute interpreter path rather than `cd`, so none depends on the executor's cwd.

---

## Sampling Rate

- **After every task commit:** backend tasks run `python -m pytest tests/test_api.py -x -q`; frontend tasks run `npm --prefix frontend run test`
- **After every plan wave:** full backend suite (`python -m pytest -q`) plus, once `frontend/` exists, `npm --prefix frontend run test && npm --prefix frontend run typecheck && npm --prefix frontend run build` and `bash scripts/verify_dev_proxy.sh`
- **Before `/gsd-verify-work`:** every command in this file green, including the five-consecutive-run concurrency gate
- **Max feedback latency:** 75 seconds (the full backend suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | APIT-01, UI-01 | T-01-01 / T-01-02 / T-01-03 / T-01-04 | No secret, no 134MB installer, and no `node_modules` tree can be staged; irreplaceable `data/snapshots/` stays tracked | infra | `git ls-files … \| wc -l \| grep -qx 6 && git ls-files data/snapshots \| grep -q . && git check-ignore -q data/raw && … && echo "REPO BASELINE OK"` | ✅ (git) | ⬜ pending |
| 01-01-02 | 01 | 1 | APIT-01, UI-01 | T-01-SC | 13 registry-flagged `[SUS]` packages reviewed by a human before any install; `gate="blocking-human"`, never auto-approved | manual gate | — (blocking human checkpoint; see Manual-Only Verifications) | n/a | ⬜ pending |
| 01-02-01 | 02 | 2 | APIT-01 | T-02-01 / T-02-02 / T-02-03 | No outbound FPL request and no `joblib.load` of the untracked artifact during any test; module globals reset per test | integration | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_api.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | APIT-01 | T-02-04 | `SolveRequest` pydantic bounds reject out-of-range input at every edge; `_resolve` tie-break is deterministic | integration | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_api.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 3 | APIT-01 | T-03-SC / T-03-02 / T-03-03 | Every FPL URL intercepted; an unregistered outbound call raises rather than reaching the network; fixtures carry no third-party PII | integration | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_api.py -x -q -k "team or rate"` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 3 | APIT-02 | T-03-01 / T-03-04 / T-03-06 | `require_key` pinned in open / valid-key / invalid-key mode on both protected endpoints; the stub itself provably unedited | integration | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_api.py -x -q -k "require_key or stay_open"` then `git diff --quiet HEAD -- api/main.py && echo "AUTH STUB UNCHANGED"` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 3 | APIT-03 | T-03-05 / T-03-06 | 20 concurrent solves across 8 threads all return 200 with no escaped exception and no corrupted `_state`; no drive-by cache fix | concurrency | `for i in 1 2 3 4 5; do … pytest tests/test_api.py -x -q -k concurrent \|\| exit 1; done; echo "CONCURRENCY STABLE x5"` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 2 | UI-01 | T-04-SC / T-04-01 / T-04-03 / T-04-04 / T-04-05 | Pipeline data fetched at runtime through a loopback-only proxy; `typescript` pinned to 6.0.3 so the lint toolchain cannot silently degrade | integration | `bash scripts/verify_dev_proxy.sh` and `npm --prefix frontend run build` and the `PINS OK` node gate | ❌ W0 | ⬜ pending |
| 01-04-02 | 04 | 2 | UI-01 | T-04-02 | No file from `web/data` reaches `frontend/dist`; no component hardcodes a colour | build gate | `bash scripts/verify_frontend_build.sh` and `! grep -rEq … frontend/src --include=*.tsx && echo "NO HEX IN COMPONENTS"` | ❌ W0 | ⬜ pending |
| 01-04-03 | 04 | 2 | UI-01 | — | Component-test harness runs non-watch, so a Phase 5 CI job cannot hang on it | unit | `npm --prefix frontend run test` and `npm --prefix frontend run typecheck` | ❌ W0 | ⬜ pending |
| 01-05-01 | 05 | 3 | UI-01 | T-05-03 | Every unmatched path resolves to a defined 404 state; all 9 route entries registered with per-route `errorElement` | integration | `npm --prefix frontend run typecheck && npm --prefix frontend run build` then the `ROUTES REGISTERED 9` node gate | ❌ W0 | ⬜ pending |
| 01-05-02 | 05 | 3 | UI-01 | T-05-02 | No raw error message, response body, request URL or stack trace reaches the DOM | integration | `npm --prefix frontend run typecheck && npm --prefix frontend run build` then the `STATE COMPONENTS WIRED` node gate, then `bash scripts/verify_dev_proxy.sh` | ❌ W0 | ⬜ pending |
| 01-05-03 | 05 | 3 | UI-01 | T-05-01 / T-05-02 / T-05-04 | One route's failure leaves the nav and siblings interactive; error copy provably leaks no internals; a skipped backstop suite fails the gate | unit (backstop) | `npm --prefix frontend run test` then `npm --prefix frontend run test -- --reporter=verbose 2>&1 \| grep -Eic 'spinner\|errorstate\|routeisolation'` (must be ≥3) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity check:** no three consecutive tasks lack an `<automated>` verify. The only task
without one is `01-01-02`, a `gate="blocking-human"` checkpoint, and it is bracketed by `01-01-01`
and `01-02-01`, both of which carry automated gates.

---

## Wave 0 Requirements

Test infrastructure that does not exist yet and is created inside this phase. Every ❌ W0 row above
resolves through one of these:

- [ ] `api/main.py` — add the `_initial_state()` DI seam (plan 01-02 Task 1)
- [ ] `tests/conftest.py` — autouse `_reset_api_state` fixture that rebuilds module globals and seeds the artifact sentinel (plan 01-02 Task 1)
- [ ] `tests/test_api.py` — new file, the whole APIT-01/02/03 suite (plans 01-02 and 01-03)
- [ ] `pip install "responses>=0.25,<0.27"` + the `requirements.txt` pin — not currently installed (plan 01-03 Task 1)
- [ ] `frontend/` — does not exist; scaffolded entirely by `npm create vite@latest frontend -- --template react-ts` (plan 01-04 Task 1)
- [ ] `frontend/vitest.config.ts` + `frontend/src/test/setup.ts` + the `test` and `typecheck` npm scripts (plan 01-04 Task 3)
- [ ] `scripts/verify_dev_proxy.sh` — the cross-tier runtime-seam harness (plan 01-04 Task 1)
- [ ] `scripts/verify_frontend_build.sh` — the no-bundled-data build gate (plan 01-04 Task 2)
- [ ] Root `.gitignore` — must land before the first `npm install` (plan 01-01 Task 1)

**Wave 0 ordering note:** the backend harness (01-02 Task 1) and the frontend harness (01-04 Tasks 1
and 3) both land in Wave 2, one wave before the tasks that depend on them. Wave 1 (plan 01-01) is
repo hygiene and the install gate, which are preconditions for both harnesses.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Package legitimacy sign-off on 13 `[SUS]`-flagged packages | APIT-01, UI-01 | Trust establishment: a machine cannot decide whether an unfamiliar registry package is the one you meant. Carries `gate="blocking-human"` and is never auto-approved, even under `workflow.auto_advance` | Plan 01-01 Task 2 lists each package with its registry URL, weekly download count and source repo; open the eight named registry pages and confirm the repository link and download magnitude match |
| `api/main.py` diff is a pure refactor | APIT-01 | The tests cannot detect a behavioural change they were written against. This module runs the live weekly pipeline | Plan 01-02 `<human-check>`: read the diff and confirm six keys, same defaults, same order, and no change to `_refresh`, `_pool`, `_solve_cache` or `CORSMiddleware` |
| No third-party manager PII in `responses` fixtures | APIT-01 | Whether a name is a real person's is a judgment, not an assertion | Plan 01-03 `<human-check>`: skim the three `responses.add` bodies |
| App shell visual conformance and mobile reflow | UI-01 | Visual layout, touch-target comfort, and colour distinguishability are not mechanically checkable at this fidelity | Plan 01-04 `<human-check>` (gameweek number, brand + footer, 375px reflow, runtime network request) and plan 01-05 `<human-check>` (8 nav links, active state, 404 route, nav wrap at 375px, live error + Retry recovery with uvicorn stopped and restarted) |

All other phase behaviours have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 12 of 13 tasks carry at least one `<automated>` command; the 13th is a blocking-human trust gate
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — all nine gaps above are created inside this phase, each one wave ahead of its first consumer
- [x] No watch-mode flags — `frontend/package.json`'s `test` script is `vitest run`, asserted by the `SCRIPTS OK` gate in plan 01-04 Task 3
- [x] Feedback latency < 75s
- [ ] `nyquist_compliant: true` set in frontmatter — set by `/gsd-validate-phase` after execution confirms the commands run green

**Approval:** pending
