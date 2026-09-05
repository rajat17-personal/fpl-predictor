# Technology Stack

**Project:** FPL Predictor — Production Hardening (frontend rebuild, testing, CI/CD)
**Researched:** 2026-08-31
**Confidence:** MEDIUM-HIGH (versions verified live against npm/PyPI registries and current 2026 docs; a few FPL-specific asset/CDN details are community-knowledge, flagged LOW below)

Scope note: this covers only the NEW surface area for this milestone — React+Vite frontend, Playwright E2E, FastAPI test suite, Docker/CI. The existing Python 3.14 / FastAPI / LightGBM / PuLP pipeline stack is documented in `.planning/codebase/STACK.md` and is not re-litigated here except where it constrains a new choice (e.g. Python 3.14 compatibility for Docker/uv).

## Recommended Stack

### Core Frontend (React + Vite rebuild)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| React | 19.2.x | UI library | Current stable line (19.0 GA Dec 2024, now at 19.2); React Compiler 1.0 went stable Oct 2025 and is endorsed by the React team — eliminates most manual `useMemo`/`useCallback` for the pitch renderer's per-player re-renders |
| Vite | ^7 (verify latest at implementation; 8.x exists but confirm React plugin support before jumping) | Build tool / dev server | De facto standard for React SPAs in 2025/2026; fast HMR, minimal config, first-class TypeScript support. **Pin the major explicitly** — Vite ships majors frequently; don't float `^8` blind, confirm `@vitejs/plugin-react-swc` compatibility first |
| @vitejs/plugin-react-swc | latest matching Vite major | Fast Refresh via SWC | SWC-based transform is materially faster than Babel for a project this size; standard pairing with Vite for React in 2026 |
| TypeScript | **6.x** (NOT 7.x yet — see What NOT to Use) | Type safety | Pin to the last TS 6.x line for compatibility with `typescript-eslint`/ESLint tooling (see below) |
| React Router | 7.18.x (`react-router-dom` package) | Client-side routing for the 8 pages | Highest-adoption router in the React ecosystem in 2026, least migration friction, mature data-loading APIs (`loader`/`useLoaderData`) map cleanly onto "load this page's JSON export and render." No SSR needed here — use it in **declarative/data mode**, not framework (Remix) mode, since this stays a static SPA build with no Node server at runtime |

### Data Fetching / State

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| @tanstack/react-query | 5.102.x | Fetching + caching `web/data/*.json` | Even though the data is "static" JSON, TanStack Query still earns its keep here: consistent loading/error/stale states across 8 pages, background refetch so the site picks up a new weekly export without a hard reload, and devtools for debugging the solve/rate flows. Treat each JSON file's `queryKey` as `[filename, exportTimestamp]` so a new weekly export invalidates cache cleanly |
| Native `fetch` (no axios) | — | HTTP calls to `api/main.py` `/solve`, `/rate`, `/team` | The API surface is small (3-4 endpoints) and same-origin/CORS-restricted per this milestone's hardening goals; axios adds a dependency for interceptor/cancellation features `fetch` + `AbortController` already covers adequately |

### Charting

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Recharts | 3.10.x | Points trend, price history, fixture-difficulty visualizations | Highest-adoption React chart library in 2026 (~49M weekly downloads), composable declarative API, sufficient for standard bar/line/area charts this product needs. Default choice — do not reach for a lower-level library unless a specific chart type proves awkward |

### Pitch Renderer (bespoke component, no off-the-shelf library)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Tailwind CSS | 4.3.x | Styling for pitch layout + design system | Utility-first CSS maps directly onto the "relative container + percentage-positioned absolute children" pattern the pitch needs; v4's CSS-first config (no `tailwind.config.js` needed, `@import "tailwindcss"` in CSS) is the current standard and pairs cleanly with Vite's native CSS pipeline |
| CSS `position: relative` container + `position: absolute` percentage-based children | — | Player token placement on the pitch | Standard pattern for formation/pitch layouts: a fixed-aspect-ratio pitch container, player tokens positioned with `top-[x%] left-[y%]` (percentages, not px) so the layout stays proportional at any viewport width. Group tokens by row (GK / DEF / MID / FWD) and compute row `top%` + evenly-spaced `left%` per formation (e.g. 3-4-3, 4-4-2) in a small pure function — do not hand-hardcode coordinates per formation |
| No dedicated "sports pitch" npm library | — | — | There is no mature, actively maintained React pitch-layout library worth adopting (small/abandoned packages exist but add more risk than the ~150 lines of custom positioning logic this needs). Build it as a first-party component |

### Assets (shirts / kits / badges) — CONFIDENCE: LOW, resolve during UI design phase

| Approach | Notes |
|----------|-------|
| FPL's own CDN pattern (community-documented, unofficial): `https://resources.premierleague.com/premierleague/badges/50/t{team_code}.png` (club badges) and `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_{team_code}-66.png` (kit shirts, `-110.png` for larger, `_1-` suffix variants for GK/alternate kits) | This is how the official FPL app itself sources these assets, and it's the pattern used by community FPL tools. **Not officially documented/supported** — PROJECT.md already flags this as trademark-sensitive and "resolve during UI design." Treat as a runtime `<img>` reference to Premier League's own CDN (same as the official app does), not as a bundled/redistributed asset, to minimize trademark exposure. Have a graceful `onError` fallback |
| Fallback: neutral generated kit graphics (CSS gradient shirt shapes colored by team's primary/secondary color from a small static lookup table) | Zero trademark risk, no external CDN dependency (no broken-image risk if Premier League changes URLs), but visually flatter. Recommended as the `<img onError>` fallback, not necessarily the primary rendering |

### Testing — Playwright E2E

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **@playwright/test (Node runner)** — NOT pytest-playwright | 1.62.x | E2E test runner | **This is the resolution to the `--browser` flag collision noted in PROJECT.md.** The repo's `pytest.ini` already disables both `pytest-playwright` and `seleniumbase`'s pytest plugin because they register the identical `--browser` CLI option (`argparse.ArgumentError: argument --browser: conflicting option string`) — this is a well-documented, unresolvable-in-place conflict class whenever both plugins are installed in the same pytest environment. Since `seleniumbase` stays installed for FBref scraping, don't fight this: **run Playwright's native Node test runner** (`npx playwright test`), which has its own separate CLI entirely outside pytest's argument parser. This sidesteps the conflict permanently instead of requiring per-run flag juggling, and gives richer built-in tooling (trace viewer, HTML reporter, parallel sharding, `--ui` mode) that pytest-playwright doesn't match |
| @playwright/test browsers (chromium only for CI) | bundled | Browser binaries | Install only `chromium` in CI (`npx playwright install --with-deps chromium`) to keep CI runtime and cache size down; add firefox/webkit locally only if cross-browser bugs actually surface |

### Testing — FastAPI Integration Suite

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| httpx | 0.28.x | Underlying HTTP client for `TestClient` | Already a dependency per `.planning/codebase/STACK.md`; FastAPI's `TestClient` is built on it |
| starlette.testclient.TestClient (sync) | bundled with FastAPI | Primary tool for `/solve`, `/rate`, `/team`, auth-stub, cache, error-response tests | Sync `TestClient` handles async FastAPI endpoints transparently and needs no `async def`/`await` ceremony in test functions — use this for the bulk of the suite (simplest, fastest to write, matches the existing sync pytest style already in the repo) |
| httpx.AsyncClient + ASGITransport | 0.28.x | Only for tests that need real concurrency (e.g. verifying the solve-cache's thread-safety/LRU behavior under concurrent requests) | The old `AsyncClient(app=app)` shortcut is deprecated; current pattern is `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` inside an `@pytest.mark.anyio`-marked test. Use sparingly — only where TestClient's synchronous model can't exercise the concurrency path under test |
| anyio (pytest plugin, via `anyio[trivial]` or `pytest-asyncio`) | 4.14.x | Enables async test functions | FastAPI's own test docs recommend `anyio`'s pytest plugin over `pytest-asyncio` since Starlette/FastAPI already depend on anyio internally — one less dependency to reconcile |
| asgi-lifespan | 2.1.x | Only if `/solve`/`/rate`/`/team` startup/shutdown events (model loading, cache warm) must fire in tests | `AsyncClient` does not trigger FastAPI lifespan events by default; wrap with `asgi_lifespan.LifespanManager` if the test suite needs the model/cache to actually be loaded rather than mocked |

### Infrastructure — Docker

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `python:3.14-slim` (Debian trixie, e.g. `3.14.7-slim-trixie`) | 3.14.7 | Final runtime base image | Matches the existing conda env's Python 3.14 exactly (no version drift between dev and prod); official Docker Hub image, ~41MB base, actively maintained |
| Multi-stage Dockerfile: `builder` stage (uv + compilers) → slim final stage (venv + app only) | — | Keep final image small and free of build tooling | Standard 2025/2026 pattern: install uv and compile/lock deps (LightGBM, PuLP, pandas/pyarrow all need native wheels or build tooling) in a fat builder stage, then `COPY --from=builder /app/.venv /app/.venv` into the slim final stage. Typical shrink is 1GB+ → well under 300MB for a data-science-adjacent Python image |
| uv | latest (Tier-1 supports Python 3.14) | Dependency install + lock in the builder stage | 10-100x faster than pip for installs — meaningfully shortens CI + Docker build time on every push. Astral publishes an official Docker integration guide; use `uv sync --locked --no-dev` in the builder stage so the image installs exactly what's locked, no resolution drift between a developer's machine and CI |
| Dependency file split: `COPY pyproject.toml uv.lock ./` then `RUN uv sync --locked` **before** `COPY . .` | — | Docker layer caching | Ensures the (slow) dependency-install layer is cache-hit on every code-only change; only busts when `uv.lock` changes |

### Infrastructure — GitHub Actions CI/CD

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `actions/checkout` | v5 (verify latest tag at implementation time; v7 exists per marketplace but confirm GA status) | Checkout repo | Standard first step in every job |
| `astral-sh/setup-uv` | v6+ (verify latest; v10 reported in marketplace listings) | Install uv, enable its cache | Official Astral action; `enable-cache: true` persists uv's cache between runs keyed on `uv.lock`, cutting install time significantly on cache hit |
| `actions/setup-node` | v4/v5 | Node toolchain for the Vite frontend job | Needed for `npm ci` + `npm run build` + Playwright; pin Node to the LTS your `package.json` `engines` field declares |
| `docker/login-action` | v3 | Auth to GHCR | Use the built-in `GITHUB_TOKEN` (no extra PAT needed) with `permissions: packages: write` on the job — standard, zero-config path for same-repo image publishing |
| `docker/metadata-action` | v5 | Generate image tags/labels | Produces `sha`, `latest`-on-default-branch, and branch-name tags automatically; avoids hand-rolled tag logic |
| `docker/build-push-action` | v6 | Build (and, per this milestone, push to GHCR but **not deploy**) | Use with `buildx` and GHA layer caching (`cache-from: type=gha`, `cache-to: type=gha,mode=max`) — meaningfully speeds up repeat builds where only app code (not deps) changed |
| `actions/upload-artifact` | v4 | Publish the Vite static build as a CI artifact | Satisfies "CI produces a deployable... static build artifact, not a deploy" from PROJECT.md constraints, with zero hosting decision required yet |

## Installation

```bash
# Frontend scaffold
npm create vite@latest web-app -- --template react-ts
cd web-app
npm install react-router-dom@^7 @tanstack/react-query@^5 recharts@^3
npm install -D tailwindcss@^4 @tailwindcss/vite typescript@^6 @vitejs/plugin-react-swc

# E2E (Node, NOT pytest-playwright)
npm install -D @playwright/test@^1.62
npx playwright install --with-deps chromium

# API test suite (conda env python314)
pip install "httpx>=0.28" "anyio>=4.14" "asgi-lifespan>=2.1"
# pytest, fastapi, uvicorn already pinned per .planning/codebase/STACK.md

# Dependency locking for Docker/CI (Python side)
pip install uv
uv pip compile requirements.in -o requirements.txt   # or migrate to pyproject.toml + uv.lock
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Router | React Router v7 (declarative mode) | TanStack Router | Best-in-class type safety, but smaller ecosystem and steeper learning curve for a solo dev; overkill for 8 largely-static pages with no complex nested/typed search-param state |
| Router | React Router v7 (declarative/SPA mode) | React Router v7 framework mode (Remix-style) | Framework mode assumes a Node server for SSR/data loading; this project stays a static SPA build (CI artifact, no live host yet) — declarative mode avoids introducing a server runtime requirement prematurely |
| Data fetching | TanStack Query | Plain `useEffect` + `fetch` | Would work, but loses free loading/error/cache-invalidation semantics across 8 pages that all follow the same "fetch a JSON export" shape — not worth hand-rolling |
| Charting | Recharts | visx | visx gives lower-level control and a smaller footprint, but its steeper API and lower package-level docs coverage aren't justified for standard trend/bar charts here |
| Charting | Recharts | Nivo | Nivo's polish and chart-type breadth are nice-to-haves this project doesn't need; Recharts' larger ecosystem/adoption reduces long-term maintenance risk |
| E2E runner | @playwright/test (Node) | pytest-playwright | Directly causes the documented `--browser` argparse collision with `seleniumbase` already installed in this repo; Node runner avoids the collision entirely and has richer tooling |
| Python dep locking | uv | pip-tools | uv is a strict superset workflow (same `pip compile` interface) that's markedly faster and has an official first-class Docker integration guide; no reason to keep pip-tools once migrating |
| Docker base | `python:3.14-slim` | `python:3.14-alpine` | Alpine's musl libc frequently breaks binary wheels for LightGBM/scikit-learn/pyarrow (this project's core ML deps), forcing slow from-source compiles; slim (Debian-based, glibc) avoids that entirely — do not use alpine for this stack |
| CSS approach | Tailwind CSS v4 | CSS Modules / vanilla CSS | Tailwind's utility classes map naturally onto percentage-based absolute positioning for the pitch, and its v4 CSS-first config removes prior JS-config overhead; CSS Modules remain a reasonable fallback if the team prefers scoped stylesheets, but offer no particular advantage here |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| TypeScript 7.0.x as the ESLint-facing compiler | TS 7.0 (GA July 2026) ships with **no stable programmatic API** — `typescript-eslint` closed same-day support requests as not-planned; ESLint's TS-aware linting breaks against it. Stable API lands in TS 7.1 (~Oct 2026 per Microsoft's own statement), with tool support following weeks after | Pin `typescript` to the latest **6.x** line for the whole project (or use Microsoft's `@typescript/typescript6` compat package solely for the ESLint toolchain) until `typescript-eslint` confirms 7.x support — re-evaluate this pin in the next milestone |
| `pytest-playwright` | Registers the same `--browser` CLI flag as `seleniumbase`'s pytest plugin, which stays installed in this repo for FBref scraping — causes an unrecoverable `argparse.ArgumentError` when both are loaded in the same pytest run (already the reason `pytest.ini` disables both plugins today) | `@playwright/test`, Playwright's native Node test runner — entirely separate CLI, zero pytest interaction |
| Redistributing/bundling Premier League shirt or badge image files in the repo | Trademarked assets (already flagged in PROJECT.md); bundling copies (vs. runtime-referencing the league's own CDN) increases legal exposure | Reference PL's own CDN URLs at runtime (same as the official FPL app does) with a neutral-graphic fallback, or use fully generic/generated kit shapes colored by team palette |
| `python:3.14-alpine` for the API image | musl libc breaks/slows prebuilt wheels for LightGBM, scikit-learn, pyarrow — the exact packages this pipeline depends on | `python:3.14-slim` (Debian-based, glibc, prebuilt-wheel compatible) |
| axios (or any HTTP client library) for the frontend's calls to `api/main.py` | Adds a dependency for interceptor/retry features the API surface (3-4 endpoints, same-origin) doesn't need | Native `fetch` + `AbortController`, wrapped in a tiny typed helper if repetition becomes a problem |
| A generic "React soccer pitch" npm package | No actively maintained, well-adopted option exists; adopting one trades a small amount of custom code for an external maintenance/security risk | First-party pitch component (~100-200 lines: relative container + percentage-positioned formation rows) |

## Stack Patterns by Variant

**If the pitch renderer needs animation (e.g. animating a transfer swap):**
- Use CSS transitions on the `top`/`left` percentage properties (they animate natively) rather than reaching for a JS animation library (Framer Motion, etc.)
- Because the only motion needed is "player token moves from position A to position B" — CSS transitions cover this with zero added dependency weight

**If Playwright E2E tests need to hit the real FastAPI backend (not mocks):**
- Start the FastAPI app via `uvicorn` as a Playwright `webServer` config entry (in `playwright.config.ts`), pointed at a throwaway/test data snapshot, and let Playwright manage process lifecycle for CI
- Because this exercises the true `/solve`/`/rate`/`/team` contract the React app depends on, catching integration breaks that mocked-API E2E tests would miss — matches PROJECT.md's call for E2E covering "team/pitch + solver flow" and "rate-my-team" end to end

**If CI time becomes a bottleneck as the test suites grow:**
- Split the GitHub Actions workflow into parallel jobs (lint, pytest+API tests, Playwright, Docker build) rather than one serial job
- Because these are independent concerns with no cross-job dependency until a final "all green" gate — parallelizing is free on GitHub Actions' per-job runners and shortens feedback loop for a solo developer

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| React 19.2.x | React Router 7.18.x | React Router 7 requires React 18+; fully compatible with 19 |
| React 19.2.x | @tanstack/react-query 5.102.x | TanStack Query v5 supports React 18/19 |
| Vite (7 or 8, verify at implementation) | @vitejs/plugin-react-swc | Confirm the plugin's supported Vite major before upgrading Vite — don't let Vite float ahead of plugin support |
| TypeScript 6.x (pinned) | typescript-eslint (current major) | This pairing is the safe/working combination as of Aug 2026; TypeScript 7.x is NOT yet supported by typescript-eslint |
| Python 3.14 | uv (Tier 1 support) | No caveats — uv treats 3.14 as fully supported/tested |
| Python 3.14 | LightGBM, scikit-learn, pyarrow (existing pipeline deps) | Already validated per `.planning/codebase/STACK.md`; carries over unchanged into the Docker image — just ensure the `slim` (not `alpine`) base so prebuilt wheels install |
| httpx 0.28.x | FastAPI TestClient | Current TestClient is built on httpx; the deprecated `AsyncClient(app=...)` shortcut is gone as of this httpx line — use `ASGITransport` explicitly |

## Sources

- npm registry (`registry.npmjs.org`) — live version lookups for react, react-dom, react-router-dom, @tanstack/react-query, recharts, vite, @vitejs/plugin-react-swc, @playwright/test, typescript, vitest, tailwindcss, axios (2026-08-31) — HIGH confidence
- PyPI (`pypi.org`) — live version lookups for httpx, fastapi, uvicorn, pytest, anyio, asgi-lifespan (2026-08-31) — HIGH confidence
- Docker Hub official `python` image page + `docker-library/official-images` — confirms `python:3.14-slim`/`3.14.7-slim-trixie` current and published — HIGH confidence
- Astral docs (`docs.astral.sh/uv`) + GitHub issues — confirms uv Tier-1 Python 3.14 support and official Docker integration guide — HIGH confidence
- InfoQ, The Register, Visual Studio Magazine, Microsoft DevBlogs (`devblogs.microsoft.com/typescript`), typescript-eslint GitHub issue #12518 — cross-confirmed TypeScript 7.0 GA (July 2026) and its lack of stable programmatic API blocking typescript-eslint until 7.1 — MEDIUM-HIGH confidence (multiple independent, dated sources agree)
- FastAPI official docs (`fastapi.tiangolo.com/advanced/async-tests`) + community guides — TestClient/ASGITransport/anyio patterns — MEDIUM confidence
- seleniumbase GitHub Discussions #976 + related pytest plugin conflict issues — confirms the `--browser` argparse collision class this repo already worked around — MEDIUM confidence (matches PROJECT.md's own documented symptom)
- Community web search (docs.astral.sh Docker guide, multiple dated 2025/2026 blog posts on uv+Docker multi-stage patterns) — MEDIUM confidence, cross-checked across 3+ independent sources
- Community knowledge of FPL's unofficial CDN URL pattern (`resources.premierleague.com`, `fantasy.premierleague.com/dist/img/shirts`) — **not confirmed via this research pass's web search results**; carried from general FPL-tooling community knowledge — **LOW confidence, verify directly (browser devtools on fantasy.premierleague.com) before implementation**
- GitHub Actions Marketplace pages + blog posts for docker/build-push-action, docker/login-action, docker/metadata-action, astral-sh/setup-uv — version numbers are point-in-time; **re-verify exact tags at implementation time**, Actions bump frequently — MEDIUM confidence

---
*Stack research for: FPL Predictor React/Vite frontend + CI/CD/testing hardening*
*Researched: 2026-08-31*
