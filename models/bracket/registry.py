"""Phase 10 plan 10-10: the stage-2 regressor swap registry (D-12).

`models/train.py::train_position`'s new `stage2` parameter calls through
`build_regressor` -- this is the ONE swap seam: the stage-1 P(play)
classifier, the calibration path, and the `ComponentModel` DEF/GK structure
are all untouched, and only the conditional-points regressor construction
is routed through here.

`CANDIDATES` intentionally contains only the candidates this plan actually
builds (`lgbm`, `ridge`, `xgb`, `catboost`); `config.BRACKET_CANDIDATES`
additionally reserves `mlp`/`rnn`/`transformer` names for future plans
(10-11/10-13) that are not yet built and are not in `CANDIDATES` -- callers
must always check `set(registry.CANDIDATES) <= set(config.BRACKET_CANDIDATES)`,
never the reverse.
"""
from __future__ import annotations

import importlib.util

from models.bracket import classical, gbdt


def _lgbm_factory(objective: str, params: dict):
    """The shipped candidate -- byte-equivalent to `models/train.py`'s own
    pre-bracket `LGBMRegressor(objective=objective, **params)` construction."""
    from lightgbm import LGBMRegressor
    return LGBMRegressor(objective=objective, **params)


# name -> (factory callable, module import name required for availability)
CANDIDATES = {
    "lgbm": (_lgbm_factory, "lightgbm"),
    "ridge": (classical.RidgeRegressorFactory(), "sklearn"),
    "xgb": (gbdt.XgbRegressorFactory(), "xgboost"),
    "catboost": (gbdt.CatBoostRegressorFactory(), "catboost"),
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
