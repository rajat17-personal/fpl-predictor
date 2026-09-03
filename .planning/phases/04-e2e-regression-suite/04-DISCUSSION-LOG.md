# Phase 4: E2E Regression Suite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-03
**Phase:** 4-E2E Regression Suite
**Areas discussed:** System-under-test topology, Fixture provenance & GW scenarios, Solver-flow determinism, Assertion depth & test matrix

---

## System-under-test topology

### What backs the /api solver endpoints when Playwright runs?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixture-mode API (Recommended) | Env-var seam in api/main.py loads frozen bootstrap/fixtures from disk; real FastAPI + solver run end to end | ✓ |
| Playwright route() mocks | Browser intercepts /api/*; no backend exercised in E2E | |
| Stub FPL server process | Second HTTP server impersonating fantasy.premierleague.com | |

### Local runs vs CI topology

| Option | Description | Selected |
|--------|-------------|----------|
| Always CI-identical (Recommended) | npm run build → uvicorn serves dist/ + fixture data, locally and in CI | ✓ |
| Dev-server locally, built in CI | Vite dev server for authoring; two topologies | |
| Both, via a flag | Default CI-identical + opt-in E2E_DEV mode | |

### How uvicorn serves the built frontend (vanilla stays live until cutover)

| Option | Description | Selected |
|--------|-------------|----------|
| Env-var mount in api/main.py (Recommended) | Same seam switches static mount to frontend/dist; Phase 7 flips the same switch | ✓ |
| Separate test-only ASGI entry | api/e2e_app.py wrapper; drift risk | |
| Two processes | uvicorn API + static server for dist/; orchestration/CORS complexity | |

### Auth mode during E2E

| Option | Description | Selected |
|--------|-------------|----------|
| Open mode (Recommended) | FPL_API_KEYS unset; APIT-02 already covers three-mode auth | ✓ |
| Keyed mode | Would force new frontend key-sending code that belongs to the auth milestone | |
| One open + one keyed spot-check | 401-surface check at cost of second server config | |

### Server lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Playwright webServer (Recommended) | playwright.config.ts declares build+uvicorn with readiness; npx playwright test is the single entry point | ✓ |
| Shell script wrapper | scripts/e2e.sh hand-rolls readiness/teardown | |

---

## Fixture provenance & GW scenarios

### Provenance of frozen web/data snapshot sets

| Option | Description | Selected |
|--------|-------------|----------|
| Real capture + synthesized variants (Recommended) | Freeze a real week's export as "normal"; script-derive blank/DGW variants | ✓ |
| Promote the Vitest fixtures | Sparse hand-crafted rows; top-50/scroll behavior untested | |
| Generator script | Synthetic data through real export builders | |

### API-side FPL-upstream payload provenance

| Option | Description | Selected |
|--------|-------------|----------|
| Real capture, same week (Recommended) | Same freeze as web/data → one coherent gameweek across /api and /data; trimmed to fields the API reads | ✓ |
| Synthetic fake_boot style | Squad pool wouldn't match frozen web/data players | |
| Your real team, synthetic pool | Same coherence problem | |

### What "versioned" means

| Option | Description | Selected |
|--------|-------------|----------|
| Versioned dirs + manifest (Recommended) | e2e/fixtures/v1/{normal,blank,dgw}/ + MANIFEST.md; contract change cuts v2, v1 immutable | ✓ |
| Manifest + schema drift guard | Adds a pytest comparing builder output keys vs fixtures | |
| Plain committed files | Can't distinguish "app regressed" from "contract moved" | |

### How blank/DGW sets get used

| Option | Description | Selected |
|--------|-------------|----------|
| Normal + targeted scenario specs (Recommended) | Flows on normal; blank/DGW back specs for surfaces they change | ✓ |
| Full suite × 3 scenarios | ~3× runtime and triple golden maintenance | |
| Scenario smoke only | Weaker than E2E-01 implies | |

---

## Solver-flow determinism

### Source of xP predictions in fixture mode

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen prediction pool (Recommended) | Solver input pool frozen at capture; no model artifact at E2E/CI time; real ILP runs | ✓ |
| Committed real artifact | Multi-MB binary in git; retrains shift every expected value; cp314 LightGBM in CI | |
| Tiny deterministic stub model | Extra machinery the frozen pool avoids | |

### Solve-result assertions

| Option | Description | Selected |
|--------|-------------|----------|
| Invariants + one pinned golden (Recommended) | Structural invariants everywhere + one canonical exact XI/transfers golden | ✓ |
| Full golden everywhere | Solver tie-flip breaks many tests at once | |
| Invariants only | Wrong-but-legal solve would pass | |

### Multi-week plan flow (10–60s warning)

| Option | Description | Selected |
|--------|-------------|----------|
| Real plan, short horizon (Recommended) | Real /api/plan at 2-GW minimum horizon, generous timeout | ✓ |
| Skip plan flow in E2E | Only multi-request flow goes browser-untested | |
| Full-horizon real plan | Tens of seconds per CI pass for little value | |

---

## Assertion depth & test matrix

### Browsers

| Option | Description | Selected |
|--------|-------------|----------|
| Chromium only (Recommended) | Target regressions are engine-independent; other engines addable later | ✓ |
| Chromium + WebKit | iOS relevance but ~2× runtime; save for pre-launch | |
| All three engines | ~3× runtime, overkill | |

### Viewports

| Option | Description | Selected |
|--------|-------------|----------|
| Desktop + phone for pitch (Recommended) | Desktop flows + 1720px G-01-3 spec + phone-width pitch specs (D-07 promise) | ✓ |
| Desktop only + G-01-3 | UI-07's mobile pitch stays browser-unverified | |
| Every flow × both viewports | Doubles runtime; only the pitch reflows | |

### Visual regression

| Option | Description | Selected |
|--------|-------------|----------|
| Geometry assertions, no screenshots (Recommended) | boundingBox() measurements catch G-03-1-class drift; zero screenshot flake | ✓ |
| Targeted pitch screenshots | Baseline images environment-sensitive (WSL2 vs CI) | |
| Full-page screenshots everywhere | Maximum flake and baseline churn | |

### Source of exact expected values (E2E-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded literals from fixtures (Recommended) | True golden, hand-derived once from immutable v1 | ✓ |
| Computed from fixture JSON at test time | Re-implements the formatting under test | |
| Mixed | Literals for sentinels + computed sort order | |

---

## Claude's Discretion

- Env-var name(s) and internal design of the fixture seam; frozen-pool format (parquet vs JSON) and hook point
- Directory layout under `e2e/` (or `frontend/e2e/`), spec organization, npm script names
- Blank/DGW synthesis script language and location
- Exact viewport pixels beyond the mandated 1720px; timeout values; retry policy
- Whether dark mode gets an E2E spot-check

## Deferred Ideas

- WebKit/Firefox engine coverage — pre-launch pass
- Screenshot/visual-regression baselines — only if geometry assertions prove insufficient (needs docker-normalized env)
- Keyed-auth E2E spot-check — Supabase JWT milestone (PAID-02)
- Schema drift guard (builder output keys vs frozen fixture keys) — fits Phase 6 validation work
