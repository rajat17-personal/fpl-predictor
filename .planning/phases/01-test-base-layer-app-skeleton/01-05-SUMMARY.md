---
phase: 01-test-base-layer-app-skeleton
plan: 05
subsystem: ui
tags: [react-router, tanstack-query, vitest, testing-library, error-boundaries, ui-shell]

# Dependency graph
requires:
  - phase: 01-04
    provides: Standalone frontend/ Vite+React+TypeScript app, the PageShell layout
      route with an empty nav slot, the tracer route (XpTable) proving the dev-proxy
      seam, the Tailwind v4 token set, and the Vitest + Testing Library harness
provides:
  - src/router.tsx exporting both `routes` (a plain array, importable by tests) and
    `router` (createBrowserRouter(routes)) — 8 concrete UI-SPEC routes plus a `*`
    catch-all, each concrete route with its own errorElement
  - Five shell components — PlaceholderPage, NotFoundPage, Spinner, ErrorState
    (+ RouteErrorBoundary), EmptyState — matching the UI-SPEC Copywriting Contract
    verbatim
  - PageShell's NAV_LINKS literal array + NavLink-rendered header nav (8 links,
    accent active state, 44px touch targets, flex-wrap)
  - Three held-out tests closing the UI-SPEC's three "resolved (backstop)" rows:
    loading, error+retry, and per-route error isolation + concurrency
affects: ["02 (fills all 7 placeholder routes with real page content against the
  same router/error/loading/empty scaffolding)", "04 (Playwright covers the same
  flows at the browser tier)"]

# Actuals (#2632) — chars/4 over the realized diff (git diff 839cbe7^..57cc708,
# excluding .planning/)
actuals:
  tokens: 6446
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-route errorElement, never a shared boundary on the layout route — a
       thrown render/fetch error in one route cannot unmount the header nav or any
       sibling route (React Router 7 native mechanism, not a custom ErrorBoundary)."
    - "RouteErrorBoundary (a thin useRouteError-reading wrapper) kept separate from
       the presentational ErrorState component, so ErrorState itself never calls a
       router hook that requires a data-router context — makes it safe to
       unit-test ErrorState in isolation with a plain render()."
    - "NAV_LINKS as a module-level literal array (never Object.keys over a map),
       consumed by both PageShell's render and Task 3's tests, so nav order is
       fixed by source and mechanically verifiable."
    - "router.tsx exports the raw `routes` array separately from the `router`
       instance it's built from, so tests rebuild the identical tree with
       createMemoryRouter instead of duplicating route definitions."

key-files:
  created:
    - frontend/src/router.tsx
    - frontend/src/components/PlaceholderPage.tsx
    - frontend/src/components/NotFoundPage.tsx
    - frontend/src/components/Spinner.tsx
    - frontend/src/components/ErrorState.tsx
    - frontend/src/components/EmptyState.tsx
    - frontend/src/components/Spinner.test.tsx
    - frontend/src/components/ErrorState.test.tsx
    - frontend/src/routes/routeIsolation.test.tsx
    - frontend/src/routes/Team.tsx
    - frontend/src/routes/Fixtures.tsx
    - frontend/src/routes/Prices.tsx
    - frontend/src/routes/League.tsx
    - frontend/src/routes/Scoreboard.tsx
    - frontend/src/routes/Differentials.tsx
    - frontend/src/routes/Methodology.tsx
  modified:
    - frontend/src/main.tsx
    - frontend/src/components/PageShell.tsx
    - frontend/src/routes/XpTable.tsx

key-decisions:
  - "Split router.tsx's errorElement wiring into two pieces: the plain <ErrorState/>
     (props: resource, onRetry?) with no router hooks, and a separate
     <RouteErrorBoundary/> that calls useRouteError() and is used ONLY as the
     errorElement value. useRouteError() throws outside a data-router context, so
     folding it into ErrorState itself would have made ErrorState unsafe to
     render in a plain render() test — the wrapper keeps the presentational
     component trivially unit-testable while still satisfying the plan's 'fall
     back to useRouteError for logging' requirement for the router-boundary case."
  - "NAV_LINKS order follows the UI-SPEC Routes table (/, /team, /fixtures,
     /prices, /league, /scoreboard, /differentials, /methodology) rather than
     vanilla web/index.html's nav order (xP table, Fixtures, League,
     Differentials, Prices, Rate my team, Scoreboard, Method) — the plan's Task 1
     action explicitly says 'UI-SPEC Routes-table order' and the acceptance
     criteria's registered-path list matches that exact sequence. Label TEXT
     (e.g. 'Rate my team', 'Method') is still taken from the vanilla nav for
     copy parity, per the read_first instruction to use it 'for label text ...
     parity'."
  - "Task 1's router.tsx shipped with a minimal local ErrorFallback function
     (not real ErrorState, which doesn't exist until Task 2) per the plan's own
     explicit instruction to state which task order was taken — Task 2's commit
     then replaces every errorElement slot with RouteErrorBoundary."

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "All 8 UI-SPEC routes plus a catch-all are registered under PageShell, each concrete route with its own error boundary"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "node route-path assertion script in Task 1's <verify> (ROUTES REGISTERED 9)"
        status: pass
      - kind: unit
        ref: "frontend/src/routes/routeIsolation.test.tsx#keeps the nav and a sibling route interactive when one route's fetch fails"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run build (tsc -b && vite build, exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Header nav renders 8 fixed links (NAV_LINKS literal array) in UI-SPEC Routes-table order via NavLink, with 44px touch targets and flex-wrap"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/routes/routeIsolation.test.tsx#keeps the nav and a sibling route interactive when one route's fetch fails (asserts all 8 nav link roles present)"
        status: pass
    human_judgment: true
    rationale: "Visual confirmation of active-link accent styling, actual flex-wrap behaviour at 375px, and comfortable tap targets is a real-browser check — deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase (see plan's <human-check> steps 1 and 3)."
  - id: D3
    description: "Spinner renders while a route's query is pending and disappears on resolve, reserving layout space (UI-SPEC E2 loading backstop)"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/Spinner.test.tsx#renders the Loading… label"
        status: pass
      - kind: unit
        ref: "frontend/src/components/Spinner.test.tsx#shows Loading… while the tracer route's query is pending, and removes it once resolved"
        status: pass
    human_judgment: false
  - id: D4
    description: "ErrorState renders heading + Retry on a failed fetch, Retry re-triggers refetch, and no raw Error message/response body/request URL/stack trace ever reaches the DOM (UI-SPEC E2 error backstop, T-05-02)"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/ErrorState.test.tsx#renders the heading, substitutes the resource into the body, and calls onRetry exactly once when Retry is clicked"
        status: pass
      - kind: unit
        ref: "frontend/src/components/ErrorState.test.tsx#renders on a rejected route query, Retry re-triggers refetch, and no raw error detail reaches the DOM"
        status: pass
    human_judgment: false
  - id: D5
    description: "EmptyState renders 'Nothing here yet' as the shell-level fallback for a zero-item fetch"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "node component-text assertion script in Task 2's <verify> (STATE COMPONENTS WIRED)"
        status: pass
    human_judgment: false
  - id: D6
    description: "One route's failed fetch leaves the nav shell and every sibling route interactive; concurrent/abandoned queries raise no unhandled promise rejection (UI-SPEC E2 partial backstop + concurrency backstop)"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/routes/routeIsolation.test.tsx#keeps the nav and a sibling route interactive when one route's fetch fails"
        status: pass
      - kind: unit
        ref: "frontend/src/routes/routeIsolation.test.tsx#raises no unhandled promise rejection across concurrent queries when one is unmounted mid-flight"
        status: pass
    human_judgment: false
  - id: D7
    description: "PlaceholderPage and NotFoundPage render the exact UI-SPEC Copywriting Contract text for all 7 placeholder routes and the catch-all"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "temporary router-acceptance test run during Task 1 execution (9/9 passed: all 8 route headings/labels + 404 heading render without throwing; deleted before commit as it wasn't in the plan's file list)"
        status: pass
    human_judgment: false
  - id: D8
    description: "The full dev-proxy + full-browser experience (visual layout, footer disclaimer wording, network tab behaviour, uvicorn-down/Retry recovery flow) reads correctly end to end"
    human_judgment: true
    rationale: "Plan-level <human-check> block (6 steps: nav visibility/active-state, 404 flow, 375px wrap, stopped-uvicorn ErrorState+Retry recovery, no-leaked-detail visual check, footer disclaimer wording) — deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase."

# Metrics
duration: 17min
completed: 2026-08-31
status: complete
---

# Phase 1 Plan 5: Test Base Layer & App Skeleton — App Shell Routes, Error Isolation & Backstop Tests Summary

**All 8 UI-SPEC routes now resolve through `router.tsx` with per-route `errorElement` isolation, a NavLink-driven header nav, and Spinner/ErrorState/EmptyState shell components — closed out by three held-out tests proving the loading, error+retry, and partial-failure/concurrency backstop rows the UI-SPEC signed off on.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-08-31T17:25:00Z (approx, following 01-03's completion)
- **Completed:** 2026-08-31T17:41:00Z
- **Tasks:** 3
- **Files modified:** 19 (`git diff --stat` across the three task commits, excluding `.planning/`)

## Accomplishments

- Extracted `frontend/src/router.tsx` from `main.tsx`: `createBrowserRouter(routes)`
  with a `PageShell` layout route wrapping 8 concrete UI-SPEC routes plus a `*`
  catch-all, exporting `routes` separately so tests can rebuild the identical tree
  with `createMemoryRouter`.
- Gave each of the 8 concrete routes its own `errorElement` — never one shared
  boundary on the layout route — so one page's failed fetch cannot take down the
  header nav or any sibling route (T-05-01).
- Built `PlaceholderPage` (used by 7 of 8 routes) and `NotFoundPage` (the
  catch-all), both rendering the UI-SPEC Copywriting Contract text verbatim.
- Filled `PageShell`'s nav slot: `NAV_LINKS` is a module-level literal array (8
  entries, UI-SPEC Routes-table order) rendered via React Router's `NavLink` —
  active-link accent styling is automatic, 44px minimum touch targets, and
  `flex-wrap` so links wrap on narrow viewports with no hamburger menu.
- Built `Spinner` (accent ring + `Loading…`, reserves min-height), `EmptyState`
  (`Nothing here yet` fallback), and `ErrorState` (heading + resource-named body +
  `Retry`, never rendering the raw thrown error into the DOM) plus a separate
  `RouteErrorBoundary` wrapper that reads `useRouteError()` for console logging
  only when used as a route's `errorElement`.
- Rewired the tracer route `XpTable.tsx`'s inline pending/error text to the three
  shared shell components, with `Retry` bound to the query's real `refetch()`.
- Wrote three held-out tests (`Spinner.test.tsx`, `ErrorState.test.tsx`,
  `routeIsolation.test.tsx`) closing the UI-SPEC's three `resolved (backstop)`
  rows — loading, error+retry, and per-route isolation plus a concurrency case
  (one query unmounted mid-flight while a sibling query runs, asserted via both
  `window` and Node `process` `unhandledrejection` listeners).

## Task Commits

Each task was committed atomically:

1. **Task 1: All eight routes, the nav, and the catch-all** — `839cbe7` (feat)
2. **Task 2: Loading, error, and empty states wired to the query layer** —
   `59a55dd` (feat)
3. **Task 3: Held-out tests for the three UI-SPEC backstop states** — `57cc708`
   (test)

**Plan metadata:** committed alongside this SUMMARY (see below).

## Files Created/Modified

- `frontend/src/router.tsx` — `createBrowserRouter(routes)`, 8 routes + catch-all,
  per-route `errorElement`
- `frontend/src/components/PlaceholderPage.tsx` — Display-role title + fixed body
  copy, used by 7 routes
- `frontend/src/components/NotFoundPage.tsx` — 404 heading/body + `Link` back to `/`
- `frontend/src/components/Spinner.tsx` — accent-ring loading indicator
- `frontend/src/components/ErrorState.tsx` — `ErrorState` (presentational) +
  `RouteErrorBoundary` (router-boundary wrapper reading `useRouteError`)
- `frontend/src/components/EmptyState.tsx` — `Nothing here yet` fallback
- `frontend/src/components/Spinner.test.tsx`,
  `frontend/src/components/ErrorState.test.tsx`,
  `frontend/src/routes/routeIsolation.test.tsx` — the three backstop suites
- `frontend/src/routes/Team.tsx`, `Fixtures.tsx`, `Prices.tsx`, `League.tsx`,
  `Scoreboard.tsx`, `Differentials.tsx`, `Methodology.tsx` — 7 placeholder routes
- `frontend/src/main.tsx` — now imports `router` from `./router` instead of
  defining routes inline
- `frontend/src/components/PageShell.tsx` — `NAV_LINKS` export + `NavLink`-rendered
  nav filling the previously-empty nav slot
- `frontend/src/routes/XpTable.tsx` — pending/error/empty states now render
  `Spinner`/`ErrorState`/`EmptyState` instead of inline text

## Decisions Made

- Kept `useRouteError()` out of the shared `ErrorState` component and put it in a
  separate `RouteErrorBoundary` wrapper used only as `errorElement` — avoids
  `ErrorState` throwing an invariant error when unit-tested with a plain
  `render()` outside a data-router context, while still satisfying the plan's
  "fall back to `useRouteError` for logging" instruction for the router-boundary
  case.
- `NAV_LINKS` order follows the UI-SPEC Routes table exactly (not vanilla
  `web/index.html`'s nav order); label text is taken from the vanilla nav for
  copy parity, per the plan's own read_first framing of that file as a label-text
  and parity reference, not an ordering one.
- Task 1 shipped `router.tsx` with a minimal local `ErrorFallback` placeholder
  (real `ErrorState` doesn't exist until Task 2), per the plan's explicit
  instruction to record which task order was taken.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `process` used without `@types/node` in scope broke `npm run build`**
- **Found during:** Task 3, while writing the concurrency backstop test (listening
  for `unhandledRejection` on Node's `process` per the plan's own guidance: "and on
  `process` where jsdom does not surface it")
- **Issue:** `tsconfig.app.json` (which covers all of `src/`, tests included) only
  declares `"types": ["vite/client"]`, not `"node"`. Referencing the global
  `process` compiled fine under `npm run typecheck` (a no-op — see the note below)
  but failed `npm run build`'s `tsc -b` step with `TS2591: Cannot find name
  'process'`.
- **Fix:** Cast through `globalThis` with a minimal local `MinimalNodeProcess`
  type (`{ on, off }` only) instead of depending on ambient `@types/node` types,
  scoped entirely to `routeIsolation.test.tsx` — no shared tsconfig changed.
- **Files modified:** `frontend/src/routes/routeIsolation.test.tsx`
- **Verification:** `npm --prefix frontend run build` exits 0 (previously failed
  with `error TS2591` before the fix)
- **Committed in:** `57cc708` (part of Task 3's commit)

---

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** Necessary to make
`npm run build` pass at all with the concurrency test's Node-level rejection
listener; fully scoped to the one test file, no shared config touched.

## Issues Encountered

- **`npm --prefix frontend run typecheck` type-checks zero files.**
  `frontend/tsconfig.json` is a TypeScript "solution" file (`"files": []`, only
  `references`); a bare `tsc --noEmit` against it does not traverse
  `references` the way `tsc -b` does, so it exits 0 having checked nothing. Only
  `npm run build`'s `tsc -b && vite build` step actually type-checks `src/**`
  today — confirmed directly when the `process`-typing bug above passed
  `typecheck` but failed `build`. This predates this plan (present since 01-04,
  which also relied on `typecheck`) and is out of this plan's scope to fix
  (changing the script's build-cache behavior, or restructuring the tsconfig
  solution, is beyond this plan's file list). Logged to
  `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md` and to
  `.planning/WINDOWS.md` (kind: `todo`) so Phase 5's `CI-01`/`CI-02` — which
  inherits these `npm --prefix frontend` commands verbatim — fixes it before
  wiring `typecheck` into CI as a meaningful gate.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All 8 UI-SPEC routes resolve, isolated behind per-route error boundaries, with
  the loading/error/empty/placeholder/404 states matching the Copywriting
  Contract verbatim — Phase 2 (`UI-02` through `UI-06`) can now fill each
  placeholder route with real page content against this scaffolding without
  touching `router.tsx`'s structure.
- `npm --prefix frontend run test` passes 7 tests (harness smoke test + the 3
  named backstop suites: Spinner, ErrorState, route isolation/concurrency) —
  Phase 4's Playwright suite covers the same flows at the browser tier.
- Plan-level `<human-check>` (nav visibility/active-state at desktop and 375px,
  404 flow, stopped-uvicorn → `ErrorState`+Retry recovery, no-leaked-detail
  visual check, footer disclaimer wording) is deferred to end-of-phase UAT per
  `workflow.human_verify_mode=end-of-phase` — see coverage entries D2 and D8.
- The `npm --prefix frontend run typecheck` gap (checks 0 files) must be fixed
  before Phase 5's `CI-01`/`CI-02` wires it into CI as a real gate — see Issues
  Encountered and `deferred-items.md`.
- `web/` is unchanged; the vanilla site remains live and authoritative.
- This closes UI-01 for Phase 1 — Phase 1's plan sequence is now complete.
- No blockers.

---
*Phase: 01-test-base-layer-app-skeleton*
*Completed: 2026-08-31*

## Self-Check: PASSED

- All 19 key files listed above verified present on disk with `[ -f ]`.
- All 3 task commits (`839cbe7`, `59a55dd`, `57cc708`) verified present in
  `git log --oneline --all`.
- All three tasks' acceptance criteria re-verified passing at plan close:
  `npm --prefix frontend run test` (7/7 passed, including the 3 named backstop
  suites), `npm --prefix frontend run typecheck` and `npm --prefix frontend run
  build` (both exit 0), `bash scripts/verify_dev_proxy.sh` (DEV PROXY OK, no
  leftover port listeners), `bash scripts/verify_frontend_build.sh` (BUILD
  PURITY OK), the Task 1 route-path node script (ROUTES REGISTERED 9), the Task
  2 component-wiring node script (STATE COMPONENTS WIRED), and the verbose-test
  suite-name grep (13 matches, ≥3 required).
- Plan-level `<verification>` automated commands all passed; `web/` confirmed
  unchanged (`git status --porcelain web` empty).
