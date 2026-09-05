---
phase: 02-data-layer-non-pitch-pages
plan: 01
subsystem: ui
tags: [react, tanstack-query, tailwind-v4, vitest, testing-library, xp-table, sort, accessibility]

# Dependency graph
requires:
  - phase: 01-test-base-layer-app-skeleton
    provides: React/Vite app skeleton, PageShell, Spinner/ErrorState/EmptyState, fetchJson/fetchApi, Vitest+Testing Library harness
provides:
  - "Complete web/data/*.json TypeScript interface set in frontend/src/lib/api.ts (13 interfaces) — no later Phase 2 plan needs to edit this file"
  - "Ported, Node-verified sortRows/useSortable comparator (frontend/src/lib/sortable.ts) reusable by any future sortable table"
  - "bandGeometry/bandTooltip + <BandCell> (frontend/src/lib/bandCell.ts, frontend/src/components/BandCell.tsx) reusable by Differentials (plan 02-04)"
  - "format.ts primitives (fixed1/fixed2/orDash/localeInt) for per-page composition"
  - "<StatusFlag> accessible tooltip component (frontend/src/lib/statusFlag.tsx) reusable by Differentials (plan 02-04)"
  - "usePageMeta hook + 8-route PAGE_META table (frontend/src/lib/usePageMeta.ts) for all remaining phase-2 pages"
  - "Real, fully-ported xP table route (frontend/src/routes/XpTable.tsx) — flagship parity reference for the rest of the phase"
affects: [02-02, 02-03, 02-04, 02-05, 02-06]

# Actuals (#2632)
actuals:
  tokens: 15006
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sort comparator ported verbatim from web/assets/app.js with the verified (counter-intuitive) dir=-1-is-ascending/▼ polarity locked in by a dedicated test file (RESEARCH.md Pitfall 1)"
    - "Format helpers are primitives only (fixed1/fixed2/orDash/localeInt) — never a per-field formatter — so each page composes its own vanilla-verbatim fallback behavior instead of a unified rule erasing real per-page differences (Pitfall 3)"
    - "Band cell width uses a CSS calc() string built from two independently-clamped percentages, not a pre-subtracted JS number (Pitfall 4)"
    - "usePageMeta's PAGE_META table is typed via `keyof typeof PAGE_META` (inferred), not a separate interface — keeps the phase's structural completeness check (exactly 8 `description:` entries) meaningful"
    - "StatusFlag's tooltip opens on hover/focus/click-toggle and closes on Escape/click-outside — a document-level listener pair scoped to `open` state, cleaned up per toggle"
    - "Tests for a route with two concurrent TanStack queries mock fetch by URL, not call order or a single shared body, and scope DOM queries to each table's accessible name (aria-label) to avoid cross-table text collisions"

key-files:
  created:
    - frontend/src/lib/format.ts
    - frontend/src/lib/format.test.ts
    - frontend/src/lib/sortable.ts
    - frontend/src/lib/sortable.test.ts
    - frontend/src/lib/bandCell.ts
    - frontend/src/lib/bandCell.test.ts
    - frontend/src/lib/usePageMeta.ts
    - frontend/src/lib/usePageMeta.test.tsx
    - frontend/src/lib/statusFlag.tsx
    - frontend/src/lib/statusFlag.test.tsx
    - frontend/src/components/BandCell.tsx
    - frontend/src/routes/XpTable.test.tsx
    - frontend/src/test/fixtures/xp_table.json
    - frontend/src/test/fixtures/captains.json
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/routes/XpTable.tsx
    - frontend/src/components/Spinner.test.tsx
    - frontend/src/components/ErrorState.test.tsx
    - frontend/tsconfig.app.json

key-decisions:
  - "Preserved vanilla's literal 'undefined' text for a null captains ownership value (R18/Pitfall 3) instead of unifying it with the main table's en-dash fallback — documented parity requirement, not a bug to fix."
  - "Added aria-label 'xP table' / 'Captain picks' to the two tables so tests (and assistive tech) can disambiguate rows once both tables can legitimately render overlapping player names."
  - "Enabled resolveJsonModule in tsconfig.app.json so fixture JSON can be imported directly into Vitest files rather than fetched/parsed at runtime in tests."

patterns-established:
  - "Vanilla-port utilities live in frontend/src/lib/*.ts as small, directly-testable pure functions (sortRows, bandGeometry/bandTooltip, fixed1/fixed2/orDash/localeInt), separated from the React components that consume them."
  - "Accessible-upgrade components (StatusFlag) keep the exact vanilla trigger/glyph/label logic and only change the interaction/reveal mechanism, with the deviation reasoning documented inline for PARITY-DEVIATIONS.md (plan 02-02) to pick up."

requirements-completed: [UI-02]

coverage:
  - id: D1
    description: "The xP table renders the top-50 rows from /data/xp_table.json with all 7 columns (Pos, Player, Team, £m, Own %, xP band, Captain xP) at vanilla number formats, including per-field null fallbacks."
    requirement: "UI-02"
    verification:
      - kind: integration
        ref: "frontend/src/routes/XpTable.test.tsx#XpTable (Task 1 — end-to-end slice)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/format.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sort direction and header glyph match the Node-verified vanilla polarity (fresh click ascending/▼, second click descending/▲, nulls first-then-last)."
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/sortable.test.ts"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/XpTable.test.tsx#clicking the £m header once sorts ascending with ▼, clicking again sorts descending with ▲"
        status: pass
    human_judgment: false
  - id: D3
    description: "Position chips (ALL/GK/DEF/MID/FWD) and case-insensitive search filter the xP table with vanilla's exact AND-composed predicate, applied only to the already-sliced top 50."
    requirement: "UI-02"
    verification:
      - kind: integration
        ref: "frontend/src/routes/XpTable.test.tsx#XpTable (Task 2 — filters, verbatim copy, page meta)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Captain picks sub-table renders exactly 5 rows from captains.json with no sort/filter, the full club name, and its own divergent (no-en-dash) ownership fallback."
    requirement: "UI-02"
    verification:
      - kind: integration
        ref: "frontend/src/routes/XpTable.test.tsx#XpTable (Task 3 — status flag + captain picks)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Flagged players (status !== 'a') carry a keyboard- and touch-accessible status flag with vanilla's exact glyph/aria-label mapping; available players carry no flag element."
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/statusFlag.test.tsx"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/XpTable.test.tsx#mounts a StatusFlag for a flagged player and none for an available one"
        status: pass
    human_judgment: false
  - id: D6
    description: "The complete web/data/*.json TypeScript interface set (13 interfaces) exists in frontend/src/lib/api.ts so no later Phase 2 plan needs to edit that file."
    requirement: "UI-02"
    verification:
      - kind: other
        ref: "npm --prefix frontend run typecheck"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full frontend Vitest suite, typecheck, and the production build-purity gate all pass with this plan's changes in place."
    verification:
      - kind: other
        ref: "npm --prefix frontend run test (58/58)"
        status: pass
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh (BUILD PURITY OK)"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-09-01
status: complete
---

# Phase 2 Plan 1: xP Table Parity Port Summary

**Ports the flagship xP table to verified vanilla parity — Node-verified sort polarity, CSS-calc band cells, position/search filters, an accessible status-flag tooltip, and a divergent-fallback Captain picks sub-table — while landing the complete `web/data/*.json` TypeScript contract for the rest of the phase.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-09-01T13:29:00Z (approx.)
- **Completed:** 2026-09-01T14:04:00Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 19 (14 created, 5 modified)

## Accomplishments
- Ported `makeSortable`'s exact (counter-intuitive) sort comparator with a Node-verified regression test locking in the fresh-click-ascending/▼ polarity (RESEARCH.md Pitfall 1)
- Ported `bandCell`'s geometry/tooltip math with a CSS `calc()` width expression, not a pre-subtracted number (Pitfall 4)
- Landed the complete 13-interface `web/data/*.json` TypeScript contract in `frontend/src/lib/api.ts` up front, so plans 02-03 through 02-06 never need to touch that file
- Replaced the Phase 1 tracer with the real, sortable, filterable top-50 xP table wired to `/data/xp_table.json`
- Added the accessible `StatusFlag` tooltip (hover/focus/click-toggle, Escape/click-outside dismissal) and the Captain picks sub-table with its deliberately divergent ownership fallback

## Task Commits

Each task was committed atomically (Tasks 2 and 3 follow full RED→GREEN TDD cycles):

1. **Task 1: End-to-end xP table slice (JSON contract → sort → band cell → table)** - `46f858f` (feat)
2. **Task 2 RED: failing tests for filters/copy/page-meta** - `6cdde82` (test)
2. **Task 2 GREEN: implement filters/copy/page-meta** - `a090dde` (feat)
3. **Task 3 RED: failing tests for status flag/captain picks** - `fceb326` (test)
3. **Task 3 GREEN: implement status flag/captain picks** - `f1a7ebe` (feat)

_No REFACTOR commits — both TDD implementations stayed minimal and clean through GREEN._

## Files Created/Modified
- `frontend/src/lib/api.ts` - Added the full 13-interface web/data/*.json TypeScript contract
- `frontend/src/lib/format.ts` / `format.test.ts` - fixed1/fixed2/orDash/localeInt primitives
- `frontend/src/lib/sortable.ts` / `sortable.test.ts` - Ported, Node-verified sort comparator + useSortable hook
- `frontend/src/lib/bandCell.ts` / `bandCell.test.ts` - Band geometry/tooltip math
- `frontend/src/components/BandCell.tsx` - Band cell component (CSS calc() width, design tokens only)
- `frontend/src/lib/usePageMeta.ts` / `usePageMeta.test.tsx` - Per-route title/meta-description hook, 8-route table
- `frontend/src/lib/statusFlag.tsx` / `statusFlag.test.tsx` - Accessible status-flag tooltip component
- `frontend/src/routes/XpTable.tsx` - Real, fully-ported flagship xP table route
- `frontend/src/routes/XpTable.test.tsx` - Full behavioral test suite for the route (27 tests)
- `frontend/src/test/fixtures/xp_table.json` / `captains.json` - Hand-authored parity fixtures
- `frontend/src/components/Spinner.test.tsx` - Updated Phase 1 loading-backstop assertion for the new route content
- `frontend/src/components/ErrorState.test.tsx` - Updated Phase 1 retry-count assertion for two concurrent queries
- `frontend/tsconfig.app.json` - Enabled resolveJsonModule for fixture imports

## Decisions Made
- Preserved vanilla's literal "undefined" text for a null captains-table ownership value (R18/Pitfall 3) rather than unifying it with the main table's en-dash fallback — this is documented parity, not a bug.
- Added `aria-label="xP table"` / `"Captain picks"` to the two tables so both tests and assistive tech can disambiguate rows once both tables can render overlapping player names (e.g. "Haaland" in both).
- Enabled `resolveJsonModule` in `tsconfig.app.json` so fixture JSON imports directly into Vitest files rather than requiring a runtime fetch/parse in tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Spinner.test.tsx's stale Phase 1 backstop assertion**
- **Found during:** Task 1
- **Issue:** The Phase 1 loading-backstop test asserted the tracer's placeholder text ("Gameweek 5"), which no longer exists once XpTable became the real, fully-ported table.
- **Fix:** Updated the resolved-fetch payload to a real xp_table.json-shaped row and asserted the player's name renders once loading clears.
- **Files modified:** frontend/src/components/Spinner.test.tsx
- **Verification:** `npm --prefix frontend run test` — full suite green.
- **Committed in:** 46f858f (Task 1 commit)

**2. [Rule 3 - Blocking] Enabled resolveJsonModule for fixture imports**
- **Found during:** Task 1
- **Issue:** `import fixtureRows from "../test/fixtures/xp_table.json"` failed to typecheck without `resolveJsonModule` in tsconfig.app.json.
- **Fix:** Added `"resolveJsonModule": true` to `frontend/tsconfig.app.json`.
- **Files modified:** frontend/tsconfig.app.json
- **Verification:** `npm --prefix frontend run typecheck` exits 0.
- **Committed in:** 46f858f (Task 1 commit)

**3. [Rule 1 - Bug] Fixed ErrorState.test.tsx's fetch-call-count assumption**
- **Found during:** Task 3
- **Issue:** The Phase 1 retry-count backstop asserted exactly 1 total fetch call, which broke once the "/" route began firing two concurrent queries (xp_table.json + captains.json, Task 3).
- **Fix:** Rewrote the mock to route by URL and track calls to `/data/xp_table.json` specifically — the primary data source this test is actually about — rather than the raw mock's overall call count.
- **Files modified:** frontend/src/components/ErrorState.test.tsx
- **Verification:** `npm --prefix frontend run test` — full suite green (58/58).
- **Committed in:** f1a7ebe (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 test-regression fixes, 1 Rule 3 blocking tsconfig fix)
**Impact on plan:** All three were necessary consequences of implementing the plan as written (replacing the tracer, adding a second concurrent query) — no scope creep, no architectural change.

## Issues Encountered
None beyond the deviations documented above.

## Threat Model Notes

Per this plan's `<threat_model>`: T-02-01 (Tampering, mitigate) — confirmed `dangerouslySetInnerHTML` is not used anywhere under `frontend/src` after this plan. T-02-02 (Information Disclosure, mitigate) — `ErrorState`'s resource-only rendering preserved; the fixed `ErrorState.test.tsx` assertion continues to prove the thrown error's message/URL never reach the DOM. T-02-03 (DoS, accept) — the `slice(0, 50)` cap is unchanged.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `frontend/src/lib/api.ts`'s full interface set, `sortable.ts`, `bandCell.ts`/`BandCell.tsx`, `format.ts`, and `statusFlag.tsx` are ready for reuse by plan 02-04 (Fixtures/Prices/League/Differentials) and beyond.
- `usePageMeta.ts`'s 8-route table is ready for every remaining route in this phase to call.
- `PARITY-DEVIATIONS.md` does not exist yet — per the phase's UI-SPEC artifact table it is created in plan 02-02; the deviations logged above (accessible StatusFlag tooltip, rich ErrorState reuse) are ready to seed it.
- No blockers for plan 02-02.

## Self-Check: PASSED

All 19 created/modified files verified present on disk; all 5 task commit hashes (`46f858f`, `6cdde82`, `a090dde`, `fceb326`, `f1a7ebe`) verified present in `git log`. Full frontend suite (58/58), typecheck, and the production build-purity gate (`BUILD PURITY OK`) all re-confirmed green immediately before writing this summary.

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-01*
