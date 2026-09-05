---
phase: 03-pitch-renderer-squad-views
plan: 03
subsystem: ui
tags: [react, tanstack-query, rate-my-team, plan-transfers, pitch-diff]

requires:
  - phase: 03-pitch-renderer-squad-views
    provides: "plan 03-01's Pitch/PlayerCard diffs+ghost prop surface, joinSquad/deriveViceCaptain/deriveFormation, lib/api.ts's Phase 3 type surface; plan 03-02's RateTab tab shell, four vanilla tiles, and lib/pairMoves.ts"
provides:
  - "RateDiff.tsx: one pitch carrying both D-18's suggested-transfer diff (out treatment + ghost insert card, exact-name matching with a documented no-overlay degrade) and D-19's 'Your best XI for GW{n}' section, plus a textual swap line that survives a failed name match"
  - "resolveRateOverlay(): the pure, independently-unit-tested move-to-card resolution helper backing RateDiff's diff overlay"
  - "PlanTransfers.tsx: verbatim vanilla plan-transfers controls (FT input, five-option horizon select, Plan my transfers CTA), the honest horizon-gated wait copy, and the full per-week output (Moves/Projected XI tiles, week-one-open collapsible squad pitch, closing note)"
  - "RateTab.tsx now mounts the complete Rate-my-team surface: four tiles + diff pitch + best-XI + plan-transfers flow"
affects: [03-04]

actuals:
  tokens: 13229
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "resolveRateOverlay() and postPlan() both exported as pure/near-pure functions separate from their consuming components, so the exact-match/degrade branches and the request-body conditional are unit-testable without full component rendering"
    - "The diff and the best-XI section share one <Pitch> mount (xi[] already IS the best-XI-for-this-GW) rather than mounting the squad twice — satisfies D-18's single-pitch rule and D-19's copy-preservation rule simultaneously"
    - "PlanTransfers.tsx builds its per-week squad pitches through the same joinSquad/deriveViceCaptain/Pitch trio as SquadTab.tsx and RateDiff.tsx — no second squad-to-pitch renderer anywhere in the phase"

key-files:
  created:
    - frontend/src/components/RateDiff.tsx
    - frontend/src/components/RateDiff.test.tsx
    - frontend/src/components/PlanTransfers.tsx
    - frontend/src/components/PlanTransfers.test.tsx
    - frontend/src/test/fixtures/rate_response_hold.json
    - frontend/src/test/fixtures/plan_response.json
  modified:
    - frontend/src/components/team/RateTab.tsx
    - frontend/src/components/team/RateTab.test.tsx
    - frontend/src/test/fixtures/rate_response.json

key-decisions:
  - "Chose the single-pitch arrangement the plan's flagged_assumption left to the executor: one <Pitch> under the verbatim 'Your best XI for GW{n}' heading/sub-copy, with the diff's diffs/ghost props layered directly onto it, rather than two separate pitch mounts."
  - "Changed rate_response.json's best_move fixture from sell=Egan(bench DEF)/buy=Gvardiol(already-owned DEF starter) to sell=Havertz(starting FWD)/buy=Haaland(not owned, FWD) — the original pairing put the 'out' card on a bench player and the 'buy' target on an already-owned starter, which cannot satisfy the 'ghost sits in the same formation row as the out card' acceptance criterion and is not a coherent transfer suggestion (you cannot buy a player you already own)."
  - "PlanTransfers.tsx takes xpTable: XpRow[] as an explicit prop (RateTab fetches it once via TanStack Query and threads it to both RateDiff and PlanTransfers) rather than each planned week's squad pitch re-fetching its own join source."
  - "Local request-state via useState (idle/pending/error/success), not TanStack Query's useMutation — no existing precedent for useMutation in this codebase, and vanilla's own async/await try/catch shape ports more directly this way."

patterns-established:
  - "postPlan()'s {detail}-extraction error handling mirrors RateTab's fetchRate() precedent exactly (fetchApi discards the response body on failure) — the third call site in this phase writing its own fetch instead of the shared helper for this specific reason."

requirements-completed: [PITCH-04]

coverage:
  - id: D1
    description: "Rate tab shows the user's own best XI on a single pitch with the suggested transfer marked (out treatment + ghost insert card in the same formation row), and a swap line with the expected points gain"
    requirement: PITCH-04
    verification:
      - kind: unit
        ref: "src/components/RateDiff.test.tsx — resolveRateOverlay unit tests (null bestMove, unique match, zero/multiple-match sell degrade, zero/multiple-match buy degrade); component tests for exactly-one-pitch, accessible out label + exactly-one-ghost, same-formation-row placement, swap-line text content"
        status: pass
      - kind: unit
        ref: "src/components/team/RateTab.test.tsx — 'mounts the diff pitch below the four tiles, with the suggested transfer marked'"
        status: pass
    human_judgment: true
    rationale: "Visual verification (pitch layout, ghost card styling, dark mode) is deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase, consistent with 03-01/03-02's SUMMARYs."
  - id: D2
    description: "Hold case (best_move: null) renders a clean pitch with no out treatment, no ghost card, and no swap line"
    requirement: PITCH-04
    verification:
      - kind: unit
        ref: "src/components/RateDiff.test.tsx — 'renders no out treatment, no ghost card, and no swap line for the Hold fixture' (rate_response_hold.json)"
        status: pass
      - kind: unit
        ref: "src/components/team/RateTab.test.tsx — 'renders a clean pitch with no overlays for the Hold fixture'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Best-XI-for-this-GW heading and sub-copy render verbatim over the same pitch data as the diff"
    requirement: PITCH-04
    verification:
      - kind: unit
        ref: "src/components/RateDiff.test.tsx — 'renders the verbatim best-XI heading and sub-copy'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Plan-transfers controls reproduce vanilla's copy, bounds, and options exactly: verbatim explanatory paragraph, FT input (min=1 max=5, prefilled from the rating's estimate, falling back to 1), five-option horizon select (no five-gameweek option) defaulting to 3 gameweeks, and the request body's conditional free_transfers key"
    requirement: PITCH-04
    verification:
      - kind: unit
        ref: "src/components/PlanTransfers.test.tsx — horizon-select options/default, FT prefill/fallback/bounds, verbatim paragraph text, request-body free_transfers presence/absence"
        status: pass
    human_judgment: false
  - id: D5
    description: "The multi-gameweek wait warning (10-60s) appears only above a one-gameweek horizon; a failed plan request renders verbatim 'Planning failed: {message}'; the button disables while pending"
    requirement: PITCH-04
    verification:
      - kind: unit
        ref: "src/components/PlanTransfers.test.tsx — horizon-3 wait copy includes both the pluralised text and the warning, horizon-1 wait copy has neither the 's' nor '10-60s'; rejected request renders 'Planning failed:'; button disabled while pending"
        status: pass
    human_judgment: false
  - id: D6
    description: "Each planned week renders vanilla's Moves tile (pairMoves output or Hold, hit-cost clause entirely omitted when hits is zero, FT-carried note) and Projected XI tile (xi_xp, 8/10 GWs range omitted when that week's interval is null, captain, bank), a week-one-open collapsible squad pitch, and the verbatim closing note"
    requirement: PITCH-04
    verification:
      - kind: unit
        ref: "src/components/PlanTransfers.test.tsx — heading variants, hit-cost clause present/absent, Hold value, null-interval Projected XI detail, exactly-one-open-disclosure (week one's), each week's disclosure containing a 15-row pitch, closing paragraph present exactly once, single-week plan renders one 'do this now' block with no 'planned' heading"
        status: pass
    human_judgment: false

duration: 48min
completed: 2026-09-03
status: complete
---

# Phase 3 Plan 3: Rate Tab Completion — Diff, Best XI, and Plan Transfers Summary

**The Rate tab is complete: a single-pitch visual diff of the suggested transfer (out treatment + ghost card, degrading gracefully to text-only on a name-match failure), the verbatim best-XI-for-this-GW section, and the full multi-week plan-transfers flow with vanilla's exact copy, bounds, and per-week output.**

## Performance

- **Duration:** 48 min
- **Tasks:** 3
- **Files created/modified:** 9
- **Commits:** 3 task commits

## Accomplishments

- `RateDiff.tsx` joins the rating's `xi[]` through the same `joinSquad`/`deriveFormation`/`deriveViceCaptain` trio the Squad tab uses, and renders exactly one `<Pitch>` carrying both D-18's suggested-transfer diff and D-19's best-XI section — never two pitches.
- `resolveRateOverlay()` resolves `best_move`'s 0-or-1 sell/buy names by exact string match only (never substring), building the ghost card from `xp_table.json`'s full pool (the only place a not-yet-owned player can be found) and degrading to "no overlay, text-only swap line" on any zero/multiple-match ambiguity — independently unit-tested for every branch.
- `rate_response.json`'s `best_move` fixture was corrected from a bench-player-out/already-owned-buy pairing (inherited from plan 03-02, which only needed it for tile-copy tests) to a starting-FWD-out/not-owned-FWD-buy pairing that actually satisfies the "ghost sits in the same formation row as the out card" contract.
- `PlanTransfers.tsx` reproduces vanilla's plan-transfers controls, request body, and wait/error copy verbatim, then renders every planned week's Moves/Projected-XI tiles and a week-one-open collapsible squad pitch through the shared `<Pitch>` component, closing with the verbatim "Week one is the decision to act on…" note.
- `RateTab.tsx` now mounts the complete Rate-my-team surface — four tiles, diff pitch, best XI, plan flow — completing PITCH-04 and this phase's last user-facing gap.

## Task Commits

1. **Task 1: RateDiff — one pitch, the suggested swap marked on it, and the best-XI section** - `9e9a114` (feat)
2. **Task 2: Plan transfers — verbatim controls, the plan request, and the honest wait copy** - `228a9ba` (feat)
3. **Task 3: Per-week plan output — moves, projected XI, the collapsible squad pitch, and the closing note** - `8c73cf2` (feat)

**Plan metadata:** commit follows this SUMMARY.

## Files Created/Modified

- `frontend/src/components/RateDiff.tsx` — the diff/best-XI pitch, `resolveRateOverlay()`
- `frontend/src/components/RateDiff.test.tsx` — pure-function + component tests
- `frontend/src/components/PlanTransfers.tsx` — controls, request, per-week output, `PlanWeekBlock`
- `frontend/src/components/PlanTransfers.test.tsx` — controls + per-week tests
- `frontend/src/components/team/RateTab.tsx` — fetches `xp_table.json`, mounts `RateDiff` + `PlanTransfers`
- `frontend/src/components/team/RateTab.test.tsx` — fixed pre-existing blanket fetch mocks to URL-aware mocking (see Deviations), added mount coverage
- `frontend/src/test/fixtures/rate_response.json` — corrected `best_move` pairing
- `frontend/src/test/fixtures/rate_response_hold.json` — Hold + null-interval fixture
- `frontend/src/test/fixtures/plan_response.json` — three-week plan fixture (real move + hits, hold, null interval)

## Decisions Made

- Single-pitch arrangement chosen for the flagged best-XI/diff layout discretion — see key-decisions above.
- `rate_response.json`'s `best_move` fixture corrected (Havertz→Haaland, both FWD) — see key-decisions above.
- `PlanTransfers.tsx` takes an explicit `xpTable` prop rather than fetching its own copy.
- Local `useState`-based request lifecycle over `useMutation` — no existing precedent in this codebase for the latter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing RateTab.test.tsx fetch mocks would have broken once RateDiff needed xp_table.json**
- **Found during:** Task 1, wiring `RateDiff` into `RateTab.tsx`
- **Issue:** The `describe("RateTab (03-02 Task 3)")` block's tests mocked `globalThis.fetch` to return the same `rateFixture` object for *every* URL, blanket-style. Once `RateTab` added a second query for `/data/xp_table.json`, that query would receive the rate-response object instead of an `XpRow[]` array, and `RateDiff`'s `joinSquad`/`xpTable.map` calls would throw at render time — silently breaking every test in that block, not just new ones.
- **Fix:** Rewrote the block's mocking to a URL-keyed helper (`mockFetch`), mirroring the URL-aware pattern the "lazy-fetch integration" describe block below it already used, with `/data/xp_table.json` mapped to the correct `xp_table_squad.json` fixture.
- **Files modified:** `frontend/src/components/team/RateTab.test.tsx`
- **Verification:** All 8 pre-existing tests in that block re-verified passing after the rewrite; no assertion text changed.
- **Committed in:** `9e9a114` (Task 1 commit)

**2. [Rule 3 - Blocking] `fetchMock.mock.calls[0]` cast rejected by the stricter `tsc -b` build-mode check**
- **Found during:** Task 3's plan-level `bash scripts/verify_frontend_build.sh` gate
- **Issue:** `vi.fn(() => Promise.resolve(...))` infers a zero-argument call signature, so `fetchMock.mock.calls[0] as [string, RequestInit]` failed TS2352 ("neither type sufficiently overlaps") only under `tsc -b`'s stricter mode — plain `tsc --noEmit` (run after Tasks 1/2) did not catch it, matching the exact class of gap 03-01's SUMMARY already recorded for `splitPitchRows`.
- **Fix:** Two-step cast (`as unknown as [string, RequestInit]`) in both request-body assertion tests.
- **Files modified:** `frontend/src/components/PlanTransfers.test.tsx`
- **Verification:** `npm run typecheck` and `bash scripts/verify_frontend_build.sh` both exit 0; full suite re-verified green (315/315).
- **Committed in:** `8c73cf2` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug — Rule 1, 1 blocking — Rule 3).
**Impact on plan:** Both fixes were necessary for the plan's own verification gates to pass. No scope creep — confined to test infrastructure the plan's own tasks touched.

## Issues Encountered

- `screen.findByText(/GW\d+/)` as a generic "wait for the plan output to render" helper matched multiple elements (each week's `<h2>` heading and its `<summary>Squad for GW{n}</summary>`, both of which independently contain "GW" + a digit as their direct text-node content) — not a code defect, a test-helper query correction. Narrowed to `/do this now/`, which is unique to the first week's heading in every fixture used.

## Known Stubs

None. Every rendered value comes from the rating/plan API response or the joined `xp_table.json` pool; the degrade paths (no out treatment, no ghost) are intentional, tested null-safety/ambiguity behavior, not stubs.

## Threat Flags

None. This plan's threat-model mitigations (T-03-10 fixed five-option horizon + in-flight button disable + server solve cache; T-03-11 exact-match-only overlay resolution with documented degrade; T-03-12 structured `pairMoves` objects, no HTML-string construction) were verified by this plan's own tests. Zero packages installed (T-03-SC).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- PITCH-04 is complete; the Rate tab now carries the full vanilla-parity surface (tiles, diff, best XI, plan) plus the new pitch diff centerpiece.
- **Flagged for end-of-phase UAT (not auto-verifiable):** the plan's own `prohibitions` entry — "no vanilla rate or plan content is dropped in the rebuild" — carries `verification: unverified` in the plan's frontmatter by design; a side-by-side read against `web/team.html` is recommended before Phase 7's cutover (CUT-01), though every individual copy string this plan touched was verified verbatim against source during implementation.
- **Carried forward for 03-04:** `PlanTransfers.tsx`'s `xpTable` prop pattern (fetched once in `RateTab.tsx`, threaded down) is available as precedent if the loaded-team/solve flow needs the same full-pool join.
- **Deferred to end-of-phase UAT** (per `workflow.human_verify_mode = end-of-phase`): visual verification of the diff pitch's out-treatment styling, ghost-card dashed border, and the plan flow's collapsible-squad interaction — jsdom proves structure and text content but not visual layout.

---
*Phase: 03-pitch-renderer-squad-views*
*Completed: 2026-09-03*

## Self-Check: PASSED

All 9 key files verified present on disk; all 3 task commits (`9e9a114`,
`228a9ba`, `8c73cf2`) verified present in `git log`.
