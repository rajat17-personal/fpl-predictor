---
phase: 03-pitch-renderer-squad-views
plan: 01
subsystem: ui
tags: [react, pitch, kit-svg, tanstack-query, css-grid, accessibility]

requires:
  - phase: 02-data-layer-non-pitch-pages
    provides: PageShell footer/nav shell, usePageMeta route table, StatusFlag accessible popover pattern, bandCell.ts band geometry math, dark-safe token palette
provides:
  - "/team route renders the model's recommended squad on a green formation-row pitch with a 4-card bench, sourced live from squad.json + xp_table.json + meta.json"
  - "The full Phase 3 type surface in frontend/src/lib/api.ts (SquadRow/Response, SolveRequest/Result, RateResponse, PlanResponse, TeamResponse, ChipsResponse) for plans 03-02/03-03/03-04 to consume without re-editing the file"
  - "lib/formation.ts (deriveFormation, splitPitchRows) and lib/squadJoin.ts (joinSquad, deriveViceCaptain) — tested, generic-over-SquadRow utilities"
  - "components/pitch/{kitMap,Kit,PlayerCard,Pitch}.tsx — the full pitch/kit/card component set, including the widened Pitch props (marks/diffs/onMark/ghost) plans 03-03/03-04 consume"
  - "docs/decisions/pitch-kit-sourcing.md — the committed PITCH-01 trademark posture"
  - "PARITY-DEVIATIONS.md for Phase 3, seeded with rows 9-13"
affects: [03-02, 03-03, 03-04]

actuals:
  tokens: 21661
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Generic splitPitchRows<T extends SquadRow> so a SquadRow subtype (PitchPlayer) survives both tsc --noEmit and the stricter tsc -b build-mode check"
    - "Below-400px range-line tap-reveal gated purely by a Tailwind min-[400px]: CSS variant, never JS media-query state"
    - "Pitch row centering via computed grid-column start offset (never justify-content on 1fr tracks), preserving the fixed 5-column grid at every viewport width"

key-files:
  created:
    - frontend/src/lib/formation.ts
    - frontend/src/lib/formation.test.ts
    - frontend/src/lib/squadJoin.ts
    - frontend/src/lib/squadJoin.test.ts
    - frontend/src/components/pitch/kitMap.ts
    - frontend/src/components/pitch/kitMap.test.ts
    - frontend/src/components/pitch/Kit.tsx
    - frontend/src/components/pitch/Kit.test.tsx
    - frontend/src/components/pitch/PlayerCard.tsx
    - frontend/src/components/pitch/PlayerCard.test.tsx
    - frontend/src/components/pitch/Pitch.tsx
    - frontend/src/components/pitch/Pitch.test.tsx
    - frontend/src/routes/Team.test.tsx
    - frontend/src/test/fixtures/squad.json
    - frontend/src/test/fixtures/xp_table_squad.json
    - docs/decisions/pitch-kit-sourcing.md
    - .planning/phases/03-pitch-renderer-squad-views/PARITY-DEVIATIONS.md
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/index.css
    - frontend/src/routes/Team.tsx
    - frontend/src/components/PageShell.tsx
    - frontend/src/components/PageShell.test.tsx
    - frontend/src/lib/usePageMeta.ts
    - frontend/src/routes/routeIsolation.test.tsx

key-decisions:
  - "Resolved Claude's-Discretion: the default Squad tab (/team, no ?entry=) is view-only — no lock/exclude/solve controls — since the loaded-team flow (plan 03-04) already fully covers that interaction surface"
  - "Resolved Claude's-Discretion: goalkeepers use one fixed club-independent kit (#3A3A3A/#EAB308/plain), never outfield club colors"
  - "Resolved Claude's-Discretion: an unmapped team_short falls back to a neutral kit (#9CA3AF/#4B5563/plain) plus a dev-only console warning, never a thrown error"
  - "Made splitPitchRows generic over T extends SquadRow (Rule 3 deviation) — plain tsc --noEmit missed the narrowing loss that the stricter tsc -b build-mode check (npm run build) caught"

patterns-established:
  - "Pitch/PlayerCard/Pitch props (marks, diffs, onMark, ghost) declared once in this plan so plans 03-03/03-04, which run in parallel, never re-edit these files"

requirements-completed: [PITCH-01, PITCH-02, UIX-01, UI-07]

coverage:
  - id: D1
    description: "/team fetches squad.json + xp_table.json + meta.json at runtime, joins by player_code, derives the formation label, and renders the model's 15-man squad as formation rows + a 4-card bench"
    requirement: PITCH-02
    verification:
      - kind: unit
        ref: "src/routes/Team.test.tsx — renders all 15 fixture player names, exactly 4 inside the bench container, formation label matches fixture's own formation, EmptyState on zero-row squad, ErrorState on fetch failure"
        status: pass
      - kind: unit
        ref: "src/lib/formation.test.ts — deriveFormation matches the live fixture's own formation string and a hand-built 5-DEF set; splitPitchRows preserves source order"
        status: pass
      - kind: unit
        ref: "src/lib/squadJoin.test.ts — joinSquad matches only on player_code, deriveViceCaptain excludes the captain and null-safe skips"
        status: pass
      - kind: unit
        ref: "src/components/pitch/kitMap.test.ts — all 20 live team_short codes resolve to an explicit KIT_MAP entry, never the fallback"
        status: pass
    human_judgment: true
    rationale: "Task 2's <verify> carries an explicit <human-check> for the rendered pitch (green surface, formation shape, kit legibility, badge placement, phone-width shrink, dark mode) — jsdom proves structure and text content but not visual layout; deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase."
  - id: D2
    description: "Full player card: C/VC badges (mutually exclusive, derived VC), always-visible p10-p90 range line with null/equal-bounds fallbacks, Locked/Excluded/IN badges, tap-a-card action popover (Lock/Exclude/Clear + detail header), phone-width shrink"
    requirement: UIX-01
    verification:
      - kind: unit
        ref: "src/components/pitch/PlayerCard.test.tsx — 15 tests: exactly one C and one V across the fixture squad, no V when all xp_capt null, range-line text for explicit/null/equal p10-p90 with no NaN, popover open/Escape/outside-click, Clear presence, mark/diff accessible labels"
        status: pass
      - kind: unit
        ref: "src/components/pitch/Pitch.test.tsx — marks/diffs apply to exactly the named player_code, ghost card inserted immediately after the named player in the named row and announced as a suggested incoming player, null ghost renders nothing extra"
        status: pass
    human_judgment: true
    rationale: "Same Task 2 <human-check> as D1 — visual card legibility, badge placement, and the phone-width shrink are UI-07/D-07's genuinely judgment-dependent items; jsdom cannot measure viewport-driven layout. Deferred to end-of-phase UAT."
  - id: D3
    description: "PITCH-01 posture: committed decision doc (neutral SVG kits, trademark reasoning, disclaimer location), footer disclaimer gains the generic-kit-imagery sentence sitewide, nav/page-title rename to 'My team'"
    requirement: PITCH-01
    verification:
      - kind: unit
        ref: "src/components/PageShell.test.tsx — nav link reads 'My team' not 'Rate my team'; footer paragraph contains the full four-sentence disclaimer on every route"
        status: pass
      - kind: other
        ref: "test -f docs/decisions/pitch-kit-sourcing.md && grep -q 'not licensed team imagery' frontend/src/components/PageShell.tsx"
        status: pass
    human_judgment: true
    rationale: "Task 3's <verify> carries an explicit <human-check>: 'Confirm docs/decisions/pitch-kit-sourcing.md states a trademark posture you are willing to stand behind at a payment-gateway review' — a legal-posture judgment call, deferred to end-of-phase UAT."
  - id: D4
    description: "Phase 3's PARITY-DEVIATIONS.md ledger created, seeded with rows 9-13 continuing Phase 2's numbering"
    verification:
      - kind: other
        ref: "grep -v '^ *#' PARITY-DEVIATIONS.md | grep -cE '^\\| *(9|1[0-3]) *\\|' equals 5"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-03
status: complete
---

# Phase 3 Plan 1: Pitch Renderer & Squad Views — Foundation Summary

**The model's recommended squad renders live on `/team` as an FPL-style green formation pitch — neutral-SVG kits, always-visible p10-p90 range lines, C/VC badges, and a full lock/exclude/ghost-card prop surface plans 03-03/03-04 consume without touching these files again.**

## Performance

- **Duration:** 55 min
- **Tasks:** 3 (tracer + 2 auto)
- **Files created/modified:** 24
- **Commits:** 4 (3 task commits + 1 Rule 3 fix)

## Accomplishments

- `/team` fetches `squad.json`/`xp_table.json`/`meta.json` at runtime (root-relative paths, TanStack Query), joins by `player_code`, and renders the model's 15-man squad on `<Pitch>` with a derived formation label matching the export's own `"3-5-2"`.
- The full Phase 3 type surface landed in `lib/api.ts` in one pass (`SquadRow`/`SquadResponse`, `SolveRequest`/`SolveResult`, `RateResponse`, `PlanResponse`, `TeamResponse`, `ChipsResponse`) with the two `<planner_corrections>` baked in: `SquadResponse` carries five top-level keys, `ChipsGwStructure`'s club counts are `number`.
- `PlayerCard` reached its full prop surface in this plan (not deferred to later plans): C/VC badges, an always-visible range line with a below-400px tap-reveal exception, Locked/Excluded/IN badges, and a `role="menu"` action popover reusing `statusFlag.tsx`'s open/close state machine.
- `Pitch` reached its full prop surface too — `marks`, `diffs`, `onMark`, `ghost` — so plans 03-03 and 03-04, which run in parallel, never need to re-edit `Pitch.tsx` or `PlayerCard.tsx`.
- PITCH-01's trademark posture is settled: `docs/decisions/pitch-kit-sourcing.md` is committed, the footer disclaimer carries the new sentence sitewide, and the nav/page title read "My team" — closing the roadmap's FPL-CDN-capture research flag as moot and retiring the STATE.md blocker for this phase.
- Phase 3's `PARITY-DEVIATIONS.md` is seeded with all five known entries (rows 9-13), including row 13 for plan 03-02's DGW/BGW club-count divergence, ahead of that plan landing.

## Task Commits

1. **Task 1: End-to-end "the model's recommended squad renders on a pitch at /team"** - `3476004` (feat)
2. **Task 2: Complete the player card** - `0862850` (feat)
3. **Task 3: Settle the PITCH-01 posture** - `9ceec8b` (docs)

**Rule 3 fix:** `9947972` (fix) — see Deviations below.

**Plan metadata:** commit follows this SUMMARY.

## Files Created/Modified

- `frontend/src/lib/api.ts` — Phase 3 type surface (13 new interfaces/types)
- `frontend/src/index.css` — three pitch tokens (`--color-pitch-1/2/-line`), light + dark
- `frontend/src/lib/formation.ts` — `deriveFormation`, `splitPitchRows<T>` (generic)
- `frontend/src/lib/squadJoin.ts` — `joinSquad`, `deriveViceCaptain`, `PitchPlayer`
- `frontend/src/components/pitch/kitMap.ts` — 20-club kit map, `GK_KIT`, `FALLBACK_KIT`, `resolveKit`
- `frontend/src/components/pitch/Kit.tsx` — parameterised inline SVG shirt
- `frontend/src/components/pitch/PlayerCard.tsx` — full card: badges, range line, popover
- `frontend/src/components/pitch/Pitch.tsx` — 5-column formation grid + bench + ghost slot
- `frontend/src/routes/Team.tsx` — replaces the placeholder; view-only model-squad pitch
- `frontend/src/components/PageShell.tsx` — nav rename, footer disclaimer sentence
- `frontend/src/lib/usePageMeta.ts` — `/team` title/description
- `docs/decisions/pitch-kit-sourcing.md` — PITCH-01 decision doc
- `.planning/phases/03-pitch-renderer-squad-views/PARITY-DEVIATIONS.md` — Phase 3 ledger
- Fixtures: `frontend/src/test/fixtures/squad.json` (verbatim live export), `xp_table_squad.json` (joined subset + 2 non-squad rows + null-path coverage rows)
- Test files for every new module/component (9 new `*.test.ts(x)` files) plus updates to `PageShell.test.tsx`, `routeIsolation.test.tsx`, `Team.test.tsx` for the nav rename.

## Decisions Made

- View-only default Squad tab (no lock/exclude/solve controls on the model-squad pitch) — per `03-RESEARCH.md`'s Open Question 1 recommendation, since plan 03-04's loaded-team flow fully covers that interaction surface.
- Fixed, club-independent GK kit scheme (never outfield club colors) — standard football convention, resolved per `03-UI-SPEC.md`.
- Neutral fallback kit + dev-only console warning for any future unmapped `team_short` — a safety net, not a substitute for the 20-club map's completeness (asserted by `kitMap.test.ts`).
- `splitPitchRows` made generic over `T extends SquadRow` — see Deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `splitPitchRows` narrowed `PitchPlayer[]` back to `SquadRow[]`, breaking `npm run build`**
- **Found during:** Running the plan-level `bash scripts/verify_frontend_build.sh` gate after Task 3
- **Issue:** `splitPitchRows(rows: SquadRow[]): PitchRows` (`PitchRows` hardcoded to `SquadRow[]` buckets) silently discarded `PitchPlayer`'s joined `p10`/`p90`/`xp_capt`/`team_short` fields when called with a `PitchPlayer[]` array from `Pitch.tsx`. Structural typing let the *call* through both `tsc --noEmit` and normal editing, but `Pitch.tsx`'s destructured buckets were then typed `SquadRow[]`, and passing those to `<PlayerCard players={...}>` (which requires `PitchPlayer[]`) failed under the stricter `tsc -b` build-mode check (`npm run build`) — the same class of gap the Phase 2 STATE.md decisions log already recorded for `lib/api.ts`'s `WatchlistRow`/`ScoreboardSummary` typings. Plain `tsc --noEmit` passed throughout Tasks 1-3 and did not catch this.
- **Fix:** Made `PitchRows<T extends SquadRow = SquadRow>` and `splitPitchRows<T extends SquadRow>(rows: T[]): PitchRows<T>` generic, so a `PitchPlayer[]` input keeps its subtype through every bucket.
- **Files modified:** `frontend/src/lib/formation.ts`
- **Verification:** `bash scripts/verify_frontend_build.sh` now exits 0 with `BUILD PURITY OK`; `npm run typecheck` and the full `npm run test` suite (234/234) re-verified green afterward.
- **Committed in:** `9947972`

---

**Total deviations:** 1 auto-fixed (1 blocking — Rule 3).
**Impact on plan:** The fix is a type-level generalization with no runtime behavior change (verified by the unchanged, still-green 234-test suite). No scope creep — it was required to satisfy this plan's own `<verification>` block (`bash scripts/verify_frontend_build.sh` must pass).

## Issues Encountered

None beyond the deviation above.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced — every card renders real joined data from the fixtures/exports, and the fallback paths (null `p10`/`p90`/`xp_capt`, unmapped `team_short`) are intentional, tested null-safety behavior, not stubs.

## Threat Flags

None. All three threat-model mitigations declared for this plan (T-03-01 JSX text nodes only, T-03-02 no remote kit assets, T-03-03 disclaimer + decision doc) were verified by this plan's own automated gates — see Verification below. No new security-relevant surface was introduced beyond what the threat model already covers.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The full Phase 3 type surface (`lib/api.ts`), the pitch/kit/card component set (with `marks`/`diffs`/`onMark`/`ghost` already on `Pitch`/`PlayerCard`), and the PITCH-01 decision doc are all in place for plans 03-02 (solver/rate/chips within `/team`'s tabs), 03-03 (Best-XI/plan-week pitch rendering), and 03-04 (loaded-team lock/exclude/solve flow) to build on without re-editing any file this plan owns.
- **Carried forward for 03-02:** `squad.json`'s five-key top-level shape and `chips.json`'s integer DGW/BGW club counts (both `<planner_corrections>` in this plan, now typed in `lib/api.ts` and recorded in ledger row 13).
- **Carried forward for 03-03/03-04:** the resolved Claude's-Discretion items — view-only default Squad tab, fixed GK kit scheme, neutral unmapped-club fallback.
- **Deferred to end-of-phase UAT** (per `workflow.human_verify_mode = end-of-phase`): Task 2's and Task 3's `<human-check>` blocks — visual pitch/card verification (green surface, kit legibility, badge placement, phone-width shrink, dark mode) and a human read of the decision doc's trademark posture. No automated gate substitutes for these; they are queued for the phase-level UAT pass, not blocking this plan's completion.

---

*Phase: 03-pitch-renderer-squad-views*
*Completed: 2026-09-03*
