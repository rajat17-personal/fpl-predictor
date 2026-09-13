---
phase: 10-xp-experiment-follow-ups
plan: 11
subsystem: ml-modeling
tags: [torch, sequence-model, model-class-bracket, deep-learning, gate, mlp]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-10's models/bracket/ registry seam, gate.py's D-15 cheap-gate schema (bracket_gate_lgbm.json), and the LightGBM val-split Spearman baseline (0.3900) every candidate is compared against"
provides:
  - "models/bracket/sequence.py -- build_sequences(season, gw): a leakage-safe padded/masked (season-scoped, strict-kickoff-time-bound) raw per-gameweek sequence tensor builder for plan 10-13's LSTM/GRU and transformer candidates"
  - "tests/test_leakage.py::test_sequence_features_no_future_gw_leakage -- D-21's named leakage gate, proven on 200+ real sampled fixtures by independent recompute"
  - "models/bracket/deep.py -- train_torch_regressor (shared raw-torch AdamW loop, best-epoch restoration), TorchRegressorAdapter (sklearn fit/predict contract for models/train.py's stage-2 slot), MlpRegressor, build_mlp, SEARCH_BUDGET=12, run_search (hard-stopped, logged)"
  - "models/bracket/deep.py::run_granularity_bracket -- D-18's both-granularities-then-gate orchestration for deep candidates; measured MLP result written to data/processed/experiments/bracket_gate_mlp.json"
affects: [10-13 (LSTM/GRU + transformer candidates reuse sequence.py and deep.py's shared training loop; registry.py registration for mlp/rnn/transformer lands there), 10-14 (ledger entry reads bracket_gate_mlp.json)]

# Actuals (#2632)
actuals:
  tokens: 10650
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Raw-torch training loop reused from optimize/rl_train.py's own convention (device auto-select, explicit seed pinning, progress-print cadence) -- no skorch/pytorch-lightning wrapper added, per 10-RESEARCH.md's Alternatives Considered"
    - "Season-scoped sequence history: build_sequences restricts prior-fixture lookback to the SAME season as the target, mirroring features/engineer.py::add_features's own groupby(['season','player_id']) convention -- rolling/sequence features never cross a season boundary in this codebase"
    - "Strict kickoff_time bound (not a gw integer bound) for sequence-history selection -- a gw<g comparison would admit an earlier fixture of the SAME double gameweek not yet played at decision time"
    - "Left-padding via a prepended dummy full-length sequence through torch.nn.utils.rnn.pad_sequence, then dropped -- forces the padded batch to exactly SEQ_WINDOW timesteps even when every row in a batch has a shorter real history than the window"
    - "Deep-candidate registry registration deliberately deferred: models/bracket/deep.py exports build_mlp directly rather than editing models/bracket/registry.py (plan 10-10's file set, an earlier wave) -- plan 10-13 Task 1 adds mlp/rnn/transformer to CANDIDATES in one edit"

key-files:
  created:
    - models/bracket/sequence.py
    - models/bracket/deep.py
  modified:
    - tests/test_leakage.py
    - tests/test_bracket.py

key-decisions:
  - "SEQ_WINDOW=10 locked at the top of D-20's stated ~8-10 band; SEQ_STATS/STATIC_COLS computed once at import time from a parquet SCHEMA-ONLY read (pyarrow.parquet.ParquetFile(...).schema.names, no row data), restricted to columns actually present -- falls back to the full ROLL_STATS/CONTEXT_COLS declared list if the parquet doesn't exist yet, so a fresh clone never breaks import"
  - "Task 3's own <verify> command (like 10-10 Task 3's before it) checks run_granularity_bracket's train_seasons against backtest.walk_forward.TEST_SEASONS -- the SAME plan-text bug 10-10-SUMMARY.md already documented and fixed: that list legitimately overlaps config.TRAIN_SEASONS by design (2020-21..2023-24 are both a walk-forward test season and part of the shipped model's fixed training window). Verified against the actually-intended invariant, config.TEST_SEASONS (['2025-26']), per T-10-11's own threat-register wording and 10-10's precedent -- confirmed the plan's literal check fails as predicted before applying the fix"
  - "Stage-1 P(play) classifier stays per-position LightGBM for BOTH granularity variants (per_position and pooled) -- D-12 states only the conditional-points regressor is ever swapped; the P(play) stage was never part of this bracket's scope, so its own granularity never varies"
  - "run_search's config-sweep selects the best config by validation MAE (regression_l1's own metric), not by Spearman -- Spearman is only computed once, after the winning config is refit at a longer final epoch count, matching the plan's own stated sequence: 'take the best config by validation loss, THEN compute that variant's played-only Spearman'"
  - "Search-time max_epochs=25 (small, budget-conscious) vs. final-refit max_epochs=60 (the winning config gets a longer fit) -- both well under the shared patience=50 default, so early stopping never actually fires within either budget; this is a legitimate outcome, not a bug (the acceptance criterion is that the DEFAULT patience matches LightGBM's, not that it must trigger every run)"

requirements-completed: [TODO-BRACKET]

coverage:
  - id: D1
    description: "The sequence builder (models/bracket/sequence.py) honours D-20's raw-input specification (SEQ_STATS/STATIC_COLS never carry a rolled _r3/_r5/_r10/_rall column) and passes D-21's leakage assertion by independent recompute on 200+ real sampled fixtures spread across seasons"
    requirement: TODO-BRACKET
    verification:
      - kind: unit
        ref: "tests/test_leakage.py::test_sequence_features_no_future_gw_leakage"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_sequence_window_is_padded_and_masked"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_sequence_uses_raw_stats_not_rolled_features"
        status: pass
      - kind: other
        ref: "grep -c pad_sequence models/bracket/sequence.py -> 4 (non-zero, standard torch idiom used, not hand-rolled)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The shared raw-torch training loop (train_torch_regressor) and TorchRegressorAdapter follow optimize/rl_train.py's own convention, restore best-epoch weights (never the last epoch), fit the imputer/scaler on train only, and drop into models/train.py's stage-2 slot unchanged (sklearn fit/predict contract, tolerates LightGBM-only kwargs)"
    requirement: TODO-BRACKET
    verification:
      - kind: unit
        ref: "tests/test_bracket.py::test_torch_adapter_matches_sklearn_predict_contract"
        status: pass
      - kind: other
        ref: "git status --porcelain models/artifacts -> empty (checkpoints land in the already-gitignored dir)"
        status: pass
      - kind: other
        ref: "grep -cE '(import|from) (skorch|pytorch_lightning|lightning)' models/bracket/deep.py -> 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "The MLP is measured at both D-18 granularities (per_position, pooled) within D-19's declared 12-config search budget per variant, and the better variant's gate result is written to data/processed/experiments/bracket_gate_mlp.json in the schema every later plan reads (key-superset of bracket_gate_lgbm.json, plus granularity + granularity_scores)"
    requirement: TODO-BRACKET
    verification:
      - kind: unit
        ref: "tests/test_bracket.py::test_mlp_search_respects_budget"
        status: pass
      - kind: unit
        ref: "tests/test_bracket.py::test_granularity_bracket_writes_gate_schema"
        status: pass
      - kind: integration
        ref: "python -m models.bracket.deep (via run_granularity_bracket('mlp')) -- real 8-season train / 2024-25 val run, per_position=0.3924, pooled=0.3942, winner=pooled, delta vs lgbm baseline (0.3900) = +0.0042 < GATE_MARGIN(0.010) -> HOLD"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 11: Sequence Builder + Raw-Torch Loop + MLP Gate Run Summary

**Leakage-safe raw per-gameweek sequence builder (D-20/D-21) proven on 200+ real fixtures; a shared raw-torch training loop and sklearn-contract adapter following `optimize/rl_train.py`'s own convention; the MLP deep candidate measured at both D-18 granularities (pooled wins, Spearman 0.3942 vs LightGBM's 0.3900) inside D-19's 12-config budget — HOLD, +0.0042 short of the +0.010 gate margin.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-10T19:10Z
- **Tasks:** 3 (all committed)
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- **`models/bracket/sequence.py`** — `SEQ_WINDOW = 10` (top of D-20's ~8-10 band, locked per 10-01-PLAN.md's decision table). `SEQ_STATS`/`STATIC_COLS` derived from `features/engineer.py::ROLL_STATS`/`CONTEXT_COLS`, restricted to columns actually present (a parquet-schema-only read via `pyarrow.parquet.ParquetFile(...).schema.names`, no row data, so import never blocks or breaks on a fresh clone). A build-time assertion rejects any `STATIC_COLS` member ending in a rolling suffix. `build_sequences(season, gw)` selects, per target fixture, the last `SEQ_WINDOW` player-gameweek rows for `(season, player_id)` whose `kickoff_time` is **strictly** earlier than the target's own `kickoff_time` (never a `gw < g` integer bound — that would admit an earlier fixture of the *same* double gameweek not yet played at decision time), restricted to the **same season** (mirrors `add_features`'s own `groupby(["season","player_id"])`, so a GW1 target legitimately has zero history and is retained as an all-padded row, never dropped). `_pad_and_mask` uses `torch.nn.utils.rnn.pad_sequence` with a prepended dummy full-length sequence (dropped after padding) to force exactly `SEQ_WINDOW` timesteps, then left-pads so the most recent gameweek is always at the last index, with an explicit boolean mask in the `src_key_padding_mask` convention (True = padded).
- **`tests/test_leakage.py::test_sequence_features_no_future_gw_leakage`** (D-21's named gate) — samples 4 seasons × 6 gameweeks (≈200+ real target fixtures), and for each, independently recomputes the expected prior-fixture set directly from `player_gw.parquet` (a fresh boolean-filter expression, never calling into the builder's own code) and asserts an exact match on both the real-timestep count and the real-timestep values (`equal_nan=True`, since legitimate enrichment-family NaN exists for old seasons), plus that every included `kickoff_time` is strictly less than the target's. **Passes on real data.**
- **`models/bracket/deep.py`** — `train_torch_regressor` (AdamW loop, L1 loss for `regression_l1`/MSE for `regression` mirroring LightGBM's own objective tags, early stopping at `patience=50` matching LightGBM's `early_stopping(50)` exactly, best-epoch weight restoration via an in-memory `state_dict` copy, checkpoint written to `config.RL_POLICY_DIR` — already gitignored). `TorchRegressorAdapter` bridges a torch model into `models/train.py`'s stage-2 slot: `fit`/`predict` sklearn contract, `SimpleImputer(strategy="median", add_indicator=True)` → `StandardScaler` fitted on train only and reused at predict time, LightGBM-only kwargs (`eval_metric`, `callbacks`) accepted and ignored with a one-time printed note, `best_iteration_` exposed. `MlpRegressor` — two-hidden-layer `nn.Sequential`, GELU, dropout. `build_mlp(objective, params)` factory, deliberately **not** registered in `models/bracket/registry.py` (that file belongs to plan 10-10's file set, an earlier wave) — plan 10-13 Task 1 adds `mlp`/`rnn`/`transformer` to `CANDIDATES` in one edit; documented in `deep.py`'s own module docstring. `SEARCH_BUDGET = 12` (D-19), `_search_space("mlp")` returns exactly 12 deterministic configs, `run_search` hard-stops at the budget and logs every config to `bracket_search_{candidate}_{granularity}.json` in `models/tune.py`'s own logging shape.
- **`run_granularity_bracket("mlp")`** (Task 3, D-18) — the P(play) classifier stays per-position LightGBM for both variants (D-12: only the regressor is ever swapped). `per_position`: one shared 12-config search (one `fit_and_score` call per config, averaging validation MAE across all 4 positions), then the winning config refit per position. `pooled`: one MLP over all positions with a `config.POSITIONS` one-hot block appended to the tabular matrix (via `_add_position_onehot`, never mutating `models/train.py::_EXCLUDE`). Both variants' played-only Spearman computed via `models.bracket.gate.played_only_spearman` (the same call site every other Phase 10 Spearman comes from), the better variant selected, and the result written to `bracket_gate_mlp.json` in `gate.py::run_gate`'s exact schema plus `granularity`/`granularity_scores`.
- **Real measured result** (train `2016-17..2023-24`, val `2024-25`, in-sample early stopping, `n_played_rows=11566`):

| variant | spearman_xp_med | val MAE (search) |
|---|---|---|
| per_position | 0.3924 | 1.7791 (best config) |
| **pooled (winner)** | **0.3942** | 1.6524 (best config) |
| lgbm baseline (10-10) | 0.3900 | — |

Delta (pooled vs. lgbm) = **+0.0042**, below `GATE_MARGIN = 0.010` → **HOLD**. The pooled variant's own `mae_xp_med` on the winning config's final refit is 1.7805. Device used: **cuda** (GPU-proven, per Phase 9's own RL precedent). Wall clock: per_position search+refit ≈ 46s, pooled search+refit ≈ 47s (total run ≈ 93s).
- **Reproducibility check**: the real gate run was executed twice (once before, once after the full `python -m pytest -q` suite, since the suite's own schema test intentionally overwrites `bracket_gate_mlp.json` with a monkeypatched tiny run) — both real runs produced **byte-identical** per-config validation losses and the identical final verdict, confirming the fixed seed (0) makes the search deterministic.
- **Full repo suite green**: `python -m pytest -q` → 318 passed, 1 unrelated pre-existing skip (109.6s); `ruff check .` clean, including `models/bracket/sequence.py` and `models/bracket/deep.py`.

**Reproduce the real gate run:**
```bash
/home/sraja/miniconda3/envs/python314/bin/python -c "
from models.bracket.deep import run_granularity_bracket
out = run_granularity_bracket('mlp')
print(out)
" > data/processed/experiments/bracket_mlp_gate_rerun.log 2>&1 &
tail -f data/processed/experiments/bracket_mlp_gate_rerun.log
```

## Task Commits

1. **Task 1: Leakage-safe padded/masked sequence builder** - `641db74` (feat)
2. **Task 2: Raw-torch training loop and the sklearn-contract adapter** - `20fb5ea` (feat)
3. **Task 3: Run the MLP through both D-18 granularities and the cheap gate** - `dffdaaa` (feat)

## Files Created/Modified

- `models/bracket/sequence.py` (new) — `SEQ_WINDOW`, `SEQ_STATS`, `STATIC_COLS`, `SequenceBundle`, `_pad_and_mask`, `_player_histories`, `build_sequences`
- `models/bracket/deep.py` (new) — `train_torch_regressor`, `TorchRegressorAdapter`, `MlpRegressor`, `build_mlp`, `SEARCH_BUDGET`, `_search_space`, `run_search`, `run_granularity_bracket`
- `tests/test_leakage.py` — `test_sequence_features_no_future_gw_leakage`
- `tests/test_bracket.py` — `test_sequence_window_is_padded_and_masked`, `test_sequence_uses_raw_stats_not_rolled_features`, `test_torch_adapter_matches_sklearn_predict_contract`, `test_mlp_search_respects_budget`, `test_granularity_bracket_writes_gate_schema`

## Decisions Made

- SEQ_WINDOW/SEQ_STATS/STATIC_COLS computed at import time from a schema-only parquet read (see key-decisions above for the fallback behavior).
- Task 3's `<verify>`-adjacent invariant check corrected from `backtest.walk_forward.TEST_SEASONS` to `config.TEST_SEASONS` — the identical plan-text bug 10-10-SUMMARY.md already documented and fixed once this phase; confirmed the plan's literal form fails as predicted before applying the fix (see Deviations below).
- Stage-1 P(play) classifier stays per-position LightGBM regardless of the stage-2 granularity variant under test.
- run_search selects by validation MAE, not Spearman; Spearman is computed once per variant, after the winning config's final refit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, plan-text bug precedent-matched] Corrected the granularity-bracket test-season invariant to `config.TEST_SEASONS`**
- **Found during:** Task 3, running the plan's own literal `<verify>` command
- **Issue:** The plan's own Task 3 `<verify>` command checks `run_granularity_bracket`'s recorded `train_seasons` against `backtest.walk_forward.TEST_SEASONS` (`["2020-21", ..., "2025-26"]`, the 6 rolling walk-forward test seasons). That list legitimately intersects `config.TRAIN_SEASONS` (`["2016-17", ..., "2023-24"]`) by design — this is the EXACT SAME plan-text bug 10-10-SUMMARY.md documented for `models/bracket/gate.py::run_gate`'s own equivalent check, now recurring in this plan's Task 3 verify text.
- **Fix:** Verified against the actually-intended invariant, `config.TEST_SEASONS` (`["2025-26"]`, the shipped model's real held-out season) — matching `models/bracket/gate.py`'s own corrected assertion and this plan's own threat-register wording (T-10-11 doesn't name this threat directly, but `run_granularity_bracket`'s in-code assertions already use `config.TEST_SEASONS`, so only the standalone verify command needed correcting). Confirmed the plan's literal command fails as predicted (`AssertionError` listing all 8 `config.TRAIN_SEASONS` members) before applying the fix.
- **Files modified:** none (verification-only correction; `models/bracket/deep.py`'s own in-code assertions were already written against `config.TEST_SEASONS` from the start, matching 10-10's established pattern)
- **Verification:** the corrected command passes; the plan's literal form was independently confirmed to fail, documented here rather than silently worked around.
- **Committed in:** N/A (no code change — a verification-command correction, recorded here per 10-10's own precedent for the identical class of plan-text issue)

**2. [Rule 1 - Bug] `np.allclose`'s default `equal_nan=False` false-failed the leakage test on legitimate enrichment NaN**
- **Found during:** Task 1, first run of `test_sequence_features_no_future_gw_leakage`
- **Issue:** Several `SEQ_STATS` columns (the Understat/FotMob enrichment families) are legitimately `NaN` for early seasons (2016-17 through ~2021-22, before those sources existed) — `np.allclose(got, expected)` with its default `equal_nan=False` treats two `NaN`s at the same position as unequal, failing the comparison even when the builder and the independent recompute agree exactly.
- **Fix:** Added `equal_nan=True` to the `np.allclose` call.
- **Files modified:** tests/test_leakage.py
- **Verification:** `pytest tests/test_leakage.py::test_sequence_features_no_future_gw_leakage -q` passes.
- **Committed in:** 641db74 (Task 1 commit)

---

**Total deviations:** 2 (1 Rule-1 plan-text-invariant correction matching 10-10's own precedent, 1 Rule-1 test-comparison bug)
**Impact on plan:** Both necessary for the plan's own stated invariants/acceptance criteria to actually hold. No scope creep — no product wiring, no `EXPERIMENTS` flag flipped on (`config.EXPERIMENTS["bracket_mlp"]` stays `False`), no change to `models/train.py`'s shipped stage-2 dispatch (the MLP is measured entirely outside the registry seam, exactly as the plan specifies).

## Issues Encountered

- Two stray `bracket_search_mlp_unit_test.json` runtime-artifact leftovers (from `test_mlp_search_respects_budget`'s monkeypatched `"unit_test"` granularity, and from the full-suite run of `test_granularity_bracket_writes_gate_schema` overwriting `bracket_gate_mlp.json` with its own monkeypatched tiny result) were cleaned up before the final real gate run and final verification pass. Both files are gitignored runtime artifacts under `data/processed/experiments/`, regenerated on every real `run_granularity_bracket("mlp")` call — not a code bug, an expected side effect of running the test suite before capturing the plan's own deliverable numbers, resolved by re-running the real (non-monkeypatched) gate call last.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `models/bracket/sequence.py` and `models/bracket/deep.py`'s shared raw-torch loop/adapter are ready for plan 10-13's LSTM/GRU and transformer candidates to consume directly (`SequenceBundle`, `train_torch_regressor`, `TorchRegressorAdapter`'s pattern).
- The MLP's gate verdict is **HOLD** (+0.0042 short of +0.010) — no candidate from this plan advances to a full 6-season walk-forward. `config.EXPERIMENTS["bracket_mlp"]` stays `False`.
- `models/bracket/registry.py` is untouched (plan 10-10's file set) — plan 10-13 Task 1 registers `mlp`, `rnn`, `transformer` in `CANDIDATES` in one edit, per this plan's own deliberate deferral.
- Context-notes reminder for the next executor: plan 10-08 remains deferred pending the background Transfermarkt backfill (PID 246897 at last check); `data/external/transfermarkt/*.csv` continued growing during this plan's execution and was correctly left out of every commit here (scoped `git add` to this plan's own files only).
- No blockers for plan 10-12 or 10-13.

## Self-Check: PASSED

All claimed files and commits verified present:
- `models/bracket/sequence.py`, `models/bracket/deep.py` — FOUND
- Commits `641db74`, `20fb5ea`, `dffdaaa` — FOUND in `git log --oneline`
- `data/processed/experiments/bracket_gate_mlp.json` — FOUND, `status: ok`, `granularity: pooled`, `spearman_xp_med: 0.3942`
- `data/processed/experiments/bracket_search_mlp_per_position.json`, `bracket_search_mlp_pooled.json` — FOUND, 12 configs each
- Re-ran `python -m pytest tests/test_bracket.py tests/test_leakage.py -q`: 27 passed
- Re-ran `python -m pytest -q` (full repo): 318 passed, 1 unrelated pre-existing skip
- Re-ran `ruff check .`: all checks passed
- Re-ran `git status --porcelain models/artifacts`: empty

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*
