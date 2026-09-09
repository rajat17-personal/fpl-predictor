---
created: 2026-09-09T05:14:14.086Z
title: Re-measure understat/fotmob accuracy per position and on covered rows only
area: models
severity: minor
files:
  - data/processed/experiments/understat_mae_comparison.json
  - backtest/benchmark_external.py
  - backtest/walk_forward.py
---

## Problem

Phase 9's understat/fotmob accuracy comparisons were pooled across all positions and all rows (understat_mae_comparison.json has per-season slices only). Two dilution effects hide any real positional signal: (1) the model is per-position and npxG/xGChain should help MID/FWD while FotMob defensive stats should help DEF — pooled MAE/Spearman can average a real gain away; (2) row-level join coverage is only ~41% (understat) / ~40% (fotmob), so ~60% of rows carry empty enrichment features and dilute the pooled reading further. understat was the closest miss of the phase (model+chips 2278 vs the 2,280 bar).

## Solution

Cheap re-measurement, no new modeling: slice the existing understat-on vs understat-off (and fotmob) MAE/Spearman comparison by position (GK/DEF/MID/FWD) and separately restrict to rows where the enrichment features actually joined. Harness artifacts and the `_stats_block` helper already exist. If a position shows a genuine covered-row gain, that motivates a per-position flag variant (e.g. understat features for MID/FWD only) as a follow-up experiment under the standard adoption discipline.
