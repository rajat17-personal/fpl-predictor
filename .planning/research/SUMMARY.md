# Project Research Summary

**Project:** FPL Predictor — Production Hardening (frontend rebuild, testing, CI/CD)
**Domain:** Fantasy Premier League prediction/optimization web product — mid-season hardening milestone
**Researched:** 2026-08-31
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a **parity rebuild + hardening milestone** for a working FPL predictor: rewrite the frontend from vanilla JS to React+Vite, build the missing API test base layer, add Playwright E2E coverage, and harden production (security, reliability, observability). The core value — trustworthy weekly ML recommendations — survives unchanged; the pipeline's JSON export contract (`web/data/*.json`) is the load-bearing invariant never bundled into builds.

**Recommended approach:** Incremental parity, not big-bang cutover. Keep the vanilla site live as a reference throughout, verify each React page against the same JSON data, and run both implementations side-by-side until a full gameweek cycle passes. This guards against silent regressions on the weekly deadline-cycle users depend on.

The stack is conservative (React 19 + Vite + TypeScript 6 + TanStack Query + Recharts + Tailwind), with careful attention to avoiding footguns (TypeScript 7.0's ESLint incompatibility, Playwright browser caching, Docker ML-dependency bloat, PuLP CBC solver availability). Architecture keeps hosting options open (FastAPI+SPA same-container now, or Cloudflare Pages+separate API later, via environment variables only).

**Key risks are silent breakage:** data-table formatting regressions that "look identical" in QA, flaky Playwright tests hitting live weekly-changing data, FastAPI tests that pass while masking concurrency bugs, Docker images that balloon to 1.5–2.5GB+, and unresolved trademark issues resurfacing at payment-gateway review. Each pitfall has clear prevention strategies but requires deliberate decisions during phase planning, not afterthought retrofits.

## Key Findings

### Recommended Stack

**Frontend:** React 19.2 + Vite 7+ (verified live, 2026-08-31). **TypeScript 6.x, NOT 7.x** (ESLint support not stable in 7.0). React Router 7.18 for 8 fixed routes. TanStack Query 5.102 for data fetching. Recharts 3.10 for charting. Tailwind CSS 4.3 with CSS-first config for pitch layout (relative container + percentage-positioned formation rows, not SVG absolute positioning).

**Testing:**
- **Playwright v1.62+ (Node runner, NOT pytest-playwright):** Repo's `pytest.ini` disables both plugins due to unrecoverable `--browser` CLI flag collision. Use `@playwright/test` Node runner — separate CLI, richer tooling (trace viewer, HTML reporter, parallel sharding), zero pytest entanglement.
- **FastAPI:** `TestClient` for sync tests (simple, works with async endpoints). `AsyncClient` + `@pytest.mark.anyio` only for concurrency-specific tests.

**Infrastructure:**
- **Docker:** Multi-stage build (builder with compilers → slim runtime). Base: `python:3.14-slim` (NOT alpine — prebuilt wheel compatibility for LightGBM/scikit-learn/pyarrow). Dependency management via `uv` (10-100x faster than pip). **Explicitly install CBC solver** (`apt-get install coinor-cbc` or `pip install pulp[cbc]`); verify at startup and in CI smoke test via `pulp.listSolvers(onlyAvailable=True)`.
- **GitHub Actions:** All third-party actions pinned to full commit SHA (not mutable `@v3` tags). Dependabot for updates. Playwright browser binaries cached by lockfile hash + Playwright version. Python deps locked via `uv.lock`.

**Data contract:** `web/data/*.json` (weekly from `predict/export.py`) is always runtime-fetched, never bundled into JS build. This decouples product from pipeline and is unchanged from vanilla site.

### Expected Features

**Table stakes (users expect):**
- Pitch view with formation layout, captain/VC badges, price+xP overlay, using FPL's official kit CDN or neutral-generated kits (trademark-safe)
- All 8 pages at parity (xP table, team, fixtures, prices, league, scoreboard, differentials, methodology)
- Sortable/filterable stat tables (no regressions on sort order, number formatting, secondary sort keys)
- FDR ticker with standard green→red colors
- Mobile-responsive pitch and tables
- Rate-my-team view (squad xP vs optimal, suggested swaps)
- Deadline countdown, gameweek meta banner

**Differentiators (competitive edge):**
- ILP-solved squad optimizer with p10/p90 prediction intervals (most competitors use heuristics)
- Public scoreboard (MAE + rank vs FPL's own ep_next) — nobody else grades themselves openly
- Ownership-aware differentials view
- Email digest as owned channel (no app-store gatekeeping)

**Defer to v2+ or out of scope:**
- Real-time in-match scoring (anti-feature; batch pipeline doesn't support without new real-time infra)
- Custom club crests / trademarked kit reproduction (legal risk)
- Social/community features (scope creep for solo dev)
- Full historical multi-season explorer in v1 (data contract exists for v2+)

### Architecture Approach

**Core invariant:** Three independent flows never cross:
1. **Pipeline (weekly):** `predict/export.py` → `web/data/*.json` (git-tracked). Frontend fetches at runtime, never imports at build time.
2. **Solver (on-demand):** Browser → `/api/solve|rate|team` → FastAPI (ILP or FPL API) → JSON. Live compute.
3. **Build (CI):** Frontend source → `npm run build` → `frontend/dist/` → Docker or Cloudflare Pages. Never touches `web/data/`.

**Key patterns:**
- **Env-gated dual serving:** `api/main.py` mounts `frontend/dist/` only when `SERVE_FRONTEND=1`, enabling both "FastAPI serves everything" (Docker demo) and "Cloudflare Pages + separate API" (future) without code branching.
- **Dev-server proxy:** `vite.config.ts` proxies `/api` and `/data` to localhost:8000, avoiding loosened CORS that only standalone hosting needs.
- **Runtime base URLs:** `lib/config.ts` exports `API_BASE` and `DATA_BASE` from env vars, defaulting to relative paths. Every fetch goes through these constants, never hardcoded URLs.
- **Presentational pitch:** CSS Grid for formation rows (responsive, accessible), SVG only for pitch markings (center circle, box lines). Pure component, no fetching or page-specific logic.
- **react-router:** Declarative route table for 8 fixed routes. No file-based routing needed at this scale.

**Build order (by dependency, not calendar):**
1. API tests (unblocks everything) + frontend scaffold (parallel) — proves dev-proxy seam end-to-end.
2. Data layer + 7 non-pitch pages — validate fetch/routing on simpler pages before pitch complexity.
3. Pitch renderer + Team page — highest-complexity UI, highest-integration-risk page last among UI work.
4. Playwright E2E + fixtures — design fixture discipline before writing first test.
5. Docker build + CI hardening — containerize after a real artifact exists; depends on all prior phases.
6. Security/reliability hardening — after core functionality works, harden non-functional requirements.
7. Parity validation + cutover — full gameweek cycle (deadline → live → finished) on React before retiring vanilla site.

### Critical Pitfalls & Prevention

**1. Big-bang React cutover breaks weekly cycle (HIGH severity):**
Risk: All 8 pages merged at once → data-shape mismatch discovered during live gameweek with no fallback.
Prevention: Keep vanilla site live during rebuild. Build page-by-page, diff rendered output against same JSON. Budget one full gameweek (7 calendar days) for side-by-side verification.

**2. Data tables regress on sort/filter/format semantics (MEDIUM severity):**
Risk: Tables "look identical" but sort order, number formatting, secondary sort keys silently differ.
Prevention: Before writing React, enumerate every `.sort()`, `.toFixed()`, conditional CSS, secondary sort key from vanilla `app.js`. Unit test formatting helpers (price, xP range, ownership %). Playwright assertions on exact cell values.

**3. Playwright E2E tests are flaky from live data (MEDIUM severity):**
Risk: Tests pass mid-week, fail on deadline (blank gameweek, price change) — with no code change. Flaky suites get disabled within weeks.
Prevention: Freeze versioned fixture snapshots (normal, blank, double gameweeks, user's own team ID 6980093). Mock/stub outbound FPL API calls. Never assert on "now" without controlling the clock.

**4. FastAPI tests hide concurrency bugs in global lock (MEDIUM severity):**
Risk: Tests pass while masking real cache-invalidation race already flagged in `CONCERNS.md`.
Prevention: Write at least one concurrency test (parallel `/solve` + pool refresh). Add state-reset fixture (autouse). Mock outbound FPL API calls.

**5. Docker image bloat from ML dependencies (MEDIUM severity):**
Risk: Single-stage build produces 1.5–2.5GB+ images, slow CI, high GHCR costs on free tier.
Prevention: Multi-stage build. Prefer prebuilt wheels; pin versions with `cp314` wheels for Python 3.14. Gate image size in CI.

**6. PuLP CBC solver missing in container (LOW-MEDIUM severity):**
Risk: `/solve` works locally but fails immediately when tested in container.
Prevention: Explicitly install CBC. Verify with `pulp.listSolvers(onlyAvailable=True)` at startup and in Docker smoke test during CI.

**7. Third-party GitHub Actions expose CI secrets (HIGH severity, supply-chain risk):**
Risk: Actions pinned to mutable tags (`@v3`) can be rewritten by compromised maintainer (real precedent: tj-actions/changed-files, March 2025, ~23K repos).
Prevention: Pin every action to full 40-character commit SHA. Use Dependabot for updates. Use scoped `GITHUB_TOKEN` with `packages: write`, not PATs.

**8. Dependency pinning breaks reproducibility (MEDIUM severity):**
Risk: `pip freeze` inside conda env may not reproduce in Docker/CI; Python 3.14 wheel availability in flux (scikit-learn lacked 3.14 wheels as of Oct 2025).
Prevention: Pin from clean pip venv (not `pip freeze` in conda). Check PyPI files tab for `cp314` wheels before finalizing `uv.lock`. Verify lockfile installs in fresh venv/Docker.

**9. Trademarked crest/kit imagery creates legal exposure (MEDIUM severity at paid launch):**
Risk: Cease-and-desist or payment-processor compliance review flags unlicensed club crests/kits.
Prevention: Use FPL's official CDN (`resources.premierleague.com`, `fantasy.premierleague.com/dist/img/shirts`) or fully neutral generated graphics (colored jersey silhouettes, no crests). Add "not affiliated with/endorsed by the Premier League" disclaimer. Treat as documented decision during Phase 3 UI design (per PROJECT.md), not afterthought.

## Implications for Roadmap

**Suggested 7-phase structure (ordered by dependency and risk):**

1. **API Test Base Layer & Frontend Scaffold** — Unblock everything. Proves dev-proxy seam end-to-end before any UI work.
2. **Data Layer & 7 Non-Pitch Pages** — Tables, xP, fixtures, prices, scoreboard, differentials, league, methodology. Validate fetch/routing on simpler pages before pitch complexity.
3. **Pitch Renderer & Team Page** — Highest UI complexity; highest integration risk. Sequence last among UI work.
4. **Playwright E2E & Fixture Strategy** — Design fixture discipline (frozen snapshots, FPL API mocking) before writing first test.
5. **Docker Build & CI Hardening** — Multi-stage Dockerfile, GitHub Actions (SHA-pinned actions, `permissions:` blocks), dependency lock, image-size gating.
6. **Security & Reliability Hardening** — CORS restriction, structured logging (JSON, correlation IDs), FPL schema validation (pydantic), graceful JSON-load failure, bounded `_solve_cache` with LRU/TTL, rate limiting (slowapi), cron alerting, pydantic-settings config validation.
7. **Parity Validation & Cutover** — Full real-world gameweek cycle (deadline → live → finished) comparing React vs vanilla side-by-side, then retire vanilla site.

**Why this order:**
- Respects dependencies (API tests unblock everything; Docker depends on all prior phases).
- Front-loads high-risk items (API tests, data flow, pitch complexity) before high-effort items (Docker, CI, extensive hardening).
- Parity validation gates cutover, ensuring weekly-cycle reliability doesn't regress.

**Research flags for phase planning:**

- **Phase 1:** Async + threading.Lock race conditions in FastAPI — if not explicitly tested before, this phase needs a spike.
- **Phase 2:** Vanilla JS table sort/filter rules — examine `web/assets/app.js` for every `.sort()`, `.toFixed()`, secondary key before writing React.
- **Phase 3:** FPL shirt/badge CDN URL patterns — open browser devtools on `fantasy.premierleague.com`'s My Team page and capture exact `<img src>` URLs before building ShirtIcon. **DO NOT guess URL patterns.**
- **Phase 5:** Python 3.14 wheel availability (LightGBM, scikit-learn, PyArrow, PuLP) — check PyPI files tab before finalizing `uv.lock`. Scikit-learn lacked 3.14 wheels as of Oct 2025; PyArrow timeline in flux.

**Phases with standard patterns (skip dedicated research phase):**
- Phase 2: React Router + TanStack Query (mature, well-documented).
- Phase 3: CSS Grid pitch layout (standard pattern).
- Phase 6: Structured logging, CORS, rate limiting (FastAPI best-practices).
- Phase 7: Parity validation (execution checklist, not research).

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| **Stack** | HIGH | React, Vite, TypeScript, TanStack Query, Recharts, Tailwind, Playwright versions verified against live npm/PyPI registries (2026-08-31). Python 3.14-slim and uv confirmed via official Docker Hub and Astral docs. One exception: FPL shirt/kit CDN URL pattern is community knowledge, not officially documented — **needs direct verification during Phase 3**. |
| **Features** | MEDIUM | Table-stakes features cross-checked against FFScout, LiveFPL, FPL Review, Fantasy Football Fix. Production-readiness checklist from 2025/2026 FastAPI best-practice sources. Exception: exact FPL JSON schema (p10/p90 nullability) assumed from existing codebase, not independently verified. |
| **Architecture** | MEDIUM-HIGH | Patterns (env-gated serving, dev proxy, runtime config, CSS Grid pitch, react-router) cross-checked against Vite/FastAPI/React official docs and 2025/2026 community sources. Project-specific decisions opinionated synthesis. No live deployment experience in this specific codebase; some integration edges may surface during Phase 5. |
| **Pitfalls** | MEDIUM | Domain patterns (React migration, Playwright, FastAPI global state, Docker, GitHub Actions) are well-established engineering knowledge. Three pitfalls LOW confidence: PuLP/CBC packaging for Python 3.14 (needs PyPI verification), Python 3.14 wheel ecosystem maturity (rapidly changing), trademarked imagery legal posture (not technical). |

**Overall:** MEDIUM-HIGH for a roadmap starting point. Stack and architecture well-validated; features and pitfalls informed by industry patterns and project's own `CONCERNS.md` audit.

**Key gaps to address during planning:**

1. **FPL shirt/badge CDN URLs (LOW confidence):** Community knowledge, not officially confirmed. Resolve during Phase 3 via browser devtools on `fantasy.premierleague.com`.
2. **Python 3.14 wheel availability (LOW confidence):** Rapidly changing; scikit-learn lacked 3.14 wheels as of Oct 2025. Re-verify during Phase 5 against current PyPI.
3. **Vanilla JS table semantics:** Assumes rules can be enumerated. During Phase 2, grep `web/assets/app.js` for every sort, format, secondary key and write as explicit checklist.
4. **Crest/kit imagery rights (unresolved):** During Phase 3 UI design (per PROJECT.md), make explicit, documented choice: FPL's official CDN or fully neutral graphics. Add non-affiliation disclaimer.
5. **CSR vs SSG per-page (unresolved):** During Phase 2, decide which pages (if any) need prerendering for SEO (methodology, scoreboard, differentials). Make explicit, not accidental.

## Sources

- `.planning/research/STACK.md` — versions verified against npm registry and PyPI, 2026-08-31
- `.planning/research/FEATURES.md` — competitor cross-check (FFScout, LiveFPL, FPL Review, Fantasy Football Fix) + production-readiness practice
- `.planning/research/ARCHITECTURE.md` — FastAPI+Vite serving patterns, GitHub Actions caching, project-specific synthesis from codebase map
- `.planning/research/PITFALLS.md` — 12 pitfalls with prevention strategies and phase mapping
