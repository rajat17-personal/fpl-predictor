# Architecture Research

**Domain:** React (Vite) frontend integration into an existing Python/FastAPI batch-ML product
**Researched:** 2026-08-31
**Confidence:** MEDIUM-HIGH (integration patterns cross-checked against multiple current sources; project-specific component decisions are opinionated synthesis, flagged where so)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     EXISTING (unchanged this milestone)                  │
│  data/ → features/ → models/ → optimize/ → predict/export.py             │
│                                        │                                  │
│                                        ▼                                  │
│                          web/data/*.json  (JSON export contract)         │
│                          — git-tracked, refreshed weekly, NOT rebuilt    │
│                            when the frontend or API code changes         │
└───────────────────────────────────┬──────────────────────────────────────┘
                                     │ runtime fetch (never build-time import)
                 ┌───────────────────┴───────────────────┐
                 ▼                                        ▼
   ┌─────────────────────────────┐         ┌─────────────────────────────┐
   │   FastAPI  (api/main.py)    │◄───────►│   React (Vite) SPA           │
   │   /api/solve /api/rate      │  fetch   │   frontend/  (NEW)           │
   │   /api/team  /api/health    │  /api/*  │   8 routed pages             │
   │   mounts StaticFiles:       │          │   pitch renderer             │
   │    - /data  → web/data/     │  fetch   │   react-router + TanStack    │
   │    - /      → frontend/dist │  /data/* │   Query                      │
   │      (only when             │          │                              │
   │       SERVE_FRONTEND=true)  │          │  dev: served by Vite dev     │
   └─────────────────────────────┘          │  server + proxy (see below) │
                                             └─────────────────────────────┘
                 ▲                                        ▲
                 │ same container (Option A)              │ separate deploy target
                 │ Docker multi-stage image                │ (Option B, future milestone)
                 └───────────────── OR ───────────────────►  Cloudflare Pages
                                                              serving frontend/dist
                                                              + a copy of web/data/
                                                              CORS-calling the API
                                                              on its own origin
```

**The one decision everything else depends on:** `web/data/*.json` stays a **runtime-fetched, git-tracked static asset directory** — it is never imported into the JS bundle at build time. This is what the existing vanilla site already does (`web/assets/app.js` does `fetch('/data/xp_table.json')`), and it's why the contract exists at all: it decouples product from pipeline and lets the site update weekly (`predict/export.py`) without a frontend rebuild or redeploy. The React rebuild must preserve exactly this behavior. Everything below (dev proxy, hosting-option flexibility, Docker layout) is designed to protect that invariant.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `predict/export.py` | Writes the JSON contract | Unchanged — still the only writer of `web/data/*.json` |
| `web/data/` | Contract storage, git-tracked | Unchanged directory; becomes the "data API" both frontend hosting options read from |
| `api/main.py` | Solver API + optional static serving | FastAPI, gains a `/data` StaticFiles mount and an optional frontend mount, both env-gated |
| `frontend/` (new) | React SPA: 8 pages, pitch renderer, solver UI | Vite + React + TypeScript + react-router + TanStack Query |
| `frontend/src/lib/config.ts` | Runtime base-URL resolution | `import.meta.env.VITE_API_BASE` / `VITE_DATA_BASE`, defaulting to relative paths (`/api`, `/data`) |
| Vite dev server | Local dev, HMR, proxy to FastAPI | `vite.config.ts` `server.proxy` for `/api` and `/data` → `http://localhost:8000` |
| Docker image | Reproducible build + runtime artifact | Multi-stage: Node build stage → Python runtime stage, frontend `dist/` copied in |
| GitHub Actions `ci.yml` | Lint/test/build/publish gate | Job graph: lint → {python-tests, api-tests, frontend-build} → e2e → docker-publish |

## Recommended Project Structure

```
fpl/
├── frontend/                        # NEW — React + Vite SPA (Node workspace)
│   ├── src/
│   │   ├── pages/                   # One component per route (8 total)
│   │   │   ├── XpTablePage.tsx      # was index.html
│   │   │   ├── TeamPage.tsx         # was team.html — hosts the pitch renderer
│   │   │   ├── ScoreboardPage.tsx
│   │   │   ├── FixturesPage.tsx
│   │   │   ├── LeaguePage.tsx
│   │   │   ├── PricesPage.tsx
│   │   │   ├── MethodologyPage.tsx
│   │   │   └── DifferentialsPage.tsx
│   │   ├── components/
│   │   │   ├── pitch/                # See "Pitch Renderer" pattern below
│   │   │   │   ├── Pitch.tsx
│   │   │   │   ├── FormationRow.tsx
│   │   │   │   ├── PlayerSlot.tsx
│   │   │   │   ├── PlayerCard.tsx
│   │   │   │   ├── ShirtIcon.tsx
│   │   │   │   └── BenchRow.tsx
│   │   │   ├── tables/               # Sortable/filterable xP + prices tables
│   │   │   ├── layout/               # NavBar, PageShell, ErrorBoundary
│   │   │   └── common/               # Loading, EmptyState, Badge, Tooltip
│   │   ├── lib/
│   │   │   ├── api.ts                 # fetch wrapper: /api/solve, /api/rate, /api/team
│   │   │   ├── data.ts                # fetch wrapper: /data/*.json contract
│   │   │   └── config.ts              # runtime API_BASE / DATA_BASE resolution
│   │   ├── hooks/                     # useXpTable, useSquad, useSolve (TanStack Query)
│   │   ├── types/                     # TS types mirroring each JSON contract file
│   │   ├── router.tsx                 # react-router route table (8 routes)
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── e2e/                           # Playwright specs
│   │   ├── fixtures/                  # Frozen JSON fixtures (copies of web/data/*.json shape)
│   │   └── *.spec.ts
│   ├── index.html
│   ├── vite.config.ts                 # dev proxy config (see Pattern 2)
│   ├── playwright.config.ts
│   ├── package.json / package-lock.json
│   ├── tsconfig.json
│   └── .env.example                   # VITE_API_BASE=, VITE_DATA_BASE=
├── api/
│   └── main.py                        # + StaticFiles mounts, env-gated (see Pattern 1)
├── web/
│   ├── data/                          # UNCHANGED — the contract; still written by predict/export.py
│   └── *.html, assets/                # Vanilla site — frozen as reference, retired at cutover
├── tests/                             # Existing pytest: leakage, legality, autosub
├── tests/test_api/                    # NEW — FastAPI TestClient integration tests
├── Dockerfile                         # NEW — multi-stage (Node build → Python runtime)
└── .github/workflows/
    ├── ci.yml                         # NEW — lint/test/build/e2e/docker-publish
    ├── daily.yml                      # existing, untouched
    └── weekly.yml                     # existing, untouched
```

### Structure Rationale

- **`frontend/` as a new top-level dir, not `web-react/` nested under `web/`:** `web/` is currently overloaded to mean both "the site" and "the data contract" (`web/data/`). Splitting them — `frontend/` for the SPA, `web/data/` staying put for the contract — makes the contract boundary explicit in the directory layout itself, not just in documentation. It also means the Node workspace (`frontend/package.json`, `node_modules/`) never sits inside a directory `predict/export.py` writes into.
- **`web/*.html` stays until cutover, then is deleted:** Full parity is a stated requirement, and keeping the vanilla site alive during the rebuild gives you a working fallback and a visual/behavioral reference to diff against — cheap insurance for a solo dev with no test coverage on the current UI.
- **`tests/test_api/` inside the existing `tests/` tree, not a separate top-level package:** One pytest invocation, one `pytest.ini`, one coverage report. Use a pytest marker (`@pytest.mark.api`) so CI can still run it as a distinct job for a clear pass/fail signal without a second test runner config.
- **Playwright lives under `frontend/e2e/`, not at repo root:** Playwright's Node tooling (`@playwright/test`) is a frontend-workspace dependency; keeping it there avoids a second root-level `package.json` and keeps `npm ci` scoped correctly in CI (`working-directory: frontend`).

## Architectural Patterns

### Pattern 1: Env-gated dual serving (StaticFiles vs standalone) via one flag

**What:** `api/main.py` mounts `web/data/` as static files unconditionally (both hosting options need it), and mounts `frontend/dist/` as the SPA root **only** when an env var (e.g. `SERVE_FRONTEND=1`) is set. This is the single mechanism that keeps "FastAPI serves everything" and "Cloudflare Pages serves the frontend, API is a separate origin" both live without branching code elsewhere.

**When to use:** Now — this milestone has no hosting purchased yet (per PROJECT.md), so you don't know which mode ships first. Building the flag now costs almost nothing and removes a future migration.

**Trade-offs:** Slightly more FastAPI boilerplate; in exchange, the Docker image works as a complete single-container demo today and as an API-only container later, with no code change — only the env var and whether you `COPY` the frontend build into the image.

```python
# api/main.py
from fastapi.staticfiles import StaticFiles
import os

app.mount("/data", StaticFiles(directory="web/data"), name="data")

if os.getenv("SERVE_FRONTEND") == "1":
    # Custom handler needed: unknown paths (client-side routes) must fall back
    # to index.html, or refreshing /team in the browser 404s.
    app.mount("/", SPAStaticFiles(directory="frontend/dist", html=True), name="spa")
```

A plain `StaticFiles(html=True)` serves `index.html` for `/` but still 404s on deep links like `/team` on a hard refresh — you need a small `SPAStaticFiles` subclass (or a catch-all route) that falls back to `index.html` on 404 for any path without a file extension. This is the most commonly hit gotcha in FastAPI+SPA setups per current community write-ups.

### Pattern 2: Dev-server proxy, not CORS, for local development

**What:** `vite.config.ts` proxies `/api` and `/data` to `http://localhost:8000` so the React dev server (port 5173) and FastAPI (port 8000) look same-origin to the browser during development. Production same-origin serving (Pattern 1) needs no proxy at all; only the CORS-restricted standalone-hosting case (Cloudflare Pages calling a separately-hosted API) needs real CORS config, and only at deploy time — not during local dev.

**Trade-offs:** None significant — this is the standard Vite+backend dev pattern and avoids loosening CORS just to develop locally (the concerns audit already flags "wide-open CORS" as a hardening item; don't reintroduce it via the dev workflow).

```ts
// frontend/vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/data": "http://localhost:8000",
    },
  },
});
```

### Pattern 3: Runtime-configurable, build-time-defaulted base URLs

**What:** `frontend/src/lib/config.ts` exports `API_BASE` and `DATA_BASE`, sourced from `import.meta.env.VITE_API_BASE` / `VITE_DATA_BASE`, defaulting to the relative paths `"/api"` and `"/data"`. Every fetch in `lib/api.ts` and `lib/data.ts` goes through these constants — never a hardcoded URL.

**When to use:** Always, from the very first page. This is what lets the exact same `frontend/dist` build artifact work when FastAPI serves it (relative paths resolve same-origin) and lets a *per-environment* build target Cloudflare Pages + a separately hosted API (`VITE_API_BASE=https://api.example.com/api` baked in at that build's `npm run build` time).

**Trade-offs:** Cloudflare Pages standalone mode still requires a distinct build per API origin (Vite env vars are compile-time, not runtime-swappable after the fact) — acceptable for a solo-dev CI pipeline that already rebuilds per push; avoid over-engineering a runtime-config-fetch layer for a problem that doesn't exist yet (no live hosting this milestone).

```ts
// frontend/src/lib/config.ts
export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
export const DATA_BASE = import.meta.env.VITE_DATA_BASE ?? "/data";
```

### Pattern 4: Presentational pitch renderer, container pages own state

**What:** `components/pitch/*` are pure, typed, prop-driven components with no data fetching and no page-specific logic. `Pitch` takes a `formation: string` (e.g. `"3-4-3"`) and `players: PitchPlayer[]`; it lays out `FormationRow`s via CSS Grid, not absolute-positioned percentages. Reason: CSS Grid rows keyed to formation counts reflow correctly at any viewport width without recalculating coordinates, each slot is a real focusable/clickable DOM node (accessibility + click-to-lock UX for the solver, drag targets if wanted later), and the layout logic is declarative (`grid-template-columns: repeat(N, 1fr)` per row) rather than trigonometry. Reserve SVG for the pitch *markings* only (center circle, box lines, half-way line) as a background layer — SVG is the right tool for scalable line art, CSS Grid is the right tool for a formation grid.

**When to use:** `TeamPage` (rate-my-team + solver) and any future squad-preview surface. Because it's presentational, the same `Pitch` component serves `squad.json` (weekly optimal squad), `/api/rate` results (user's actual squad), and `/api/solve` results (what-if squad) — three data sources, one component.

**Trade-offs:** A hybrid SVG-background + CSS-Grid-foreground needs the two layers kept in visual sync (grid row heights matching where the pitch thirds are drawn) — a minor CSS coordination cost, worth it for the responsiveness and DOM-semantics win over a fully-SVG pitch (where every player position is a manually computed `<g transform>`).

```tsx
// frontend/src/components/pitch/Pitch.tsx (sketch)
function Pitch({ formation, players }: { formation: string; players: PitchPlayer[] }) {
  const rows = formationToRows(formation); // "3-4-3" -> [DEF x3, MID x4, FWD x3], GK row implicit
  return (
    <div className="pitch">
      <PitchMarkings />           {/* SVG background layer */}
      {rows.map(row => (
        <FormationRow key={row.position} count={row.count}>
          {row.playersFor(players).map(p => <PlayerSlot key={p.id} player={p} />)}
        </FormationRow>
      ))}
    </div>
  );
}
```

**Shirts/kits:** Use FPL's own shirt image CDN (same asset the official app references) inside `ShirtIcon`, with an `onError` fallback to a neutral generated jersey (solid team-color SVG) if the CDN URL 404s or is unreachable — avoids bundling or redistributing trademarked crest assets locally, per the open question flagged in PROJECT.md, and requires no build-time asset licensing decision.

### Pattern 5: react-router over file-based routing

**What:** Use `react-router` (`createBrowserRouter`, declarative route table in `router.tsx`) for the 8 known pages, mapped 1:1 from the existing `.html` files.

**When to use:** This project — a fixed, small, known set of 8 routes with no marketing/content-driven page sprawl that would benefit from file-based conventions (which in the Vite world means pulling in a routing plugin like `vite-plugin-pages`, an extra dependency for no real gain at this scale). react-router is also the de facto standard "boring" choice for a Vite+React SPA and has the largest ecosystem overlap with component/pitch libraries, matching the stated rationale for choosing React itself.

**Trade-offs:** File-based routing would auto-generate the route table as pages are added, saving a few lines — not worth the extra build-plugin dependency for a fixed 8-page app that isn't expected to grow route count materially.

## Data Flow

### Request Flow (page load, e.g. Team page)

```
Browser navigates to /team
    ↓
react-router renders <TeamPage/>
    ↓                                    ↓
useXpTable() [TanStack Query]      useTeam(entryId) [TanStack Query]
    ↓                                    ↓
GET {DATA_BASE}/xp_table.json      GET {API_BASE}/team/{entryId}
    ↓                                    ↓
(same-origin or CORS, per          FastAPI api/main.py
 hosting option — Pattern 1/3)     → cached pool + FPL live fetch
    ↓                                    ↓
JSON response cached by            JSON response (squad + xP)
TanStack Query (staleTime
tuned to weekly refresh cadence)
    ↓                                    ↓
              <Pitch formation={...} players={...}/>
                          ↓
        FormationRow → PlayerSlot → PlayerCard → ShirtIcon
```

### Solver Interaction Flow (what-if / rate-my-team)

```
User locks/excludes a player on <TeamPage/>
    ↓
Local component state (locks: Set<playerId>)
    ↓
POST {API_BASE}/solve  { locks, excludes, horizon, chip }
    ↓
api/main.py: threading.Lock()-guarded pool refresh (if TTL expired)
    ↓ optimize/squad_ilp.py or optimize/transfers.py
Response: { squad, xi, captain, expected_points }
    ↓
TanStack Query mutation result → re-render <Pitch/> with proposed XI
    (previous "current" squad remains visible for diff/comparison — UX detail for UI-SPEC, not architecture)
```

### Key Data Flows

1. **Contract flow (weekly, pipeline-owned):** `predict/export.py` → `web/data/*.json` (git commit). Nothing in the frontend build touches this path; it is read only at browser runtime via `fetch()`. This is unchanged by the React rebuild — it's the load-bearing invariant.
2. **Solver flow (on-demand, request/response):** Browser → `/api/solve|rate|team` → FastAPI (ILP solve or FPL live fetch) → JSON → browser. No caching contract file is involved; this is live compute, same as the current vanilla site's `app.js` → `/api/*` calls.
3. **Build-time flow (CI, no runtime relevance):** `frontend/` source → `npm run build` → `frontend/dist/` (static JS/CSS/HTML) → copied into the Docker image or a Cloudflare Pages publish directory. This never touches `web/data/`.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (solo dev, pre-revenue, few users) | Single container running both FastAPI and (optionally) the built frontend is entirely sufficient. No CDN, no separate frontend host needed yet. |
| Freemium launch (hundreds–low thousands of managers, weekly traffic spike near GW deadlines) | Move frontend to Cloudflare Pages (free tier, global CDN) — the architecture above already supports this with zero code change, only a build-time env var and a hosting decision. API stays on a small VM; solve-cache + pool-cache (already in `api/main.py`) absorb deadline-hour load as they do today. |
| Paid subscriber growth (tens of thousands) | `/api/solve` is the only CPU-heavy endpoint (ILP solve); horizontal-scale the API behind a load balancer if solve latency becomes the bottleneck, keep the frontend static/CDN-served throughout — it never needs to scale differently than a brochure site. |

### Scaling Priorities

1. **First bottleneck:** ILP solve latency at deadline-hour traffic spikes — already mitigated by the existing solve cache; if it recurs, it's an API/optimize-layer concern, not a frontend architecture concern.
2. **Second bottleneck:** FPL's own API rate limits during pool refresh — again pre-existing (TTL cache), unaffected by the frontend rebuild.

The React rebuild does not introduce new scaling concerns; it inherits the existing API's scaling profile and, if anything, *reduces* future scaling risk by making the frontend trivially CDN-offloadable.

## Anti-Patterns

### Anti-Pattern 1: Bundling `web/data/*.json` into the JS build

**What people do:** `import xpTable from '../../web/data/xp_table.json'` in a React component, because it's convenient and gives you build-time type inference for free.

**Why it's wrong:** It bakes this week's data into the JS bundle. The moment `predict/export.py` runs again (weekly, or after a GW), the deployed site silently serves stale data until the frontend is rebuilt and redeployed — defeating the entire purpose of the JSON export contract, which PROJECT.md explicitly calls out as decoupling product from pipeline.

**Do this instead:** Always `fetch()` the JSON contract at runtime through `lib/data.ts`, using generated/hand-written TypeScript types in `types/` for the shape, not a build-time import for the values.

### Anti-Pattern 2: Hardcoding `http://localhost:8000` or a specific API domain in components

**What people do:** Sprinkle the API origin directly into `fetch()` calls scattered across page components.

**Why it's wrong:** Locks the build to one hosting topology, breaking the "keep both options open" requirement (FastAPI-served vs standalone Cloudflare Pages) and making local dev, Docker, and future prod builds each need source-code edits.

**Do this instead:** Route every request through `API_BASE`/`DATA_BASE` from `lib/config.ts` (Pattern 3).

### Anti-Pattern 3: A single monolithic `<Pitch>` component owning fetch + state + layout

**What people do:** One giant component that fetches squad data, manages lock/exclude state, computes formation math, and renders SVG coordinates all in one file — the natural shape a solo dev reaches for when moving fast.

**Why it's wrong:** It can't be reused across the three surfaces that need a pitch (squad.json view, rate-my-team, solver what-if), and it makes the Playwright E2E suite (which needs to assert on rendered player slots) fragile since there's no stable component boundary to target.

**Do this instead:** Keep `Pitch`/`FormationRow`/`PlayerSlot`/`PlayerCard` purely presentational (Pattern 4); push fetching and state to the page component and a `hooks/` layer.

### Anti-Pattern 4: Playwright E2E against the live FPL API / live gameweek state

**What people do:** Point E2E tests at the real API with no fixture override, asserting on "today's" data.

**Why it's wrong:** Non-deterministic (data changes weekly, injuries/prices shift daily), and slow (real FPL API + real ILP solves per test run). It also means CI failures can be caused by upstream FPL API changes, not your code.

**Do this instead:** Serve the built frontend via uvicorn with `web/data/` pointed at a **fixtures** directory (frozen JSON snapshots, including a fixture for entry `6980093` per PROJECT.md's note to use the user's own team ID for rate-my-team/solver E2E) so E2E is deterministic and fast. Real FPL API/live-data behavior belongs in the API test suite (mocked HTTP) or a separate, non-blocking smoke check, not the E2E gate.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| FPL shirt/kit CDN | `<img>` `src` pointed at FPL's public shirt asset URLs, with `onError` fallback | Avoids redistributing trademarked crest images locally; resolve exact CDN URL pattern during UI design (flagged open question in PROJECT.md) |
| GHCR (GitHub Container Registry) | `docker/build-push-action` in CI, `docker-publish` job | Free for public/private repos at this project's scale — fits the "prefer free tiers" constraint |
| Cloudflare Pages (future milestone) | Build `frontend/dist` + a copy of `web/data/` as the publish directory; set `VITE_API_BASE` to the API's public origin at build time | Out of scope this milestone (no hosting purchased) — architecture above keeps it a config change, not a rewrite |
| Supabase JWT (future milestone) | Frontend adds an `Authorization` header in `lib/api.ts`; `require_key()` in `api/main.py` is the documented swap point | Explicitly deferred per PROJECT.md; frontend's `api.ts` fetch wrapper is the one place to add the header later, so build it as a single interceptor now even while auth is a no-op |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `predict/export.py` ↔ `frontend/` | File contract (`web/data/*.json`), read via HTTP fetch, never a direct import | The load-bearing boundary of this whole milestone — see "Standard Architecture" above |
| `api/main.py` ↔ `frontend/` | HTTP/JSON (`/api/solve`, `/api/rate`, `/api/team`, `/api/health`) | Same contract the vanilla site already uses; no endpoint shape changes needed for the rebuild itself |
| `frontend/` build ↔ Docker image | Build artifact copy (`frontend/dist` → image layer), not source | Keeps the Python runtime stage free of `node_modules` |
| `tests/test_api/` ↔ `api/main.py` | In-process `TestClient`, no network | Fast, deterministic, no server process needed — this is the "missing base layer" PROJECT.md calls out |
| `frontend/e2e/` ↔ built app | Real HTTP against `uvicorn` serving `frontend/dist` + fixture `web/data/` | Full-stack but deterministic; the top of the test pyramid |

## Suggested Build Order

Ordered by dependency, not necessarily by calendar phase — items on the same line have no dependency on each other and can proceed in parallel:

1. **`api/main.py` FastAPI TestClient test suite** (`tests/test_api/`) — no frontend dependency at all; this is PROJECT.md's explicitly called-out missing base layer and should not wait on any React work.
   **(parallel with 1)** **`frontend/` scaffold** — Vite + React + TS, dev proxy (Pattern 2), a single page hitting `/api/health` to prove the seam end-to-end before building real UI.
2. **Data contract typing + fetch layer** (`types/`, `lib/data.ts`, `lib/api.ts`, `lib/config.ts`) — depends on the scaffold (1) existing; can be built against the real, current `web/data/*.json` files as fixtures.
3. **Non-pitch pages** (xP table, fixtures, prices, methodology, differentials, league, scoreboard — 7 of 8) — depends on (2). These are tables/lists; lowest complexity, validates routing + data flow before tackling the hardest UI.
4. **Pitch renderer component set** (`Pitch`, `FormationRow`, `PlayerSlot`, `PlayerCard`, `ShirtIcon`, `BenchRow`) — depends on (2) for types only; can be built and manually verified in isolation (e.g., a throwaway dev-only route feeding it `squad.json`) before it's wired into a real page.
5. **Team page (rate-my-team + solver UI)** — depends on (3)'s patterns, (4)'s components, and (1)'s API test suite having already validated `/api/solve`/`/api/rate`/`/api/team` behavior. This is the highest-integration-risk page; sequence it last among pages.
6. **Dockerfile (multi-stage)** — depends on (1)-(5) existing enough that `npm run build` produces a real artifact worth baking; can be scaffolded earlier with a stub frontend build if you want the CI plumbing ready sooner.
7. **GitHub Actions `ci.yml` job skeleton** (lint, python-tests, api-tests, frontend-build) — can start as soon as (1) and (1-parallel) exist; doesn't need to be complete until later.
8. **Playwright E2E suite + fixtures** (incl. entry `6980093` fixture) — depends on (5) for a meaningful surface to test and on a working uvicorn-serves-built-frontend setup (from 6/7's Docker/CI work) for the "serve built frontend with fixture JSON" execution model.
9. **`e2e` and `docker-publish` CI jobs wired into `ci.yml`** — depends on (6), (7), (8) all existing; this is the last piece of the pipeline, gated behind everything else passing.
10. **Cutover** — retire `web/*.html` + `web/assets/` once React reaches verified full parity; `web/data/` is untouched throughout and requires no migration step at all.

This ordering front-loads the two things with zero mutual dependency and the highest architectural risk if deferred — the API test base layer, and proving the frontend-to-API/data seam — before any pixel-level UI work, and pushes the pitch renderer and CI/Docker/E2E plumbing to the middle/end where they belong once there's a real app to containerize and test.

## Sources

- [Serving a Vite.js React project with a FastAPI backend via Docker — fastapi/fastapi Discussion #5134](https://github.com/fastapi/fastapi/discussions/5134) — community-validated pattern for the StaticFiles + SPA-fallback approach (Pattern 1)
- [Monorepo Development with FastAPI and Vite.js — Grokipedia](https://grokipedia.com/page/Monorepo_Development_with_FastAPI_and_Vitejs) — monorepo layout and dev-proxy conventions (Pattern 2)
- [How to Serve a React Frontend with FastAPI — Medium](https://medium.com/@c.tasca.1971/how-to-serve-a-react-frontend-with-fastapi-36a96663b3cb) — StaticFiles mounting and relative-asset-path gotchas
- [Cache Playwright Browsers in GitHub Actions — QASkills.sh](https://qaskills.sh/blog/github-actions-cache-playwright-browsers) — `actions/cache` keyed on lockfile hash for `~/.cache/ms-playwright`, chromium-only-in-CI recommendation
- [Playwright CI on GitHub Actions: Complete 2026 Guide — QASkills.sh](https://qaskills.sh/blog/playwright-ci-github-actions-complete-guide-2026) — job sequencing and `PLAYWRIGHT_BROWSERS_PATH` for multi-stage Docker builds
- [GitHub Actions cache: dependencies, keys, and cache hits — starsling.dev](https://starsling.dev/best-practices/github-actions/cache-dependencies) — `actions/setup-python` `cache: pip` and `actions/setup-node` `cache: npm` built-in caching, no manual `actions/cache` needed for those two
- Project-internal: `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md` (2026-08-31 codebase map) — source of truth for the existing contract, component boundaries, and explicit constraints (no live deploy, React+Vite choice, full 8-page parity, API test gap)

---
*Architecture research for: React (Vite) frontend integration into a Python/FastAPI batch-ML product*
*Researched: 2026-08-31*
