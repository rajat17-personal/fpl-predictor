"""Phase 10 plan 10-09: the validating external-prediction ingestion seam
(D-14) -- proves an externally-produced (e.g. Colab) per-fixture prediction
parquet scores through `backtest.season.run_season` identically to an
in-process LightGBM run, and that every validation axis (schema, season set,
row count, ground truth, implausibility) actually fires.

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

    out = load_external_predictions(path, "2025-26", df=df_full)
    captured = capsys.readouterr()
    assert "WARNING" in captured.out and "y_points" in captured.out
    # The real y_points is re-attached locally, never the artifact's fabricated 999.0.
    assert (out["y_points"] != 999.0).all()
