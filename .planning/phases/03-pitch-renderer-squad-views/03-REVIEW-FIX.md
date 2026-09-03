---
phase: 03-pitch-renderer-squad-views
fixed_at: 2026-09-03T06:50:51Z
review_path: .planning/phases/03-pitch-renderer-squad-views/03-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-09-03T06:50:51Z
**Source review:** .planning/phases/03-pitch-renderer-squad-views/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (1 critical, 3 warning — fix_scope: critical_warning; the 3 Info findings were intentionally not touched)
- Fixed: 4
- Skipped: 0

**Verification environment:** All fixes were applied, verified (Tier 1 re-read + Tier 2 `npx tsc --noEmit` + targeted `npx vitest run`), and committed inside an isolated git worktree (`.claude/worktrees/rf-03-111094-1788418100`, branch `gsd-reviewfix/03-111094`), not the main checkout. `node_modules` was symlinked from the main checkout into the worktree so `tsc`/`vitest` could resolve dependencies. After all four fixes, the full frontend suite (`npx vitest run`) and `npm run typecheck` were re-run once more inside the same worktree as a final gate — both passed. These results are reproducible from the worktree's git history (now fast-forwarded onto `master`) but not from a separately-checked-out main tree after the worktree is torn down.

## Fixed Issues

### CR-01: Ghost card in a full formation row overflows the fixed 5-column pitch grid

**Files modified:** `frontend/src/components/pitch/Pitch.tsx`
**Commit:** c1c7636
**Applied fix:** `PitchRow` now computes `columns = Math.max(5, slots.length)` and renders `gridTemplateColumns: repeat(${columns}, minmax(0, 1fr))` instead of a hard-coded `grid-cols-5` class. `centeredStartColumn` was updated to take `columns` as a parameter (`Math.floor((columns - count) / 2) + 1`) instead of hard-coding `5`. A row with a ghost card pushing it to 6 total cards now gets a genuine 6-column grid where every card (including the ghost) shrinks together, instead of a 5-column grid with the 6th card landing in an unsized implicit column and clipping inside the pitch's `overflow-hidden` wrapper. Verified with `npx tsc --noEmit` (clean) and `npx vitest run src/components/pitch/Pitch.test.tsx` (6/6 passed, including the existing ghost-card test that exercises the 5-real + 1-ghost MID row scenario).

### WR-01: A malformed `/api/solve` response leaves the Squad tab stuck in "pending" forever

**Files modified:** `frontend/src/components/team/SquadTab.tsx`
**Commit:** f89439d
**Applied fix:** In `useSolveController.solveNow`, the unexpected `kind: "squad"` branch (previously a silent no-op after the exhaustiveness assignment) now calls `setSolve({ status: "error", error: "Unexpected solve response" })`. The compile-time exhaustiveness check (`const stillSquad: SolveSquadResult = result`) is preserved unchanged. Verified with `npx tsc --noEmit` (clean) and `npx vitest run src/components/team/SquadTab.test.tsx` (34/34 passed).

### WR-02: Conflicting Tailwind size utilities on the current-GW marker rely on cascade order

**Files modified:** `frontend/src/components/ChipTimeline.tsx`
**Commit:** 80ef052
**Applied fix:** Replaced the always-present `h-3 w-3` + conditionally-appended `h-5 w-5` string concatenation with a single `size` variable computed via a ternary (`isCurrent ? "h-5 w-5 ring-2 ..." : "h-3 w-3"`), so the two size class sets are now mutually exclusive in the rendered `class` attribute rather than both present and dependent on Tailwind's stylesheet emission order. Verified with `npx tsc --noEmit` (clean) and `npx vitest run src/components/ChipTimeline.test.tsx` (8/8 passed).

### WR-03: Unchecked cast can silently drop the suggested-buy ghost card

**Files modified:** `frontend/src/components/RateDiff.tsx`
**Commit:** 837fee2
**Applied fix:** Added a `VALID_PITCH_ROWS` set (`"GK" | "DEF" | "MID" | "FWD"`) and validated `row.position` against it before constructing the ghost in `resolveRateOverlay`. On a match, the ghost is built as before (cast retained, now guarded). On no match, the ghost is left `null` and — mirroring `kitMap.ts`'s `resolveKit` pattern — a `console.warn` fires only in `import.meta.env.DEV`, so an out-of-set position now leaves a debuggable signal instead of a silent no-op. Verified with `npx tsc --noEmit` (clean) and `npx vitest run src/components/RateDiff.test.tsx` (15/15 passed).

## Skipped Issues

None — all 4 in-scope findings were fixed.

## Full Suite Verification

After all four fixes were committed, the full frontend suite was re-run once from the worktree:

- `npx vitest run` — 38 test files, 357 tests, all passed
- `npm run typecheck` (`tsc --noEmit`) — no errors

Info findings IN-01, IN-02, IN-03 were left untouched per `fix_scope: critical_warning`.

---

_Fixed: 2026-09-03T06:50:51Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
