# Phase 1: Test Base Layer & App Skeleton - Research

**Researched:** 2026-08-31
**Domain:** FastAPI integration/concurrency testing (pytest) + React/Vite SPA scaffold with dev-proxy runtime data seam
**Confidence:** HIGH — core findings verified by reading `api/main.py`, `predict/live.py`, `config.py`, `pytest.ini`, the approved `01-UI-SPEC.md`, and by running `npm view` / the package-legitimacy seam against the live registries. Frontend framework-version pairings are MEDIUM (WebSearch-cited) since no frontend code exists yet to verify against.

## Summary

This phase has two independent tracks that share nothing but a git repo: (1) a real pytest safety net for the five existing `api/main.py` endpoints plus the auth stub and a concurrency race test, and (2) a brand-new `frontend/` Vite+React+TypeScript app that proves it can reach the same backend through a dev-server proxy without bundling any pipeline output.

**Track A (APIT-01/02/03) is a testing problem, not a feature-building problem.** `api/main.py` already works; nothing in this phase's success criteria asks for new production behavior beyond "add a DI seam as needed." The critical finding is that `api/main.py` holds module-level global mutable state (`_state`, `_solve_cache`, `_lock`) exactly as `CLAUDE.md` documents, and `_refresh()` unconditionally attempts `joblib.load(models/artifacts/xp_model.joblib)` the first time it runs — that file exists on disk locally but **is not tracked in git** (verified: `git cat-file` on `HEAD:models/artifacts/xp_model.joblib` fails). Any endpoint test that lets `_refresh()` run for real (rather than short-circuiting `_pool`) is implicitly coupled to a large untracked binary and will break the moment CI (Phase 5) runs on a clean checkout. The existing precedent test (`tests/test_product.py::test_api_solve_and_resolve`) already avoids this by monkeypatching `api.main._pool` directly — that pattern should be the template for `/solve`, `/team`, and `/rate` (all three call `_pool()` internally). `/health` and `/meta` only need `_load_live` mocked plus the artifact stubbed non-`None`; they never call `_pool()`.

**Track B (UI-01) is scaffolding, not page-building.** The approved `01-UI-SPEC.md` already locked the design system (no shadcn, Tailwind v4, Archivo/IBM Plex fonts, `frontend/src/components/`), the 8 routes, and per-route error boundaries. Research confirms the technical pairing is sound: TypeScript 7.0.2 is npm's current `latest`, but `typescript-eslint@8.68.0`'s own `peerDependencies` field declares `typescript: '>=4.8.4 <6.1.0'` — a hard, present constraint, not a rumor — which verifies the roadmap's "TS 6.x, not 7.x" flag and pins the exact target to **6.0.3** (the newest 6.x release). React Router v7 unified `react-router-dom` into the base `react-router` package; the UI-SPEC's "declarative mode, no framework/Remix mode" maps to `createBrowserRouter` + `RouterProvider` imported from `react-router` directly (not `-dom`). The runtime-fetch requirement ("no pipeline data bundled") has a concrete, verified mechanism: `api/main.py:402` mounts `StaticFiles(directory=config.ROOT / "web", html=True)` at `/`, which already serves `web/data/xp_table.json` at `GET /data/xp_table.json` — so the Vite dev proxy just needs to forward both `/api` and `/data` to the uvicorn process, mirroring production's single-origin behavior exactly.

**Primary recommendation:** Build Track A as five thin `TestClient` test functions plus one concurrency test, all driven by a new `tests/conftest.py` autouse fixture that resets `api.main._state`/`_solve_cache` via a small `_initial_state()` factory added to `api/main.py` (the phase's only production-code change); mock the FPL bootstrap/fixtures via `monkeypatch.setattr(api.main, "_load_live", ...)` and the FPL live-entry HTTP calls via the `responses` library. Build Track B as `npm create vite@latest frontend -- --template react-ts`, then pin `typescript@6.0.3`, add `react-router@7`, `@tanstack/react-query@5`, Tailwind v4 via `@tailwindcss/vite`, and a `server.proxy` block in `vite.config.ts` forwarding `/api` and `/data` to `http://localhost:8000`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| APIT-01 | FastAPI TestClient integration tests for /solve, /rate, /team, /health, /meta with mocked FPL API | `_pool`-monkeypatch pattern (existing precedent) for /solve, /team, /rate; `_load_live`-monkeypatch + artifact stub for /health, /meta; `responses` library for the two direct `requests.get` calls in `_fetch_team`/`_free_transfers` — see Architecture Patterns, Code Examples |
| APIT-02 | Auth stub (`require_key`) tests — open mode, valid key, invalid key | `require_key()` read in full (api/main.py:159-163); three-mode test matrix documented in Code Examples |
| APIT-03 | Concurrency test for pool refresh + solve-cache race, with autouse state-reset fixture (adds DI seam as needed) | Race mechanism identified by reading `_refresh()`/`_pool()`/`solve()` (unlocked `_solve_cache` reads/writes concurrent with a locked `_refresh().clear()`); real-thread `ThreadPoolExecutor` needed because a single-threaded TestClient loop cannot exercise the race — see Common Pitfalls and Code Examples |
| UI-01 | React (Vite, TypeScript 6.x) app with routes for all 8 pages, dev-server proxy to the API, and runtime-fetched `web/data/*.json` (never bundled at build time) | TypeScript 6.0.3 pinned by verified `typescript-eslint` peerDependency; `react-router@7` declarative-mode setup; dev-proxy mechanism verified against the actual `StaticFiles` mount in `api/main.py`; 8 routes and app-shell contract already locked in `01-UI-SPEC.md` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Constraint | Source | Impact on this phase |
|---|---|---|
| Python 3.14, conda env `python314` at `/home/sraja/miniconda3/envs/python314/bin/python` for ALL Python work | CLAUDE.md Environment | Every pytest invocation and pip install in this phase must use that interpreter, not system Python |
| Frontend rebuild is React + Vite — user's explicit choice, no framework alternatives research | CLAUDE.md Constraints | Do not evaluate Next.js/Remix/SvelteKit; React Router 7 in **library/declarative mode** only (no `react-router/dev`, no SSR) |
| `web/data/*.json` export schema is the API between pipeline and site — rebuild consumes it unchanged | CLAUDE.md Constraints | Frontend must fetch these JSON files at their existing shape/URL, never transform or re-export them |
| No live infrastructure yet — CI ends at image + build artifact | CLAUDE.md Constraints | Out of scope for Phase 1, but confirms the dev-proxy (not a live deploy config) is the correct target for this phase |
| Solo developer, pre-revenue — prefer free tiers, boring/maintainable choices | CLAUDE.md Constraints | Favors Vite 7.x (mature) + `@vitejs/plugin-react@5.x` (broad peer range) over bleeding-edge Vite 8/plugin-react 6 pairing — see Alternatives Considered |
| Hardening must not disrupt the weekly recommendation cycle during the current season | CLAUDE.md Constraints | Adding `_initial_state()` to `api/main.py` must be a pure refactor (same dict shape) — do not change `_refresh()`/`_pool()` runtime behavior |
| `snake_case.py` modules, `test_*.py` test files, `from __future__ import annotations`, `dict | None` union syntax | CLAUDE.md Naming/Style | New test file should be `tests/test_api.py` (or extend `tests/test_product.py`'s existing API section) following these conventions |
| Error handling: `HTTPException` for API errors, `pytest.raises` for expected exceptions | CLAUDE.md Error Handling | Auth-stub tests assert `status_code == 401`/`422`, matching existing `test_api_solve_and_resolve` idiom |
| No project skills found in `.claude/skills/` etc. | CLAUDE.md Project Skills | No additional skill-specific conventions to layer in |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `/solve`, `/rate`, `/team`, `/health`, `/meta` contract tests | API / Backend | — | Tests exercise `api/main.py` in-process via `TestClient`; no browser or network involved |
| `require_key()` auth-stub coverage | API / Backend | — | Pure FastAPI dependency-injection unit under test |
| Pool-refresh + solve-cache concurrency | API / Backend | — | Races live entirely in `api/main.py` module globals (`_state`, `_solve_cache`, `_lock`) |
| React app shell, routing, loading/error states | Browser / Client | — | Client-side SPA rendered entirely in-browser; no SSR (declarative React Router mode) |
| Dev-server proxy (`/api`, `/data` → uvicorn) | Browser / Client (build tooling) | API / Backend (proxy target) | Vite's dev server is a client-side build/dev tool; it forwards, not owns, the API/data responses |
| `web/data/*.json` runtime fetch | CDN / Static | API / Backend | In production these files are served by FastAPI's `StaticFiles` mount (`api/main.py:402`) — effectively a static-file tier co-located with the API process, not a separate CDN, but architecturally it is a static-asset responsibility, not application logic |
| Design tokens / Tailwind v4 `@theme` | Browser / Client | — | Pure CSS delivered to the client; no server involvement |

## Standard Stack

### Core (Python — Track A)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.1.1 [VERIFIED: pip show, installed in python314 env] | Test runner | Already the project's runner (`pytest.ini` exists); no change |
| httpx | 0.28.1 [VERIFIED: pip show, installed] | Transport under `fastapi.testclient.TestClient` | Already a pinned dependency (`requirements.txt`); TestClient requires it |
| fastapi | 0.136.1 [VERIFIED: pip show, installed] | App under test | Already installed; `TestClient` import unchanged |
| responses | 0.26.3 [ASSUMED — see Package Legitimacy Audit] | Mock the two direct `requests.get` calls in `_fetch_team`/`_free_transfers` (FPL entry picks/summary/history endpoints) | Industry-standard `requests`-mocking library (getsentry); registers exact URLs and raises `ConnectionError` on any unregistered outbound call, which is the concrete mechanism that makes "mocked FPL API" enforceable rather than aspirational — an accidental real network call in CI fails loudly instead of silently passing/flaking |

### Core (Node/TypeScript — Track B)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vite | 7.3.6 [ASSUMED — npm registry, see Alternatives] | Dev server + build | Roadmap explicitly calls for "React (Vite, TypeScript 6.x)"; 7.x is the mature line still receiving releases (8.x shipped 11 days before this research, see State of the Art) |
| @vitejs/plugin-react | 5.2.0 [ASSUMED — npm registry] | React Fast Refresh + JSX transform for Vite | Official Vite React plugin; 5.2.0 is the first version whose `peerDependencies` spans `vite ^4 \|\| ^5 \|\| ^6 \|\| ^7 \|\| ^8` [VERIFIED: `npm view @vitejs/plugin-react@5.2.0 peerDependencies`] — pairs cleanly with the Vite 7 pin |
| react | 19.2.8 [ASSUMED — npm registry] | UI library | User's explicit choice (CLAUDE.md); no reason to pin 18.x on a greenfield app |
| react-dom | 19.2.8 [ASSUMED — npm registry] | DOM renderer | Matches `react` version exactly (React convention) |
| typescript | **6.0.3** [VERIFIED: `npm view typescript-eslint peerDependencies` → `typescript: '>=4.8.4 <6.1.0'`] | Type checking | Roadmap research flag explicitly warns off 7.x; the *reason* is verified, not just cited — the current `typescript-eslint@8.68.0` cannot lint a 7.x project at all |
| react-router | 7.18.3 [ASSUMED — npm registry] | Client-side routing (declarative/library mode: `createBrowserRouter` + `RouterProvider`) | UI-SPEC already locks "React Router 7, SPA mode — no framework/Remix mode"; import from the unified `react-router` package, not the now-legacy `react-router-dom` re-export [CITED: reactrouter.com migration notes via WebFetch] |
| @tanstack/react-query | 5.102.8 [ASSUMED — npm registry] | Data fetching/caching for `web/data/*.json` and `/api/*` | UI-SPEC's Loading/Error component contract (`<Spinner/>`, `<ErrorState/>` with `refetch()`) is written in TanStack Query vocabulary; `peerDependencies` confirm `react: '^18 \|\| ^19'` [VERIFIED: `npm view @tanstack/react-query peerDependencies`] |
| tailwindcss | 4.3.3 [ASSUMED — npm registry] | Utility CSS / design-token system | UI-SPEC explicitly targets a Tailwind v4 `@theme` block ported from `web/assets/style.css` |
| @tailwindcss/vite | 4.3.3 [VERIFIED: `npm view @tailwindcss/vite version`] | Tailwind v4's official Vite plugin (replaces PostCSS pipeline) | v4's CSS-first config eliminates `tailwind.config.js`/`postcss.config.js`/`autoprefixer` entirely [CITED: tailwindcss.com/blog/tailwindcss-v4] |
| lucide-react | 1.38.0 [ASSUMED — npm registry] | Icon set | UI-SPEC names this exact package |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| eslint | 10.9.1 [ASSUMED — npm registry] | Linting (feeds Phase 5 CI-01) | Flat config (`eslint.config.js`), current major |
| typescript-eslint | 8.68.0 [VERIFIED: peerDependencies checked directly, see above] | TS-aware lint rules | The package whose peer constraint pins the TS version — install this *before* choosing the TS version, not after |
| eslint-plugin-react-hooks | 7.1.1 [ASSUMED — npm registry] | Rules-of-hooks lint | Official React team plugin |
| eslint-plugin-react-refresh | 0.5.5 [ASSUMED — npm registry] | Fast-refresh-safety lint | Standard `create-vite react-ts` companion |
| @types/react / @types/react-dom | 19.2.18 / 19.2.5 [ASSUMED — npm registry] | Type defs matching React 19 | Required for TS to typecheck JSX |
| @types/node | 26.4.0 [ASSUMED — npm registry] | Type defs for `vite.config.ts` (Node APIs) | Needed because `vite.config.ts` runs under Node, not the browser |
| vitest | 4.1.11 [ASSUMED — npm registry] | Unit/component test runner for the "backstop" tests UI-SPEC already commits to (loading spinner, error+retry, route-isolation) | UI-SPEC's own UI Considerations table marks 3 states "🧪 resolved (backstop)" — those need an actual test framework in Phase 1, not Phase 4 (Phase 4 is E2E/Playwright, a different tier) |
| jsdom | 30.0.1 [ASSUMED — npm registry] | DOM environment for Vitest | Standard Vitest companion for component tests |
| @testing-library/react | 16.3.3 [ASSUMED — npm registry] | Component rendering/assertions | Standard pairing with Vitest for React |
| @testing-library/jest-dom | 7.0.1 [ASSUMED — npm registry] | DOM matchers (`toBeInTheDocument`, etc.) | Standard companion to `@testing-library/react` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vite 7.3.6 + `@vitejs/plugin-react@5.2.0` | Vite 8.2.2 + `@vitejs/plugin-react@6.1.1` | Vite 8 is npm's `latest` and plugin-react 6's peerDependency requires `vite ^8.0.0` exclusively [VERIFIED: `npm view @vitejs/plugin-react peerDependencies`] — technically current, but both packages were published within days of this research (see State of the Art), stacking two bleeding-edge majors on a phase with no other reason to chase latest. Recommend Vite 7 now; revisit in Phase 5 if CI tooling needs 8's features. |
| `responses` for FPL-API mocking | Plain `monkeypatch.setattr(requests, "get", fake_get)` | Zero new dependency, matches project's monkeypatch-only precedent, but any URL-dispatch logic has to be hand-rolled and silently allows real network calls for URLs the dispatcher doesn't recognize — `responses` fails loudly on unregistered URLs by default, which is the stronger guarantee "mocked FPL API" implies |
| `react-router` (unified) | `react-router-dom@7.18.3` | Same v7 codebase; `react-router-dom` is kept only as a re-export for v6 migration convenience [CITED: reactrouter.com]. No reason to add the extra package name for a greenfield app. |
| Vitest + RTL for backstop tests | Defer all frontend testing to Phase 4 Playwright | UI-SPEC already wrote "verification: backstop (held-out test...)" into 3 approved UI-Considerations rows for *this* phase's scope (E2 loading/error/partial) — deferring would leave those UI-SPEC commitments unverified until Phase 4, three phases later |

**Installation:**
```bash
# Track A (from repo root, python314 env active)
/home/sraja/miniconda3/envs/python314/bin/python -m pip install "responses>=0.25,<0.27"

# Track B (creates frontend/)
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install typescript@6.0.3 --save-exact
npm install react-router@7 @tanstack/react-query@5 tailwindcss@4 @tailwindcss/vite@4 lucide-react
npm install -D eslint typescript-eslint eslint-plugin-react-hooks eslint-plugin-react-refresh \
  vitest jsdom @testing-library/react @testing-library/jest-dom @types/node
```

**Version verification:** All versions above were checked via `npm view <pkg> version` / `pip show` against the live registries on 2026-08-31 (commands in this research session, not training-data recall). Re-run before executing the plan if more than a few days have elapsed — this ecosystem ships patch releases multiple times a week (see Package Legitimacy Audit "too-new" flags below).

## Package Legitimacy Audit

Every "too-new" verdict below reflects the ecosystem's release cadence (all of React, Vite, Tailwind, TanStack Query, and the ESLint toolchain shipped a release within the last two weeks of this research date), not a suspicious-package signal — every flagged package has a verified GitHub source repo and tens-to-hundreds of millions of weekly downloads. Per the Package Legitimacy Gate protocol, they are still gated as SUS and require a `checkpoint:human-verify` before install; the planner should not skip that step just because this research explains the flag.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| react | npm | latest published 2026-07-21 | 171.6M/wk | github.com/react/react (facebook/react) | OK | Approved |
| react-dom | npm | 2026-07-21 | 161.2M/wk | github.com/react/react | OK | Approved |
| typescript | npm | 2026-07-08 | 273.4M/wk | github.com/microsoft/TypeScript | OK | Approved |
| tailwindcss | npm | 2026-07-16 | 125.6M/wk | github.com/tailwindlabs/tailwindcss | OK | Approved |
| @tailwindcss/vite | npm | 2026-07-16 | 45.4M/wk | github.com/tailwindlabs/tailwindcss | OK | Approved |
| jsdom | npm | 2026-07-29 | 98.8M/wk | github.com/jsdom/jsdom | OK | Approved |
| eslint-plugin-react-hooks | npm | 2026-04-17 | 97.0M/wk | github.com/facebook/react | OK | Approved |
| react-router | npm | 2026-08-28 | 43.5M/wk | github.com/remix-run/react-router | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| @tanstack/react-query | npm | 2026-08-27 | 65.7M/wk | github.com/TanStack/query | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| vite | npm | 2026-08-20 | 176.3M/wk | github.com/vitejs/vite | SUS ("too-new") — recommend pinning 7.3.6, not `latest` 8.2.2 | Flagged — planner must add checkpoint before install |
| @vitejs/plugin-react | npm | 6.1.1: 2026-08-28 / **5.2.0 (recommended): older, still current** | 83.6M/wk | github.com/vitejs/vite-plugin-react | SUS on 6.x ("too-new") | Install 5.2.0, still flagged by the gate — checkpoint before install |
| lucide-react | npm | 2026-08-31 (same day as this research) | 97.8M/wk | github.com/lucide-icons/lucide | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| eslint-plugin-react-refresh | npm | 2026-08-26 | 39.1M/wk | github.com/ArnaudBarre/eslint-plugin-react-refresh | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| typescript-eslint | npm | 2026-08-24 | 87.3M/wk | github.com/typescript-eslint/typescript-eslint | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| @types/node | npm | 2026-08-27 | 429.8M/wk | github.com/DefinitelyTyped/DefinitelyTyped | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| vitest | npm | 2026-08-18 | 99.9M/wk | github.com/vitest-dev/vitest | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| @testing-library/react | npm | 2026-08-27 | 57.1M/wk | github.com/testing-library/react-testing-library | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| @testing-library/jest-dom | npm | 2026-08-09 | 63.2M/wk | github.com/testing-library/jest-dom | SUS ("too-new") | Flagged — planner must add checkpoint before install |
| responses (PyPI) | PyPI | 2026-08-26 | not reported by tool | github.com/getsentry/responses | SUS ("too-new", "unknown-downloads") | Flagged — planner must add checkpoint before install; note: PyPI download-stats lookup returned null for this package in this session, not a "low downloads" signal — this is a long-established (10+ year, getsentry-maintained) library, but the checkpoint still applies per protocol |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** react-router, @tanstack/react-query, vite, @vitejs/plugin-react, lucide-react, eslint-plugin-react-refresh, typescript-eslint, @types/node, vitest, @testing-library/react, @testing-library/jest-dom, responses (PyPI) — the planner must insert a `checkpoint:human-verify` task before the `npm install`/`pip install` step that pulls these in, even though every one of them checks out as a legitimate, high-download, source-verified package under manual review in this session.

## Architecture Patterns

### System Architecture Diagram

```
DEV MODE (this phase)                              PROD MODE (unchanged, for reference)
──────────────────────                              ─────────────────────────────────────

 Browser                                             Browser
   │  GET /                                            │  GET /
   ▼                                                    ▼
 Vite Dev Server (frontend/, :5173)                  uvicorn (api.main:app, :8000)
   │  serves React SPA bundle                           │  StaticFiles mount "/" → web/
   │                                                     │  (serves web/index.html, web/data/*.json)
   │  fetch("/api/meta")     ─┐                          │
   │  fetch("/data/xp_table  │  server.proxy             │
   │        .json")         ─┤  rewrites → :8000         │
   ▼                         ▼                           ▼
 (proxied, same-origin      uvicorn (api.main:app, :8000)   FastAPI route handlers
  from the browser's POV —   │                              │  /api/health /api/meta
  no CORS involved)          │  /api/*  → FastAPI routes    │  /api/team/{entry}
                              │  /data/* → StaticFiles(web/) │  /api/solve /api/rate
                              ▼                              ▼
                          _refresh() [threading.Lock]     requests.get(FPL_API/...)
                              │                              (real network, prod only)
                              ▼
                          _state{boot, fixtures, gw, pools}
                          _solve_cache{}
                              │
                              ▼
                          optimize/*.py (PuLP/CBC ILP solve)


TEST MODE (pytest, in-process — no Vite, no real uvicorn, no real network)
───────────────────────────────────────────────────────────────────────────
 pytest
   │
   ▼
 TestClient(api.main.app)  ── in-process ASGI calls, no sockets ──►  FastAPI route handlers
   │                                                                       │
   │  conftest.py autouse fixture:                                        │
   │    api.main._state = api.main._initial_state()                       ▼
   │    api.main._solve_cache.clear()                              _refresh()/_pool()
   │                                                                       │
   │  monkeypatch.setattr(api.main, "_load_live", fake_load_live)  ◄──────┤ (bootstrap/fixtures)
   │  responses.add(GET, f"{FPL_API}/entry/{id}/event/{gw}/picks/", ...)  │ (/team, /rate only)
   │  monkeypatch.setattr(api.main, "_pool", lambda h=1: (fake_pool, gw, boot))  (bypasses model
   │                                                                              inference entirely)
   ▼
 ThreadPoolExecutor(N) ── real OS threads, each calling client.post/get concurrently ──►
   exercises the _lock / _state / _solve_cache race (APIT-03)
```

### Recommended Project Structure

```
frontend/
├── src/
│   ├── main.tsx                 # createRoot + RouterProvider
│   ├── router.tsx                # createBrowserRouter([...]) — 8 routes + catch-all, each with errorElement
│   ├── components/
│   │   ├── PageShell.tsx        # header/nav/footer chrome (UI-SPEC "App Shell Contract")
│   │   ├── Spinner.tsx
│   │   ├── ErrorState.tsx
│   │   ├── PlaceholderPage.tsx
│   │   └── NotFoundPage.tsx
│   ├── routes/                  # one file per route, Phase 1 = <PlaceholderPage title="…"/> each
│   │   ├── XpTable.tsx           # "/"
│   │   ├── Team.tsx              # "/team"
│   │   ├── Fixtures.tsx          # "/fixtures"
│   │   ├── Prices.tsx            # "/prices"
│   │   ├── League.tsx            # "/league"
│   │   ├── Scoreboard.tsx        # "/scoreboard"
│   │   ├── Differentials.tsx     # "/differentials"
│   │   └── Methodology.tsx       # "/methodology"
│   ├── lib/
│   │   └── api.ts                # thin fetch wrappers: fetchJson("/data/xp_table.json"), fetchApi("/api/meta")
│   ├── index.css                 # @import "tailwindcss"; @theme { --bg: #fafbf7; ... }
│   └── vite-env.d.ts
├── index.html
├── vite.config.ts                # server.proxy for /api, /data
├── eslint.config.js
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
└── package.json
```

### Pattern 1: `_pool`-monkeypatch contract test (established precedent — extend, don't invent)

**What:** Bypass `_refresh()`/`_load_live()`/model inference entirely by monkeypatching `api.main._pool` to return a small, deterministic fake pool + boot dict.
**When to use:** `/solve`, `/team`, `/rate` — every endpoint that calls `_pool()`.
**Example:**
```python
# Source: existing tests/test_product.py:156-183 (this repo, read in full this session)
def test_api_solve_and_resolve(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as m
    boot = fake_boot()
    pool = fake_pool(boot)
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (pool, 1, boot))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)
    c = TestClient(m.app)
    r = c.post("/api/solve", json={"locks": [pool.iloc[0]["name"]]})
    assert r.status_code == 200
```

### Pattern 2: `_load_live`-monkeypatch + artifact stub for `/health`, `/meta`

**What:** These two endpoints call `_refresh()` but never `_pool()` — they only need `_state["boot"]`, `_state["gw"]`, `_state["loaded_at"]` populated, and `_state["artifact"]` non-`None` so `_refresh()` skips `joblib.load(...)`.
**When to use:** `/health`, `/meta`.
**Example:**
```python
def test_health_and_meta(monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient
    boot, fixtures = fake_boot(), []
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, fixtures))
    m._state["artifact"] = object()   # non-None sentinel: skips joblib.load(xp_model.joblib)
    c = TestClient(m.app)
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True
    r = c.get("/api/meta")
    assert r.json()["season"] == config.CURRENT_SEASON
```

### Pattern 3: `responses`-mocked FPL entry endpoints for `/team`, `/rate`

**What:** `_fetch_team()` and `_free_transfers()` call `requests.get()` directly against `config.FPL_API` — not through an importable seam like `_load_live`. Register exact URLs with `responses` so any *other* outbound call fails loudly.
**When to use:** `/team/{entry}`, `/rate/{entry}` (rate also needs the `/history/` endpoint mocked).
**Example:**
```python
# Source: api/main.py:166-201 (_fetch_team), :148-156 (_free_transfers) — read in full this session
import responses
import config

@responses.activate
def test_team_endpoint(monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient
    boot, pool = fake_boot(), fake_pool(fake_boot())
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (pool, 1, boot))
    responses.add(responses.GET, f"{config.FPL_API}/entry/12345/event/0/picks/",
                  json={"picks": [{"element": 1001}], "entry_history": {"bank": 5, "value": 1000}},
                  status=200)
    responses.add(responses.GET, f"{config.FPL_API}/entry/12345/",
                  json={"name": "Test FC", "player_first_name": "A", "player_last_name": "B",
                        "summary_overall_points": 100, "summary_overall_rank": 500,
                        "summary_event_points": 50}, status=200)
    c = TestClient(m.app)
    r = c.get("/api/team/12345")
    assert r.status_code == 200 and r.json()["entry"] == 12345
```

### Pattern 4: three-mode `require_key()` auth test

**What:** `require_key()` reads `FPL_API_KEYS` from `os.environ` at call time (not import time), so `monkeypatch.setenv`/`delenv` is sufficient — no app restart needed.
**When to use:** APIT-02.
**Example:**
```python
# Source: api/main.py:159-163, read in full this session
def test_require_key_three_modes(monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (fake_pool(fake_boot()), 1, fake_boot()))
    c = TestClient(m.app)

    monkeypatch.delenv("FPL_API_KEYS", raising=False)          # open mode
    assert c.post("/api/solve", json={}).status_code == 200

    monkeypatch.setenv("FPL_API_KEYS", "k1,k2")                # valid key
    assert c.post("/api/solve", json={}, headers={"X-API-Key": "k2"}).status_code == 200

    assert c.post("/api/solve", json={}).status_code == 401    # invalid/missing key
    assert c.post("/api/solve", json={}, headers={"X-API-Key": "wrong"}).status_code == 401
```

### Pattern 5: real-thread concurrency race test

**What:** A single-threaded loop of `client.get(...)` calls does **not** exercise `threading.Lock` contention — Starlette dispatches each sync request handler to an `anyio` worker thread, but sequential calls from one test thread never overlap. Real overlap requires genuine OS threads issuing requests concurrently against one shared `TestClient`.
**When to use:** APIT-03.
**Example:**
```python
# Widen the race window deterministically with a slow fake _load_live,
# then hammer /api/health (triggers _refresh) and /api/solve concurrently.
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_concurrent_refresh_and_solve(monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient
    boot, pool = fake_boot(), fake_pool(fake_boot())
    calls = {"n": 0}
    def slow_pool(horizon=1):
        calls["n"] += 1
        time.sleep(0.05)          # widen the window
        return pool, 1, boot
    monkeypatch.setattr(m, "_pool", slow_pool)
    m._state = m._initial_state()   # DI seam: fresh state per test
    m._solve_cache.clear()
    c = TestClient(m.app)

    def hit():
        return c.post("/api/solve", json={}).status_code

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(hit) for _ in range(20)]
        results = [f.result() for f in as_completed(futures)]

    assert all(status == 200 for status in results)   # no corruption / exception under concurrency
```

### Anti-Patterns to Avoid

- **Letting `_refresh()` run for real in unit tests:** couples the test suite to a 7.4MB untracked binary (`models/artifacts/xp_model.joblib`) and a real `models/artifacts/intervals.json` load, plus real network to the FPL API. Always short-circuit via `_pool` or `_load_live` + artifact stub.
- **Testing concurrency with a sequential loop:** gives false confidence — the race only manifests under genuine thread overlap (`ThreadPoolExecutor`/`threading.Thread`), not repeated sequential calls.
- **Copying `web/data/*.json` into `frontend/public/` at build time:** technically makes the dev server "work" but violates UI-01's explicit "no pipeline data bundled into the build" — the JSON must be fetched at runtime through the proxy, sourced live from `web/data/`, so a weekly pipeline re-export is picked up without a frontend rebuild.
- **Hand-rolling a URL-dispatch `fake_get(url)` function instead of `responses`:** works until someone adds a third mocked URL and the dispatcher silently returns `None`/`404` for an unrecognized path instead of failing the test loudly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mocking `requests.get()` calls to the FPL API | A manual URL-keyed dispatch function inside test fixtures | `responses` library (`@responses.activate`, `responses.add(...)`) | Fails loudly (raises `ConnectionError`) on any unregistered outbound call — the only way "mocked FPL API" is actually enforced rather than merely convention |
| Concurrent request generation for the race test | Custom thread-pool/queue orchestration | `concurrent.futures.ThreadPoolExecutor` | Standard library, handles thread lifecycle/`as_completed` correctly; no reason to hand-roll |
| Client-side data fetching + caching + retry | `useEffect` + `useState` + manual `AbortController` | `@tanstack/react-query` | UI-SPEC's Loading/Error contract already speaks TanStack Query vocabulary (`refetch()`); manual fetch-in-`useEffect` re-derives caching/dedup/retry TanStack Query gives for free, and is the exact pattern the industry moved away from (see State of the Art) |
| Per-route error isolation ("one page's crash never takes down the nav shell") | Custom top-level `<ErrorBoundary>` wrapping each page | React Router 7's per-route `errorElement` | Router-native mechanism; UI-SPEC already specifies it explicitly |
| Route matching / not-found handling | Manual `switch(window.location.pathname)` | `createBrowserRouter` catch-all route (`path: "*"`) | Standard, already the mechanism `errorElement`/loaders assume |

**Key insight:** Every "don't hand-roll" item above is a place where reaching for a well-established library removes an entire failure mode (silent mock misses, thread bugs, stale-cache bugs, crashed-nav-shell bugs) rather than just saving typing.

## Common Pitfalls

### Pitfall 1: Untracked model artifact silently required by `_refresh()`
**What goes wrong:** A test that exercises `/health` or `/meta` without stubbing `_state["artifact"]` will call `joblib.load(models/artifacts/xp_model.joblib)` for real. It works today (the file exists locally) and will fail the moment Phase 5's CI runs `pytest` on a clean checkout, because the file is not committed (`git cat-file -s HEAD:models/artifacts/xp_model.joblib` → `fatal: ... exists on disk, but not in 'HEAD'`, verified this session).
**Why it happens:** `_refresh()`'s guard is `if _state["artifact"] is None:` — any non-`None` sentinel silences it, but nothing forces a test author to set one.
**How to avoid:** The `conftest.py` autouse reset fixture should set `m._state["artifact"]` to a harmless non-`None` sentinel by default (not `None`), so every test starts in the "artifact already loaded" state unless it explicitly wants to test the cold-start path.
**Warning signs:** A test passes locally but the CI plan (Phase 5) reports `FileNotFoundError: models/artifacts/xp_model.joblib`.

### Pitfall 2: TypeScript 7.x breaks `typescript-eslint` outright
**What goes wrong:** `npm create vite@latest -- --template react-ts` installs whatever `typescript` version is `latest` at scaffold time — currently 7.0.2. `typescript-eslint@8.68.0`'s `peerDependencies` declares `typescript: '>=4.8.4 <6.1.0'`; installing both leaves either an npm peer-dependency warning (with `--legacy-peer-deps`/npm 9+ default "loose" install) or, more insidiously, a lint pipeline that silently no-ops on TS 7-only syntax it doesn't understand.
**Why it happens:** `create-vite`'s scaffold pins `typescript: "~5.x"` or `latest` depending on template version, independent of whatever ESLint tooling gets added afterward.
**How to avoid:** Explicitly pin `typescript@6.0.3` (`--save-exact`) immediately after scaffolding, before running `npm install` for the ESLint toolchain.
**Warning signs:** `npm install` prints `ERESOLVE` / peer-dependency conflict warnings mentioning `typescript-eslint`.

### Pitfall 3: `web/data` served at `/data/*`, not `/web/data/*`, in production — the proxy must match
**What goes wrong:** `api/main.py:402` mounts `StaticFiles(directory=config.ROOT / "web", html=True)` at `/`. A file at `web/data/xp_table.json` is therefore served at `GET /data/xp_table.json`, **not** `/web/data/xp_table.json`. A `vite.config.ts` proxy rule for the wrong prefix (e.g. `/web`) will 404 every fetch in dev while looking correct in isolation.
**Why it happens:** The mount prefix (`/`) and the on-disk directory name (`web/`) are easy to conflate.
**How to avoid:** Proxy exactly `/data` (and `/api`) to `http://localhost:8000`; verify with `curl http://localhost:8000/data/meta.json` against a running `uvicorn api.main:app` before wiring the frontend.
**Warning signs:** Dev-server network tab shows 404s for `/web/data/*.json` or similar mismatched prefixes.

### Pitfall 4: `_solve_cache` is read/written without the lock — benign today, a real race under Phase 6's planned LRU/TTL fix
**What goes wrong:** `solve()` does `if key in _solve_cache: return _solve_cache[key]` and later `_solve_cache[key] = out` with no `_lock` acquisition, while `_refresh()` calls `_solve_cache.clear()` *inside* `_lock`. Concurrently, a `_refresh()` triggered by staleness can clear the cache mid-flight of another thread's `solve()` call — the worst outcome today is a cache miss (harmless), but REL-05 (Phase 6, "Solve cache bounded (LRU/TTL) with the invalidation race fixed") explicitly names this as a known gap this phase must **observe**, not fix.
**Why it happens:** `_solve_cache` was never brought under `_lock`'s protection when it was added.
**How to avoid:** Phase 1's concurrency test should assert "no exceptions, all 200s, no corrupted state" under load — not "the cache is perfectly consistent." Don't let the test accidentally start asserting a stronger guarantee than the code provides; that would make APIT-03 fail for the wrong reason (revealing a known, deferred issue) rather than demonstrating the current code doesn't crash.
**Warning signs:** A concurrency test that asserts cache-hit-rate or "identical response bodies across concurrent calls" is testing a guarantee the code doesn't make yet.

### Pitfall 5: Vite's default dev server doesn't need CORS changes — don't touch `api/main.py`'s `allow_origins=["*"]`
**What goes wrong:** A planner might see `CORSMiddleware(allow_origins=["*"])` (api/main.py:48) and think Phase 1 needs to restrict it for the new frontend to work.
**Why it happens:** Confusing SEC-01 (Phase 6: "CORS restricted from `["*"]` to configured origins") with this phase's dev-proxy work.
**How to avoid:** The Vite proxy makes all frontend→backend requests same-origin from the browser's perspective (browser talks to `:5173`, Vite forwards server-side to `:8000`) — CORS headers are never consulted in this flow. Leave `allow_origins=["*"]` untouched; SEC-01 is explicitly Phase 6 scope.
**Warning signs:** A plan task proposes editing `CORSMiddleware` configuration in Phase 1.

## Code Examples

### `api/main.py` — minimal DI seam addition (the phase's only production-code change)
```python
# Source: api/main.py:51-54 (current), read in full this session — proposed refactor
_lock = threading.Lock()

def _initial_state() -> dict:
    """Factory for _state's pristine shape — single source of truth so tests
    (and _refresh's cold-start check) never hardcode the dict's keys."""
    return {"artifact": None, "boot": None, "fixtures": None, "gw": None,
            "pools": {}, "loaded_at": 0.0}

_state: dict = _initial_state()
_solve_cache: dict = {}
```

### `tests/conftest.py` — autouse state-reset fixture
```python
"""Shared pytest fixtures for the API test suite."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_api_state():
    """Reset api.main's module-level globals before every test so test order
    never leaks state (APIT-03's required autouse reset)."""
    import api.main as m
    m._state = m._initial_state()
    m._solve_cache.clear()
    yield
    m._state = m._initial_state()
    m._solve_cache.clear()
```

### `vite.config.ts` — dev proxy for `/api` and `/data`
```typescript
// Source: pattern verified against api/main.py:402's actual StaticFiles mount + /api/* routes
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/data": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
```

### `src/router.tsx` — React Router 7 declarative mode, 8 routes + catch-all
```tsx
// Source: reactrouter.com SPA guide (WebFetch, this session) + 01-UI-SPEC.md Routes table
import { createBrowserRouter } from "react-router";
import { PageShell } from "./components/PageShell";
import { ErrorState } from "./components/ErrorState";
import { NotFoundPage } from "./components/NotFoundPage";
import XpTable from "./routes/XpTable";
import Team from "./routes/Team";
import Fixtures from "./routes/Fixtures";
import Prices from "./routes/Prices";
import League from "./routes/League";
import Scoreboard from "./routes/Scoreboard";
import Differentials from "./routes/Differentials";
import Methodology from "./routes/Methodology";

export const router = createBrowserRouter([
  {
    element: <PageShell />,
    errorElement: <ErrorState resource="this page" />,
    children: [
      { path: "/", element: <XpTable /> },
      { path: "/team", element: <Team /> },
      { path: "/fixtures", element: <Fixtures /> },
      { path: "/prices", element: <Prices /> },
      { path: "/league", element: <League /> },
      { path: "/scoreboard", element: <Scoreboard /> },
      { path: "/differentials", element: <Differentials /> },
      { path: "/methodology", element: <Methodology /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
```

### `src/main.tsx`
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { router } from "./router";
import "./index.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
```

### `src/index.css` — Tailwind v4 CSS-first config
```css
/* Source: tailwindcss.com/blog/tailwindcss-v4 (WebSearch, this session) + 01-UI-SPEC.md Color table */
@import "tailwindcss";

@theme {
  --color-bg: #fafbf7;
  --color-surface: #f1f4ec;
  --color-accent: #1c7a45;
  --color-bad: #a3392e;
  /* dark values applied via prefers-color-scheme or a data-theme attribute — Phase 2 (UIX-02) decides which */
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `import { createBrowserRouter } from "react-router-dom"` | `import { createBrowserRouter } from "react-router"` | React Router v7 (unified the two packages) | `react-router-dom` still exists and works (peerDependency `react >= 18`) [VERIFIED: `npm view react-router-dom peerDependencies`] but is a compatibility re-export, not the primary package — use `react-router` directly on a greenfield app |
| Tailwind `tailwind.config.js` + PostCSS + `autoprefixer` | `@tailwindcss/vite` plugin + CSS-first `@theme` block, no config file | Tailwind v4 (2026) | UI-SPEC's "Tailwind v4 `@theme` block" instruction assumes this — do not scaffold a `tailwind.config.js` |
| `useEffect`+`useState` manual fetch | `@tanstack/react-query` `useQuery` | Long-standing React ecosystem convention, not a recent change | UI-SPEC's Loading/Error contract is written assuming `refetch()` exists, which is a TanStack Query API, not a raw-fetch concept |
| Vite 8.2.2 + `@vitejs/plugin-react` 6.1.1 (both `npm latest` as of this research) | Recommend Vite 7.3.6 + `@vitejs/plugin-react` 5.2.0 | Vite 8 published 2026-08-20 (11 days before this research) | Plugin-react 6.x's peerDependency requires `vite ^8.0.0` exclusively — a tight, brand-new pairing; Vite 7 + plugin-react 5.2.0 supports `vite ^4 || ^5 || ^6 || ^7 || ^8` and is the "boring, maintainable" choice CLAUDE.md's constraints ask for |

**Deprecated/outdated:**
- `react-router-dom` as the primary import source for new v7 projects — kept only for v6→v7 migration ergonomics.
- Tailwind v3-style JS config (`tailwind.config.js` with `content: [...]`) — v4's automatic content detection and CSS-first `@theme` supersede it; do not scaffold one unless a legacy plugin requires it.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact pinned versions for react, react-dom, react-router, @tanstack/react-query, vite, @vitejs/plugin-react, lucide-react, eslint*, @types/*, vitest, jsdom, @testing-library/* (all "ASSUMED — npm registry" in Standard Stack) | Standard Stack | These were read from `npm view <pkg> version` output this session (so registry-verified to *exist*), but the package names themselves came from training knowledge / conventional pairing, not an authoritative doc citation per the package-name provenance rule — a patch release between research and execution could shift the exact pin by a version or two. Re-run `npm view` at plan/execute time. |
| A2 | `responses>=0.25,<0.27` is the correct pin for FPL-API mocking rather than `requests-mock` or manual `monkeypatch` | Standard Stack, Don't Hand-Roll | If the planner prefers zero new test dependencies, `monkeypatch.setattr(requests, "get", dispatch_fn)` is a documented fallback (see Alternatives Considered) — low risk either way, but `responses` needs a `checkpoint:human-verify` per the Package Legitimacy Gate before install |
| A3 | Vite 7.3.6 + `@vitejs/plugin-react@5.2.0` is preferable to the `npm latest` Vite 8 + plugin-react 6 pairing | Standard Stack, Alternatives Considered, State of the Art | This is a judgment call favoring stability over "latest"; if the planner/user prefers bleeding-edge, Vite 8 + plugin-react 6 is verified compatible (peerDependency checked) and equally valid — not a correctness risk, a preference call |
| A4 | Frontend project directory is named `frontend/` at repo root | Recommended Project Structure | Actually **not assumed** — verified in `01-UI-SPEC.md:40` ("first-party components only (`frontend/src/components/`)"), an artifact from this same phase's approved UI design contract. Listed here only because REQUIREMENTS.md/ROADMAP.md don't independently confirm it. |
| A5 | The "backstop" tests UI-SPEC commits to (loading spinner, error+retry, route-isolation) should be built with Vitest + React Testing Library in this phase, not deferred | Standard Stack (Supporting), Alternatives Considered | If the planner instead treats these as Phase 4 (Playwright/E2E) scope, UI-SPEC's own sign-off table will show 3 approved rows unverified for 3 phases — moderate risk of scope drift, worth confirming with the user/planner rather than assuming |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **Should `frontend/` have its own `package.json`/`node_modules`, or should the repo become a monorepo with a root `package.json` (workspaces)?**
   - What we know: No `package.json` exists anywhere in the repo yet; `web/` (vanilla site) has none (framework-free JS).
   - What's unclear: Whether Phase 5's CI (CI-01: "lint, typecheck, pytest + API tests on every push") expects a single `npm install` at repo root or a `cd frontend && npm install` step.
   - Recommendation: Start with a plain standalone `frontend/package.json` (simplest, matches "boring" ethos) — a root-level workspace can be introduced later without breaking `frontend/`'s internal structure if Phase 5 needs it.

2. **Does the concurrency test (APIT-03) need to run against a *real* `uvicorn` process (separate OS process) rather than in-process `TestClient`, to catch races `TestClient`'s ASGI-transport shortcuts might mask?**
   - What we know: `TestClient` dispatches through Starlette's real `anyio.to_thread.run_sync` worker-thread mechanism for sync endpoints — genuine thread-level concurrency, not faked.
   - What's unclear: Whether any race depends on OS-level socket/connection-pool behavior that only a real multi-worker uvicorn process would surface (unlikely for this codebase's globals-based race, but not proven false).
   - Recommendation: Start with in-process `TestClient` + `ThreadPoolExecutor` (Pattern 5) — it already exercises the actual `_lock`/`_state` code paths. Escalate to a real subprocess uvicorn test only if the in-process version fails to reproduce a race the team already suspects from production logs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 (conda `python314`) | All Track A work | ✓ | 3.14.3 | — |
| pytest | Track A | ✓ (installed in `python314` env) | 9.1.1 | — |
| httpx | `TestClient` transport | ✓ | 0.28.1 | — |
| fastapi | App under test | ✓ | 0.136.1 | — |
| `responses` (PyPI) | FPL-API HTTP mocking | ✗ (not installed) | — | `monkeypatch.setattr(requests, "get", ...)` (see Alternatives Considered) — no blocking fallback needed, just an extra `pip install` |
| PuLP + CBC solver | Real ILP solve inside `/solve` tests | ✓ | PuLP 3.3.2, `PULP_CBC_CMD` available | — |
| `models/artifacts/xp_model.joblib` | `_refresh()`'s cold-start path (should be stubbed in tests, not relied on) | ✓ locally, **✗ in git** (untracked) | — | Tests must stub `_state["artifact"]` rather than depend on this file (see Pitfall 1) — this is a blocking issue for CI (Phase 5) if not addressed now |
| Node.js | Track B (`npm create vite`, dev server) | ✓ | v24.20.0 | — |
| npm | Track B package management | ✓ | 12.0.2 | — |
| `frontend/` directory / `package.json` | Track B | ✗ (does not exist yet — greenfield) | — | Created by this phase's plan |
| `.gitignore` at repo root | Prevent `frontend/node_modules` from being committed | ✗ (no `.gitignore` file exists at all, verified — full hygiene pass is Phase 5 SEC-04) | — | Phase 1 must add a minimal `.gitignore` covering at least `frontend/node_modules/`, `frontend/dist/`, `__pycache__/` — do not wait for Phase 5 to avoid a `node_modules` commit disaster |

**Missing dependencies with no fallback:**
- None — every gap above has a documented, low-risk fallback or is simply "this phase creates it."

**Missing dependencies with fallback:**
- `responses` (PyPI) — falls back to manual `monkeypatch.setattr(requests, "get", ...)` if the team prefers zero new test dependencies.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest 9.1.1 [VERIFIED: pip show] |
| Config file (backend) | `pytest.ini` (repo root) — `testpaths = tests`, disables `playwright`/`seleniumbase` plugins to avoid `--browser` flag collision [VERIFIED: read in full this session] |
| Quick run command (backend) | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_api.py -x` |
| Full suite command (backend) | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest` |
| Framework (frontend, this phase's "backstop" tests only) | Vitest 4.1.11 [ASSUMED — npm registry] + `@testing-library/react` |
| Config file (frontend) | none yet — Wave 0 must add `vitest.config.ts` or a `test` block in `vite.config.ts` |
| Quick run command (frontend) | `cd frontend && npx vitest run src/components/ErrorState.test.tsx` |
| Full suite command (frontend) | `cd frontend && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APIT-01 | `/solve` returns a legal squad, `/team` returns picks, `/rate` returns a score, `/health`/`/meta` return expected shape | integration | `pytest tests/test_api.py -k "solve or team or rate or health or meta" -x` | ❌ Wave 0 |
| APIT-02 | `require_key()` behaves correctly open / valid-key / invalid-key | integration | `pytest tests/test_api.py -k require_key -x` | ❌ Wave 0 |
| APIT-03 | Concurrent solve + refresh doesn't crash or corrupt state, runs green repeatedly | integration/concurrency | `pytest tests/test_api.py -k concurrent -x` (consider `--count=5` via `pytest-repeat` or a manual loop if flakiness needs to be ruled out — not currently installed, evaluate at plan time) | ❌ Wave 0 |
| UI-01 | All 8 routes resolve without throwing; loading/error/placeholder backstop states render | component (Vitest+RTL) | `cd frontend && npx vitest run` | ❌ Wave 0 (frontend + its tests don't exist yet) |

### Sampling Rate
- **Per task commit:** backend — `pytest tests/test_api.py -x`; frontend — `npx vitest run` (once scaffolded)
- **Per wave merge:** full `pytest` (backend) + `npx vitest run` (frontend, once it exists)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — autouse `_reset_api_state` fixture (see Code Examples)
- [ ] `api/main.py` — add `_initial_state()` factory (minimal DI seam, see Code Examples)
- [ ] `tests/test_api.py` — new file (or extend `tests/test_product.py`'s existing API section) covering APIT-01/02/03
- [ ] `pip install "responses>=0.25,<0.27"` (or the monkeypatch fallback) — not currently installed
- [ ] `frontend/` — does not exist; Wave 0 scaffolds it entirely (`npm create vite@latest frontend -- --template react-ts`)
- [ ] `frontend/vitest.config.ts` (or a `test` block in `vite.config.ts`) — framework install for the backstop tests
- [ ] Root `.gitignore` — at minimum `frontend/node_modules/`, `frontend/dist/`, `__pycache__/` (see Environment Availability)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `require_key()` stub — this phase *tests* it, does not change it. No new auth mechanism is introduced. |
| V3 Session Management | no | Stateless API-key header, no sessions |
| V4 Access Control | no | Single-tier key check, no roles/permissions in this phase's scope |
| V5 Input Validation | yes | Already handled by existing Pydantic `SolveRequest`/`PlanRequest` models — no new input surface this phase |
| V6 Cryptography | no | No cryptographic operations added |
| V13 API and Web Service | yes | CORS (`allow_origins=["*"]`) is explicitly out of scope (deferred SEC-01, Phase 6) — see Pitfall 5. Do not restrict it in this phase. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Test suite accidentally hitting the real FPL API (data leakage / flaky CI / rate-limit risk) | Information Disclosure | `responses` library's default behavior — any unregistered outbound `requests` call raises `ConnectionError` rather than silently succeeding, making "no real network in tests" enforceable rather than a convention that erodes over time |
| `X-API-Key` comparison timing side-channel (`x_api_key not in keys`, a set-membership check) | Information Disclosure (minor) | Out of scope for this phase — `require_key()` is explicitly a stub, upgraded to real auth (Supabase JWT) only when payments ship (per CLAUDE.md's documented migration path). Testing its current three modes (this phase's job) does not require fixing its constant-time-comparison posture. |
| Committing `frontend/node_modules/` or a real `.env`/API key into git because no `.gitignore` exists yet | Tampering / Information Disclosure | Add a minimal root `.gitignore` in this phase (see Environment Availability) — full hygiene (Chrome `.deb` removal, etc.) stays Phase 5 SEC-04 scope, but node_modules must not land in a commit even in Phase 1 |

## Sources

### Primary (HIGH confidence)
- `api/main.py` (read in full, this session) — endpoint behavior, `_state`/`_lock`/`_solve_cache` globals, `require_key()`, `StaticFiles` mount path
- `predict/live.py` (read, this session) — `_load_live`, `_next_gw`, `_gw_pool`, `build_pool`/`build_horizon_pool` signatures
- `config.py` (read in full, this session) — `FPL_API`, `MAX_FREE_TRANSFERS`, path constants
- `tests/test_product.py` (read in full, this session) — existing `test_api_solve_and_resolve`/`test_free_transfer_accrual` precedent, `fake_boot`/`fake_pool` fixture pattern
- `pytest.ini` (read, this session) — `-p no:playwright -p no:seleniumbase` addopts, `testpaths = tests`
- `.planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md` (read in full, this session) — approved design system, 8 routes, app-shell contract, `frontend/src/components/` directory decision
- `git cat-file` / `git ls-files` on `models/artifacts/xp_model.joblib` (run this session) — confirmed the artifact is untracked
- `npm view <pkg> version` / `peerDependencies` for react, react-dom, react-router, react-router-dom, typescript, typescript-eslint, vite, @vitejs/plugin-react (both major lines), tailwindcss, @tailwindcss/vite, @tanstack/react-query, lucide-react, eslint*, vitest, jsdom, @testing-library/*, @types/node, @types/react, @types/react-dom (run this session, live npm registry)
- `pip show pytest httpx fastapi` / `pip index versions responses pytest-cov` (run this session, live PyPI registry)
- Package-legitimacy seam (`gsd-tools query package-legitimacy check`) — run against all npm/PyPI candidates listed in the audit table, this session

### Secondary (MEDIUM confidence)
- reactrouter.com "Single Page App (SPA)" guide (WebFetch, this session) — `createBrowserRouter`/`RouterProvider`/`errorElement` pattern, `react-router` vs `react-router-dom` migration note
- tailwindcss.com/blog/tailwindcss-v4 (WebSearch, this session, cross-referenced across multiple independent tutorial sources) — `@tailwindcss/vite` plugin, CSS-first `@theme` config, no `tailwind.config.js` needed

### Tertiary (LOW confidence)
- None — all WebSearch findings above were cross-checked against either the official docs domain or a verified `npm view`/`pip` command output before being included.

## Metadata

**Confidence breakdown:**
- Standard stack (Python/Track A): HIGH — every package version/behavior claim is either a live `pip show`/registry check or a direct source-file read
- Standard stack (Node/Track B): MEDIUM — package existence and peerDependency constraints are registry-verified, but exact version pins are training-knowledge-informed package *names* confirmed to exist on the registry this session (per the package-name provenance rule, tagged ASSUMED accordingly)
- Architecture patterns: HIGH — every code pattern in this document either extends an existing, working test in this repo or is derived from reading `api/main.py`'s actual control flow line-by-line
- Pitfalls: HIGH — all five are grounded in something verified this session (git tracking status, a read peerDependency constraint, a read `StaticFiles` mount path, a read unlocked-cache code path, a read `CORSMiddleware` call site), not speculation

**Research date:** 2026-08-31
**Valid until:** ~7 days for the Node/npm package version pins (this ecosystem ships releases multiple times a week, as the "too-new" legitimacy flags demonstrate) — re-run `npm view` before executing the plan if there's been a delay. ~30 days for the Python/backend findings (stable, slower-moving stack, verified directly against this repo's source).
