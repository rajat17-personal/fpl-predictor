---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 06
subsystem: ml-experimentation
tags: [reinforcement-learning, gymnasium, sb3-contrib, torch, package-legitimacy, dependency-isolation]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, backtest/walk_forward.py --experiments/--seasons/--tag CLI, tracked 6-season baseline); plan 09-04's chip scheduler v2 verdict (rejected, v1 causal_schedule stays shipped default) as the heuristic baseline the RL policy will compete against in plan 09-07"
provides:
  - "requirements-rl.in/.txt -- dev-only, hash-locked RL dependency stack (torch 2.12.0, gymnasium 1.3.0, stable-baselines3 2.9.0, sb3-contrib 2.9.0), D-12-approved, D-09-isolated (grep + parser assertion prove zero reference in Dockerfile/.github/workflows/)"
  - "optimize/rl_env.py::FplStrategyEnv -- Gymnasium environment with a fixed 40-action (chip x transfer-count) space, action_masks() for MaskablePPO, and a realised-points-net-of-hits reward computed by directly reusing backtest.season's own scoring helpers"
  - "tests/test_rl_env.py -- 6 tests including the anti-Pitfall-4 reward-equivalence proof against backtest.season.run_season"
affects: [09-07]

actuals:
  tokens: 11030
  tasks: 3
  commits: 2

tech-stack:
  added: ["torch==2.12.0 (dev-only)", "gymnasium==1.3.0 (dev-only)", "stable-baselines3==2.9.0 (dev-only)", "sb3-contrib==2.9.0 (dev-only)"]
  patterns:
    - "Dev-only lockfile isolation: a standalone requirements-rl.in (not `-r requirements.in`-composed) compiled with `-c requirements.txt` for shared-pin consistency, proven never-referenced by Dockerfile/.github/workflows/ via grep + a parser assertion, rather than merely documented as unused"
    - "Realised-points RL reward: optimize/rl_env.py imports backtest.season's private scoring helpers (_score/_pad_holdings/_squad_from_pick/_team_value/_update_meta) directly instead of reimplementing autosub/captain-multiplier logic, so the RL reward and the honest walk-forward harness's score can never drift apart"
    - "Fixed-cardinality action space independent of player pool size: Discrete(len(CHIPS_ORDER) * len(TRANSFER_CAPS))=40, decoded via divmod -- never player identity (D-02's hybrid split, ILP stays the un-learned selection step)"

key-files:
  created:
    - requirements-rl.in
    - requirements-rl.txt
    - optimize/rl_env.py
    - tests/test_rl_env.py
  modified: []

key-decisions:
  - "Human approved all four RL packages at their proposed pins verbatim: \"Approve all four (Recommended)\" -- torch==2.12.0, gymnasium==1.3.0, stable-baselines3==2.9.0, sb3-contrib==2.9.0. Live PyPI re-verification at execution time found zero drift from 09-RESEARCH.md's audit (same version ladders, same pins available); torch pinned to 2.12.0 (not the newest 2.14.0) deliberately, reusing the build already proven with CUDA in this conda env"
  - "Chose the reward-equivalence test's 'equivalent configuration' as a full-season hold policy (chip='-', max_transfers=0 every gameweek) rather than trying to inject a custom per-gameweek chip schedule into run_season, which has no such injection point (its schedule is always internally computed by optimize.chips). This keeps the anti-Pitfall-4 proof fully deterministic and exercises the real _score/_pad_holdings/_team_value chain end-to-end without needing to fork run_season's signature"
  - "Observation's horizon xP signal uses each squad player's OWN current-gameweek xp_med, decay-forward-weighted only by whether the player has ANY row in gw+k (public fixture-schedule knowledge, never a future prediction or outcome) -- deliberately lighter-weight than backtest/walk_forward.py::leakage_safe_plan's full model-reprediction machinery (which needs the trained LightGBM model + per-fixture feature columns not present in the frozen test_predictions.parquet this environment reads), while preserving the same no-future-outcome, no-future-prediction leakage-safety guarantee"

patterns-established:
  - "Isolation is proven, never merely asserted: a dev-only lockfile's non-reachability from production install paths is checked by grep -F over the exact file list plus a parser assertion on every pip-install line, matching D-09's own instruction not to even add a warning comment naming the lockfile (which would satisfy a naive grep and neuter the guard)"

requirements-completed: []

coverage:
  - id: D1
    description: "Package-legitimacy gate for the four new RL packages (D-12): live PyPI re-verification, human decision recorded verbatim"
    verification:
      - kind: other
        ref: "live re-verification, this session: pip index versions {torch,gymnasium,stable-baselines3,sb3-contrib} + PyPI JSON project_urls/release-count cross-check, zero drift from 09-RESEARCH.md"
        status: pass
    human_judgment: true
    rationale: "D-12 requires this checkpoint to be a genuine human decision, never auto-approved -- gate=blocking-human by design. The decision itself (\"Approve all four (Recommended)\") is recorded here and in STATE.md, but the checkpoint's purpose (independent human judgment on supply-chain trust) is not something a passing test can stand in for."
  - id: D2
    description: "Dev-only hash-locked RL lockfile (requirements-rl.in/.txt), proven unreachable from every production install path"
    verification:
      - kind: other
        ref: "grep -rn -F 'requirements-rl' Dockerfile .github/workflows/ ; test $? -eq 1 -- zero matches"
        status: pass
      - kind: other
        ref: "python parser assertion: every pip-install line in Dockerfile/ci.yml/daily.yml/weekly.yml names only requirements.txt or requirements-dev.txt"
        status: pass
      - kind: other
        ref: "python -c 'import torch, gymnasium, stable_baselines3, sb3_contrib; torch.cuda.is_available()' -- all four import, CUDA True, versions match approved pins exactly"
        status: pass
      - kind: unit
        ref: "python -m pytest -q -- 199 passed, 1 skipped (pre-existing suite unperturbed by the install)"
        status: pass
    human_judgment: false
  - id: D3
    description: "optimize/rl_env.py::FplStrategyEnv -- masked chip/transfer-count action space, realised-points reward reusing backtest.season's scoring"
    verification:
      - kind: unit
        ref: "tests/test_rl_env.py#test_reset_returns_valid_observation"
        status: pass
      - kind: unit
        ref: "tests/test_rl_env.py#test_action_masks_marks_used_chip_illegal_after_use"
        status: pass
      - kind: unit
        ref: "tests/test_rl_env.py#test_action_masks_masks_transfer_above_budget"
        status: pass
      - kind: unit
        ref: "tests/test_rl_env.py#test_action_space_one_dim_and_bounded"
        status: pass
      - kind: unit
        ref: "tests/test_rl_env.py#test_reset_seed_reproducible"
        status: pass
      - kind: unit
        ref: "tests/test_rl_env.py#test_reward_matches_run_season_hold_policy (anti-Pitfall-4: cumulative env reward == run_season total for an equivalent hold-policy config, within 1e-6)"
        status: pass
      - kind: other
        ref: "python -m pytest -q -- 205 passed, 1 skipped (199 pre-existing + 6 new); ruff check . green"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 6: RL Environment Stand-Up -- Dependency Isolation + Realised-Points Gymnasium Env Summary

**Approved and installed a D-09-isolated, D-12-gated RL dependency stack (torch 2.12.0 + gymnasium 1.3.0 + stable-baselines3/sb3-contrib 2.9.0), then built `optimize/rl_env.py::FplStrategyEnv` -- a masked-action Gymnasium environment whose reward is proven, not asserted, to equal `backtest.season.run_season`'s own realised-points scoring for an equivalent configuration.**

## Performance

- **Duration:** 30 min (active work; excludes the human checkpoint wait)
- **Started:** 2026-09-08T14:20:00Z (approx.)
- **Completed:** 2026-09-08T14:50:04Z
- **Tasks:** 3 (1 checkpoint, 2 auto)
- **Files modified:** 4 (4 created, 0 modified)

## Accomplishments

- **Task 1 (checkpoint:human-verify, gate=blocking-human):** Live-re-verified all four proposed RL packages against the PyPI registry at execution time (per Phase 05's precedent of never trusting stale research) -- `pip index versions` for torch/gymnasium/stable-baselines3/sb3-contrib plus a PyPI JSON pull of each package's `project_urls` and release count, confirming zero drift from 09-RESEARCH.md's audit and adding independent cross-verification (torch: 50 releases back to 1.0.0, declared source pytorch.org; gymnasium: 20 releases back to 0.0.1, Farama Foundation; stable-baselines3: 115 releases back to 0.6.0a1, DLR-RM; sb3-contrib: 79 releases back to 0.10.0a0, same maintaining org). Human replied **verbatim: "Approve all four (Recommended)"** -- torch==2.12.0, gymnasium==1.3.0, stable-baselines3==2.9.0, sb3-contrib==2.9.0.
- **Task 2:** Wrote `requirements-rl.in` (standalone, not `-r requirements.in`-composed, per D-09) with the four approved pins and a header explaining the dev-only/never-in-production rule. Compiled `requirements-rl.txt` with `uv pip compile --generate-hashes --python-version 3.14 -c requirements.txt`, matching the house lockfile banner. Installed with `pip install --require-hashes -r requirements-rl.txt` into the `python314` conda env -- all four import successfully, `torch.cuda.is_available()` remains `True`. **Proved** (not merely asserted) D-09 isolation: `grep -rn -F 'requirements-rl' Dockerfile .github/workflows/` returns nothing, and a parser assertion over every `pip install` line in `Dockerfile`/`ci.yml`/`daily.yml`/`weekly.yml` confirms each names only `requirements.txt`/`requirements-dev.txt`. `git diff` confirms all four production files are byte-identical to before this plan. Full pre-existing pytest suite (199 passed, 1 skipped) stayed green after the install; no `ruff.toml` change needed.
- **Task 3:** Built `optimize/rl_env.py::FplStrategyEnv`, a `gymnasium.Env` stepping one season one gameweek at a time. Action space is a fixed `Discrete(40)` over `(chip choice x transfer count)` -- `CHIPS_ORDER=("-","wc","fh","bb","tc")` x `TRANSFER_CAPS=(0..7)` -- decoded via `divmod` and passed straight into `optimize.squad_ilp.pick_squad`/`optimize.transfers.optimize_gw`, the un-learned player-selection step (D-02's hybrid split; the action space never scales with pool size and stays under 200 by construction). `action_masks()` excludes an already-used chip in the current half, a transfer count above `free_transfers + HIT_BUDGET(2)`, and redundant transfer-count pairings with a full-squad-rebuild chip (wc/fh only keep their canonical `transfer_cap=0` slot). The reward is realised points net of hits, computed by calling `backtest.season`'s own private scoring helpers (`_score`, `_pad_holdings`, `_squad_from_pick`, `_team_value`, `_update_meta`) directly -- never reimplemented, never xP even as a shaping term. `tests/test_rl_env.py` (6 tests, none training anything): reset-observation validity, chip-use masking, transfer-budget masking, action-space shape/size, seed(7) reproducibility, and the anti-Pitfall-4 test proving a full-season hold-policy run through the environment sums to exactly `run_season`'s total for the equivalent configuration (within 1e-6). `config.EXPERIMENTS['rl_strategy']` remains `False`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Package-legitimacy gate (checkpoint, no code changes)** - no commit (nothing installed until approved; the verbatim decision is recorded here and in STATE.md, per the task's own acceptance criteria)
2. **Task 2: Dev-only hash-locked RL lockfile that cannot reach production** - `af867f6` (feat)
3. **Task 3: Gymnasium environment with masked actions and a realised-points reward** - `c66fe20` (feat)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `requirements-rl.in` (new) - the four approved RL packages at their approved pins, dev-only header
- `requirements-rl.txt` (new) - uv-compiled, hash-locked, `-c requirements.txt`-constrained
- `optimize/rl_env.py` (new) - `FplStrategyEnv(gymnasium.Env)`: `reset()`, `step()`, `action_masks()`, `_observe()`
- `tests/test_rl_env.py` (new) - 6 tests, including the anti-Pitfall-4 reward-equivalence proof

## Decisions Made

- Human approved all four RL packages verbatim: **"Approve all four (Recommended)"** (torch==2.12.0, gymnasium==1.3.0, stable-baselines3==2.9.0, sb3-contrib==2.9.0). Live registry re-verification found zero drift; torch pinned below the newest 2.14.0 release deliberately, reusing the already-proven CUDA-enabled build in this conda environment.
- The anti-Pitfall-4 reward-equivalence test uses a full-season hold policy (`chip="-"`, `max_transfers=0` every gameweek) as its "equivalent configuration" rather than trying to inject a custom per-gameweek schedule into `run_season` (which has no such injection point -- its schedule is always internally computed by `optimize.chips`). This keeps the proof fully deterministic while still exercising the real `_score`/`_pad_holdings`/`_team_value` chain end-to-end.
- The observation's horizon xP signal is a lighter-weight, deliberately simplified stand-in for `backtest/walk_forward.py::leakage_safe_plan`'s full model-reprediction machinery: it decay-forward-weights each squad player's OWN current-gameweek `xp_med` by whether they have any row in a future gameweek (public fixture-schedule knowledge, never a prediction or outcome), because the full `leakage_safe_plan` construction needs the trained LightGBM model plus per-fixture feature columns that the frozen `test_predictions.parquet` this environment reads does not retain. The no-future-outcome, no-future-prediction leakage-safety guarantee is preserved; the fidelity of the multi-GW plan signal itself is intentionally minimal for this stand-up plan and can be revisited in a later plan if training in 09-07 shows the policy needs a richer horizon feature.

## Deviations from Plan

None - plan executed exactly as written, including the checkpoint gate.

## Issues Encountered

- `pip install --require-hashes -r requirements-rl.txt` restored `numpy` from an ad-hoc `2.4.4` (installed outside any tracked lockfile, likely by an unrelated tool like `numba`) back up to `2.5.2` -- the exact version `requirements.txt` already pins. This is not drift: `requirements.txt`'s own lock already specifies `numpy==2.5.2`, so the RL install's `-c requirements.txt` constraint correctly enforced the existing production pin rather than introducing a new one. Pip additionally warned about pre-existing, lockfile-untracked conflicts (`datasets`, `numba`, `seleniumbase` vs `setuptools`/`fsspec`) -- none of those three packages appear in any tracked `requirements*.in`/`.txt` file, so they are ad-hoc dev-machine installs outside this project's lockfile discipline, not a production-path concern. Verified harmless: the full pytest suite (199 -> 205 after Task 3's additions) and `ruff check .` both stayed green after the install.

## User Setup Required

None - no external service configuration required. The RL stack is installed manually in the developer's own `python314` conda environment per D-09; it is never installed by CI or the Docker image.

## Next Phase Readiness

- `optimize/rl_env.py::FplStrategyEnv` and its hash-locked dependency stack are ready for plan 09-07's time-boxed `MaskablePPO` training run and D-02 comparison against the v1 heuristic chip scheduler.
- The RL stack stays fully isolated from the weekly product: `Dockerfile` and every `.github/workflows/*.yml` are byte-identical to before this plan (git-diff-confirmed), and `config.EXPERIMENTS['rl_strategy']` stays `False`.
- No blockers.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (requirements-rl.in, requirements-rl.txt, optimize/rl_env.py, tests/test_rl_env.py) exist on disk; both task commits (af867f6, c66fe20) found in `git log`; full pytest suite (205 passed, 1 skipped) and `ruff check .` both green after the final commit; `git diff` confirms Dockerfile/ci.yml/daily.yml/weekly.yml unchanged; `config.EXPERIMENTS['rl_strategy']` confirmed `False`; grep + parser isolation proof over Dockerfile/.github/workflows/ confirmed zero references to the RL lockfile.
