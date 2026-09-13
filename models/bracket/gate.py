"""Phase 10 plan 10-10: the D-15 stage-1 cheap gate.

Decides which `models.bracket.registry.CANDIDATES` challenger earns a full
6-season walk-forward, at the cost of one validation-split fit per
candidate instead of a full retrain. `run_gate` trains on
`config.TRAIN_SEASONS` and evaluates on `config.VAL_SEASON` ONLY -- it never
touches `config.TEST_SEASONS` (["2025-26"], the shipped model's held-out
season), asserted below and re-checked by
`tests/test_bracket.py::test_gate_never_trains_on_a_test_season`.

Deliberately checked against `config.TEST_SEASONS`, NOT
`backtest.walk_forward.TEST_SEASONS` -- the latter is a DIFFERENT concept
(the 6 rolling seasons the walk-forward backtest retrains per-season
against, using only data strictly before each one) that legitimately
OVERLAPS `config.TRAIN_SEASONS` by design (2020-21..2023-24 are both a
walk-forward test season AND part of the shipped model's fixed training
window). The invariant this gate protects is "never trains on the model's
real held-out season", which is `config.TEST_SEASONS` alone.

Run:
  python -m models.bracket.gate
  python -m models.bracket.gate --candidate lgbm --candidate ridge
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np
from scipy.stats import spearmanr

import config
from backtest.walk_forward import apply_experiment_feature_gating
from models import train as train_module
from models.bracket import classical, gbdt
from models.bracket import registry as bracket_registry
from models.train import load_features, train_predict
from ops.jsonio import write_json

# D-15: "A candidate advances only when its Spearman is at least LightGBM's
# baseline plus 0.010." MAE is computed and recorded as a diagnostic ONLY --
# it never appears in the advance decision, because the selection task this
# project actually performs is a RANKING task (the squad ILP picks by rank,
# not by absolute error), which is the whole finding the 0.383-vs-0.579
# xp_fpl/our-xP Spearman gap (IMPROVEMENTS.md) surfaced: a candidate with a
# better MAE and a worse Spearman does not advance.
GATE_MARGIN = 0.010

# The resolved hyperparameter dict actually used for each candidate, logged
# in models/tune.py's own style so a future reader knows exactly what was
# fitted. Non-lgbm factories ignore the incoming LightGBM `_LGB_COMMON` dict
# (see classical.py/gbdt.py's own factory docstrings) and use these fixed,
# untuned (D-19) dicts instead.
_RESOLVED_PARAMS = {
    "lgbm": train_module._LGB_COMMON,
    "ridge": classical._RIDGE_PARAMS,
    "xgb": gbdt._XGB_PARAMS,
    "catboost": gbdt._CAT_PARAMS,
}

# Passing VAL_SEASON as BOTH the early-stopping split and the evaluation
# split is deliberate: it is a RELATIVE comparison between candidates that
# all share the identical handicap (every candidate sees the same
# in-sample optimism), and it never touches a test season. The resulting
# absolute Spearman figure is therefore optimistic and is NOT comparable to
# the 0.383 pooled played-only test-season number (IMPROVEMENTS.md) -- this
# label makes that non-comparability explicit in every recorded result so a
# ledger reader cannot confuse the two.
EVAL_SPLIT_LABEL = "val_season_in_sample_early_stopping"


def played_only_spearman(y_true, y_pred, minutes) -> float:
    """Played-only (`minutes > 0`) Spearman rank correlation, using the
    IDENTICAL `scipy.stats.spearmanr(...).statistic` call form
    `backtest/benchmark_external.py::_stats_block` uses -- one metric
    definition everywhere in this project, never a fourth near-identical
    helper. (`models/train.py::_report`'s `Series.corr(method="spearman")`
    form agrees numerically with this scipy form; the scipy form is chosen
    here so every Phase 10 Spearman in the experiment ledger comes from one
    call site.)
    """
    yt = np.asarray(y_true, dtype="float64")
    yp = np.asarray(y_pred, dtype="float64")
    m = np.asarray(minutes, dtype="float64") > 0
    return float(spearmanr(yp[m], yt[m]).statistic)


def run_gate(candidate: str, *, df=None) -> dict:
    """Train `candidate` on `config.TRAIN_SEASONS`, evaluate on
    `config.VAL_SEASON`, and record a same-split gate result. Never touches
    `config.TEST_SEASONS` -- an `AssertionError` fires before any training
    if that invariant is ever violated by a future edit to this function or
    to `config.TRAIN_SEASONS`/`config.VAL_SEASON`.
    """
    assert not (set(config.TRAIN_SEASONS) & set(config.TEST_SEASONS)), (
        f"run_gate must never train on a config.TEST_SEASONS member: "
        f"{set(config.TRAIN_SEASONS) & set(config.TEST_SEASONS)}")
    assert config.VAL_SEASON not in config.TEST_SEASONS, (
        f"run_gate must never evaluate on a config.TEST_SEASONS member: {config.VAL_SEASON}")

    base_result = {
        "candidate": candidate,
        "eval_split": EVAL_SPLIT_LABEL,
        "train_seasons": list(config.TRAIN_SEASONS),
        "val_season": config.VAL_SEASON,
        "params": _RESOLVED_PARAMS.get(candidate),
    }

    if not bracket_registry.is_available(candidate):
        result = {
            **base_result,
            "status": "unavailable",
            "spearman_xp_med": None,
            "mae_xp_med": None,
            "n_played_rows": 0,
            "wall_clock_s": 0.0,
        }
        _write_result(candidate, result)
        return result

    t0 = time.monotonic()
    d = load_features() if df is None else df
    # D-03: the bracket answers a MODEL-CLASS question on the shipped
    # feature set, not one that also happens to include an unadopted Tier-1
    # enrichment family -- every experiment flag is forced off here, so a
    # candidate's gate result is never confounded by a feature-set change.
    d = apply_experiment_feature_gating(d, config.resolve_experiments("none"))

    te, _models, _cols = train_predict(
        d, config.TRAIN_SEASONS, config.VAL_SEASON, [config.VAL_SEASON],
        objectives={"med": "regression_l1", "mean": "regression"},
        calibrate=True, stage2=candidate)
    wall_clock_s = round(time.monotonic() - t0, 2)

    played = te[te.y_minutes > 0]
    spearman = played_only_spearman(played.y_points, played.xp_med, played.y_minutes)
    mae = float((played.xp_med - played.y_points).abs().mean())

    result = {
        **base_result,
        "status": "ok",
        "spearman_xp_med": round(spearman, 4),
        "mae_xp_med": round(mae, 4),
        "n_played_rows": int(len(played)),
        "wall_clock_s": wall_clock_s,
    }
    _write_result(candidate, result)
    return result


def _write_result(candidate: str, result: dict) -> None:
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(result, config.EXPERIMENTS_DIR / f"bracket_gate_{candidate}.json", indent=1)


def _advances(candidate_spearman: float | None, baseline_spearman: float) -> bool:
    """The D-15 mechanical advance rule, factored out for direct testing
    without requiring a real training run: ADVANCE iff
    `candidate_spearman >= baseline_spearman + GATE_MARGIN`. `None` (an
    unavailable candidate) never advances."""
    if candidate_spearman is None:
        return False
    return candidate_spearman >= baseline_spearman + GATE_MARGIN


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", action="append", dest="candidates",
                    choices=sorted(bracket_registry.CANDIDATES),
                    help="repeatable; defaults to lgbm, ridge, xgb, catboost")
    args = ap.parse_args(argv)
    candidates = args.candidates or ["lgbm", "ridge", "xgb", "catboost"]

    df = load_features()
    results = {}
    for c in candidates:
        print(f"[bracket gate] running {c} ...", flush=True)
        results[c] = run_gate(c, df=df)

    baseline = results.get("lgbm", {}).get("spearman_xp_med")
    print(f"\n{'candidate':10} {'status':12} {'spearman':>9} {'delta':>8} "
          f"{'mae':>8}  verdict")
    for c, r in results.items():
        s = r["spearman_xp_med"]
        delta = None if (s is None or baseline is None) else round(s - baseline, 4)
        verdict = ("ADVANCE" if baseline is not None and _advances(s, baseline)
                   else "HOLD")
        s_str = "n/a" if s is None else f"{s:.4f}"
        d_str = "n/a" if delta is None else f"{delta:+.4f}"
        mae_str = "n/a" if r["mae_xp_med"] is None else f"{r['mae_xp_med']:.4f}"
        print(f"{c:10} {r['status']:12} {s_str:>9} {d_str:>8} {mae_str:>8}  {verdict}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
