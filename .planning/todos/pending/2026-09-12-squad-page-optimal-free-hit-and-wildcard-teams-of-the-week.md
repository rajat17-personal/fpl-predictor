---
created: 2026-09-12T10:56:23.962Z
title: Squad page — show optimal Free Hit and Wildcard teams of the week
area: ui
severity: minor
files:
  - optimize/squad_ilp.py
  - predict/export.py
  - frontend/src/components/pitch
---

## Problem

The squad page shows only the single from-scratch "template" squad
(`squad.json`). A user weighing whether to play Free Hit or Wildcard this week
has no view of what the optimal team for *this specific gameweek* would look
like under each chip, so the chip decision stays abstract.

Origin: user request 2026-09-12 (pre-Phase-7 discussion) — post-cutover work,
must not enter the Phase 7 cutover scope.

## Solution

Render two additional pitch views alongside the template squad:

- **Optimal Free Hit team**: from-scratch ILP squad optimized for the current
  GW only (single-GW xP, no ownership continuity) — `pick_squad`
  (`optimize/squad_ilp.py`) already computes exactly this shape.
- **Optimal Wildcard team**: from-scratch squad optimized over the multi-GW
  horizon (the squad you'd hold going forward), i.e. the same solve on the
  horizon pool.

Export both from `predict/export.py` into the `web/data/*.json` contract (new
fields or files, additive only) and reuse the existing pitch renderer
components (`frontend/src/components/pitch`). Pairs with the chip-aware GW
plan todo (2026-09-12-chip-aware-gw-plan-…): these views visualize what that
plan's WC/FH decisions would field.
