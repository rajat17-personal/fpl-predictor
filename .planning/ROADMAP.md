# Roadmap: FPL Predictor — Production Hardening

## Overview

This milestone takes a working FPL prediction system — validated model, ILP solvers, weekly JSON export contract, live vanilla site — and makes it production-trustworthy ahead of monetization. The journey runs bottom-up along the dependency chain: first build the missing API test base layer and prove the React/Vite dev seam against it; then rebuild the seven non-pitch pages at verified parity from the same `web/data/*.json` contract; then the highest-risk UI, the FPL-style pitch renderer and squad views; then a deterministic Playwright regression suite backed by frozen fixtures; then containerization and CI so every push is verified and produces a publishable image; then close the security, reliability, and observability gaps from `CONCERNS.md`; and finally validate parity across a full real gameweek cycle before retiring the vanilla site. The load-bearing constraint throughout: the weekly recommendation cycle never breaks. The vanilla site stays live until the final phase.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Test Base Layer & App Skeleton** - API integration tests plus a React/Vite scaffold that proves the dev-proxy seam (completed 2026-09-01)
- [x] **Phase 2: Data Layer & Non-Pitch Pages** - Seven pages rebuilt at verified parity from the JSON export contract (completed 2026-09-02)
- [x] **Phase 3: Pitch Renderer & Squad Views** - FPL-style pitch, team page solving, and rate-my-team (completed 2026-09-03)
- [x] **Phase 4: E2E Regression Suite** - Deterministic Playwright coverage of the critical flows on frozen fixtures (completed 2026-09-04)
- [x] **Phase 5: Container Build & CI Pipeline** - Locked deps, multi-stage Docker image, GitHub Actions verification and publish (completed 2026-09-05)
- [x] **Phase 6: Security, Reliability & Observability Hardening** - Close the CONCERNS.md production-readiness gaps (completed 2026-09-07)
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

**Plans**: 6/6 plans executed (4 waves)
**Wave 1**

- [x] 01-01-PLAN.md — Repo baseline (`.gitignore` + initial source commit) and the blocking package-legitimacy gate

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — API contract tracer: `_initial_state()` seam, autouse reset fixture, `/health` + `/meta` + `/solve` with bounds and precision
- [x] 01-04-PLAN.md — React dev-seam tracer: Vite + React Router 7 + TanStack Query scaffold, `/api` and `/data` proxy, design tokens, shell chrome, Vitest harness

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — `/team` and `/rate` against a `responses`-mocked FPL API, three-mode `require_key` coverage, and the concurrency race test
- [x] 01-05-PLAN.md — All 8 routes with per-route error boundaries, the loading/error/empty/404 states, and the three UI-SPEC backstop tests

**Wave 4** *(gap closure — blocked on Wave 3 completion)*

- [x] 01-06-PLAN.md — Gap G-01-3: contain the header brand+nav at 68rem so header/main/footer content edges align, with a containment-parity regression test

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

**Plans**: 7/8 plans executed — 6/6 executed (2 waves), plus 2 gap-closure plans from UAT

**Wave 1**

- [x] 02-01-PLAN.md — Parity tracer: the flagship xP table end to end, plus the shared sort/band/format/status-flag/page-meta utilities and the full JSON-contract interface set
- [x] 02-02-PLAN.md — Package-legitimacy gate, the single four-package install, and the parity deviation ledger

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-03-PLAN.md — Chrome: class-based dark palette, three-state theme toggle, live gameweek banner, self-hosted fonts
- [x] 02-04-PLAN.md — Fixtures ticker with the FDR cell, and the price watch page with its three mode notes and rise/fall indicators
- [x] 02-05-PLAN.md — League table and leader boards, plus the accuracy scoreboard's missing-file versus server-failure distinction
- [x] 02-06-PLAN.md — Differentials with its own band scale, and the methodology page from bundled markdown

**Gap closure** *(from `02-UAT.md`, both cosmetic — 3/5 UAT tests passed)*

- [x] 02-07-PLAN.md — G-02-1: rebalance the dark neutral tokens off the accent hue and under the light theme's chroma budget (in lockstep with vanilla), restore `color-scheme` and the body paint, and gate the budget automatically *(gap-closure wave 1)*
- [x] 02-08-PLAN.md — G-02-2: stack the fixture chip's H/A venue tag beneath the opponent code, move the 56px minimum width onto the chip, restore vanilla's tight ticker-cell padding, and pin the geometry with tests *(gap-closure wave 2 — shares the `frontend/package.json` test script that 02-07 rewires)*

**UI hint**: yes

**Research flags**: enumerate every `.sort()`, `.toFixed()`, secondary sort key, and conditional class in `web/assets/app.js` as an explicit checklist *before* writing React. Decide CSR vs prerender per page explicitly (methodology, scoreboard, differentials are the SEO candidates). *Both closed in `02-RESEARCH.md`: the 41-rule Parity Rule Inventory enumerates every rule (and confirms no secondary sort key exists anywhere in vanilla); D-10 locks pure CSR for all seven pages, with prerender deferred as an SEO pass.*

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

**Plans**: 5/5 plans executed (4 waves) — 4/5 executed; 03-05 is UAT gap closure

**Wave 1**

- [x] 03-01-PLAN.md — Pitch tracer: Phase 3 type surface, pitch tokens, kit system, player card, and the model squad rendered on `/team`; plus the PITCH-01 decision doc, footer disclaimer and "My team" rename

**Wave 2** *(blocked on Wave 1)*

- [x] 03-02-PLAN.md — Three-tab shell with `?entry=`/`?tab=` URL state, the load-your-own-team flow, the chip-timing timeline, the four verbatim rate tiles, and the shared `pairMoves` port

**Wave 3** *(blocked on Wave 2; the two run in parallel — zero file overlap)*

- [x] 03-03-PLAN.md — Rate tab completion: single-pitch visual diff with the suggested swap, the best-XI section, and the multi-week plan-transfers flow
- [x] 03-04-PLAN.md — Squad tab solver: lock/exclude marks, the three bounded solver knobs, in-place pitch update with IN badges, the results bar, and reset

**Wave 4** *(UAT gap closure — blocked on Wave 3)*

- [x] 03-05-PLAN.md — Close G-03-1: center every formation row continuously so 2-card, 4-card and bench rows stop drifting half a column left; add the missing symmetry regression test and correct the UI-SPEC's defective centering mechanism

**UI hint**: yes

**Research flags**: ~~FPL shirt/badge CDN URL patterns~~ — **closed as moot at planning time.** `03-CONTEXT.md` D-01 chose self-hosted neutral generated kits over FPL CDN imagery, so no CDN URLs are needed and no devtools capture is required. The trademark posture is settled here as required, via the committed decision doc (`docs/decisions/pitch-kit-sourcing.md`) plus the sitewide footer disclaimer — not deferred to payment-gateway review.

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

**Plans**: 8/8 plans executed (6/8 executed; 2 gap-closure plans added after verification found 2 gaps — 5 waves)

**Wave 1**

- [x] 04-01-PLAN.md — Frozen v1 fixture capture (real week + trimmed upstream payloads + per-gameweek pools) and the `FPL_FIXTURE_DIR` seam in `api/main.py`, with the `dist/404.html` SPA build hook

**Wave 2** *(blocked on Wave 1)*

- [x] 04-02-PLAN.md — Playwright harness and the phase tracer: package gate, `playwright.config.ts` with the three fixture-fed servers, the pinned-clock helper, one end-to-end smoke spec, and the G-01-3 / pitch-symmetry geometry spec

**Wave 3** *(blocked on Wave 2; the four run in parallel — zero file overlap)*

- [x] 04-03-PLAN.md — Blank and double-gameweek fixture synthesis plus the fixtures ticker, price watch and four targeted variant specs
- [x] 04-04-PLAN.md — xP table and captain picks: exact cell values, both sort directions with tie and null behaviour, filters and the empty result
- [x] 04-05-PLAN.md — Team/pitch solver flow: load, lock/exclude, real ILP solve invariants, the single pinned golden, and the two-gameweek plan flow
- [x] 04-06-PLAN.md — Rate-my-team: the four tiles with their boundary and precision behaviour, and the single-pitch diff with its ghost card

**Wave 4** *(gap closure — 04-VERIFICATION.md, status gaps_found)*

- [x] 04-07-PLAN.md — CR-01: capture the production `predict.live._gw_pool` once and restore it in an explicit else-branch when `FPL_FIXTURE_DIR` is unset, with the regression assertion `tests/test_fixture_mode.py` was missing

**Wave 5** *(blocked on Wave 4 — its gate boots the `api.main` module Wave 4 edits)*

- [x] 04-08-PLAN.md — Ghost-row fix: key the rate-diff ghost card off the sell target's actual row (bench included), update the E2E and Vitest assertions to the corrected same-row behaviour, and close WINDOWS.md id=2

**Research flags**: use the Node `@playwright/test` runner, not `pytest-playwright` — the repo's `pytest.ini` disables both plugins over the `--browser` flag collision. Design the fixture strategy (E2E-01) before writing the first test. Gap `G-01-3` handoff: at a 1720px viewport, assert the header's inner content wrapper is ≤1088px wide, horizontally centered, and shares the `<main>` element's content x-range (see `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md`).

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

**Plans**: 5/5 plans executed (4 waves)

**Wave 1**

- [x] 05-01-PLAN.md — Dependency tracer: the `requirements.in`/`requirements-dev.in` split, uv-compiled hashed locks, a clean-venv `--require-hashes` install that runs the whole existing test suite green, plus the `uv`/`ruff` package-legitimacy gate and the Python lint configuration

**Wave 2** *(blocked on Wave 1; the two run in parallel — zero file overlap)*

- [x] 05-02-PLAN.md — Multi-stage `python:3.14-slim` image with the CBC runtime library, a non-root user and no model artifact, plus the smoke test that runs a real ILP solve inside the container
- [x] 05-04-PLAN.md — SEC-04 hygiene: modernize and disarm `daily.yml`/`weekly.yml` (py3.14, hashed installs, SHA pins, bot identity), delete the 140MB Chrome installer, reconcile `.gitignore`, and prove no tracked file carries a personal email or credential literal

**Wave 3** *(blocked on Wave 2 — the docker job needs the Dockerfile)*

- [x] 05-03-PLAN.md — `ci.yml`: the chained lint/typecheck → backend+frontend tests → Playwright E2E → image build + smoke + Trivy → main-only GHCR publish, with the built-bundle artifact handoff Phase 4's review flagged

**Wave 4** *(blocked on Wave 3)*

- [x] 05-05-PLAN.md — `scripts/preflight.sh` local reproduction of the CI verification chain, then the D-14 blocking human checkpoint: private repo, first push, branch protection, and the first real CI run + GHCR image

**Research flags**: ~~verify `cp314` wheel availability on PyPI for LightGBM, scikit-learn, PyArrow and PuLP~~ — **closed in `05-RESEARCH.md`.** A real `pip install --require-hashes` round trip in a clean Python 3.14.3 venv succeeded for the entire ML+API stack with zero source compilation; D-03's builder-stage fallback stays pre-authorized but is not expected to be needed. Two research findings change the plan: `understatapi` must be pinned exactly (a floating constraint drags in a browser-automation dependency chain) and `pulp` needs an upper bound below 4.0 (which removes the bundled CBC binary all three solver call sites use). Original flag text: verify `cp314` wheel availability on PyPI for LightGBM, scikit-learn, PyArrow, and PuLP before finalizing the lockfile — scikit-learn lacked 3.14 wheels as of Oct 2025. Pin from a clean pip venv, not `pip freeze` inside the conda env. Watch image size (multi-stage; ML deps can balloon past 1.5GB).

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

**Plans**: 6/7 executed, plus 1 gap-closure plan pending (5 waves)

**Wave 1**

- [x] 06-01-PLAN.md — Fail-loudly tracer: the `ops/` package (jsonio, jsonlog, payloads), `predict.live._load_live` reading and validating through it, and `/api/ready` as the operator-visible far end of a corrupt FPL payload

**Wave 2** *(blocked on Wave 1; the three run in parallel — zero file overlap)*

- [x] 06-02-PLAN.md — REL-01/REL-04 sweep: 24 remaining bare file handles across `data/`, `models/`, `predict/`, `e2e/scripts/` and `tests/`, plus the self-tested repository-wide regression gate
- [x] 06-03-PLAN.md — Cron reliability and secrets: snapshot retry/backoff with atomic writes, never-raising `ops/notify.py`, per-step accounting in `daily.sh`/`weekly.sh` with the workflows delegating to them, and the mode-600 `.env` pattern
- [x] 06-04-PLAN.md — API hardening: configured CORS origins with a wildcard treated as a boot failure, a bounded LRU/TTL solve cache keyed on a monotonic pool version, and one redacted JSON log record per request

**Wave 3** *(blocked on Wave 2)*

- [x] 06-05-PLAN.md — `scripts/verify_hardening.sh` runtime proof against a real uvicorn boot on the frozen fixture set, wired into `scripts/preflight.sh` as a new gate

**Wave 4** *(gap closure — from 06-VERIFICATION.md `status: gaps_found`)*

- [x] 06-06-PLAN.md — Close CR-01: restore the `import json` that 06-02 Task 3 removed from `e2e/scripts/capture_fixtures.py`, narrow `ruff.toml`'s blanket `data`/`e2e` exclusions so the CI lint step and preflight Gate 2/8 cover all 54 tracked Python files (10 were invisible), and add a self-tested lint-coverage gate plus a ruff-independent runtime-object gate over the capture path

**Wave 5** *(gap closure — from the re-verified 06-VERIFICATION.md `status: gaps_found`, REL-05)*

- [x] 06-07-PLAN.md — Close the REL-05 TOCTOU race: return the `pool_version` from inside `_pool()`/`_gw_pools_meta()`'s own locked block so `solve()`/`plan()` key their cache on one atomic (pool, version) pair instead of two separate lock acquisitions, and prove it with a deterministic, stub-free regression test that drives the real `_pool()`/`_refresh()` interleaving plus a syntax-tree gate that stops the two-acquisition shape returning

**User setup required**: a mode-600 `.env` (06-03) and the daily/weekly cron schedule plus a watched alert webhook (06-05) — `crontab -l` currently reports no crontab on this host.

**Research flags**: none — FastAPI CORS, pydantic validation, structured logging, and LRU/TTL caching are standard patterns. The concrete gap inventory lives in `.planning/codebase/CONCERNS.md`. The daily snapshot cron is time-critical (price history cannot be backfilled) — REL-02 changes must not interrupt it.

### Phase 7: Parity Validation & Cutover

**Goal**: The React site becomes the live site without breaking a single weekly recommendation cycle
**Depends on**: Phase 6
**Requirements**: CUT-01
**Success Criteria** (what must be TRUE):

  1. The React and vanilla sites run side by side through a complete gameweek cycle — deadline → live → finished — serving the same JSON exports
  2. Every page's output is compared against the vanilla site across that cycle, with each difference either explained as an intended improvement or fixed; no unexplained deltas remain
  3. The vanilla site is retired only after that cycle passes, and the weekly recommendations flow uninterrupted throughout

**Plans**: 3/6 plans executed (6 waves — strictly sequential; waves 3-6 are calendar-gated on the validation gameweek)

**Wave 1**

- [x] 07-01-PLAN.md — Production `FPL_FRONTEND=react` serving seam, the `dual_site.sh` two-process runner, a one-page live cross-origin parity tracer, mount-branch tests, and the react-mode container assertion in CI

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 07-02-PLAN.md — All eight page extractors, `PARITY-DEVIATIONS.md`-aware delta classification, and the `PARITY-REPORT.md` / `PARITY-CHECKLIST.md` evidence artifacts

**Wave 3** *(blocked on Wave 2; gated on the pre-deadline weekly export)*

- [x] 07-03-PLAN.md — Validation pass 1: pre-deadline eight-page comparison, defect closure by fixing forward, and the entry-6980093 same-session solver handover

**Wave 4** *(blocked on Wave 3; gated on the deadline passing)*

- [ ] 07-04-PLAN.md — Validation pass 2: mid-gameweek comparison while matches are live or settling, and defect closure

**Wave 5** *(blocked on Wave 4; gated on the gameweek finishing and the scoreboard scoring it)*

- [ ] 07-05-PLAN.md — Validation pass 3: post-finish comparison, final defect closure, and the derived cutover-readiness block

**Wave 6** *(blocked on Wave 5; human-gated)*

- [ ] 07-06-PLAN.md — Cutover: the D-15 human approval gate, flipping the serving default to React with a CI-proven vanilla rollback, closing the deviation ledger and the palette lockstep, and updating the README

**Research flags**: none — this is an execution checklist, not a research problem. Its completion is gated on real calendar time (a full gameweek), so it cannot be compressed.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Test Base Layer & App Skeleton | 6/6 | Complete    | 2026-09-01 |
| 2. Data Layer & Non-Pitch Pages | 8/8 | Complete    | 2026-09-02 |
| 3. Pitch Renderer & Squad Views | 5/5 | Complete    | 2026-09-03 |
| 4. E2E Regression Suite | 8/8 | Complete    | 2026-09-04 |
| 5. Container Build & CI Pipeline | 5/5 | Complete    | 2026-09-05 |
| 6. Security, Reliability & Observability Hardening | 7/7 | Complete    | 2026-09-07 |
| 7. Parity Validation & Cutover | 3/6 | In Progress|  |

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

### Phase 8: Self-Hosted Gameweek Data Capture

**Goal:** Remove vaastav/Fantasy-Premier-League as a single point of failure for training data. A new `data/gw_capture.py` reconstructs vaastav-schema per-GW rows (`gw{N}.csv`, `merged_gw.csv`, refreshed `players_raw.csv`/`fixtures.csv`) directly from the official FPL API into `data/raw/2026-27/`, runs from `scripts/daily.sh`, and backfills the already-finished GWs before season rollover makes them unrecoverable (element-summary only retains the current season). vaastav is demoted to past-season backfill; `build_table`/`id_map` consume the captured rows unchanged. Research: `.planning/research/DATA-SOURCE-RESILIENCE.md`.
**Requirements**: TBD
**Depends on:** Phase 7
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 8 to break down)

### Phase 9: xP Model & Optimizer Improvement Experiments

**Goal:** Raise honest walk-forward season points from the current ~2,105–2,256 core toward the realistic automated frontier (~2,300+), judged exclusively by the existing leakage-safe 6-season harness (`backtest/walk_forward.py`) — never by optimistic backtests. Candidate experiments, in recommended order: (1) benchmark our xP against public projections (theFPLkiwi/OpenFPL) on common rows to size remaining accuracy headroom; (2) captaincy/TC ceiling EV from `models/intervals.py` quantiles (attacks the measured 4.8 pts/GW captaincy gap); (3) solver-scored chip scheduler v2 judged by the isolated-chip harness; (4) Dixon-Coles/Poisson team-strength features (fills NaN-odds 2016-19 rows and horizon GWs); (5) hybrid RL-for-strategy layer (FPL-RL-style: MaskablePPO chooses chip timing and transfer count while the existing ILP keeps doing player selection) — gated on (3) first, since the RL layer must beat the solver-scored chip scheduler on the same honest harness to earn its complexity; (6) additional enrichment data sources: Understat npxG/xGChain via theFPLkiwi's ready-made ID maps, FotMob per-match defensive stats, and FBref once a Chrome-capable scrape host exists — name→FPL ID mapping is the shared prerequisite, and all enter as features only, never sub-models. Excludes everything already tested and rejected in PLAN.md/IMPROVEMENTS.md (ranking loss, CS sub-model, 3-state minutes, true multi-period MILP). Research: `.planning/research/XP-IMPROVEMENT-OPTIONS.md` (incl. the ADnocap/FPL-RL audit — its 2,918 headline is in-sample, but its RL/MILP split and FotMob source are the salvageable ideas adopted here).
**Requirements**: TBD
**Depends on:** Phase 8
**Plans:** 10/10 plans complete

Plans:
**Wave 1**

- [x] 09-01-PLAN.md — Experiment flag seam + captaincy ceiling EV tracer + measured 6-season baseline

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 09-02-PLAN.md — External-projection benchmark, shared ID crosswalk, committed theFPLkiwi snapshot (D-10)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 09-03-PLAN.md — Captaincy ceiling EV: lambda sweep, adoption run, conditional Monte-Carlo variant

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 09-04-PLAN.md — Chip scheduler v2 (solver-scored, causal) + first measured Wildcard isolated value

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 09-05-PLAN.md — Dixon-Coles team-strength features, leakage test, decision-time horizon graft

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 09-06-PLAN.md — RL stack: package-legitimacy gate, dev-only lockfile (D-09), Gymnasium environment

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 09-07-PLAN.md — RL training inside a declared time-box + the D-02 gate against chip scheduler v2

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 09-08-PLAN.md — Understat npxG/xGChain/xGBuildup enrichment as rolled features

**Wave 9** *(blocked on Wave 8 completion)*

- [x] 09-09-PLAN.md — FotMob acquisition (D-11) + FBref spike gate (D-04), closing all enrichment rows

**Wave 10** *(blocked on Wave 9 completion)*

- [x] 09-10-PLAN.md — Final combined run (D-13), D-05 verdict, product wiring, Phase F ledger close

### Phase 10: xP Experiment Follow-ups

**Goal:** Pursue Phase 9's measured leads under the same honest-harness discipline (D-05/D-07/D-08 pattern: pre-declared criteria, default-off flags, ledger verdicts). Scope = the six 2026-09-09 pending todos: (1) ep_next + availability-flag features to attack the ranking gap (our Spearman 0.383 vs ep_next's 0.579 on the EXP-1 benchmark); (2) per-position + covered-rows re-measurement of understat/fotmob accuracy; (3) manual FBref CSV snapshot committed like the kiwi data, joined via the crosswalk; (4) high-replica (≥25) capt_ceiling adoption re-run recorded as a Phase F addendum; (5) RL v2 bigger-timestep run (120-min/policy box declared 2026-09-09, training launched, artifacts in data/processed/experiments/rl_v2_policies/) with its 5-season adoption comparison; (6) RL reward-shaping notes (potential-based shaping only, if ever revisited). Adoption bar unchanged: ≥2,280 model+chips vs the 2,262 baseline. Scope extended 2026-09-10 from the research sweep (six new todos): Tier 1 — availability flags into P(play) from our own daily snapshots (optional one-time vendored 2025-26 backfill), Transfermarkt injury history (all-seasons backfillable); Tier 2 — model-class bracket (LSTM/GRU, XGBoost/CatBoost, Ridge, MLP vs LightGBM, Spearman-gated), conditional Guardian/GDELT news sentiment; Tier 3 — top-100 consensus + fplreview scoreboard benchmarks. Manual FBref snapshot deprioritized below all of these.
**Requirements**: TODO-AVAIL-FLAGS, TODO-TM-INJURY, TODO-BRACKET, TODO-NEWS, TODO-TOP100, TODO-FPLREVIEW, TODO-FBREF-MANUAL, TODO-RL-SHAPING, PHASE10-CRON, PHASE10-COLAB-SEAM, PHASE10-CRITERIA (this phase is not mapped in REQUIREMENTS.md — its spec is the eight `resolves_phase: 10` todos plus three infrastructure items; the IDs above are the traceability keys the plan set uses)
**Depends on:** Phase 9
**Plans:** 15/16 plans executed across 10 waves

Plans:
**Wave 1**

- [x] 10-01-PLAN.md — TRACER: one availability column end-to-end (capture → provider → as-of-deadline join → flag → harness) + Phase G pre-declared criteria
- [x] 10-02-PLAN.md — Tier 3: top-100 consensus + fplreview manual capture, both scored in the scoreboard
- [x] 10-03-PLAN.md — D-08: anacron-style snapshot catch-up + daily gap report

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 10-04-PLAN.md — Full OpenFPL availability encoding + D-10 safe fallback + coverage report
- [x] 10-05-PLAN.md — Transfermarkt access: figshare check + bounded probe + go/no-go

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 10-06-PLAN.md — D-05: FPL-Core-Insights vendor + verify + committed snapshot
- [x] 10-07-PLAN.md — Transfermarkt injury backfill + spell-overlap join + leakage test

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 10-08-PLAN.md — Tier-1 adoption runs (D-09 dual criterion, 6-season A/B) + D-02 trigger verdict
- [x] 10-09-PLAN.md — External-prediction ingestion seam (the Colab handoff prerequisite, D-14)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 10-10-PLAN.md — Bracket A: package gate + Ridge/XGBoost/CatBoost + D-15 cheap gate

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 10-11-PLAN.md — Bracket B: sequence builder (D-20) + D-21 leakage test + MLP at both granularities
- [x] 10-12-PLAN.md — Conditional news sentiment (D-02 trigger-routed)

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 10-13-PLAN.md — Bracket C: GRU + transformer + Colab handoff (D-13/D-14)

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 10-14-PLAN.md — Bracket verdict: gate-winner 6-season runs + D-17 ONNX export + ledger

**Wave 9** *(blocked on Wave 8 completion)*

- [x] 10-15-PLAN.md — Tail (D-04): manual FBref snapshot decision + RL reward-shaping notes

**Wave 10** *(blocked on Wave 9 completion)*

- [ ] 10-16-PLAN.md — Close-out: D-11 split-verdict combined run + D-01..D-21 audit + product-surface proof

---
*Roadmap created: 2026-08-31*
