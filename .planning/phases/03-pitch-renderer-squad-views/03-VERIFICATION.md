---
phase: 03-pitch-renderer-squad-views
verified: 2026-09-03T11:30:00Z
status: human_needed
score: 12/12 must-haves verified (automated)
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 12/12 must-haves verified (automated)
  gaps_closed:
    - "G-03-1: even-cardinality formation rows (2-card Forwards, 4-card DEF/MID, 4-card Bench) drifted left of the pitch midline — closed by 03-05's continuous flexbox centering (display:flex; justify-content:center; fixed flex-basis via calc() and a --pitch-gap custom property), replacing the defective integer grid-column scheme. 12/12 Pitch.test.tsx assertions (including a new symmetry-oracle suite spanning row sizes 1-6, both UAT viewports) pass; full 363/363 frontend suite, typecheck, and build-purity gate all green; anti-regression grep confirms zero gridColumn/gridTemplateColumns/centeredStartColumn/Math.floor remain in Pitch.tsx; 03-UI-SPEC.md's Layout subsection rewritten to document the shipped mechanism and cite the debug session so the defect is not re-derived."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Open /team at desktop width and at 375px, in both light and dark mode. On the default model squad (3-5-2), confirm the 2-card Forwards row and the 4-card bench sit centered on the pitch midline — aligned with the SVG center circle and the single GK card — and that the 3-card Defenders and 5-card Midfielders rows have not moved. Load a real entry with a 4-4-2 formation and confirm the 4-card Defenders and Midfielders rows are centered too. Confirm names still ellipsize, price/xP stay visible, and no row overflows horizontally."
    expected: "Every formation row (1, 2, 3, 4, or 5 cards) and the 4-card bench read as horizontally centered on the pitch, matching the FPL-style pitch's visual midline, in both light and dark mode and at both viewport widths — this is UAT test 1 / gap G-03-1, now re-checked against the 03-05 fix."
    why_human: "jsdom performs no real layout — 03-05's Pitch.test.tsx suite (12/12 passing) asserts the declared layout model (inline flex/justify-content/flex-basis/flex-grow/min-width and a computed symmetry oracle), not measured pixels in an actual browser. The plan's own Task 1 <human-check> requires this browser confirmation, and 03-05-SUMMARY.md explicitly deferred it to this end-of-phase UAT pass per the project's human_verify_mode=end-of-phase setting — it has not yet been re-checked by a human since the fix shipped."
---

# Phase 3: Pitch Renderer & Squad Views Verification Report

**Phase Goal:** Users see and manipulate their squad on an FPL-style pitch, including the solver and rate-my-team flows
**Verified:** 2026-09-03T11:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap-closure plan 03-05 closed UAT gap G-03-1

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | A documented decision records shirt/kit sourcing and a non-affiliation disclaimer is visible sitewide | ✓ VERIFIED | Unchanged since prior verification and independently human-confirmed in UAT test 3 ("pass" — trademark posture sign-off). `docs/decisions/pitch-kit-sourcing.md` still present; `PageShell.tsx:80` footer sentence "not licensed team imagery" confirmed live by direct read; zero hex/remote-host references in `Kit.tsx`/`kitMap.ts`/`Pitch.tsx`/`PlayerCard.tsx` (regression grep re-run). |
| 2 | A squad renders on a pitch in formation-driven rows + bench, cards show shirt/name/price/xP with p10/p90, C/VC badges, and pitch+tables stay usable at phone width | ⚠️ Structurally VERIFIED, visual re-check pending | `Pitch.test.tsx` 12/12 green including the new `Pitch — row centering (G-03-1)` suite (symmetry oracle over row sizes 1-6 at both UAT viewports, 600px/8px-gap and 311px/4px-gap); full 363/363 frontend suite green; anti-regression grep confirms integer column placement fully removed. This is the exact truth UAT test 1 rejected (even-count rows off-center) — the fix is now structurally proven, but the deferred browser re-check (human_verify_mode=end-of-phase) has not yet run. Routed to human verification below. |
| 3 | From the team page a user loads a squad (default entry 6980093), locks/excludes players, requests a solve, sees transfers/XI update on the pitch | ✓ VERIFIED | Unaffected by 03-05 (no `SquadTab.tsx`/`useSolveController` changes). `SquadTab.test.tsx` unchanged and green in the full-suite re-run; UAT test 2 (post-solve IN badges, rate diff, solve results bar wrapping) passed with human sign-off. |
| 4 | Rate-my-team shows a visual diff of the user's squad against the optimal one with suggested swaps | ✓ VERIFIED | `RateDiff.tsx` consumes the same shared `<Pitch>`/`PitchRow` that 03-05 fixed — no separate renderer, so the centering fix reaches this view too. `RateDiff.test.tsx` (15/15) re-run standalone and green; UAT test 2 passed with human sign-off on the diff styling itself. |
| 5 | Chip timing shows a "why this GW" explanation with DGW/BGW callouts | ✓ VERIFIED | Unaffected by 03-05. `ChipTimeline.tsx`/`ChipsTab.tsx` tests unchanged and green in the full-suite re-run; not touched by any file in this gap-closure plan. |

**Score:** 12/12 automated must-haves (5 ROADMAP SCs + 7 plan-level truths, see below) structurally verified by code + tests. One SC (#2) carries a still-open, explicitly-deferred visual re-check — not a code gap, a rendering confirmation gap.

### Deferred Follow-Ups (not gaps, informational)

Recorded in `03-UAT.md`'s "Deferred Follow-Ups" section from test 2: a UX idea to replace the dashed ghost card with an in-place player swap + label, deferred by the user during UAT sign-off. Not a phase must-have; not actionable here.

### Plan-Level Must-Haves — 03-05 Gap-Closure Plan (full verification, all failed-in-prior-round items)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 6 | Every formation row renders horizontally centered on the pitch midline, including 2-card FWD, 4-card DEF/MID, and 4-card bench (G-03-1) | ✓ VERIFIED (structural) | `Pitch.test.tsx` symmetry-oracle assertions per row size 1-6, computing leading/trailing free space equality and `rowWidth <= W`; all pass. Visual confirmation pending (see human verification). |
| 7 | Odd-cardinality rows (1, 3, 5 cards) stay exactly centered — no over-correction | ✓ VERIFIED | Same symmetry-oracle suite explicitly names Goalkeeper(1)/Defenders(3)/Midfielders(5) as "odd controls" and asserts them unmoved; all pass. |
| 8 | Card measure still derives from a fixed 5-part ceiling; cards shrink, row never reflows (D-07) | ✓ VERIFIED | `cardMeasure`/`rowParts` (`Pitch.tsx:40-46`) implement `Math.max(5, count)`; test asserts `d === Math.max(5, count)` and `k === d - 1` for every row. |
| 9 | Ghost card still renders after its anchor and grows its row to a 6-part measure | ✓ VERIFIED | `Pitch.test.tsx` "grows the ghost-holding Midfielders row to a 6-part measure and keeps it exactly centered" passes; ghost DOM-order test (pre-existing) unaffected. |
| 10 | Long player name still ellipsizes; no row overflows its container | ✓ VERIFIED (structural) | Every cell asserted `flexGrow: "0"`, `minWidth: "0px"` (the flex equivalent of the removed zero track-minimum); `PlayerCard.tsx`'s `truncate` class on the name span is unchanged. Pixel-level overflow confirmation is part of the same deferred visual re-check as truth #2. |
| 11 | `--pitch-gap` responsive custom property exists, readable inside `calc()` | ✓ VERIFIED | `index.css:98` (`--pitch-gap: var(--spacing-xs)`) and `index.css:101-104` (`@media (min-width: 480px)` override to `var(--spacing-sm)`) confirmed by direct read; structural check `node -e ...` (plan's own gate) re-run and passes. |
| 12 | 03-UI-SPEC.md documents the shipped mechanism, not a mechanism that was rejected | ✓ VERIFIED | `03-UI-SPEC.md:97-124` rewritten Layout subsection: names `flex-basis`, `--pitch-gap`, `max(5, cardsInRow)`, cites `pitch-row-centering-drift.md`, records both rejected mechanisms by concept. Grep gates from the plan's own verify block re-run and pass. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `frontend/src/components/pitch/Pitch.tsx` | Continuous flex centering, `rowParts`/`cardMeasure` helpers, no integer grid placement | ✓ VERIFIED | Read in full; matches plan's `<action>` exactly. `centeredStartColumn` and all `gridColumn`/`gridTemplateColumns` usage removed. |
| `frontend/src/index.css` | `--pitch-gap` custom property, base + 480px override | ✓ VERIFIED | Present at L93-105, derived from `--spacing-xs`/`--spacing-sm` theme tokens as specified. |
| `frontend/src/components/pitch/Pitch.test.tsx` | Symmetry regression across row sizes 1-6 | ✓ VERIFIED | `Pitch — row centering (G-03-1)` describe block, 6 new test cases (5 row sizes + ghost-grown row), all passing. |
| `.planning/phases/03-pitch-renderer-squad-views/03-UI-SPEC.md` | Corrected row-centering mechanism | ✓ VERIFIED | Layout subsection retitled and rewritten; matches shipped code. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `--pitch-gap` custom property (`index.css`) | `cardMeasure()` `calc()` string (`Pitch.tsx`) | Direct `var(--pitch-gap)` reference inside the returned `calc()` expression | ✓ WIRED | Confirmed by reading both files; the plan's structural grep gate re-run and passes. |
| `PitchRow` (single shared component) | `SquadTab.tsx`, `RateDiff.tsx`, `PlanTransfers.tsx` (all 3 wave-3 consumers) | Import of the one `Pitch`/`PitchRow` component — no duplicate renderer | ✓ WIRED | `grep -rln "Pitch" frontend/src/components` confirms exactly these 3 non-test consumers outside `pitch/`; one shared fix reaches all three, confirmed by each consumer's test suite passing in the full re-run. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `Pitch.test.tsx` targeted re-run | `npx vitest run src/components/pitch/Pitch.test.tsx` | 12/12 passed | ✓ PASS |
| Full frontend suite re-run | `npx vitest run` (frontend/) | 38 files, 363 tests, all passed | ✓ PASS |
| TypeScript strict build-mode check | `npm run typecheck` | exits 0, no errors | ✓ PASS |
| Build purity | `bash scripts/verify_frontend_build.sh` | "BUILD PURITY OK" | ✓ PASS |
| Anti-regression grep (integer column placement) | plan's own two-grep pipeline: strip comments, then search for `gridColumn`, `gridTemplateColumns`, `centeredStartColumn`, or `Math.floor` | no match | ✓ PASS ("INTEGER COLUMN PLACEMENT GONE") |
| `--pitch-gap` structural check (base + 480px override) | plan's own `node -e` gate | both declarations found | ✓ PASS |
| Shared-consumer regression: `RateDiff.test.tsx` | `npx vitest run src/components/RateDiff.test.tsx` | 15/15 passed | ✓ PASS |
| Ghost-row targeted re-run | `npx vitest run -t "ghost" src/components/pitch/Pitch.test.tsx` | 3 passed / 9 skipped (targeted filter) | ✓ PASS |
| Commit existence | `git cat-file -e 25a7244`, `4e83899`, `250f589` | all present in history | ✓ PASS |
| No debt markers in modified files | grep TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER across `index.css`, `Pitch.tsx`, `Pitch.test.tsx`, `03-UI-SPEC.md` | none found | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| PITCH-01 | 03-01 | Kit/shirt sourcing decision + non-affiliation disclaimer | ✓ SATISFIED | Human-confirmed pass in UAT test 3; unaffected by 03-05. |
| PITCH-02 | 03-01, 03-05 | Pitch renderer — formation rows, bench, card fields, centering | ✓ SATISFIED (structural); visual re-check pending | 03-05 closed the centering defect with automated proof; browser confirmation deferred to human verification below. |
| PITCH-03 | 03-02, 03-04 | Team page — load, lock/exclude, solve, XI update | ✓ SATISFIED | Human-confirmed pass in UAT test 2; unaffected by 03-05; full suite green. |
| PITCH-04 | 03-03 | Rate-my-team visual diff with suggested swaps | ✓ SATISFIED | Human-confirmed pass in UAT test 2; shares the fixed `Pitch` component; `RateDiff.test.tsx` re-run green. |
| UI-07 | 03-01, 03-05 | Mobile-responsive pitch and tables | ✓ SATISFIED (structural); visual re-check pending | Same G-03-1 fix; symmetry oracle covers both UAT viewports (600px/8px, 311px/4px); browser confirmation deferred. |
| UIX-01 | 03-01 | p10/p90 intervals on cards | ✓ SATISFIED | Unaffected by 03-05; `PlayerCard.test.tsx` unchanged and green. |
| UIX-03 | 03-02 | Chip-timing "why this GW" UI | ✓ SATISFIED | Unaffected by 03-05; `ChipTimeline.tsx`/`ChipsTab.tsx` tests unchanged and green. |

**No orphaned requirements.** All 7 requirement IDs REQUIREMENTS.md maps to Phase 3 (`grep` re-run: PITCH-01/02/03/04, UI-07, UIX-01, UIX-03, all marked `[x]` "Complete") exactly match the union of `requirements:` fields declared across all 5 plans (03-01 through 03-05). 03-05 additionally declares `PITCH-02, UI-07` in its own frontmatter for the gap-closure work — consistent with, not additive to, the phase's requirement set.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `frontend/src/components/pitch/kitMap.ts` | 18-39 | `"hoops"` kit pattern implemented/tested but unused by any of the 20 mapped clubs | ℹ️ Info | Pre-existing, carried forward from prior verification; intentional forward-provisioning, not touched by 03-05. |
| `.planning/phases/03-pitch-renderer-squad-views/03-UAT.md` | 47-66 | Gap `G-03-1` entry still reads `status: failed` and does not reference the closing plan `03-05` | ℹ️ Info | Documentation lag, not a functional gap — 03-05-SUMMARY.md's "Next Phase Readiness" section explicitly flagged this as an outstanding update. Does not affect the verified fix; noted for bookkeeping. |

No 🛑 Blocker and no unreferenced debt markers found in any file touched by 03-05 or in the phase's prior deliverables re-checked in this pass.

### Human Verification Required

See frontmatter `human_verification` — 1 item: the deferred browser re-check of UAT test 1 / gap G-03-1 (pitch row centering at desktop and 375px, light and dark mode, 3-5-2 model squad and a loaded 4-4-2 entry). This is the phase's own Task 1 `<human-check>` from 03-05-PLAN.md, explicitly deferred to this end-of-phase UAT pass per `human_verify_mode: end-of-phase` (`.planning/config.json:32`) — it is not a new finding, it is the closing half of the fix that automated tooling (jsdom has no layout engine) structurally cannot complete. Every other item this phase's own workflow previously deferred to human judgment (kit-sourcing legal posture, rate-tab/solve visual styling) has already been human-confirmed as `pass` in `03-UAT.md` tests 2 and 3, and is not re-listed here.

### Gaps Summary

No code gaps. UAT gap G-03-1 is closed at the code level: the defective integer CSS-grid centering scheme is fully removed from `Pitch.tsx`, replaced by continuous flexbox centering with a fixed `calc()`-derived measure; a new symmetry-regression suite (12/12 passing, including both previously-drifting even rows and the three odd controls that must not move) closes the coverage hole that let the original defect ship undetected; the full 363-test frontend suite, typecheck, and build-purity gate are all green; and `03-UI-SPEC.md` now documents the mechanism that actually shipped, with both rejected mechanisms recorded so neither is re-derived. The one remaining item — visually confirming the fix renders correctly in an actual browser at both UAT viewports and both color schemes — is exactly what `human_verify_mode: end-of-phase` defers to this verification pass, and is surfaced above rather than assumed passing or wrongly marked failed.

---

_Verified: 2026-09-03T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
