---
phase: 03-pitch-renderer-squad-views
plan: 05
subsystem: ui
tags: [react, css, flexbox, pitch-renderer, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 03-pitch-renderer-squad-views
    provides: "The shared Pitch/PitchRow component, index.css design tokens, and the pitch-row-centering-drift.md root-cause diagnosis (03-01 through 03-04, plus the standalone gap-closure debug session)"
provides:
  - "Continuously-centered PitchRow layout (flex + fixed flex-basis measure) — exact centering at every row size, no integer-quantized grid placement"
  - "--pitch-gap responsive custom property in index.css, readable from inside calc()"
  - "Symmetry regression suite in Pitch.test.tsx covering row sizes 1-6"
  - "Corrected 03-UI-SPEC.md Layout subsection documenting the shipped mechanism and both rejected alternatives"
affects: [pitch-renderer, squad-views, rate-my-team, solve-preview]

# Actuals (#2632)
actuals:
  tokens: 3094
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Row centering via CSS flexbox (display:flex; justify-content:center) with a fixed calc()-derived flex-basis, replacing integer CSS-grid start-column placement — supersedes the pattern recorded at 03-01-SUMMARY.md L29"
    - "Design tokens that must be read inside a calc() live in a plain CSS custom property (--pitch-gap), not a Tailwind utility class, which calc() cannot see"

key-files:
  created: []
  modified:
    - frontend/src/index.css
    - frontend/src/components/pitch/Pitch.tsx
    - frontend/src/components/pitch/Pitch.test.tsx
    - .planning/phases/03-pitch-renderer-squad-views/03-UI-SPEC.md

key-decisions:
  - "Continuous flex centering (Option B from the debug session's fix_direction) over a doubled 10-column grid — smallest diff, no gap-to-padding surgery, and it is the mechanism 03-UI-SPEC.md now documents"
  - "minWidth set as the literal string \"0px\" (not the number 0) on the implementation side, to avoid React's numeric-zero-suppresses-unit-suffix quirk producing an ambiguous inline style the jsdom regression test could misread"
  - "Added the literal term 'flex-basis' to 03-UI-SPEC.md's prose to satisfy the plan's own anti-regression grep gate, which greps for that string — a Rule 3 (blocking) fix, not a content change"
  - "Deferred Task 1's <human-check> (visual pitch-centering re-verification in a browser at desktop/375px, light/dark, 3-5-2 and 4-4-2) to the next verify-work/UAT pass — HUMAN_VERIFY_MODE is 'end-of-phase' project-wide and no Playwright/screenshot tooling exists yet in this milestone (E2E suite is a later phase per PROJECT.md); every automated gate in Task 1's <verify> block passed. The frontend dev server (localhost:5173/team) and API (localhost:8000) were already running throughout this plan and remain live for that check."

patterns-established:
  - "Pitch row centering via flex + calc()-derived flex-basis (parts = max(5, cardCount)), continuous and exact at every row size — supersedes the integer grid-column start pattern from 03-01"

requirements-completed: [PITCH-02, UI-07]

coverage:
  - id: D1
    description: "Every formation row (GK/DEF/MID/FWD) and the bench render continuously centered on the pitch midline at every row size 1-6, with no integer-quantized column placement; D-07's 5-part no-reflow ceiling and the ghost row's 6-part growth are preserved"
    requirement: "PITCH-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/pitch/Pitch.test.tsx#Pitch — row centering (G-03-1)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/pitch/Pitch.test.tsx (full file, 12/12 including 6 pre-existing)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run test (full suite, 363/363 including token-budget gate)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck && bash scripts/verify_frontend_build.sh"
        status: pass
    human_judgment: true
    rationale: "jsdom has no layout engine, so the automated suite asserts the declared layout model (inline flex/basis/grow/min-width and a derived symmetry oracle), not measured pixels. The plan's own <verify> block requires a human to confirm the actual rendered result in a browser at desktop and 375px, light and dark, on the 3-5-2 model squad and a loaded 4-4-2 entry — that check is deferred to the next UAT pass per HUMAN_VERIFY_MODE=end-of-phase (see key-decisions)."
  - id: D2
    description: "03-UI-SPEC.md's Layout subsection describes the continuous-centering mechanism and max(5, cardsInRow) measure that shipped, names --pitch-gap and why it is a custom property, and records both rejected mechanisms by concept with a citation to the debug session"
    requirement: "UI-07"
    verification:
      - kind: other
        ref: "grep -q 'flex-basis' && grep -q -- '--pitch-gap' (spec + Pitch.tsx + index.css) => SPEC DOCUMENTS THE MECHANISM THAT SHIPPED"
        status: pass
      - kind: other
        ref: "grep -q 'pitch-row-centering-drift' 03-UI-SPEC.md => DEFECT RATIONALE CITED"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-09-03
status: complete
---

# Phase 3 Plan 5: Pitch Row Centering Gap Closure Summary

**Replaced integer CSS-grid start-column row centering with continuous flexbox centering (fixed `flex-basis` measure via a `--pitch-gap` custom property), closing UAT gap G-03-1 where every even-cardinality formation row and the bench sat half a column-pitch left of the pitch midline.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-09-03T11:02:23Z
- **Completed:** 2026-09-03T11:09:08Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Root-caused defect (integer grid-column placement cannot express the half-track offset an even-cardinality row needs against a fixed 5-column odd track set) replaced with continuous flex centering — exact at every row size, no parity condition
- New symmetry regression suite in `Pitch.test.tsx` spans row sizes 1-6, naming both previously-drifting even rows (2-card Forwards, 4-card Bench) and the three odd controls (1, 3, 5) that must not move, plus the ghost-grown 6-part row — closes the coverage hole that let a pure, trivially-unit-testable arithmetic function ship wrong
- `--pitch-gap` responsive custom property (4px below 480px, 8px at/above) lifted out of Tailwind gap utilities so the card measure's `calc()` can subtract it
- `03-UI-SPEC.md`'s Layout subsection corrected to document the shipped mechanism and record both rejected mechanisms (the original `justify-content: center` no-op prescription, and the integer-start-column scheme it provoked) so the next implementer cannot re-derive either

## Task Commits

Each task was committed atomically:

1. **Task 1: Center every formation row continuously — design token through row layout to rendered DOM** - `25a7244` (fix, tdd)
2. **Task 2: Correct the UI-SPEC's row-centering mechanism so the defect is not re-derived** - `4e83899` (docs)

_Note: Task 1 carried `tdd="true"`; see TDD Gate Compliance below._

## Files Created/Modified

- `frontend/src/index.css` - Adds `--pitch-gap` custom property to the author `:root` block plus a `@media (min-width: 480px)` override, derived from the existing `--spacing-xs`/`--spacing-sm` tokens
- `frontend/src/components/pitch/Pitch.tsx` - Removes `centeredStartColumn()` and integer `gridColumn`/`gridTemplateColumns` placement; adds `rowParts()`/`cardMeasure()` helpers and a flex row (`display:flex; justify-content:center; gap:var(--pitch-gap)`) with per-cell `flexGrow:0; flexShrink:1; flexBasis: calc(...); minWidth:"0px"`
- `frontend/src/components/pitch/Pitch.test.tsx` - Adds a `Pitch — row centering (G-03-1)` describe block: layout-mode, no-grid-placement, shared-basis/part-count, zero-grow/zero-min-width, and a symmetry-oracle assertion per row size (1-6) at both UAT viewports
- `.planning/phases/03-pitch-renderer-squad-views/03-UI-SPEC.md` - Rewrites the Layout subsection (retitled "continuous flex centering, verified 5-part ceiling") to match the shipped mechanism, names `--pitch-gap`, and records both rejected mechanisms with a citation to the debug session

## Decisions Made

- Continuous flex centering (the debug session's recommended Option B) chosen over the alternative doubled 10-column grid — smallest diff, no gap-to-padding conversion needed, and it is what `03-UI-SPEC.md` now documents as canonical
- `minWidth` set as the literal string `"0px"` rather than the number `0` on the cell wrapper, sidestepping React's inline-style zero/unit-suffix ambiguity and giving the jsdom regression test a deterministic value to read
- Added the literal term `flex-basis` to `03-UI-SPEC.md`'s prose specifically to satisfy the plan's own automated verify gate, which greps for that exact string (Rule 3 — blocking issue, not a content change)
- Deferred Task 1's `<human-check>` (visual re-verification of UAT test 1 at desktop/375px, light/dark, 3-5-2 and 4-4-2) to the next `/gsd-verify-work` pass — see "Deviations from Plan" below

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added the literal string "flex-basis" to 03-UI-SPEC.md**
- **Found during:** Task 2 (correcting the UI-SPEC's Layout subsection)
- **Issue:** The plan's own automated verify command (`grep -q 'flex-basis' ...`) requires the literal term to appear in the spec; the first draft described the measure only via the `calc(...)` expression without naming the CSS property it becomes
- **Fix:** Reworded the shared-row bullet to say "a fixed `flex-basis` measure of `calc(...)`" — a wording addition, not a mechanism change
- **Files modified:** `.planning/phases/03-pitch-renderer-squad-views/03-UI-SPEC.md`
- **Verification:** `grep -q 'flex-basis' ... && echo "SPEC DOCUMENTS THE MECHANISM THAT SHIPPED"` passes
- **Committed in:** `4e83899` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial wording fix required by the plan's own verify gate. No scope creep, no mechanism change.

**Deferred, not auto-fixed:**

**Task 1's `<human-check>` visual re-verification of UAT test 1** — not run in this session. `HUMAN_VERIFY_MODE` is `end-of-phase` project-wide (`.planning/config.json`), and no Playwright/screenshot tooling exists yet in this milestone (the Playwright E2E suite is a later phase per `PROJECT.md`), so there is no automated way to capture a real rendered screenshot for evidence. All 6 automated `<verify>` checks in Task 1 passed (targeted test file, full 363-test suite + token-budget gate, typecheck + build-purity gate, the integer-column-placement anti-regression grep, the `--pitch-gap` structural check, and the dependency-set-unchanged check). The frontend dev server (`localhost:5173/team`) and the FastAPI backend (`localhost:8000`) were already running throughout this plan and remain live — the human check is a single visual pass at `/team`, desktop width and 375px, light and dark mode, on the default 3-5-2 model squad and a loaded 4-4-2 entry, confirming the 2-card Forwards row, 4-card bench, 4-card Defenders/Midfielders rows are now centered on the SVG midline while GK/3-card/5-card rows are unmoved.

## TDD Gate Compliance

Task 1 carried `tdd="true"`. The RED/GREEN cycle was followed in process:

- **RED:** The full `Pitch — row centering (G-03-1)` test block was written first and run against the pre-fix implementation. Result: 6 of 12 tests failed (all 6 new row-centering assertions; `centers the Goalkeeper/Defenders/Midfielders/Forwards/Bench row...` and `grows the ghost-holding Midfielders row...`), with the first failure being `expected '' to be 'flex'` — exactly the expected failure mode described in the plan (the row's layout mode was a Tailwind class, invisible to jsdom, so nothing was declared inline for the test to read). The 6 pre-existing assertions passed unchanged.
- **GREEN:** `index.css` and `Pitch.tsx` were then implemented per the plan's `<action>`. Re-run: 12/12 pass.

Both phases were verified as described, but committed as a single atomic `fix(03-05): ...` commit (`25a7244`) rather than as separate `test(...)` → `feat(...)` commits. This plan's frontmatter is `type: execute` (not `type: tdd`), so the whole-plan RED/GREEN/REFACTOR gate-commit sequence in the plan-level TDD enforcement section does not apply; the task-level `tdd="true"` attribute's guidance for split commits was not followed for this task. No functional impact — the RED-phase failure output above is the evidence trail in lieu of a separate `test()` commit.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- G-03-1 is closed pending the deferred human visual re-check noted above (dev server already running at `localhost:5173/team`, API at `localhost:8000`).
- `03-UAT.md`'s gap G-03-1 entry should be updated to reference this plan (`03-05`) once the human re-check confirms the fix, so the phase's overall UAT record reflects closure.
- No other blockers for Phase 3 completion; the shared `PitchRow` component now serves every squad view (Squad, Rate, solve preview) with the corrected centering, confirmed by the full 363-test suite passing.

---
*Phase: 03-pitch-renderer-squad-views*
*Completed: 2026-09-03*
