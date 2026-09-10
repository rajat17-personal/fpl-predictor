"""Phase 10 plan 10-09: the validating external-prediction ingestion seam
(D-14) -- proves an externally-produced (e.g. Colab) per-fixture prediction
parquet scores through `backtest.season.run_season` identically to an
in-process LightGBM run, and that every validation axis (schema, season set,
row count, ground truth) and the vintage-keyed implausibility gate
(Task 2's `_lgbm_played_spearman`) actually fire -- and that the gate stays
quiet on a legitimate artifact.

Mirrors tests/test_leakage.py's `@needs_data` + module-scoped fixture shape.
"""
from __future__ import annotations

import pandas as pd
import pytest

import config
from backtest.season import run_season
from backtest.walk_forward import _preds_for, load_external_predictions
from models.train import load_features

FEATURES = config.PROCESSED_DIR / "features.parquet"
RAW = config.PROCESSED_DIR / "player_gw.parquet"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")

_ARTIFACT_COLS = ["season", "gw", "player_code", "fixture_id", "xp_med", "xp_mean"]


@pytest.fixture(scope="module")
def df_full():
    return load_features()


@pytest.fixture(scope="module")
def te_2025(df_full):
    """A real in-process LightGBM run's own `_preds_for` output for the 2025-26
    test season -- the known-good input the round-trip test writes to a
    parquet and reads back through the new seam. Module-scoped: this trains
    real models, so every test needing a legitimate artifact shares one run."""
    te, _models, _cols = _preds_for(df_full, "2025-26")
    return te


# --- round-trip equivalence (the seam's whole correctness claim) -----------

@needs_data
def test_external_preds_roundtrip_matches_in_process_run(tmp_path, df_full, te_2025):
    artifact = te_2025[_ARTIFACT_COLS]
    path = tmp_path / "external.parquet"
    artifact.to_parquet(path)

    external = load_external_predictions(path, "2025-26", df=df_full, baseline_spearman=0.383)

    in_process_total = int(run_season(te_2025, "xp_med", use_chips=True).points.sum())
    external_total = int(run_season(external, "xp_med", use_chips=True).points.sum())
    assert external_total == in_process_total


# --- validation axis 1: schema ----------------------------------------------

def test_external_preds_rejects_missing_required_column(tmp_path):
    artifact = pd.DataFrame({
        "season": ["2025-26"], "gw": [1], "player_code": [1], "fixture_id": [1],
        "xp_med": [1.0],
        # xp_mean deliberately missing
    })
    path = tmp_path / "external.parquet"
    artifact.to_parquet(path)
    with pytest.raises(ValueError, match="xp_mean"):
        load_external_predictions(path, "2025-26")


# --- validation axis 2: season set -------------------------------------------

def test_external_preds_rejects_wrong_season_set(tmp_path):
    artifact = pd.DataFrame({
        "season": ["2024-25", "2025-26"], "gw": [1, 1], "player_code": [1, 2],
        "fixture_id": [10, 11], "xp_med": [1.0, 2.0], "xp_mean": [1.0, 2.0],
    })
    path = tmp_path / "external.parquet"
    artifact.to_parquet(path)
    with pytest.raises(ValueError, match="season set"):
        load_external_predictions(path, "2025-26")


# --- validation axis 3: row-count-preserving join ---------------------------

@needs_data
def test_external_preds_rejects_row_count_increase(tmp_path, df_full):
    # The row-count check compares the WHOLE season's local row count before
    # vs after the join (the `_attach_opponent_id` form) -- a single
    # duplicated key would be diluted away by the inner join against the
    # rest of the season, so every (player_code, fixture_id) key for the
    # season is duplicated here to force a real fan-out at the whole-frame
    # level, the same failure shape a Colab notebook emitting two rows per
    # fixture (e.g. a home/away leg mixup) would produce.
    keys = df_full.loc[df_full.season == "2025-26",
                       ["season", "gw", "player_code", "fixture_id"]]
    artifact = pd.concat([keys, keys], ignore_index=True)
    artifact["xp_med"] = 1.0
    artifact["xp_mean"] = 1.0
    path = tmp_path / "external.parquet"
    artifact.to_parquet(path)
    with pytest.raises(AssertionError, match="row count"):
        load_external_predictions(path, "2025-26", df=df_full)


# --- validation axis 4: ground truth is never trusted from the artifact ----

@needs_data
def test_external_preds_ignores_ground_truth_columns_in_the_artifact(tmp_path, df_full, capsys):
    local = df_full[df_full.season == "2025-26"]
    sample = local[["season", "gw", "player_code", "fixture_id"]].head(5).copy()
    sample["xp_med"] = 1.0
    sample["xp_mean"] = 1.0
    sample["y_points"] = 999.0  # a ground-truth column that must never be trusted
    path = tmp_path / "external.parquet"
    sample.to_parquet(path)

    # Explicit baseline_spearman skips the (now always-on, Task 2)
    # `_lgbm_played_spearman` run -- irrelevant to this test's own claim and
    # otherwise a second, redundant training run alongside `te_2025`.
    out = load_external_predictions(path, "2025-26", df=df_full, baseline_spearman=0.383)
    captured = capsys.readouterr()
    assert "WARNING" in captured.out and "y_points" in captured.out
    # The real y_points is re-attached locally, never the artifact's fabricated 999.0.
    assert (out["y_points"] != 999.0).all()


# --- implausibility check: a candidate's own Spearman vs the LightGBM baseline

@needs_data
def test_external_preds_flags_implausible_spearman_jump(tmp_path, df_full, capsys):
    local = df_full[df_full.season == "2025-26"]
    artifact = local[["season", "gw", "player_code", "fixture_id", "y_points"]].copy()
    # Deliberate, obvious leak: xp_med is a monotone function of the REAL
    # y_points for the test season -- a candidate that could only have
    # trained on (or otherwise seen) the very rows it is being scored
    # against, exactly the smells-like-leakage signal 10-RESEARCH.md
    # Pitfall 6 describes.
    artifact["xp_med"] = artifact["y_points"]
    artifact["xp_mean"] = artifact["y_points"]
    artifact = artifact.drop(columns=["y_points"])
    path = tmp_path / "external.parquet"
    artifact.to_parquet(path)

    out = load_external_predictions(path, "2025-26", df=df_full, baseline_spearman=0.383)
    captured = capsys.readouterr()
    assert out.attrs["implausible"] is True
    assert "IMPLAUSIBLE" in captured.out


@needs_data
def test_external_preds_legitimate_roundtrip_not_flagged_implausible(tmp_path, df_full, te_2025):
    """A check that fires on everything is worthless -- a legitimate
    round-tripped artifact (the same known-good input the round-trip test
    uses) must NOT be flagged implausible."""
    artifact = te_2025[_ARTIFACT_COLS]
    path = tmp_path / "external.parquet"
    artifact.to_parquet(path)

    external = load_external_predictions(path, "2025-26", df=df_full, baseline_spearman=0.383)
    assert external.attrs["implausible"] is False


# --- Phase 10 plan 10-10: the D-15 stage-1 cheap gate (models/bracket/gate.py) --

from models.bracket import gate as bracket_gate  # noqa: E402


@pytest.fixture(scope="module")
def gate_lgbm_result(df_full):
    """One real run_gate("lgbm") call, shared by every test below that needs
    a genuine gate result -- run_gate trains on the full config.TRAIN_SEASONS
    (8 seasons), so this is intentionally computed once, not per-test."""
    return bracket_gate.run_gate("lgbm", df=df_full)


def test_gate_spearman_matches_benchmark_external_definition():
    """Same numeric definition as backtest/benchmark_external.py::_stats_block,
    to within 1e-12 on identical synthetic input -- one metric everywhere."""
    from backtest.benchmark_external import _stats_block

    played = pd.DataFrame({
        "xp_med": [1.2, 1.9, 3.5, 3.8, 5.5, 5.9],
        "xp_mean": [1.1, 2.1, 3.4, 3.9, 5.4, 6.1],
        "xp_fpl": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "proj_pts": [1.3, 1.8, 3.6, 3.7, 5.6, 5.8],
        "y_points": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    })
    minutes = pd.Series([90, 90, 90, 90, 90, 90])

    got = bracket_gate.played_only_spearman(played.y_points, played.xp_med, minutes)
    want = _stats_block(played)["spearman_xp_med"]
    assert got == pytest.approx(want, abs=1e-12)


def test_gate_spearman_filters_to_played_only():
    """A minutes==0 row must never influence the correlation, regardless of
    how wildly its prediction disagrees with its (irrelevant) actual."""
    y_true = pd.Series([1.0, 2.0, 3.0, 999.0])
    y_pred = pd.Series([1.1, 2.1, 2.9, -999.0])
    minutes = pd.Series([90, 90, 90, 0])
    played_only = bracket_gate.played_only_spearman(y_true[:3], y_pred[:3], minutes[:3])
    with_unplayed = bracket_gate.played_only_spearman(y_true, y_pred, minutes)
    assert played_only == pytest.approx(with_unplayed, abs=1e-12)


def test_advances_only_when_margin_cleared():
    m = bracket_gate.GATE_MARGIN
    assert bracket_gate._advances(0.500, 0.500 - m) is True     # exactly at the margin
    assert bracket_gate._advances(0.500, 0.500 - m + 0.001) is False  # just short
    assert bracket_gate._advances(None, 0.490) is False          # unavailable candidate


def test_mae_recorded_as_diagnostic_never_in_advance_decision():
    import inspect

    run_gate_src = inspect.getsource(bracket_gate.run_gate)
    assert "mae" in run_gate_src.lower(), "MAE must still be recorded as a diagnostic"
    advances_src = inspect.getsource(bracket_gate._advances)
    assert "mae" not in advances_src.lower(), "MAE must never gate the advance decision"


def test_gate_unavailable_candidate_records_status_without_training(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "EXPERIMENTS_DIR", tmp_path)
    monkeypatch.setattr(bracket_gate.bracket_registry, "is_available", lambda name: False)
    result = bracket_gate.run_gate("ridge")
    assert result["status"] == "unavailable"
    assert result["spearman_xp_med"] is None
    assert result["mae_xp_med"] is None
    assert result["eval_split"] == bracket_gate.EVAL_SPLIT_LABEL
    assert (tmp_path / "bracket_gate_ridge.json").exists()


@needs_data
def test_gate_never_trains_on_a_test_season(gate_lgbm_result):
    """Checked against config.TEST_SEASONS (["2025-26"], the shipped model's
    real held-out season) -- NOT backtest.walk_forward.TEST_SEASONS, which is
    a different concept (the 6 rolling walk-forward test seasons) that
    legitimately overlaps config.TRAIN_SEASONS by design. See
    models/bracket/gate.py's module docstring for the full reasoning."""
    assert not (set(gate_lgbm_result["train_seasons"]) & set(config.TEST_SEASONS)), \
        gate_lgbm_result
    assert gate_lgbm_result["val_season"] not in config.TEST_SEASONS


@needs_data
def test_gate_records_the_in_sample_eval_split_label(gate_lgbm_result):
    assert gate_lgbm_result["eval_split"] == "val_season_in_sample_early_stopping"
    assert gate_lgbm_result["status"] == "ok"
    assert gate_lgbm_result["spearman_xp_med"] is not None
    assert gate_lgbm_result["mae_xp_med"] is not None
    assert gate_lgbm_result["n_played_rows"] > 0


# --- Phase 10 plan 10-11: the leakage-safe padded/masked sequence builder (D-20/D-21) ---

import numpy as np  # noqa: E402
import torch  # noqa: E402

from models.bracket import sequence as bracket_sequence  # noqa: E402


def test_sequence_window_is_padded_and_masked():
    """A synthetic player with 3 prior fixtures against window=10 gives 7
    masked positions, all at the front (left-padding -- the most recent
    gameweek always sits at the LAST index)."""
    window, n_stats = 10, 4
    three_real = np.arange(3 * n_stats, dtype="float32").reshape(3, n_stats)
    x_seq, mask = bracket_sequence._pad_and_mask([three_real], window, n_stats)

    assert x_seq.shape == (1, window, n_stats)
    assert mask.shape == (1, window)
    # 7 padded (True) positions, then 3 real (False) positions, in that order.
    assert mask[0].tolist() == [True] * 7 + [False] * 3
    # The real rows land at the LAST 3 indices, most-recent row last.
    assert torch.allclose(x_seq[0, 7:], torch.as_tensor(three_real))


def test_sequence_uses_raw_stats_not_rolled_features():
    """D-20's raw-input contract: neither SEQ_STATS nor STATIC_COLS may
    contain a rolled (_r3/_r5/_r10/_rall) column -- re-feeding the already-
    rolled features would test nothing about learned temporal aggregation."""
    rolling_suffixes = ("_r3", "_r5", "_r10", "_rall")
    bad = [c for c in list(bracket_sequence.SEQ_STATS) + list(bracket_sequence.STATIC_COLS)
          if c.endswith(rolling_suffixes)]
    assert not bad, bad


# --- Phase 10 plan 10-11: the shared raw-torch training loop + MLP candidate ---

from models.bracket import deep as bracket_deep  # noqa: E402


def test_torch_adapter_matches_sklearn_predict_contract():
    """TorchRegressorAdapter satisfies fit(X, y, eval_set=...)/predict(X)
    (sklearn's contract, models/train.py's stage-2 slot) on tiny synthetic
    data with max_epochs=2, and tolerates LightGBM-only kwargs
    (eval_metric/callbacks) without raising."""
    rng = np.random.RandomState(0)
    Xtr = rng.randn(64, 5).astype("float32")
    Xtr[::9, 1] = np.nan   # legitimate missingness (e.g. a first appearance)
    ytr = (Xtr[:, 0] * 2 + rng.randn(64) * 0.1).astype("float32")
    Xva, yva = Xtr[:16], ytr[:16]

    reg = bracket_deep.build_mlp("regression_l1", {"hidden": (8, 4), "max_epochs": 2})
    reg.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="l1", callbacks=[])
    preds = reg.predict(Xva)

    assert preds.shape == (16,)
    assert np.isfinite(preds).all()
    assert reg.best_iteration_ is not None


def test_mlp_search_respects_budget(monkeypatch):
    """run_search never evaluates more than SEARCH_BUDGET configs, even when
    the underlying search space is monkeypatched larger -- the hard-stop
    D-19 declares, proven directly rather than by trusting the grid's own
    length."""
    monkeypatch.setattr(bracket_deep, "_search_space",
                        lambda candidate: [{"hidden": (4, 2)}] * 50)
    calls = []

    def fit_and_score(cfg):
        calls.append(cfg)
        return float(len(calls))   # monotonically increasing fake val_loss

    log = bracket_deep.run_search("mlp", "unit_test", fit_and_score=fit_and_score)
    assert len(calls) == bracket_deep.SEARCH_BUDGET
    assert len(log["configs"]) == bracket_deep.SEARCH_BUDGET
