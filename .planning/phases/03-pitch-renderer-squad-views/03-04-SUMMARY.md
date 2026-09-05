---
phase: 03-pitch-renderer-squad-views
plan: 04
subsystem: ui
tags: [react, tanstack-query, solver-ux, pitch-diff, lock-exclude]

requires:
  - phase: 03-pitch-renderer-squad-views
    provides: "plan 03-01's Pitch/PlayerCard marks+diffs+onMark prop surface, joinSquad/deriveViceCaptain/deriveFormation, lib/api.ts's Phase 3 type surface; plan 03-02's SquadTab load flow, selectLoadedSquad, and Team.tsx's ?entry=/?tab= URL-state ownership; plan 03-03's lib/pairMoves.ts"
provides:
  - "SquadTab's loaded-team pitch is fully interactive: tap-a-card lock/exclude (mutually exclusive, ephemeral, never cleared by a solve), exported lockedCodes/excludedCodes derivations, and buildSolveRequest turning marks into /api/solve's numeric locks/excludes"
  - "SolveControls.tsx: three server-bound-mirrored knobs (free transfers, max transfers, plan horizon) and the 'Solving your transfers…' wait status"
  - "useSolveController(): the solve request lifecycle as an exported, independently renderHook-testable hook, with an ordering-safety guard against a superseded response ever overwriting a newer one"
  - "SolveResultsBar.tsx: moves (or Hold), the hit-cost clause omitted entirely at zero hits, bank after, XI xP alone (no interval — the endpoint returns none), captain"
  - "In-place pitch update: a completed solve re-renders the same pitch with IN badges computed against the squad as originally loaded (never the previous solve), so repeated solves and Reset both stay idempotent"
  - "'Reset to loaded squad': clears marks and the solve result locally, with no network request"
affects: []

actuals:
  tokens: 13053
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "useSolveController extracted as its own hook (not inline component state) specifically so the ordering-safety guard is directly unit-testable via renderHook — jsdom/React suppress a simulated second click on a genuinely-disabled DOM button regardless of DOM-level attribute manipulation, so a real double-click reproduction is not reliable in this test environment"
    - "The as-loaded squad and the IN-badge diff base are never separate state — both are recomputed deterministically from teamQuery.data (untouched by a solve) on every render, so Reset and idempotent re-solves fall out of the data flow rather than needing their own bookkeeping"
    - "SolveResult's kind discriminator is handled with a compiler-enforced exhaustiveness check (narrowing the non-'transfers' branch to SolveSquadResult) rather than a silent no-op, so a future third kind fails the build instead of silently doing nothing"

key-files:
  created:
    - frontend/src/components/SolveControls.tsx
    - frontend/src/components/SolveControls.test.tsx
    - frontend/src/components/SolveResultsBar.tsx
    - frontend/src/components/SolveResultsBar.test.tsx
    - frontend/src/test/fixtures/solve_transfers_response.json
  modified:
    - frontend/src/components/team/SquadTab.tsx
    - frontend/src/components/team/SquadTab.test.tsx

key-decisions:
  - "SolveControls' Free-transfers input always prefills from null->1 (SolveRequest's own server-side default), never from a live estimate — the only endpoint returning that estimate is /api/rate/{entry}, and D-20 forbids the Squad tab firing a rate-cost fetch just to prefill one input. The input stays editable per D-14, matching the plan's own flagged_assumptions note that a wrong prefill is the server's inference being wrong, not a UI defect."
  - "Extracted useSolveController() as an exported hook so T-03-16's ordering-safety guard (a superseded solve response must never overwrite a newer one) is tested via renderHook calling solveNow() twice back-to-back, rather than via two real fireEvent.click calls on the Solve transfers button — verified empirically that neither removeAttribute('disabled') nor a direct .disabled=false property assignment un-suppresses React's synthetic click handling for a button that was disabled at any point in its lifecycle in this jsdom/RTL setup, so a UI-level double-click reproduction is not reliable."
  - "The Hold condition in SolveResultsBar checks result.buys.length > 0, not pairMoves()'s own output length — pairMoves buckets by the sells side, so a response with sells but zero buys would still produce non-empty pairs (with a '?' buyName) if pairs.length itself were the check. Matches PlanTransfers.tsx's identical week.buys.length > 0 rule (found and fixed during this plan's own Task 3 verification loop, before commit)."
  - "SolveResult's kind is handled via a compiler-enforced exhaustiveness narrowing (assigning the non-'transfers' branch to SolveSquadResult) instead of a bare if with no else, per the plan's explicit 'handle the union exhaustively so the compiler enforces it' requirement — found and fixed as a small follow-up commit after Task 3's own commit."

patterns-established:
  - "buildSolveRequest(entry, values, marks) lives in SquadTab.tsx (not SolveControls.tsx) precisely so SolveControls stays ignorant of locks/excludes/player_code entirely — it only collects the three UI knobs and hands them back via onSolve; the caller owns request construction. Avoids the circular import SolveControls importing lockedCodes/excludedCodes from SquadTab would have created."

requirements-completed: [PITCH-03]

coverage:
  - id: D1
    description: "Tap a card on a loaded team's pitch to lock or exclude a player through the action menu (mutually exclusive, badge visible, Clear removes it), and the marks survive re-renders/re-solves — the default model-squad pitch stays view-only with no popover trigger at all"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — 'renders no popover trigger and no menu in the default model-squad mode'; 'locks a player…'; 'excluding an already-locked player…'; 'Clear removes the badge…'; 'keeps both marks in place after the loaded squad re-renders…'"
        status: pass
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — lockedCodes/excludedCodes derivation tests (numeric, empty when none)"
        status: pass
    human_judgment: false
  - id: D2
    description: "SolveControls exposes exactly three server-bound-mirrored inputs (free transfers 0-5, max transfers 0-15 unset by default, plan horizon 1/2/3/4/6) and the Solve transfers CTA disables with the exact 'Solving your transfers…' wait copy while the pitch stays rendered"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/components/SolveControls.test.tsx — three-input/label test, min/max/option-value tests, prefill/fallback tests, pending-disable/wait-copy tests"
        status: pass
    human_judgment: false
  - id: D3
    description: "A solve request sends numeric player_code arrays for locks/excludes (never a marked player's display name), omits max_transfers entirely when its input is empty, and a superseded response can never overwrite a newer one"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — buildSolveRequest unit tests (numeric arrays, no names in JSON.stringify, max_transfers omission); 'sends locks/excludes as numeric player_code arrays…' and 'omits max_transfers…' integration tests"
        status: pass
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — 'useSolveController ordering safety' describe block: renderHook-driven back-to-back solveNow() calls, asserting the earlier (stale) response never overwrites the later one's applied result"
        status: pass
    human_judgment: false
  - id: D4
    description: "A completed solve re-renders the same pitch in place (never a second pitch/modal) with the incoming players badged IN — computed against the squad as originally loaded, not the previous solve — and no out treatment anywhere on this pitch; a rejected solve renders the verbatim error copy"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — 'renders exactly one pitch with the solve fixture's 15 players…'; 'badges only the two incoming players…'; 'carries no out treatment…'; 'renders Couldn't solve:… on a rejected solve'"
        status: pass
    human_judgment: true
    rationale: "The pitch's visual IN-badge placement/styling is deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase, consistent with 03-01/03-02/03-03's SUMMARYs — jsdom proves structure/text content, not visual layout."
  - id: D5
    description: "The results bar renders sell-to-buy moves (or Hold when there are no buys), the hit-cost clause omitted entirely at zero hits, bank after, XI xP alone with no interval, and the captain — one pair and several pairs render through the same list"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/components/SolveResultsBar.test.tsx — full field-by-field coverage plus the single-pair/several-pairs same-list test and the no-interval-fields test"
        status: pass
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — SquadTab-level integration coverage of the same results-bar fields, plus the mutated Hold/zero-hit fixtures"
        status: pass
    human_judgment: false
  - id: D6
    description: "Locks/excludes and the solve result persist across re-solves so a user can adjust one mark and iterate; 'Reset to loaded squad' restores the team exactly as loaded, clears every mark and the results bar, and issues no network request; two identical solves leave the screen identical"
    requirement: PITCH-03
    verification:
      - kind: unit
        ref: "src/components/team/SquadTab.test.tsx — 'Reset to loaded squad restores the loaded team, clears marks and the results bar, and issues no further fetch'; 'solving twice with identical marks and control values renders an identical squad, results bar, and captain'"
        status: pass
    human_judgment: false

duration: 42min
completed: 2026-09-03
status: complete
---

# Phase 3 Plan 4: Solver UX — Lock/Exclude, Solve Controls, Results, and Reset Summary

**The loaded-team pitch becomes fully interactive: tap-to-lock/exclude, a bounded three-knob solver form, an in-place pitch update with IN badges computed against the as-loaded squad, a results bar, and a network-free Reset — closing PITCH-03, the last unimplemented interaction in Phase 3.**

## Performance

- **Duration:** 42 min
- **Started:** 2026-09-03T05:18:39Z
- **Completed:** 2026-09-03T06:00:34Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- `SquadTab.tsx` gained a `MarkRecord` state (locked/excluded, keyed by `player_code`), wired only into the loaded-team `<Pitch>` mount — the default model-squad pitch stays view-only exactly as 03-01 resolved. `lockedCodes`/`excludedCodes` are exported, tested derivations that turn the mark record into the numeric arrays `/api/solve` needs.
- `SolveControls.tsx` collects exactly three knobs (free transfers, max transfers, plan horizon), each input mirroring `SolveRequest`'s own server-side `Field(ge=…, le=…)` bound as its `min`/`max`, and renders the disabled-button/"Solving your transfers…" wait state.
- `useSolveController()` — an exported hook, not inline component state — owns the `/api/solve` request lifecycle: `buildSolveRequest()` turns marks + `SolveControls`' values into a numeric-only request body, `postSolve()` extracts the vanilla-style `{message}` error copy, and a sequence-ref guard drops any response that arrives after a newer solve has started.
- A completed solve re-renders the *same* pitch with the solve's own `squad[]`; the IN diff is computed against the squad's `player_code`s as originally loaded (via `teamQuery.data`, untouched by any solve) — never against a previous solve's result — which is also what makes Reset and repeated identical solves both trivially idempotent with no extra state.
- `SolveResultsBar.tsx` renders `pairMoves()`'s sell→buy pairs (or `Hold`), the `−{4×hits} pts in hits` clause only when `hits > 0`, bank after, `xi_xp` alone (the endpoint returns no interval fields), and the captain.
- "Reset to loaded squad" clears marks and the solve result via local state only — zero network requests, matching D-17's "the solve was only ever a local preview" framing.

## Task Commits

1. **Task 1: Lock and exclude — per-card marks that persist across solves** - `1f88316` (feat)
2. **Task 2: Solve controls and the solve request** - `993a031` (feat)
3. **Task 3: Results bar, in-place pitch update with IN badges, and Reset to loaded squad** - `4056de5` (feat)

**Follow-up fix (same-plan, before this SUMMARY):** `a8cf4f2` (fix) — see Deviations below.

**Plan metadata:** commit follows this SUMMARY.

## Files Created/Modified

- `frontend/src/components/SolveControls.tsx` — `SolveControls`, `SolveControlValues`
- `frontend/src/components/SolveResultsBar.tsx` — `SolveResultsBar`
- `frontend/src/components/team/SquadTab.tsx` — `MarkRecord`, `lockedCodes`/`excludedCodes`, `buildSolveRequest`, `useSolveController`, wired marks/diffs/onMark, Reset
- Test files: `SolveControls.test.tsx`, `SolveResultsBar.test.tsx`, extended `SquadTab.test.tsx`
- Fixture: `solve_transfers_response.json` — a genuine two-transfer, two-hit solve (McBurnie→Haaland FWD, Unmapped→Palmer MID) overlapping the loaded-team fixture

## Decisions Made

- `freeTransfersEstimate` is `null` from `SquadTab` — the only endpoint carrying that estimate is `/api/rate/{entry}`, and D-20 forbids the Squad tab firing that fetch just to prefill one input; `SolveControls` falls back to 1 (see key-decisions).
- `useSolveController` extracted as its own hook to make the ordering-safety guard directly `renderHook`-testable — see Deviations for why the UI-level double-click path proved unreliable in this test environment.
- `SolveResultsBar`'s Hold condition checks `result.buys.length`, not `pairMoves()`'s own output length — see Deviations.
- `SolveResult.kind` handled via a compiler-enforced exhaustiveness narrowing — see Deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SolveResultsBar's Hold condition used `pairMoves()`'s output length instead of `result.buys.length`**
- **Found during:** Task 3's own `SolveResultsBar.test.tsx` verification loop (the "renders Hold for a mutated fixture with an empty buys array" test), before commit
- **Issue:** `pairMoves()` buckets by the *sells* side and returns a pair (with `buyName: "?"`) for every sell even when the matching position has zero buys. Checking `pairs.length > 0` therefore never reads `Hold` as long as `sells` is non-empty, contradicting the must-have truth ("The results bar reads Hold when the solve returns no buys") and PlanTransfers.tsx's own established `week.buys.length > 0` rule for the identical situation.
- **Fix:** Changed the condition to `result.buys.length > 0`, matching `PlanTransfers.tsx`'s precedent exactly.
- **Files modified:** `frontend/src/components/SolveResultsBar.tsx`
- **Verification:** `SolveResultsBar.test.tsx`'s Hold test and the SquadTab-level "renders Hold in the results bar for a mutated zero-buys solve" test both pass.
- **Committed in:** `4056de5` (Task 3 commit — found and fixed before that commit)

**2. [Rule 3 - Blocking] Task 2's own ordering-safety acceptance criterion could not be verified through a real double-click**
- **Found during:** Task 2's own verification loop, writing the "never lets a superseded solve response overwrite a newer one" test
- **Issue:** `SolveControls`' `disabled={pending}` prop correctly disables the DOM button after the first click (required by D-15/T-03-15), but `fireEvent.click` on that now-disabled button never invokes React's `onClick` handler — verified this is a React synthetic-event behaviour (isolated repro against plain jsdom `dispatchEvent` showed jsdom itself does *not* suppress the event; only React's own handling does), and that neither `removeAttribute("disabled")` nor a direct `.disabled = false` property assignment before the next `fireEvent.click` un-suppresses it in this environment.
- **Fix:** Extracted the solve lifecycle out of inline `SquadTab` state into an exported `useSolveController(entry, marks)` hook, and tested the ordering-safety guard directly via `@testing-library/react`'s `renderHook`, calling `solveNow()` twice back-to-back — this exercises the exact same production code the button would call, without depending on any DOM click-suppression behaviour.
- **Files modified:** `frontend/src/components/team/SquadTab.tsx` (refactor, no behavior change to `SquadTab`'s own rendering — same hook is used from within the component)
- **Verification:** The new `renderHook`-based test passes; all pre-existing solve-flow tests (button disables, wait copy, error copy, request body) continued passing unchanged after the refactor.
- **Committed in:** `993a031` (Task 2 commit — the hook extraction happened before Task 2's own tests were finalized, so it is folded into that commit, not a separate fix commit)

**3. [Rule 1 - Bug] `SolveResult`'s `kind` was handled with a bare `if`, not the plan's required compiler-enforced exhaustiveness**
- **Found during:** Task 3's own acceptance-criteria re-verification pass against the plan's `<action>` text ("handle the union exhaustively so the compiler enforces it rather than a runtime assumption")
- **Issue:** `if (result.kind === "transfers") { … }` with no `else` silently no-ops on a `"squad"` response — correct today (this UI never sends `entry: null`), but not compiler-enforced: a future third `SolveResult` variant would also silently no-op rather than failing the build.
- **Fix:** Added an `else` branch narrowing `result` to `SolveSquadResult` (the only remaining union member today) via an explicit type annotation — if `SolveResult` ever grows a third `kind`, that assignment stops type-checking and the build fails at this exact line.
- **Files modified:** `frontend/src/components/team/SquadTab.tsx`
- **Verification:** `npm run typecheck` and the full test suite (357/357) both re-verified green.
- **Committed in:** `a8cf4f2` (small follow-up commit, after Task 3's own commit)

---

**Total deviations:** 3 auto-fixed (2 bugs — Rule 1, 1 blocking — Rule 3).
**Impact on plan:** All three fixes were necessary to satisfy this plan's own stated must-haves and action text. No scope creep — every fix stayed inside the files this plan already owned.

## Issues Encountered

None beyond the deviations above.

## Known Stubs

None. Every rendered value comes from the loaded team's real fetched data, the mark state the user sets, or a real (or fixture-mocked) `/api/solve` response — the `freeTransfersEstimate={null}` fallback-to-1 behavior is documented, tested, intentional null-safety, not a stub.

## Threat Flags

None. This plan's threat-model mitigations (T-03-14 numeric-only lock/exclude codes, T-03-15 in-flight button disable, T-03-16 the ordering-safety guard now `renderHook`-tested directly, T-03-17 no API key read/stored/sent anywhere in this plan's code, T-03-18 no write path to any FPL account, T-03-SC zero packages installed) were all verified by this plan's own tests. No new security-relevant surface beyond what the threat model already covers.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- PITCH-03 is complete. Phase 3's four requirements (PITCH-01 through PITCH-04, plus UI-07/UIX-01/UIX-03) are now fully implemented across all four plans.
- **Deferred to end-of-phase UAT** (per `workflow.human_verify_mode = end-of-phase`): the IN-badge placement/styling on a completed solve, the lock/exclude popover's visual treatment, and the results bar's layout at narrow widths — jsdom proves structure and text content, not visual layout, consistent with every prior plan's SUMMARY in this phase.
- **Carried forward for phase verification:** this plan's `<prohibitions>` entry ("this phase never writes to a manager's FPL account") carries `verification: unverified` in the plan's own frontmatter by design — no write-path code exists anywhere in this plan, but a dedicated read against the diff is recommended before `/gsd-verify-work`.

---
*Phase: 03-pitch-renderer-squad-views*
*Completed: 2026-09-03*

## Self-Check: PASSED

All 8 key files verified present on disk; all 4 commits (`1f88316`, `993a031`,
`4056de5`, `a8cf4f2`) verified present in `git log`.
