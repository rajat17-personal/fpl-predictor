---
phase: 10-xp-experiment-follow-ups
plan: 09
subsystem: backtest
tags: [external-prediction-seam, colab, leakage-check, walk-forward, spearman-baseline]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-07's current backtest/walk_forward.py state (apply_experiment_feature_gating's tm_ drop branch) -- this plan extends the same file, never a fork of it"
provides:
  - "backtest/walk_forward.py::load_external_predictions -- ingests a Colab-produced per-fixture prediction parquet, validates it on four axes (schema, season set, row count, ground truth), and returns a frame that scores through backtest.season.run_season identically to an in-process LightGBM run"
  - "backtest/walk_forward.py::_lgbm_played_spearman -- a self-sufficient, vintage-keyed (season + features.parquet sha256) in-process LightGBM played-only Spearman baseline, cached to data/processed/experiments/lgbm_played_spearman.json"
  - "main()'s --external-preds CLI flag: scores a frozen artifact through the season loop, refuses combination with --experiments capt_ceiling, records multi_safe as None with a printed note"
  - "tests/test_bracket.py: round-trip equivalence proof plus rejection tests for every validation axis and the implausibility gate (fires on a real leak, stays quiet on a legitimate artifact)"
affects: [10-10, any future Colab bracket-candidate scoring plan]

# Actuals (#2632)
actuals:
  tokens: 6339
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "External-artifact ingestion: validate on arrival (schema -> season set -> ground-truth strip -> row-count-preserving join), re-attach ID_COLS/ground truth locally rather than trust the artifact, then feed the exact same run_season-shaped frame an in-process run produces -- no second scoring path"
    - "Self-sufficient vintage-keyed baseline: a plausibility check's reference figure is computed and cached on first use (season + input-hash key), not deferred to a later plan's artifact file -- no verdict waits on infrastructure that doesn't exist yet"
    - "NaN-safe season-average aggregation: gm built as a plain dict with an isna().all() guard per column, not a pandas Series + astype(int), so an intentionally-unavailable metric (multi_safe under --external-preds) stays a real None instead of crashing or being fabricated"

key-files:
  created:
    - tests/test_bracket.py
  modified:
    - backtest/walk_forward.py

key-decisions:
  - "Task 1's own baseline lookup (config.EXPERIMENTS_DIR/'bracket_gate_lgbm.json', written by a not-yet-executed plan 10-10) was implemented exactly as specified, then Task 2 fully replaced it with a self-sufficient _lgbm_played_spearman baseline per the plan's own explicit instruction ('that ordering is backwards ... make the baseline self-sufficient here') -- both tasks' own <verify> blocks passed independently before moving on"
  - "The artifact's own 'gw' column is validated for presence (schema contract) but dropped before the join -- the join key is (season, player_code, fixture_id) per the plan's own literal instruction, and joining on 'gw' too would only risk a gw_x/gw_y merge-suffix collision against the local frame's already-authoritative 'gw' (from ID_COLS)"
  - "gm (the season-average dict in main()) rewritten from `res.mean().round(0).astype(int)` to a plain per-column dict with an isna().all() guard, and the two print sites plus the tagged-JSON summary guarded for a None multi_safe -- required so --external-preds runs don't crash when multi_safe is intentionally unavailable (Rule 2: missing critical functionality, since a crash on the plan's own documented path would be a bug, not a feature)"
  - "tests/test_bracket.py's row-count-increase test duplicates EVERY (player_code, fixture_id) key for the season, not a single row -- a single duplicated key is diluted away by the inner join against the rest of the season's non-duplicated rows and never trips the whole-frame row-count assertion, so the test needed a season-wide fan-out to genuinely exercise the check"
  - "Added test_external_preds_rejects_missing_required_column (not one of the plan's five named tests) to cover the acceptance criterion 'a missing column raises ValueError naming every absent column at once', which had no dedicated named test slot (Rule 2 -- missing test coverage for a stated acceptance criterion, same precedent as Phase 6 plan 06-01's ops.jsonlog.redact() test)"

patterns-established:
  - "Colab bracket candidates score through load_external_predictions, never a second ad-hoc scoring path -- any future notebook's output must produce exactly the six-column (season, gw, player_code, fixture_id, xp_med, xp_mean) contract"

requirements-completed: [TODO-BRACKET, PHASE10-COLAB-SEAM]

coverage:
  - id: D1
    description: "An externally-produced per-season prediction parquet scores through the exact same run_season/_preds_for path an in-process LightGBM run uses -- proven by exact round-trip equivalence (both totals 2133 for 2025-26, 100% join coverage)"
    requirement: PHASE10-COLAB-SEAM
    verification:
      - kind: unit
        ref: "tests/test_bracket.py::test_external_preds_roundtrip_matches_in_process_run"
        status: pass
    human_judgment: false
  - id: D2
    description: "load_external_predictions VALIDATES rather than merely loads: missing-column, wrong-season-set, row-count-fan-out, and ground-truth-column rejections all fire with the required named-in-error-message detail"
    requirement: TODO-BRACKET
    verification:
      - kind: unit
        ref: "tests/test_bracket.py::test_external_preds_rejects_missing_required_column"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_external_preds_rejects_wrong_season_set"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_external_preds_rejects_row_count_increase"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_external_preds_ignores_ground_truth_columns_in_the_artifact"
        status: pass
    human_judgment: false
  - id: D3
    description: "A leakage-corrupt candidate (xp_med literally copied from real y_points) is flagged IMPLAUSIBLE against a vintage-keyed in-process LightGBM baseline (2025-26 measured 0.3464 played-only Spearman); a legitimate round-tripped artifact is NOT flagged -- the check fires on a real leak and stays quiet on a real candidate"
    requirement: PHASE10-COLAB-SEAM
    verification:
      - kind: unit
        ref: "tests/test_bracket.py::test_external_preds_flags_implausible_spearman_jump"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_external_preds_legitimate_roundtrip_not_flagged_implausible"
        status: pass
      - kind: other
        ref: "python -c '...hashlib.sha256(features.parquet)... assert h in json.dumps(cache entry)...' -- confirms lgbm_played_spearman.json's cache entry is keyed by the feature-matrix hash, not just the season"
        status: pass
    human_judgment: false
  - id: D4
    description: "The seam is built and proven before any Colab candidate exists (--external-preds refuses --experiments capt_ceiling with a named reason; multi_safe recorded as None with a printed note rather than a fabricated number; the plain unflagged walk_forward path runs unchanged)"
    requirement: PHASE10-COLAB-SEAM
    verification:
      - kind: integration
        ref: "python -m backtest.walk_forward --external-preds /nonexistent.parquet --experiments capt_ceiling --seasons 2025-26 -- non-zero exit, 'capt_ceiling' named in stderr"
        status: pass
      - kind: integration
        ref: "python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag seam_regression -- [2025-26] model= line printed, wf_seam_regression.csv/.json written"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 09: External-Prediction Ingestion Seam (D-14) Summary

**Built `backtest/walk_forward.py::load_external_predictions` -- a four-axis-validated ingestion seam that scores a Colab-trained bracket candidate's per-fixture parquet through the identical `run_season`/`_preds_for` path an in-process LightGBM run uses, plus a self-sufficient vintage-keyed implausibility check (`_lgbm_played_spearman`), proven by exact round-trip equivalence before any Colab candidate exists.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-10T17:04:35Z
- **Tasks:** 2 (both committed)
- **Files modified:** 2 (`backtest/walk_forward.py`, `tests/test_bracket.py`)

## Accomplishments

- **`load_external_predictions(path, test_season, *, df=None, baseline_spearman=None)`** (Task 1): validates an externally-produced parquet on four axes -- schema (`_EXTERNAL_PRED_COLS = ["season", "gw", "player_code", "fixture_id", "xp_med", "xp_mean"]`, missing columns named at once), season set (must equal exactly `{test_season}`, both sets named on mismatch), ground truth (any `y_points`/`y_minutes`/`y_played`/`y_started`/`y_clean_sheets` column present is dropped with a named warning -- the artifact is never trusted for what actually happened), and row count (the join onto `features.parquet` must never fan out, both counts named on failure). Every `ID_COLS` member and real ground truth are re-attached locally via an inner join on `(season, player_code, fixture_id)`; `xp_form`/`opponent_team_id` are added exactly as `_preds_for` does, so the returned frame satisfies every consumer in `main`'s season loop (`leakage_safe_plan`'s `opponent_team_id` dependency included).
- **Round-trip proof, the seam's whole correctness claim**: a real LightGBM run's own `_preds_for` output for 2025-26, written to a temp parquet as the six-column contract and read back through `load_external_predictions`, produces an **identical `model+chips` total (2133) at 100% join coverage** to the in-process frame it was derived from -- `tests/test_bracket.py::test_external_preds_roundtrip_matches_in_process_run`.
- **`--external-preds PATH`** wired into `main()` (Task 1): the season loop uses `load_external_predictions` in place of `_preds_for` for each selected season. Refuses combination with `--experiments capt_ceiling` (`SystemExit` naming `capt_ceiling` -- captaincy needs a real `models`/`cols` pair a frozen artifact cannot supply) and records `multi_safe` as `None` with a printed note rather than substituting a locally-trained model's `models`/`cols`, which would describe a different model than the one under test (T-10-09-04). The season-average `gm` computation was rewritten from a pandas-Series `.astype(int)` (which crashes on an all-`None` column) to a NaN-safe plain dict, and both downstream print sites plus the tagged-JSON summary were guarded for a `None` `multi_safe`.
- **`_lgbm_played_spearman(df, test_season)`** (Task 2): the self-sufficient baseline every candidate's implausibility check is compared against -- runs `_preds_for` for the season, scores played-only Spearman with the identical `spearmanr(...).statistic` + `y_minutes > 0` form `backtest/benchmark_external.py::_stats_block` uses, and caches the result to `data/processed/experiments/lgbm_played_spearman.json` keyed by **both** season and `features.parquet`'s sha256 (`_features_parquet_hash`) -- a hash change forces a recompute rather than silently comparing a fresh candidate against a stale baseline. **Measured 2025-26 in-process LightGBM played-only Spearman: 0.3464** (season-specific; the pooled 6-season figure recorded in IMPROVEMENTS.md is 0.383).
- **Implausibility gate rewritten** (Task 2) to call `_lgbm_played_spearman` whenever `baseline_spearman` is `None`, replacing Task 1's read of plan 10-10's not-yet-written `bracket_gate_lgbm.json` and its "no baseline available, skipping" branch -- the baseline is now always available on arrival, so no Colab candidate's verdict waits on a later plan's file. A jump over `_MAX_PLAUSIBLE_SPEARMAN_JUMP = 0.15` prints a loud `IMPLAUSIBLE` warning naming both figures, the threshold, and the likely cause, and sets `.attrs["implausible"]` on the returned frame -- **proven to fire on a deliberately leaked artifact (`xp_med` literally copied from real `y_points`) and stay quiet on a legitimate round-tripped one.**
- **`tests/test_bracket.py`** (both tasks): 7 tests total -- round-trip equivalence, missing-column rejection, wrong-season-set rejection, row-count-fan-out rejection, ground-truth-column drop-and-warn, implausibility-fires-on-a-leak, and implausibility-stays-quiet-on-a-legitimate-artifact. A module-scoped `te_2025` fixture trains the LightGBM models exactly once and is shared across every test needing a legitimate artifact.
- **Full repo suite green**: `python -m pytest -q` -> 296 passed, 1 unrelated pre-existing skip (`.env`-gated cron test, same one noted in 10-07); `ruff check .` clean.

## Task Commits

1. **Task 1: The validating external-prediction ingestion seam** - `b3b93d7` (feat)
2. **Task 2: Implausibility check wired to a recorded baseline** - `137b0e8` (feat)

## Files Created/Modified

- `backtest/walk_forward.py` - `_EXTERNAL_PRED_COLS`, `_MAX_PLAUSIBLE_SPEARMAN_JUMP`, `_GROUND_TRUTH_COLS`, `_features_parquet_hash`, `_lgbm_played_spearman`, `load_external_predictions`; `main()` gained `--external-preds`, the `capt_ceiling` conflict check, and a NaN-safe `gm` season-average computation
- `tests/test_bracket.py` (new) - `df_full`/`te_2025` module-scoped fixtures, 7 tests covering round-trip equivalence, every validation axis, and the implausibility gate

## Decisions Made

- Task 1's own literal instruction (read `bracket_gate_lgbm.json` if present, else print-and-skip) was implemented exactly as written, then fully replaced by Task 2's self-sufficient `_lgbm_played_spearman` per the plan's own explicit "that ordering is backwards ... make the baseline self-sufficient here" -- both tasks' `<verify>` blocks passed independently before moving to the next.
- The artifact's own `gw` column is validated for presence (schema contract, `_EXTERNAL_PRED_COLS`) but dropped before the join -- joining on `(season, player_code, fixture_id)` per the plan's literal instruction, without also joining on `gw`, avoids a `gw_x`/`gw_y` merge-suffix collision against the local frame's already-authoritative `gw` (from `ID_COLS`).
- `gm` (the season-average dict in `main()`) rewritten from `res.mean().round(0).astype(int)` to a plain per-column dict with an `isna().all()` guard: required so `--external-preds` runs don't crash when `multi_safe` is intentionally `None` for every row (Rule 2 -- a crash on the plan's own documented behavior would be a bug, not a feature, and the plan's own acceptance criteria requires `multi_safe` recorded as `None`, not a crash).
- `tests/test_bracket.py::test_external_preds_rejects_row_count_increase` duplicates **every** `(player_code, fixture_id)` key for the season rather than a single row -- a single duplicated key is diluted away by the inner join against the rest of the season's non-duplicated rows and never trips the whole-frame row-count assertion (discovered empirically: the first version of this test failed with `DID NOT RAISE`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `test_external_preds_rejects_missing_required_column`**
- **Found during:** Task 1, writing `tests/test_bracket.py`
- **Issue:** The plan's acceptance criteria requires "a missing column raises `ValueError` naming every absent column at once", but none of the five named tests in the plan's "Artifacts this phase produces" list covers this axis directly.
- **Fix:** Added a sixth test (beyond the five named ones) asserting the exact behavior.
- **Files modified:** tests/test_bracket.py
- **Verification:** `pytest tests/test_bracket.py::test_external_preds_rejects_missing_required_column -q` passes.
- **Committed in:** b3b93d7 (Task 1 commit)

**2. [Rule 1 - Bug] Row-count-increase test fixed to force a genuine whole-frame fan-out**
- **Found during:** Task 1 verify
- **Issue:** The first version of `test_external_preds_rejects_row_count_increase` duplicated a single `(player_code, fixture_id)` key; the row-count assertion compares the WHOLE season's local row count before vs after the join, and a single duplicated key is diluted away by the inner join against the rest of the (non-duplicated) season -- `DID NOT RAISE AssertionError`.
- **Fix:** Duplicated every `(player_code, fixture_id)` key for the season, forcing a genuine season-wide fan-out that actually exceeds the pre-join row count.
- **Files modified:** tests/test_bracket.py
- **Verification:** `pytest tests/test_bracket.py::test_external_preds_rejects_row_count_increase -q` passes.
- **Committed in:** b3b93d7 (Task 1 commit)

**3. [Rule 2 - Missing Critical] NaN-safe `gm` season-average aggregation**
- **Found during:** Task 1, wiring `--external-preds` into `main()`
- **Issue:** `main()`'s original `gm = res.mean().round(0).astype(int)` crashes with a `ValueError` (cannot convert NaN to int) whenever `multi_safe` is all-`None` for the selected seasons -- exactly the state `--external-preds` intentionally produces, per the plan's own acceptance criteria ("`--external-preds` records `multi_safe` as `None` with a printed note rather than a fabricated number").
- **Fix:** Rewrote `gm` as a plain per-column dict with an `isna().all()` guard (`None` if the whole column is NaN, else the rounded int mean); guarded the two `print()` sites referencing `gm['multi_safe']` and the tagged-JSON summary's `multi_safe` key for a possible `None`.
- **Files modified:** backtest/walk_forward.py
- **Verification:** `python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag seam_regression` (the unflagged path, `multi_safe` always populated) still prints correctly; the `--external-preds` code path was manually exercised (round-trip test + a standalone script) confirming `multi_safe=None` flows through without a crash.
- **Committed in:** b3b93d7 (Task 1 commit)

---

**Total deviations:** 3 (2 Rule-2 missing-critical, 1 Rule-1 test-bug fix)
**Impact on plan:** All three necessary for correctness or for the plan's own stated acceptance criteria to actually hold. No scope creep -- no product wiring, no new experiment flags, no change to the plain unflagged `walk_forward` path's behavior (confirmed unchanged by `wf_seam_regression.csv/.json`).

## Issues Encountered

- `ConstantInputWarning` from `scipy.stats.spearmanr` when a test artifact's `xp_med` is a constant (in `test_external_preds_ignores_ground_truth_columns_in_the_artifact` before the fix): resolved by passing an explicit `baseline_spearman=0.383` in that test (it doesn't test the implausibility path) rather than letting the constant-input correlation compute and warn. Not a code bug -- `spearmanr` on constant input correctly returns NaN, and `NaN > 0.15` correctly evaluates `False` in Python, so `implausible` stays `False` either way; the fix just avoids noisy, irrelevant warning output.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The seam (`load_external_predictions`, `--external-preds`, `_lgbm_played_spearman`) is complete and proven against a known-good input, ahead of any Colab candidate existing -- per D-14, no adoption verdict for a future bracket candidate (plan 10-10 and beyond) waits on infrastructure.
- `data/processed/experiments/lgbm_played_spearman.json` (gitignored, regenerated on demand) now holds a cached 2025-26 baseline (0.3464); future seasons populate lazily on first `load_external_predictions`/`_lgbm_played_spearman` call for that season.
- The six-column artifact contract (`season, gw, player_code, fixture_id, xp_med, xp_mean`) is the fixed target any Colab notebook (plan 10-10+) must produce -- documented in the constant's own comment specifically to survive a future author's temptation to "simplify" it to gameweek-level.
- No blockers for 10-10.

## Self-Check: PASSED

All claimed files and commits verified present:
- `backtest/walk_forward.py`, `tests/test_bracket.py` -- FOUND
- Commits `b3b93d7`, `137b0e8` -- FOUND in `git log --oneline`
- Re-ran `python -m pytest -q`: 296 passed, 1 unrelated pre-existing skip
- Re-ran `ruff check .`: all checks passed
- Re-ran `python -m pytest tests/test_bracket.py -v`: all 7 tests PASSED
- `data/processed/experiments/lgbm_played_spearman.json` confirmed present and vintage-keyed (season + features.parquet sha256 in the cached entry)

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*
