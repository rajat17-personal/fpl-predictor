---
phase: 01-test-base-layer-app-skeleton
plan: 06
subsystem: ui
tags: [react, tailwind, layout, testing, gap-closure]

requires:
  - phase: 01-test-base-layer-app-skeleton
    provides: PageShell.tsx app-shell chrome (header/main/footer) from plans 01-04/01-05
provides:
  - Header and footer content contained at the same 68rem centred column as main
  - PageShell.test.tsx containment-parity regression test locking the fix
  - Phase 4 (E2E-01) handoff for the real pixel-width browser assertion
affects: [phase-4-e2e-regression-suite]

actuals:
  tokens: 8000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Chrome containment parity: outer header/footer stay full-bleed (border only), an inner div/paragraph carries mx-auto w-full max-w-[68rem] px-4 so all three chrome sections share one content geometry"

key-files:
  created:
    - frontend/src/components/PageShell.test.tsx
  modified:
    - frontend/src/components/PageShell.tsx
    - .planning/phases/01-test-base-layer-app-skeleton/deferred-items.md
    - .planning/ROADMAP.md

key-decisions:
  - "Moved the 16px gutter (px-4) onto the contained inner wrapper on both header and footer, not just the width cap, so chrome content aligns exactly with main's content edges instead of being 16px wider per side (an extension beyond the gap's literal wording, justified in the plan's gap_coverage_audit)."

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "Header brand+nav contained at 68rem, centered, with borders staying full-bleed"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "frontend/src/components/PageShell.test.tsx#PageShell chrome containment (G-01-3) > header, main and footer content share one containment geometry"
        status: pass
      - kind: unit
        ref: "frontend/src/components/PageShell.test.tsx#PageShell chrome containment (G-01-3) > chrome borders stay full-bleed while only content is capped"
        status: pass
      - kind: other
        ref: "node containment-gate script in Task 1 <verify> — prints CONTAINMENT PARITY 3/3, BORDERS FULL-BLEED, TYPE SCALE FIXED"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real pixel-width/centering geometry at a 1720px viewport (jsdom cannot measure layout)"
    requirement: UI-01
    verification: []
    human_judgment: true
    rationale: "jsdom has no layout engine — class-token assertions prove intent but not rendered geometry. Deferred to Phase 4 (E2E-01) Playwright suite per the plan's Task 2 handoff; recorded in deferred-items.md and ROADMAP.md Phase 4 research flags."
  - id: D3
    description: "Full frontend suite and production build stay green with the fix applied"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "npm --prefix frontend run test (5 files / 9 tests)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run build (tsc -b && vite build)"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-09-01
status: complete
---

# Phase 01 Plan 06: Header Containment Gap Closure Summary

**Closed UAT gap G-01-3 by giving the header (and footer) an inner 68rem-capped, 16px-gutter wrapper so their content edges align with `<main>` at every viewport width, locked by a new class-token regression test — and handed the real pixel-geometry assertion forward to Phase 4's Playwright suite since jsdom cannot measure it.**

## Performance
- **Duration:** 13min
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Fixed the actual containment omission on `PageShell.tsx`'s header (and the identical latent defect on the footer paragraph) — root cause was already diagnosed in `.planning/debug/nav-text-not-responsive.md`, so no re-diagnosis was needed; this plan applied the layout fix, not a typography change.
- Added `PageShell.test.tsx`, which reads live `className` tokens off the rendered DOM (as a `Set`, not a substring match) so any future drift between header/main/footer containment fails a test instead of silently regressing to a screenshot nobody takes.
- Recorded a self-contained, findable handoff for Phase 4 (E2E-01) to assert the true pixel-width/centering geometry at a 1720px viewport — in both `deferred-items.md` and a scoped one-line edit to `ROADMAP.md`'s Phase 4 research flags.

## Task Commits
1. **Task 1: Give the header a contained inner wrapper and lock chrome containment parity with a test** - `06b70d8` (fix)
2. **Task 2: Hand the real pixel-width assertion forward to Phase 4 (E2E-01)** - `00f91ee` (docs)

**Plan metadata:** commit pending (see below)

## Before/After className strings

**Header (outer element):**
- Before: `flex flex-wrap items-center gap-[18px] border-b border-line px-4 py-4`
- After: `border-b border-line py-4`

**Header inner wrapper (new element, header's only child):**
- Added: `mx-auto flex w-full max-w-[68rem] flex-wrap items-center gap-[18px] px-4`
- Contains (moved in unchanged): the brand span, the `nav` element, and the empty meta-banner `div`.

**Main (unchanged — the reference geometry the header/footer now match):**
- `mx-auto w-full max-w-[68rem] flex-1 px-4`

**Footer (outer element):**
- Before: `border-t border-line px-4 py-4 text-label text-ink-2`
- After: `border-t border-line py-4 text-label text-ink-2`

**Footer paragraph:**
- Before: `mx-auto max-w-[68rem]`
- After: `mx-auto w-full max-w-[68rem] px-4`

## RED confirmation (test written before the fix)

Ran `npm --prefix frontend run test -- --reporter=verbose src/components/PageShell.test.tsx` against the unmodified `PageShell.tsx` and observed both new tests fail, exactly as the plan's RED expectation predicted:

```
× PageShell chrome containment (G-01-3) > header, main and footer content share one containment geometry
  AssertionError: expected false to be true  (header's first child — the brand span — carried
  none of the CONTAINMENT tokens)

× PageShell chrome containment (G-01-3) > chrome borders stay full-bleed while only content is capped
  AssertionError: expected true to be false  (the outer header still carried a px- horizontal
  padding token)
```

After the fix, both tests pass (GREEN) with no further edits to the test file.

## Final test counts

- Baseline before this plan: 4 files / 7 tests, green.
- After this plan: **5 files / 9 tests**, green (`npm --prefix frontend run test`).
- `PageShell.test.tsx` specifically: 2/2 passing (grep count confirmed via `--reporter=verbose | grep -Eic 'pageshell'` → `3`, i.e. the file name plus the 2 describe/test lines).

## Files Created/Modified
- `frontend/src/components/PageShell.test.tsx` - new containment-parity regression test (2 tests)
- `frontend/src/components/PageShell.tsx` - header/footer containment fix (see before/after above)
- `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md` - new handoff section for Phase 4's browser-level pixel-width assertion
- `.planning/ROADMAP.md` - Phase 4's `**Research flags**:` line extended with the same G-01-3/1720px handoff instruction (scoped single-line edit; no other phase entry touched, confirmed by `git diff`)

## Decisions Made
- Moved the horizontal gutter (`px-4`) onto the contained inner wrapper on both header and footer, not only the width cap. Reading the gap's `missing:` item literally (keep padding on the outer header) would have left header content 16px wider per side than `<main>`'s content — replacing the stranded-nav bug with a new, more subtle misalignment. Vanilla's `.wrap` owns both the cap and the gutter and nests `header.site`/`footer.site` inside it, so this decision restores true vanilla parity rather than a literal-but-broken reading of the gap text. Documented in the plan's `gap_coverage_audit` as a deliberate, in-scope extension — not scope creep, since it is the same single concern (chrome containment geometry) in the same single file.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` steps were followed verbatim, all automated `<verify>` gates passed on the first attempt with no fix-and-retry cycles, and the negative gates (exact containment-cap count = 3, exact gutter count = 3, no breakpoint-scaled font utilities, exactly 2 `G-01-3` references in ROADMAP.md) all passed without adjustment.

## Issues Encountered

None.

## Verification Results (plan-level `<verification>` section)

1. `npm --prefix frontend run test` — exits 0, **5 test files / 9 tests** passing (baseline 4/7 + 2 new). PASS.
2. `npm --prefix frontend run build` — `tsc -b && vite build` exits 0, `dist/` produced. PASS. (Correctly used `run build`, not the documented-no-op `run typecheck`.)
3. Task 1's containment gate script prints `CONTAINMENT PARITY 3/3, BORDERS FULL-BLEED, TYPE SCALE FIXED`. PASS.
4. Task 2's two handoff gates print `PHASE 1 HANDOFF ENTRY RECORDED` and `PHASE 4 HANDOFF RECORDED AND SCOPED`. PASS.
5. No dependency drift: `git status --porcelain frontend/package.json frontend/package-lock.json` empty → `NO DEPENDENCY CHANGE`. PASS.
6. No regression in previously-passing UAT-relevant tests: `frontend/src/routes/routeIsolation.test.tsx` and `frontend/src/test/harness.test.tsx` both still pass, and neither file appears in this plan's two commits (`git log --oneline --all -- <path>` shows only their 01-04/01-05 origin commits) — confirming they required no modification. PASS.

**Human-check note (embedded per `human_verify_mode: end-of-phase`, not run as a blocking checkpoint):** the plan's Task 1 `<verify>` also specifies a manual visual check — run `npm --prefix frontend run dev`, confirm at a wide (~1720px) viewport the brand+nav sit in a centered column aligned with the page heading/footer disclaimer below, and confirm at ~375px the nav still wraps with unchanged padding. This is deferred to end-of-phase UAT consolidation per the project's `human_verify_mode: end-of-phase` config rather than treated as a mid-plan blocking checkpoint. All automated proxies for this (the class-token tests, the containment-count gate) already pass.

## Known Stubs

None. This is a pure presentational fix on existing static chrome — no new data-empty states or placeholder content introduced.

## Threat Flags

None. Consistent with the plan's `<threat_model>`: all three STRIDE entries were disposed `accept` (literal Tailwind class strings, no injection surface, empty meta-slot re-parented but rendering no data) except `T-01-06-03` (ROADMAP.md scoped-edit risk), which was `mitigate`d exactly as specified — the edit was scoped to one line, verified by `git diff` and the Task 2 verify gate's leak check against Phase 5's body.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

Gap G-01-3 is fully closed for Phase 1's scope (class-level fix + regression test). Phase 4 (E2E Regression Suite) now carries a findable, self-contained instruction — in both `deferred-items.md` and `ROADMAP.md`'s Phase 4 research flags — to add the real 1720px-viewport pixel-geometry assertion once Playwright is stood up. No blockers for Phase 1 completion.

## Self-Check: PASSED

- `[ -f frontend/src/components/PageShell.test.tsx ]` → FOUND
- `[ -f frontend/src/components/PageShell.tsx ]` → FOUND (modified)
- `git log --oneline --all --grep="01-06"` → 2 commits found (`06b70d8`, `00f91ee`)
- All plan-level `<acceptance_criteria>`/`<verify>` commands re-run above — all PASS
- Plan-level `<verification>` items 1-6 re-run above — all PASS

---
*Phase: 01-test-base-layer-app-skeleton*
*Completed: 2026-09-01*
