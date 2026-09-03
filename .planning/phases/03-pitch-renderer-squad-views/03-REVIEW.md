---
phase: 03-pitch-renderer-squad-views
reviewed: 2026-09-03T00:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - docs/decisions/pitch-kit-sourcing.md
  - frontend/src/components/ChipTimeline.test.tsx
  - frontend/src/components/ChipTimeline.tsx
  - frontend/src/components/PageShell.test.tsx
  - frontend/src/components/PageShell.tsx
  - frontend/src/components/PlanTransfers.test.tsx
  - frontend/src/components/PlanTransfers.tsx
  - frontend/src/components/RateDiff.test.tsx
  - frontend/src/components/RateDiff.tsx
  - frontend/src/components/SolveControls.test.tsx
  - frontend/src/components/SolveControls.tsx
  - frontend/src/components/SolveResultsBar.test.tsx
  - frontend/src/components/SolveResultsBar.tsx
  - frontend/src/components/pitch/Kit.test.tsx
  - frontend/src/components/pitch/Kit.tsx
  - frontend/src/components/pitch/Pitch.test.tsx
  - frontend/src/components/pitch/Pitch.tsx
  - frontend/src/components/pitch/PlayerCard.test.tsx
  - frontend/src/components/pitch/PlayerCard.tsx
  - frontend/src/components/pitch/kitMap.test.ts
  - frontend/src/components/pitch/kitMap.ts
  - frontend/src/components/team/ChipsTab.test.tsx
  - frontend/src/components/team/ChipsTab.tsx
  - frontend/src/components/team/RateTab.test.tsx
  - frontend/src/components/team/RateTab.tsx
  - frontend/src/components/team/SquadTab.test.tsx
  - frontend/src/components/team/SquadTab.tsx
  - frontend/src/index.css
  - frontend/src/lib/api.ts
  - frontend/src/lib/formation.test.ts
  - frontend/src/lib/formation.ts
  - frontend/src/lib/pairMoves.test.ts
  - frontend/src/lib/pairMoves.ts
  - frontend/src/lib/usePageMeta.ts
  - frontend/src/routes/Team.test.tsx
  - frontend/src/routes/Team.tsx
  - frontend/src/routes/routeIsolation.test.tsx
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-03T00:00:00Z
**Depth:** standard
**Files Reviewed:** 33 (+ 1 decision doc, non-code)
**Status:** issues_found

## Summary

Reviewed the pitch renderer, kit system, and Squad/Rate/Chips team-page components delivered
in Phase 3, along with their supporting `lib/` helpers and tests. Overall the code is careful
and well-tested for the behaviours its own test suite targets (DOM structure, accessible names,
request bodies, ordering-safety of overlapping solves). The one blocker found is a real CSS
Grid layout defect in the shared `Pitch`/`PitchRow` component: a formation row that is already
at its 5-card ceiling (D-07) and also receives a ghost/suggested-transfer card ends up with 6
grid items forced into a `grid-cols-5` container via inline `gridColumn` indices — the 6th card
lands in an unsized implicit column and will overflow/clip inside the pitch surface's
`overflow-hidden` wrapper, contradicting the component's own comment that the row "stays
5-column" and "shrinks." This is not caught by the existing test suite because jsdom performs
no layout, so the DOM-order assertions pass while the actual rendered layout is broken. This
scenario is directly exercised in production by `RateDiff`'s ghost overlay and `SquadTab`'s
solve-diff overlay whenever the suggested buy's position is already a full row.

Three warnings and three info-level items are also noted below — a permanently-stuck "pending"
solve state if the server ever violates its own response-kind contract, a fragile Tailwind
class-conflict pattern, an unchecked type assertion that can silently drop a ghost card, and
some minor dead-code/robustness gaps.

## Critical Issues

### CR-01: Ghost card in a full formation row overflows the fixed 5-column pitch grid

**File:** `frontend/src/components/pitch/Pitch.tsx:29-31,82-114`
**Issue:** `PitchRow` always renders inside a `grid grid-cols-5` container (5 explicit
`minmax(0, 1fr)` column tracks) and positions each slot via an inline `style={{ gridColumn:
start + i }}`. `buildRowSlots` can add a ghost card to a row that already holds the D-07 ceiling
of 5 real cards (DEF/MID max 5), producing 6 slots. `centeredStartColumn(6)` returns `1` (via
`Math.max(1, Math.floor((5-6)/2)+1)`), so the 6 cards are placed at columns 1 through 6 — but
the grid only defines 5 explicit tracks. CSS Grid creates an implicit 6th column track sized by
`grid-auto-columns` (default `auto`, i.e. sized to content), which does **not** shrink to match
the other five `1fr` tracks. The row therefore overflows its container width, and because the
row sits inside the pitch surface's `overflow-hidden` wrapper (`Pitch.tsx:146-147`), the 6th
(ghost) card is likely to be partially or fully clipped rather than "shrinking to fit" as the
adjacent comment claims (`Pitch.tsx:27-28`). This is directly reachable in production:
`RateDiff.tsx` and `SquadTab.tsx` both feed suggested-transfer ghost overlays into `<Pitch>`,
and `Pitch.test.tsx`'s own ghost-card test exercises exactly this case (5 MID starters +
1 ghost = 6 cards in the MID row) — it just doesn't assert on layout, so jsdom lets it pass.
**Fix:** Either widen the grid to fit the ghost slot count and let every card shrink together,
or exempt the row from `overflow-hidden` clipping. The simplest fix that preserves the "all
five columns shrink together" intent:
```tsx
// Pitch.tsx — PitchRow
const columns = Math.max(5, slots.length);
return (
  <div
    className="grid gap-1 min-[480px]:gap-2"
    style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
    role="group"
    aria-label={label}
  >
    {slots.map((slot, i) => (
      <div key={`${slot.kind}-${slot.player.player_code}`} style={{ gridColumn: start + i }}>
        ...
      </div>
    ))}
  </div>
);
```
and recompute `centeredStartColumn` against `columns` instead of the hard-coded `5`. This makes
a 6-card row a genuine 6-column grid (all cards shrink together, matching the documented intent)
instead of a 5-column grid with an overflowing 6th item.

## Warnings

### WR-01: A malformed `/api/solve` response leaves the Squad tab stuck in "pending" forever

**File:** `frontend/src/components/team/SquadTab.tsx:143-160`
**Issue:** `useSolveController.solveNow` calls `setSolve({ status: "pending" })` before awaiting
`postSolve`. On success, if `result.kind === "transfers"` it calls `setSolve({status:
"success", ...})`; otherwise (the `kind === "squad"` branch) it does nothing but a
compile-time-only exhaustiveness assignment (`const stillSquad: SolveSquadResult = result; void
stillSquad;`). No `setSolve` call happens in that branch, so if the server ever returns
`kind: "squad"` for a solve triggered from this UI (a backend regression, or the "this UI never
sends entry: null" assumption ever becoming false), `solve.status` stays `"pending"`
indefinitely: the button stays disabled and "Solving your transfers…" is shown forever, with no
error and no way to recover short of a full remount.
**Fix:** Treat the unexpected-kind branch as a defensive error path, not a silent no-op:
```ts
} else {
  if (seq === solveSeqRef.current) {
    setSolve({ status: "error", error: "Unexpected solve response" });
  }
}
```

### WR-02: Conflicting Tailwind size utilities on the current-GW marker rely on cascade order

**File:** `frontend/src/components/ChipTimeline.tsx:64-66`
**Issue:**
```ts
const dotClasses = `h-3 w-3 shrink-0 rounded-full ${...} ${
  isCurrent ? "h-5 w-5 ring-2 ring-accent ring-offset-1 ring-offset-surface" : ""
}`;
```
`h-3 w-3` is unconditionally present, and `h-5 w-5` is appended (not swapped in) when
`isCurrent`. Both class names coexist in the DOM's `class` attribute; which one visually wins
depends entirely on the order Tailwind happens to emit the two utility rules in the generated
stylesheet, not on source order in this string. It currently likely "works" because Tailwind's
default spacing scale is emitted in ascending numeric order (so `h-5`/`w-5` land after
`h-3`/`w-3` and win), but that is an implementation detail of the build, not a guarantee this
component enforces itself.
**Fix:** Make the two class sets mutually exclusive:
```ts
const size = isCurrent
  ? "h-5 w-5 ring-2 ring-accent ring-offset-1 ring-offset-surface"
  : "h-3 w-3";
const dotClasses = `${size} shrink-0 rounded-full ${...}`;
```

### WR-03: Unchecked cast can silently drop the suggested-buy ghost card

**File:** `frontend/src/components/RateDiff.tsx:64-68`
**Issue:** `resolveRateOverlay` builds the ghost with `row: row.position as PitchGhost["row"]`
— an unchecked type assertion from `XpRow.position: string` to the union `"GK" | "DEF" | "MID"
| "FWD"`. If `xp_table.json` ever contains a position value outside that set (typo in the
export pipeline, a new position code, etc.), `Pitch.tsx`'s `rowGhost(row)` will never match it
against any of the four rendered rows (`ghost.row === row` never true), so the ghost simply
never renders — no error, no console warning, no visible failure. A tester following the
"+{xp_gain} xP" swap line but seeing no ghost card would have no signal that something is
wrong with the underlying data rather than working as designed.
**Fix:** Validate the position before constructing the ghost and fall back gracefully with a
dev warning, mirroring `kitMap.ts`'s `resolveKit` pattern:
```ts
const VALID_ROWS = new Set(["GK", "DEF", "MID", "FWD"]);
if (!VALID_ROWS.has(row.position)) {
  if (import.meta.env.DEV) {
    console.warn(`resolveRateOverlay: unexpected position "${row.position}" for ghost buy`);
  }
} else {
  ghost = { row: row.position as PitchGhost["row"], afterCode: outCode, player: ghostPlayer };
}
```

## Info

### IN-01: `hoops` kit pattern is fully implemented and tested but unused by any current club

**File:** `frontend/src/components/pitch/kitMap.ts:18-39`, `frontend/src/components/pitch/Kit.tsx:30-36`
**Issue:** `KitPattern` includes `"hoops"`, and `Kit.tsx` renders a dedicated hoops SVG branch
(also covered by `Kit.test.tsx`'s `it.each` over all four patterns), but no entry in `KIT_MAP`'s
current 20 clubs uses `"hoops"`. It's dead code in production today.
**Fix:** No action required if this is intentional forward-provisioning (kept for future club
additions/corrections per the kit-sourcing decision doc's Assumption A1); otherwise consider a
`kitMap.test.ts` assertion that every declared `KitPattern` is used at least once, so the map
and the pattern enum can't silently drift apart.

### IN-02: Dead fallback expressions for horizon/plan-horizon selects

**File:** `frontend/src/components/PlanTransfers.tsx:70`, `frontend/src/components/SolveControls.tsx:48`
**Issue:** Both `submitPlan`/`submit` compute `Number(horizon || 1)`. `horizon` is always a
non-empty string driven by a `<select>` with a fixed default value ("3" / "1") and a fixed
option list — it can never be `""`/falsy, so the `|| 1` fallback is unreachable.
**Fix:** Simplify to `Number(horizon)` (or leave as defensive belt-and-braces if intentional —
worth a one-line comment either way so a future reader doesn't wonder if it's load-bearing).

### IN-03: Free-transfers/max-transfers inputs aren't clamped to their declared HTML bounds

**File:** `frontend/src/components/SolveControls.tsx:37-50`, `frontend/src/components/PlanTransfers.tsx:69-81`
**Issue:** Both components declare `min`/`max` on their numeric `<input>`s (mirroring the
server's `Field(ge=…, le=…)` constraints per the adjacent comments), but the values sent in
`onSolve`/`postPlan` are only checked for finiteness, not clamped/rejected against those same
bounds. A value entered outside the declared range (e.g. via a spinner double-click, paste, or
programmatic `fireEvent.change`) is still submitted as-is, so out-of-range requests are caught
only by the server's 422 response and surfaced as a generic "Couldn't solve/plan: {status}"
message rather than an inline client-side validation error.
**Fix:** Not a security concern (server validates), but for UX robustness, clamp before sending,
e.g. `Math.min(5, Math.max(0, ftNum))` for free transfers, or short-circuit and show a local
validation message instead of firing the request.

---

_Reviewed: 2026-09-03T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
