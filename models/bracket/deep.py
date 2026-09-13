"""Phase 10 plan 10-11: the shared raw-torch training loop, the sklearn-
contract adapter, and the first deep D-12 model-class-bracket candidate --
the MLP (D-19's search budget, D-18's dual-granularity gate run).

Follows `optimize/rl_train.py`'s own raw-torch-training-loop convention
(device selection, explicit seed pinning, progress-print cadence) rather
than adding a `skorch`/`pytorch-lightning` wrapper -- 10-RESEARCH.md's
Alternatives Considered is explicit that no such wrapper is to be added
because this project already has a working from-scratch pattern.

Registry registration for deep candidates (`mlp`, and plan 10-13's
`rnn`/`transformer`) is deliberately NOT done here: `models/bracket/
registry.py` belongs to plan 10-10's file set (an earlier wave). This
module instead exports `build_mlp(objective, params)` directly; plan
10-13 Task 1 adds the three deep entries to `models.bracket.registry.
CANDIDATES` in one edit. This plan's own Task 3 gate run
(`run_granularity_bracket`) calls `build_mlp` directly, which is enough to
measure the MLP without registry wiring -- an unregistered factory here is
a deliberate split, not an oversight.
"""
from __future__ import annotations

import copy
import time

import numpy as np
import pandas as pd
import torch
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from torch import nn

import config
from ops.jsonio import write_json

# D-19's locked deep-candidate search budget (10-01-PLAN.md's decision
# table): at most 12 configs per candidate PER GRANULARITY VARIANT, hard
# stop -- do not continue "just one more" on a promising trend -- every
# config's result logged like models/tune.py.
SEARCH_BUDGET = 12

# LightGBM's own patience (models/train.py: early_stopping(50, verbose=False))
# -- matched exactly, not re-tuned, per D-19/D-12 (only the regressor
# implementation changes, not its training discipline).
_PATIENCE = 50


def _select_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _seed_everything(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)


class MlpRegressor(nn.Module):
    """A small `nn.Sequential` over the tabular feature vector: two hidden
    layers, GELU, dropout, sized from the search space. The MLP is the one
    deep candidate that consumes the TABULAR matrix directly rather than
    `models/bracket/sequence.py`'s sequence tensors, which is exactly why it
    goes first in this plan: it exercises the training loop, the adapter,
    the search harness and the gate without also depending on Task 1's
    sequence-builder output."""

    def __init__(self, n_features: int, hidden: tuple[int, int] = (64, 32),
                dropout: float = 0.1):
        super().__init__()
        h1, h2 = hidden
        self.net = nn.Sequential(
            nn.Linear(n_features, h1), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(h1, h2), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(h2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def train_torch_regressor(model: nn.Module, train_batches, val_batches, *,
                          seed: int, max_epochs: int, patience: int = _PATIENCE,
                          lr: float, weight_decay: float,
                          objective: str = "regression_l1",
                          name: str = "bracket") -> tuple[nn.Module, dict]:
    """AdamW training loop with per-epoch validation. L1 loss for the "med"
    objective (`objective="regression_l1"`) and MSE for "mean"
    (`objective="regression"`), mirroring LightGBM's own
    `regression_l1`/`regression` objective tags. Early-stops on validation
    loss at `patience` (LightGBM's own 50 by default) and restores the
    BEST-epoch weights via an in-memory `state_dict` copy -- never the last
    epoch. Pins the seed, selects CUDA when available and CPU otherwise, and
    reports which device it used.

    Returns `(fitted_model, history)` where `history` records per-epoch
    train/val loss, the best epoch, wall-clock seconds, the device used, and
    the checkpoint path (`config.RL_POLICY_DIR / f"bracket_{name}_{seed}.pt"`
    -- already gitignored for exactly this reason: multi-hundred-MB
    artifacts never reach the repo, reusing Phase 9's own gitignore rule
    rather than adding a second one).
    """
    _seed_everything(seed)
    device = _select_device()
    model = model.to(device)
    loss_fn = nn.L1Loss() if objective == "regression_l1" else nn.MSELoss()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_val = float("inf")
    best_epoch = -1
    best_state = copy.deepcopy(model.state_dict())
    history: dict = {"train_loss": [], "val_loss": [], "device": str(device)}
    t0 = time.monotonic()

    for epoch in range(max_epochs):
        model.train()
        train_losses = []
        for xb, yb in train_batches:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            opt.step()
            train_losses.append(loss.item())

        model.eval()
        val_losses = []
        with torch.no_grad():
            for xb, yb in val_batches:
                xb, yb = xb.to(device), yb.to(device)
                val_losses.append(loss_fn(model(xb), yb).item())

        train_loss = float(np.mean(train_losses)) if train_losses else float("nan")
        val_loss = float(np.mean(val_losses)) if val_losses else train_loss
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if val_loss < best_val:
            best_val, best_epoch = val_loss, epoch
            best_state = copy.deepcopy(model.state_dict())
        elif epoch - best_epoch >= patience:
            break   # patience exhausted -- best-epoch weights already saved above

    model.load_state_dict(best_state)
    history["best_epoch"] = best_epoch
    history["best_val_loss"] = best_val
    history["wall_clock_s"] = round(time.monotonic() - t0, 2)

    ckpt_path = config.RL_POLICY_DIR / f"bracket_{name}_{seed}.pt"
    torch.save(best_state, ckpt_path)
    history["checkpoint"] = str(ckpt_path)

    return model, history


def _make_batches(X: np.ndarray, y: np.ndarray, batch_size: int, *,
                  shuffle: bool, seed: int = 0) -> list[tuple[torch.Tensor, torch.Tensor]]:
    n = len(X)
    idx = np.arange(n)
    if shuffle:
        np.random.RandomState(seed).shuffle(idx)
    batches = []
    for start in range(0, max(n, 1), batch_size):
        b = idx[start:start + batch_size]
        if len(b) == 0:
            continue
        batches.append((torch.as_tensor(X[b], dtype=torch.float32),
                        torch.as_tensor(y[b], dtype=torch.float32)))
    return batches


class TorchRegressorAdapter:
    """The bridge that lets a torch model sit in `models/train.py`'s stage-2
    slot: exposes sklearn's `fit(X, y, eval_set=..., callbacks=...)` /
    `predict(X)` contract so every existing call site (`_fit_stage2`'s plain
    med/mean loop, the DEF/GK `ComponentModel` residual regressor, and the
    3-state minutes model's per-segment regressors) works unchanged.
    LightGBM-specific kwargs (`eval_metric`, `callbacks`) are accepted and
    ignored with a ONE-TIME printed note rather than raising, since
    `_fit_stage2` passes them positionally to every regressor.

    `fit` standardizes the tabular input: the scaler and imputer are fitted
    on TRAIN only, then reused in `predict` -- a scaler refit at predict
    time would be a silent train/serve skew. NaN is handled by median
    imputation with an added missingness indicator, exactly as
    `models/bracket/classical.py`'s `RidgeRegressorFactory` does (same
    reasoning: the missingness is information-bearing, not an artefact to
    paper over). `predict(X)` returns a 1-D numpy array. `best_iteration_`
    is exposed as the recorded best epoch so `models/train.py`'s existing
    `getattr(reg, "best_iteration_", None)` reporting keeps working.
    """

    _warned = False

    def __init__(self, *, name: str, objective: str = "regression_l1",
                hidden: tuple[int, int] = (64, 32), dropout: float = 0.1,
                lr: float = 1e-3, weight_decay: float = 0.0,
                max_epochs: int = 200, patience: int = _PATIENCE,
                seed: int = 0, batch_size: int = 1024):
        self.name = name
        self.objective = objective
        self.hidden = hidden
        self.dropout = dropout
        self.lr = lr
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.patience = patience
        self.seed = seed
        self.batch_size = batch_size
        self.best_iteration_ = None
        self.history_: dict | None = None
        self._imputer: SimpleImputer | None = None
        self._scaler: StandardScaler | None = None
        self._model: nn.Module | None = None

    @classmethod
    def _warn_once(cls, ignored: list[str]) -> None:
        if ignored and not cls._warned:
            print(f"[bracket/deep] TorchRegressorAdapter ignoring LightGBM-only "
                  f"kwargs (no torch equivalent): {ignored}", flush=True)
            cls._warned = True

    def fit(self, X, y, eval_set=None, **kwargs) -> "TorchRegressorAdapter":
        self._warn_once(sorted(kwargs))
        Xtr = np.asarray(X, dtype="float64")
        ytr = np.asarray(y, dtype="float32")

        self._imputer = SimpleImputer(strategy="median", add_indicator=True)
        Xtr_imp = self._imputer.fit_transform(Xtr)
        self._scaler = StandardScaler()
        Xtr_s = self._scaler.fit_transform(Xtr_imp).astype("float32")

        if eval_set:
            Xva_raw, yva = eval_set[0]
            Xva = np.asarray(Xva_raw, dtype="float64")
            yva = np.asarray(yva, dtype="float32")
            Xva_s = self._scaler.transform(self._imputer.transform(Xva)).astype("float32")
        else:
            Xva_s, yva = Xtr_s, ytr

        model = MlpRegressor(Xtr_s.shape[1], hidden=self.hidden, dropout=self.dropout)
        train_batches = _make_batches(Xtr_s, ytr, self.batch_size, shuffle=True, seed=self.seed)
        val_batches = _make_batches(Xva_s, yva, self.batch_size, shuffle=False)

        model, history = train_torch_regressor(
            model, train_batches, val_batches, seed=self.seed,
            max_epochs=self.max_epochs, patience=self.patience, lr=self.lr,
            weight_decay=self.weight_decay, objective=self.objective, name=self.name)

        self._model = model
        self.history_ = history
        self.best_iteration_ = history["best_epoch"]
        return self

    def predict(self, X) -> np.ndarray:
        if self._model is None or self._scaler is None or self._imputer is None:
            raise RuntimeError("TorchRegressorAdapter.predict called before fit")
        Xp = np.asarray(X, dtype="float64")
        Xp_s = self._scaler.transform(self._imputer.transform(Xp)).astype("float32")
        device = next(self._model.parameters()).device
        self._model.eval()
        with torch.no_grad():
            out = self._model(torch.as_tensor(Xp_s, dtype=torch.float32, device=device))
        return out.detach().cpu().numpy()


def build_mlp(objective: str, params: dict | None) -> TorchRegressorAdapter:
    """Factory for the "mlp" bracket candidate -- called directly by this
    plan's own Task 3 gate run, and by plan 10-13 Task 1 once `mlp` is
    registered in `models.bracket.registry.CANDIDATES`. Unrecognised/absent
    `params` keys fall back to sensible defaults."""
    p = dict(params or {})
    return TorchRegressorAdapter(
        name="mlp", objective=objective,
        hidden=tuple(p.get("hidden", (64, 32))),
        dropout=p.get("dropout", 0.1),
        lr=p.get("lr", 1e-3),
        weight_decay=p.get("weight_decay", 0.0),
        max_epochs=p.get("max_epochs", 200),
        patience=p.get("patience", _PATIENCE),
        seed=p.get("seed", 0),
        batch_size=p.get("batch_size", 1024),
    )


def _search_space(candidate: str) -> list[dict]:
    """A deterministic, ordered hyperparameter grid for `candidate`, capped
    at `SEARCH_BUDGET` entries -- D-19's declared deep-candidate search
    budget."""
    if candidate == "mlp":
        grid = [
            {"hidden": (32, 16), "dropout": 0.0, "lr": 1e-3, "weight_decay": 0.0},
            {"hidden": (32, 16), "dropout": 0.1, "lr": 1e-3, "weight_decay": 0.0},
            {"hidden": (64, 32), "dropout": 0.0, "lr": 1e-3, "weight_decay": 0.0},
            {"hidden": (64, 32), "dropout": 0.1, "lr": 1e-3, "weight_decay": 0.0},
            {"hidden": (64, 32), "dropout": 0.2, "lr": 1e-3, "weight_decay": 1e-4},
            {"hidden": (128, 64), "dropout": 0.1, "lr": 1e-3, "weight_decay": 0.0},
            {"hidden": (128, 64), "dropout": 0.2, "lr": 1e-3, "weight_decay": 1e-4},
            {"hidden": (64, 32), "dropout": 0.1, "lr": 5e-4, "weight_decay": 0.0},
            {"hidden": (64, 32), "dropout": 0.1, "lr": 2e-3, "weight_decay": 0.0},
            {"hidden": (128, 64), "dropout": 0.1, "lr": 5e-4, "weight_decay": 1e-4},
            {"hidden": (32, 16), "dropout": 0.1, "lr": 2e-3, "weight_decay": 0.0},
            {"hidden": (128, 64), "dropout": 0.0, "lr": 1e-3, "weight_decay": 0.0},
        ]
    else:
        raise ValueError(f"no search space defined for candidate '{candidate}'")
    return grid[:SEARCH_BUDGET]


def _jsonable_config(cfg: dict) -> dict:
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}


def run_search(candidate: str, granularity: str, *, fit_and_score,
               budget: int = SEARCH_BUDGET) -> dict:
    """Evaluate at most `budget` configs from `_search_space(candidate)`,
    calling `fit_and_score(config) -> val_loss` for each, and hard-stop --
    D-19's declared limit; do not continue "just one more" on a promising
    trend, and Phase 9's own RL entry records what happens when compute is
    the binding constraint and is not respected as declared. Every config's
    result is logged, in `models/tune.py`'s own logging shape, to
    `config.EXPERIMENTS_DIR / f"bracket_search_{candidate}_{granularity}.json"`.
    """
    space = _search_space(candidate)[:budget]
    results = []
    for i, cfg in enumerate(space):
        t0 = time.monotonic()
        val_loss = float(fit_and_score(cfg))
        wall = round(time.monotonic() - t0, 2)
        print(f"[bracket search] {candidate}/{granularity} [{i + 1}/{len(space)}] "
              f"val_loss={val_loss:.4f} {cfg} ({wall}s)", flush=True)
        results.append({"config": _jsonable_config(cfg), "val_loss": val_loss,
                        "wall_clock_s": wall})

    best = min(results, key=lambda r: r["val_loss"]) if results else None
    log = {
        "candidate": candidate,
        "granularity": granularity,
        "budget": budget,
        "configs": results,
        "best_config": best["config"] if best else None,
        "best_val_loss": best["val_loss"] if best else None,
    }
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(log, config.EXPERIMENTS_DIR / f"bracket_search_{candidate}_{granularity}.json",
              indent=1)
    return log


# --- Task 3: run the candidate at both D-18 granularities, through the gate ---

_SEARCH_MAX_EPOCHS = 25     # per-config search budget -- kept small so 12 configs stays fast
_FINAL_MAX_EPOCHS = 60      # the winning config gets a longer final fit


def _add_position_onehot(df_slice: pd.DataFrame, X: np.ndarray) -> np.ndarray:
    """Append a `config.POSITIONS` one-hot block to `X` for the "pooled"
    granularity variant -- `position` is currently in
    `models/train.py::_EXCLUDE` (the per-position split made it redundant
    there), so it is added explicitly here rather than mutating `_EXCLUDE`,
    which would change the shipped tabular path."""
    onehot = pd.get_dummies(df_slice["position"]).reindex(columns=config.POSITIONS, fill_value=0)
    return np.concatenate([X, onehot.to_numpy(dtype="float64")], axis=1)


def _fit_stage1(trp: pd.DataFrame, vap: pd.DataFrame, cols: list[str], params: dict):
    """The P(play) classifier -- ALWAYS per-position LightGBM, for BOTH
    granularity variants: D-12 states only the conditional-points regressor
    is ever swapped, so the P(play) stage was never part of this bracket."""
    from lightgbm import LGBMClassifier, early_stopping, log_evaluation

    from models.train import _prep

    clf = LGBMClassifier(**params)
    clf.fit(_prep(trp, cols), trp.y_played,
            eval_set=[(_prep(vap, cols), vap.y_played)],
            eval_metric="binary_logloss",
            callbacks=[early_stopping(50, verbose=False), log_evaluation(0)])
    return clf


def _fit_stage2_tabular(trp_p: pd.DataFrame, vap_p: pd.DataFrame, cols: list[str],
                        cfg: dict, *, max_epochs: int, seed: int, pooled: bool):
    from models.train import _prep

    Xtr = _prep(trp_p, cols).to_numpy(dtype="float64")
    Xva = _prep(vap_p, cols).to_numpy(dtype="float64")
    if pooled:
        Xtr = _add_position_onehot(trp_p, Xtr)
        Xva = _add_position_onehot(vap_p, Xva)
    ytr = trp_p.y_points.to_numpy(dtype="float32")
    yva = vap_p.y_points.to_numpy(dtype="float32")

    adapter = build_mlp("regression_l1", {**cfg, "max_epochs": max_epochs, "seed": seed})
    adapter.fit(Xtr, ytr, eval_set=[(Xva, yva)])
    val_mae = (float(np.mean(np.abs(adapter.predict(Xva) - yva)))
              if len(Xva) else float("nan"))
    return adapter, val_mae


def run_granularity_bracket(candidate: str, *, df=None) -> dict:
    """D-18 for deep candidates: run `candidate` at BOTH granularities and
    let the better validation variant be the one that enters the D-15 cheap
    gate. Writes `config.EXPERIMENTS_DIR / f"bracket_gate_{candidate}.json"`
    in the same schema `models/bracket/gate.py::run_gate` produces (a
    superset: same keys, plus `granularity` and `granularity_scores`) --
    plan 10-13's comparison table and plan 10-14's ledger entry read all
    seven candidates' gate files uniformly.
    """
    from backtest.walk_forward import apply_experiment_feature_gating
    from models import train as train_module
    from models.bracket import gate as bracket_gate
    from models.train import load_features

    if candidate != "mlp":
        raise ValueError(f"run_granularity_bracket only supports 'mlp' in this plan; "
                         f"got {candidate!r}")

    t0 = time.monotonic()
    d = load_features() if df is None else df
    # D-03: the bracket answers a MODEL-CLASS question on the shipped
    # feature set, never one confounded by an unadopted enrichment family --
    # every experiment flag is forced off, mirroring models/bracket/gate.py.
    d = apply_experiment_feature_gating(d, config.resolve_experiments("none"))

    assert not (set(config.TRAIN_SEASONS) & set(config.TEST_SEASONS)), (
        f"must never train on a config.TEST_SEASONS member: "
        f"{set(config.TRAIN_SEASONS) & set(config.TEST_SEASONS)}")
    assert config.VAL_SEASON not in config.TEST_SEASONS, (
        f"must never evaluate on a config.TEST_SEASONS member: {config.VAL_SEASON}")

    cols = train_module.feature_cols(d)
    tr = d[d.season.isin(config.TRAIN_SEASONS)]
    va = d[d.season == config.VAL_SEASON]

    clfs = {pos: _fit_stage1(tr[tr.position == pos], va[va.position == pos],
                             cols, train_module._LGB_COMMON)
           for pos in config.POSITIONS}

    played_va = va[va.y_played == 1]
    granularity_scores: dict[str, float] = {}
    xp_by_granularity: dict[str, pd.Series] = {}
    best_cfg_by_granularity: dict[str, dict] = {}

    # --- per_position: one MLP per position, one shared 12-config search ---
    def _score_per_position(cfg):
        losses = []
        for pos in config.POSITIONS:
            trp_p = tr[(tr.position == pos) & (tr.y_played == 1)]
            vap_p = va[(va.position == pos) & (va.y_played == 1)]
            _, val_mae = _fit_stage2_tabular(trp_p, vap_p, cols, cfg,
                                             max_epochs=_SEARCH_MAX_EPOCHS, seed=0, pooled=False)
            losses.append(val_mae)
        return float(np.mean(losses))

    log_pp = run_search(candidate, "per_position", fit_and_score=_score_per_position)
    best_cfg_by_granularity["per_position"] = log_pp["best_config"]

    regs_pp = {}
    for pos in config.POSITIONS:
        trp_p = tr[(tr.position == pos) & (tr.y_played == 1)]
        vap_p = va[(va.position == pos) & (va.y_played == 1)]
        reg, _ = _fit_stage2_tabular(trp_p, vap_p, cols, log_pp["best_config"],
                                     max_epochs=_FINAL_MAX_EPOCHS, seed=0, pooled=False)
        regs_pp[pos] = reg

    xp_pp = pd.Series(np.nan, index=played_va.index, dtype="float64")
    for pos in config.POSITIONS:
        idx = played_va.index[played_va.position == pos]
        if len(idx) == 0:
            continue
        from models.train import _prep
        p_play = clfs[pos].predict_proba(_prep(played_va.loc[idx], cols))[:, 1]
        e_pts = regs_pp[pos].predict(_prep(played_va.loc[idx], cols).to_numpy(dtype="float64"))
        xp_pp.loc[idx] = p_play * e_pts
    xp_by_granularity["per_position"] = xp_pp
    granularity_scores["per_position"] = round(
        bracket_gate.played_only_spearman(played_va.y_points, xp_pp, played_va.y_minutes), 4)

    # --- pooled: one MLP over all positions, position one-hot appended ---
    def _score_pooled(cfg):
        trp_p = tr[tr.y_played == 1]
        vap_p = va[va.y_played == 1]
        _, val_mae = _fit_stage2_tabular(trp_p, vap_p, cols, cfg,
                                         max_epochs=_SEARCH_MAX_EPOCHS, seed=0, pooled=True)
        return val_mae

    log_pool = run_search(candidate, "pooled", fit_and_score=_score_pooled)
    best_cfg_by_granularity["pooled"] = log_pool["best_config"]

    trp_p = tr[tr.y_played == 1]
    vap_p = va[va.y_played == 1]
    reg_pool, _ = _fit_stage2_tabular(trp_p, vap_p, cols, log_pool["best_config"],
                                      max_epochs=_FINAL_MAX_EPOCHS, seed=0, pooled=True)

    xp_pool = pd.Series(np.nan, index=played_va.index, dtype="float64")
    for pos in config.POSITIONS:
        idx = played_va.index[played_va.position == pos]
        if len(idx) == 0:
            continue
        from models.train import _prep
        p_play = clfs[pos].predict_proba(_prep(played_va.loc[idx], cols))[:, 1]
        X = _add_position_onehot(played_va.loc[idx],
                                 _prep(played_va.loc[idx], cols).to_numpy(dtype="float64"))
        e_pts = reg_pool.predict(X)
        xp_pool.loc[idx] = p_play * e_pts
    xp_by_granularity["pooled"] = xp_pool
    granularity_scores["pooled"] = round(
        bracket_gate.played_only_spearman(played_va.y_points, xp_pool, played_va.y_minutes), 4)

    winner = max(granularity_scores, key=granularity_scores.get)
    xp_winner = xp_by_granularity[winner]
    mae_winner = float((xp_winner - played_va.y_points).abs().mean())
    wall_clock_s = round(time.monotonic() - t0, 2)

    result = {
        "candidate": candidate,
        "eval_split": bracket_gate.EVAL_SPLIT_LABEL,
        "train_seasons": list(config.TRAIN_SEASONS),
        "val_season": config.VAL_SEASON,
        "params": best_cfg_by_granularity[winner],
        "status": "ok",
        "spearman_xp_med": granularity_scores[winner],
        "mae_xp_med": round(mae_winner, 4),
        "n_played_rows": int(len(played_va)),
        "wall_clock_s": wall_clock_s,
        "granularity": winner,
        "granularity_scores": granularity_scores,
    }
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(result, config.EXPERIMENTS_DIR / f"bracket_gate_{candidate}.json", indent=1)
    return result
