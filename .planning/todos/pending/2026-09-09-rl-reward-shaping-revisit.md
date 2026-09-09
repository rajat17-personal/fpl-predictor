---
created: 2026-09-09T05:14:14.086Z
title: RL revisit — potential-based team-value shaping and a real training budget
area: optimize
severity: minor
files:
  - optimize/rl_env.py:247-259
  - optimize/rl_train.py
  - IMPROVEMENTS.md
---

## Problem

Phase 9's rl_strategy used a deliberately pure reward (realised GW points − 4×hits, proven equal to run_season's total within 1e-6) and was rejected (seed-mean 2020 vs solver's 2192). Diagnosis in IMPROVEMENTS.md: the policy trained only 5-14k timesteps inside the 30-min box — far too few for a 40-action space — not reward misdesign. User asks whether shaping terms from the referenced FPL-RL project (week-average baseline, team-value bonus) should be added, since higher team value buys future transfer freedom.

## Solution

If RL is ever revisited, the honest version of the user's instinct is:
1. Week-average baseline: action-independent, so it cannot change the optimal policy — PPO's own value-function baseline already serves this variance-reduction role. Skip.
2. Team value: a raw additive bonus (referenced project's +0.05×Δvalue) biases the objective toward price-chasing — part of why that project's 2,918 was optimistic. If shaping is wanted, use POTENTIAL-BASED shaping (reward += γ·Φ(s′) − Φ(s), Φ = small weight × team value): provably preserves the optimal policy (Ng et al. 1999) while giving intermediate signal; net points keep weight 1.
3. The binding constraint was budget: any re-run needs a much larger declared time-box (hours per policy, larger timestep count) declared before training per D-16.
Adoption judgment stays on pure realised points via the honest harness, never on the shaped reward. Low priority: five other leads rank ahead of RL on measured promise.
