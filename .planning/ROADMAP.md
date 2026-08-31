# Roadmap: FPL Predictor — Production Hardening

## Overview

This milestone takes a working FPL prediction system — validated model, ILP solvers, weekly JSON export contract, live vanilla site — and makes it production-trustworthy ahead of monetization. The journey runs bottom-up along the dependency chain: first build the missing API test base layer and prove the React/Vite dev seam against it; then rebuild the seven non-pitch pages at verified parity from the same `web/data/*.json` contract; then the highest-risk UI, the FPL-style pitch renderer and squad views; then a deterministic Playwright regression suite backed by frozen fixtures; then containerization and CI so every push is verified and produces a publishable image; then close the security, reliability, and observability gaps from `CONCERNS.md`; and finally validate parity across a full real gameweek cycle before retiring the vanilla site. The load-bearing constraint throughout: the weekly recommendation cycle never breaks. The vanilla site stays live until the final phase.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Test Base Layer & App Skeleton** - API integration tests plus a React/Vite scaffold that proves the dev-proxy seam
- [ ] **Phase 2: Data Layer & Non-Pitch Pages** - Seven pages rebuilt at verified parity from the JSON export contract
- [ ] **Phase 3: Pitch Renderer & Squad Views** - FPL-style pitch, team page solving, and rate-my-team
- [ ] **Phase 4: E2E Regression Suite** - Deterministic Playwright coverage of the critical flows on frozen fixtures
- [ ] **Phase 5: Container Build & CI Pipeline** - Locked deps, multi-stage Docker image, GitHub Actions verification and publish
- [ ] **Phase 6: Security, Reliability & Observability Hardening** - Close the CONCERNS.md production-readiness gaps
- [ ] **Phase 7: Parity Validation & Cutover** - Full gameweek cycle side-by-side, then retire the vanilla site

## Phase Details

### Phase 1: Test Base Layer & App Skeleton

**Goal**: The API has a real test safety net, and a React app talks to it through a proven runtime seam
**Depends on**: Nothing (first phase)
**Requirements**: APIT-01, APIT-02, APIT-03, UI-01
**Success Criteria** (what must be TRUE):

  1. `pytest` exercises `/solve`, `/rate`, `/team`, `/health`, and `/meta` against a mocked FPL API, and fails when any endpoint's response contract or error handling regresses
  2. The `require_key()` auth stub is covered in all three modes — open, valid key, invalid key — so swapping in real auth later is a verified change rather than a leap
  3. A concurrent solve + pool-refresh test runs green repeatedly, making the cache/lock race observable in tests instead of only in production
  4. `npm run dev` serves a React (Vite, TypeScript 6.x) app whose routes for all 8 pages resolve, fetching `web/data/*.json` and `/api` at runtime through the dev proxy — with no pipeline data bundled into the build

**Plans**: 1/5 plans executed (3 waves)
**Wave 1**

- [x] 01-01-PLAN.md — Repo baseline (`.gitignore` + initial source commit) and the blocking package-legitimacy gate

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-02-PLAN.md — API contract tracer: `_initial_state()` seam, autouse reset fixture, `/health` + `/meta` + `/solve` with bounds and precision
- [ ] 01-04-PLAN.md — React dev-seam tracer: Vite + React Router 7 + TanStack Query scaffold, `/api` and `/data` proxy, design tokens, shell chrome, Vitest harness

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-03-PLAN.md — `/team` and `/rate` against a `responses`-mocked FPL API, three-mode `require_key` coverage, and the concurrency race test
- [ ] 01-05-PLAN.md — All 8 routes with per-route error boundaries, the loading/error/empty/404 states, and the three UI-SPEC backstop tests

**UI hint**: yes

**Research flags**: async + `threading.Lock` interaction in FastAPI may need a spike before APIT-03; TypeScript 6.x (not 7.x — ESLint support unstable in 7.0).

### Phase 2: Data Layer & Non-Pitch Pages

**Goal**: Seven of the eight pages render at verified parity with the vanilla site from the same JSON contract
**Depends on**: Phase 1
**Requirements**: UI-02, UI-03, UI-04, UI-05, UI-06, UIX-02
**Success Criteria** (what must be TRUE):

  1. The xP table sorts, filters, and formats identically to the vanilla site — including secondary sort keys, number formatting, and conditional styling — checked against an enumerated inventory of the vanilla rules, not by eyeball
  2. The fixtures page shows an FDR ticker in the standard 1–5 green→red convention
  3. The prices page shows watchlist rise/fall indicators matching the vanilla site's calls
  4. League, scoreboard, differentials, and methodology pages present the same information as their vanilla counterparts from the same JSON files
  5. A gameweek meta banner with a live deadline countdown is visible on every page, and a dark mode toggle persists across navigation and reload

**Plans**: TBD
**UI hint**: yes

**Research flags**: enumerate every `.sort()`, `.toFixed()`, secondary sort key, and conditional class in `web/assets/app.js` as an explicit checklist *before* writing React. Decide CSR vs prerender per page explicitly (methodology, scoreboard, differentials are the SEO candidates).

### Phase 3: Pitch Renderer & Squad Views

**Goal**: Users see and manipulate their squad on an FPL-style pitch, including the solver and rate-my-team flows
**Depends on**: Phase 2
**Requirements**: PITCH-01, PITCH-02, PITCH-03, PITCH-04, UI-07, UIX-01, UIX-03
**Success Criteria** (what must be TRUE):

  1. A documented decision records where shirt/kit imagery comes from — FPL's own CDN URLs captured from live devtools, or neutral generated kits — and a non-affiliation disclaimer is visible on the site
  2. A squad renders on a pitch in formation-driven rows with bench, each card showing shirt, name, price, xP with its p10/p90 interval, and C/VC badges — and both the pitch and the data tables stay usable at phone width
  3. From the team page a user loads a squad (default entry 6980093), locks or excludes players, requests a solve, and sees transfers and the XI update on the pitch
  4. Rate-my-team shows a visual diff of the user's squad against the optimal one with suggested swaps
  5. Chip timing shows a "why this GW" explanation with DGW/BGW callouts

**Plans**: TBD
**UI hint**: yes

**Research flags**: FPL shirt/badge CDN URL patterns are community knowledge, not documented — open devtools on `fantasy.premierleague.com`'s My Team page and capture the exact `<img src>` values. **Do not guess URL patterns.** Trademark posture must be settled here, not at payment-gateway review.

### Phase 4: E2E Regression Suite

**Goal**: The critical user flows are protected by browser tests that pass or fail on code, never on the calendar
**Depends on**: Phase 3
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04, E2E-05
**Success Criteria** (what must be TRUE):

  1. Frozen versioned JSON snapshots (normal, blank, double gameweek) plus a mocked FPL API back every test — the suite behaves identically on deadline day and mid-week, with no live-data dependence
  2. The team/pitch + solver flow is covered end to end: load a squad, request a solve, assert the resulting XI and transfers
  3. The xP table and captains view are covered, asserting exact cell values and sort order rather than "a table rendered"
  4. The rate-my-team flow is covered end to end
  5. The fixtures and prices pages are covered

**Plans**: TBD

**Research flags**: use the Node `@playwright/test` runner, not `pytest-playwright` — the repo's `pytest.ini` disables both plugins over the `--browser` flag collision. Design the fixture strategy (E2E-01) before writing the first test.

### Phase 5: Container Build & CI Pipeline

**Goal**: Every push is automatically verified and produces a publishable, scanned container image
**Depends on**: Phase 4
**Requirements**: CI-01, CI-02, CI-03, CI-04, CI-05, SEC-02, SEC-04
**Success Criteria** (what must be TRUE):

  1. Dependencies are locked and verified installable from scratch in a clean environment, with `cp314` wheels confirmed available for every ML dependency
  2. The repo is CI-ready: the 134MB Chrome `.deb` is gone, `.gitignore` covers generated artifacts, and the workflows are tracked in git
  3. Every push and PR runs lint, typecheck, pytest + API tests, and a frontend-build + Playwright job against uvicorn serving the built frontend with fixture data — and the build fails on any regression
  4. A multi-stage `python:3.14-slim` image builds, passes a smoke test proving the CBC solver is available and `/health` responds, and publishes to GHCR with SHA-pinned actions and a scoped `GITHUB_TOKEN` (deploy step stubbed)
  5. A Trivy vulnerability scan reports on the image on every build

**Plans**: TBD

**Research flags**: verify `cp314` wheel availability on PyPI for LightGBM, scikit-learn, PyArrow, and PuLP before finalizing the lockfile — scikit-learn lacked 3.14 wheels as of Oct 2025. Pin from a clean pip venv, not `pip freeze` inside the conda env. Watch image size (multi-stage; ML deps can balloon past 1.5GB).

### Phase 6: Security, Reliability & Observability Hardening

**Goal**: The system fails loudly, safely, and visibly instead of silently
**Depends on**: Phase 5
**Requirements**: SEC-01, SEC-03, REL-01, REL-02, REL-03, REL-04, REL-05, OBS-01, OBS-02, OBS-03
**Success Criteria** (what must be TRUE):

  1. The API accepts requests only from configured origins, and secrets are read from a mode-600 `.env` — never present in code, logs, or workflow files
  2. A malformed or changed FPL bootstrap/fixtures payload is rejected by schema validation with an actionable message, and a missing or corrupt export JSON produces a clear error instead of a traceback
  3. The daily snapshot and weekly export crons retry on transient failure and surface failures visibly — a failed run is noticed the same day, not discovered weeks later
  4. The API emits structured JSON request logs and exposes distinct liveness and readiness endpoints
  5. A long-running API process leaks no file handles, and the solve cache is bounded with correct invalidation under concurrent requests

**Plans**: TBD

**Research flags**: none — FastAPI CORS, pydantic validation, structured logging, and LRU/TTL caching are standard patterns. The concrete gap inventory lives in `.planning/codebase/CONCERNS.md`. The daily snapshot cron is time-critical (price history cannot be backfilled) — REL-02 changes must not interrupt it.

### Phase 7: Parity Validation & Cutover

**Goal**: The React site becomes the live site without breaking a single weekly recommendation cycle
**Depends on**: Phase 6
**Requirements**: CUT-01
**Success Criteria** (what must be TRUE):

  1. The React and vanilla sites run side by side through a complete gameweek cycle — deadline → live → finished — serving the same JSON exports
  2. Every page's output is compared against the vanilla site across that cycle, with each difference either explained as an intended improvement or fixed; no unexplained deltas remain
  3. The vanilla site is retired only after that cycle passes, and the weekly recommendations flow uninterrupted throughout

**Plans**: TBD

**Research flags**: none — this is an execution checklist, not a research problem. Its completion is gated on real calendar time (a full gameweek), so it cannot be compressed.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Test Base Layer & App Skeleton | 1/5 | In Progress|  |
| 2. Data Layer & Non-Pitch Pages | 0/TBD | Not started | - |
| 3. Pitch Renderer & Squad Views | 0/TBD | Not started | - |
| 4. E2E Regression Suite | 0/TBD | Not started | - |
| 5. Container Build & CI Pipeline | 0/TBD | Not started | - |
| 6. Security, Reliability & Observability Hardening | 0/TBD | Not started | - |
| 7. Parity Validation & Cutover | 0/TBD | Not started | - |

## Requirement Coverage

All 40 v1 requirements map to exactly one phase.

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1 | APIT-01, APIT-02, APIT-03, UI-01 | 4 |
| 2 | UI-02, UI-03, UI-04, UI-05, UI-06, UIX-02 | 6 |
| 3 | PITCH-01, PITCH-02, PITCH-03, PITCH-04, UI-07, UIX-01, UIX-03 | 7 |
| 4 | E2E-01, E2E-02, E2E-03, E2E-04, E2E-05 | 5 |
| 5 | CI-01, CI-02, CI-03, CI-04, CI-05, SEC-02, SEC-04 | 7 |
| 6 | SEC-01, SEC-03, REL-01, REL-02, REL-03, REL-04, REL-05, OBS-01, OBS-02, OBS-03 | 10 |
| 7 | CUT-01 | 1 |
| **Total** | | **40** |

## Milestone Invariants

These hold across every phase, not just one:

- The weekly recommendation cycle (xP table, squad, captains, transfers) keeps flowing. The vanilla site stays live and authoritative until CUT-01 completes.
- The daily snapshot cron runs every day regardless of milestone work — price-model history cannot be backfilled.
- `web/data/*.json` is the pipeline↔product contract. It is consumed unchanged and always fetched at runtime, never bundled into a build.
- All Python work uses the conda env `python314` at `/home/sraja/miniconda3/envs/python314/bin/python`.

---
*Roadmap created: 2026-08-31*
