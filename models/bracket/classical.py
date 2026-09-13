"""Phase 10 plan 10-10: the Ridge stage-2 candidate (D-12).

A linear baseline for the model-class bracket -- the cheapest possible
challenger to LightGBM's tree-based stage-2 regressor, and the only
candidate that needs no new PyPI package (`sklearn` is already a project
dependency, so this file alone never triggers the D-16 package-legitimacy
gate).
"""
from __future__ import annotations

from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# D-19: sensible, low-effort defaults -- no search budget spent tuning a
# candidate that exists to answer "does model CLASS matter at all", not to
# be individually optimal. alpha=1.0 is sklearn's own Ridge default.
_RIDGE_PARAMS = dict(alpha=1.0, random_state=0)


class RidgeRegressorFactory:
    """Builds the stage-2 regressor Pipeline for the "ridge" bracket
    candidate.

    Ridge (and any other linear model) cannot consume NaN, and this
    project's feature matrix is full of LEGITIMATE NaN: first appearances
    have no rolling features by construction (features/engineer.py's
    `_roll` shift-then-rolling has nothing to look back on), and the
    availability family (config.AVAILABILITY_COLS) is NaN wherever no
    snapshot qualified. So this factory returns an
    `sklearn.pipeline.Pipeline` of `SimpleImputer(strategy="median",
    add_indicator=True)` -> `StandardScaler()` -> `Ridge`.

    `add_indicator=True` matters: without it, imputation destroys the
    missingness signal `tests/test_leakage.py::
    test_first_appearance_has_no_rolling_features` proves is
    information-bearing (a first appearance's NaN-ness is itself
    predictive, not merely an artefact to paper over). Do not "simplify"
    this to a bare `SimpleImputer(strategy="median")` -- that would
    silently discard that signal for every linear candidate.
    """

    def __call__(self, objective: str, params: dict) -> Pipeline:
        # `objective` (LightGBM's "regression_l1"/"regression" tags) and
        # `params` (LightGBM's tree hyperparameters) have no Ridge
        # equivalent -- Ridge has exactly one loss (squared error) and no
        # boosting hyperparameters, so both arguments are accepted only for
        # interface parity with the GBDT factories in gbdt.py and are
        # otherwise unused here.
        del objective, params
        return Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
            ("ridge", Ridge(**_RIDGE_PARAMS)),
        ])
