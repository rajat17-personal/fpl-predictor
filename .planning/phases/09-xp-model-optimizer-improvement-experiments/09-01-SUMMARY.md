---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 01
subsystem: ml-experimentation
tags: [experiment-flags, config, lightgbm, walk-forward, captaincy, intervals, backtest]

requires:
  - phase: 06-security-reliability-observability-hardening
    provides: ops.jsonio as the single JSON I/O chokepoint (write_json used by the new wf_<tag>.json artifacts)
provides:
  - "config.EXPERIMENTS eight-key flag registry (all default-off) + config.resolve_experiments()"
  - "backtest/walk_forward.py --experiments/--seasons/--tag CLI options, season-subset fast iteration, tagged JSON/CSV run artifacts"
  - "models/captaincy.py: leakage-safe captaincy ceiling-EV column (xp_capt_ceiling), the first experiment riding the new seam"
  - "scripts/experiment_run.sh unattended harness launcher (D-15)"
  - "The re-measured, tracked 6-season baseline (model+chips 2262) every later experiment in this phase is judged against"
affects: [09-02, 09-03, 09-04, 09-05, 09-06, 09-07, 09-08, 09-09, 09-10]

actuals:
  tokens: 6104
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Experiment flags: one ALL_CAPS-style registry key in config.EXPERIMENTS + one branch in backtest/walk_forward.py::main, every default off"
    - "Tagged run artifacts under gitignored data/processed/experiments/ (wf_<tag>.csv + .json), written via ops.jsonio.write_json"
    - "Post-hoc, no-retrain enrichment columns (models/captaincy.py mirrors models/intervals.py's apply_intervals discipline)"

key-files:
  created:
    - models/captaincy.py
    - scripts/experiment_run.sh
    - tests/test_experiments.py
  modified:
    - config.py
    - backtest/walk_forward.py
    - IMPROVEMENTS.md

key-decisions:
  - "captaincy ceiling artifact is refit per test season on the immediately-prior validation season (not the shipped 2025-26 intervals.json), because reusing the shipped artifact would leak 2025-26 residuals into an earlier test season's captaincy decision"
  - "pandas ddof=1 std over a single-season Series is NaN -- guarded to 0.0 for n=1 rather than crashing int(), since --seasons now makes single-season runs a first-class path (D-14)"
  - "the measured 2262 model+chips baseline (not either inherited ~2,256/~2,263 estimate) is the number this phase's D-05 >=2,280 bar is judged against"

requirements-completed: []

coverage:
  - id: D1
    description: "Experiment flag registry (config.EXPERIMENTS/resolve_experiments) with every flag defaulted off"
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_experiments_registry_default_off"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_experiments_none_spec_no_env_matches_default"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_experiments_single_flag_leaves_registry_unmutated"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_experiments_multi_flag_with_space"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_experiments_none_token_is_all_off"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_experiments_all_token_is_all_on"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_resolve_experiments_bogus_token_raises"
        status: pass
    human_judgment: false
  - id: D2
    description: "Season/flag/tag-aware backtest/walk_forward.py CLI that reproduces the pre-phase baseline unflagged and changes captaincy outcome when capt_ceiling is on"
    verification:
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag t1base (model+chips=2172, matches recorded 2025-26 baseline exactly)"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --experiments capt_ceiling --tag t1ceil (capt_capture 0.595 -> 0.619)"
        status: pass
    human_judgment: false
  - id: D3
    description: "models/captaincy.py xp_capt_ceiling column, leakage-safe fit on the prior validation season, no retraining"
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_add_ceiling_ev_matches_formula_row_by_row"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_add_ceiling_ev_lam_zero_reproduces_xp_mean"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_fit_ceiling_artifact_shape"
        status: pass
    human_judgment: false
  - id: D4
    description: "Unattended-run launcher (scripts/experiment_run.sh) for long harness runs (D-15)"
    verification:
      - kind: other
        ref: "bash -n scripts/experiment_run.sh; bash scripts/experiment_run.sh smoke --seasons 2025-26 --replicas 1 (returned in <1s, log carried [wf] tag=smoke)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Re-measured, tracked 6-season baseline (all flags off) opening the Phase F results ledger in IMPROVEMENTS.md"
    verification:
      - kind: integration
        ref: "scripts/experiment_run.sh baseline_phase9 -> data/processed/experiments/wf_baseline_phase9.json (replicas=5, 6 seasons, all flags false, model+chips=2262)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 1: Experiment Spine + Captaincy Ceiling EV Tracer Summary

**Built the eight-key experiment flag registry, a season/tag-aware walk-forward CLI, and rode the cheapest real experiment (captaincy ceiling EV) through it end-to-end — then re-measured and recorded the tracked 6-season baseline (model+chips 2262) every later experiment in this phase is judged against.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-08T11:01:44Z
- **Completed:** 2026-09-08T11:26:36Z
- **Tasks:** 3
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- `config.EXPERIMENTS` — eight-key flag registry (`capt_ceiling`, `capt_mc`, `chips_v2`, `team_strength`, `rl_strategy`, `understat`, `fotmob`, `fbref_v2`), every value `False`; `config.resolve_experiments(spec)` resolves a comma-separated spec (or `FPL_EXPERIMENTS` env fallback), with `none`/`all` tokens and a `ValueError` on any unrecognised flag name.
- `backtest/walk_forward.py` extended with `--experiments`, `--seasons`, `--tag` CLI options: a season subset for fast iteration (D-14), any flag combination A/B-able in one command, and a tagged `wf_<tag>.csv`/`.json` result written via `ops.jsonio.write_json` when `--tag` is given (unflagged/untagged behaviour is byte-identical to before this plan).
- `models/captaincy.py` — `fit_ceiling_artifact()` (leakage-safe: fits the p10/p25/p75/p90 residual-quantile artifact on the validation season immediately prior to the test season under evaluation, never the shipped 2025-26 `intervals.json`) and `add_ceiling_ev()` (post-hoc `xp_capt_ceiling = xp_mean + lam*(p90 - xp_med)` column, no retraining — same "no new sub-model" discipline that made the Phase C clean-sheet decomposition a documented -50/season rejection).
- `scripts/experiment_run.sh` — D-15 unattended launcher: detaches a `backtest.walk_forward` run via `nohup`+`disown`, logs stdout/stderr to `data/processed/experiments/<tag>-<UTC-ts>.log`, resolves the repo root from its own path, rejects a missing tag with a usage message, and returns to the shell immediately.
- `tests/test_experiments.py` — 10 tests locking the flag-registry invariants (default-off, env fallback, `none`/`all` tokens, bad-token `ValueError`, module dict never mutated) and the captaincy ceiling-EV formula (row-by-row match, `lam=0` reproduces `xp_mean` exactly), plus a `needs_data`-guarded shape check on a real (not mocked) trained-model artifact.
- **Re-measured 6-season baseline** (all flags off, 5 replicas): `model_mean` 2132, **`model+chips` 2262**, `capt_mean` 2150, `capt_capture` 0.563, `multi_safe` 2147, `form` 2032, `hold` 1729 — recorded in a new `## Phase F` section of `IMPROVEMENTS.md` alongside the pre-declared D-05/D-06 adoption criteria and a pending per-flag results table for later plans to fill in.
- **Provisional captaincy A/B reading** (single-season 2025-26, not adoption-deciding): unflagged `capt_capture` 0.595 vs `capt_ceiling`-on `capt_capture` 0.619 — a +2.4 pt absolute move in one season, in the direction the D-06 capture criterion (≥+2 pts absolute over captain-by-mean) is looking for, but this is a 1-season/1-replica smoke reading from Task 1's tracer verify, not the 6-season measurement plan 09-03 will run to actually judge adoption.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "one flag changes the armband and the harness reports it"** - `eb8261b` (feat)
2. **Task 2: Unattended-run launcher and the flag-registry regression test** - `738601c` (test)
3. **Task 3: Measure the real 6-season baseline and open the Phase F results ledger** - `8e35392` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `config.py` - `EXPERIMENTS` registry, `CAPT_CEILING_LAMBDA`/`CHIPS_V2_HYSTERESIS` constants, `EXPERIMENTS_DIR`, `resolve_experiments()`
- `models/captaincy.py` (new) - `fit_ceiling_artifact()`, `add_ceiling_ev()`, CLI smoke check
- `backtest/walk_forward.py` - `--experiments`/`--seasons`/`--tag` CLI options, `capt_col` wiring, tagged JSON/CSV output, `[wf]` summary line
- `scripts/experiment_run.sh` (new) - unattended launcher
- `tests/test_experiments.py` (new) - 10 regression tests
- `IMPROVEMENTS.md` - new `## Phase F` section (baseline table, adoption criteria, pending results table)

## Decisions Made

- Captaincy ceiling artifact is refit per test season on its own immediately-prior validation season, matching `_preds_for`'s own train/val split arithmetic exactly (`DATA_SEASONS[DATA_SEASONS.index(T) - 1]`) — not the shipped `models/artifacts/intervals.json`, which is fit on the 2025-26 test season and would leak into any earlier test season's captaincy decision.
- The measured 2262 `model+chips` baseline (not D-05's inherited ~2,256 or 09-RESEARCH.md's ~2,263 from the cached CSV) is the number the ≥2,280 adoption bar is judged against for the rest of this phase — all three values agree within the harness's own noise band (SE ≈16), so this is a re-grounding, not a correction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pandas ddof=1 std crashes on a single-season `--seasons` run**
- **Found during:** Task 1's own `<verify>` command (`--seasons 2025-26 --replicas 1 --tag t1base`)
- **Issue:** `res["model_mean"].std()` (default `ddof=1`) is `NaN` for a 1-row `pandas.Series`; the surrounding `int(...)` then raised `ValueError: cannot convert float NaN to integer`, crashing the exact single-season fast-iteration path D-14 requires this plan to add.
- **Fix:** Guarded the season-to-season std computation to `0.0` when `n == 1` (the honest answer: there is no season-to-season spread from one season), used consistently for both the printed line and the tagged JSON summary's `model_std` field.
- **Files modified:** `backtest/walk_forward.py`
- **Verification:** `python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag t1base` now completes and prints `±0/season, SE 0`; full 6-season baseline run (`n=6`) still reports the pre-existing non-zero std unaffected.
- **Committed in:** `eb8261b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for the plan's own `--seasons` fast-iteration feature (D-14) to function at all on a single season; no scope creep — the fix only touches the newly-added code path.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The experiment spine (`config.EXPERIMENTS`/`resolve_experiments`, `--experiments`/`--seasons`/`--tag` on the harness, tagged `wf_<tag>.csv`/`.json` artifacts under gitignored `data/processed/experiments/`) is ready for every remaining plan in this phase to build on without inventing its own switch.
- The tracked 6-season baseline (2262 `model+chips`) and the pre-declared D-05/D-06 adoption criteria are in `IMPROVEMENTS.md`'s new `## Phase F` section, ready for plan 09-03 (the full captaincy ceiling-EV sweep/adoption decision) to run against.
- No blockers. `predict/live.py` and `predict/export.py` are untouched, so the weekly product surface is unaffected by this plan.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (config.py, models/captaincy.py, backtest/walk_forward.py, scripts/experiment_run.sh, tests/test_experiments.py, IMPROVEMENTS.md) exist on disk; all three task commits (eb8261b, 738601c, 8e35392) found in git log; full pytest suite (184 passed, 1 skipped) and ruff both green; walk_forward_results.csv unchanged from before this plan.
