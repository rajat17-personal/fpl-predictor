"""Phase 3: two-stage, per-position expected-points (xP) model.

Structure — a hurdle model that bakes in the rule "a player who doesn't play
scores exactly 0":

    xP = P(play) * E[points | played]

  Stage 1  (classifier, per position): p_play = P(minutes > 0)
  Stage 2  (regressor,  per position): conditional points, trained ONLY on
           fixtures the player actually played.

Both stages are LightGBM, trained separately for GK/DEF/MID/FWD because scoring
dynamics differ wildly by position. Validation is strictly time-based: train on
old seasons, early-stop on a later season, evaluate on the most recent one.
Never random splits (that leaks the future).

Run (after features.engineer):
  python -m models.train
"""
from __future__ import annotations

import sys

import joblib
import numpy as np
import pandas as pd
from lightgbm import (LGBMClassifier, LGBMRanker, early_stopping,
                      log_evaluation)
from sklearn.isotonic import IsotonicRegression

import config
from models.bracket import registry as bracket_registry

ARTIFACTS = config.ROOT / "models" / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

# Columns that are identifiers or targets — never fed to the model.
_EXCLUDE = {
    "season", "player_key", "player_code", "player_id", "name", "team",
    "position", "fixture_id", "kickoff_time",
    "y_points", "y_minutes", "y_played", "y_started", "y_clean_sheets",
    "xp_fpl",  # FPL's own prediction — evaluation baseline only, not a feature
}

_LGB_COMMON = dict(n_estimators=1500, learning_rate=0.03, num_leaves=31,
                   subsample=0.8, subsample_freq=1,   # freq>=1 actually enables row bagging
                   colsample_bytree=0.8, min_child_samples=40,
                   reg_lambda=1.0, n_jobs=-1, verbosity=-1)


def feature_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in _EXCLUDE]


def _prep(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    x = df[cols].copy()
    for c in ("was_home", "is_dgw"):
        if c in x.columns:
            x[c] = x[c].astype("float32")
    return x


def load_features() -> pd.DataFrame:
    """Feature matrix + FPL's own per-fixture xP attached as an evaluation baseline
    only (never a model feature — that would just be copying FPL's model)."""
    df = pd.read_parquet(config.PROCESSED_DIR / "features.parquet")
    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet")
    return df.merge(raw[["season", "player_id", "fixture_id", "xp_fpl"]],
                    on=["season", "player_id", "fixture_id"], how="left")


def train_predict(df: pd.DataFrame, train_seasons, val_season, test_seasons,
                  params: dict | None = None, objectives: dict | None = None,
                  minutes_model: str = "binary", calibrate: bool = False,
                  stage2: str = "lgbm"):
    """Train per-position two-stage models on the given split and return the test
    rows with xp_<tag> columns added, plus the models and feature list.

    stage2: passthrough to `train_position`'s D-12 model-class bracket seam."""
    objectives = objectives or STAGE2_OBJECTIVES
    cols = feature_cols(df)
    tr = df[df.season.isin(train_seasons)]
    va = df[df.season == val_season]
    te = df[df.season.isin(test_seasons)].copy()
    models = {pos: train_position(pos, tr, va, cols, params, objectives,
                                  minutes_model=minutes_model, calibrate=calibrate,
                                  stage2=stage2)
              for pos in config.POSITIONS}
    for tag in objectives:
        te[f"xp_{tag}"] = predict_xp(models, te, cols, tag)
    return te, models, cols


# Stage-2 objectives to build, so the Phase-6 backtest can compare which picks
# more points: "med" = L1/median (best MAE, biased low), "mean" = L2/expected
# value (what you actually want to maximise; handles negative points e.g. cards).
# "rank" (opt-in, not default) = LambdaRank ordering calibrated back to points —
# aligns training with the selection task; adding it never changes med/mean.
STAGE2_OBJECTIVES = {"med": "regression_l1", "mean": "regression"}


class RankCalibrated:
    """A LambdaRank model whose ordering scores are mapped back to point units
    (isotonic on validation) so they stay comparable across positions for the knapsack."""

    def __init__(self, ranker, iso):
        self.ranker, self.iso = ranker, iso

    def predict(self, X):
        return self.iso.predict(self.ranker.predict(X))


class ComponentModel:
    """DEF/GK conditional points = E[non-clean-sheet points] + P(clean sheet)*4.
    The clean-sheet part comes from a dedicated classifier that consumes the odds
    directly, instead of being diluted inside a single generic points regressor."""

    CS_VALUE = 4          # FPL clean-sheet points for DEF and GK

    def __init__(self, cs_clf, resid_reg):
        self.cs_clf, self.resid_reg = cs_clf, resid_reg

    def predict(self, X):
        p_cs = self.cs_clf.predict_proba(X)[:, 1]
        return self.resid_reg.predict(X) + p_cs * self.CS_VALUE


def _train_cs_component(trp_p, vap_p, cols, params, stage2: str = "lgbm"):
    """Clean-sheet classifier + residual (non-CS) points regressor, for DEF/GK.

    The clean-sheet classifier stays LightGBM regardless of `stage2` -- only
    the residual points regressor is swappable (D-12's "one swap seam" never
    touches a classifier)."""
    ytr, yva = trp_p.y_clean_sheets, vap_p.y_clean_sheets
    clf = LGBMClassifier(**params)
    clf.fit(_prep(trp_p, cols), ytr, eval_set=[(_prep(vap_p, cols), yva)],
            eval_metric="binary_logloss",
            callbacks=[early_stopping(50, verbose=False), log_evaluation(0)])

    rtr = trp_p.y_points - ComponentModel.CS_VALUE * trp_p.y_clean_sheets
    rva = vap_p.y_points - ComponentModel.CS_VALUE * vap_p.y_clean_sheets
    reg = bracket_registry.build_regressor(stage2, "regression_l1", params)
    _fit_stage2(stage2, reg, _prep(trp_p, cols), rtr, _prep(vap_p, cols), rva)
    return ComponentModel(clf, reg), getattr(reg, "best_iteration_", None)


def _train_ranker(trp_p, vap_p, cols, params):
    """Rank players within each (season, gw) by points, then calibrate to points."""
    tr = trp_p.sort_values(["season", "gw"])
    va = vap_p.sort_values(["season", "gw"])
    gtr = tr.groupby(["season", "gw"], sort=True).size().values
    gva = va.groupby(["season", "gw"], sort=True).size().values
    ytr = tr.y_points.clip(lower=0, upper=30).round().astype(int)
    yva = va.y_points.clip(lower=0, upper=30).round().astype(int)
    rk = LGBMRanker(objective="lambdarank", label_gain=list(range(31)), **params)
    rk.fit(_prep(tr, cols), ytr, group=gtr,
           eval_set=[(_prep(va, cols), yva)], eval_group=[gva], eval_at=[11],
           callbacks=[early_stopping(50, verbose=False), log_evaluation(0)])
    iso = IsotonicRegression(out_of_bounds="clip").fit(
        rk.predict(_prep(va, cols)), va.y_points.values)
    return RankCalibrated(rk, iso), rk.best_iteration_


class _ConstantModel:
    """Fallback regressor when a segment has too few rows (e.g. GK cameos)."""

    def __init__(self, value: float):
        self.value = float(value)

    def predict(self, X):
        return np.full(len(X), self.value)


def _fit_reg(objective, params, trX, trY, vaX, vaY, stage2: str = "lgbm"):
    reg = bracket_registry.build_regressor(stage2, objective, params)
    _fit_stage2(stage2, reg, trX, trY, vaX, vaY)
    return reg


def _fit_stage2(stage2: str, reg, trX, trY, vaX, vaY):
    """Fit an unfitted stage-2 regressor from `models.bracket.registry.
    build_regressor` on the given train/val split.

    `stage2="lgbm"` fits via the EXACT same call LightGBM's stage-2
    regressor always used pre-bracket (`early_stopping(50)` callback,
    `eval_metric="l1"`) -- this is the identical code path stage2="lgbm"
    always took, not merely an equivalent one, so the shipped path is
    byte-unchanged. Every challenger uses its own library's early-stopping
    mechanism at the SAME patience (D-19 allocates no search budget beyond
    matching it): XGBoost's `early_stopping_rounds` is set at construction
    (models/bracket/gbdt.py) so a plain `eval_set` here is enough; CatBoost's
    is also set at construction. Ridge (no boosting, no early stopping) just
    fits once on the training split -- it ignores `vaX`/`vaY` entirely.
    """
    if stage2 == "lgbm":
        reg.fit(trX, trY, eval_set=[(vaX, vaY)], eval_metric="l1",
                callbacks=[early_stopping(50, verbose=False), log_evaluation(0)])
    elif stage2 == "xgb":
        reg.fit(trX, trY, eval_set=[(vaX, vaY)], verbose=False)
    elif stage2 == "catboost":
        reg.fit(trX, trY, eval_set=(vaX, vaY), verbose=False)
    else:
        reg.fit(trX, trY)
    return reg


def _train_3state(pos, trp, vap, cols, params, objectives, stage2: str = "lgbm"):
    """C.1 minutes upgrade: no-play / cameo (<60) / start (>=60) classifier, with
    separate conditional-points regressors for starts and cameos:
        xP = P(start)·E[pts|start] + P(cameo)·E[pts|cameo]
    """
    y3tr = (trp.y_played + trp.y_started).astype(int)   # 0 none, 1 cameo, 2 start
    y3va = (vap.y_played + vap.y_started).astype(int)
    clf = LGBMClassifier(**params)
    clf.fit(_prep(trp, cols), y3tr, eval_set=[(_prep(vap, cols), y3va)],
            eval_metric="multi_logloss",
            callbacks=[early_stopping(50, verbose=False), log_evaluation(0)])

    seg = {
        "start": (trp[trp.y_started == 1], vap[vap.y_started == 1]),
        "cameo": (trp[(trp.y_played == 1) & (trp.y_started == 0)],
                  vap[(vap.y_played == 1) & (vap.y_started == 0)]),
    }
    regs_start, regs_cameo = {}, {}
    for tag, objective in objectives.items():
        if objective in ("rank", "cs"):
            raise ValueError(f"objective '{objective}' unsupported with 3-state minutes")
        for name, store in (("start", regs_start), ("cameo", regs_cameo)):
            t, v = seg[name]
            if len(t) < 200 or len(v) < 50:      # thin segment (e.g. GK cameos)
                store[tag] = _ConstantModel(t.y_points.mean() if len(t) else 1.0)
            else:
                store[tag] = _fit_reg(objective, params, _prep(t, cols), t.y_points,
                                      _prep(v, cols), v.y_points, stage2=stage2)
    return {"kind": "3state", "clf": clf, "regs_start": regs_start,
            "regs_cameo": regs_cameo, "clf_best": clf.best_iteration_,
            "reg_best": {}}


def train_position(pos: str, tr: pd.DataFrame, va: pd.DataFrame, cols: list[str],
                   params: dict | None = None, objectives: dict | None = None,
                   minutes_model: str = "binary", calibrate: bool = False,
                   stage2: str = "lgbm"):
    """Train stage-1 (minutes) and stage-2 conditional-points regressor(s).

    minutes_model: "binary" (default, P(play)) or "3state" (no-play/cameo/start).
    calibrate: isotonic-recalibrate binary P(play) on the validation season
    (fixes the DEF under-confidence found by models.calibration).
    stage2: the D-12 model-class bracket's swap seam -- one of
    `models.bracket.registry.CANDIDATES` ("lgbm" default, "ridge", "xgb",
    "catboost"). Only the conditional-points regressor is swapped; the
    stage-1 P(play) classifier above is LightGBM in every case, and
    stage2="lgbm" takes the exact pre-bracket code path (byte-equivalent,
    not merely equivalent).
    """
    params = params or _LGB_COMMON
    objectives = objectives or STAGE2_OBJECTIVES
    trp, vap = tr[tr.position == pos], va[va.position == pos]

    if minutes_model == "3state":
        return _train_3state(pos, trp, vap, cols, params, objectives, stage2=stage2)

    # Stage 1: probability the player features in the match at all.
    clf = LGBMClassifier(**params)
    clf.fit(_prep(trp, cols), trp.y_played,
            eval_set=[(_prep(vap, cols), vap.y_played)],
            eval_metric="binary_logloss",
            callbacks=[early_stopping(50, verbose=False), log_evaluation(0)])
    cal = None
    if calibrate:
        p_va = clf.predict_proba(_prep(vap, cols))[:, 1]
        cal = IsotonicRegression(out_of_bounds="clip").fit(p_va, vap.y_played)

    # Stage 2: expected points GIVEN the player played (played rows only).
    trp_p, vap_p = trp[trp.y_played == 1], vap[vap.y_played == 1]
    regs, best = {}, {}
    for tag, objective in objectives.items():
        if objective == "rank":
            regs[tag], best[tag] = _train_ranker(trp_p, vap_p, cols, params)
            continue
        if objective == "cs":     # dedicated clean-sheet decomposition for DEF/GK
            if pos in ("GK", "DEF"):
                regs[tag], best[tag] = _train_cs_component(trp_p, vap_p, cols, params,
                                                            stage2=stage2)
            else:                 # MID/FWD: clean sheets negligible -> plain L1
                reg = bracket_registry.build_regressor(stage2, "regression_l1", params)
                _fit_stage2(stage2, reg, _prep(trp_p, cols), trp_p.y_points,
                           _prep(vap_p, cols), vap_p.y_points)
                regs[tag], best[tag] = reg, getattr(reg, "best_iteration_", None)
            continue
        reg = bracket_registry.build_regressor(stage2, objective, params)
        _fit_stage2(stage2, reg, _prep(trp_p, cols), trp_p.y_points,
                   _prep(vap_p, cols), vap_p.y_points)
        regs[tag] = reg
        best[tag] = getattr(reg, "best_iteration_", None)

    return {"clf": clf, "regs": regs, "cal": cal,
            "clf_best": clf.best_iteration_, "reg_best": best}


def predict_xp(models: dict, df: pd.DataFrame, cols: list[str], tag: str) -> pd.Series:
    """Expected points for stage-2 objective `tag`, per position.

    binary:  xP = P(play) · E[pts | played]        (optionally recalibrated)
    3state:  xP = P(start)·E[pts|start] + P(cameo)·E[pts|cameo]
    """
    xp = pd.Series(np.nan, index=df.index, dtype="float64")
    for pos, m in models.items():
        idx = df.index[df.position == pos]
        if len(idx) == 0:
            continue
        x = _prep(df.loc[idx], cols)
        if m.get("kind") == "3state":
            proba = m["clf"].predict_proba(x)
            col = {c: i for i, c in enumerate(m["clf"].classes_)}
            xp.loc[idx] = (proba[:, col[2]] * m["regs_start"][tag].predict(x)
                           + proba[:, col[1]] * m["regs_cameo"][tag].predict(x))
        else:
            p_play = m["clf"].predict_proba(x)[:, 1]
            if m.get("cal") is not None:
                p_play = m["cal"].predict(p_play)
            xp.loc[idx] = p_play * m["regs"][tag].predict(x)
    return xp


def _report(name: str, y_true, y_pred) -> dict:
    yt = np.asarray(y_true, dtype="float64")
    yp = np.asarray(y_pred, dtype="float64")
    err = yp - yt
    mae = np.abs(err).mean()
    rmse = np.sqrt((err ** 2).mean())
    corr = pd.Series(yp).corr(pd.Series(yt), method="spearman")
    print(f"  {name:28} MAE={mae:.3f}  RMSE={rmse:.3f}  Spearman={corr:.3f}")
    return {"mae": mae, "rmse": rmse, "spearman": corr}


def main() -> int:
    df = load_features()
    # calibrate=True: isotonic P(play) recalibration on the validation season —
    # fixes the measured DEF under-confidence, strictly better fixture metrics.
    te, models, cols = train_predict(df, config.TRAIN_SEASONS,
                                     config.VAL_SEASON, config.TEST_SEASONS,
                                     calibrate=True)
    print(f"features: {len(cols)} | train seasons={config.TRAIN_SEASONS} "
          f"val={config.VAL_SEASON} test={config.TEST_SEASONS}")
    for pos in config.POSITIONS:
        print(f"[{pos}] stage1 best_iter={models[pos]['clf_best']}  "
              f"stage2 best_iter={models[pos]['reg_best']}")
    joblib.dump({"models": models, "cols": cols}, ARTIFACTS / "xp_model.joblib")

    # --- Evaluation on the untouched test season (fixture level) ---
    print(f"\n=== TEST ({config.TEST_SEASONS[0]}) fixture-level, n={len(te):,} ===")
    _report("our xP (median obj)", te.y_points, te.xp_med)
    _report("our xP (mean obj)", te.y_points, te.xp_mean)
    _report("baseline: FPL xp_fpl", te.y_points, te.xp_fpl)
    _report("baseline: points_r5", te.y_points, te.total_points_r5.fillna(0))
    print(f"  mean predicted:  median-obj={te.xp_med.mean():.2f}  "
          f"mean-obj={te.xp_mean.mean():.2f}  actual={te.y_points.mean():.2f}")

    # Played-only view: ~60% of rows are 0-minute rows the model trivially ranks
    # last, which inflates the headline Spearman. This is the honest ranking number.
    played = te[te.y_minutes > 0]
    print(f"\n  played-only (n={len(played):,}):")
    _report("  our xP (median obj)", played.y_points, played.xp_med)
    _report("  baseline: FPL xp_fpl", played.y_points, played.xp_fpl)

    # --- GW level: sum fixture xP per player-gameweek (handles DGW/blank) ---
    gw = (te.groupby(["player_code", "gw"])
          .agg(xp_med=("xp_med", "sum"), xp_mean=("xp_mean", "sum"),
               fpl=("xp_fpl", "sum"), actual=("y_points", "sum")).reset_index())
    print(f"\n=== TEST GW-level, n={len(gw):,} player-gameweeks ===")
    _report("our xP (median obj)", gw.actual, gw.xp_med)
    _report("our xP (mean obj)", gw.actual, gw.xp_mean)
    _report("baseline: FPL xp_fpl", gw.actual, gw.fpl)

    # Persist test predictions for the Phase-4 optimizer backtest (both variants).
    te["xp_form"] = te["total_points_r5"].fillna(0)   # naive baseline: recent form
    keep = ["season", "gw", "player_code", "player_id", "name", "team",
            "position", "price_m", "y_points", "y_minutes",
            "xp_med", "xp_mean", "xp_form", "xp_fpl"]
    te[keep].to_parquet(config.PROCESSED_DIR / "test_predictions.parquet", index=False)
    print(f"\nsaved model -> {(ARTIFACTS/'xp_model.joblib').relative_to(config.ROOT)}")
    print("saved preds -> data/processed/test_predictions.parquet")
    print("Next: Phase 4 optimizer (optimize/squad_ilp.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
