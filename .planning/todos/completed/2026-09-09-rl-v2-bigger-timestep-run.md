---
created: 2026-09-09T05:14:14.086Z
title: RL v2 — retrain MaskablePPO with a 120-min/policy time-box, judge vs solver
area: optimize
severity: minor
resolves_phase: 10
files:
  - optimize/rl_train.py
  - optimize/rl_env.py
  - data/processed/experiments/rl_v2_policies/
---

## Problem

Phase 9's rl_strategy rejection was budget-bound, not design-bound: 30-min/policy reached only 5-14k of the 200k target timesteps, far too few for a 40-action space, and the policy never moved off initialization (seed-mean 2020 vs solver's 2192). Worth one honest re-run with a materially larger budget before considering the RL direction settled.

## Declared time-box (written before training started, D-16 discipline)

- Seeds: 0, 1, 2 (config.RL_SEEDS, unchanged). Policies: 15 (5 trainable seasons × 3 seeds; 2020-21 structurally excluded as before).
- Per-policy wall-clock cap: **120 minutes** (user-selected 2026-09-09), `--timesteps 200000` target unchanged.
- Reward: unchanged — pure realised points net of hits. No shaping.
- Outputs isolated from Phase 9 evidence: `--out data/processed/experiments/rl_v2_policies/rl_policy_<season>_<seed>.zip` (default RL_POLICY_DIR would overwrite the phase's recorded policies/sidecars).
- Launched 2026-09-09 as 3 detached per-seed drivers (survives session exits); logs `data/processed/experiments/rl_v2_train_seed{0,1,2}.log`, done-markers `rl_v2_train_seed<N>.done`.
- Stop rule: when the box is spent, evaluate as-is. No extra seeds, no extension.

## Solution (after training completes)

Copy/point the v2 policies into RL_POLICY_DIR (or add an env override) and run the same 5-season adoption comparison as plan 09-07: `wf_rl_v2_adopt_seed{0,1,2}` vs the recorded 5-season figures (chips_v2 2192, v1 baseline 2272). Judged on pure realised points; record the verdict with numbers as an IMPROVEMENTS.md Phase F addendum per D-08. Check the anti-Pitfall-4 curve (training reward vs held-out score) in the training logs before trusting any gain.
