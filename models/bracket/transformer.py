"""Phase 10 plan 10-13: the small transformer sequence candidate (D-12).

Size budget locked at 10-01-PLAN.md's "Locked planner decisions" table
("Transformer budget": `d_model=64`, `nhead=4`, 2 encoder layers,
`dim_feedforward=128`, `dropout=0.1` -- "small transformer encoder" per D-12,
sized to fit D-13's compute box) -- these five constants are module-level,
never searched: `_TRANSFORMER_SPACE` below only varies training
hyperparameters (dropout override, lr, weight_decay), not architecture size.

Shares `models/bracket/recurrent.py::_SeqRegressorAdapter` (see that module's
docstring for why `TorchRegressorAdapter` itself cannot wrap either sequence
candidate) rather than a second, near-identical copy.
"""
from __future__ import annotations

import torch
from torch import nn

from models.bracket.deep import SEARCH_BUDGET as _SEARCH_BUDGET
from models.bracket.recurrent import _SeqRegressorAdapter
from models.bracket.sequence import SEQ_WINDOW

# 10-01-PLAN.md's "Locked planner decisions" table, "Transformer budget" row.
D_MODEL = 64        # 10-01-PLAN.md decision table: Transformer budget
N_HEAD = 4           # 10-01-PLAN.md decision table: Transformer budget
N_LAYERS = 2         # 10-01-PLAN.md decision table: Transformer budget
DIM_FF = 128         # 10-01-PLAN.md decision table: Transformer budget
DROPOUT = 0.1        # 10-01-PLAN.md decision table: Transformer budget


class TransformerSeqRegressor(nn.Module):
    """A linear input projection from `n_stats` to `D_MODEL`, a learned
    positional embedding over `window` positions, then
    `nn.TransformerEncoder` called with `src_key_padding_mask=mask` so the
    encoder never attends to a padded position. Pools by MEAN over
    non-padded positions only (guarding the all-padded row -- a first
    appearance -- with a zeros output rather than a division by zero), then
    concatenates the static side-vector AFTER pooling, never as an extra
    timestep (D-20).
    """

    def __init__(self, n_stats: int, n_static: int, window: int = SEQ_WINDOW,
                dropout: float = DROPOUT):
        super().__init__()
        self.input_proj = nn.Linear(n_stats, D_MODEL)
        self.pos_embed = nn.Parameter(torch.zeros(window, D_MODEL))
        nn.init.normal_(self.pos_embed, std=0.02)
        layer = nn.TransformerEncoderLayer(d_model=D_MODEL, nhead=N_HEAD,
                                           dim_feedforward=DIM_FF, dropout=dropout,
                                           batch_first=True)
        self.encoder = nn.TransformerEncoder(layer, num_layers=N_LAYERS)
        self.head = nn.Sequential(
            nn.Linear(D_MODEL + n_static, 32), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(32, 1))

    def forward(self, x_seq: torch.Tensor, mask: torch.Tensor,
               x_static: torch.Tensor) -> torch.Tensor:
        # Zero the padded positions' raw input before projection -- a
        # defense-in-depth pairing with `src_key_padding_mask` below (the
        # mask alone already stops a padded KEY from influencing any
        # non-padded query's attention output; zeroing here additionally
        # removes any dependency of the padded position's OWN output on its
        # raw value, which matters since a fully-padded row's own outputs
        # would otherwise be undefined-by-construction).
        x = x_seq.masked_fill(mask.unsqueeze(-1), 0.0)
        h = self.input_proj(x) + self.pos_embed.unsqueeze(0)
        enc = self.encoder(h, src_key_padding_mask=mask)

        enc = enc.masked_fill(mask.unsqueeze(-1), 0.0)
        lengths = (~mask).sum(dim=1)
        denom = lengths.clamp(min=1).unsqueeze(1).to(enc.dtype)
        pooled = enc.sum(dim=1) / denom
        zero_len = (lengths == 0).unsqueeze(1)          # a first appearance: all-padded
        pooled = torch.where(zero_len, torch.zeros_like(pooled), pooled)

        combined = torch.cat([pooled, x_static], dim=1)
        return self.head(combined).squeeze(-1)


# D-19's declared deep-candidate search budget: at most SEARCH_BUDGET (12)
# configs, hard stop. Architecture size (D_MODEL/N_HEAD/N_LAYERS/DIM_FF) is
# LOCKED above, not searched -- only training hyperparameters vary.
_TRANSFORMER_SPACE: list[dict] = [
    {"dropout": 0.1, "lr": 1e-3, "weight_decay": 0.0},
    {"dropout": 0.1, "lr": 5e-4, "weight_decay": 0.0},
    {"dropout": 0.2, "lr": 1e-3, "weight_decay": 1e-4},
    {"dropout": 0.0, "lr": 1e-3, "weight_decay": 0.0},
    {"dropout": 0.1, "lr": 2e-3, "weight_decay": 0.0},
    {"dropout": 0.2, "lr": 5e-4, "weight_decay": 1e-4},
]
assert len(_TRANSFORMER_SPACE) <= _SEARCH_BUDGET, (len(_TRANSFORMER_SPACE), _SEARCH_BUDGET)


def build_transformer(objective: str, params: dict | None) -> _SeqRegressorAdapter:
    """Factory for the "transformer" bracket candidate."""
    p = dict(params or {})
    return _SeqRegressorAdapter(
        model_cls=TransformerSeqRegressor,
        name="transformer",
        objective=objective,
        model_kwargs={"dropout": p.get("dropout", DROPOUT)},
        lr=p.get("lr", 1e-3),
        weight_decay=p.get("weight_decay", 0.0),
        max_epochs=p.get("max_epochs", 200),
        patience=p.get("patience", 50),
        seed=p.get("seed", 0),
        batch_size=p.get("batch_size", 256),
    )
