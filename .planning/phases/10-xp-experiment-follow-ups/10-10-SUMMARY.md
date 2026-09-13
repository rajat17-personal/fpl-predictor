---
phase: 10-xp-experiment-follow-ups
plan: 10
subsystem: ml-modeling
tags: [xgboost, catboost, lightgbm, scikit-learn, model-class-bracket, gate, lockfile]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-09's external-prediction ingestion seam and played-only Spearman metric definition (backtest/walk_forward.py's _lgbm_played_spearman / benchmark_external.py's _stats_block), reused verbatim by this plan's gate"
provides:
  - "models/bracket/registry.py -- build_regressor(name, objective, params) / is_available(name): the one seam models/train.py::train_position swaps its stage-2 regressor through"
  - "models/bracket/classical.py, gbdt.py -- Ridge, XGBoost, CatBoost stage-2 candidate factories"
  - "models/bracket/gate.py -- the D-15 cheap validation-split gate (GATE_MARGIN=0.010, MAE diagnostic-only) with four measured, recorded results"
  - "requirements-experiments.in/.txt -- dev-only hash-locked lockfile for xgboost/catboost, isolated from Docker/CI"
affects: [any future plan expanding models.bracket (mlp/rnn/transformer, reserved in config.BRACKET_CANDIDATES but not built here)]

# Actuals (#2632)
actuals:
  tokens: 25000
  tasks: 3
  commits: 2

tech-stack:
  added: [xgboost==3.4.1, catboost==1.2.10]
  patterns:
    - "One swap seam: models.bracket.registry.build_regressor is the SOLE place a stage-2 regressor is constructed in models/train.py -- every call site (the plain med/mean objective loop, the DEF/GK ComponentModel residual regressor, and the 3-state minutes model's per-segment regressors) routes through it, never a second ad-hoc construction path"
    - "stage2='lgbm' takes the EXACT pre-bracket code path (not merely an equivalent one) -- proven via a prediction-equivalence test (1e-9) and a full walk-forward run reproducing the pre-change baseline's model+chips figure exactly (2172, both runs)"
    - "Dev-only hash-locked lockfile isolation (established by requirements-rl.txt in Phase 9, repeated here): requirements-experiments.in/.txt pin only what a single experiment needs, are never referenced by Dockerfile/CI, and are verify-enforced absent from both"

key-files:
  created:
    - models/bracket/__init__.py
    - models/bracket/registry.py
    - models/bracket/classical.py
    - models/bracket/gbdt.py
    - models/bracket/gate.py
    - requirements-experiments.in
    - requirements-experiments.txt
  modified:
    - models/train.py
    - config.py
    - tests/test_experiments.py
    - tests/test_bracket.py
    - .gitignore

key-decisions:
  - "Human approved both xgboost==3.4.1 and catboost==1.2.10 verbatim ('approve both') under Task 1's blocking-human package-legitimacy gate; live PyPI re-verification at install time found zero drift from both the 10-RESEARCH.md audit and the prior executor's own re-check"
  - "The plan's own Task 3 <verify> checks run_gate's train_seasons against backtest.walk_forward.TEST_SEASONS (the 6 rolling walk-forward test seasons), which legitimately OVERLAPS config.TRAIN_SEASONS by design (2020-21..2023-24 are both a walk-forward test season and part of the shipped model's fixed training window) -- implemented and tested against the actually-intended invariant instead, config.TEST_SEASONS (['2025-26'], the shipped model's real held-out season), which is what T-10-10-03's threat description names"
  - "gbdt.py's XgbRegressorFactory/CatBoostRegressorFactory ignore the incoming LightGBM params dict (num_leaves/min_child_samples/subsample_freq have no XGBoost/CatBoost equivalent) and use their own fixed, D-19-untuned _XGB_PARAMS/_CAT_PARAMS instead -- same pattern as classical.py's RidgeRegressorFactory ignoring params entirely"
  - "None of the three challengers cleared GATE_MARGIN=0.010 on the val-split played-only Spearman: ridge +0.0055, xgb +0.0049, catboost -0.0014 against the lgbm baseline of 0.3900 -- all HOLD, no candidate advances to a full 6-season walk-forward"

requirements-completed: [TODO-BRACKET]

coverage:
  - id: D1
    description: "xgboost/catboost installed only after the blocking-human package gate, at re-verified pins, into a dev-only hash-locked lockfile provably isolated from Docker/CI (zero grep hits, production/dev locks byte-identical)"
    requirement: TODO-BRACKET
    verification:
      - kind: other
        ref: "grep -rl requirements-experiments Dockerfile .github/workflows/ -> 0 hits; git diff --stat requirements.txt requirements-dev.txt requirements.in requirements-dev.in -> empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "train_position(..., stage2='lgbm') is byte-equivalent to the pre-bracket shipped path -- only the conditional-points regressor is swappable; the stage-1 P(play) classifier and ComponentModel structure are untouched"
    requirement: TODO-BRACKET
    verification:
      - kind: unit
        ref: "tests/test_experiments.py::test_stage2_lgbm_default_matches_explicit_prediction_equivalence"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py::test_stage2_ridge_swaps_only_the_conditional_points_regressor"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py::test_stage2_ridge_def_component_path_swaps_only_residual_regressor"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag bracket_seam_regression -- model+chips=2172, identical to the pre-change wf_seam_regression.json baseline"
        status: pass
    human_judgment: false
  - id: D3
    description: "Ridge, XGBoost and CatBoost each have a measured, recorded, same-split D-15 gate result (Spearman, MAE, delta, ADVANCE/HOLD verdict), gate provably never trains on the model's real held-out test season"
    requirement: TODO-BRACKET
    verification:
      - kind: unit
        ref: "tests/test_bracket.py::test_gate_never_trains_on_a_test_season"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_gate_spearman_matches_benchmark_external_definition"
        status: pass
      - kind: integration
        ref: "python -m models.bracket.gate --candidate lgbm --candidate ridge --candidate xgb --candidate catboost -- four bracket_gate_<candidate>.json files written, all HOLD"
        status: pass
    human_judgment: false

duration: ~80min (this continuation; excludes the prior executor's Task 1 checkpoint session)
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 10: Model-Class Bracket -- Stage-2 Regressor Swap Seam + D-15 Gate Summary

**xgboost/catboost installed under human approval into a dev-only hash-locked lockfile; `models/bracket/` gives `models/train.py` one swap seam for the stage-2 (conditional-points) regressor, proven byte-equivalent for the shipped LightGBM path; the D-15 cheap gate measured all three challengers against LightGBM on the same validation split and none cleared the +0.010 Spearman margin (ridge +0.0055, xgb +0.0049, catboost -0.0014) -- all HOLD.**

## Performance

- **Duration:** ~80 min (this continuation session)
- **Completed:** 2026-09-10T18:26Z
- **Tasks:** 3 (Task 1 checkpoint resolved this session; Tasks 2 and 3 executed and committed)
- **Files modified:** 12 (7 created, 5 modified)

## Task 1: Package-Legitimacy Gate -- Resolution

**Verbatim human decision:** "approve both" -- xgboost==3.4.1 and catboost==1.2.10 approved for install under the plan's dev-only hash-locked `requirements-experiments` posture.

**Live PyPI re-verification at install time (this session):** `xgboost` latest = 3.4.1, `catboost` latest = 1.2.10 -- **zero drift** from both 10-RESEARCH.md's original audit and the prior executor's own pre-approval re-check. The re-verification-at-install-time discipline's zero-drift record now extends across Phases 1, 2, 4, 5, 9 and this plan.

**Explicitly NOT requested, per the plan's own scope statement:** `skorch` (excluded outright by 10-RESEARCH.md's own recommendation), `onnxruntime` (deferred to plan 10-14, gated separately), `gdeltdoc` (plan 10-12 uses plain `requests`). `requirements.txt` and `requirements-dev.txt` are untouched (confirmed via `git diff --stat`, empty).

**Ad-hoc xgboost==3.2.0 resolution:** the pre-existing untracked `xgboost==3.2.0` install (present in the conda env, absent from every requirements file) was replaced by the pinned `xgboost==3.4.1` during this session's dependency work, as anticipated by the plan.

## Critical Incident: `uv pip sync` Wiped the Shared Conda Environment (Discovered, Recovered, and Documented)

Following the plan's literal install instruction (`uv pip sync requirements-experiments.txt --require-hashes`) treated the **entire** `python314` conda environment as the sync target, since `sync` (unlike `install`) removes anything not listed in the given lockfile. Because `requirements-experiments.txt` lists only 19 packages, this **uninstalled everything else in the environment** -- including project-critical packages (`torch`, `lightgbm`, `scikit-learn`, `fastapi`, `pulp`) and unrelated non-project packages this shared conda env also carries per CLAUDE.md's "use this env for all Python work" convention (`jupyter`/`transformers`/`yt-dlp`/`wordcloud`/`tensorboard`/etc.).

**Detected immediately** (post-install verification import-checked every critical package) and **fully recovered** for this project's purposes by reinstalling from the project's own hash-locked lockfiles using the non-destructive `install` verb instead of `sync`:
- `uv pip install -r requirements.txt --require-hashes`
- `uv pip install -r requirements-dev.txt --require-hashes`
- `uv pip install -r requirements-rl.txt --require-hashes` (restores torch/gymnasium/stable-baselines3/sb3-contrib -- also destroyed by the same incident)
- `uv pip install -r requirements-experiments.txt --require-hashes`
- One additional ad-hoc reinstall: `lxml` (untracked in any lockfile, silently relied on by `pandas.read_html` in `tests/test_transfermarkt.py`; also destroyed and restored)
- One corrupted-download reinstall: `nvidia-nccl-cu13==2.29.7` initially installed with a missing 236MB `.so` payload (network hiccup during the large background torch reinstall); `--reinstall --no-cache` fixed it

**Verified recovered:** full repo `pytest -q` run green (296 passed, 1 unrelated pre-existing skip) immediately after recovery, before any of this plan's own code changes.

**NOT recoverable:** the unrelated non-project packages this shared conda env carried (jupyter/transformers/yt-dlp/wordcloud/tensorboard and others) have no lockfile of record and cannot be restored to their exact prior versions. This is disclosed here for the user's awareness -- reinstall any of these manually if needed for other work in this environment.

**Recorded to `.planning/WINDOWS.md`** (entry id 5, kind `deviation`) for cross-phase visibility, and to `IMPROVEMENTS.md`-adjacent memory: **future installs into any lockfile in this shared conda env must use `uv pip install -r <file> --require-hashes`, never `uv pip sync`**, unless the operator has first confirmed the target environment is dedicated solely to lockfile-tracked packages. This applies equally to `requirements-rl.txt` (Phase 9's RL stack) and any future dev-only lockfile.

## Accomplishments

- **`models/bracket/registry.py`** -- `CANDIDATES` (`lgbm`/`ridge`/`xgb`/`catboost`, a proper subset of `config.BRACKET_CANDIDATES`'s 7 reserved names), `is_available(name)` (never raises, guards a missing package via `importlib.util.find_spec`), `build_regressor(name, objective, params)` (raises `ValueError` naming the bad name and listing valid keys for an unrecognised candidate, `config.resolve_experiments`'s own error style). This is the ONE construction seam `models/train.py` calls through.
- **`models/bracket/classical.py`** -- `RidgeRegressorFactory`: `SimpleImputer(strategy="median", add_indicator=True)` -> `StandardScaler()` -> `Ridge`, with `add_indicator=True` documented as load-bearing (preserves the missingness signal `tests/test_leakage.py::test_first_appearance_has_no_rolling_features` proves is information-bearing).
- **`models/bracket/gbdt.py`** -- `XgbRegressorFactory`/`CatBoostRegressorFactory`, LightGBM-adjacent untuned defaults (D-19), each library's own objective/loss tag mapped from our `"regression_l1"`/`"regression"` vocabulary, `early_stopping_rounds=50` matching LightGBM's own patience exactly.
- **`models/train.py`** -- `train_position`/`train_predict` gain `stage2: str = "lgbm"`. Only the conditional-points regressor is routed through `bracket_registry.build_regressor` (the plain med/mean loop, the DEF/GK `ComponentModel` residual regressor inside `_train_cs_component`, and the 3-state minutes model's per-segment regressors via `_fit_reg`) -- the stage-1 P(play) classifier, calibration path, and `ComponentModel` clean-sheet classifier stay LightGBM unconditionally. New `_fit_stage2` helper dispatches each library's own fit/early-stopping call form; `stage2="lgbm"` calls the EXACT pre-bracket sequence (not a refactored equivalent). `reg.best_iteration_` reads are guarded (`getattr(..., None)`) since Ridge has no such attribute.
- **`config.py`** -- `BRACKET_CANDIDATES` (7 names: `lgbm`/`ridge`/`xgb`/`catboost` built now, `mlp`/`rnn`/`transformer` reserved for future plans) and 6 new `EXPERIMENTS` keys, all `False`.
- **`models/bracket/gate.py`** -- the D-15 cheap gate. `GATE_MARGIN = 0.010`; `played_only_spearman` matches `backtest/benchmark_external.py::_stats_block`'s exact `scipy.stats.spearmanr(...).statistic` call form (proven to 1e-12 on identical synthetic input); `run_gate(candidate)` trains on `config.TRAIN_SEASONS`, evaluates on `config.VAL_SEASON` with `eval_split` labelled `"val_season_in_sample_early_stopping"` so the optimistic in-sample figure is never confused with the 0.383 pooled test-season number; MAE recorded but never gates the advance decision (`_advances` is a pure function taking only Spearman); every experiment flag forced off before training (D-03: the bracket answers a model-class question on the shipped feature set only); `main()` prints a comparison table with per-candidate ADVANCE/HOLD verdicts.
- **Measured gate results** (train 2016-17..2023-24, val 2024-25, in-sample early stopping):

| candidate | status | spearman_xp_med | delta vs lgbm | mae_xp_med | verdict |
|---|---|---|---|---|---|
| lgbm (baseline) | ok | 0.3900 | +0.0000 | 1.7470 | HOLD (self) |
| ridge | ok | 0.3955 | +0.0055 | 1.8190 | HOLD |
| xgb | ok | 0.3949 | +0.0049 | 1.7473 | HOLD |
| catboost | ok | 0.3886 | -0.0014 | 1.7548 | HOLD |

None of the three challengers cleared `GATE_MARGIN=0.010`. Ridge came closest (+0.0055, just over half the margin) with a worse MAE; XGBoost was nearly identical to Ridge on Spearman with LightGBM-matching MAE; CatBoost was slightly worse than the baseline on both metrics. **No candidate advances to a full 6-season walk-forward** -- the model-class question D-03 asked is closed with numbers: for this feature set, the tree-boosting model class (LightGBM vs. XGBoost vs. CatBoost) and even a linear baseline (Ridge) land within noise of each other on the validation-split ranking metric. All four `data/processed/experiments/bracket_gate_<candidate>.json` files are written (gitignored runtime artifacts, regenerable via `python -m models.bracket.gate`).
- **`tests/test_experiments.py`** -- 12 new tests: registry subset/availability/unknown-name/build-regressor-raises, stage2="lgbm" prediction equivalence to 1e-9, stage2="ridge" class-swap proof (regressor swaps, classifier does not), unknown-stage2 raises naming valid keys, DEF/GK component-path swap proof (`getattr` guard confirmed via `reg_best["cs_tag"] is None`).
- **`tests/test_bracket.py`** -- 8 new tests: Spearman-definition match to 1e-12 against `_stats_block`, played-only filtering proof, the `_advances` decision function at the exact margin boundary, MAE-never-gates via source inspection, unavailable-candidate handling (monkeypatched, no training triggered), never-trains-on-test-season, eval_split label present, full result shape.
- **Full repo suite green** post-recovery and post-implementation: `python -m pytest -q` -> 312 passed, 1 unrelated pre-existing skip; `ruff check .` clean including `models/bracket/`.

## Task Commits

1. **Task 1: Package-legitimacy gate** -- resolved this session (checkpoint, no code commit; approval recorded above)
2. **Task 2: Dev-only lockfile, the stage-2 swap seam, and three classical/GBDT candidates** - `c0eae23` (feat)
3. **Task 3: The D-15 stage-1 cheap gate** - `baf9041` (feat)

## Files Created/Modified

- `requirements-experiments.in`/`.txt` (new) - dev-only hash-locked lockfile, xgboost==3.4.1 + catboost==1.2.10, no torch pin
- `models/bracket/__init__.py`, `registry.py`, `classical.py`, `gbdt.py` (new) - the swap seam and three candidate factories
- `models/bracket/gate.py` (new) - the D-15 cheap gate
- `models/train.py` - `stage2` parameter threaded through `train_predict`/`train_position`/`_train_cs_component`/`_train_3state`/`_fit_reg`; new `_fit_stage2` helper; `LGBMRegressor` import removed (no longer used directly)
- `config.py` - `BRACKET_CANDIDATES`, 6 new `EXPERIMENTS` keys
- `tests/test_experiments.py` - `_EXPERIMENT_KEYS` extended; 12 new bracket-seam tests
- `tests/test_bracket.py` - 8 new D-15 gate tests
- `.gitignore` - `catboost_info/` (CatBoost's auto-dumped training-log directory)

## Decisions Made

- Human approved both xgboost==3.4.1 and catboost==1.2.10 ("approve both"), zero PyPI drift re-verified at install time.
- The plan's Task 3 `<verify>` checks against `backtest.walk_forward.TEST_SEASONS` (a different, overlapping-by-design concept from `config.TEST_SEASONS`) -- implemented and tested against the correct invariant instead (`config.TEST_SEASONS`), documented in `gate.py`'s module docstring and confirmed the plan's literal command fails as predicted (proving the plan text bug, not a code bug).
- `gbdt.py`'s factories ignore the incoming LightGBM `params` dict, using their own fixed `_XGB_PARAMS`/`_CAT_PARAMS` (D-19: no tuning budget spent).
- No candidate cleared `GATE_MARGIN`; none advance to a full walk-forward.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected the D-15 gate's test-season invariant to `config.TEST_SEASONS`**
- **Found during:** Task 3, first pytest run of the new gate tests
- **Issue:** The plan's own Task 3 `<verify>` (and my first implementation, following it literally) checked `run_gate`'s recorded `train_seasons` against `backtest.walk_forward.TEST_SEASONS` (`["2020-21", ..., "2025-26"]`, the 6 rolling walk-forward test seasons). That list legitimately intersects `config.TRAIN_SEASONS` (`["2016-17", ..., "2023-24"]`) by design -- the shipped model's fixed training window necessarily includes seasons that also happen to be walk-forward test seasons elsewhere in the codebase. The assertion as literally specified is unsatisfiable by any correct implementation of the plan's own action text.
- **Fix:** Implemented and tested the actually-intended invariant instead: `run_gate` never trains or validates on `config.TEST_SEASONS` (`["2025-26"]`, the shipped model's real held-out season) -- what T-10-10-03's threat description actually names. Confirmed the plan's literal check does fail (all four candidates flagged) when run as written, proving this is a plan-text bug.
- **Files modified:** models/bracket/gate.py, tests/test_bracket.py
- **Verification:** `tests/test_bracket.py::test_gate_never_trains_on_a_test_season` passes against the corrected invariant; the plan's literal check was independently run and confirmed to fail as predicted (documented, not silently worked around).
- **Committed in:** baf9041 (Task 3 commit)

**2. [Rule 1 - Bug, incident recovery] Restored the conda environment after `uv pip sync` wiped it**
- **Found during:** Task 1's post-approval install step
- **Issue:** See "Critical Incident" section above -- `uv pip sync requirements-experiments.txt --require-hashes` removed every package not in that 19-package lockfile from the shared `python314` conda env, including project-critical dependencies.
- **Fix:** Reinstalled every project lockfile (`requirements.txt`, `requirements-dev.txt`, `requirements-rl.txt`, `requirements-experiments.txt`) via non-destructive `uv pip install -r <file> --require-hashes`, plus one ad-hoc `lxml` reinstall and one `--reinstall --no-cache` fix for a corrupted `nvidia-nccl-cu13` download.
- **Files modified:** none (environment-only; no repo files changed by the incident or its recovery)
- **Verification:** full repo `pytest -q` green (296/296 passed, 1 pre-existing skip) before proceeding to Task 2's own code changes.
- **Committed in:** N/A (no code change; recorded in `.planning/WINDOWS.md` entry 5 and this SUMMARY for future-executor visibility)

**3. [Rule 2 - Missing Critical] Added `catboost_info/` to `.gitignore`**
- **Found during:** Task 3, staging commit
- **Issue:** `CatBoostRegressor.fit()` auto-dumps a training-log directory (`catboost_info/`) to the current working directory on every fit; it appeared as an untracked directory that would otherwise leak into git history on a future broad `git add`.
- **Fix:** Added `catboost_info/` to `.gitignore`; removed the already-generated directory.
- **Files modified:** .gitignore
- **Verification:** `git status --short` clean of `catboost_info/` after a fresh `python -m models.bracket.gate` + `pytest` run.
- **Committed in:** baf9041 (Task 3 commit)

---

**Total deviations:** 3 (1 Rule-1 plan-text bug fix, 1 Rule-1 incident recovery, 1 Rule-2 missing-.gitignore-entry)
**Impact on plan:** All three necessary for correctness or for the plan's own stated invariants to actually hold. No scope creep -- no product wiring, no `EXPERIMENTS` flag flipped on, no change to the plain unflagged `walk_forward` path's behavior (confirmed byte-identical via the `bracket_seam_regression` run).

## Issues Encountered

- See "Critical Incident" above -- the most significant issue this session, fully resolved before any of this plan's own code was written.
- `sklearn.impute.SimpleImputer` prints a `UserWarning` ("Skipping features without any observed values") when the ridge candidate is exercised against a season-subset test fixture where several enrichment families (odds/availability/etc.) are wholly absent for old seasons -- expected, not a bug; those columns are legitimately all-NaN for 2016-17/2017-18 (pre-dating those data sources).

## User Setup Required

None - no external service configuration required. **Recommended follow-up (not required for this plan):** if this shared conda env is used for non-FPL work (jupyter/ML experimentation), the user may want to manually reinstall any of the packages destroyed by the incident above (transformers, yt-dlp, wordcloud, tensorboard, jupyter extensions, etc.) -- none of these are tracked by any lockfile in this repo and were not restored.

## Next Phase Readiness

- `models/bracket/` is a complete, tested seam; any future plan (10-11/10-13, reserved as `mlp`/`rnn`/`transformer` in `config.BRACKET_CANDIDATES`) can add a new candidate by adding one factory + one registry entry, without touching `models/train.py` again.
- The D-15 gate's verdict is final for this plan's scope: none of Ridge/XGBoost/CatBoost clear the bar, so no candidate proceeds to a full 6-season walk-forward under this plan. `EXPERIMENTS["bracket_ridge"|"bracket_xgb"|"bracket_catboost"]` all stay `False`.
- **Operational note for future executors of this repo:** never run `uv pip sync` against the shared `python314` conda env for a dev-only experiment lockfile -- use `uv pip install -r <file> --require-hashes` instead. Recorded in `.planning/WINDOWS.md`.
- No blockers for subsequent Phase 10 plans.

## Self-Check: PASSED

All claimed files and commits verified present:
- `models/bracket/__init__.py`, `registry.py`, `classical.py`, `gbdt.py`, `gate.py` -- FOUND
- `requirements-experiments.in`, `requirements-experiments.txt` -- FOUND, hash-locked (635 `--hash=sha256:` occurrences)
- Commits `c0eae23`, `baf9041` -- FOUND in `git log --oneline`
- `data/processed/experiments/bracket_gate_{lgbm,ridge,xgb,catboost}.json` -- FOUND, all `status: ok`
- Re-ran `python -m pytest -q`: 312 passed, 1 unrelated pre-existing skip
- Re-ran `ruff check .`: all checks passed
- Re-ran `git diff --stat requirements.txt requirements-dev.txt requirements.in requirements-dev.in`: empty
- Re-ran `grep -rl requirements-experiments Dockerfile .github/workflows/`: 0 hits

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*
