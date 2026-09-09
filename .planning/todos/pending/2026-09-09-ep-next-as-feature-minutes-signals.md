---
created: 2026-09-09T05:14:14.086Z
title: Feed ep_next + availability flags into the xP model to close the ranking gap
area: models
severity: minor
files:
  - models/train.py:41
  - features/engineer.py
  - data/build_table.py
---

## Problem

Phase 9's external benchmark (backtest/benchmark_external.py, `benchmark_phase9.json`) showed FPL's own `ep_next` out-ranks our xP on played-only common rows: pooled Spearman 0.579 vs our 0.383 (MAE comparable, 1.975 vs 1.978). `xp_fpl` is deliberately excluded as a model feature (models/train.py:41 — "evaluation baseline only, not a feature"), and the minutes model sees no availability/news signals (chance_of_playing, status flags) that ep_next bakes in. The ranking gap is the most promising measured lead Phase 9 left behind.

## Solution

Two-part experiment behind a new default-off flag in config.EXPERIMENTS, judged on the standard 6-season/5-replica harness against baseline 2262 and the ≥2,280 bar (D-05/D-07/D-08 discipline):
1. Join lagged `xp_fpl` (already in player_gw.parquet) as a decision-time-known feature.
2. Add availability-flag features (chance_of_playing, status transitions) to the P(play) stage.
Also re-score the EXP-1 benchmark afterward — closing the Spearman gap to ep_next on the same played-only basis is the confirmation signal named in IMPROVEMENTS.md Phase F. Note: rank-aware training loss (LambdaRank) was already tested and rejected in an earlier phase — do not re-try that route.
