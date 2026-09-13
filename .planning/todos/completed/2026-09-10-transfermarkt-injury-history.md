---
created: 2026-09-10T03:30:00.000Z
title: Transfermarkt injury-history flag for P(play) — backfillable across all seasons
area: data
severity: major
resolves_phase: 10
files:
  - data/
  - models/train.py
  - tests/test_leakage.py
---

## Problem

Historical per-gameweek availability is the P(play) stage's missing signal, and FPL-API history can only be backfilled ~1 season. Transfermarkt injury records are retrospective, timestamped, and structured — backfillable across ALL training seasons (2016-17 onward), per the IJCSS 2025 paper (10.2478/ijcss-2025-0008) whose clearest wins were on the will-play classification task.

## Solution

Build a cached, rate-limited, kill-switchable Transfermarkt injury-history fetcher (same conventions as data/understat.py / data/fotmob.py; worldfootballR documents the endpoints — reimplement in Python). Features per player-GW: injured-boolean and days-out in the pre-deadline week, joined via the id crosswalk. Feed P(play) only, behind a default-off flag; extend tests/test_leakage.py to assert injury-spell dates precede fixture kickoff. A/B on the full walk-forward (this source covers all seasons, unlike the FPL-flag backfill). Run as a background killable fetcher; expect rate-limit-bound wall clock.
