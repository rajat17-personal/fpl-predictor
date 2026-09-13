"""Phase 10 plan 10-10: the XGBoost and CatBoost stage-2 candidates (D-12).

Both packages passed the D-16 blocking-human package-legitimacy gate
(10-10-PLAN.md Task 1) and are installed only from the dev-only hash-locked
`requirements-experiments.txt` (never `requirements.txt`/`requirements-dev.txt`,
never Docker/CI -- see that file's own header). `models/bracket/registry.py`'s
`is_available()` lets a caller skip either candidate cleanly on a machine
without that lockfile installed.

D-19 budget: "sensible LightGBM-adjacent defaults, low expected delta,
cheap" -- both factories below mirror `models/train.py::_LGB_COMMON`'s
depth/learning-rate/subsample neighbourhood rather than tuning either
library. No hyperparameter search is run here; that is a deliberate
allocation, not an oversight.
"""
from __future__ import annotations

# Our stage-2 objective tags (models/train.py::STAGE2_OBJECTIVES) are passed
# through as LightGBM's own objective strings ("regression_l1" = median/L1,
# "regression" = mean/L2) -- these two maps translate that vocabulary onto
# each library's own loss-function name, so this file never invents a third
# objective-tag vocabulary.
_XGB_OBJECTIVE = {"regression_l1": "reg:absoluteerror", "regression": "reg:squarederror"}
_CAT_LOSS = {"regression_l1": "MAE", "regression": "RMSE"}

# D-19: LightGBM-adjacent neighbourhood, not tuned. num_leaves=31 in
# _LGB_COMMON is roughly a full depth-5 binary tree (2**5=32 leaves), so
# max_depth=5 here targets the same tree-size ballpark; learning_rate,
# subsample and colsample mirror _LGB_COMMON's values directly.
_XGB_PARAMS = dict(n_estimators=1500, learning_rate=0.03, max_depth=5,
                   subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
                   reg_lambda=1.0, n_jobs=-1, verbosity=0)

_CAT_PARAMS = dict(iterations=1500, learning_rate=0.03, depth=5,
                   subsample=0.8, colsample_bylevel=0.8, reg_lambda=1.0,
                   bootstrap_type="Bernoulli", thread_count=-1, verbose=False)

# LightGBM's own patience (models/train.py: early_stopping(50, verbose=False))
# -- matched exactly, not re-tuned, per D-19.
_EARLY_STOPPING_ROUNDS = 50


class XgbRegressorFactory:
    """Builds an unfitted `xgboost.XGBRegressor` for the "xgb" bracket
    candidate. `early_stopping_rounds` is set at construction (this
    library's own convention) so `models/train.py`'s fit call can pass a
    plain `eval_set=[(vaX, vaY)]`, matching LightGBM's `early_stopping(50)`
    patience."""

    def __call__(self, objective: str, params: dict):
        del params  # LightGBM's _LGB_COMMON keys don't map onto XGBoost's
        import xgboost as xgb
        return xgb.XGBRegressor(objective=_XGB_OBJECTIVE[objective],
                                early_stopping_rounds=_EARLY_STOPPING_ROUNDS,
                                **_XGB_PARAMS)


class CatBoostRegressorFactory:
    """Builds an unfitted `catboost.CatBoostRegressor` for the "catboost"
    bracket candidate. `early_stopping_rounds` is set at construction so
    `models/train.py`'s fit call can pass a plain `eval_set=(vaX, vaY)`,
    matching LightGBM's `early_stopping(50)` patience."""

    def __call__(self, objective: str, params: dict):
        del params  # LightGBM's _LGB_COMMON keys don't map onto CatBoost's
        from catboost import CatBoostRegressor
        return CatBoostRegressor(loss_function=_CAT_LOSS[objective],
                                 early_stopping_rounds=_EARLY_STOPPING_ROUNDS,
                                 **_CAT_PARAMS)
