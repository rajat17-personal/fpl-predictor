# Phase 4: E2E Regression Suite - Research

**Researched:** 2026-09-03
**Domain:** Playwright browser E2E testing against a real FastAPI+React stack, fixture-mode backend seam, SPA static serving
**Confidence:** HIGH (backend seam mechanics, SPA fallback, package versions) / MEDIUM (exact fixture directory layout, Playwright best-practice idioms) / LOW (none — every claim below is either read-verified this session or explicitly flagged ASSUMED)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** **One real full-stack process, fixture-fed.** Playwright runs against uvicorn serving the real FastAPI app; a new **env-var fixture seam in `api/main.py`** (e.g. `FPL_FIXTURE_DIR`) makes the API load frozen FPL-upstream payloads from disk instead of calling `fantasy.premierleague.com`. The real FastAPI code paths, caching, and ILP solver run end to end — E2E genuinely covers the wire between React and FastAPI. Playwright `route()` mocks of `/api/*` were explicitly rejected (they'd leave the React↔API contract browser-untested). — **Reversibility:** costly — Phase 5's CI-02 job ("Playwright against uvicorn serving the built frontend with fixture data") is built on this seam; switching to browser-layer mocks later restructures both the suite and the CI job.
- **D-02:** **The same seam switches the static mount:** in fixture/E2E mode uvicorn serves `frontend/dist` instead of the vanilla `web/` directory. Production default stays `web/` (milestone invariant: vanilla is live until CUT-01); Phase 7's cutover flips this same switch. A separate test-only ASGI app was rejected (drift risk).
- **D-03:** **Local runs are CI-identical, always.** `npm run build` → uvicorn serves `dist/` + fixture data. No dev-server variant, no `E2E_DEV` flag — one topology, zero "works locally, fails in CI" drift.
- **D-04:** **Open auth mode** (`FPL_API_KEYS` unset) — matches today's production posture; the three-mode auth behavior is already covered by Phase 1's APIT-02 tests. No keyed-mode E2E.
- **D-05:** **Playwright's `webServer` config owns the server lifecycle** (build + uvicorn command, port/health readiness, reuse locally, strict in CI). `npx playwright test` is the single entry point; no shell-script orchestration.
- **D-06:** **Real capture + synthesized variants.** Freeze one real week's `web/data/*.json` export as the "normal" set — real player names and realistic magnitudes for humans debugging failures. Derive the **blank** and **double-GW** sets from it by scripted transformation (no real blank/DGW export exists yet this season). Committed once; never auto-refreshed.
- **D-07:** **Coherent same-week API-side capture.** The fixture-mode API's FPL-upstream payloads (bootstrap-static, fixtures, entry **6980093** picks) are captured in the same freeze as the `web/data` snapshot, so `/api` and `/data` describe the same gameweek universe — solve results and page data stay mutually consistent. Trim payloads to the fields the API actually reads.
- **D-08:** **Versioned as immutable dirs + manifest:** `e2e/fixtures/v1/{normal,blank,dgw}/` (exact layout is planner's) with a `MANIFEST.md` recording capture date, GW, source, and the synthesis rules for the variants. A contract change cuts `v2` alongside `v1`; **v1 is never edited in place** — this is what keeps the hardcoded goldens (D-15) from rotting. — **Reversibility:** costly — D-15's literal assertions and the pinned solver golden (D-11) all reference v1 values; mutating v1 invalidates the goldens silently.
- **D-09:** **Normal set backs the five flow suites; blank/DGW back targeted specs** for the surfaces those scenarios actually change (chip timeline DGW/BGW callouts, fixtures ticker with missing/double rows, xP table under a blank week). A full suite × 3-scenarios matrix was rejected (3× runtime, 3× golden maintenance, little signal).
- **D-10:** **Frozen prediction pool, no model artifact at test time.** The fixture set includes the solver's input pool (per-player xP/prices etc.) frozen at capture; fixture mode loads it directly, bypassing model inference. The real ILP still solves over it. No `xp_model.joblib` in git, nothing to load in CI, and weekly retrains can't shift expected values — the "never the calendar" guarantee.
- **D-11:** **Invariants everywhere + one pinned golden.** Every solve test asserts structural invariants: legal 15-man squad (2/5/5/3), locks present, excludes absent, results bar consistent with the pitch, bank arithmetic. One canonical solve on the frozen pool additionally pins the exact XI/transfers as a golden — if a CBC version bump ever flips an optimal tie, exactly one test needs re-pinning, not the whole suite.
- **D-12:** **Plan flow is tested for real at minimum horizon:** a real `/api/plan` solve on the frozen pool at 2 GWs (a few seconds) with a generous per-test timeout — the flow, wait copy, and per-week rendering are exercised in-browser. Skipping the plan flow and full-horizon solves were both rejected.
- **D-13:** **Chromium only.** The regressions this suite hunts (contract drift, sort semantics, solver flows) are engine-independent; WebKit/Firefox are addable later as Playwright projects without rewriting tests.
- **D-14:** **Viewports:** standard desktop (e.g. 1280×720) for the flow suites; a dedicated **1720px spec for G-01-3** (header inner wrapper ≤1088px, horizontally centered, x-range matching `<main>`'s content box — per the Phase 1 handoff); **phone-width specs (e.g. 390px) for the team/pitch page** asserting Phase 3's D-07 promise — full formation plus bench fit the viewport with no horizontal overflow.
- **D-15:** **Exact expected values are hardcoded literals** hand-derived once from the immutable v1 fixtures (cell strings, row order). Re-deriving expectations from fixture JSON at test time was rejected — it re-implements the formatting logic under test, so a shared bug would pass silently.
- **D-16:** **Geometry via `boundingBox()` assertions, no screenshot baselines.** Pitch layout is guarded the G-01-3 way: row-centering symmetry (the G-03-1 class of bug), cards within viewport at phone width, bench alignment. Screenshot testing was rejected for environment flake (WSL2 local vs CI runners, font rendering).

### Claude's Discretion

- Exact env-var name(s) and internal design of the fixture seam in `api/main.py`; how the frozen pool is loaded (parquet vs JSON) and where it hooks into pool-building.
- Directory layout and naming under `e2e/` (or `frontend/e2e/`), spec file organization, and npm script names.
- The blank/DGW synthesis script's language and location.
- Exact viewport pixel choices beyond the mandated 1720px; per-test timeout values; retry policy.
- Whether dark-mode gets an E2E spot-check (not discussed; Vitest covers the toggle).

### Deferred Ideas (OUT OF SCOPE)

- **WebKit/Firefox engine coverage** — revisit as a pre-launch pass (FPL managers are phone-heavy → iOS/WebKit); addable as Playwright projects without rewriting tests.
- **Screenshot/visual-regression baselines** — reconsider only if geometry assertions prove insufficient; would need a docker-normalized environment (Phase 5+).
- **Keyed-auth E2E spot-check** — belongs with the Supabase JWT milestone (PAID-02), when the frontend actually sends keys.
- **Schema drift guard** (pytest comparing export-builder output keys against frozen fixture keys) — nice-to-have hardening; fits Phase 6's validation work if wanted.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| E2E-01 | Fixture strategy — frozen versioned JSON snapshots (normal, blank, double GW) and mocked FPL API; no live-data dependence | Architecture Patterns (fixture seam, dual static mounts, versioned fixture dirs); the G-01-3 1720px geometry spec (Phase 1 handoff) is scoped here as infra-adjacent shell coverage |
| E2E-02 | Team/pitch + solver flow regression test | Architecture Patterns (real `/api/solve`/`/api/plan` over frozen pool); Code Examples (invariant + golden assertions); Common Pitfalls (`_fetch_team` network call sites, ILP timing) |
| E2E-03 | xP table + captains rendering/sorting regression test | Code Examples (exact-cell-value assertions per D-15); existing `XpTable.tsx`/`aria-label` structure documented below for locator strategy |
| E2E-04 | Rate-my-team flow regression test | `RateTab.tsx`/`RateDiff.tsx` structure documented below; real `/api/rate/{entry}` over the frozen pool |
| E2E-05 | Fixtures and prices pages regression tests | `Fixtures.tsx`/`Prices.tsx` structure documented below (no sort, no interactive cells — simpler locator strategy than E2E-03) |

</phase_requirements>

## Summary

This phase builds a Node `@playwright/test` suite that drives the real FastAPI+React stack — not jsdom, not a mocked API — through a new fixture-mode seam in `api/main.py`. The single hardest technical problem is **not** Playwright itself (it is a mature, well-documented tool at v1.62.1) but the **two production-shaped changes the fixture seam forces on `api/main.py`**, both verified this session by reading the file directly: (1) every one of `api/main.py`'s outbound-network call sites (`_load_live`'s indirect `fetch_fpl_live`, plus `_fetch_team`'s two `requests.get` calls and `_free_transfers`'s one) must independently branch on the fixture env var — patching just `_load_live` leaves three live network calls active; and (2) switching the static mount from `web/` to `frontend/dist` (D-02) turns a same-directory `/` + `/data` layout into two directories that must be served by **two separate mounts**, and introduces a genuine SPA deep-link problem (`GET /team` 404s against a built React app) that vanilla never had, because vanilla is a classic multi-page site with a real `team.html` file per route.

Both problems have small, low-risk, verified-workable solutions: read-branch every call site behind one env var (mirroring `tests/conftest.py`'s existing `_reset_api_state` precedent, generalized from test-time monkeypatching to a real runtime branch), split the static mount into `app.mount("/data", ...)` + `app.mount("/", ...)`, and fix the SPA 404 by shipping a `dist/404.html` that is a byte-copy of `dist/index.html` — confirmed by reading the installed Starlette `StaticFiles.get_response` source directly: `html=True` mode already checks for and serves `404.html` automatically for any unmatched path, so no custom middleware or catch-all route is needed.

**Primary recommendation:** Build the fixture seam as data-loading + dual-mount branches only (no new routing logic), keep the E2E harness in a repo-root `e2e/` directory with its own `package.json` (isolated from Vitest's default file-discovery glob), and drive everything through Playwright's `webServer` config chaining `npm --prefix frontend run build && uvicorn api.main:app --port 8000` with `FPL_FIXTURE_DIR` set in `env`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fixture-backed FPL-upstream data loading (`_load_live`, `_fetch_team`, `_free_transfers`) | API / Backend | Database / Storage (frozen JSON on disk) | `api/main.py` branches on `FPL_FIXTURE_DIR` and reads committed JSON instead of calling `fantasy.premierleague.com` |
| Frozen prediction pool (no model inference at test time, D-10) | API / Backend | Database / Storage (frozen parquet/JSON) | `_pool`/`_gw_pools` bypass `build_pool`/`build_horizon_pool` + `joblib.load` entirely in fixture mode |
| SPA static serving + client-route fallback | CDN / Static (build artifact) | API / Backend (mount config) | `dist/404.html` is a build-time artifact; the dual-mount split that makes it reachable lives in `api/main.py` |
| Team/pitch + solver flow assertions (E2E-02) | Browser / Client | API / Backend | Playwright drives real UI interaction; the solve itself is a real `/api/solve` ILP run |
| xP table / captains sort+format assertions (E2E-03) | Browser / Client | — | Pure rendering/sort correctness against a frozen, already-fetched JSON file — no solver involvement |
| Rate-my-team flow assertions (E2E-04) | Browser / Client | API / Backend | Real `/api/rate/{entry}` call against the frozen pool |
| Fixtures / Prices page assertions (E2E-05) | Browser / Client | — | Static JSON rendering, no solver, no sort (neither page is sortable — verified in both route files) |
| 1720px header-containment geometry (G-01-3 handoff) | Browser / Client | — | Requires a real layout engine; jsdom (Vitest) cannot measure `boundingBox()` |
| Test/build orchestration (`webServer` lifecycle) | API / Backend | CDN / Static | Playwright's `webServer.command` runs the frontend build, then starts uvicorn — both tiers, one process lifecycle |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@playwright/test` | 1.62.1 [VERIFIED: npm registry] | Node E2E test runner, browser automation, `webServer` orchestration | Explicitly mandated by this phase's research flag (`pytest.ini`'s `-p no:playwright` blocks the Python plugin over a `--browser` flag collision with `seleniumbase`); Microsoft-maintained, 58.3M weekly downloads, no postinstall script flagged |

No other core runtime dependency is required — `@playwright/test` bundles the `playwright` browser-automation core as its own dependency; installing it alone is sufficient (confirmed: `npm view playwright version` and `npm view @playwright/test version` both resolve to `1.62.1`, same release train).

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| none | — | Blank/DGW fixture synthesis script | This repo's convention for small, dependency-free tooling scripts is a plain Node script using only `node:fs`/`node:path` (see `frontend/scripts/check-tokens.mjs`, read this session) — the synthesis script should follow the same zero-dependency pattern rather than pulling in a JSON-transform library |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@playwright/test` | `pytest-playwright` | Rejected by the phase's own research flag — collides with `-p no:seleniumbase`/`-p no:playwright` in `pytest.ini` (read this session, confirmed the exact `--browser` flag collision comment) |
| Real backend (D-01) | Playwright `page.route()` API mocking | Rejected in CONTEXT.md D-01 — leaves the React↔FastAPI wire contract browser-untested, which is the whole point of an E2E suite over the existing Vitest fetch-mock coverage |
| Chromium only (D-13) | Cypress, or a multi-engine Playwright matrix now | Not evaluated — D-13 locks Chromium-only for this phase; WebKit/Firefox are explicitly deferred, addable later as Playwright `projects` entries without a rewrite |

**Installation:**
```bash
# From a new e2e/ package.json (recommended layout, see Architecture Patterns)
cd e2e
npm install --save-exact --save-dev @playwright/test@1.62.1
npx playwright install chromium   # browser binary not yet cached in this environment (see Environment Availability)
```

**Version verification:** `npm view @playwright/test version` → `1.62.1`, matching `npm view playwright version` → `1.62.1` (same release), verified live against the npm registry this session (2026-09-03).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `@playwright/test` | npm | published 2026-07-30 (this release; project itself is years old) | 58,362,881/wk | github.com/microsoft/playwright | OK | Approved |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

No other new npm packages are required by this research. If the planner elects to write the fixture-synthesis script in TypeScript rather than plain JS, `tsx` or `ts-node` would need this same gate run against them before install — the recommendation above (plain Node script, zero deps) avoids that entirely.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │  Playwright webServer (D-05, one process) │
                         │  npm --prefix frontend run build           │
                         │    && uvicorn api.main:app --port 8000    │
                         │  env: FPL_FIXTURE_DIR=e2e/fixtures/v1/normal │
                         └───────────────────┬─────────────────────┘
                                              │ spawns
                                              ▼
                         ┌─────────────────────────────────────────┐
                         │  uvicorn / FastAPI (api/main.py)          │
                         │                                           │
  GET /              ──▶│  app.mount("/",  dist/,  html=True) ─┐    │
  GET /team?entry=…  ──▶│      (404 on unmatched path falls    │    │
                         │       back to dist/404.html == index) │    │
                         │                                       ▼    │
                         │  GET /data/*.json                          │
  fetch("/data/…")   ──▶│      app.mount("/data", <fixture>/web-data/)│
                         │                                           │
  POST /api/solve    ──▶│  _pool()/_gw_pools() ── FPL_FIXTURE_DIR? ──┼─▶ frozen pool (parquet/JSON)
  GET  /api/rate/…   ──▶│                                            │      no joblib.load (D-10)
  GET  /api/team/…   ──▶│  _fetch_team()/_free_transfers() ── FPL_FIXTURE_DIR? ─▶ entry_6980093_*.json
  GET  /api/health,  ──▶│  _refresh() → _load_live() ── FPL_FIXTURE_DIR? ─────▶ bootstrap-static.json,
       /api/meta          (real optimize/squad_ilp.py + optimize/transfers.py    fixtures.json (D-07)
                            ILP still runs — only the INPUT is frozen, D-10/D-11) │
                         └─────────────────────────────────────────┘
                                              ▲
                                              │ real browser navigation + assertions
                         ┌─────────────────────────────────────────┐
                         │  Chromium (Playwright, D-13)              │
                         │  e2e/specs/*.spec.ts                      │
                         │   - shell-geometry.spec.ts (G-01-3, 1720px)│
                         │   - team-solver.spec.ts     (E2E-02)       │
                         │   - xp-table.spec.ts        (E2E-03)       │
                         │   - rate-my-team.spec.ts    (E2E-04)       │
                         │   - fixtures-prices.spec.ts (E2E-05)       │
                         └─────────────────────────────────────────┘
```

### Recommended Project Structure

```
e2e/                                # repo-root, sibling to frontend/ api/ tests/ — NOT under frontend/
├── package.json                    # own @playwright/test devDependency, isolated from Vitest's glob
├── playwright.config.ts            # webServer (D-05), projects: [{ name: "chromium", use: devices["Desktop Chrome"] }]
├── tsconfig.json                   # standalone, no dependency on frontend/tsconfig.*
├── specs/
│   ├── shell-geometry.spec.ts      # E2E-01 infra: G-01-3 1720px header containment
│   ├── team-solver.spec.ts         # E2E-02
│   ├── xp-table.spec.ts            # E2E-03
│   ├── rate-my-team.spec.ts        # E2E-04
│   └── fixtures-prices.spec.ts     # E2E-05
├── fixtures/
│   └── v1/
│       ├── MANIFEST.md             # D-08: capture date, GW, source, synthesis rules
│       ├── normal/
│       │   ├── api/
│       │   │   ├── bootstrap-static.json      # trimmed to fields _load_live/_gw_pool actually read
│       │   │   ├── fixtures.json
│       │   │   ├── pool.parquet               # D-10: the frozen prediction pool (build_pool's own output shape)
│       │   │   ├── entry_6980093_picks.json    # D-07
│       │   │   ├── entry_6980093_summary.json
│       │   │   └── entry_6980093_history.json
│       │   └── web-data/           # mirrors web/data/*.json — mounted at /data in fixture mode
│       │       ├── meta.json  xp_table.json  captains.json  squad.json
│       │       ├── fixtures.json  chips.json  standings.json  leaders.json  watchlist.json
│       ├── blank/                  # D-09: same shape, synthesized (blank-GW subset of clubs)
│       └── dgw/                    # D-09: same shape, synthesized (double-GW subset of clubs)
└── scripts/
    └── synthesize-variants.mjs     # D-06: normal -> blank/dgw, zero-dependency (repo convention)
```

**Why `e2e/` at repo root, not `frontend/e2e/`:** `frontend/vitest.config.ts` (read this session) has no `test.include` override, so Vitest's default discovery glob (`**/*.{test,spec}.*`) would recursively pick up any `.spec.ts` file placed inside `frontend/`, including a `frontend/e2e/*.spec.ts` directory — `npm --prefix frontend run test` already runs `vitest run` with no path scoping (`package.json`'s `"test": "node scripts/check-tokens.mjs && vitest run"`, read this session). Playwright's `test`/`expect` globals would collide with Vitest's own auto-injected globals (`vitest.config.ts` sets `globals: true`). A repo-root `e2e/` directory with its own `package.json` avoids this entirely without touching `vitest.config.ts`, and mirrors the existing multi-stack layout (`tests/` for pytest, `frontend/src` for Vitest, now `e2e/` for Playwright).

### Pattern 1: Fixture-mode data-loading branch in `api/main.py`

**What:** Every outbound-network call site in `api/main.py` branches on `FPL_FIXTURE_DIR` to read committed JSON instead of calling the live FPL API.
**When to use:** All of E2E-01 through E2E-05 — every test in the suite depends on this seam existing.
**Verified call sites (read `api/main.py` in full this session):**

| Function | Line(s) | What it currently does |
|----------|---------|-------------------------|
| `_refresh()` → `_load_live()` (imported from `predict/live.py`) | `api/main.py:41-42` (import), `:73` (call) | `predict.live._load_live()` calls `fetch_fpl_live(force=True)` (`data/ingest.py:78-92`, read this session) which **unconditionally downloads** `bootstrap-static.json`/`fixtures.json` from `fantasy.premierleague.com` before ever reading the cached copy — patching only the return value after the fact does not stop the network call |
| `_fetch_team()` | `api/main.py:174-209` | `requests.get(f"{config.FPL_API}/entry/{entry}/event/{gw-1}/picks/")` (line 175) and `requests.get(f"{config.FPL_API}/entry/{entry}/")` (line 185, best-effort manager summary) |
| `_free_transfers()` | `api/main.py:156-164` | `requests.get(f"{config.FPL_API}/entry/{entry}/history/")` (line 158) |
| `_state["artifact"]` cold-start | `api/main.py:70-72` | `joblib.load(config.ROOT / "models" / "artifacts" / "xp_model.joblib")` — that file is untracked and **absent on a clean checkout** (confirmed by `tests/conftest.py`'s own comment, read this session); D-10 requires this never runs in fixture mode |
| `_pool()` / `_gw_pools()` | `api/main.py:85-111` | Calls `build_pool`/`build_horizon_pool`/`_gw_pool` (from `predict/live.py`), which run the real LightGBM `predict_xp()` over the artifact — D-10 requires fixture mode to load a pre-computed pool DataFrame instead |

**Example (proposed skeleton — not existing code; every referenced line number above is verified, this composition is a design proposal for the planner):**
```python
# api/main.py — near the top, after imports
_FIXTURE_DIR = os.environ.get("FPL_FIXTURE_DIR")

def _load_live_fixture(force: bool = True):
    d = Path(_FIXTURE_DIR) / "api"
    return (json.load(open(d / "bootstrap-static.json")),
            json.load(open(d / "fixtures.json")))

if _FIXTURE_DIR:
    _load_live = _load_live_fixture      # shadows the name imported from predict.live

def _fetch_team(entry: int, gw: int, boot: dict) -> dict:
    if _FIXTURE_DIR:
        return _fetch_team_fixture(entry, gw, boot)   # reads entry_6980093_*.json; 404s any other entry
    # ... existing requests.get logic unchanged

def _free_transfers(entry: int, next_gw: int) -> int | None:
    if _FIXTURE_DIR:
        return _free_transfers_fixture(entry, next_gw)  # reads entry_6980093_history.json
    # ... existing requests.get logic unchanged

def _refresh(force: bool = False) -> None:
    with _lock:
        stale = time.time() - _state["loaded_at"] > POOL_TTL_S
        if not (force or stale or _state["boot"] is None):
            return
        if _state["artifact"] is None:
            _state["artifact"] = "fixture" if _FIXTURE_DIR else joblib.load(...)  # D-10: no real load
        boot, fixtures = _load_live()
        _state.update(boot=boot, fixtures=fixtures, gw=_next_gw(boot), pools={}, loaded_at=time.time())
        _solve_cache.clear()

def _pool(horizon: int = 1):
    _refresh()
    with _lock:
        key = horizon
        if key not in _state["pools"]:
            if _FIXTURE_DIR:
                pool = pd.read_parquet(Path(_FIXTURE_DIR) / "api" / "pool.parquet")  # D-10
            else:
                build = build_horizon_pool if horizon > 1 else build_pool
                pool = build(_state["boot"], _state["fixtures"], _state["gw"], _state["artifact"], *([horizon] if horizon > 1 else []))
            _state["pools"][key] = _with_bands(pool)
        return _state["pools"][key], _state["gw"], _state["boot"]
```
This composition directly mirrors `tests/conftest.py`'s existing `_reset_api_state` autouse-fixture precedent (read this session) — seeding a non-`None` artifact sentinel *before* `_refresh()` reaches the `joblib.load` cold-start branch — generalized from "reset before each pytest test" to "branch for the lifetime of a fixture-mode uvicorn process."

### Pattern 2: SPA static serving with client-route fallback (D-02)

**What:** Splitting the single production `StaticFiles` mount into two mounts, and shipping a `404.html` copy of `index.html` so direct navigation to a client-side route (`/team?entry=…&tab=rate`) does not 404.
**When to use:** Required for every E2E-02 through E2E-05 test that navigates directly to a route via `page.goto()` rather than clicking through the nav — which D-11's deep-link testing (`?entry=`/`?tab=` per Phase 3's D-11) explicitly requires.

**Verified root cause (read the installed `starlette==1.0.0` source this session, `StaticFiles.get_response`):**
```python
# starlette/staticfiles.py (installed copy, read in full this session)
if stat_result and stat.S_ISREG(stat_result.st_mode):
    return self.file_response(full_path, stat_result, scope)
elif stat_result and stat.S_ISDIR(...) and self.html:
    ...  # index.html for directory URLs only
if self.html:
    # Check for '404.html' if we're in HTML mode.
    full_path, stat_result = await anyio.to_thread.run_sync(self.lookup_path, "404.html")
    if stat_result and stat.S_ISREG(stat_result.st_mode):
        return FileResponse(full_path, stat_result=stat_result, status_code=404)
raise HTTPException(status_code=404)
```
`StaticFiles(html=True)` **already implements** "serve `404.html` for any unmatched path" — no custom middleware, no catch-all route, no subclass is needed. A request for `/team` (not a real file/directory under `dist/`) falls straight through to this branch.

**Why vanilla (`web/`) never had this problem:** vanilla is a classic multi-page site — `web/team.html` is a real file, so `GET /team...` was never a missing path in production mode. This SPA-fallback need is created *by* D-02's dist-mode switch, not by anything already in the codebase.

**Why `/data/*.json` also needs its own mount in fixture/dist mode:** in production, `web/data/meta.json` is served by the *same* mount as `web/index.html` because they share a parent directory (`web/`), confirmed by `frontend/vite.config.ts`'s own comment (read this session: *"api/main.py mounts StaticFiles(directory=config.ROOT / 'web') at '/', so a file at web/data/meta.json is served at GET /data/meta.json"*). `frontend/dist/` (read this session: contains only `index.html`, `favicon.svg`, `assets/`) has **no `data/` subfolder** — Vite's build never produces one, since `web/data/*.json` is fetched at runtime, never bundled (per this project's own established invariant, restated in CONTEXT.md's Established Patterns). Fixture mode therefore needs a **second, independent mount** for `/data` pointed at the fixture's `web-data/` directory, registered before the catch-all `/` mount so `/data/*` requests resolve there and never fall through to the SPA's `404.html`-serves-`index.html` behavior (which would otherwise return HTML for a JSON fetch and break every page).

**Example:**
```python
# frontend/package.json — add a postbuild hook (npm auto-runs any "post<script>" after "<script>")
"scripts": {
  "build": "tsc -b && vite build",
  "postbuild": "cp dist/index.html dist/404.html"
}
```
```python
# api/main.py — replaces the single mount at the bottom of the file (line 410, read this session)
if _FIXTURE_DIR:
    site_dir = config.ROOT / "frontend" / "dist"
    data_dir = Path(_FIXTURE_DIR) / "web-data"
else:
    site_dir = config.ROOT / "web"
    data_dir = config.ROOT / "web" / "data"

app.mount("/data", StaticFiles(directory=data_dir), name="data")
app.mount("/", StaticFiles(directory=site_dir, html=True), name="site")
```
Registering `/data` **before** the catch-all `/` mount is required — Starlette matches mounted routes in registration order, and the more general `/` mount is already last in the file today.

### Pattern 3: Playwright `webServer` config (D-05)

**What:** A single `playwright.config.ts` that owns the full server lifecycle — build the frontend, start uvicorn with the fixture env var, wait for a health URL, and reuse the server across a local `--ui` run.
**Verified via Playwright's own documentation this session (playwright.dev/docs/test-webserver):** `command` accepts a shell string chained with `&&`; `reuseExistingServer: !process.env.CI` is the documented idiom for "reuse locally, always start fresh on CI" (matches D-05's "reuse locally, strict in CI" requirement exactly); `timeout` is configurable per-server for slow boot commands (the frontend build step is the slow part here).

```typescript
// e2e/playwright.config.ts
import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

export default defineConfig({
  testDir: "./specs",
  timeout: 30_000,           // per-test default; team-solver.spec.ts overrides for D-12's plan-flow test
  use: { baseURL: "http://localhost:8000" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],  // D-13
  webServer: {
    command: "npm --prefix ../frontend run build && " +
             "uvicorn api.main:app --app-dir ../ --port 8000",
    url: "http://localhost:8000/api/health",
    timeout: 120_000,        // frontend build + uvicorn boot
    reuseExistingServer: !process.env.CI,
    env: {
      FPL_FIXTURE_DIR: path.resolve(__dirname, "fixtures/v1/normal"),
    },
  },
});
```
A test that needs the `blank`/`dgw` fixture set (D-09) instead of `normal` cannot simply pass a different env var per-test — Playwright's `webServer` starts once for the whole run. Two documented options exist: (a) a second `playwright.config.ts`/`webServer` entry pointed at a second port for the targeted blank/DGW specs (Playwright supports an array of `webServer` configs, confirmed via the same doc search), or (b) a project-level `testMatch` + a separate `npx playwright test --config` invocation. Flagged as an **Open Question** below — the CONTEXT.md discretion note ("exact directory layout... is planner's") does not resolve which of these two the plan should pick.

### Anti-Patterns to Avoid

- **Reaching for `unittest.mock`/`responses` in `api/main.py` itself:** those work inside a pytest process via `monkeypatch`; a real `uvicorn` process serving live Playwright traffic has no pytest harness to install them in. Use plain `if _FIXTURE_DIR:` branches reading from disk (Pattern 1).
- **A custom Starlette `StaticFiles` subclass or catch-all `@app.get("/{path:path}")` route for the SPA fallback:** unnecessary — `html=True` already implements the exact `404.html` fallback needed (Pattern 2, verified from the installed source).
- **`page.waitForTimeout()` sleeps** to wait for a solve to finish or data to load: Playwright's locator assertions (`expect(...).toHaveText(...)`, `page.waitForResponse(...)`) already auto-retry with sane defaults; a fixed sleep is either too short (flaky) or wastes CI time (too long).
- **Pointing `webServer.command` at `vite dev`** for local convenience: D-03 explicitly forbids an `E2E_DEV` variant — the whole point of the fixture seam is that local and CI runs are topologically identical.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SPA deep-link 404 on direct navigation | Custom Starlette middleware or a hand-written catch-all route that decides "asset vs. page" | `dist/404.html` = copy of `dist/index.html`, served automatically by `StaticFiles(html=True)`'s existing fallback branch | Verified this session by reading the installed Starlette source — the feature already exists and needs zero new routing code |
| Waiting for the browser to finish loading web fonts before measuring `boundingBox()` | A fixed `page.waitForTimeout(500)` before every geometry assertion | `page.evaluate(() => document.fonts.ready)` or Playwright's own load-state waits, once, in a shared helper | `@fontsource/*` packages (confirmed installed in `frontend/package.json`, read this session) load asynchronously; card/header widths depend on the loaded font metrics — a fixed sleep is exactly the "pass or fail on the calendar" anti-pattern this phase's own north star rejects |
| Frozen prediction pool storage format | A bespoke JSON schema for the pool | `pandas.DataFrame.to_parquet`/`read_parquet` — the same format the rest of the pipeline already uses for `data/processed/*.parquet` (confirmed via `config.py`'s `PROCESSED_DIR` convention, read this session) | Keeps the fixture format consistent with the pipeline's own conventions; `build_pool`'s output columns (`player_code, name, team, position, price_m, xp, xp_capt, actual`, verified by reading `predict/live.py`) drop straight into parquet with no custom serializer |
| Blank/DGW fixture variants | Three independently hand-authored JSON fixture sets | One deterministic transform script off the "normal" capture (D-06) | Guarantees all three scenarios share the same real player names/prices (debuggability requirement, per CONTEXT.md's Specific Ideas) and only fixture-count-per-team differs — hand-authoring three sets risks silent drift between them |

**Key insight:** every "hand-roll" temptation in this phase (SPA routing, HTTP mocking, wait-for-ready polling) has an existing, already-verified-present mechanism in the stack (Starlette's `404.html`, Playwright's auto-waiting locators, `pandas.to_parquet`) — the phase's job is composition and correct sequencing, not new infrastructure.

## Common Pitfalls

### Pitfall 1: Patching `_load_live` alone leaves three live network calls active
**What goes wrong:** A fixture seam that only intercepts `api.main._load_live` (the pattern `tests/test_api.py` already uses via `monkeypatch.setattr`) still lets `_fetch_team()`'s two `requests.get` calls and `_free_transfers()`'s one `requests.get` call reach `fantasy.premierleague.com` for real during an E2E run.
**Why it happens:** `test_api.py`'s existing pytest tests patch each function independently per test (`monkeypatch.setattr(m, "_pool", ...)`, separate `responses.add(...)` calls for team/rate tests) — that per-test granularity is invisible when designing "one env var" for a always-on runtime seam; it is easy to port only the most obviously-named function (`_load_live`) and miss the other three call sites.
**How to avoid:** Enumerate all four call sites explicitly (table in Pattern 1) and branch every one.
**Warning signs:** A team/rate/solve E2E test passes locally (network available) but fails in a network-isolated CI runner, or — worse — silently succeeds against real, non-deterministic live FPL data, defeating "pass or fail on code, never on the calendar."

### Pitfall 2: `app.frontend()` does not exist on this project's pinned FastAPI
**What goes wrong:** A community blog post surfaced during research claims FastAPI has "native SPA support" via `app.frontend()`, replacing the manual `StaticFiles(html=True)` + fallback pattern.
**Why it happens:** Blog content about upcoming/unreleased framework features is easy to mistake for shipped behavior.
**How to avoid:** Verified this session — `hasattr(fastapi.FastAPI, "frontend")` returns `False` on the actual installed/pinned `fastapi==0.136.1` (this project's `requirements.txt` pins `fastapi>=0.110`). Use Pattern 2's manual `404.html` approach instead; do not spend planning time investigating `app.frontend()`.
**Warning signs:** none yet observed in this codebase — flagging preemptively so the planner doesn't chase this dead end.

### Pitfall 3: `models/artifacts/xp_model.joblib` crashes a clean checkout
**What goes wrong:** `_refresh()`'s cold-start branch (`if _state["artifact"] is None: _state["artifact"] = joblib.load(...)`) runs `joblib.load` unconditionally the first time any endpoint is hit, and that file is gitignored (`models/artifacts/` is in `.gitignore`, read this session) and absent on a clean CI checkout.
**Why it happens:** The existing pytest precedent (`tests/conftest.py`'s `_reset_api_state`) already works around this by seeding `m._state["artifact"] = object()` before every test — but that is test-harness code that does not run in a real `uvicorn` process.
**How to avoid:** The fixture-mode branch in `_refresh()` must set a non-`None` artifact sentinel *before* the `joblib.load` line is ever reached (shown in Pattern 1's example).
**Warning signs:** `FileNotFoundError` on the very first request to any endpoint in a fresh CI checkout.

### Pitfall 4: Pool/solve cache persists across the whole Playwright run, not per-test
**What goes wrong:** Unlike pytest's `_reset_api_state` autouse fixture (which resets `_state`/`_solve_cache` before and after every single test), a Playwright `webServer` process stays alive for the entire test run — `_state["pools"]` and `_solve_cache` accumulate across every spec file.
**Why it happens:** This is a fundamentally different process lifecycle than the pytest suite the seam is modeled on.
**How to avoid:** This is largely benign for fixture mode specifically — the frozen pool never changes mid-run, so a cached pool is still correct data. The one thing to verify: solve requests with different `locks`/`excludes`/`horizon` combinations across different spec files hash to different `_solve_cache` keys (confirmed: the cache key is `sha1(json.dumps({"gw": gw, **req.model_dump()}, ...))`, read `api/main.py:284-287` this session) — different request bodies never collide.
**Warning signs:** A solve test asserting a specific result unexpectedly gets a *different* test's cached response — would indicate two tests sending byte-identical request bodies, which the golden-solve test (D-11) should catch immediately if it happens.

### Pitfall 5: Real personal data (entry 6980093) becomes a permanent git record
**What goes wrong:** `tests/test_api.py`'s own comment (read this session) states: *"Synthetic fixture identities only ... never a real FPL manager's name, team, rank, or entry id — these endpoints return third-party personal data and a committed fixture is a permanent public record."* CONTEXT.md's D-07/Specifics explicitly choose to capture the real entry 6980093 (the project owner's own team) for E2E fixtures, including its manager sub-object (`team_name`, `manager` name, `overall_points`, `overall_rank`).
**Why it happens:** The two decisions are not actually in conflict — 6980093 is the *project owner's own* team, captured by their own choice, not a third party's — but the pytest precedent's wording ("never a real ... entry id") reads as an absolute rule that this phase deliberately overrides for one specific, owner-consented entry.
**How to avoid:** Flagged as an **Open Question** below rather than resolved here — confirm before capture whether the `manager` sub-object's real name fields should be captured verbatim or scrubbed even though the entry itself is intentionally real.
**Warning signs:** none — this is a policy question, not a code defect.

### Pitfall 6: `boundingBox()` geometry assertions racing web-font loading
**What goes wrong:** D-16's `boundingBox()` assertions (header containment, pitch row centering) can read pre-font-swap layout metrics if measured before `@fontsource/*` webfonts finish loading, producing flaky width/position numbers.
**How to avoid:** Await `document.fonts.ready` (via `page.evaluate`) once per test, before any `boundingBox()` call, in a shared test helper.
**Warning signs:** A geometry test that fails intermittently only on a cold cache / first run in a spec file, and passes on retry.

### Pitfall 7: `/api/plan`'s real multi-GW solve needs a bumped per-test timeout
**What goes wrong:** D-12 requires a real `/api/plan` solve at horizon=2 ("a few seconds") in-browser; Playwright's default test timeout (30s, per the `playwright.config.ts` example above) is probably enough headroom on a healthy machine but PuLP/CBC startup plus two sequential GW solves on a loaded CI runner is a plausible source of an occasional slow run.
**How to avoid:** `test.setTimeout(60_000)` (or similar) on the specific plan-flow test, not a global config bump that masks genuinely-hung other tests.
**Warning signs:** An intermittent timeout specifically on the plan-flow spec, never on the single-GW solve specs.

### Pitfall 8: `npx playwright install chromium` needs network access and is not yet cached
**What goes wrong:** This environment's Playwright browser cache (`~/.cache/ms-playwright/`, checked this session) contains only a stray `webkit-2248` directory — no Chromium binary. D-13 mandates Chromium; the install step needs to succeed before any spec can run.
**How to avoid:** Include `npx playwright install chromium` (or `--with-deps chromium` for a from-scratch Linux/WSL2 host, which also installs the OS-level shared libraries Chromium needs) as an explicit Wave 0 setup step, not an assumed pre-existing condition.
**Warning signs:** `browserType.launch: Executable doesn't exist` on the very first spec run.

## Code Examples

### G-01-3 1720px header-containment geometry assertion

```typescript
// Source: composed from api/main.py-verified DOM structure (frontend/src/components/PageShell.tsx,
// read this session) + the exact three assertions specified in
// .planning/phases/01-test-base-layer-app-skeleton/deferred-items.md (read this session)
import { test, expect } from "@playwright/test";

test("header inner wrapper stays contained at 1720px (G-01-3)", async ({ page }) => {
  await page.setViewportSize({ width: 1720, height: 900 });
  await page.goto("/");
  await page.evaluate(() => document.fonts.ready);   // Pitfall 6

  // PageShell.tsx: <header><div class="mx-auto w-full max-w-[68rem] ... px-4">
  const headerInner = page.locator("header > div").first();
  const main = page.locator("main");

  const headerBox = await headerInner.boundingBox();
  const mainBox = await main.boundingBox();
  if (!headerBox || !mainBox) throw new Error("expected boxes, got null");

  expect(headerBox.width).toBeLessThanOrEqual(1088);                 // 68rem
  const viewportCenter = 1720 / 2;
  const headerCenter = headerBox.x + headerBox.width / 2;
  expect(Math.abs(headerCenter - viewportCenter)).toBeLessThan(1);   // horizontally centered
  expect(headerBox.x).toBeCloseTo(mainBox.x, 0);                     // shares <main>'s x-range
  expect(headerBox.x + headerBox.width).toBeCloseTo(mainBox.x + mainBox.width, 0);
});
```

### Solve-flow invariants + one pinned golden (D-11)

```typescript
// Source: composed from api/main.py's SolveRequest/response shape (read this session,
// api/main.py:235-330) and config.py's FPL rule constants (read this session)
import { test, expect } from "@playwright/test";

const BUDGET = 100.0;             // config.py:23, verified
const QUOTA = { GK: 2, DEF: 5, MID: 5, FWD: 3 };  // config.py:24, verified

test("team solve produces a legal squad honouring locks", async ({ page, request }) => {
  await page.goto("/team?entry=6980093");
  // ... UI interaction to lock a player, click "Solve transfers" ...

  const res = await page.waitForResponse((r) => r.url().includes("/api/solve") && r.status() === 200);
  const body = await res.json();

  expect(body.squad).toHaveLength(15);
  expect(body.squad.filter((p: any) => p.starting)).toHaveLength(11);
  expect(body.squad.filter((p: any) => p.captain)).toHaveLength(1);
  const byPos: Record<string, number> = {};
  for (const p of body.squad) byPos[p.position] = (byPos[p.position] ?? 0) + 1;
  expect(byPos).toEqual(QUOTA);
  expect(body.squad.reduce((s: number, p: any) => s + p.price_m, 0)).toBeLessThanOrEqual(BUDGET);
});

test("golden: canonical solve on the frozen pool pins exact XI (D-11)", async ({ page }) => {
  // One specific, hand-derived request against e2e/fixtures/v1/normal's frozen pool —
  // exact player names/codes hardcoded per D-15, re-pinned only if this one test needs it.
  // ... (values filled in once the fixture capture exists — flagged in Open Questions)
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `pytest-playwright` for Python-driven browser tests | Node `@playwright/test` for this repo, specifically | This phase (forced by `pytest.ini`'s pre-existing plugin collision, not a general industry shift) | Test authors write specs in TypeScript, not Python — a genuinely different stack from the rest of this repo's test suites |
| Manual visual QA for pixel-geometry regressions (G-01-3 was only human-verified in Phase 1 UAT) | Automated `boundingBox()` assertions in a real browser | This phase | Closes the exact gap Phase 1 explicitly deferred (jsdom has no layout engine) |

**Deprecated/outdated:** `app.frontend()` as a solution for SPA fallback — not deprecated so much as never-existed on this project's pinned FastAPI version (Pitfall 2); do not adopt even if a newer FastAPI release ships it, without re-verifying `hasattr` against whatever version is actually pinned at that time.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `e2e/` should live at repo root (not `frontend/e2e/`) to avoid Vitest's default glob picking up Playwright spec files | Architecture Patterns, Recommended Project Structure | Low — reversible; if the planner prefers `frontend/e2e/` instead, `vitest.config.ts` needs one added `test.include` line to scope Vitest to `src/**` |
| A2 | `dist/404.html` should be produced via an npm `postbuild` script hook (`cp dist/index.html dist/404.html`) | Architecture Patterns, Pattern 2 | Low — npm's `pre`/`post` script auto-run convention is extremely standard, but not verified against npm's own docs this session; if wrong, the copy step can just be folded into the `build` script directly (`tsc -b && vite build && cp dist/index.html dist/404.html`) |
| A3 | The frozen prediction pool should be stored as parquet (matching pipeline convention) rather than JSON | Don't Hand-Roll, Pattern 1 | Low — reversible; D-10/D-08 explicitly leave the storage format to the planner's discretion, this is only a recommendation |
| A4 | Two `webServer` config entries (or two `playwright.config.ts` files) are needed to serve the `blank`/`dgw` fixture sets alongside `normal` in the same test run | Pattern 3 | Medium — if wrong, D-09's targeted blank/DGW specs cannot run in the same `npx playwright test` invocation as the five flow suites without a manual server restart; resolve during planning, not execution |
| A5 | Entry 6980093's `manager` sub-object (real name/team-name fields) should be captured verbatim into the committed fixture, matching D-07's literal instruction, despite `tests/test_api.py`'s adjacent "never a real manager's name" convention for *other* pytest fixtures | Common Pitfalls, Pitfall 5 | Medium — a privacy/data-hygiene question, not a technical one; needs explicit confirmation before the fixture-capture task runs, not a silent default either way |

## Open Questions

1. **How does the suite serve `blank`/`dgw` fixture sets in the same `npx playwright test` run as the `normal`-backed flow suites?**
   - What we know: D-09 requires targeted blank/DGW specs; Playwright's `webServer` config supports an array of server configs (confirmed via official docs this session), each bindable to its own port.
   - What's unclear: whether the planner should stand up two full uvicorn processes (one per fixture set, two ports) for the whole run, or scope blank/DGW specs to a separate `playwright.config.ts` invocation (`npx playwright test --config=playwright.blank.config.ts`) run as a second CI/local step.
   - Recommendation: the two-process (two-port) approach keeps `npx playwright test` as the single entry point per D-05; the two-invocation approach is simpler per-config but violates D-05's "single entry point" spirit. Flag this as a planning-time decision, not something to resolve in research.

2. **Should entry 6980093's real manager name/team-name be captured verbatim in the committed fixture, or scrubbed?**
   - What we know: D-07 explicitly names entry 6980093 as the real capture target; CONTEXT.md's Specific Ideas explains real names matter for debuggability; `tests/test_api.py`'s adjacent convention for *other, non-owner* pytest fixtures is strict synthetic-identity-only, citing "a committed fixture is a permanent public record."
   - What's unclear: whether that same "permanent public record" caution should still apply to the *manager sub-object's free-text name fields* specifically (as opposed to the entry ID, picks, and rank, which are already publicly visible via the official FPL site for any entry ID), even though the entry itself is the project owner's own, by their own explicit choice.
   - Recommendation: surface this as a confirm-before-capture checkpoint in the plan (e.g., a `checkpoint:human-verify` before the fixture-capture task commits the `entry_6980093_summary.json` file), rather than silently defaulting either way.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Playwright runtime | ✓ | v24.20.0 | — |
| npm | package installs | ✓ | 12.0.2 | — |
| `@playwright/test` | test runner | ✗ (not yet installed) | registry: 1.62.1 | install during Wave 0, no fallback needed — install is fast |
| Chromium browser binary | D-13 (Chromium-only) | ✗ (cache has only a stray `webkit-2248`) | — | `npx playwright install chromium` (or `--with-deps chromium` on a fresh Linux/WSL2 host) — requires network access at install time, no offline fallback |
| Python 3.14 / FastAPI / uvicorn | backend under test | ✓ | FastAPI 0.136.1, uvicorn 0.44.0 | — |
| PuLP / CBC solver | real ILP solves (D-11/D-12) | ✓ | PuLP 3.3.2, `PULP_CBC_CMD` available (`pulp.listSolvers(onlyAvailable=True)`) | — |
| Ports 8000 (uvicorn) / no Vite dev port needed (D-03: build-only) | `webServer` | ✓ (both free at research time) | — | — |

**Missing dependencies with no fallback:**
- Chromium browser binary — must be installed via `npx playwright install chromium` before any spec can run; this environment currently has network access confirmed (npm registry lookups succeeded this session), so this should resolve cleanly, but it is not yet done and has no offline fallback if the execution sandbox lacks network access at plan-execution time.

**Missing dependencies with fallback:**
- none — `@playwright/test` itself installs in seconds and has no meaningful fallback need.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `@playwright/test` 1.62.1 (not yet installed — this phase's own deliverable) |
| Config file | `e2e/playwright.config.ts` — none yet, Wave 0 |
| Quick run command | `npx playwright test --project=chromium <spec-file>` (from `e2e/`) |
| Full suite command | `npx playwright test` (from `e2e/`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| E2E-01 | Fixture-mode API/data seam behaves identically across runs; G-01-3 1720px geometry holds | e2e (infra) + e2e (geometry) | `npx playwright test specs/shell-geometry.spec.ts` | ❌ Wave 0 |
| E2E-02 | Team/pitch load → lock/exclude → solve → assert XI/transfers | e2e | `npx playwright test specs/team-solver.spec.ts` | ❌ Wave 0 |
| E2E-03 | xP table + captains: exact cell values, sort order | e2e | `npx playwright test specs/xp-table.spec.ts` | ❌ Wave 0 |
| E2E-04 | Rate-my-team: tiles, diff, best move | e2e | `npx playwright test specs/rate-my-team.spec.ts` | ❌ Wave 0 |
| E2E-05 | Fixtures ticker + prices watchlist rendering | e2e | `npx playwright test specs/fixtures-prices.spec.ts` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** the specific spec file(s) the task touches, e.g. `npx playwright test specs/team-solver.spec.ts`
- **Per wave merge:** `npx playwright test` (full suite, Chromium project only per D-13)
- **Phase gate:** full suite green before `/gsd-verify-work`, plus the manual confirm-before-capture checkpoint from Open Question 2 if not already resolved

### Wave 0 Gaps

- [ ] `e2e/package.json` + `e2e/playwright.config.ts` + `e2e/tsconfig.json` — no E2E harness exists yet
- [ ] `e2e/fixtures/v1/{normal,blank,dgw}/` + `MANIFEST.md` — no fixture capture exists yet
- [ ] `api/main.py`'s `FPL_FIXTURE_DIR` seam (Pattern 1) — the single production file this phase touches, per CONTEXT.md's code_context
- [ ] `frontend/package.json`'s `postbuild` (or inlined `build`) step producing `dist/404.html` (Pattern 2)
- [ ] Frozen prediction pool file (`pool.parquet` or equivalent) captured alongside the fixture set (D-10)
- [ ] `@playwright/test` install (via the package-legitimacy gate — approved above) + `npx playwright install chromium`
- [ ] `e2e/scripts/synthesize-variants.mjs` — the blank/DGW transform script (D-06)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | D-04 explicitly scopes out keyed-auth E2E; already covered by Phase 1's APIT-02 pytest suite |
| V3 Session Management | No | Stateless API, no session/cookie surface in this phase |
| V4 Access Control | No | No per-user access control beyond the existing `require_key` stub, already tested |
| V5 Input Validation | Yes | Client-side entry-ID validation (`SquadTab.tsx`'s `LoadTeamControl`, read this session: regex `^\d+$` + `id >= 1` guard before any request fires) — E2E can add one smoke assertion that an invalid entry ID never triggers a network request, complementing existing Vitest unit coverage |
| V6 Cryptography | No | No crypto surface introduced by this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| `FPL_FIXTURE_DIR` accidentally set in a real production deploy | Tampering (real users silently served frozen fake data) | Never set `FPL_FIXTURE_DIR` in any real deploy config; Phase 5/7 should carry this forward as an explicit deploy-config invariant, not just an E2E-time convenience |
| Fixture data silently drifting from the real export contract over time | Tampering (integrity) | D-08's immutable versioned `v1`/`v2` directories + `MANIFEST.md` — already locked by CONTEXT.md, not a new control this phase invents |
| Real personal data (entry 6980093's manager name/rank) committed to git as a permanent public record | Information Disclosure | Explicit confirm-before-capture checkpoint (Open Question 2) rather than a silent default |

## Sources

### Primary (HIGH confidence)
- `api/main.py` (read in full this session) — every call site, mount, and cache structure referenced above
- `tests/conftest.py`, `tests/test_api.py` (read in full this session) — the existing mocking/reset precedent this phase's runtime seam generalizes
- `predict/live.py`, `predict/export.py`, `data/ingest.py` (read in full this session) — `_load_live`/`build_pool`/`fetch_fpl_live` mechanics, the JSON export contract
- `config.py` (read in full this session) — `BUDGET`, `SQUAD_SIZE`, `POSITION_QUOTA`, `MAX_FREE_TRANSFERS`, `CURRENT_SEASON`
- `frontend/src/router.tsx`, `frontend/src/components/PageShell.tsx`, `frontend/src/routes/{XpTable,Fixtures,Prices,Team}.tsx`, `frontend/src/components/team/{SquadTab,RateTab,ChipsTab}.tsx`, `frontend/src/components/{SolveControls,pitch/PlayerCard}.tsx` (read in full this session) — DOM structure, aria-labels, and interaction points the specs will target
- `frontend/vite.config.ts`, `frontend/vitest.config.ts`, `frontend/package.json`, `frontend/dist/index.html` and directory listing (read this session) — confirms the `/data` mount-splitting need and Vitest's default glob risk
- Installed `starlette==1.0.0` source, `StaticFiles.get_response` (read via `inspect.getsource` this session) — the verified basis for Pattern 2
- `npm view @playwright/test version` / `npm view playwright version` → `1.62.1` (run live against the npm registry this session)
- `gsd_run query package-legitimacy check --ecosystem npm @playwright/test` → `OK` (run this session)
- `hasattr(fastapi.FastAPI, "frontend")` → `False` against installed `fastapi==0.136.1` (run this session) — basis for Pitfall 2

### Secondary (MEDIUM confidence)
- [Web server | Playwright](https://playwright.dev/docs/test-webserver) — `webServer` config semantics (command chaining, `reuseExistingServer`, `timeout`, multiple servers)
- [Configuration | Playwright](https://playwright.dev/docs/test-configuration) — general config reference

### Tertiary (LOW confidence)
- Blog claim about `app.frontend()` (uncredited source surfaced via WebSearch) — explicitly refuted by direct `hasattr` verification against this project's pinned FastAPI version; retained here only as a documented dead end (Pitfall 2), not as guidance

## Metadata

**Confidence breakdown:**
- Standard stack (Playwright version/package legitimacy): HIGH — verified live against npm registry and the package-legitimacy tool
- Fixture-seam architecture (network call sites, static mount split, SPA fallback): HIGH — every claim traces to a file read this session, including the installed Starlette source
- Playwright `webServer`/multi-fixture-set orchestration idiom: MEDIUM — confirmed via official docs, but the exact two-fixture-set-in-one-run mechanism (Open Question 1) needs a planning-time decision, not just a docs citation
- Directory layout, fixture file naming, pool storage format: MEDIUM — reasonable, convention-consistent recommendations, explicitly marked as this phase's "Claude's Discretion" items rather than locked facts

**Research date:** 2026-09-03
**Valid until:** ~30 days for the architecture patterns (stable once implemented); Playwright's own version pin should be re-verified at install time if this research is consumed more than a few weeks after 2026-09-03, given the package's active release cadence
