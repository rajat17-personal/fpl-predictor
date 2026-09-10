"""Phase 10 plan 10-10: the stage-2 regressor swap registry (D-12).

`models/train.py::train_position`'s new `stage2` parameter calls through
`build_regressor` -- this is the ONE swap seam: the stage-1 P(play)
classifier, the calibration path, and the `ComponentModel` DEF/GK structure
are all untouched, and only the conditional-points regressor construction
is routed through here.

`CANDIDATES` now covers all seven `config.BRACKET_CANDIDATES` names (plan
10-10's `lgbm`/`ridge`/`xgb`/`catboost`, plan 10-11's `mlp`, and this plan's
`rnn`/`transformer`) -- `set(registry.CANDIDATES) == set(config.BRACKET_CANDIDATES)`.
The three deep-candidate factories (`mlp`/`rnn`/`transformer`) import their
owning module LAZILY, inside the factory function body rather than at this
module's top level: `models/bracket/deep.py`, `recurrent.py` and
`transformer.py` all import `torch` at module scope, which would make this
whole registry unimportable on a machine without torch installed if imported
eagerly here. `is_available` never triggers that import either -- it only
resolves `importlib.util.find_spec("torch")`, so it can answer False for a
missing package rather than raising.
"""
from __future__ import annotations

import importlib.util

from models.bracket import classical, gbdt


def _lgbm_factory(objective: str, params: dict):
    """The shipped candidate -- byte-equivalent to `models/train.py`'s own
    pre-bracket `LGBMRegressor(objective=objective, **params)` construction."""
    from lightgbm import LGBMRegressor
    return LGBMRegressor(objective=objective, **params)


def _mlp_factory(objective: str, params: dict):
    """Plan 10-11's tabular MLP candidate -- lazy import (see module docstring)."""
    from models.bracket import deep
    return deep.build_mlp(objective, params)


def _rnn_factory(objective: str, params: dict):
    """This plan's GRU sequence candidate -- lazy import (see module docstring)."""
    from models.bracket import recurrent
    return recurrent.build_gru(objective, params)


def _transformer_factory(objective: str, params: dict):
    """This plan's transformer sequence candidate -- lazy import (see module
    docstring)."""
    from models.bracket import transformer as transformer_mod
    return transformer_mod.build_transformer(objective, params)


# name -> (factory callable, module import name required for availability)
CANDIDATES = {
    "lgbm": (_lgbm_factory, "lightgbm"),
    "ridge": (classical.RidgeRegressorFactory(), "sklearn"),
    "xgb": (gbdt.XgbRegressorFactory(), "xgboost"),
    "catboost": (gbdt.CatBoostRegressorFactory(), "catboost"),
    "mlp": (_mlp_factory, "torch"),
    "rnn": (_rnn_factory, "torch"),
    "transformer": (_transformer_factory, "torch"),
}


def is_available(name: str) -> bool:
    """True iff `name` is a known candidate whose required package resolves
    in the current environment. Never raises for an unknown/unavailable
    name -- returns False instead, so `models/bracket/gate.py::run_gate` can
    skip a candidate cleanly (`"status": "unavailable"`) on a machine
    without the dev-only `requirements-experiments.txt` lockfile installed."""
    if name not in CANDIDATES:
        return False
    _, import_name = CANDIDATES[name]
    return importlib.util.find_spec(import_name) is not None


def build_regressor(name: str, objective: str, params: dict):
    """Return an unfitted stage-2 regressor for `name`, exposing sklearn's
    `fit`/`predict`. Raises `ValueError` naming the bad name and listing
    valid keys (`config.resolve_experiments`'s own error-message style) for
    an unrecognised name -- this is a programmer error (a typo'd candidate
    name), never an expected runtime state; an unavailable-but-known
    candidate is instead handled by `is_available`, not by this function."""
    if name not in CANDIDATES:
        raise ValueError(
            f"unknown bracket candidate '{name}' -- valid keys: {sorted(CANDIDATES)}")
    factory, _ = CANDIDATES[name]
    return factory(objective, params)
