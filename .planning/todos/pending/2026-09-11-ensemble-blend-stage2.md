---
created: 2026-09-11T16:19:15.784Z
title: Ensemble blend of LightGBM + Ridge + XGBoost stage-2 predictions
area: models
severity: minor
files:
  - models/bracket/registry.py
  - models/bracket/classical.py
  - models/bracket/gbdt.py
  - models/bracket/gate.py
  - models/train.py
  - data/processed/experiments/bracket_gate_lgbm.json
  - data/processed/experiments/bracket_gate_ridge.json
  - data/processed/experiments/bracket_gate_xgb.json
---

## Problem

Phase 10's model-class bracket closed 7/7 HOLD — no single challenger cleared the
+0.010 gate margin over LightGBM — but the gate data contains one untested
hypothesis it actively supports: three *different model families* all edged the
incumbent on the identical 2024-25 validation split (played-only Spearman,
n=11,566):

- Ridge 0.3955 (+0.0055)
- XGBoost 0.3949 (+0.0049)
- MLP 0.3942 (+0.0042)
- LightGBM 0.3900 (incumbent)

Several decorrelated models tying slightly above the incumbent is the classic
setup where **averaging** beats any single-model swap. The bracket never had a
"blend" candidate, so this was not measured. This is a NEW candidate, not a
re-run of a rejected one — the ledger (IMPROVEMENTS.md Phase G) records the
seven solo rejections; it says nothing about a combination.

Important prior to keep honest: Phase 10 also established the problem is
signal-starved (Ridge topping the table is the tell), so the expected upside is
modest. The reason this is still worth one run is cost: zero new dependencies,
all three models already built in `models/bracket/`, seconds of extra inference,
and the D-15 cheap gate filters it before any expensive run.

## Solution

Reuse the existing bracket infrastructure end-to-end (D-15 two-stage discipline):

1. Add a `blend` candidate to `models/bracket/registry.py::CANDIDATES` (and a
   `bracket_blend` flag in `config.EXPERIMENTS`, default False). Start with the
   simple mean of lgbm+ridge+xgb `xp_med`/`xp_mean` predictions; optionally also
   a stacked linear combiner whose weights are fit on the validation season only
   (never the test season — leakage discipline as in models/bracket/sequence.py).
2. Declare the adoption criteria BEFORE any run (Phase 10's own discipline):
   gate margin (reuse +0.010 Spearman over the LightGBM baseline vintage) and
   the full-run bar (>= 2,280 model+chips over 6 seasons, 5 replicas).
3. Run the D-15 cheap gate (`models/bracket/gate.py`) — writes
   `data/processed/experiments/bracket_gate_blend.json`.
4. ONLY if the gate clears: one full 6-season 5-replica walk-forward (~2h,
   `backtest.walk_forward --tag blend6 --experiments bracket_blend`) against the
   >= 2,280 bar. Record the verdict either way in IMPROVEMENTS.md.

Caution from Phase 10 ops: never `uv pip sync` against the shared conda env;
long runs logged under data/processed/experiments/ with a `tail -f` command
printed; background jobs via `setsid nohup ... < /dev/null &`.
