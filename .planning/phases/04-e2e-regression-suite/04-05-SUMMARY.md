---
phase: 04-e2e-regression-suite
plan: 05
subsystem: testing
tags: [e2e, playwright, chromium, ilp-solver, transfers, plan-flow, real-api]

requires:
  - phase: 04-e2e-regression-suite (plan 01)
    provides: "e2e/fixtures/v1/normal/**: the frozen GW3 capture (entry 6980093's picks/summary, the per-gameweek pools) every solve in this plan runs the real ILP over"
  - phase: 04-e2e-regression-suite (plan 02)
    provides: "e2e/playwright.config.ts's webServer lifecycle and e2e/helpers/page.ts's gotoReady/ENTRY/GW/PICKS_EVENT constants, reused throughout both new spec files"

provides:
  - "e2e/specs/team-solver.spec.ts: full E2E-02 coverage of the Squad tab — default view-only model squad, entry-id load flow, ?entry= deep link, client-side guard, the 404 failure path + Change-team recovery, ephemeral lock/exclude marks, real-solve legality invariants, results-bar mirroring, IN-badge idempotency, locks/excludes, control bounds, Reset, the solve-failure error copy, and one pinned golden solve (15 tests)"
  - "e2e/specs/team-plan.spec.ts: a real two-gameweek /api/plan solve exercised in the browser — verbatim wait copy, per-week Moves/Projected-XI tiles, open/collapsed squad sections, 15-card week-one pitch, and the closing plan-flow paragraph (1 test)"
  - "frontend/src/components/team/SquadTab.tsx: fetchTeam() — a Rule 1 fix so a failed team load surfaces the server's own `detail` text instead of a bare status code"
affects: [e2e-suite-wave-3, ci-02, cutover]

actuals:
  tokens: 7540
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "window.fetch override (not page.route()) to drive an otherwise-unreachable real server error path: buildSolveRequest only ever emits numeric player_code locks/excludes (D-15's client invariant), so the server's string-name _resolve() 422 branch has no UI trigger. Wrapping window.fetch inside page.evaluate() to inject one bogus string lock into the one outgoing /api/solve request's own JSON body — while still letting the real fetch complete over the wire — proves the real error path without a Playwright route mock and without ever making the client capable of sending a name."
    - "Structural (not literal) solve assertions read every expected value off the LIVE /api/solve response captured via page.waitForResponse(), not off fixture JSON at test time — mirrors D-15's already-established distinction between deriving-from-input-fixture (forbidden, re-implements formatting) and deriving-from-live-response (required for a test that must hold under 'whichever optimum CBC lands on')."
    - "CSS :has()/:text() Playwright locator extensions (`div:has(> h2:text(\"...\"))`) scope assertions to one specific per-week block without adding a new data-testid to production code, when the heading text itself is already a unique per-block identifier."

key-files:
  created:
    - e2e/specs/team-solver.spec.ts
    - e2e/specs/team-plan.spec.ts
  modified:
    - frontend/src/components/team/SquadTab.tsx

key-decisions:
  - "[Rule 1 — auto-fixed bug, no checkpoint needed] SquadTab.tsx's teamQuery used lib/api.ts's fetchApi, which discards a non-ok response's body (`Error(`${path}: ${res.status}`)`), unlike this same file's own postSolve / RateTab.tsx's fetchRate / PlanTransfers.tsx's postPlan — all three of which already carry a custom detail-extracting fetch specifically BECAUSE fetchApi cannot reproduce a detail-bearing error copy, and postSolve's own header comment documents exactly why. teamQuery was the one fetch in this file left on the discarding path. Added fetchTeam() mirroring the established sibling pattern; the plan's own failure-path task (\"assert the exact ... copy including the API's own detail text\") would have been unsatisfiable against the pre-fix code, which rendered `Couldn't load that team: /api/team/9999999: 404.` instead of the detail-bearing copy."
  - "[Flagged tension, resolved without a checkpoint] The plan's failure-copy task for /api/solve (\"drive it by submitting a lock naming a player absent from the frozen pool\") cannot be reached through any real UI interaction: frontend/src/lib/api.ts's SolveRequest types locks/excludes as `number[]` only, and buildSolveRequest never emits a string — this is a deliberate, already-shipped invariant (D-15's \"client sends numeric player_code locks/excludes, never free-text names\", PROJECT.md's own Key Decisions table). `_resolve()`'s `isinstance(it, int)` branch never validates a numeric code against the pool either, so no numeric value can trigger the 422 there. Resolved by wrapping `window.fetch` inside the page to inject one bogus string lock into the one outgoing `/api/solve` request's own body before it goes over the wire — a real round trip to the real server (not a Playwright route mock), exercising the genuine `_resolve()` player-not-found path the product's error-rendering code was built to display."
  - "Lock/exclude test players chosen for real effect, not arbitrary picks: Mateta (injured, xp=0, sold by the default/golden solve) is locked to prove a lock genuinely forces a keep; Haaland (the golden solve's own captain) is excluded to force a genuinely different optimum, not a no-op."
  - "The plan flow's real horizon-2 solve happens to buy on both weeks in this frozen fixture — the Moves tile's Hold branch is implemented and asserted conditionally but not actually exercised by this specific real solve. Documented rather than forced via mutating the immutable v1 fixture (D-08) or a second, out-of-scope plan request."

patterns-established:
  - "A component's own header comment documenting why a sibling function needs a custom detail-extracting fetch (rather than lib/api.ts's discarding fetchApi) is a signal to check every other fetch in the same file for the identical gap — SquadTab.tsx already explained the fix it needed for its own team-load path, one function away."

requirements-completed: [E2E-02]

coverage:
  - id: D1
    description: "Squad tab: default view-only model squad, entry-id load flow, ?entry= deep link, client-side guard (zero requests on empty/non-numeric), the 404 failure path + Change-team recovery, and ephemeral lock/exclude marks"
    requirement: "E2E-02"
    verification:
      - kind: e2e
        ref: "E2E_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python E2E_VARIANTS=0 npm --prefix e2e run test -- specs/team-solver.spec.ts --project=chromium (6/6 of this coverage group; 15/15 file-wide)"
        status: pass
      - kind: other
        ref: "node coverage-grep: LOAD FLOW COVERAGE OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real ILP solve: legality invariants (15/11/1-captain/2-5-5-3/budget), in-place pitch update, results-bar mirroring (moves/hits-omitted-at-zero/bank/captain), IN-badge idempotency, locks present/excludes absent, control bounds, Reset with zero requests, and the solve-failure detail-text copy"
    requirement: "E2E-02"
    verification:
      - kind: e2e
        ref: "E2E_PYTHON=... npm --prefix e2e run test -- specs/team-solver.spec.ts --project=chromium (7/7 of this coverage group)"
        status: pass
      - kind: other
        ref: "node coverage-grep: SOLVE COVERAGE OK (no page.route() anywhere in the file)"
        status: pass
    human_judgment: false
  - id: D3
    description: "One pinned golden solve (D-11's exact XI/captain/moves/bank/XI-xP re-pin point) and a real two-gameweek /api/plan flow with verbatim wait copy and per-week rendering"
    requirement: "E2E-02"
    verification:
      - kind: e2e
        ref: "E2E_PYTHON=... npm --prefix e2e run test -- specs/team-solver.spec.ts specs/team-plan.spec.ts --project=chromium (15 passed)"
        status: pass
      - kind: other
        ref: "node coverage-grep: PLAN TIMEOUT SCOPED (own test.setTimeout, global config timeout unchanged at 30_000)"
        status: pass
      - kind: e2e
        ref: "E2E_PYTHON=... npm --prefix e2e run test -- --project=chromium (full non-variant suite, 33 passed: 18 prior + 15 new)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-04
status: complete
---

# Phase 4 Plan 05: Team/Pitch + Solver Flow E2E Coverage Summary

**Covered the Squad tab's full load→mark→solve→reset cycle and the two-gameweek plan flow end to end in a real browser, against a real PuLP/CBC ILP run over the frozen GW3 pool — including one pinned golden solve and a Rule 1 fix to SquadTab.tsx's team-load error copy that the failure-path test itself caught.**

## Performance
- **Duration:** ~45min active work
- **Started:** 2026-09-03 (immediately following 04-04)
- **Completed:** 2026-09-04
- **Tasks:** 3 (all `type="auto"`, no checkpoints)
- **Files modified:** 3 (2 new spec files, 1 production fix)

## Accomplishments

- **Task 1 — Load flow, guard, failure path, marks.** Before writing any assertions, derived every literal from the committed fixture set: scripted the entry 6980093 picks joined to `bootstrap-static.json`/`xp_table.json` to reproduce `selectLoadedSquad`'s DEF/MID/FWD search (4-4-2, matching `smoke.spec.ts`'s own derivation) and confirmed the captain (Haaland, highest `xp_capt`=6.82 among starters). `e2e/specs/team-solver.spec.ts`'s first six tests cover: the default `/team` view (model squad, 3-5-2, 15 cards, zero action-menu triggers, entry input never auto-submitted); the entry-id load flow (URL gains `?entry=`, heading/formation/15-card pitch match); the `?entry=` deep link (D-11, no interaction needed); the client-side guard (empty AND `"1.5"` — a value valid for `<input type="number">` but rejected by the `/^\d+$/` integer regex, distinct from the browser's own sanitization of truly non-numeric text like `"abc"` to `""`); the 404 failure path (`entry 9999999: no picks for GW2 ...`) plus Change-team recovery; and ephemeral lock/exclude marks (menu shows name/club/ownership, badge appears, both gone after a reload).
- **Rule 1 fix discovered by the failure-path test itself:** `SquadTab.tsx`'s `teamQuery` used `lib/api.ts`'s `fetchApi`, which discards a non-ok response's body — the rendered error would have been `Couldn't load that team: /api/team/9999999: 404.`, not the detail-bearing copy the plan's own task text assumed. The same file's `postSolve` (two lines below `teamQuery` in the original file) already carries a custom fetch specifically documented as working around this exact `fetchApi` limitation, matching `RateTab.tsx`'s `fetchRate` and `PlanTransfers.tsx`'s `postPlan`. Added `fetchTeam()` mirroring that established sibling pattern and rewired `teamQuery` to use it. Verified: `npm --prefix frontend run build` (tsc -b build-mode check) and `npm --prefix frontend run test` (363 passed, no regression) both green after the change; no existing unit test asserted the old status-code-only message.
- **Task 2 — Real-solve legality, results bar, IN badges, locks/excludes, bounds, Reset, failure copy.** Every solve in this describe block is a genuine `POST /api/solve`, awaited via `page.waitForResponse`, with every expected value read off the *live response* rather than re-derived from fixture JSON (the same "never re-implement the formatting/logic under test" discipline `xp-table.spec.ts` established, applied here to "never re-implement the ILP's own optimum choice"). Covered: the five structural invariants (15/11-starters/1-captain/2-5-5-3/budget) holding against whatever optimum CBC returns; the pitch showing the exact same 15 names as the response, updated in place; the results bar (paired move lines with same-position sell/buy matching, hit line entirely absent at zero hits, exact bank/captain strings); the IN-badge diff proven against the as-loaded squad and shown idempotent across an identical repeat solve; two locked players (one, Mateta, chosen because the unmarked default solve *sells* it — proving the lock has real effect, not a no-op) present and one excluded player (Haaland, the default solve's own captain, forcing a genuinely different squad) absent, with both surviving lock badges still visible post-solve; the three solve-control bounds (0-5, 0-15, and the exact five horizon options) mirroring the server's declared constraints; Reset restoring the as-loaded fifteen with a `page.on("request")` listener proving zero network calls; and the solve-failure error copy.
  - **Flagged tension resolved without a checkpoint:** the plan's failure-copy scenario ("submit a lock naming a player absent from the frozen pool") cannot be reached through any real UI action — `SolveRequest.locks`/`excludes` are typed `number[]` only in `lib/api.ts`, and `buildSolveRequest` never emits a string; this is a deliberate, already-shipped project decision (D-15 / PROJECT.md's "Client sends numeric player_code locks/excludes, never free-text names"), and `_resolve()`'s `isinstance(it, int)` branch never validates a numeric code against the pool either, so no numeric value can trigger the 422. Resolved by wrapping `window.fetch` *inside the page* (via `page.evaluate`) to inject one extra bogus string into the one outgoing `/api/solve` request's own JSON body immediately before it goes over the wire — the request still makes a genuine round trip to the real server and exercises the real `_resolve()` player-not-found path (confirmed once by curl against the fixture-mode server: `422 {"detail":"player not found in this gameweek: 'ZzzzzNotARealPlayerXyz'"}`), without a Playwright route mock and without giving the client itself the ability to send a name.
- **Task 3 — Pinned golden + real plan flow.** Hand-derived the golden by running the exact default-values request (`entry=6980093, free_transfers=1, horizon=1`, no marks) against the committed fixture set via curl against a locally-booted fixture-mode uvicorn: starting XI in rendered row order (Roefs; Shaw, Calafiori, O'Reilly; B.Fernandes, Szoboszlai, Tzolis, Mbeumo; Calvert-Lewin, Wissa, Haaland), bench (Hughes, Diop, Davis, Kinsky), one move (Mateta → Wissa, FWD), zero hits, bank £0.3m, XI xP 27.79, captain Haaland. Pinned as the suite's single documented re-pin point (a comment states plainly that only this test needs re-deriving if a CBC version bump ever flips the tie). `e2e/specs/team-plan.spec.ts` (new file) drives a real horizon-2 `/api/plan` solve from the Rate tab: verbatim pending copy including the multi-gameweek wait clause, both week headings ("GW3 — do this now" / "GW4 — planned"), per-week Moves/Projected-XI tiles asserted dynamically against the live response (not hardcoded — the Moves tile's Hold branch happens not to be exercised by this real fixture's actual solve, documented in-file and here rather than forced), the first week's squad section open and 15 cards on its pitch, the second week's collapsed, and the closing "Week one is the decision to act on" paragraph. Raises its own `test.setTimeout(90_000)`, leaving `playwright.config.ts`'s global 30s timeout untouched.
- Re-ran the full non-variant suite after each task (18 prior + 15 new = 33 passed, no cross-contamination across parallel workers), `npm --prefix frontend run test` (363 passed) and the full pytest suite (76 passed) — none regressed.

## Task Commits
1. **Task 1: Load a squad onto the pitch, mark players, and cover the failure paths** — `6dc3e3d` (feat) — `e2e/specs/team-solver.spec.ts`, `frontend/src/components/team/SquadTab.tsx`
2. **Task 2: Real solve — legality invariants, in-place pitch update, results bar and reset** — `a9a9f91` (test) — `e2e/specs/team-solver.spec.ts`
3. **Task 3: The pinned golden solve and the real two-gameweek plan flow** — `f658d05` (test) — `e2e/specs/team-solver.spec.ts`, `e2e/specs/team-plan.spec.ts`

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `e2e/specs/team-solver.spec.ts` (new, 465 lines, 15 tests across 4 `describe` blocks) — the complete E2E-02 Squad-tab spec.
- `e2e/specs/team-plan.spec.ts` (new, 142 lines, 1 test) — the real two-gameweek plan flow.
- `frontend/src/components/team/SquadTab.tsx` — added `fetchTeam()`, rewired `teamQuery` to use it instead of `fetchApi`; removed the now-unused `fetchApi` import.

## Decisions Made
See `key-decisions` in frontmatter — the Rule 1 `fetchTeam()` fix and the `window.fetch`-override resolution of the plan/codebase tension over the player-not-found failure path are the two load-bearing decisions for this plan.

## Deviations from Plan

**1. [Rule 1 - Bug] `SquadTab.tsx`'s team-load error discarded the API's own detail text**
- **Found during:** Task 1, while deriving the exact failure-path copy from the running fixture-mode server.
- **Issue:** `teamQuery` used `lib/api.ts`'s `fetchApi`, which throws `Error(`${path}: ${res.status}`)` on a non-ok response — discarding the response body entirely. The plan's own task text ("assert the exact ... copy including the API's own detail text") assumes the detail text is rendered; it was not. The same file's `postSolve` (and `RateTab.tsx`'s `fetchRate`, `PlanTransfers.tsx`'s `postPlan`) already document this exact `fetchApi` limitation and work around it — `teamQuery` was the one fetch in the file left unfixed.
- **Fix:** Added `fetchTeam(entry)` mirroring the established custom-fetch-with-detail-extraction pattern; rewired `teamQuery`'s `queryFn` to call it; removed the now-unused `fetchApi` import.
- **Files modified:** `frontend/src/components/team/SquadTab.tsx`
- **Verification:** `npm --prefix frontend run build` (tsc -b) exits 0; `npm --prefix frontend run test` — 363 passed, no regression (no existing unit test asserted the old status-code-only message); the new E2E failure-path test asserts the corrected copy end-to-end against the real fixture-mode server.
- **Commit:** `6dc3e3d`

**2. [Flagged tension between the plan and an already-shipped project decision — resolved without a checkpoint, no production-code change] The prescribed failure-copy trigger for `/api/solve` cannot be reached through the real UI**
- **Found during:** Task 2, while implementing the solve-failure-copy test exactly as the plan's `<action>` text describes ("drive it by submitting a lock naming a player absent from the frozen pool").
- **Issue:** `SolveRequest.locks`/`excludes` are typed `number[]` only (`lib/api.ts`), and `buildSolveRequest` never constructs a string lock — this is a deliberate, already-shipped invariant (D-15 / PROJECT.md's Key Decisions: "Client sends numeric player_code locks/excludes, never free-text names"). Additionally, `api/main.py`'s `_resolve()` never validates an `int` lock against the pool (`if isinstance(it, int): codes.append(it); continue`), so even an out-of-pool numeric code silently no-ops rather than 422ing. No genuine UI interaction can reach the server's player-not-found error path.
- **Fix:** Kept the client invariant untouched (no production code change, no weakening of D-15). Instead, wrapped `window.fetch` inside the page (via `page.evaluate`, not `page.route()`) to inject one extra bogus string into the *outgoing* `/api/solve` request's own JSON body immediately before the real fetch call proceeds — the request still makes a genuine round trip to the real fixture-mode server and exercises the real `_resolve()` 422 path. Confirmed via a standalone curl against the fixture-mode server first (`422 {"detail":"player not found in this gameweek: 'ZzzzzNotARealPlayerXyz'"}`) before wiring the in-page equivalent.
- **Files modified:** none in production code; documented in `e2e/specs/team-solver.spec.ts`'s own test comment.
- **Verification:** the test passes, asserting the exact `Couldn't solve: player not found in this gameweek: 'ZzzzzNotARealPlayerXyz'. Check your inputs and try again.` copy.
- **Commit:** `a9a9f91`

**Total deviations:** 2 (1 Rule 1 production fix, 1 flagged plan/codebase tension resolved via a documented, non-route-mocking test technique). **Impact:** the production fix makes SquadTab.tsx's error handling consistent across all four of its fetches (team/solve/rate/plan); no behavior change to any already-tested path. The failure-copy resolution keeps D-15's numeric-only client invariant fully intact while still proving the server's real error-rendering path end to end.

## Issues Encountered

- **Fixture-data note (not a gap, just recorded):** the real horizon-2 `/api/plan` solve against this frozen fixture happens to buy on both weeks — the Moves tile's "Hold" branch (implemented in `PlanTransfers.tsx` and asserted conditionally in `team-plan.spec.ts`) is not actually exercised by this specific real solve. Not forced via mutating the immutable v1 fixture (D-08) or an out-of-scope second plan request at a different horizon (D-12 bounds this plan to horizon 2).

## User Setup Required

None. Local runs need `E2E_PYTHON` set to the conda interpreter, exactly as established in 04-02 — no new environment requirement introduced by this plan.

## Next Phase Readiness

E2E-02 (team/pitch + solver flow regression test) is now closed. Remaining phase scope per `04-CONTEXT.md`: E2E-04 (rate-my-team end to end) and E2E-05 (fixtures/prices, already covered by 04-03's `fixtures-prices.spec.ts` — confirm against `04-CONTEXT.md`/`04-06-PLAN.md` for the final plan in this phase). The `fetchTeam()` pattern (custom fetch + detail extraction) is now consistent across all four of SquadTab.tsx's/RateTab.tsx's/PlanTransfers.tsx's fetches — any future fifth fetch added to this file should follow the same pattern from the start. No blockers.

## Self-Check: PASSED

- `e2e/specs/team-solver.spec.ts` — FOUND on disk (465 lines)
- `e2e/specs/team-plan.spec.ts` — FOUND on disk (142 lines)
- `frontend/src/components/team/SquadTab.tsx` — FOUND, contains `fetchTeam` and no `fetchApi` import
- `git log --oneline --all --grep="04-05"` — commits `6dc3e3d`, `a9a9f91`, `f658d05` all present in `git log --oneline -6` with `(04-05)` scope
- Re-ran all three tasks' acceptance criteria: all pass (15/15 `team-solver.spec.ts`; 1/1 `team-plan.spec.ts`; `LOAD FLOW COVERAGE OK`; `SOLVE COVERAGE OK`; `PLAN TIMEOUT SCOPED`; `(cd e2e && npx tsc --noEmit -p tsconfig.json)` exits 0)
- Re-ran plan-level `<verification>`: `npm --prefix e2e run test -- --project=chromium` (full non-variant suite) green — 33 passed; no spec in this plan calls `page.route(`; `playwright.config.ts`'s global `timeout: 30_000` unchanged; `npm --prefix frontend run test` unaffected (363 passed); full pytest suite unaffected (76 passed)
