---
phase: 01-test-base-layer-app-skeleton
plan: 04
subsystem: ui
tags: [vite, react, react-router, tanstack-query, tailwindcss-v4, vitest, testing-library, dev-proxy]

# Dependency graph
requires:
  - phase: 01-01
    provides: Root .gitignore (frontend/node_modules, frontend/dist ignored) and
      recorded human sign-off on the 13 [SUS]-flagged packages installed here
provides:
  - Standalone frontend/ Vite+React+TypeScript app with its own package.json/node_modules
  - Proven dev-server proxy (/api, /data -> localhost:8000) matching api/main.py's
    StaticFiles(directory=web/) mount at "/"
  - fetchJson/fetchApi wrappers (src/lib/api.ts) that throw a descriptive Error on
    a non-ok fetch response
  - Full UI-SPEC Tailwind v4 @theme token set (24 --color- properties, spacing
    scale, typography roles) with light/dark values
  - PageShell app-shell component (header/nav-slot/meta-banner-slot, 68rem/16px
    content wrapper, persistent verbatim footer disclaimer)
  - scripts/verify_dev_proxy.sh and scripts/verify_frontend_build.sh reusable gates
  - Vitest + Testing Library component-test harness (jsdom, jest-dom matchers,
    non-watch test script) ready for plan 01-05's UI-SPEC backstop assertions
affects: [01-05, "02 (page content built against this shell/token set)", "05 (CI-02 inherits the npm --prefix frontend commands verbatim)"]

# Actuals (#2632) — chars/4 over the realized diff (excl. package-lock.json, machine-generated)
actuals:
  tokens: 8227
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added:
    - "vite@7.3.6 + @vitejs/plugin-react@5.2.0 (deliberate downgrade pin from npm latest 8.2.2/6.1.1)"
    - "typescript@6.0.3 (deliberate downgrade pin from npm latest 7.0.2, per typescript-eslint's peer range)"
    - "react-router@7.18.3 (unified package, not react-router-dom; npm latest has since moved to 8.x)"
    - "@tanstack/react-query@5.102.8"
    - "tailwindcss@4.3.3 + @tailwindcss/vite@4.3.3 (CSS-first, no tailwind.config.js/postcss.config.js)"
    - "lucide-react@1.38.0"
    - "vitest@4.1.11 + jsdom@30.0.1 + @testing-library/react@16.3.3 + @testing-library/jest-dom@7.0.1"
    - "@types/node@26.4.0"
  patterns:
    - "Same-origin relative fetch paths only (fetchJson/fetchApi never build an absolute URL
       or read a base-URL env var) so dev (Vite proxy) and prod (FastAPI StaticFiles mount)
       resolve identically"
    - "Tailwind v4 @theme token block with light values on the token and dark values
       re-declared in a plain :root override inside @media (prefers-color-scheme: dark) —
       swappable for a data-theme attribute strategy when Phase 2's UIX-02 toggle lands"
    - "Filename-comparison build-purity gate (scripts/verify_frontend_build.sh) rather than
       content grep — cannot be defeated by minification, doesn't depend on field names"
    - "vitest.config.ts kept as a separate file from vite.config.ts so the dev-proxy config
       and the test config cannot interfere with each other"

key-files:
  created:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/vite.config.ts
    - frontend/vitest.config.ts
    - frontend/tsconfig.json / tsconfig.app.json / tsconfig.node.json
    - frontend/index.html
    - frontend/src/main.tsx
    - frontend/src/index.css
    - frontend/src/lib/api.ts
    - frontend/src/routes/XpTable.tsx
    - frontend/src/components/PageShell.tsx
    - frontend/src/test/setup.ts
    - frontend/src/test/harness.test.tsx
    - scripts/verify_dev_proxy.sh
    - scripts/verify_frontend_build.sh
  modified: []

key-decisions:
  - "All npm installs used --save-exact against the exact versions plan 01-01's human
     sign-off approved (typescript@6.0.3, vite@7.3.6, @vitejs/plugin-react@5.2.0,
     react-router@7.18.3, @tanstack/react-query@5.102.8, lucide-react@1.38.0,
     tailwindcss@4.3.3, @tailwindcss/vite@4.3.3, @types/node@26.4.0, vitest@4.1.11,
     jsdom@30.0.1, @testing-library/react@16.3.3, @testing-library/jest-dom@7.0.1) —
     re-verified against the live registry immediately before each install; every pin
     still resolved to the exact requested version, so no drift occurred and no
     deviation was needed on that front."
  - "Removed oxlint (and its .oxlintrc.json / package.json 'lint' script) that
     create-vite@9.2.0's current react-ts template auto-adds — it is not on plan
     01-01's approved package-legitimacy list and this plan's scope has no linting
     task, so it was deleted before npm install ever pulled it down rather than left
     in place as an unapproved, unreviewed dependency."
  - "Deleted create-vite@9.2.0's newer demo assets not named in the plan's literal
     file list (src/assets/hero.png, public/icons.svg, src/assets/vite.svg) —
     the template shipped since the 01-RESEARCH.md research session and added
     assets beyond App.tsx/App.css/react.svg/vite.svg; all were unreferenced once
     App.tsx was removed, so kept the intent (delete scaffold demo files) rather
     than the literal path list."

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "Dev-server proxy proven end to end: browser reads live web/data/meta.json and /api/health through the Vite proxy to the real uvicorn process"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "bash scripts/verify_dev_proxy.sh (prints DEV PROXY OK, exit 0)"
        status: pass
      - kind: unit
        ref: "node -e pins-check script asserting typescript===6.0.3, vite matches ^7., react-router present"
        status: pass
    human_judgment: false
  - id: D2
    description: "Production build never bundles pipeline JSON (web/data/*.json) into frontend/dist or frontend/public"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh (prints BUILD PURITY OK, exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full UI-SPEC Tailwind v4 @theme token set exists with light and dark values; no component hardcodes a hex colour"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "grep -c @theme / --color- in frontend/src/index.css (24 matches); ! grep hex literal in frontend/src/**/*.tsx"
        status: pass
    human_judgment: false
  - id: D4
    description: "Vitest + Testing Library harness runs a real component test in jsdom with jest-dom matchers"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/test/harness.test.tsx#renders PageShell and shows the footer disclaimer"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck (tsc --noEmit, exit 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The live dev experience (visual layout, gameweek number correctness, footer wrap at 375px, no console errors) reads correctly in a real browser"
    human_judgment: true
    rationale: "Plan-level <human-check> block — visual/console verification that no automated test in this phase asserts; deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase."

# Metrics
duration: 21min
completed: 2026-08-31
status: complete
---

# Phase 1 Plan 4: Test Base Layer & App Skeleton — Frontend Dev-Proxy Tracer & App Shell Summary

**A standalone Vite+React+TypeScript `frontend/` app proves the dev-proxy seam to the live FastAPI backend, carries the full Tailwind v4 design-token set and app-shell chrome ported from the vanilla site, and ships a working Vitest+Testing Library harness — all installs pinned exactly to plan 01-01's human-approved package list.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-31T16:50:00Z (approx)
- **Completed:** 2026-08-31T17:11:28Z
- **Tasks:** 3
- **Files modified:** 20 (`git diff --stat` across the three task commits, excluding `.planning/`)

## Accomplishments

- Scaffolded `frontend/` via `npm create vite@latest frontend -- --template react-ts`, then
  pinned every dependency to plan 01-01's approved package-legitimacy list with
  `--save-exact` (typescript@6.0.3, vite@7.3.6, @vitejs/plugin-react@5.2.0, react-router@7.18.3,
  @tanstack/react-query@5.102.8, lucide-react@1.38.0, tailwindcss@4.3.3, @tailwindcss/vite@4.3.3,
  @types/node@26.4.0) — re-checked against the live npm registry immediately before install;
  all resolved to the exact requested version.
- Wired `vite.config.ts`'s `server.proxy` for both `/api` and `/data` to
  `http://localhost:8000`, matching `api/main.py`'s `StaticFiles(directory=web/)` mount at `/`
  (not `/web`) — the exact seam the whole React rebuild depends on.
- Built `src/lib/api.ts` (`fetchJson`/`fetchApi`, relative paths only, throws a descriptive
  `Error` with path+status on a non-ok response) and the tracer route
  `src/routes/XpTable.tsx`, which reads `web/data/meta.json` live through the proxy via
  TanStack Query.
- Authored `scripts/verify_dev_proxy.sh` — starts real `uvicorn`/`vite` processes, asserts
  `/data/meta.json`, `/api/health`, and `/` all resolve through port 5173 only, then tears
  both down with a trap that also does a port-based cleanup fallback (see Deviations).
- Ported the full UI-SPEC design-token set into `src/index.css` as a Tailwind v4 `@theme`
  block (24 `--color-` properties including the reserved warn/band/FDR-ramp slots, plus the
  spacing scale and four typography roles), with dark values applied via
  `prefers-color-scheme`.
- Built `PageShell.tsx` (header with brand + empty nav/meta-banner slots, `68rem`/`16px`
  content wrapper around `<Outlet/>`, persistent verbatim footer disclaimer) and wired the
  `/` route under it as a layout route in `main.tsx`.
- Authored `scripts/verify_frontend_build.sh` — a filename-comparison gate proving no
  `web/data/*.json` filename ever lands in `frontend/dist`.
- Installed and configured Vitest + jsdom + Testing Library + jest-dom, added non-watch
  `test`/`typecheck` npm scripts, and wrote `harness.test.tsx` — a smoke test rendering
  `PageShell` inside `MemoryRouter`/`Routes`/`Route` and asserting the footer disclaimer is
  present, proving the harness itself works ahead of plan 01-05's backstop assertions.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "the browser reads live pipeline data through the dev proxy"** —
   `bb4a706` (feat)
2. **Task 2: Design tokens, app shell chrome, and the no-bundled-data build gate** —
   `8e670d3` (feat)
3. **Task 3: Stand up the Vitest + Testing Library harness** — `1c76cef` (test)

**Plan metadata:** committed alongside this SUMMARY (see below).

## Files Created/Modified

- `frontend/package.json`, `frontend/package-lock.json` — standalone app manifest, all
  installs `--save-exact` pinned
- `frontend/vite.config.ts` — dev-server proxy (`/api`, `/data` → `localhost:8000`) + React
  and Tailwind v4 plugins
- `frontend/vitest.config.ts` — separate jsdom test config (kept apart from vite.config.ts)
- `frontend/tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` — scaffold-generated,
  unmodified beyond the pinned `typescript` version
- `frontend/index.html` — Google Fonts links (Archivo/IBM Plex Sans/IBM Plex Mono), page title
- `frontend/src/main.tsx` — `createRoot` → `StrictMode` → `QueryClientProvider` →
  `RouterProvider`, `/` route nested under the `PageShell` layout route
- `frontend/src/index.css` — Tailwind v4 `@theme` token block (light values) +
  `prefers-color-scheme: dark` override block
- `frontend/src/lib/api.ts` — `fetchJson`, `fetchApi`, `MetaResponse`
- `frontend/src/routes/XpTable.tsx` — tracer route, `useQuery` over `/data/meta.json`
- `frontend/src/components/PageShell.tsx` — app-shell chrome, `<Outlet/>`, footer disclaimer
- `frontend/src/test/setup.ts` — jest-dom matcher registration + `afterEach` cleanup
- `frontend/src/test/harness.test.tsx` — harness smoke test
- `scripts/verify_dev_proxy.sh` — reusable dev-proxy end-to-end gate
- `scripts/verify_frontend_build.sh` — reusable build-purity gate

## Decisions Made

- Every install pinned `--save-exact` to plan 01-01's human-approved versions; re-verified
  against the live registry immediately before each `npm install` — no drift occurred (all
  requested exact versions resolved as-is), so no version-substitution deviation was needed.
- Removed `oxlint` (`create-vite@9.2.0`'s current default linter, not on the approved list)
  before running any install, rather than letting an unreviewed package land in
  `package.json`/`node_modules` — see Deviations.
- Deleted the newer scaffold's unreferenced demo assets (`hero.png`, `icons.svg`,
  `src/assets/vite.svg`) that weren't in the plan's literal delete list because the
  `create-vite` template has moved on since `01-RESEARCH.md` was written — kept the plan's
  intent (no leftover scaffold demo content) over its literal path list.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `verify_dev_proxy.sh`'s cleanup trap left an orphaned vite process on port 5173**
- **Found during:** Task 1 acceptance-criteria verification ("leaves no process listening on
  8000 or 5173 after it exits")
- **Issue:** `npm --prefix frontend run dev -- ...` backgrounded with `&` captures `$!` as the
  `npm` process's PID, not the actual `vite` binary it spawns as a child. Killing the tracked
  PID left the real Vite listener (a separate PID) alive on port 5173 after the script exited
  — confirmed via `lsof -i:5173` showing a live `node .../vite` process after a "successful"
  run.
- **Fix:** Added a port-based cleanup fallback in the `cleanup()` trap: after killing the
  tracked PIDs, `lsof -ti:8000` / `lsof -ti:5173` and kill anything still bound to either port.
  Re-ran the script twice after the fix; both times `lsof -ti:8000,5173` returned nothing
  post-exit.
- **Files modified:** `scripts/verify_dev_proxy.sh`
- **Verification:** `lsof -ti:8000,5173` returns empty after two subsequent successful runs
- **Committed in:** `bb4a706` (part of Task 1's initial commit — fixed before committing, not
  as a follow-up)

**2. [Rule 2/3 - Scope/Safety] Removed `oxlint` auto-added by the current `create-vite` template**
- **Found during:** Task 1, immediately after scaffolding, before any `npm install`
- **Issue:** `create-vite@9.2.0`'s `react-ts` template (newer than the one `01-RESEARCH.md` was
  written against) ships `oxlint` as a default devDependency with a `"lint": "oxlint"` script.
  `oxlint` is not on plan 01-01's human-approved package-legitimacy list, and this plan's task
  scope has no linting deliverable.
- **Fix:** Edited `package.json` to remove the `oxlint` devDependency and `lint` script, and
  deleted the generated `.oxlintrc.json`, before running `npm install` — so `oxlint` was never
  actually installed or resolved from the registry.
- **Files modified:** `frontend/package.json` (edited before first install), `.oxlintrc.json`
  (deleted)
- **Verification:** `frontend/package.json`'s final `devDependencies` (post-installs) contain
  only the plan 01-01 approved-list packages; `npm ls oxlint` (not run, package never
  installed) — confirmed by absence from `package-lock.json`
- **Committed in:** `bb4a706` (part of Task 1's initial commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 scope/safety). **Impact:** Both were necessary —
the orphaned-process fix makes the reusable verification script actually reusable (a stale
uvicorn/vite holding ports 8000/5173 would break the *next* invocation), and the oxlint
removal keeps installs strictly within the human-approved package-legitimacy list per the
plan's own threat model (T-04-SC). No scope creep beyond what the plan's acceptance criteria
already required.

## Issues Encountered

- `npm install` printed a benign `npm warn install-scripts` for `esbuild@0.28.2`'s blocked
  postinstall script (npm's newer `allowScripts` allowlist feature). Verified this does not
  break anything: `esbuild`'s platform-specific binary package
  (`@esbuild/linux-x64`) was still installed as an optional dependency, and
  `node_modules/.bin/esbuild --version` runs correctly. `npm --prefix frontend run build` and
  `run test` both exercise esbuild transitively (via Vite/Vitest) and passed. No action taken.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `frontend/` exists with a proven dev-proxy seam, the full design-token set, app-shell
  chrome, and a working component-test harness — plan 01-05 can now extract `router.tsx`,
  add the remaining seven routes plus the catch-all, and write the three UI-SPEC backstop
  assertions (loading spinner, error+retry, route-isolation) against this harness.
- The exact `npm --prefix frontend ...` commands used here (documented above) are the ones
  Phase 5's `CI-02` job must replicate verbatim.
- Plan-level `<human-check>` (visual layout at 375px, footer wrap, console errors, network
  tab showing `/data/meta.json` as its own runtime request) is deferred to end-of-phase UAT
  per `workflow.human_verify_mode=end-of-phase` — see coverage entry D5.
- `web/` is unchanged; the vanilla site remains live and authoritative.
- No blockers.

---
*Phase: 01-test-base-layer-app-skeleton*
*Completed: 2026-08-31*

## Self-Check: PASSED

- All 13 key files listed above verified present on disk with `[ -f ]`.
- All 4 commits (`bb4a706`, `8e670d3`, `1c76cef`, `4380b08`) verified present in `git log --oneline --all`.
- All three tasks' acceptance criteria re-verified passing at plan close: `npm --prefix frontend run build`, the pins check, `bash scripts/verify_dev_proxy.sh` (DEV PROXY OK, no leftover port listeners), `bash scripts/verify_frontend_build.sh` (BUILD PURITY OK), `npm --prefix frontend run typecheck`, `npm --prefix frontend run test`.
- Plan-level `<verification>` automated commands all passed; `web/` confirmed unchanged (`git status --porcelain web` empty).
