---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 05
subsystem: ml-experimentation
tags: [dixon-coles, team-strength, walk-forward, horizon-leakage, adoption-decision]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, backtest/walk_forward.py --experiments/--seasons/--tag CLI, the tracked 6-season baseline in IMPROVEMENTS.md Phase F); plan 09-04's chip scheduler verdict (rejected, flag off) as the current-default configuration this plan's A/B is judged against"
provides:
  - "data/team_strength.py -- expanding-window Dixon-Coles team attack/defence ratings, keyed on numeric (season, team_id), covering every season including 2016-19 where the odds join is null"
  - "config.TEAM_STRENGTH_COLS (8 ts_* names) -- computed unconditionally in data/build_table.py/features/engineer.py; the EXPERIMENTS['team_strength'] gate lives at feature-selection time in backtest/walk_forward.py, never a pipeline rebuild"
  - "backtest/walk_forward.py's leakage_safe_plan() decision-time team-strength graft: future fixture's opponent IDENTITY carried forward via FIXTURE_CTX, but ts_* values re-derived from ratings_as_of(season, g) -- the decision gameweek's own ratings, never the future gameweek's"
  - "backtest/walk_forward.py --optimistic-plan / multi_optimistic -- the honest-vs-flattering horizon A/B every horizon-touching change must now report (D-06)"
  - "D-07 adoption verdict for team_strength: REJECTED (model+chips -2/season, multi_safe -12/season), flag off, code merged"
affects: [09-10]

actuals:
  tokens: 10160
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Numeric (season, team_id) reconstruction from the two distinct opponent_team_id values within a fixture, never the team NAME column -- the pattern any future enrichment source needing pre-2020 coverage should copy (the name column is 0% populated 2016-19)"
    - "L2-ridge-regularized MLE for a per-gameweek expanding-window fit: an unregularized fit at the minimum-data floor diverges (42 params over 20 matches is underdetermined); shrinkage toward zero degrades gracefully instead"
    - "Decision-time-vs-future-row horizon graft: carry FORWARD only what is genuinely knowable ahead (fixture schedule, opponent identity) and re-derive anything model-fit (ratings) from the decision gameweek's own snapshot -- the same discipline leakage_safe_plan already used for fdr_self/was_home, now made explicit for a value that looks knowable-ahead but isn't"

key-files:
  created:
    - data/team_strength.py
  modified:
    - config.py
    - data/build_table.py
    - features/engineer.py
    - backtest/walk_forward.py
    - tests/test_leakage.py
    - IMPROVEMENTS.md

key-decisions:
  - "Relaxed build_matches()'s two-sides/380-fixtures assertion from an exact match to a tolerant floor (>=370/380) after discovering one genuine vaastav data gap: a 2019-20 COVID-rescheduled fixture (season 2019-20, fixture_id 275) whose non-scoring side never received a backfilled row for the replayed gameweek, so it loses one of its two sides once rows without a recorded score are dropped. A systemic failure (season count far below 370) still raises; this one-off gap is logged and skipped."
  - "Added an L2 ridge shrinkage (RIDGE=0.1) to the Dixon-Coles fit after an unregularized BFGS run diverged at the MIN_MATCHES=20 floor (|attack|>1e3, rho>1e9, exp() overflow to inf/nan) -- a 42-parameter fit over 20 matches (40 goal observations) is hopelessly underdetermined without it. Switched to L-BFGS-B with bounds as a second stabilizer."
  - "team_strength REJECTED per D-07's mechanical rule applied against the plan 09-01 baseline: the adoption-deciding run measured model+chips -2/season (2262->2260, not an improvement) and multi_safe -12/season (2147->2135, a regression, not a hold). config.EXPERIMENTS['team_strength'] stays False; all code stays merged behind the flag (D-08)."

requirements-completed: []

coverage:
  - id: D1
    description: "Expanding-window Dixon-Coles ratings (data/team_strength.py) covering every season including 2016-19, reproducible from a truncated match history"
    verification:
      - kind: integration
        ref: "python -m data.team_strength (team_strength.parquet: 7,580 rows, one per (season, gw, team_id), 10 seasons incl. 2016-17..2019-20, zero NaN/inf)"
        status: pass
      - kind: unit
        ref: "tests/test_leakage.py#test_team_strength_ratings_reproducible_from_prior_matches"
        status: pass
    human_judgment: false
  - id: D2
    description: "Ratings joined into the canonical pipeline as ordinary feature columns, computed unconditionally, row-count-preserving"
    verification:
      - kind: integration
        ref: "python -m data.build_table && python -m features.engineer (player_gw.parquet 253,509 rows unchanged; features.parquet 101 features, 100% ts_* coverage incl. 2016-19)"
        status: pass
      - kind: unit
        ref: "tests/test_leakage.py -q (4 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Decision-time horizon graft (no ts_* leak via FIXTURE_CTX), optimistic-vs-frozen A/B (--optimistic-plan), and the D-07 adoption verdict"
    verification:
      - kind: other
        ref: "python -c assertion: no ts_* column in backtest.walk_forward.FIXTURE_CTX"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2024-25,2025-26 --replicas 1 --experiments team_strength --optimistic-plan --tag ts_fast (wf_ts_fast.json: multi_safe 2100, multi_optimistic 2437, gap +337, optimistic >= safe)"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --experiments team_strength --optimistic-plan --tag team_strength_adopt (6 seasons, 5 replicas: model+chips 2262->2260, multi_safe 2147->2135; config.EXPERIMENTS['team_strength'] confirmed False, consistent with the regression)"
        status: pass
      - kind: other
        ref: "IMPROVEMENTS.md team_strength row: no 'pending' cell, optimistic/frozen numbers recorded"
        status: pass
      - kind: other
        ref: "python -m pytest -q (199 passed, 1 skipped) and ruff check . both green"
        status: pass
    human_judgment: false

duration: 33min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 5: Team-Strength Dixon-Coles Ratings Summary

**Built expanding-window Dixon-Coles team attack/defence ratings that cover every season including the 2016-19 odds gap, wired a leakage-safe decision-time horizon graft that reproduces the project's own +337-vs-honest multi-GW trap on purpose, and REJECTED the experiment at adoption: model+chips -2/season, multi_safe -12/season against the plan 09-01 baseline.**

## Performance

- **Duration:** 33 min
- **Started:** 2026-09-08T13:38:47Z (approx., continuing from plan 09-04's close-out)
- **Completed:** 2026-09-08T14:11:28Z
- **Tasks:** 3
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- **`data/team_strength.py`** (new) — `build_matches()` collapses the player-fixture
  table to one row per `(season, fixture_id)`, reconstructing each side's numeric
  team id from the two distinct `opponent_team_id` values within it (the `team`
  name column, the odds join key, is 0% populated 2016-17 through 2019-20, so a
  name-keyed table would inherit exactly the same hole). `dc_log_likelihood()` is
  the pure Dixon-Coles negative log-likelihood (Dixon and Coles 1997, low-score
  tau correction on the 0-0/1-0/0-1/1-1 scorelines); `fit_ratings_as_of()` fits it
  via `scipy.optimize.minimize` with an L2 ridge shrinkage and parameter bounds
  (needed — see Deviations) on matches strictly before the target gameweek.
  `build()` walks every season's gameweeks in order, emitting one row per
  `(season, gw, team_id)` (neutral zero ratings below 20 prior matches).
  `ratings_as_of()` and `attach()` are the accessor/join surface. No `lightgbm`
  import; the module docstring states the feature-only, no-decomposition
  constraint explicitly.
- **`tests/test_leakage.py`** gained
  `test_team_strength_ratings_reproducible_from_prior_matches`: independently
  rebuilds the match table, refits 2022-23 GW20's ratings from `gw < 20` matches
  only, and reproduces the stored parquet row (`atol=1e-4`, the optimizer's own
  noise floor is ~1e-6); a second assertion confirms one row per
  `(season, gw, team_id)`, not per `(season, team_id)` — Pitfall 2's own warning
  sign made executable.
- **Pipeline join**: `config.TEAM_STRENGTH_COLS` (8 `ts_*` names) declared next to
  `ODDS_COLS`/`FBREF_COLS`; `data/build_table.py` gained a guarded
  `ts_mod.attach()` join immediately after the fbref block (`[team_strength]`
  print tag both paths); `features/engineer.py::CONTEXT_COLS` includes the
  columns unconditionally (a comment explains why: the flag gate lives in the
  harness, not here). Rebuilt end to end: `player_gw.parquet` stayed at
  **253,509 rows** (unchanged), `features.parquet` gained 8 columns at **100%
  coverage on every season including 2016-19** (vs `odds_pwin`'s 64.3%, 0% for
  2016-19).
- **Decision-time horizon graft**: `backtest/walk_forward.py::FIXTURE_CTX` gained
  `opponent_team_id` (knowable ahead — on the published fixture list) but no
  `ts_*` name (verified). `leakage_safe_plan()` now takes `team_strength: bool`;
  when on, `_graft_team_strength_ratings()` re-derives
  `ts_attack_opp`/`ts_defence_opp`/`ts_xg_for`/`ts_xg_against`/`ts_pwin`/`ts_pcs`
  from `team_strength.ratings_as_of(season, g)` — the ratings as of the
  **decision gameweek g**, crossed with the future fixture's opponent identity —
  never the future gameweek's own (leaky) rating row. Self-side ratings need no
  change: the frozen form row's `ts_attack_self`/`ts_defence_self` were already
  fit as-of `g`.
- **Optimistic-vs-frozen A/B (D-06)**: `--optimistic-plan` added; every tagged run
  can now report `multi_optimistic` (the pre-existing `_plan_col`, which peeks at
  future gameweeks' own predictions) beside the honest `multi_safe`. Fast A/B
  (2 seasons, 1 replica, `team_strength` on): `multi_safe` 2100 vs
  `multi_optimistic` 2437, **gap +337** — landing in the same neighbourhood as
  the project's own previously-documented +337-optimistic-vs-+40-honest
  multi-GW leakage finding, reproduced here on purpose.
- **Adoption verdict**: full-replica run (6 seasons, 5 replicas,
  `wf_team_strength_adopt.json`) against the plan 09-01 baseline
  (`wf_baseline_phase9.json`): `model+chips` **2262 → 2260** (−2/season, not an
  improvement), `multi_safe` **2147 → 2135** (−12/season, a regression). Both
  D-07 conditions fail. **REJECTED** — `config.EXPERIMENTS['team_strength']`
  stays `False` (already the default; no flip, so `tests/test_experiments.py`
  needed no change). All code stays merged behind the flag (D-08).

## Task Commits

Each task was committed atomically:

1. **Task 1: Expanding-window Dixon-Coles ratings and the leakage assertion D-06 demands** - `484d9f7` (feat)
2. **Task 2: Declare the columns, join them into the canonical table, and rebuild the pipeline** - `e7e6508` (feat)
3. **Task 3: Decision-time horizon graft, the optimistic-versus-frozen A/B, and the verdict** - `6d2075b` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `data/team_strength.py` (new) - `build_matches()`, `dc_log_likelihood()`, `fit_ratings_as_of()`, `build()`, `ratings_as_of()`, `attach()`
- `config.py` - `TEAM_STRENGTH_COLS` (8 `ts_*` names)
- `data/build_table.py` - guarded `team_strength` join after the fbref block
- `features/engineer.py` - `CONTEXT_COLS` includes `TEAM_STRENGTH_COLS` unconditionally
- `backtest/walk_forward.py` - `FIXTURE_CTX` gains `opponent_team_id`; `_attach_opponent_id()`, `_graft_team_strength_ratings()`, `leakage_safe_plan(team_strength=)`, `--optimistic-plan`/`multi_optimistic`
- `tests/test_leakage.py` - `test_team_strength_ratings_reproducible_from_prior_matches`
- `IMPROVEMENTS.md` - `team_strength` Phase F row and results sub-section filled (no pending cells)

## Decisions Made

- Relaxed `build_matches()`'s two-sides/380-fixtures check from an exact match to
  a tolerant floor (raise below 370/380, warn-and-continue between 370-379) after
  discovering one genuine vaastav data gap (2019-20 fixture 275, a COVID
  reschedule whose non-scoring side never got backfilled for the replayed
  gameweek) — a systemic failure still raises; this one-off gap is logged and
  the fixture dropped from the match table used to fit ratings only (it never
  touches `player_gw.parquet`/`features.parquet` row counts).
- Added L2 ridge shrinkage + parameter bounds to the Dixon-Coles fit (see
  Deviations) after an unregularized fit diverged at the minimum-data floor.
- `team_strength` REJECTED per D-07's mechanical rule, applied against the
  plan 09-01 baseline exactly as plans 09-03/09-04 applied it: neither
  condition (model+chips improves, multi_safe holds) is met.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Unregularized Dixon-Coles fit diverged at the minimum-match floor**
- **Found during:** Task 1's own verify run (`python -m data.team_strength`)
- **Issue:** An unregularized BFGS fit of the 42-parameter model (20 teams x 2 +
  home_adv + rho) over the `MIN_MATCHES=20` floor (40 goal observations) is
  hopelessly underdetermined. It produced `RuntimeWarning: overflow encountered
  in exp` and diverged to `|attack|>1e3`, `home_adv=-3568`, `rho=1.69e10` for
  several early-season gameweeks — numerically broken ratings that would have
  fed `inf`/garbage values into the model as features.
- **Fix:** Added an L2 ridge shrinkage term (`RIDGE=0.1`, applied only inside
  `fit_ratings_as_of`'s wrapper objective, never inside the canonical
  `dc_log_likelihood`) and switched from unbounded `BFGS` to bounded `L-BFGS-B`
  (attack/defence in `[-3, 3]`, home_adv in `[-2, 2]`, rho in `[-0.9, 0.9]`).
- **Files modified:** `data/team_strength.py`
- **Verification:** Re-ran `python -m data.team_strength` — zero warnings, zero
  NaN/inf in the output parquet, attack/defence in a realistic `[-3, 2.6]` range
  (sd ~0.4); the leakage-reproduction test still passes at a tight tolerance.
- **Committed in:** `484d9f7` (Task 1 commit)

**2. [Rule 1 - Bug] `build_matches()`'s exact-380-fixtures assertion crashed on a real one-off vaastav data gap**
- **Found during:** Task 1's own verify run
- **Issue:** A hard `nsides != 2` / `count != 380` assertion (as literally worded
  in the plan) raised on a genuine 2019-20 COVID-rescheduled fixture (fixture_id
  275) whose non-scoring side's players never received a backfilled row for the
  replayed gameweek — after requiring a recorded score, only 1 of that fixture's
  ~59 player-rows survives, leaving a single `opponent_team_id` value instead of
  two. This is a known, tiny (1 of 3,800 fixtures) data-quality artifact, not a
  systemic reconstruction failure.
- **Fix:** Relaxed the assertion to drop individually-unrecoverable fixtures
  (logged by name) while still raising if a season loses more than a handful
  (`< 370/380`, i.e. a "half a league" scale problem) — preserving the plan's own
  stated intent ("raise... rather than silently yielding half a league") without
  crashing on a single legitimate anomaly.
- **Files modified:** `data/team_strength.py`
- **Verification:** `python -m data.team_strength` completes, prints the one
  dropped fixture by name, and every season still reaches its full (379 or 380)
  fixture count; the 380-fixtures-per-season acceptance criterion is otherwise
  met for the other 9 seasons.
- **Committed in:** `484d9f7` (Task 1 commit)

**3. [Rule 3 - Blocking] Leakage-reproduction test's initial `atol=1e-6` was tighter than the optimizer's own convergence noise floor**
- **Found during:** Task 1's own verify run (`pytest tests/test_leakage.py`)
- **Issue:** Re-running the identical fit twice (once inside `build()`, once
  independently in the test) produced values differing by up to ~1.5e-6 due to
  BLAS thread-count-dependent floating-point reduction order inside
  `scipy.optimize.minimize` — genuine optimizer noise, not a leakage bug, but
  the test's `atol=1e-6` was tighter than that noise floor and failed.
- **Fix:** Loosened to `atol=1e-4` — still >10x tighter than the observed noise
  and >1000x tighter than the attack/defence scale (sd ~0.4), so a real leakage
  bug (fitting on the whole season, or on a future match) would still be caught.
- **Files modified:** `tests/test_leakage.py`
- **Verification:** `pytest tests/test_leakage.py -q` — 4 passed.
- **Committed in:** `484d9f7` (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All three fixes were necessary for the module to produce
correct, usable ratings at all (numerical stability) or for its own stated
verification to run on real data (the one-off data gap and the tolerance fix).
No scope creep — every fix stayed inside `data/team_strength.py` or its own new
test.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Experiment 4 (team-strength ratings) is fully closed: measured, decided
  REJECTED, with both the leakage-safety evidence (D-06's own stated bar for
  this option) and the model+chips/multi_safe adoption numbers recorded.
- The optimistic-vs-frozen A/B (`--optimistic-plan`/`multi_optimistic`) is now
  a permanent harness capability any future horizon-touching plan (RL strategy,
  09-06 onward) can reuse without re-deriving it.
- `predict/live.py` and `predict/export.py` remain untouched — the weekly
  product surface is unaffected, matching this plan's own success criteria.
- Plan 09-10 (results table finalization) has the `team_strength` row ready
  with no `pending` cells remaining.
- No blockers.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (data/team_strength.py, config.py, data/build_table.py,
features/engineer.py, backtest/walk_forward.py, tests/test_leakage.py,
IMPROVEMENTS.md) exist on disk with the expected changes; all three task
commits (484d9f7, e7e6508, 6d2075b) found in `git log`; full pytest suite
(199 passed, 1 skipped) and `ruff check .` both green after the final commit;
`config.EXPERIMENTS['team_strength']` confirmed `False`, consistent with the
measured regression; `data/processed/team_strength.parquet`,
`data/processed/experiments/wf_ts_fast.json`, and
`data/processed/experiments/wf_team_strength_adopt.json` all present with the
expected shape (7,580 / — / 6-season-5-replica respectively).
