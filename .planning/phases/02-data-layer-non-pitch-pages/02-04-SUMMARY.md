---
phase: 02-data-layer-non-pitch-pages
plan: 04
subsystem: ui
tags: [react, tanstack-query, fdr, watchlist, lucide-react, vitest, parity]

# Dependency graph
requires:
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-01's shared parity utilities (lib/format.ts primitives, the full web/data/*.json TypeScript contract in lib/api.ts) and the StatusFlag accessible-tooltip precedent"
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-02's PARITY-DEVIATIONS.md ledger, pre-seeded with entry 5 (trend icons) attributed to this plan"
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-03's current PageShell chrome — built on top of it without modification"
provides:
  - "frontend/src/components/FdrCell.tsx — the fixture-difficulty cell (blank-gameweek em dash, per-fixture opponent+venue chips styled through an explicit 1-5 literal token map), reusable by any future ticker-shaped table"
  - "Real, fully-ported /fixtures route with data-derived gameweek columns (R20-R24)"
  - "Real, fully-ported /prices route with vanilla's exact progress math, three verbatim mode notes, and new trend icons (R25-R31)"
  - "Four hand-authored parity fixtures: fixtures.json (4 teams/4 gameweeks) and one watchlist fixture per export mode (official/heuristic/model), cross-checked against models/price.py"
affects: [02-05, 02-06, 07]

# Actuals (#2632)
actuals:
  tokens: 10400
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FdrCell's difficulty->token map is an explicit literal object (1-5 keys), never a class name built by string interpolation — Tailwind's build-time scanner cannot see a dynamically-interpolated class name, so an interpolated version would silently emit no colour"
    - "FdrCell exposes its per-cell description via a plain aria-label on a non-interactive <span>, not a StatusFlag-style click-toggle button — the fixtures/prices tables have zero interactive cells (neither is sortable), so an interaction-gated tooltip would be the wrong pattern for data that's already fully visible as text/colour"
    - "Prices' progress math and three mode-note variants are ported as small pure functions (computeProgress, ModeNote) rather than inlined per-row, keeping the R25-R31 rule set independently testable"
    - "price_m/ownership on the Prices page deliberately skip lib/format.ts's orDash — R29/Pitfall 3 requires no fallback at all here, diverging from the xP table's Own % column; the two call sites are not unified"

key-files:
  created:
    - frontend/src/components/FdrCell.tsx
    - frontend/src/components/FdrCell.test.tsx
    - frontend/src/routes/Fixtures.test.tsx
    - frontend/src/routes/Prices.test.tsx
    - frontend/src/test/fixtures/fixtures.json
    - frontend/src/test/fixtures/watchlist_official.json
    - frontend/src/test/fixtures/watchlist_heuristic.json
    - frontend/src/test/fixtures/watchlist_model.json
  modified:
    - frontend/src/routes/Fixtures.tsx
    - frontend/src/routes/Prices.tsx
    - frontend/src/lib/api.ts
    - frontend/src/routes/routeIsolation.test.tsx

key-decisions:
  - "FdrCell's accessible description is a plain aria-label on a <span>, not StatusFlag's click-toggle button pattern — the task text pointed at StatusFlag's approach generically (aria-based description over a bare title), but a literal button-per-fixture-chip would have populated the fixtures table with interactive elements, contradicting the table's own not-sortable/no-buttons requirement."
  - "WatchlistRow.prob/proj_tonight marked optional in lib/api.ts after cross-checking models/price.py directly — official-mode rows never carry a prob key at all, and heuristic-mode rows never carry proj_tonight; the previous non-optional typing didn't reflect the real per-mode shape."

patterns-established: []

requirements-completed: [UI-03, UI-04]

coverage:
  - id: D1
    description: "/fixtures renders one row per club with Team/xG next/xGC next/dynamic gameweek columns/Ease, deriving the gameweek count from the data (never hard-coded to six)."
    requirement: "UI-03"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Fixtures.test.tsx#renders exactly four gameweek column headers, proving the count is data-derived (R20)"
        status: pass
      - kind: other
        ref: "grep -q 'gws.length\\|gws\\.map' + ! grep -q 'gwCount = 6\\|slice(0, 6)' (plan Task 1 automated verify)"
        status: pass
    human_judgment: false
  - id: D2
    description: "FdrCell renders the blank-gameweek em dash (neutral difficulty-3 styling, 'Blank gameweek' description), per-fixture opponent+venue chips coloured by their own fdr value with a distinct token per difficulty 1-5, and clamps an out-of-range fdr to the neutral styling."
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/FdrCell.test.tsx (7 tests)"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Fixtures.test.tsx#collects a distinct background class at every difficulty 1 through 5"
        status: pass
    human_judgment: false
  - id: D3
    description: "The fixtures table's xG next/xGC next fall back to en-dash on null while Ease has no fallback; the table has zero interactive elements (not sortable, matching vanilla) and the legend row renders verbatim."
    requirement: "UI-03"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Fixtures.test.tsx (R23/R24 test, no-buttons test, legend test)"
        status: pass
    human_judgment: false
  - id: D4
    description: "/prices renders Likely risers/Likely fallers from watchlist.json using vanilla's exact raw/pct/bar progress math (bar clamped at 100%, label not) and per-mode label branch."
    requirement: "UI-04"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Prices.test.tsx#shows 114% with the progress bar clamped to 100% ... / #appends the tonight clause only when proj_tonight is non-null / #shows the threshold label in non-official mode when prob is null"
        status: pass
    human_judgment: false
  - id: D5
    description: "Exactly one of three verbatim mode notes renders per w.mode (official/heuristic/trained), with the official note's price-locked-players sentence gated on locked_players truthiness; all three fixtures were cross-checked against models/price.py's actual emitted shapes."
    requirement: "UI-04"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Prices.test.tsx (3 mode-note tests + 1 locked_players=0 test)"
        status: pass
    human_judgment: false
  - id: D6
    description: "net_transfers renders through toLocaleString with a zero fallback (never fixed-decimal); price_m/ownership render through fixed1 with no optional chaining and no en-dash fallback, deliberately diverging from the xP table's Own % column."
    requirement: "UI-04"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Prices.test.tsx#renders net_transfers with locale grouping and no decimal point (R28) / #falls back net_transfers to zero when absent"
        status: pass
      - kind: other
        ref: "grep -q 'toLocaleString'||'localeInt' (plan Task 2 automated verify: NET TRANSFERS LOCALE FORMAT)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Riser rows carry a distinguishable trending-up icon (accent token) and faller rows a trending-down icon (destructive token), which never cross tables; neither price table has any interactive column headers."
    requirement: "UI-04"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Prices.test.tsx#renders distinguishable riser and faller icons that never cross tables / #has no interactive column headers in either table — not sortable"
        status: pass
    human_judgment: false
  - id: D8
    description: "Full frontend Vitest suite, typecheck, and the production build-purity gate all pass with this plan's changes in place."
    verification:
      - kind: other
        ref: "npm --prefix frontend run test (129/129 passed)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck (exit 0)"
        status: pass
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh (BUILD PURITY OK)"
        status: pass
    human_judgment: false
  - id: D9
    description: "Visual spot check in light and dark themes — the difficulty ramp reads easy-to-blue through hard-to-red and the trend icons stay distinguishable at a glance."
    verification: []
    human_judgment: true
    rationale: "The plan's <verification> step 4 is an explicit non-gating manual spot check across both themes — no automated test asserts a colour actually LOOKS easy-to-hard to a human eye; Vitest only proves the underlying class selection is data-correct and distinct per value."

duration: 20min
completed: 2026-09-01
status: complete
---

# Phase 2 Plan 4: Fixtures Ticker & Price Watch Parity Summary

**Fixture-difficulty ticker with data-derived gameweek columns and a literal 1-5 FDR token map, plus a price-watch page carrying vanilla's exact progress math, all three mode-dependent qualifying notes, and new trend icons — both pages verified non-sortable and covered by fixtures cross-checked against `models/price.py`.**

## Performance

- **Duration:** 20 min (approx.)
- **Started:** 2026-09-01T10:38:00Z (approx.)
- **Completed:** 2026-09-01T10:46:00Z (approx.)
- **Tasks:** 2 (both TDD)
- **Files modified:** 12 (8 created, 4 modified)

## Accomplishments
- Ported `FdrCell` — the fixture-difficulty cell — with an explicit literal 1-5 token map (never string-interpolated class names, which Tailwind's build-time scanner can't see), a neutral difficulty-3 blank-gameweek em dash, and out-of-range-value clamping
- Replaced the `/fixtures` placeholder with a real route deriving its gameweek column count from the data (`ticker[0].gws.length`, R20) instead of a hard-coded six, plus the verbatim legend and copy
- Replaced the `/prices` placeholder with a real route porting vanilla's exact `raw`/`pct`/`bar` progress math (bar clamped at 100%, label not) and all three verbatim mode-note variants keyed on `w.mode`
- Added `TrendingUp`/`TrendingDown` trend icons (ledger entry 5, already seeded in `PARITY-DEVIATIONS.md` by plan 02-02) to riser/faller rows
- Authored four hand-checked parity fixtures — one fixtures ticker (4 teams/4 gameweeks covering a blank gameweek, a double gameweek, a null `xg_next`, and all five difficulty values) and three watchlist fixtures (official/heuristic/model), the latter two cross-checked directly against `models/price.py`'s emitted field shapes since the live pipeline has only ever exercised official mode

## Task Commits

Each task was committed atomically (both are `tdd="true"` tasks; both wrote passing tests on first implementation, so no separate RED-only commit was needed beyond the single feat commit per task):

1. **Task 1: Fixtures ticker with the FDR difficulty cell** - `e22c38b` (feat)
2. **Task 2: Price watch page with mode-dependent notes and rise/fall indicators** - `2eb899d` (feat)

## Files Created/Modified
- `frontend/src/components/FdrCell.tsx` / `FdrCell.test.tsx` - Fixture-difficulty cell, literal 1-5 token map
- `frontend/src/routes/Fixtures.tsx` / `Fixtures.test.tsx` - Real, fully-ported fixtures ticker route
- `frontend/src/routes/Prices.tsx` / `Prices.test.tsx` - Real, fully-ported price watch route
- `frontend/src/test/fixtures/fixtures.json` - Hand-authored 4-team/4-gameweek parity fixture
- `frontend/src/test/fixtures/watchlist_official.json` / `watchlist_heuristic.json` / `watchlist_model.json` - One fixture per watchlist export mode
- `frontend/src/lib/api.ts` - `WatchlistRow.prob`/`proj_tonight` marked optional (see Deviations)
- `frontend/src/routes/routeIsolation.test.tsx` - Updated a stale Phase 1 placeholder assertion (see Deviations)

## Decisions Made
- FdrCell's accessible description is a plain `aria-label` on a non-interactive `<span>`, not a StatusFlag-style click-toggle button — a literal per-chip button would have populated the fixtures table with interactive elements, contradicting the table's own not-sortable/no-buttons requirement (verified by `queryAllByRole("button")` being empty in both `Fixtures.test.tsx` and `Prices.test.tsx`).
- `WatchlistRow.prob`/`proj_tonight` marked optional in `lib/api.ts` after cross-checking `models/price.py` directly — official-mode rows never carry a `prob` key, and heuristic/model-mode rows never carry `proj_tonight`; the field shapes genuinely differ by mode, not just by nullability.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `WatchlistRow.prob`/`proj_tonight` were non-optional, breaking the stricter build-mode typecheck**
- **Found during:** Task 2, running `bash scripts/verify_frontend_build.sh`
- **Issue:** `npm run typecheck` (`tsc --noEmit`) passed, but the build's `tsc -b` step failed: the heuristic/model watchlist fixtures (correctly omitting `prob`/`proj_tonight` keys per real `models/price.py` output) didn't satisfy `WatchlistRow`'s non-optional `prob`/`proj_tonight` fields.
- **Fix:** Marked both fields optional (`prob?: number | null; proj_tonight?: number | null;`) in `frontend/src/lib/api.ts`, documenting the per-mode key-absence behavior confirmed by reading `models/price.py` directly. `Prices.tsx`'s existing `??`/`!= null` guards already treat `undefined` the same as `null`, so no runtime logic changed.
- **Files modified:** frontend/src/lib/api.ts
- **Verification:** `npm --prefix frontend run typecheck` and `bash scripts/verify_frontend_build.sh` (`BUILD PURITY OK`) both pass.
- **Committed in:** 2eb899d (Task 2 commit)

**2. [Rule 1 - Bug] `routeIsolation.test.tsx` asserted the Phase 1 placeholder's heading**
- **Found during:** Task 1, running the full suite
- **Issue:** The route-isolation regression test clicked the Fixtures nav link and asserted a heading named "Fixtures" — the Phase 1 `PlaceholderPage`'s literal title. Now that `/fixtures` is the real ported route (h1 "Fixture ticker"), and the test's universal fetch-rejection mock makes the route surface its own `ErrorState`, the old assertion no longer matched anything.
- **Fix:** Updated the assertion to check for the route's own `ErrorState` resource text ("the fixture data"), which still proves route isolation (the sibling route mounted and rendered its own distinct content, not a stale render of the previous route's error) without depending on placeholder copy that no longer exists.
- **Files modified:** frontend/src/routes/routeIsolation.test.tsx
- **Verification:** `npm --prefix frontend run test` — full suite green (129/129).
- **Committed in:** 2eb899d (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking type-shape fix, 1 Rule 1 test-regression fix)
**Impact on plan:** Both were necessary consequences of implementing the plan as written (real fixture-mode-shape fixtures for Task 2; replacing the Fixtures placeholder for Task 1). No scope creep, no architectural change.

## Issues Encountered
None beyond the deviations documented above.

## Threat Model Notes

Per this plan's `<threat_model>`: T-02-08 (Tampering, mitigate) — confirmed `FdrCell` selects its token class from an explicit literal 1-5 map (`FDR_CLASSES`), never by interpolating the source `fdr` value into a class-name string; an out-of-range value clamps to neutral difficulty-3 styling. `FdrCell.test.tsx`'s "clamps an out-of-range fdr value" and "distinct background class per difficulty" tests assert this directly. T-02-09 (Information Disclosure, mitigate) — confirmed `Prices.tsx`'s `ModeNote` branch is driven by the same `w.mode` field as the progress label branch, in the same component render; the three per-mode `Prices.test.tsx` tests each assert exactly one note renders and the other two are absent, so the numbers can never ship without their qualifying context.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `FdrCell.tsx` and the FDR token-map pattern are available to any future page needing difficulty-coloured cells.
- `PARITY-DEVIATIONS.md` entry 5 (trend icons) is now implemented exactly as pre-seeded — confirmed present, no new ledger row needed.
- `lib/api.ts`'s `WatchlistRow` interface now accurately models the per-mode field-presence shape confirmed against `models/price.py`, so any later plan reading watchlist data inherits the corrected typing.
- No blockers for plans 02-05, 02-06.

## Self-Check: PASSED

All 12 created/modified files verified present on disk; both task commit hashes (`e22c38b`, `2eb899d`) verified present in `git log`. Full frontend suite (129/129), typecheck, and the production build-purity gate (`BUILD PURITY OK`) all re-confirmed green immediately before writing this summary.

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-01*
