---
created: 2026-09-10T03:30:00.000Z
title: Model-class bracket — LSTM/GRU, XGBoost/CatBoost, Ridge, small MLP vs LightGBM
area: models
severity: minor
resolves_phase: 10
files:
  - models/train.py
  - backtest/walk_forward.py
---

## Problem

Phase 9/10 measured that added INPUTS don't move season points, but the MODEL CLASS has never been varied: LightGBM is the only regressor ever fielded. The user wants at least 1-2 candidates from each family tested (deep learning, classical/regression, decision trees).

## Solution

One bounded bracket experiment, not N separate ones. Candidates on the SAME feature matrix and splits: Ridge/ElasticNet (classical floor, interpretable), XGBoost + CatBoost (GBDT siblings; low expected delta but cheap — same pipeline), small MLP, and a small LSTM/GRU consuming leakage-safe per-GW sequence vectors (last 8-10 GWs, padded/masked) for E[pts|played] only, keeping the LightGBM P(play) stage. Two-stage gate to control cost: (1) cheap gate — played-only fixture-level Spearman/MAE on the standard validation split; only candidates beating LightGBM's 0.383 Spearman advance; (2) full 6-season walk-forward for gate-winners only, judged on the ≥2,280 bar. Prior: GBDTs usually win on tabular data; the value is closing the model-class question with numbers. Colab GPU units are useful here (the sequence models are actually GPU-bound, unlike the RL env). Note: LambdaRank/ranking loss already tested and rejected — exclude.
