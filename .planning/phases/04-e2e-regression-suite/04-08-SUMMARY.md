---
phase: 04-e2e-regression-suite
plan: 08
subsystem: testing
tags: [pitch-renderer, ghost-card, react, playwright, vitest, regression-fix]

# Dependency graph
requires:
  - phase: 04-e2e-regression-suite (plan 07)
    provides: the restored FPL_FIXTURE_DIR teardown seam in api/main.py that this plan's Playwright gate boots through
  - phase: 03-pitch-renderer-squad-views
    provides: Pitch.tsx's rowGhost mechanism and RateDiff.tsx's resolveRateOverlay (the pre-existing code this plan fixes)
provides:
  - "PitchGhost['row'] widened to include 'BENCH', wired into the Bench PitchRow via the existing rowGhost helper"
  - "resolveRateOverlay derives the ghost's row from the matched sell row itself (bench sell -> BENCH, starter sell -> its own row, unresolved sell -> the buy's position fallback)"
  - "e2e/specs/rate-my-team.spec.ts asserting the corrected same-row-plus-adjacency ghost behavior against the unmodified v1 capture"
  - "WINDOWS.md id=2 closed (fixed), open_count 1"
affects: ["/gsd-ship's windows_enforce gate (no longer blocked on this phase's own defect)", any future phase touching Pitch.tsx/RateDiff.tsx's ghost mechanism]

# Actuals (#2632)
actuals:
  tokens: 21000
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ordered fallback rule for deriving a rendering slot from server data: most-specific match first (bench sell), then a same-shape match (starter sell), then a documented fallback (buy position), then no-op -- mirrors this codebase's existing zero/multiple-match degrade pattern in resolveRateOverlay."

key-files:
  created: []
  modified:
    - frontend/src/components/pitch/Pitch.tsx
    - frontend/src/components/RateDiff.tsx
    - frontend/src/components/pitch/Pitch.test.tsx
    - frontend/src/components/RateDiff.test.tsx
    - e2e/specs/rate-my-team.spec.ts
    - .planning/WINDOWS.md
    - .planning/phases/04-e2e-regression-suite/deferred-items.md

key-decisions:
  - "Kept 'BENCH' out of VALID_PITCH_ROWS (which validates API-supplied position strings) and reachable only through the boolean starting field on a resolved sell row -- an attacker-controlled position string can never produce a BENCH ghost."
  - "Held the matched sell row itself (not just its player_code) as a local in resolveRateOverlay so the ordered row-derivation rule can read both starting and position off the same object the existing outCode/diffs logic already resolved."
  - "Re-pinned the visual-diff spec's Forwards/Bench row counts from a real Playwright run (Forwards 2, Bench 5) rather than trusting the plan's own derived arithmetic outright, per D-15 -- the live run confirmed the derived numbers were correct."

patterns-established:
  - "Adjacency proof for 'same row' claims: walk a row group's direct-child cells, find both markers' indices, assert ghostIdx === outIdx + 1 -- not just co-membership in the same role=group container. Mirrors Pitch.test.tsx's own cell-index check and is now also live in the Playwright spec."

requirements-completed: [E2E-04]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "The ghost card and the outgoing player's dimmed card render inside the same role=\"group\" container (Bench), adjacent, for the real v1 capture's own benched best_move (sell Mateta, buy Wissa)"
    requirement: "E2E-04"
    verification:
      - kind: e2e
        ref: "e2e/specs/rate-my-team.spec.ts -- Rate tab: visual diff describe block, adjacency assertion (ghostIdx === outIdx + 1) inside the Bench group"
        status: pass
      - kind: e2e
        ref: "E2E_PYTHON=... E2E_VARIANTS=0 E2E_PORT=8140 npm --prefix e2e run test -- specs/rate-my-team.spec.ts --project=chromium -- 5 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "The starter-sell ghost path (sell target already in a formation row) is unchanged and still lands in that row, not the bench"
    requirement: "E2E-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/RateDiff.test.tsx -- 'places the ghost card in the same formation row as the out card' (pre-existing test, unmodified, still passing)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/pitch/Pitch.test.tsx -- MID-row ghost tests (pre-existing, unmodified, still passing)"
        status: pass
    human_judgment: false
  - id: D3
    description: "New bench-sell path: resolveRateOverlay resolves ghost.row 'BENCH' for a benched sell (McBurnie), and RateDiff renders both markers inside the Bench group, zero in Forwards"
    requirement: "E2E-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/RateDiff.test.tsx -- 'keys the ghost row off the sell target's own row: BENCH for a benched sell (04-08)' and 'places the ghost card in the Bench group (not Forwards) for a benched sell target (04-08)'"
        status: pass
      - kind: unit
        ref: "frontend/src/components/pitch/Pitch.test.tsx -- 'renders in the Bench group immediately after the named bench player when row is BENCH (04-08)'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Unresolvable-sell fallback (buy's position, afterCode null) is preserved unchanged"
    requirement: "E2E-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/RateDiff.test.tsx -- 'falls back to the buy's position row, afterCode null, when the sell name is unresolvable'"
        status: pass
    human_judgment: false
  - id: D5
    description: "The ghost-holding Bench row (4 real + 1 ghost = 5 cells) stays exactly centered -- no G-03-1 centering regression"
    requirement: "E2E-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/pitch/Pitch.test.tsx -- 'keeps the ghost-holding Bench row (4 real + 1 ghost = 5) exactly centered (04-08)'"
        status: pass
    human_judgment: false
  - id: D6
    description: "e2e/fixtures/v1 stays byte-identical (D-08); no page.route() mocking added to the spec; full frontend build stays pure"
    requirement: ""
    verification:
      - kind: other
        ref: "git status --porcelain e2e/fixtures/v1 -- no output"
        status: pass
      - kind: other
        ref: "grep -c 'page.route(' e2e/specs/rate-my-team.spec.ts -- 0"
        status: pass
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh -- BUILD PURITY OK"
        status: pass
    human_judgment: false
  - id: D7
    description: "WINDOWS.md id=2 is closed (fixed, timestamped), open_count is 1, id=1 (Phase 1 typecheck no-op) is untouched, and deferred-items.md records the resolution"
    requirement: "E2E-04"
    verification:
      - kind: other
        ref: "node gsd-tools.cjs windows status -- open_count 1, fixed_count 1, id=2 status fixed"
        status: pass
      - kind: other
        ref: "grep -c 'Resolution' .planning/phases/04-e2e-regression-suite/deferred-items.md -- 1"
        status: pass
    human_judgment: false
  - id: D8
    description: "Full test suites stay green after the fix: Vitest 368 passed, full Playwright suite 42 passed, pytest 77 passed"
    requirement: ""
    verification:
      - kind: unit
        ref: "npm --prefix frontend run test -- 368 passed"
        status: pass
      - kind: e2e
        ref: "E2E_PYTHON=... npm --prefix e2e run test -- 42 passed (one shell-geometry.spec.ts flake on the first run, reproduced green on immediate rerun in isolation and in the full suite -- out of this plan's file scope)"
        status: pass
      - kind: other
        ref: "python -m pytest -q -- 77 passed"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-09-04
status: complete
---

# Phase 4 Plan 08: Bench-sell ghost-row fix (WINDOWS.md id=2 closure) Summary

**Keyed the rate-diff ghost card's row off the sell target's own row (bench included) instead of the buy's position, so the ghost and the outgoing card land in the same `role="group"` container for the real v1 capture's own bench-sell best_move — closing 04-VERIFICATION.md Gap 2 and WINDOWS.md id=2.**

## Performance
- **Duration:** 12min
- **Started:** 2026-09-04T05:45:14Z
- **Completed:** 2026-09-04T05:57:00Z
- **Tasks:** 3 completed
- **Files modified:** 7

## Accomplishments
- `Pitch.tsx`: widened `PitchGhost["row"]` to accept `"BENCH"` and wired the Bench `PitchRow` into the existing `rowGhost` mechanism, so it can now receive a ghost card exactly like the four formation rows already do.
- `RateDiff.tsx`: `resolveRateOverlay` now holds the matched sell row and derives the ghost's row with an ordered rule — bench sell → `"BENCH"`, starter sell → the sell row's own position, unresolved sell → the buy's position fallback (unchanged), replacing the old unconditional "always the buy's position" logic.
- `e2e/specs/rate-my-team.spec.ts`: rewrote the visual-diff test's per-row counts (Forwards 3→2, Bench 4→5, confirmed against a real Playwright run, not just arithmetic) and its ghost/outgoing assertions to prove same-group placement plus cell-adjacency (`ghostIdx === outIdx + 1`); rewrote the file's header comment to describe the corrected contract instead of the old two-different-row-groups explanation.
- Added 5 Vitest tests across `Pitch.test.tsx` and `RateDiff.test.tsx` pinning both the new bench-sell path and the preserved starter-sell/unresolvable-sell paths, plus a centering regression guard for the now-6-cell-capable Bench row.
- Closed `WINDOWS.md` id=2 via `gsd-tools windows fixed 2` (open_count 2→1, fixed_count 0→1) and appended a `## Resolution` section to `deferred-items.md`'s entry.
- Full suites confirmed green after the fix: Vitest 368/368, full 3-server Playwright suite 42/42 (a single `shell-geometry.spec.ts` flake on the first run reproduced green on an immediate isolated rerun and on a full-suite rerun — that file is outside this plan's `files_modified` and untouched), pytest 77/77.

## Task Commits
Each task was committed atomically:
1. **Task 1: Key the ghost row off the sell target's actual row, proven end to end against the real capture** - `8da751a` (fix)
2. **Task 2: Lock the bench-row ghost at component level in the Vitest suites** - `7d74a32` (test)
3. **Task 3: Close WINDOWS.md id=2 and the deferred-items entry** - `f984c09` (docs)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `frontend/src/components/pitch/Pitch.tsx` - Widened `PitchGhost["row"]` to include `"BENCH"`; spread `{...rowGhost("BENCH")}` onto the Bench `PitchRow`; updated the ghost-card doc comment.
- `frontend/src/components/RateDiff.tsx` - `resolveRateOverlay` now derives `ghost.row` from the matched sell row's `starting`/`position` via an ordered rule instead of unconditionally using the buy's position; updated the doc comment.
- `frontend/src/components/pitch/Pitch.test.tsx` - Added a bench-row ghost placement/adjacency test and a bench-row centering test (5-cell measure).
- `frontend/src/components/RateDiff.test.tsx` - Added a bench-sell `resolveRateOverlay` test, an unresolvable-sell fallback test, and a bench-sell render test.
- `e2e/specs/rate-my-team.spec.ts` - Rewrote the header comment and the visual-diff test's row counts/ghost assertions/adjacency proof for the corrected same-row behavior.
- `.planning/WINDOWS.md` - id=2 marked `fixed` with a `resolved_at` timestamp; `open_count` 2→1, `fixed_count` 0→1.
- `.planning/phases/04-e2e-regression-suite/deferred-items.md` - Appended a `## Resolution` section (original root-cause analysis left unchanged).

## Decisions Made
- Kept `"BENCH"` out of `VALID_PITCH_ROWS` (which validates API-supplied `position` strings) and reachable only through the boolean `starting` field on a resolved sell row — an attacker-controlled `position` string can never produce a `BENCH` ghost (T-04-08-01 mitigation).
- Held the matched sell row itself (not just its `player_code`) as a local in `resolveRateOverlay` so the ordered row-derivation rule can read both `starting` and `position` off the same object the pre-existing `outCode`/`diffs` logic already resolved.
- Re-pinned the visual-diff spec's Forwards/Bench row counts from a real Playwright run (Forwards 2, Bench 5) per D-15, rather than trusting the plan's own derived arithmetic outright — the live run confirmed the derived numbers were correct.

## Deviations from Plan

**1. [Informational — not a Rule 1-4 deviation] Task 2's baseline test count was mis-cited in the plan**

- **Found during:** Task 2 verification.
- **Issue:** The plan's `<verify>`/acceptance criteria for Task 2 state the two files' pre-existing test count as 16 (expecting `21 passed` after adding 5). The actual pre-existing count across `Pitch.test.tsx` and `RateDiff.test.tsx` was 27 (12 + 15), so the post-Task-2 total is `32 passed`, not `21`.
- **Fix:** None needed — the underlying property the criterion exists to protect (exactly 5 new tests added, zero deletions, zero failures) held exactly: `27 + 5 = 32`. The full-suite total the plan also specifies (`368 passed` = `363` baseline `+ 5`) matched exactly and is the criterion that actually gates correctness.
- **Files modified:** None (test-count arithmetic only, not implementation).
- **Verification:** `npm --prefix frontend run test -- src/components/RateDiff.test.tsx src/components/pitch/Pitch.test.tsx` → `32 passed`; `npm --prefix frontend run test` → `368 passed`.
- **Commit:** `7d74a32`.

**Total deviations:** 1 informational (plan arithmetic mis-citation, no code/test change required).
**Impact on plan:** None — all acceptance criteria that gate actual behavior (368 total Vitest, 5 Playwright, BUILD PURITY OK, WINDOWS.md counters) passed exactly as specified.

## Issues Encountered
A single `shell-geometry.spec.ts` test (`team page has no horizontal overflow at 390px (D-07)`) failed once during the first full 3-server Playwright run (`cardBoxes.length` was 0). This file is outside this plan's `files_modified` and was not touched. Re-ran it in isolation (passed) and re-ran the full suite (all 42 passed, including that test) — consistent with a one-off flake in an unrelated spec, not a regression caused by this plan's changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
04-VERIFICATION.md's Gap 2 is closed and WINDOWS.md's `open_count` is 1 (only id=1, the Phase 1 `npm run typecheck` no-op, remains — a different, already-scoped-out defect). All 6 items this plan's `flagged_assumptions` section carried are resolved or explicitly documented as unreachable on the immutable v1 capture (score-exactly-100 and the `xi_p10`-null branch), matching the precedent set by plans 04-04/04-05/04-06. This was the final gap-closure plan in phase 04-e2e-regression-suite's 8-plan sequence.

---
*Phase: 04-e2e-regression-suite*
*Completed: 2026-09-04*
