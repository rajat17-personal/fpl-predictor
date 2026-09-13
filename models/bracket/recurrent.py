"""Phase 10 plan 10-13: the recurrent sequence candidate (D-12's "exactly one
recurrent, LSTM or GRU, not both").

**GRU, not LSTM.** D-12 requires exactly one recurrent candidate and leaves
the choice open. GRU is the pick for two reasons: it has fewer parameters
than an LSTM for the same hidden size and sequence length, which matters
directly against D-13's fixed 200-unit Colab compute budget, and the
10-gameweek window (`models/bracket/sequence.py::SEQ_WINDOW`) is short enough
that LSTM's extra input/forget/output gating buys little over GRU's simpler
update/reset gates. This is a decision on the record, not an accident.

This module also owns `_SeqRegressorAdapter`, the sklearn `fit`/`predict`
contract `models/bracket/deep.py::TorchRegressorAdapter` establishes
(`fit(X, y, eval_set=...) -> self`, `predict(X) -> np.ndarray`,
`best_iteration_`), generalised to a `SequenceBundle`-shaped input.
`TorchRegressorAdapter` itself cannot wrap either sequence candidate: its
`fit` hardcodes `MlpRegressor` construction over a flat 2-D
`StandardScaler`-fitted matrix, and neither applies to a
`(x_seq, mask, x_static)` triple -- and `models/bracket/deep.py` is outside
this plan's file set (it belongs to plan 10-11's). Defined once here and
imported into `models/bracket/transformer.py` so both sequence candidates
share one adapter rather than two near-identical copies. It runs its own
best-epoch-restoring training loop (mirroring `train_torch_regressor`'s
device-select / seed-pin / early-stop / best-state-restore shape) because
that shared loop calls `model(xb)` with exactly one positional tensor, which
does not fit a 3-tensor `(x_seq, mask, x_static)` forward signature.
"""
from __future__ import annotations

import copy
import time

import numpy as np
import torch
from torch import nn

from models.bracket.deep import SEARCH_BUDGET as _SEARCH_BUDGET


def _select_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _seed_everything(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)


class GruSeqRegressor(nn.Module):
    """`nn.GRU(input_size=n_stats, hidden_size, num_layers, batch_first=True)`
    over the raw per-gameweek sequence, reading the LAST NON-PADDED hidden
    state (never the last index blindly), then a small head over
    `[selected_hidden ; x_static]` -- the static side-vector is concatenated
    AFTER the encoder, never as an extra timestep (D-20).

    Deliberately does NOT use torch's sequence-packing helper: that helper
    expects RIGHT-padding, and would silently misread the LEFT-padded layout
    `models/bracket/sequence.py::_pad_and_mask` produces (the most recent
    gameweek always sits at the last index, regardless of history length).
    Padding is instead zeroed out before the recurrent pass and the true
    last-timestep hidden state is selected explicitly via the mask.
    """

    def __init__(self, n_stats: int, n_static: int, hidden_size: int = 32,
                num_layers: int = 1, dropout: float = 0.1):
        super().__init__()
        self.hidden_size = hidden_size
        self.gru = nn.GRU(input_size=n_stats, hidden_size=hidden_size,
                          num_layers=num_layers, batch_first=True,
                          dropout=dropout if num_layers > 1 else 0.0)
        self.head = nn.Sequential(
            nn.Linear(hidden_size + n_static, 32), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(32, 1))

    def forward(self, x_seq: torch.Tensor, mask: torch.Tensor,
               x_static: torch.Tensor) -> torch.Tensor:
        # Padded timesteps are zeroed BEFORE the recurrent pass. Because
        # padding is LEFT-padding, a padded position always sits strictly
        # before the real history in the sequence -- a plain forward pass
        # over the raw (untouched) input would let a padded position's own
        # value influence the hidden state that every later, REAL timestep
        # builds on. Zeroing removes that dependency entirely: the only
        # thing a padded position can still influence is how many zero
        # steps precede the real history, which is fixed by the mask
        # alone, never by the padded position's actual value. This is what
        # makes the padding-mask invariance test (overwrite padded values,
        # predict again, expect a bit-identical result) hold.
        x = x_seq.masked_fill(mask.unsqueeze(-1), 0.0)
        out, _ = self.gru(x)   # (batch, window, hidden_size)

        lengths = (~mask).sum(dim=1)              # true history length per row
        batch_idx = torch.arange(x.shape[0], device=x.device)
        last_idx = (lengths - 1).clamp(min=0)
        selected = out[batch_idx, last_idx]        # (batch, hidden_size)
        zero_len = (lengths == 0).unsqueeze(1)      # a first appearance: all-padded
        selected = torch.where(zero_len, torch.zeros_like(selected), selected)

        combined = torch.cat([selected, x_static], dim=1)
        return self.head(combined).squeeze(-1)


# D-19's declared deep-candidate search budget: at most SEARCH_BUDGET (12)
# configs, hard stop. Varies training hyperparameters and architecture size;
# window/input size are fixed by the sequence builder, not searched.
_GRU_SPACE: list[dict] = [
    {"hidden_size": 16, "num_layers": 1, "dropout": 0.0, "lr": 1e-3, "weight_decay": 0.0},
    {"hidden_size": 32, "num_layers": 1, "dropout": 0.0, "lr": 1e-3, "weight_decay": 0.0},
    {"hidden_size": 32, "num_layers": 1, "dropout": 0.1, "lr": 1e-3, "weight_decay": 0.0},
    {"hidden_size": 32, "num_layers": 2, "dropout": 0.1, "lr": 1e-3, "weight_decay": 0.0},
    {"hidden_size": 64, "num_layers": 1, "dropout": 0.1, "lr": 1e-3, "weight_decay": 0.0},
    {"hidden_size": 64, "num_layers": 2, "dropout": 0.1, "lr": 1e-3, "weight_decay": 1e-4},
    {"hidden_size": 64, "num_layers": 1, "dropout": 0.2, "lr": 5e-4, "weight_decay": 0.0},
    {"hidden_size": 32, "num_layers": 1, "dropout": 0.1, "lr": 2e-3, "weight_decay": 0.0},
]
assert len(_GRU_SPACE) <= _SEARCH_BUDGET, (len(_GRU_SPACE), _SEARCH_BUDGET)


class _SeqRegressorAdapter:
    """See module docstring: the sklearn `fit`/`predict` contract
    `TorchRegressorAdapter` establishes, generalised to a `SequenceBundle`
    input. `X` in `fit(X, y, ...)`/`predict(X)` is a `SequenceBundle` (or any
    object exposing `.x_seq`/`.mask`/`.x_static`/`.y`), not a flat array.
    """

    _warned = False

    def __init__(self, *, model_cls, name: str, objective: str = "regression_l1",
                model_kwargs: dict | None = None, lr: float = 1e-3,
                weight_decay: float = 0.0, max_epochs: int = 200,
                patience: int = 50, seed: int = 0, batch_size: int = 256):
        self.model_cls = model_cls
        self.name = name
        self.objective = objective
        self.model_kwargs = dict(model_kwargs or {})
        self.lr = lr
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.patience = patience
        self.seed = seed
        self.batch_size = batch_size
        self.best_iteration_ = None
        self.history_: dict | None = None
        self._model: nn.Module | None = None

    @classmethod
    def _warn_once(cls, ignored: list[str]) -> None:
        if ignored and not cls._warned:
            print(f"[bracket] {cls.__name__} ignoring LightGBM-only kwargs "
                  f"(no torch equivalent): {ignored}", flush=True)
            cls._warned = True

    def _resolve_y(self, bundle, y):
        return bundle.y if y is None else torch.as_tensor(np.asarray(y, dtype="float32"))

    def _batches(self, bundle, y, *, shuffle: bool):
        n = bundle.x_seq.shape[0]
        idx = np.arange(n)
        if shuffle:
            np.random.RandomState(self.seed).shuffle(idx)
        batches = []
        for start in range(0, max(n, 1), self.batch_size):
            b = idx[start:start + self.batch_size]
            if len(b) == 0:
                continue
            xb = (torch.nan_to_num(bundle.x_seq[b]), bundle.mask[b],
                  torch.nan_to_num(bundle.x_static[b]))
            batches.append((xb, y[b]))
        return batches

    def fit(self, bundle, y=None, eval_set=None, **kwargs) -> "_SeqRegressorAdapter":
        self._warn_once(sorted(kwargs))
        _seed_everything(self.seed)
        device = _select_device()

        y_train = self._resolve_y(bundle, y)
        n_stats = bundle.x_seq.shape[-1]
        n_static = bundle.x_static.shape[-1]
        model = self.model_cls(n_stats=n_stats, n_static=n_static,
                               **self.model_kwargs).to(device)
        loss_fn = nn.L1Loss() if self.objective == "regression_l1" else nn.MSELoss()
        opt = torch.optim.AdamW(model.parameters(), lr=self.lr,
                                weight_decay=self.weight_decay)

        train_batches = self._batches(bundle, y_train, shuffle=True)
        if eval_set:
            vb, vy = eval_set[0]
            val_batches = self._batches(vb, self._resolve_y(vb, vy), shuffle=False)
        else:
            val_batches = train_batches

        best_val = float("inf")
        best_epoch = -1
        best_state = copy.deepcopy(model.state_dict())
        history: dict = {"train_loss": [], "val_loss": [], "device": str(device)}
        t0 = time.monotonic()

        for epoch in range(self.max_epochs):
            model.train()
            train_losses = []
            for (xs, m, xst), yb in train_batches:
                xs, m, xst, yb = (xs.to(device), m.to(device), xst.to(device),
                                  yb.to(device))
                opt.zero_grad()
                pred = model(xs, m, xst)
                loss = loss_fn(pred, yb)
                loss.backward()
                opt.step()
                train_losses.append(loss.item())

            model.eval()
            val_losses = []
            with torch.no_grad():
                for (xs, m, xst), yb in val_batches:
                    xs, m, xst, yb = (xs.to(device), m.to(device), xst.to(device),
                                      yb.to(device))
                    val_losses.append(loss_fn(model(xs, m, xst), yb).item())

            train_loss = float(np.mean(train_losses)) if train_losses else float("nan")
            val_loss = float(np.mean(val_losses)) if val_losses else train_loss
            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)

            if val_loss < best_val:
                best_val, best_epoch = val_loss, epoch
                best_state = copy.deepcopy(model.state_dict())
            elif epoch - best_epoch >= self.patience:
                break   # patience exhausted -- best-epoch weights already saved above

        model.load_state_dict(best_state)
        history["best_epoch"] = best_epoch
        history["best_val_loss"] = best_val
        history["wall_clock_s"] = round(time.monotonic() - t0, 2)

        self._model = model
        self.history_ = history
        self.best_iteration_ = best_epoch
        return self

    def predict(self, bundle) -> np.ndarray:
        if self._model is None:
            raise RuntimeError(f"{type(self).__name__}.predict called before fit")
        device = next(self._model.parameters()).device
        self._model.eval()
        with torch.no_grad():
            out = self._model(torch.nan_to_num(bundle.x_seq).to(device),
                              bundle.mask.to(device),
                              torch.nan_to_num(bundle.x_static).to(device))
        return out.detach().cpu().numpy()


def build_gru(objective: str, params: dict | None) -> _SeqRegressorAdapter:
    """Factory for the "rnn" bracket candidate."""
    p = dict(params or {})
    return _SeqRegressorAdapter(
        model_cls=GruSeqRegressor,
        name="rnn",
        objective=objective,
        model_kwargs={
            "hidden_size": p.get("hidden_size", 32),
            "num_layers": p.get("num_layers", 1),
            "dropout": p.get("dropout", 0.1),
        },
        lr=p.get("lr", 1e-3),
        weight_decay=p.get("weight_decay", 0.0),
        max_epochs=p.get("max_epochs", 200),
        patience=p.get("patience", 50),
        seed=p.get("seed", 0),
        batch_size=p.get("batch_size", 256),
    )
