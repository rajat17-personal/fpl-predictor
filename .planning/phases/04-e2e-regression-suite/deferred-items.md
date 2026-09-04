# Deferred Items — Phase 04

Items observed during execution that are out of scope for the plan that found them
(scope boundary: only auto-fix issues directly caused by the current task's changes).

## Ghost card and outgoing label land in different pitch rows when the sold player is benched

- **Found during:** 04-06 Task 2, while writing `e2e/specs/rate-my-team.spec.ts`'s
  single-pitch visual-diff assertions against the real, immutable `e2e/fixtures/v1/normal`
  capture's `/api/rate/6980093` response.
- **What the frozen data actually produces:** the rating's `best_move` sells Mateta
  (xp=0, `starting: false` — a bench player in the no-transfer XI) for Wissa (FWD, not
  currently owned). Verified by booting the fixture-mode server locally and rendering the
  page in a real headless Chromium session (not just by reading source): the ghost card
  lands in the `role="group" aria-label="Forwards"` row (its position, per
  `RateDiff.tsx`'s `resolveRateOverlay`), while the dimmed outgoing card and its
  `sr-only "Suggested transfer out"` label land in `role="group" aria-label="Bench"` — two
  different row-group containers, not the same one.
- **Root cause:** `frontend/src/components/pitch/Pitch.tsx`'s ghost-insertion mechanism
  (`rowGhost`) is only ever wired into the four formation rows (GK/DEF/MID/FWD), never the
  bench row, and it always inserts the ghost into the row matching the **buy's** position —
  never the row the **sell** target actually occupies. When the sell target is a starter in
  that same position, `ghostAfterCode` finds it and both land in the same row (the scenario
  `03-03-SUMMARY.md` deliberately corrected its Vitest fixture to exercise: "Egan(bench
  DEF)/Gvardiol(already-owned)" → "Havertz(starting FWD)/Haaland(not owned)" specifically
  because a bench-out pairing "cannot satisfy the ghost-same-row acceptance criterion"). When
  the sell target is benched instead (as the real, immutable v1 capture happens to produce),
  the same-row guarantee silently does not hold — this was accepted-but-avoided in Phase 3's
  Vitest fixture, not actually fixed in `Pitch.tsx`.
- **Impact:** the visual diff's core promise ("the incoming ghost sits where the outgoing
  player was") is broken specifically for a real, legitimately-suggested transfer whose sell
  target is a bench player rather than a starter — arguably the MORE common real-world
  suggestion (selling a worthless bench player is a very ordinary "best move"). A user
  reading the diff sees a new ghost appear in the Forwards row with no visible link to the
  player it's meant to be replacing (which is dimmed, unrelated-looking, in the Bench
  section below).
- **Not fixed here:** `04-06-PLAN.md`'s `files_modified` is `e2e/specs/rate-my-team.spec.ts`
  only; `Pitch.tsx`/`RateDiff.tsx` are pre-existing Phase 3 code, not touched by this plan's
  own changes (scope boundary). Mutating the immutable `e2e/fixtures/v1/normal` capture to
  force a starting-player sell instead is forbidden (D-08). `e2e/specs/rate-my-team.spec.ts`
  asserts the REAL observed behavior (both the ghost and the outgoing label present, in two
  different row groups) rather than silently asserting the plan's originally-assumed
  same-row behavior, which this real data does not exhibit.
- **Suggested follow-up:** extend `Pitch.tsx`'s ghost mechanism to key off the SELL target's
  actual row (including the bench row) rather than the BUY's position — e.g. thread the
  ghost through `rowGhost("Bench")` too when `ghost.afterCode` resolves inside the bench
  array — so the same-row guarantee holds regardless of which row the outgoing player
  currently occupies. Logged to `.planning/WINDOWS.md` (kind: deviation) so `/gsd-ship`
  surfaces it before this milestone ships.

## Resolution

Fixed in plan `04-08` (04-VERIFICATION.md Gap 2 was the source of truth that required the
fix). `Pitch.tsx`'s `PitchGhost["row"]` union was widened to accept `"BENCH"` and the Bench
`PitchRow` was wired into the existing `rowGhost` mechanism; `RateDiff.tsx`'s
`resolveRateOverlay` now derives the ghost's row from the matched sell row itself (bench sell
-> `"BENCH"`, starter sell -> the sell row's own position, unresolved sell -> the buy's
position fallback, unchanged) instead of unconditionally using the buy's position. Files
changed: `frontend/src/components/pitch/Pitch.tsx`, `frontend/src/components/RateDiff.tsx`.

`e2e/specs/rate-my-team.spec.ts` now asserts the corrected same-row-plus-adjacency behavior
against the same unmodified `e2e/fixtures/v1` capture (D-08): the ghost card and the outgoing
player's dimmed card both render inside the `role="group"` container labelled Bench, with the
ghost immediately after the outgoing card (Forwards 2 / Bench 5 replacing the old Forwards 3 /
Bench 4 counts). `.planning/WINDOWS.md` id=2 is marked `fixed`.
