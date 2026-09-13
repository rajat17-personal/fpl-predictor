"""Phase 10 plans 10-11/10-13: the torch-dependent half of the bracket
suite -- the leakage-safe padded/masked sequence builder (D-20/D-21), the
shared raw-torch training loop + MLP candidate, the GRU/transformer sequence
candidates (D-12), and the Colab handoff export + manifest split authority.

Split out of tests/test_bracket.py so that file's torch-free tests keep
running in CI, where torch ships only in the dev-only requirements-rl.txt /
requirements-experiments lockfile (D-09).
"""
from __future__ import annotations

import json
import pandas as pd
import pytest

import config

# torch ships only in the dev-only requirements-rl.txt / requirements-
# experiments lockfile (D-09), so CI (which installs only requirements.txt)
# must skip this whole module rather than crash pytest collection.
pytest.importorskip("torch")

import numpy as np  # noqa: E402
import torch  # noqa: E402

from models.bracket import sequence as bracket_sequence  # noqa: E402
from models.bracket import deep as bracket_deep  # noqa: E402
from models.bracket import recurrent as bracket_recurrent  # noqa: E402
from models.bracket import transformer as bracket_transformer  # noqa: E402
from models.bracket import registry as bracket_registry  # noqa: E402
from models.train import load_features  # noqa: E402

FEATURES = config.PROCESSED_DIR / "features.parquet"
RAW = config.PROCESSED_DIR / "player_gw.parquet"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")


@pytest.fixture(scope="module")
def df_full():
    return load_features()


# --- Phase 10 plan 10-11: the leakage-safe padded/masked sequence builder (D-20/D-21) ---

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


def test_mlp_search_respects_budget(monkeypatch, tmp_path):
    """run_search never evaluates more than SEARCH_BUDGET configs, even when
    the underlying search space is monkeypatched larger -- the hard-stop
    D-19 declares, proven directly rather than by trusting the grid's own
    length."""
    monkeypatch.setattr(config, "EXPERIMENTS_DIR", tmp_path)
    monkeypatch.setattr(bracket_deep, "_search_space",
                        lambda candidate: [{"hidden": (4, 2)}] * 50)
    calls = []

    def fit_and_score(cfg):
        calls.append(cfg)
        return float(len(calls))   # monotonically increasing fake val_loss

    log = bracket_deep.run_search("mlp", "unit_test", fit_and_score=fit_and_score)
    assert len(calls) == bracket_deep.SEARCH_BUDGET
    assert len(log["configs"]) == bracket_deep.SEARCH_BUDGET


@needs_data
def test_granularity_bracket_writes_gate_schema(monkeypatch, tmp_path, df_full):
    """run_granularity_bracket("mlp") writes a gate result whose key set is
    a SUPERSET of bracket_gate_lgbm.json's (plan 10-13's comparison table
    and plan 10-14's ledger read all seven candidates' gate files
    uniformly), plus granularity + granularity_scores for both variants.
    Monkeypatched to a single tiny config and max_epochs=1 so the suite
    stays fast. config.EXPERIMENTS_DIR is redirected to tmp_path so this
    run never clobbers the live, measured bracket_gate_mlp.json."""
    import json

    # Capture the real baseline BEFORE redirecting EXPERIMENTS_DIR -- it
    # only exists in the live directory.
    baseline_path = config.EXPERIMENTS_DIR / "bracket_gate_lgbm.json"
    assert baseline_path.exists(), "run plan 10-10's gate first (python -m models.bracket.gate)"
    baseline = json.loads(baseline_path.read_text())

    monkeypatch.setattr(config, "EXPERIMENTS_DIR", tmp_path)
    monkeypatch.setattr(bracket_deep, "_search_space",
                        lambda candidate: [{"hidden": (4, 2), "dropout": 0.0,
                                            "lr": 1e-3, "weight_decay": 0.0}])
    monkeypatch.setattr(bracket_deep, "_SEARCH_MAX_EPOCHS", 1)
    monkeypatch.setattr(bracket_deep, "_FINAL_MAX_EPOCHS", 1)

    out = bracket_deep.run_granularity_bracket("mlp", df=df_full)

    missing = [k for k in baseline if k not in out]
    assert not missing, missing
    assert "granularity" in out and "granularity_scores" in out
    assert set(out["granularity_scores"]) == {"per_position", "pooled"}

    # Isolation: this run's writes must land under tmp_path, never the
    # live config.EXPERIMENTS_DIR.
    assert (tmp_path / "bracket_gate_mlp.json").exists()
    assert (tmp_path / "bracket_search_mlp_per_position.json").exists()
    assert (tmp_path / "bracket_search_mlp_pooled.json").exists()


# --- Phase 10 plan 10-13: the GRU + transformer sequence candidates (D-12) ---

def test_sequence_regressors_consume_the_padding_mask():
    """The important test: build a synthetic bundle with known padding
    (including one first-appearance row that is fully padded), predict, then
    overwrite the PADDED timesteps with large arbitrary values, predict
    again, and assert the two prediction vectors are bit-identical for BOTH
    the GRU and the transformer. A model that quietly attends to padding
    would pass every shape assertion and produce a plausible, wrong number."""
    torch.manual_seed(0)
    window, n_stats, n_static, n_rows = 10, 5, 3, 4
    x_seq = torch.randn(n_rows, window, n_stats)
    x_static = torch.randn(n_rows, n_static)
    lengths = torch.tensor([10, 6, 1, 0])   # last row: a first appearance
    idx = torch.arange(window).unsqueeze(0)
    mask = idx < (window - lengths).unsqueeze(1)   # True = padded

    models = [
        bracket_recurrent.GruSeqRegressor(n_stats=n_stats, n_static=n_static, hidden_size=8),
        bracket_transformer.TransformerSeqRegressor(n_stats=n_stats, n_static=n_static,
                                                     window=window),
    ]
    for model in models:
        model.eval()
        with torch.no_grad():
            pred1 = model(x_seq, mask, x_static)

        x_seq_tampered = x_seq.clone()
        x_seq_tampered[mask] = 1e6   # only touches PADDED positions

        with torch.no_grad():
            pred2 = model(x_seq_tampered, mask, x_static)

        assert torch.equal(pred1, pred2), f"{type(model).__name__} attends to padding"
        assert torch.isfinite(pred1).all(), f"{type(model).__name__} produced non-finite output"


def test_transformer_size_matches_locked_budget():
    """10-01-PLAN.md's locked Transformer budget row."""
    assert (bracket_transformer.D_MODEL, bracket_transformer.N_HEAD,
            bracket_transformer.N_LAYERS, bracket_transformer.DIM_FF,
            bracket_transformer.DROPOUT) == (64, 4, 2, 128, 0.1)


def test_registry_covers_all_seven_bracket_candidates():
    import config
    missing = [c for c in config.BRACKET_CANDIDATES if c not in bracket_registry.CANDIDATES]
    assert not missing, missing
    assert set(bracket_registry.CANDIDATES) == set(config.BRACKET_CANDIDATES)


def test_registry_is_available_never_raises_for_deep_candidates():
    """is_available answers True/False, never raises -- even for the deep
    candidates whose factory does a lazy torch import."""
    for name in ("mlp", "rnn", "transformer"):
        assert bracket_registry.is_available(name) in (True, False)


# --- Phase 10 plan 10-13: the Colab handoff export + manifest split authority ---

@needs_data
def test_exported_bundle_roundtrips_to_the_same_tensors(tmp_path, df_full):
    """Export one season (the lightest valid test season, to keep this test
    fast), reload the `.npz`/`.parquet` from disk, and assert the tensors
    are element-wise equal to a fresh `build_sequences` call -- and that the
    manifest's split triple matches `backtest.walk_forward`'s own
    expanding-window computation for the same season. That second assertion
    is what makes the manifest trustworthy as the notebook's split
    authority (T-10-13-02)."""
    import numpy as np

    from backtest.walk_forward import DATA_SEASONS
    from models.bracket import sequence as bracket_sequence
    from models.bracket.registry import export_sequence_bundle

    test_season = "2018-19"   # DATA_SEASONS index 2 -- the smallest valid export union
    out_dir = export_sequence_bundle([test_season], tmp_path / "colab_input")
    manifest = json.loads((out_dir / "manifest.json").read_text())

    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet")
    gws = sorted(df_full.loc[df_full.season == test_season, "gw"].unique().tolist())
    fresh = [bracket_sequence.build_sequences(test_season, int(gw), raw=raw, feat=df_full)
            for gw in gws]
    fresh_x_seq = torch.cat([b.x_seq for b in fresh], dim=0).numpy()
    fresh_mask = torch.cat([b.mask for b in fresh], dim=0).numpy()
    fresh_x_static = torch.cat([b.x_static for b in fresh], dim=0).numpy()

    loaded = np.load(out_dir / f"{test_season}_tensors.npz")
    assert np.array_equal(loaded["x_seq"], fresh_x_seq, equal_nan=True)
    assert np.array_equal(loaded["mask"], fresh_mask)
    assert np.array_equal(loaded["x_static"], fresh_x_static, equal_nan=True)

    i = DATA_SEASONS.index(test_season)
    exp_train, exp_val = DATA_SEASONS[:i - 1], DATA_SEASONS[i - 1]
    sp = manifest["splits"][test_season]
    assert list(sp["train_seasons"]) == list(exp_train)
    assert sp["val_season"] == exp_val
    assert sp["test_season"] == test_season
