---
created: 2026-09-12T10:56:23.962Z
title: Chip-aware GW plan — chips as MILP decision variables with reservation values
area: models
severity: minor
files:
  - optimize/multi_period.py
  - optimize/chips.py
  - api/main.py:688
  - frontend/src/components/RateDiff.tsx
  - frontend/src/components/ChipTimeline.tsx
  - backtest/walk_forward.py
---

## Problem

Chip advice is currently generic and disconnected from the transfer plan:

- `optimize/chips.py` schedules chips purely from fixture structure (biggest
  DGWs → TC/BB, biggest blanks → FH, fixed WC slots) — identical for every
  user, and BB/FH are *only ever* scheduled on doubles/blanks. In a half with
  no doubles or blanks, BB and FH are never recommended and expire unused at
  the half deadline (2026/27 rule: one chip set per half, gone at GW19/GW38).
  An unused chip is pure lost value; "wait for a double" is only right when a
  double is actually coming.
- `optimize/multi_period.py` explicitly excludes chips ("Chips are not decided
  here — they stay with the season-level scheduler"), so the GW plan can never
  say "play Bench Boost this week".
- `/api/rate` never mentions chips at all, even though it already runs the two
  ILP solves (user's squad + optimal squad) whose gap is the natural
  Wildcard/Free Hit signal.

Origin: user request 2026-09-12 (pre-Phase-7 discussion) — post-cutover work,
must not enter the Phase 7 cutover scope.

## Solution

Chips become decision variables inside the multi-period plan, not a
side-annotation:

1. **MILP extension** (`optimize/multi_period.py`): per-week binaries per chip —
   BB adds bench xP that week; TC adds the captain's xP a second time; WC
   relaxes transfer costs that week; FH gets a one-week parallel squad that
   reverts. Constraints: at most one chip per GW, per-half inventory.
2. **Reservation values** (the non-trivial part): a myopic 6-GW window always
   wants to burn chips (saving has value 0 inside the window). Each chip gets a
   reservation value = estimated worth in the best remaining week of the half —
   from fixture structure where known, historical DGW/BGW frequency where not.
   A chip fires only when in-window value beats the reservation value. The
   value decays to zero as the GW19/GW38 expiry approaches, so
   "spend BB on the best normal bench week rather than let it expire" falls
   out of the math instead of being a special case.
3. **Surfacing**: Rate My Team shows this week's chip verdict from the plan;
   the Chips tab becomes a view of the plan's chip schedule instead of the
   standalone fixture-structure heuristic.
4. **Validation**: walk-forward backtest already measures isolated chip value
   (`backtest/walk_forward.py`) — use it to prove the chip-aware plan beats the
   current heuristic schedule before shipping.
