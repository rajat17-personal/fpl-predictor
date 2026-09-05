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
  - frontend/src/lib/squadJoin.test.ts
  - frontend/src/lib/squadJoin.ts
  - frontend/src/lib/usePageMeta.ts
  - frontend/src/routes/Team.test.tsx
  - frontend/src/routes/Team.tsx
  - frontend/src/routes/routeIsolation.test.tsx
  - frontend/src/test/fixtures/chips.json
  - frontend/src/test/fixtures/chips_dgw.json
  - frontend/src/test/fixtures/plan_response.json
  - frontend/src/test/fixtures/rate_response.json
  - frontend/src/test/fixtures/rate_response_hold.json
  - frontend/src/test/fixtures/solve_transfers_response.json
  - frontend/src/test/fixtures/squad.json
  - frontend/src/test/fixtures/team_response.json
  - frontend/src/test/fixtures/xp_table_squad.json
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-09-03T00:00:00Z
**Depth:** standard
**Files Reviewed:** 33 (source + test + fixture files in required scope)
**Status:** issues_found

## Summary

This is a re-review after gap-closure plan 03-05 landed, which rewrote `Pitch.tsx`'s row-centering
mechanism (flexbox `justify-content: center` against a shared `Math.max(5, count)`-part
`calc()` basis, driven by a new `--pitch-gap` CSS custom property) and added a dedicated row-symmetry
regression suite (`Pitch.test.tsx`'s `describe("Pitch — row centering (G-03-1)")`).

**The centering fix itself is correct.** I traced the algebra by hand for every row size the
formation supports (GK=1, DEF=3-5, MID=2-5, FWD=1-3, bench=4, and the ghost-widened 6-card case):
for a row whose card count equals the shared part count, `parts * basis + (parts-1) * gap` reduces
exactly to `100%` of the container, so `justify-content: center` is a no-op; for any row with fewer
cards than the shared part count, the row is strictly narrower than the container and centers
symmetrically. The test suite's own simulated-layout oracle (`assertRowIsExactlyCentered`) verifies
the same algebra against two viewports and both match the `--pitch-gap` breakpoint declared in
`index.css`. I found no defect in this code path.

Reviewing the rest of the required scope, I found two genuine logic bugs unrelated to the centering
fix — both are input-handling edge cases that silently drop or corrupt user intent rather than
crashing, and both are exercised by hand-written regression tests I wrote and ran against the
current code to confirm (not hypothetical):

1. `SolveControls`'s "Free transfers" field sends `free_transfers: 0` when the user clears the
   input, instead of falling back to `1` like its own `maxTransfers` sibling field and like
   `PlanTransfers`'s analogous field both do.
2. `PlayerCard`'s action-menu status/news paragraph is gated on `statusLabel` being non-null, so a
   player with `status: "a"` (available) and a non-empty `news` string never has that news text
   rendered, even though the `newsBody` variable was explicitly computed to include it.

No security issues, hardcoded secrets, or dangerous-function usage were found. No dead/unreachable
code beyond one intentionally-dead fallback branch (noted as Info below).

## Warnings

### WR-01: SolveControls sends `free_transfers: 0` instead of falling back to 1 when the input is emptied

**File:** `frontend/src/components/SolveControls.tsx:38-39`
**Issue:** `submit()` computes the request value as:
```ts
const ftNum = Number(freeTransfers);
const ftToSend = Number.isFinite(ftNum) ? ftNum : 1;
```
`Number("")` evaluates to `0` in JavaScript, and `Number.isFinite(0)` is `true` — so when a user
clears the "Free transfers" input (e.g. select-all + delete) and clicks "Solve transfers" without
retyping a value, the request silently carries `free_transfers: 0` rather than falling back to `1`
(the documented "never rendered blank" intent, and `/api/solve`'s own server-side default per the
component's own docstring). `0` free transfers is a **materially different, valid value** from the
server default — it tells the optimizer the user has *no* free transfer available, so every
recommended transfer is priced with a 4-point hit that may not actually apply, producing
incorrect financial advice in the UI.

Confirmed empirically: a throwaway test (`fireEvent.change(... , { target: { value: "" } })` then
clicking Solve) asserts `onSolve` is called with `{ freeTransfers: 0, ... }`, not `{ freeTransfers:
1, ... }`.

This is inconsistent with two sibling implementations in the same codebase that get this right:
- `SolveControls`'s own `maxTransfers` field, a few lines below, explicitly checks
  `trimmedMax !== ""` before parsing, treating empty as omitted.
- `PlanTransfers.tsx:70-72`'s analogous free-transfers handling explicitly guards
  `Number.isFinite(ftNum) && ftNum >= 1 ? ftNum : null`, which correctly treats an emptied field
  (parses to `0`) as invalid and falls back.

**Fix:**
```ts
const trimmedFt = freeTransfers.trim();
const ftNum = Number(trimmedFt);
const ftToSend = trimmedFt !== "" && Number.isFinite(ftNum) ? ftNum : 1;
```
(Mirror the `maxTransfers` empty-string guard above it, or use the same `>= 1` idiom as
`PlanTransfers.tsx` if `0` should never be sendable at all — clarify which is intended and add a
regression test for the emptied-input case, which is currently untested.)

### WR-02: PlayerCard drops a player's `news` text whenever `status` is `"a"` (available)

**File:** `frontend/src/components/pitch/PlayerCard.tsx:111-113, 209`
**Issue:**
```ts
const statusLabel =
  player.status && player.status !== "a" ? (STATUS_LABELS[player.status] ?? player.status) : null;
const newsBody = player.news || statusLabel;
...
{statusLabel && <p ...>{newsBody}</p>}
```
`newsBody` is deliberately computed as "news, falling back to the status label" — implying the
paragraph should render whenever there is *either* real news text *or* a status label. But the
render gate only checks `statusLabel`, ignoring `newsBody` entirely. Whenever `player.status` is
`"a"` (or `null`/empty), `statusLabel` is `null` regardless of whether `player.news` holds real
content, so the paragraph never renders — the news text is silently dropped even though `newsBody`
correctly resolved to it.

Confirmed empirically: rendering a `PlayerCard` with `status: "a"` and
`news: "Returned to full training this week"`, opening the action menu, and querying for that text
fails to find it in the DOM.

This is a real (if likely rare in current FPL-export data) information-loss bug: it silently hides
legitimate news copy for available players, and the behavior is untested (no `PlayerCard.test.tsx`
case exercises `status: "a"` with a non-empty `news` value).

**Fix:**
```ts
{newsBody && <p className="font-label text-label text-ink-2">{newsBody}</p>}
```
(Gate on `newsBody`, not `statusLabel`, since `newsBody` is the value actually rendered — add a
test case for `status: "a"` + non-empty `news`.)

## Info

### IN-01: Duplicated `Tile` component definition

**File:** `frontend/src/components/team/RateTab.tsx:38-54` and
`frontend/src/components/PlanTransfers.tsx:159-175`
**Issue:** Both files declare an identical `Tile({ heading, value, detail })` component
(same props interface, same JSX, same class strings). This is a straightforward extract-to-shared-
component opportunity; as written, a future styling change to one tile risks drifting from the
other.
**Fix:** Move `Tile` (and its `TileProps` interface) into a shared file, e.g.
`frontend/src/components/Tile.tsx`, and import it from both call sites.

### IN-02: Duplicated outside-click/Escape dismissal `useEffect` pattern

**File:** `frontend/src/components/pitch/PlayerCard.tsx:89-109` and
`frontend/src/components/ChipTimeline.tsx:35-55`
**Issue:** Both components independently implement the same "attach document click + keydown
listeners while open, tear down on close/unmount" pattern almost verbatim (same variable names,
same structure). This is a good candidate for a shared `useDismissablePopover(open, onDismiss)`
hook to avoid the two copies drifting (e.g. one gaining a bug fix the other doesn't get).
**Fix:** Extract a shared hook in `frontend/src/lib/` and use it from both components (and any
future popover/tooltip that needs the same behavior).

### IN-03: Dead fallback branches for values that can never occur

**File:** `frontend/src/components/SolveControls.tsx:48`, `frontend/src/components/PlanTransfers.tsx:70`
**Issue:** Both `const horizonNum = Number(horizon || 1)` (SolveControls) and
`const hz = Number(horizon || 1)` (PlanTransfers) guard against `horizon` being falsy/empty, but
`horizon` is always a controlled `<select>` value seeded from a fixed `HORIZON_OPTIONS`/hardcoded
option list and can never be an empty string in practice — the `|| 1` branch is unreachable. Low
severity (harmless, self-documenting even if dead), but worth removing or at least noting it's
defensive-only so a future reader doesn't assume it's load-bearing.
**Fix:** Either remove the `|| 1` (simplify to `Number(horizon)`) or add a one-line comment noting
it's unreachable defensive code, matching the project's own convention of commenting non-obvious
guards.

---

_Reviewed: 2026-09-03T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
