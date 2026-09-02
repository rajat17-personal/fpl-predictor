---
phase: 02-data-layer-non-pitch-pages
plan: 08
subsystem: ui
tags: [react, tailwind, vitest, css-parity, gap-closure]

# Dependency graph
requires:
  - phase: 02-data-layer-non-pitch-pages
    provides: FdrCell and Fixtures route from plan 02-01/02-04's fixtures ticker port, and
      plan 02-07's token-gate wiring into `npm run test` that this plan's test runs now exercise
provides:
  - Column-stacked, monospace, minimum-width fixture chip in FdrCell.tsx matching vanilla's
    web/assets/style.css `.fdr small { display: block }` layout
  - Geometry regression tests in FdrCell.test.tsx pinning class-list contracts (jsdom applies no
    stylesheet, so this is the only gate that can catch a reversion to row-direction or a
    stripped minimum width)
  - Vanilla's tight fixture-specific gameweek-cell padding (4px/3px) restored in Fixtures.tsx,
    scoped to the ticker column only, with a matching Fixtures.test.tsx assertion
affects: [phase-02-uat, phase-07-cutover]

actuals:
  tokens: 2070
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Class-list substring assertions (not computed style) for jsdom geometry regression
       tests — jsdom applies no stylesheet, so the Tailwind class contract IS the layout
       contract worth pinning"

key-files:
  created: []
  modified:
    - frontend/src/components/FdrCell.tsx
    - frontend/src/components/FdrCell.test.tsx
    - frontend/src/routes/Fixtures.tsx
    - frontend/src/routes/Fixtures.test.tsx

key-decisions:
  - "Adopted vanilla's mono family and 0.75 venue-tag opacity (no size change) but deliberately
     did NOT adopt vanilla's smaller chip/venue font sizes, per the plan's gap-coverage audit —
     doing so would contradict PARITY-DEVIATIONS.md entry 7 (sub-14px vanilla chrome renders at
     the 14px Label token) and the four-size typography contract. No new ledger entry needed:
     every change in this plan moves the port toward vanilla."

requirements-completed: [UI-03]

coverage:
  - id: D1
    description: "Venue letter renders on its own line, centred beneath the opponent code, in
      both the populated and blank-gameweek chip branches"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "frontend/src/components/FdrCell.test.tsx#FdrCell geometry contract (UAT gap G-02-2) > stacks the populated chip in a column direction..."
        status: pass
      - kind: unit
        ref: "frontend/src/components/FdrCell.test.tsx#FdrCell geometry contract (UAT gap G-02-2) > stacks the blank-gameweek chip in the same column direction..."
        status: pass
    human_judgment: true
    rationale: "The class-list assertions prove Tailwind compiles the intended column-direction
      layout, but jsdom applies no stylesheet — whether the rendered result visually matches
      vanilla's stacked chip is deferred to the plan's own <human-check>, batched into
      end-of-phase UAT per workflow.human_verify_mode=end-of-phase."
  - id: D2
    description: "Every chip, populated or blank, carries its own 56px minimum width; the
      wrapper carries none"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "frontend/src/components/FdrCell.test.tsx#FdrCell geometry contract (UAT gap G-02-2) > carries the 56px minimum width on the populated chip itself, not on the wrapper"
        status: pass
      - kind: unit
        ref: "frontend/src/components/FdrCell.test.tsx#FdrCell geometry contract (UAT gap G-02-2) > gives both chips of a double gameweek their own 56px minimum width independently"
        status: pass
    human_judgment: false
  - id: D3
    description: "Gameweek cells use vanilla's tight fixture padding (4px/3px); the four
      non-ticker cells and header cells keep the generic padding"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "frontend/src/routes/Fixtures.test.tsx#gives gameweek cells vanilla's tight fixture-specific padding"
        status: pass
      - kind: other
        ref: "grep -c 'px-3 py-2' frontend/src/routes/Fixtures.tsx == 5 (EYEBROW_TH + 4 non-ticker cells)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Chip renders in the monospace family with the venue tag at 75 percent
      opacity; no new font size or weight introduced"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "frontend/src/components/FdrCell.test.tsx#FdrCell geometry contract (UAT gap G-02-2) > renders the chip in the monospace family and de-emphasises the venue tag at 75 percent opacity"
        status: pass
    human_judgment: false
  - id: D5
    description: "A regression that returns the chip to a single row, or strips its minimum
      width, fails the frontend test command"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "frontend/src/components/FdrCell.test.tsx (6 geometry assertions, RED-confirmed against pre-fix component)"
        status: pass
    human_judgment: false

duration: ~2min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 08: Fixture chip venue-label stacking (UAT gap G-02-2) Summary

**Restored vanilla's column-stacked fixture chip (venue letter beneath opponent code, chip-owned 56px min-width, mono family, tight ticker-cell padding) with new geometry regression tests that pin the class contract jsdom cannot verify via computed style.**

## Performance

- **Duration:** ~2 min (three small, tightly-scoped commits)
- **Tasks:** 3
- **Files modified:** 4 (0 created, 4 modified)

## Accomplishments

- Added a `FdrCell` geometry describe block (6 new assertions) that failed 5/6 against the
  shipped row-direction chip and passed the one markup-shape assertion that already held —
  confirming RED before any implementation change, exactly as the plan required.
- Switched both `FdrCell` branches (populated and blank-gameweek) to column-direction flex,
  moved the 56px minimum width off the wrapper and onto each chip, swapped the chip's font
  family from the sans Label token to the mono token, and added 75% opacity to the venue tag —
  reproducing `web/assets/style.css:152-155` exactly, with no new font size or weight.
- Restored vanilla's tight fixture-specific gameweek-cell padding (`px-1 py-[3px]`, was the
  generic `px-3 py-2`) scoped to the ticker column only; the four non-ticker cells and the
  header cells keep the generic padding untouched.
- All 7 pre-existing `FdrCell` tests and all 12 pre-existing `Fixtures` tests remain unmodified
  and green throughout — the diagnosis's premise (they query text/accessible-names only, so a
  layout regression is invisible to them) held exactly as predicted.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin the chip geometry with failing regression assertions** - `a4ce30a` (test)
2. **Task 2: Stack the venue tag beneath the opponent code and give every chip its own minimum width** - `22e07fa` (fix)
3. **Task 3: Restore vanilla's tight gameweek-cell padding so the taller chip does not inflate the table** - `702ae4b` (fix)

## Files Created/Modified

- `frontend/src/components/FdrCell.test.tsx` - Added geometry describe block (6 tests) pinning
  column-direction, chip-owned min-width, mono family, and venue-tag opacity
- `frontend/src/components/FdrCell.tsx` - Column-direction chip, chip-owned 56px min-width, mono
  family, 75% opacity venue tag, updated header comment naming G-02-2
- `frontend/src/routes/Fixtures.tsx` - Gameweek cell padding changed from generic `px-3 py-2` to
  vanilla's tight `px-1 py-[3px]`, scoped to the ticker cell only
- `frontend/src/routes/Fixtures.test.tsx` - Added assertion that a gameweek `<td>` carries the
  tight vertical padding utility

## Decisions Made

- Adopted vanilla's mono family and 75% venue-tag opacity but not its smaller chip/venue font
  sizes — see key-decisions in frontmatter; already governed by PARITY-DEVIATIONS.md entry 7,
  no new ledger entry required.
- Followed the plan's TDD sequencing literally: Task 1 wrote and confirmed RED, Task 2 made
  the whole `FdrCell` suite GREEN, Task 3 (plain `auto`, no tdd flag) added its own test alongside
  the implementation change in one commit, matching the plan's task-type split.

## Deviations from Plan

None - plan executed exactly as written. All five gap-coverage-audit items (column stack, chip
min-width, tight cell padding, mono family + opacity, geometry regression test) were delivered
by the tasks the plan assigned them to.

## Issues Encountered

None. The RED-phase failure counts matched exactly what the diagnosis predicted: 5 of 6 new
assertions failed against the pre-fix component (min-width, column-direction, mono family,
opacity), and the one assertion pinning the existing markup shape (small element's parent is
the chip) passed unchanged both before and after.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `FdrCell` and `Fixtures` test suites now carry a geometry gate that fails the standard
  `npm run test` command if the chip ever reverts to a single row or loses its minimum width —
  closing the exact blind spot the diagnosis identified (text/accessible-name queries pass
  identically under either layout).
- Human visual confirmation of the stacked chip on `/fixtures` against `web/fixtures.html` (the
  plan's own `<human-check>`) is deferred to the end-of-phase UAT batch per
  `workflow.human_verify_mode: end-of-phase` — not yet performed by this executor run. This
  closes out UAT gap G-02-2's re-verification once that batch runs.
- No new PARITY-DEVIATIONS.md entry required — every change in this plan moves the port toward
  vanilla; the one remaining delta (chip font size) is already covered by existing entry 7.

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: frontend/src/components/FdrCell.tsx
- FOUND: frontend/src/components/FdrCell.test.tsx
- FOUND: frontend/src/routes/Fixtures.tsx
- FOUND: frontend/src/routes/Fixtures.test.tsx
- FOUND: commit a4ce30a (Task 1)
- FOUND: commit 22e07fa (Task 2)
- FOUND: commit 702ae4b (Task 3)
- Re-ran `npm --prefix frontend run test` (token gate + 178 Vitest tests) and
  `npm --prefix frontend run build` (tsc -b + vite build): both green.
- Re-ran all plan `<verification>` items: geometry describe block RED-before/GREEN-after
  confirmed via git history; seven original FdrCell tests unchanged; full suite 178/178;
  build succeeds; both FdrCell branches carry identical utilities (verified by tests);
  four non-ticker cells retain generic padding (grep count 5); human check deferred per config.
