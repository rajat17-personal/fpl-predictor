---
phase: 03-pitch-renderer-squad-views
plan: 02
subsystem: ui
tags: [react, tanstack-query, react-router, aria-tabs, chip-timing, rate-my-team]

requires:
  - phase: 03-pitch-renderer-squad-views
    provides: "plan 03-01's Pitch/PlayerCard component surface, lib/api.ts's Phase 3 type surface, joinSquad/deriveViceCaptain/deriveFormation utilities"
provides:
  - "/team as a three-ARIA-tab shell (Squad default, Rate my team, Chips) with ?entry= and ?tab= as the only URL state, mounting only the active tab so an unopened tab never fires a request"
  - "The load-your-own-team flow: numeric entry-ID input against /api/team/{entry}, with selectLoadedSquad() reconstructing a legal starting eleven + captain from picks that carry no xp/starting/captain"
  - "The Chips tab: a horizontal current-GW-to-38 timeline with DGW/BGW markers derived from chips.json's integer club counts, and the verbatim 'Why GW{n}' note callout"
  - "The Rate tab: on-demand /api/rate/{entry} fetch with vanilla's exact wait/error copy and four tiles (Team score, Season so far, Captain, Best move)"
  - "lib/pairMoves.ts — the shared, tested sell/buy pairing port both wave-3 plans (03-03/03-04) consume"
affects: [03-03, 03-04]

actuals:
  tokens: 18974
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "selectLoadedSquad(): brute-force search over the DEF(3-5)/MID(2-5)/FWD(1-3) formation-bound combinations, maximising joined xp, to reconstruct a legal eleven from an API response that carries no starting/captain flags — exported for plan 03-04 to reuse after a solve"
    - "A page-local fetch function (fetchRate in RateTab.tsx) bypassing lib/api.ts's shared fetchApi when the shared helper's error handling can't reproduce vanilla's exact {message} extraction from the response body's detail field — same precedent as routes/Scoreboard.tsx"
    - "Team.tsx mounts only the active tab's panel (never render-but-hidden) so D-20's per-tab lazy fetch is structurally guaranteed, not just conventionally followed"

key-files:
  created:
    - frontend/src/components/team/SquadTab.tsx
    - frontend/src/components/team/SquadTab.test.tsx
    - frontend/src/components/team/ChipsTab.tsx
    - frontend/src/components/team/ChipsTab.test.tsx
    - frontend/src/components/team/RateTab.tsx
    - frontend/src/components/team/RateTab.test.tsx
    - frontend/src/components/ChipTimeline.tsx
    - frontend/src/components/ChipTimeline.test.tsx
    - frontend/src/lib/pairMoves.ts
    - frontend/src/lib/pairMoves.test.ts
    - frontend/src/test/fixtures/team_response.json
    - frontend/src/test/fixtures/chips.json
    - frontend/src/test/fixtures/chips_dgw.json
    - frontend/src/test/fixtures/rate_response.json
  modified:
    - frontend/src/routes/Team.tsx
    - frontend/src/routes/Team.test.tsx
    - frontend/src/lib/api.ts

key-decisions:
  - "Fixed lib/api.ts's TeamResponse.picks typing (Rule 1 bug fix): it was typed SquadRow[] (implying xp/starting/captain), but api/main.py's _fetch_team only ever returns player_code/name/team/position/price_m. Added a narrower TeamPick interface and widened TeamResponse.manager to the fields _fetch_team actually populates."
  - "selectLoadedSquad ties resolve by first-found-in-loop-order under floating-point summation, not a fully deterministic mathematical tiebreak — acceptable per the plan's 'highest-xp legal combination' wording, which does not mandate a specific tiebreak rule."
  - "RateTab.tsx writes its own fetchRate() rather than using lib/api.ts's shared fetchApi, because fetchApi discards the response body on a failed request (only the HTTP status survives) and D-19 requires vanilla's exact detail-field extraction for the error copy."
  - "Chip timeline markers report the affected-club count (not names) per this plan's <planner_corrections> — chips.json's dgw_clubs/bgw_clubs are integers, not club-name arrays (already ledgered as PARITY-DEVIATIONS row 13 by plan 03-01)."

patterns-established:
  - "Team.tsx owns ?entry=/?tab= URL state centrally and passes plain load/clear callbacks down to SquadTab, rather than each tab reading useSearchParams independently — keeps the 'only ?entry=/?tab= reach the URL' invariant (D-11) enforced in one place."

requirements-completed: [PITCH-03, UIX-03]

coverage:
  - id: D1
    description: "/team presents exactly three ARIA tabs (Squad default, Rate my team, Chips), each an ARIA tab/tabpanel pair; only the active panel is mounted so an unopened tab cannot fetch"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/routes/Team.test.tsx — getAllByRole('tab') returns exactly 3 with the expected accessible names; Squad tab aria-selected true by default; /team?tab=chips opens the Chips panel with Squad's tab aria-selected false"
        status: pass
    human_judgment: false
  - id: D2
    description: "Arriving at /team with no query string renders the model squad and fires zero /api/ requests; opening Chips fires zero /api/ requests; opening Squad never triggers the rate request, switching to Rate fires exactly one"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/routes/Team.test.tsx — zero /api/ calls with no query string and on the Chips tab"
        status: pass
      - kind: unit
        ref: "src/components/team/RateTab.test.tsx — 'fires zero /api/rate/ requests on the Squad tab, exactly one after switching to Rate'"
        status: pass
    human_judgment: false
  - id: D3
    description: "/team?entry=6980093 loads that manager's squad without interaction; /team?entry=...&tab=rate runs the rating immediately on arrival; Change team clears ?entry= and returns to the model squad"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/routes/Team.test.tsx — 'fires exactly one /api/team/6980093 request with no user interaction'"
        status: pass
      - kind: unit
        ref: "src/components/team/RateTab.test.tsx — 'runs the rating immediately on arrival at /team?entry=6980093&tab=rate' and 'Change team clears ?entry= and returns the Squad tab to the model squad view'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Empty Load-team input is a no-op (zero requests); a rejected /api/team request renders the verbatim 'Couldn't load that team:' copy; the loaded squad is normalised into exactly 11 starters/1 GK/1 captain, with a pick missing from the xp table benched, not started"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/routes/Team.test.tsx and src/components/team/SquadTab.test.tsx — empty-input no-op, error copy, starter/GK/captain counts, missing-player bench placement"
        status: pass
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — selectLoadedSquad direct unit tests (11 starters, 1 GK, 1 captain, xp:0 for an unmatched pick, 15 rows preserved)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Chip timeline: current-GW-to-38 markers, DGW/BGW badges derived from integer club counts (never invented names), current GW distinguishable by accessible attribute, marker popover reports the count capped at 240px, empty structure renders EmptyState, failed fetch renders ErrorState+Retry, the note callout reproduces chips.json's note verbatim, container scrolls horizontally"
    requirement: UIX-03
    verification:
      - kind: unit
        ref: "src/components/ChipTimeline.test.tsx — classifyMarker unit tests; 36-marker all-plain live fixture; DGW/BGW marker assignment on chips_dgw.json; current-GW data-attribute; popover count + 240px cap; overflow-x-auto class"
        status: pass
      - kind: unit
        ref: "src/components/team/ChipsTab.test.tsx — heading/sub/callout verbatim note text; EmptyState on empty structure; ErrorState+Retry on a rejected fetch; DGW/BGW rendering via the tab"
        status: pass
    human_judgment: false
  - id: D6
    description: "Rate tab: on-demand fetch with vanilla's exact 'Solving your squad…' wait copy and 'Couldn't rate that team:' error copy; four tiles reproduce vanilla's exact headings/values/fallbacks including the xi_p10-null omission, fmtRank en-dash, and the Hold/best_move branches"
    requirement: UIX-03
    verification:
      - kind: unit
        ref: "src/components/team/RateTab.test.tsx — tile headings; 8/10 GWs clause present/absent by xi_p10 nullness; Hold branch; en-dash for a null overall_rank; exact wait copy; exact error copy; no fetch with no entry loaded"
        status: pass
    human_judgment: false
  - id: D7
    description: "pairMoves() is a verbatim algorithmic port of web/team.html's pairMoves(), returning structured { sellName, buyName, position } objects (never markup), pairing by array order within each position and falling back to '?' when a position has more sells than buys"
    verification:
      - kind: unit
        ref: "src/lib/pairMoves.test.ts — structured-object shape with no angle brackets; two-MID array-order pairing; more-sells-than-buys '?' fallback; empty-sells case"
        status: pass
    human_judgment: false

duration: 62min
completed: 2026-09-03
status: complete
---

# Phase 3 Plan 2: Squad Load Flow, Chip Timing, and Rate Tiles Summary

**`/team` becomes a real three-ARIA-tab page — Squad (default + load-your-own-team), Rate my team, and Chips — with `?entry=`/`?tab=` as the only URL state, a legal-starter-eleven reconstruction for any loaded team, a DGW/BGW gameweek timeline, and vanilla-verbatim rate tiles.**

## Performance

- **Duration:** 62 min
- **Started:** 2026-09-03T00:38:00Z
- **Completed:** 2026-09-03T01:40:00Z
- **Tasks:** 3
- **Files created/modified:** 17

## Accomplishments

- `Team.tsx` is now the tab shell: three `role="tab"`/`role="tabpanel"` pairs, `?tab=` defaulting to and falling back to Squad on any unrecognised value, `?entry=` as the only other URL state, and only the active panel ever mounted (D-20's per-tab lazy fetch is structural, not conventional).
- `SquadTab.tsx` carries 03-01's model-squad view forward unchanged and adds the load-your-own-team flow against `/api/team/{entry}`, including `selectLoadedSquad()` — an exported, unit-tested helper that reconstructs a legal starting eleven and captain from an API response that carries no `xp`/`starting`/`captain` fields at all.
- `ChipTimeline.tsx`/`ChipsTab.tsx` render the current-GW-to-38 timeline with DGW/BGW markers derived from `chips.json`'s integer club counts (never invented names — this plan's `<planner_corrections>`, PARITY-DEVIATIONS row 13) and the verbatim "Why GW{n}" note callout.
- `RateTab.tsx` fetches `/api/rate/{entry}` on demand and reproduces `web/team.html`'s four tiles and copy exactly, including the `xi_p10`-null omission, the `fmtRank` en-dash, and the Hold/`best_move` branches.
- `lib/pairMoves.ts` ports `web/team.html`'s `pairMoves()` verbatim, landing here (rather than in either wave-3 plan) so plans 03-03/03-04 both import one tested module instead of each writing their own.

## Task Commits

1. **Task 1: Three-tab shell, ?entry= and ?tab= URL state, and the load-your-own-team flow** - `1e77468` (feat)
2. **Task 2: Chips tab — gameweek timeline with DGW/BGW markers and the verbatim "why this GW" callout** - `45430e0` (feat)
3. **Task 3: Rate tab — on-demand rating, the four verbatim vanilla tiles, and the shared pairMoves port** - `9bedd2c` (feat)

**Additional test-coverage commits** (same-plan follow-ups, not new tasks): `9595289` (test — `?entry=&tab=rate` deep-link auto-fetch and Change-team clearing, end-to-end) and `3f48162` (test — Chips tab fires zero `/api/` requests).

**Plan metadata:** commit follows this SUMMARY.

## Files Created/Modified

- `frontend/src/routes/Team.tsx` — replaces the placeholder-free single-view route with the three-tab shell owning `?entry=`/`?tab=`
- `frontend/src/components/team/SquadTab.tsx` — model-squad view (unchanged from 03-01) + loaded-team flow + `selectLoadedSquad`
- `frontend/src/components/team/ChipsTab.tsx` — chip-timing tab
- `frontend/src/components/team/RateTab.tsx` — rate-my-team tab
- `frontend/src/components/ChipTimeline.tsx` — the GW timeline strip + `classifyMarker`
- `frontend/src/lib/pairMoves.ts` — verbatim `pairMoves()` port, `MovePair` type
- `frontend/src/lib/api.ts` — fixed `TeamResponse`'s `picks` typing (see Deviations)
- Test files for every new module/component, plus `Team.test.tsx` extended for the tab shell
- Fixtures: `team_response.json`, `chips.json` (verbatim live export), `chips_dgw.json` (hand-built DGW/BGW coverage), `rate_response.json`

## Decisions Made

- Fixed `lib/api.ts`'s `TeamResponse.picks` typing — see Deviations below.
- `selectLoadedSquad`'s DEF/MID/FWD split maximises total joined `xp` via brute-force search over `squad_ilp.py`'s own formation bounds (3-5/2-5/1-3); ties are resolved by loop order under floating-point summation rather than a fully deterministic rule — acceptable per the plan's "highest-xp legal combination" wording.
- `RateTab.tsx` writes its own `fetchRate()` instead of reusing `lib/api.ts`'s shared `fetchApi`, because vanilla's error copy requires the response body's `detail` field (which `fetchApi` discards on failure) — same precedent as `routes/Scoreboard.tsx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `lib/api.ts`'s `TeamResponse.picks` was typed as `SquadRow[]`, implying fields the API never returns**
- **Found during:** Task 1, reading `api/main.py`'s `_fetch_team` per the plan's own `<read_first>` ("the real integration risk")
- **Issue:** `TeamResponse.picks: SquadRow[]` requires `xp`/`starting`/`captain`, but `_fetch_team`'s picks comprehension (lines 199-205) only ever returns `player_code`/`name`/`team`/`position`/`price_m`. Code trusting the old type could read `pick.starting` and compile cleanly while reading `undefined` at runtime.
- **Fix:** Added a narrower `TeamPick` interface (the real five fields) and changed `TeamResponse.picks` to `TeamPick[]`; also added the missing `entry` field and widened `manager` to the fields `_fetch_team` actually populates (`overall_points`/`overall_rank`/`gw_points`), matching `RateResponse.manager`'s existing shape.
- **Files modified:** `frontend/src/lib/api.ts`
- **Verification:** `npm run typecheck` passes; `SquadTab.tsx`'s `selectLoadedSquad` and its tests exercise the corrected shape directly.
- **Committed in:** `1e77468` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — Rule 1).
**Impact on plan:** Necessary correction of a type that would otherwise have silently masked a real runtime gap (the exact risk the plan's `<read_first>` flagged). No scope creep — confined to the one field this plan's Task 1 already had to reason about.

## Issues Encountered

- The DEF/MID/FWD formation search in `selectLoadedSquad` initially produced a test expectation based on manual (exact-decimal) arithmetic that didn't match the actual JS floating-point sum for a genuine tie between two combinations (`(3,4,3)` and `(4,4,2)`, both summing to `27.55` on paper but differing by `~3.5e-15` in IEEE 754). Recomputed the expected bench composition directly from the running code rather than by hand and corrected the test — not a code defect, a test-authoring correction.

## Known Stubs

None. Every rendered value comes from a real fetched/joined data source; there are no hardcoded empty values or "coming soon" placeholders in the shipped tabs.

## Threat Flags

None. This plan's three threat-model mitigations (T-03-05 numeric-input DoS guard, T-03-06 `?tab=` fallback, T-03-07 JSX-only rendering + structured `pairMoves`) were verified by this plan's own tests; T-03-08 (no team persistence) is enforced by the plan's own storage grep gate, re-run clean after every task. No new security-relevant surface beyond what the threat model already covers.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `selectLoadedSquad` (starter/captain reconstruction) is exported from `SquadTab.tsx` specifically so plan 03-04 can reuse it after a solve, per this plan's own instruction.
- `lib/pairMoves.ts` is committed and tested for both wave-3 plans (03-03, 03-04) to import without re-creating it.
- PARITY-DEVIATIONS row 13 (DGW/BGW integer counts, not club names) — seeded by 03-01, confirmed still accurate and unchanged by this plan's implementation.
- Carried forward for 03-03/03-04: `Team.tsx` now owns `?entry=`/`?tab=` centrally via `loadEntry`/`clearEntry`/`selectTab` closures — any solve-flow or rate-diff work those plans add should read `entry` as a prop rather than re-deriving it from `useSearchParams` independently.

---
*Phase: 03-pitch-renderer-squad-views*
*Completed: 2026-09-03*

## Self-Check: PASSED

All 17 key files verified present on disk; all 5 commits (`1e77468`, `45430e0`,
`9bedd2c`, `9595289`, `3f48162`) verified present in `git log`.
