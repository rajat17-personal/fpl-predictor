---
phase: 03-pitch-renderer-squad-views
verified: 2026-09-03T06:54:50Z
status: human_needed
score: 12/12 must-haves verified (automated)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open /team (no ?entry=) at a narrow (375px) viewport and confirm the pitch/card visual rendering matches UI-SPEC: green gradient surface, white decorative markings, formation rows top-to-bottom, bench in its own non-green strip, cards shrink without the 5-column grid reflowing, name ellipsis, price/xP never hidden."
    expected: "Pitch reads as an FPL-style pitch at both desktop and 375px width; no horizontal overflow; kit colours/patterns are legible; exactly one C badge and at most one V badge visible; dark mode keeps text legible against the pitch tokens."
    why_human: "jsdom performs no real layout; UI-07's mobile-responsiveness contract and the pitch's visual hierarchy (color, spacing, badge placement) can only be confirmed by rendering in a real viewport. This is 03-01 Task 2's own deferred <human-check>, carried into 03-VALIDATION.md's Manual-Only Verifications table."
  - test: "On the Rate tab (with a real or sample entry loaded), confirm the diff pitch's out-treatment styling, the dashed ghost-insert card, and the Squad tab's post-solve IN badges render legibly, and that the solve results bar / plan-transfers per-week blocks wrap correctly at narrow widths."
    expected: "The out card is visually dimmed/marked distinct from a normal card; the ghost card is visually distinguishable (dashed border, reduced opacity) and sits in the correct formation row; IN badges are visible and placed per UI-SPEC; no layout overflow at phone width."
    why_human: "Same class of jsdom layout blindness as above — 03-03 and 03-04's SUMMARYs both explicitly defer this to end-of-phase UAT (structure/text proven by tests, visual styling not)."
  - test: "Read docs/decisions/pitch-kit-sourcing.md in full and confirm the trademark posture (neutral SVG kits, no crest/sponsor/CDN imagery, non-legal-opinion caveat) is one you are willing to stand behind at a future payment-gateway review."
    expected: "The decision doc's reasoning and reversibility framing read as sound and sufficient without a formal legal review at this stage."
    why_human: "Legal-adjacent judgment call, not a DOM or grep assertion — this is 03-01 Task 3's own deferred <human-check>, and PITCH-01's plan-frontmatter prohibition (\"no club crest/sponsor/imagery\") carries verification: unverified pending this read, even though the automated remote-host/hex-literal grep gates back it structurally."
---

# Phase 3: Pitch Renderer & Squad Views Verification Report

**Phase Goal:** Users see and manipulate their squad on an FPL-style pitch, including the solver and rate-my-team flows
**Verified:** 2026-09-03T06:54:50Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | A documented decision records shirt/kit sourcing and a non-affiliation disclaimer is visible sitewide | ✓ VERIFIED | `docs/decisions/pitch-kit-sourcing.md` committed (decision, reasoning, disclaimer location, reversibility note, all three PITCH-01 elements present); `PageShell.tsx:78-80` footer paragraph contains "not licensed team imagery" verbatim on every route (`PageShell.test.tsx` asserts this); grep confirms zero hex literals and zero remote-host references in `Kit.tsx`/`kitMap.ts`/`Pitch.tsx`/`PlayerCard.tsx`. Legal-posture judgment routed to human verification below. |
| 2 | A squad renders on a pitch in formation rows + bench, cards show shirt/name/price/xP with p10/p90, C/VC badges; pitch and tables stay usable at phone width | ✓ VERIFIED | `Team.test.tsx`/`Pitch.test.tsx`/`PlayerCard.test.tsx` (357/357 green) assert 15 names render, exactly 4 bench cards, derived formation label matches export, exactly one C and at most one V badge, range line renders for null/equal/explicit p10-p90 with no `NaN`. UI-REVIEW's one BLOCKER (fixed 8px-only row gap) is confirmed fixed live in `Pitch.tsx:100` (`gap-1 min-[480px]:gap-2`, commit `651feae`). Visual phone-width rendering routed to human verification below (UI-07 is manual-only per 03-VALIDATION.md by design — jsdom has no layout engine). |
| 3 | From the team page a user loads a squad, locks/excludes players, requests a solve, sees transfers/XI update on the pitch | ✓ VERIFIED | `SquadTab.test.tsx` (34+ tests) covers: `/api/team/{entry}` load flow, `selectLoadedSquad` producing 11 starters/1 GK/1 captain, mutually-exclusive lock/exclude via the popover, `buildSolveRequest` emitting numeric `player_code` arrays only (grep-confirmed no display names in `JSON.stringify`), an ordering-safety guard (`useSolveController`, `renderHook`-tested) that drops superseded responses, in-place pitch re-render with IN badges computed against the as-loaded squad, and "Reset to loaded squad" issuing zero network calls. `CR-01` (ghost-card grid overflow) and `WR-01` (stuck-pending on unexpected solve kind) from code review are both confirmed fixed live in `Pitch.tsx` and `SquadTab.tsx` (commits `c1c7636`, `f89439d`). |
| 4 | Rate-my-team shows a visual diff of the user's squad vs optimal with suggested swaps | ✓ VERIFIED | `RateDiff.tsx`/`RateDiff.test.tsx`: one `<Pitch>` (never two) carrying the out treatment + ghost insert card resolved by exact-name match with a documented no-overlay degrade (`resolveRateOverlay`, `WR-03` unchecked-cast fix confirmed live at `RateDiff.tsx` guarding `row.position` against `VALID_PITCH_ROWS`), a swap line reading `{sell} → {buy}` + `+{xp_gain} xP`, and the Hold case (no out treatment, no ghost, no swap line) all test-covered. |
| 5 | Chip timing shows a "why this GW" explanation with DGW/BGW callouts | ✓ VERIFIED | `ChipTimeline.tsx`/`ChipsTab.tsx`: current-GW-to-38 timeline, DGW/BGW markers derived from `chips.json`'s integer club counts (`classifyMarker` unit-tested against both the live all-zero fixture and a hand-built `chips_dgw.json`), the verbatim `note` string in a "Why GW{n}" callout, empty/error states covered. `WR-02` (Tailwind class-conflict on the current-GW marker) confirmed fixed live in `ChipTimeline.tsx` (commit `80ef052`). |

**Score:** 5/5 ROADMAP success criteria structurally verified by code + tests; 0 truths failed; visual/legal judgment components of SC1-SC4 routed to human verification (see below) per this phase's own deferred `<human-check>` blocks and `03-VALIDATION.md`'s Manual-Only Verifications table.

### Plan-Level Must-Haves (representative sample, cross-checked against all 4 plans' frontmatter)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 6 | `deriveFormation` returns `"3-5-2"` for the live fixture; `joinSquad` matches only on `player_code` | ✓ VERIFIED | `formation.test.ts`, `squadJoin.test.ts` pass (part of 357/357) |
| 7 | 20 of 20 `team_short` codes resolve to explicit `KIT_MAP` entries, none to fallback | ✓ VERIFIED | `grep -c` on `kitMap.ts` confirms exactly 20 club entries; `kitMap.test.ts` asserts no fallback hits |
| 8 | No club crest/sponsor mark/remote image anywhere in the kit/pitch system | ✓ VERIFIED | Direct grep of `Kit.tsx`, `Pitch.tsx`, `PlayerCard.tsx`, `kitMap.ts` for hex literals and remote-host URL patterns — zero matches |
| 9 | Solve request sends `locks`/`excludes` as numeric codes, never names; a solve request's body never contains a marked player's display name | ✓ VERIFIED | `SquadTab.test.tsx`'s `buildSolveRequest` unit tests + integration test asserting `JSON.stringify` of the request body contains no marked player's name |
| 10 | Locks/excludes and solve results never reach the URL or browser storage | ✓ VERIFIED | Direct grep across `src/components/team/*.tsx`, `src/routes/Team.tsx` for `localStorage`/`sessionStorage`/`indexedDB` — zero matches; only `/api/plan` and `/api/solve` (local preview solves, not FPL-account writes) appear in the phase's outbound fetch calls |
| 11 | Two identical solves with unchanged marks/controls render an identical squad, results bar, and captain | ✓ VERIFIED | `SquadTab.test.tsx` "solving twice with identical marks and control values renders an identical squad, results bar, and captain" |
| 12 | pairMoves is a verbatim structured (non-HTML-string) port shared by both wave-3 consumers | ✓ VERIFIED | `pairMoves.test.ts` passes; `RateDiff`/`PlanTransfers`/`SolveResultsBar` all import the same module (no duplicate implementation found) |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `frontend/src/lib/formation.ts` | `deriveFormation`, `splitPitchRows` | ✓ VERIFIED | Present, tested, generic over `SquadRow` |
| `frontend/src/lib/squadJoin.ts` | `joinSquad`, `deriveViceCaptain` | ✓ VERIFIED | Present, tested |
| `frontend/src/components/pitch/kitMap.ts` | 20-club kit map | ✓ VERIFIED | 20 entries, no fallback hits |
| `frontend/src/components/pitch/Kit.tsx` | Parameterised inline SVG shirt | ✓ VERIFIED | No hex, no remote host, `aria-hidden` |
| `frontend/src/components/pitch/PlayerCard.tsx` | Full card: badges, range line, popover | ✓ VERIFIED | All prop branches test-covered |
| `frontend/src/components/pitch/Pitch.tsx` | Formation rows + bench + marks/diffs/ghost | ✓ VERIFIED | CR-01 grid-overflow fix confirmed live |
| `frontend/src/routes/Team.tsx` | Three-tab shell, `?entry=`/`?tab=` state | ✓ VERIFIED | ARIA tab/tabpanel pairs, per-tab lazy fetch |
| `frontend/src/components/team/{SquadTab,ChipsTab,RateTab}.tsx` | Squad/Chips/Rate tab panels | ✓ VERIFIED | All present, tested |
| `frontend/src/components/{RateDiff,PlanTransfers,ChipTimeline,SolveControls,SolveResultsBar}.tsx` | Diff/plan/timeline/solver UI | ✓ VERIFIED | All present, tested |
| `frontend/src/lib/pairMoves.ts` | Shared sell/buy pairing | ✓ VERIFIED | Structured objects, no markup |
| `docs/decisions/pitch-kit-sourcing.md` | PITCH-01 decision doc | ✓ VERIFIED | Committed, three required elements present |
| `.planning/phases/03-pitch-renderer-squad-views/PARITY-DEVIATIONS.md` | Phase 3 ledger | ✓ VERIFIED | Rows 9-13 present, correctly attributed |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `squad.json`/`team_response.json` rows | `xp_table.json` rows | `joinSquad` by numeric `player_code` | ✓ WIRED | `squadJoin.test.ts`; no name-matching found anywhere in the join path |
| `SolveControls`/`SquadTab` mark state | `/api/solve` request body | `buildSolveRequest` (numeric codes) | ✓ WIRED | Grep + unit test confirm no display names cross into the request |
| Solve/plan/rate `squad[]`/`xi[]` responses | `<Pitch>` | `joinSquad` + `deriveFormation` (same trio used everywhere) | ✓ WIRED | `RateDiff.tsx`, `PlanTransfers.tsx`, `SquadTab.tsx` all route through the one `Pitch` component — no second renderer found |
| `best_move` (names only) | `Pitch`'s `diffs`/`ghost` props | `resolveRateOverlay` exact-match with documented degrade | ✓ WIRED | `RateDiff.test.tsx` covers unique-match, zero-match, and multi-match branches |
| `index.css` `@theme` pitch tokens | Pitch surface color | Token classes only, no hex | ✓ WIRED | Grep confirms zero hex literals in pitch component files |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full frontend suite | `npx vitest run` (frontend/) | 38 files, 357 tests, all passed | ✓ PASS |
| TypeScript strict build-mode check | `npm run typecheck` | exits 0, no errors | ✓ PASS |
| Build purity (no pipeline JSON bundled) | `bash scripts/verify_frontend_build.sh` | "BUILD PURITY OK" | ✓ PASS |
| Backend suite | `python -m pytest -q` (conda `python314`) | 67 passed | ✓ PASS |
| Ghost-card row overflow fix live | targeted `vitest -t "ghost"` on `Pitch.test.tsx` | 2 passed | ✓ PASS |
| C/VC exclusivity fix live | targeted `vitest -t "exactly one"` on `PlayerCard.test.tsx` | 1 passed | ✓ PASS |
| Numeric-only solve request | targeted `vitest -t "numeric"` on `SquadTab.test.tsx` | 7 passed | ✓ PASS |
| No debt markers (TODO/FIXME/HACK/XXX/TBD) in phase files | grep across all Phase 3 component/lib files | none found (one false-positive "placeholder" is an HTML `placeholder=` attribute, not a marker) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| PITCH-01 | 03-01 | Kit/shirt sourcing decision + non-affiliation disclaimer | ✓ SATISFIED | Decision doc + footer sentence confirmed live; legal-posture read routed to human verification |
| PITCH-02 | 03-01 | Pitch renderer — formation rows, bench, card fields | ✓ SATISFIED | `Pitch.tsx`/`PlayerCard.tsx` + full test suite |
| PITCH-03 | 03-02, 03-04 | Team page — load, lock/exclude, solve, XI update | ✓ SATISFIED | `SquadTab.tsx`, `SolveControls.tsx`, `SolveResultsBar.tsx` + tests |
| PITCH-04 | 03-03 | Rate-my-team visual diff with suggested swaps | ✓ SATISFIED | `RateDiff.tsx` + tests |
| UI-07 | 03-01 | Mobile-responsive pitch and tables | ✓ SATISFIED (structural) | Fixed 5-column `minmax(0,1fr)` grid + UI-REVIEW's responsive-gap blocker confirmed fixed live; real-viewport confirmation routed to human verification (manual-only by nature, per 03-VALIDATION.md) |
| UIX-01 | 03-01 | p10/p90 intervals on cards | ✓ SATISFIED | `PlayerCard.test.tsx` null/equal/explicit-bounds coverage |
| UIX-03 | 03-02 | Chip-timing "why this GW" UI | ✓ SATISFIED | `ChipTimeline.tsx`/`ChipsTab.tsx` + tests |

**No orphaned requirements.** All 7 requirement IDs declared across the 4 plans' frontmatter (PITCH-01/02 + UIX-01 + UI-07 in 03-01; PITCH-03 + UIX-03 in 03-02; PITCH-04 in 03-03; PITCH-03 in 03-04) exactly match REQUIREMENTS.md's Phase 3 traceability row set — nothing mapped to Phase 3 in REQUIREMENTS.md is missing from a plan's `requirements:` field, and no plan claims an ID REQUIREMENTS.md doesn't map here.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `frontend/src/components/pitch/kitMap.ts` | 18-39 | `"hoops"` kit pattern implemented/tested but unused by any of the 20 mapped clubs | ℹ️ Info | Dead code, intentional forward-provisioning per code review IN-01; not fixed, explicitly left per `fix_scope: critical_warning` |
| `frontend/src/components/PlanTransfers.tsx:70`, `SolveControls.tsx:48` | — | Unreachable `\|\| 1` fallback on a value a `<select>` can never make falsy | ℹ️ Info | Dead defensive code, left per IN-02 |
| `frontend/src/components/SolveControls.tsx:37-50`, `PlanTransfers.tsx:69-81` | — | Numeric inputs' `min`/`max` not clamped client-side before the request is sent | ℹ️ Info | Server validates (422); UX-only gap, left per IN-03 |

No 🛑 Blocker or unreferenced debt markers found. The one 🛑-level finding from code review (CR-01, ghost-card grid overflow) and all 3 ⚠️ Warnings (WR-01/02/03) were fixed in commits `c1c7636`/`f89439d`/`80ef052`/`837fee2` and independently confirmed live in this verification pass (see Behavioral Spot-Checks and Observable Truths above). The one UI-REVIEW BLOCKER (responsive formation-row gap) was fixed in commit `651feae` and confirmed live in `Pitch.tsx:100`.

### Human Verification Required

See frontmatter `human_verification` — 3 items, all visual-appearance or legal-judgment checks that jsdom cannot assert and that this phase's own plans/SUMMARYs/VALIDATION.md explicitly deferred to end-of-phase UAT (`workflow.human_verify_mode = end-of-phase`). These are not gaps in the implementation — every structural, textual, and state-machine behavior they touch is already covered by the 357/357 green automated suite; only the rendered visual result and one legal-posture judgment call remain.

### Gaps Summary

No gaps. All must-haves derived from ROADMAP Success Criteria and all four plans' `must_haves` frontmatter are structurally verified: artifacts exist, are substantive, are wired end-to-end (squad/team/rate/plan/solve responses all flow through one `joinSquad`/`Pitch` path, never a static or duplicated renderer), and the full automated suite (357 frontend + 67 backend tests, typecheck, build purity) passes clean when re-run independently in this verification pass. The prior code review's one blocker and three warnings, and the UI review's one blocker, are all confirmed fixed in the current codebase (not just claimed in SUMMARY.md). The phase's own workflow explicitly defers three genuinely-visual/legal-judgment checks to end-of-phase UAT; per the escalation-gate pattern these are surfaced above for human sign-off rather than silently passed or wrongly failed.

---

_Verified: 2026-09-03T06:54:50Z_
_Verifier: Claude (gsd-verifier)_
