---
phase: 02-data-layer-non-pitch-pages
plan: 03
subsystem: ui
tags: [dark-mode, tailwind-v4, localstorage, matchmedia, tanstack-query, fontsource, vitest, accessibility]

# Dependency graph
requires:
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-01's PageShell chrome (header ml-auto slot, 68rem containment) and frontend/src/lib/api.ts's MetaResponse interface"
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-02's human-approved @fontsource/archivo, @fontsource/ibm-plex-sans, @fontsource/ibm-plex-mono installs and the PARITY-DEVIATIONS.md ledger (entries 3, 4 pre-seeded for this plan)"
provides:
  - "Class-based dark-mode mechanism: @custom-variant dark + .dark token block in index.css, pre-mount head script in index.html — single mechanism, no competing media-query block"
  - "useTheme()/resolveTheme()/ThemeToggle — the three-state Light/Dark/System control every future themed component reads"
  - "fmtAbs/fmtRel/fmtFreshness (frontend/src/lib/deadline.ts) — reusable deadline/freshness formatting for any future page needing meta.json"
  - "GwBanner mounted in PageShell's header, backed by the single shell-owned meta.json TanStack Query — every remaining Phase 2 route inherits it for free"
  - "frontend/src/test/fixtures/meta.json — the shared meta fixture for any later test needing it"
affects: [02-04, 02-05, 02-06, 03]

# Actuals (#2632)
actuals:
  tokens: 11400
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dark mode is applied via document.documentElement.classList.toggle('dark', boolean) in exactly two places (inline head script, useTheme's apply effect) that read the identical localStorage key and identical unknown-value coercion, so they can never disagree about which class belongs on <html>"
    - "GwBanner's live countdown uses a self-rescheduling setInterval whose delay is recomputed from current `now` on every effect run ([deadlineMs, intervalMs] dependency), switching from 60s to 1s cadence as remaining time crosses the one-hour boundary without a separate timer mechanism"
    - "fmtRel returns a discriminated { passed: true } | { passed: false; text } result instead of a bare string, so the caller branches on the passed state explicitly rather than string-matching a sentinel value"
    - "GwBanner takes { status, data } props (TanStack Query's own status union) rather than the full UseQueryResult type, keeping the component trivially testable with plain object literals instead of a QueryClientProvider"
    - "Fetch mocks that must support two-plus concurrent queries route by URL and return independent response objects per URL — sharing one Response instance across consumers breaks on the second .json() call (see Spinner.test.tsx fix, extending the pattern 02-01 established for ErrorState.test.tsx)"

key-files:
  created:
    - frontend/src/lib/theme.ts
    - frontend/src/lib/theme.test.ts
    - frontend/src/lib/deadline.ts
    - frontend/src/lib/deadline.test.ts
    - frontend/src/components/ThemeToggle.tsx
    - frontend/src/components/ThemeToggle.test.tsx
    - frontend/src/components/GwBanner.tsx
    - frontend/src/components/GwBanner.test.tsx
    - frontend/src/test/fixtures/meta.json
  modified:
    - frontend/src/index.css
    - frontend/index.html
    - frontend/src/components/PageShell.tsx
    - frontend/src/components/PageShell.test.tsx
    - frontend/src/test/harness.test.tsx
    - frontend/src/components/Spinner.test.tsx

key-decisions:
  - "Added a --font-mono token to index.css's @theme block (IBM Plex Mono, ui-monospace fallback) so GwBanner's Numeric-modifier text (UI-SPEC Typography table) actually renders in the newly-bundled mono font — the token didn't exist yet even though the three @fontsource packages were already installed in 02-02."
  - "GwBanner's prop type is a minimal { status, data } shape (TanStack Query's own status union) rather than the full UseQueryResult<MetaResponse> generic, so unit tests construct plain object literals per state instead of standing up a QueryClientProvider for every GwBanner test."
  - "fmtRel implements the sub-hour per-second granularity (D-19's discretion item) since the countdown effect already needed the interval-switching conditional — matches RESEARCH.md's Open Question 1 recommendation that it 'falls out naturally' from the existing structure."

patterns-established:
  - "Pre-mount theme resolution logic is duplicated exactly twice (head script, useTheme) by design — both read the same storage key and apply the identical coercion rule, verified by a dedicated corrupt-value fallback test, rather than trying to share code across the pre-bundle/post-bundle boundary."

requirements-completed: [UI-06, UIX-02]

coverage:
  - id: D1
    description: "Dark mode resolves through a single class-based mechanism (@custom-variant dark + .dark block) with a complete palette covering surfaces, text, borders, accent, destructive, warn, band and the FDR 1-5 ramp — identical values to the migrated media-query block, no second mechanism."
    requirement: "UIX-02"
    verification:
      - kind: other
        ref: "plan Task 1 automated verify: DARK CLASS STRATEGY OK + FDR RAMP BOTH THEMES (20 declarations)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fonts are self-hosted via bundled @fontsource CSS imports; the Google Fonts CDN link is removed from index.html; a pre-mount inline head script applies the resolved theme class before React mounts, wrapped in try/catch."
    requirement: "UIX-02"
    verification:
      - kind: other
        ref: "plan Task 1 automated verify: HEAD SCRIPT OK; bash scripts/verify_frontend_build.sh (BUILD PURITY OK)"
        status: pass
    human_judgment: false
  - id: D3
    description: "resolveTheme resolves system/dark/light correctly; useTheme persists to localStorage with a try/catch degrade-to-session-only path on write failure; tracks matchMedia live while choice is system; the media-query listener is removed on unmount or when choice stops being system; applying the same resolved theme twice is a no-op."
    requirement: "UIX-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/theme.test.ts (12 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "ThemeToggle renders exactly three buttons (Light theme, Dark theme, System theme accessible names) with exactly one aria-pressed=true at all times, moving on click; token classes only, no hex literal."
    requirement: "UIX-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/ThemeToggle.test.tsx (3 tests)"
        status: pass
      - kind: other
        ref: "plan Task 2 automated verify: TOGGLE TOKENS ONLY"
        status: pass
    human_judgment: false
  - id: D5
    description: "fmtAbs/fmtRel/fmtFreshness implement the UI-SPEC's graduated-precision countdown and freshness tables against a fixed now, with fmtRel signaling a discriminated passed state rather than a negative countdown."
    requirement: "UI-06"
    verification:
      - kind: unit
        ref: "frontend/src/lib/deadline.test.ts (17 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "GwBanner renders the four states (loading, future deadline with two lines, passed deadline, failed query with the quiet deadline TBC fallback and no Retry control) and drives a live countdown that flips to the passed state without any further fetch."
    requirement: "UI-06"
    verification:
      - kind: unit
        ref: "frontend/src/components/GwBanner.test.tsx (5 tests, including a fake-timers deadline-crossing case)"
        status: pass
    human_judgment: false
  - id: D7
    description: "PageShell owns the single meta.json TanStack Query and mounts GwBanner + ThemeToggle in the header's trailing slot; the pre-existing 68rem containment geometry and both original containment assertions are unchanged."
    requirement: "UI-06"
    verification:
      - kind: integration
        ref: "frontend/src/components/PageShell.test.tsx (3 tests: 2 pre-existing containment + 1 new wiring test)"
        status: pass
      - kind: other
        ref: "plan Task 3 automated verify: SHELL WIRED, GEOMETRY INTACT"
        status: pass
    human_judgment: false
  - id: D8
    description: "Full frontend Vitest suite, typecheck, and the production build-purity gate all pass with this plan's changes in place."
    verification:
      - kind: other
        ref: "npm --prefix frontend run test (97/97)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck (exit 0)"
        status: pass
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh (BUILD PURITY OK)"
        status: pass
    human_judgment: false
  - id: D9
    description: "No flash of the wrong theme on reload and the header's dark-mode/GW-banner surface degrade safely; human eyes confirming the actual visual flash-free reload and OS-preference-follow behavior in a real browser (plan's own manual spot check, non-gating)."
    verification: []
    human_judgment: true
    rationale: "The plan's <verification> step 4 is an explicit non-gating manual spot check (load with OS dark mode / no stored preference, confirm no flash on reload, click through Light/Dark/System) — jsdom has no paint pipeline to assert a flash didn't occur, so this is inherently a human-observable claim, not something Vitest can prove."

duration: 40min
completed: 2026-09-01
status: complete
---

# Phase 2 Plan 3: GW Banner Countdown + Dark Mode Toggle Summary

**Class-based Tailwind v4 dark mode (single mechanism, full token palette) with flash-free pre-mount resolution, a three-state Light/Dark/System toggle, and a live gameweek-deadline countdown chip fed by one shell-owned `meta.json` query — plus self-hosted Fontsource delivery replacing the Phase 1 Google Fonts CDN link.**

## Performance

- **Duration:** 40 min (approx.)
- **Started:** 2026-09-01T13:50:00Z (approx.)
- **Completed:** 2026-09-01T14:30:00Z (approx.)
- **Tasks:** 3 (1 auto, 2 TDD)
- **Files modified:** 15 (9 created, 6 modified)

## Accomplishments
- Migrated `index.css` from a `@media (prefers-color-scheme: dark)` block to Tailwind v4's `@custom-variant dark` class strategy with an additive `.dark` selector block carrying identical token values (no second competing mechanism, D-17)
- Removed the Phase 1 Google Fonts CDN `<link>` and replaced it with three bundled `@fontsource` CSS imports; added a `--font-mono` token so the Numeric-modifier typography rule actually renders in IBM Plex Mono
- Added an inline pre-mount `<head>` script in `index.html` that resolves `localStorage["fpl-theme"]` and `matchMedia` before React mounts, so a reload in dark mode never flashes light (D-16)
- Built `useTheme()`/`resolveTheme()`/`ThemeToggle` — a three-state Light/Dark/System control that persists to `localStorage`, degrades to session-only on a storage-write failure, and tracks OS-level theme changes live while set to `system`
- Built `fmtAbs`/`fmtRel`/`fmtFreshness` (`lib/deadline.ts`) porting vanilla's absolute-time format verbatim and implementing the UI-SPEC's graduated-precision countdown and freshness tables, including the optional sub-hour per-second granularity
- Built `GwBanner` — the four-state gameweek chip (loading/future/passed/failed) driven by a self-rescheduling countdown interval, and wired `PageShell` to own the single `meta.json` query feeding it, mounted alongside `ThemeToggle` in the header's trailing slot

## Task Commits

Each task was committed atomically (Tasks 2 and 3 follow full RED→GREEN TDD cycles):

1. **Task 1: Class-based dark palette, pre-mount theme script, self-hosted fonts** - `4bdc072` (feat)
2. **Task 2 RED: failing tests for useTheme/ThemeToggle** - `471c1e1` (test)
2. **Task 2 GREEN: implement useTheme hook and ThemeToggle** - `2a3936d` (feat)
3. **Task 3 RED: failing tests for deadline formatting, GwBanner, PageShell wiring** - `8a5bfb4` (test)
3. **Task 3 GREEN: implement deadline.ts, GwBanner, PageShell wiring** - `aecd52a` (feat)

_No REFACTOR commits — both TDD implementations stayed minimal and clean through GREEN._

## Files Created/Modified
- `frontend/src/index.css` - Class-based dark variant + `.dark` token block, `--font-mono` token, three `@fontsource` imports
- `frontend/index.html` - Removed Google Fonts CDN link, added the pre-mount theme-resolution head script
- `frontend/src/lib/theme.ts` / `theme.test.ts` - `ThemeChoice`, `resolveTheme`, `useTheme()`
- `frontend/src/components/ThemeToggle.tsx` / `ThemeToggle.test.tsx` - Three-button Light/Dark/System control
- `frontend/src/lib/deadline.ts` / `deadline.test.ts` - `fmtAbs`/`fmtRel`/`fmtFreshness`
- `frontend/src/components/GwBanner.tsx` / `GwBanner.test.tsx` - Four-state gameweek chip with live countdown
- `frontend/src/components/PageShell.tsx` - Owns the single `meta.json` query; mounts `GwBanner` + `ThemeToggle`
- `frontend/src/components/PageShell.test.tsx` - Wrapped in `QueryClientProvider`; added the wiring test
- `frontend/src/test/fixtures/meta.json` - Shared meta fixture
- `frontend/src/test/harness.test.tsx` / `frontend/src/components/Spinner.test.tsx` - Rule 1 fixes (see below)

## Decisions Made
- Added a `--font-mono` token to `index.css`'s `@theme` block so `GwBanner`'s Numeric-modifier text renders in the newly-bundled IBM Plex Mono, rather than falling back to Tailwind's generic default `font-mono` stack.
- Gave `GwBanner` a minimal `{ status, data }` prop shape instead of the full `UseQueryResult<MetaResponse>` generic, keeping the component trivially unit-testable with plain object literals per state.
- Implemented the sub-hour per-second countdown granularity (D-19's discretion item) since the interval-switching logic already needed the conditional to support it — the "falls out naturally" case RESEARCH.md's Open Question 1 anticipated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrapped src/test/harness.test.tsx in a QueryClientProvider**
- **Found during:** Task 3
- **Issue:** `PageShell` now calls `useQuery` for `meta.json`; the harness smoke test rendered it without a `QueryClientProvider`, throwing "No QueryClient set".
- **Fix:** Wrapped the render in a `QueryClientProvider` with a fresh `QueryClient` (retries disabled) and mocked `fetch` to resolve deterministically.
- **Files modified:** frontend/src/test/harness.test.tsx
- **Verification:** `npm --prefix frontend run test` — full suite green.
- **Committed in:** aecd52a (Task 3 GREEN commit)

**2. [Rule 1 - Bug] Fixed Spinner.test.tsx's shared-Response-instance and text-collision regressions**
- **Found during:** Task 3
- **Issue:** The full-route-tree test mocked `fetch` to return one shared `Response` instance for every URL; adding `PageShell`'s concurrent `meta.json` query meant a second consumer called `.json()` on the same already-read body. Separately, `GwBanner`'s "loading…" pill (now mounted in every route via the header) collided with `screen.getByText(/Loading…/i)`, which the test previously assumed was unique to `<Spinner/>`.
- **Fix:** Routed the fetch mock by URL (`meta.json` and `captains.json` each get their own independently-resolved response; `xp_table.json` keeps the deferred promise) and scoped the `Loading…` assertions to `within(screen.getByRole("main"))` so the header's `GwBanner` text can't collide.
- **Files modified:** frontend/src/components/Spinner.test.tsx
- **Verification:** `npm --prefix frontend run test` — full suite green (97/97).
- **Committed in:** aecd52a (Task 3 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 test-regression fixes, both direct consequences of `PageShell` now owning a concurrent query and rendering `GwBanner` on every route)
**Impact on plan:** Necessary consequences of implementing the plan as written (PageShell wiring, Task 3). No scope creep, no architectural change.

## Issues Encountered
None beyond the deviations documented above.

## Threat Model Notes

Per this plan's `<threat_model>`: T-02-05 (Tampering, accept) — a corrupt/unrecognised `localStorage["fpl-theme"]` value falls through to the operating-system result in both the head script and `useTheme`, confirmed by a dedicated test. T-02-06 (Information Disclosure, mitigate) — confirmed no reference to `fonts.googleapis.com` remains in `index.html`; fonts are served from the app's own bundle. T-02-07 (Tampering, mitigate) — `GwBanner` renders `meta.json`'s string fields as JSX children (auto-escaped) and the numeric `gw` only as text, never in a URL, selector, or style value; the failed-query path routes to the fixed `deadline TBC` literal rather than echoing any response content.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `useTheme`/`ThemeToggle`, the full dark token palette, and the `--font-mono` token are ready for Phase 3's pitch UI to build on without any palette restructuring.
- `GwBanner` and the shell-owned `meta.json` query are live on every route already wired through `PageShell` — no further plan in this phase needs to touch the header.
- `frontend/src/lib/deadline.ts`'s formatters and `frontend/src/test/fixtures/meta.json` are available for any later plan that needs deadline/freshness text.
- `PARITY-DEVIATIONS.md` entries 3 and 4 (freshness line, deadline-passed copy) are now implemented, matching their pre-seeded ledger rows exactly.
- No blockers for plans 02-04, 02-05, 02-06.

## Self-Check: PASSED

All 15 created/modified files verified present on disk; all 5 task commit hashes (`4bdc072`, `471c1e1`, `2a3936d`, `8a5bfb4`, `aecd52a`) verified present in `git log`. Full frontend suite (97/97), typecheck, and the production build-purity gate (`BUILD PURITY OK`) all re-confirmed green immediately before writing this summary.

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-01*
