---
created: 2026-09-10T03:30:00.000Z
title: fplreview free projections as a weekly scoreboard benchmark
area: predict
severity: minor
resolves_phase: 10
files:
  - predict/scoreboard.py
---

## Problem

We benchmark against ep_next and theFPLkiwi, but not against the strongest commercial projection service. Their model is closed (ToS blocks ingestion as a feature source), but their free-tier projections can be recorded weekly for comparison.

## Solution

Manual-assisted weekly capture (their site 403s scrapers — likely a user download/paste step before each GW), stored under data/external/fplreview/, scored post-GW alongside ep_next in the scoreboard (MAE + Spearman on common players). Diagnostic only — never redistributed, never a model input (ToS). Low priority; skip if the manual step proves annoying.
