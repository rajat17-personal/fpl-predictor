---
created: 2026-09-09T05:14:14.086Z
title: High-replica captaincy ceiling-EV re-run to settle the +1.5pt capture reading
area: models
severity: minor
resolves_phase: 10
files:
  - backtest/walk_forward.py
  - config.py:149
  - IMPROVEMENTS.md
---

## Problem

Phase 9's capt_ceiling experiment measured capture 0.563→0.578 (+1.5pt absolute, bar was ≥+2) and model+chips +16 (2262→2278) at the harness default of 5 replicas — where SE ≈ 16 pts/season, so the +16 is ~1 standard error and indistinguishable from noise (the identical +16 also appeared for understat with flat accuracy). The direction is positive; the measurement is just too noisy to decide whether +1.5pt capture is real. User wants this settled under Phase 9's own ledger (IMPROVEMENTS.md Phase F addendum), not deferred to a distant phase.

## Solution

Re-run the adoption comparison (baseline vs `--experiments capt_ceiling`, lambda already pinned at 0.5) at a much higher replica count — e.g. 25 replicas × 6 seasons for both arms — to shrink the CI ~√5×. Record as a Phase F addendum row in IMPROVEMENTS.md. Decision rule: if +1.5pt capture holds with a CI excluding zero and season points don't regress, present to the user as a case for revising the D-06 bar (human decision — D-07's mechanical rule stands until the user changes the bar). If it washes out, the rejection is confirmed cheaply. Gate capt_mc (Monte-Carlo variant, models/simulate.py still unbuilt) on this outcome: only build it if the ceiling signal proves real.
