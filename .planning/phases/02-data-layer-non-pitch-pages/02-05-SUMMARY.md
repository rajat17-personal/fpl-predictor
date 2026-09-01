---
phase: 02-data-layer-non-pitch-pages
plan: 05
subsystem: ui
tags: [react, tanstack-query, league, scoreboard, vitest, parity, error-handling]

# Dependency graph
requires:
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-01's shared parity utilities (lib/format.ts primitives, the full web/data/*.json TypeScript contract in lib/api.ts) and Phase 1's ErrorState/EmptyState/Spinner"
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-02's PARITY-DEVIATIONS.md ledger, pre-seeded with entry 8 (scoreboard tile Display token) attributed to this plan"
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-03's current PageShell chrome — built on top of it without modification"
provides:
  - "Real, fully-ported /league route: standings table with array-position ranking and vanilla's exact GD sign rule, five fixed leader boards with an 8-entry cap and verbatim empty-board fallback"
  - "Real, fully-ported /scoreboard route: a dedicated fetchScoreboard() that distinguishes a genuinely-missing pre-season file (404 -> zero-state) from a real server/network failure (-> ErrorState), the one page in the phase more discriminating than vanilla"
  - "Widened ScoreboardSummary.mae_fpl/spearman_fpl to number | null in lib/api.ts, matching ScoreboardEntry's existing nullable typing — available to any later plan reading scoreboard data"
  - "Three hand-authored parity fixtures: standings.json, leaders.json, and a scoreboard.json synthesised from predict/scoreboard.py's schema (the only way the populated scoreboard path is exercisable before the first real gameweek)"
affects: [02-06, 07]

# Actuals (#2632)
actuals:
  tokens: 8078
  tasks: 2
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scoreboard is the one route in the phase with a dedicated query function instead of the shared fetchJson — fetchScoreboard() branches on res.status === 404 to return null (-> zero-state) versus throwing for every other non-ok status (-> ErrorState), with retry disabled so a 500 surfaces promptly (D-08, RESEARCH.md Pitfall 2)"
    - "League combines two independent TanStack Query results (standings, leaders) into one pending/error/empty branch set rather than rendering them as separately-failable regions, since both are required for the page to mean anything"
    - "Scoreboard's zero-state and populated-state are structurally exclusive branches (entries.length === 0) — the zero-state renders no history table element at all, not an empty one, matching vanilla's hide-the-whole-tablewrap behavior"

key-files:
  created:
    - frontend/src/routes/League.test.tsx
    - frontend/src/routes/Scoreboard.test.tsx
    - frontend/src/test/fixtures/standings.json
    - frontend/src/test/fixtures/leaders.json
    - frontend/src/test/fixtures/scoreboard.json
  modified:
    - frontend/src/routes/League.tsx
    - frontend/src/routes/Scoreboard.tsx
    - frontend/src/lib/api.ts

key-decisions:
  - "Widened ScoreboardSummary.mae_fpl/spearman_fpl from optional-only (number | undefined) to number | null in lib/api.ts — the plan's own fixture instructions required a null summary.mae_fpl to test the tile fallback, and the stricter tsc -b build-mode check (not npm run typecheck, which trivially passes on the root project's empty files:[]) rejected the mismatch. Matches ScoreboardEntry's existing per-row nullable typing, so the two interfaces are now consistent."
  - "Dropped the plan-authored Vitest assertion that read Scoreboard.tsx's source text via node:fs to check for the explanatory comment — frontend/tsconfig.app.json's src include has no 'node' types (only 'vite/client'), so node:fs/node:path/process fail tsc -b. Verified the same fact — the comment explaining why fetchJson is bypassed is present — via a direct grep instead, documented here rather than silently dropping the acceptance criterion."

patterns-established: []

requirements-completed: [UI-05]

coverage:
  - id: D1
    description: "/league renders the standings table from /data/standings.json with columns #, Team, P, W, D, L, GF, GA, GD, Pts; the # column is the array position (index + 1), never a data field."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/League.test.tsx#renders rank cells 1, 2, 3, 4 for a four-row fixture with no rank field (R32)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Goal difference renders with a leading + only when strictly positive; zero and negative render bare."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/League.test.tsx#renders the goal-difference cells +7, +4, 0 and -3 for source values 7, 4, 0 and -3 (R33)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Exactly five leader boards render in the fixed order points/goals/assists/clean_sheets/cards with the exact documented headings; each board caps at 8 entries; an empty or entirely-absent board renders the verbatim 'Nothing yet this season' line without throwing."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/League.test.tsx (five headings test, 8-entry cap test, empty-board test, missing-key test)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Neither the standings table nor the leader boards are sortable — no interactive column headers; zero standings rows render the shared EmptyState; a failed standings/leaders fetch renders ErrorState naming the league data."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/League.test.tsx (no-buttons test, EmptyState test, ErrorState test)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A 404 on /data/scoreboard.json renders the verbatim pre-season zero-state (three backtest tiles + paragraph, no history table), never an error; a 500 or network failure renders ErrorState with Retry — the phase's one deliberately more-discriminating-than-vanilla page (D-08)."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Scoreboard.test.tsx (404 test, 500 test, network-rejection test, empty-entries-200 test)"
        status: pass
    human_judgment: false
  - id: D6
    description: "A populated scoreboard renders four tiles (Gameweeks scored, MAE, Rank correlation, Captain average) and every entry the export emits as a history row in export order, with independent per-cell/per-tile en-dash fallbacks for null mae_fpl/spearman_fpl."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Scoreboard.test.tsx (gw-order test, per-row null fallback tests, tile null fallback test, four-tiles test)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full frontend Vitest suite, typecheck, and the production build-purity gate all pass with this plan's changes in place."
    verification:
      - kind: other
        ref: "npm --prefix frontend run test (149/149 passed)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck (exit 0)"
        status: pass
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh (BUILD PURITY OK)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Manual spot check with the dev proxy running and web/data/scoreboard.json genuinely absent: visiting /scoreboard shows the pre-season zero-state rather than an error."
    verification: []
    human_judgment: true
    rationale: "The plan's <verification> step 4 is an explicit non-gating manual spot check against the live dev server/proxy — Vitest's mocked-fetch tests prove the 404-vs-error branching logic is correct, but only a human visiting the real running app can confirm the end-to-end proxy behavior against a truly absent file."

duration: 25min
completed: 2026-09-01
status: complete
---

# Phase 2 Plan 5: League Table & Accuracy Scoreboard Parity Summary

**Ports `/league` (array-position ranking, vanilla's GD sign rule, five capped leader boards) and `/scoreboard` (a dedicated 404-vs-server-failure fetch function — this phase's one deliberate behavioral upgrade over vanilla's blanket catch), plus a scoreboard fixture synthesised from `predict/scoreboard.py` since the live file does not exist pre-season.**

## Performance

- **Duration:** 25 min (approx.)
- **Started:** 2026-09-01T14:31:00Z (approx.)
- **Completed:** 2026-09-01T14:56:00Z (approx.)
- **Tasks:** 2 (both TDD)
- **Files modified:** 8 (5 created, 3 modified)

## Accomplishments
- Replaced the `/league` placeholder with a real route: standings table with `index + 1` rank numbering (R32), vanilla's exact `gd > 0 ? "+" + gd : gd` sign rule (R33), and five fixed leader boards (`points`/`goals`/`assists`/`clean_sheets`/`cards`) each capped at 8 entries with the verbatim `Nothing yet this season` fallback for an empty or entirely-absent board key (R34)
- Replaced the `/scoreboard` placeholder with a real route built around a dedicated `fetchScoreboard()` that returns `null` on a 404 (routing to the verbatim pre-season zero-state) and throws for every other non-ok status (routing to `ErrorState` with Retry) — the phase's single deliberate improvement over vanilla's uniform `try{}catch{}` swallow
- Rendered the populated scoreboard's four tiles and full history table in export order, with independent per-cell and per-tile en-dash fallbacks for null `mae_fpl`/`spearman_fpl` (R37, R38)
- Authored three hand-checked parity fixtures — `standings.json` (positive/zero/negative GD), `leaders.json` (a 10-entry board, an empty board, and an entirely omitted board key), and `scoreboard.json` synthesised directly from `predict/scoreboard.py`'s `score_gw()`/`running_summary()` output shape

## Task Commits

Each task was committed atomically (both `tdd="true"`, full RED->GREEN cycles):

1. **Task 1 RED: failing tests for league table and leader boards** - `ff33d51` (test)
1. **Task 1 GREEN: implement league table and season leader boards** - `8388ef5` (feat)
2. **Task 2 RED: failing tests for accuracy scoreboard 404/500/network branching** - `fb95c2f` (test)
2. **Task 2 GREEN: implement accuracy scoreboard with 404-vs-error distinction** - `c0143e8` (feat)

_No REFACTOR commits — both TDD implementations stayed minimal and clean through GREEN._

## Files Created/Modified
- `frontend/src/routes/League.tsx` - Real, fully-ported league standings + leader boards route
- `frontend/src/routes/League.test.tsx` - Full behavioral test suite (10 tests)
- `frontend/src/test/fixtures/standings.json` / `leaders.json` - Hand-authored parity fixtures
- `frontend/src/routes/Scoreboard.tsx` - Real, fully-ported scoreboard route with `fetchScoreboard()`
- `frontend/src/routes/Scoreboard.test.tsx` - Full behavioral test suite (10 tests)
- `frontend/src/test/fixtures/scoreboard.json` - Synthesised populated-scoreboard fixture
- `frontend/src/lib/api.ts` - Widened `ScoreboardSummary.mae_fpl`/`spearman_fpl` to `number | null`

## Decisions Made
- Widened `ScoreboardSummary.mae_fpl`/`spearman_fpl` from optional-only to `number | null` in `lib/api.ts` — the plan's fixture instructions required a null `summary.mae_fpl` to test the tile fallback, and the stricter `tsc -b` build-mode check (not `npm run typecheck`, which trivially passes on the root project's empty `files: []`) rejected the type mismatch. Now matches `ScoreboardEntry`'s existing per-row nullable typing.
- Combined the standings and leaders TanStack Query results into one shared pending/error/empty branch set for `/league`, since both are required together for the page to render anything meaningful — neither table is independently degradable the way the xP table's captains sub-table is.
- Dropped the plan-authored Vitest assertion that read `Scoreboard.tsx`'s source via `node:fs` to check for the bypass-explanation comment (`frontend/tsconfig.app.json`'s `src` include has no `"node"` types, only `"vite/client"`, so `node:fs`/`node:path`/`process` fail `tsc -b`). Verified the same fact directly via `grep -n "fetchJson" frontend/src/routes/Scoreboard.tsx` instead, confirming the comment is present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `ScoreboardSummary.mae_fpl`/`spearman_fpl` were optional-only, breaking the stricter build-mode typecheck**
- **Found during:** Task 2, running `bash scripts/verify_frontend_build.sh`
- **Issue:** `npm run typecheck` (`tsc --noEmit` against the root project, which has `files: []` and only project references — a no-op check) passed trivially, but the build's `tsc -b` step failed: the plan-required `scoreboard.json` fixture's `summary.mae_fpl: null` didn't satisfy `ScoreboardSummary`'s non-nullable-optional `mae_fpl?: number` field.
- **Fix:** Widened both fields to `mae_fpl?: number | null; spearman_fpl?: number | null;` in `frontend/src/lib/api.ts`, matching `ScoreboardEntry`'s existing nullable typing for the same field names.
- **Files modified:** frontend/src/lib/api.ts
- **Verification:** `npm --prefix frontend run typecheck` and `bash scripts/verify_frontend_build.sh` (`BUILD PURITY OK`) both pass.
- **Committed in:** c0143e8 (Task 2 GREEN commit)

**2. [Rule 3 - Blocking] `node:fs`-based source-comment test broke `tsc -b` (no `"node"` types in `tsconfig.app.json`)**
- **Found during:** Task 2, running `bash scripts/verify_frontend_build.sh`
- **Issue:** The plan's acceptance criterion "Scoreboard.tsx contains a comment explaining why the shared fetch helper is bypassed" was initially encoded as a Vitest test reading the source file via `node:fs`/`node:path`/`process.cwd()`. `frontend/tsconfig.app.json`'s `types` array is `["vite/client"]` only (no Node types), and its `include` covers all of `src/` including test files, so the build-mode `tsc -b` step failed on three `Cannot find name` errors.
- **Fix:** Removed the `node:fs`-based test; verified the same underlying fact (the comment exists) via `grep -n "fetchJson" frontend/src/routes/Scoreboard.tsx`, which found it at lines 9 and 14. The acceptance criterion is satisfied by inspection, not a repo-committed automated test, since no test-time file-read primitive is currently available under this project's strict build-mode typecheck.
- **Files modified:** frontend/src/routes/Scoreboard.test.tsx
- **Verification:** `npm --prefix frontend run typecheck && bash scripts/verify_frontend_build.sh` (`BUILD PURITY OK`); manual `grep` confirms the comment.
- **Committed in:** fb95c2f (Task 2 RED commit, before the fix landed) / c0143e8 (Task 2 GREEN commit, final state)

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking type/tooling fixes)
**Impact on plan:** Both were necessary consequences of implementing the plan's fixture and acceptance-criteria instructions exactly as written against this project's existing strict build-mode gate (the same gate 02-04's SUMMARY documents catching a similar type-shape mismatch). No scope creep, no architectural change.

## Issues Encountered
None beyond the deviations documented above.

## Threat Model Notes

Per this plan's `<threat_model>`: T-02-10 (Spoofing, mitigate) — confirmed `fetchScoreboard` branches explicitly on `res.status === 404` (returns `null`) and throws for every other non-ok status; the dedicated 500 test (`Scoreboard.test.tsx`) asserts the Retry control appears and the backtest tile text is absent, proving a server failure can never be presented as "no gameweeks scored yet." T-02-11 (Information Disclosure, mitigate) — confirmed `ErrorState` on both `/league` and `/scoreboard` failure paths only ever receives a `resource` string; the thrown `Error`'s message (embedding the request path and status) is passed only to `console.error`, never rendered into the DOM.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `PARITY-DEVIATIONS.md` entry 8 (scoreboard tile Display-token weight) is now implemented exactly as pre-seeded — confirmed via the `Tile` component's `font-display text-display font-bold` classes.
- `lib/api.ts`'s `ScoreboardSummary` interface now accurately models the nullable `mae_fpl`/`spearman_fpl` shape, consistent with `ScoreboardEntry` — any later plan reading scoreboard data inherits the corrected typing.
- No blockers for plan 02-06 (Differentials + Methodology, the phase's remaining wave-2 plan).

## Self-Check: PASSED

All 8 created/modified files verified present on disk; all 4 task commit hashes (`ff33d51`, `8388ef5`, `fb95c2f`, `c0143e8`) verified present in `git log`. Full frontend suite (149/149), typecheck, and the production build-purity gate (`BUILD PURITY OK`) all re-confirmed green immediately before writing this summary.

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-01*
