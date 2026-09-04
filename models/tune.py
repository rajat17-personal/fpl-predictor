"""Small, validation-scored hyperparameter search for the xP model.

Scores by Spearman rank correlation on the validation season (2024-25) — ranking
quality is what the optimizer actually consumes, not absolute MAE. Only the median
stage-2 objective is trained here (the backtest winner) to keep the search fast.
Early stopping uses the same validation season, so scores are mildly optimistic but
uniformly so, which is fine for RANKING hyperparameter combos.

Never touches the test season (2025-26). After picking, confirm once on walk-forward.

Run:
  python -m models.tune --iters 24
"""
from __future__ import annotations

import argparse
import random
import sys

import pandas as pd

import config
from models.train import load_features, train_predict

SEARCH = {
    "learning_rate": [0.02, 0.03, 0.05, 0.08],
    "num_leaves": [15, 31, 63, 127],
    "min_child_samples": [20, 40, 80, 150],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "subsample": [0.7, 0.8, 1.0],
    "reg_lambda": [0.0, 1.0, 5.0],
}
FIXED = dict(n_estimators=2000, subsample_freq=1, n_jobs=-1, verbosity=-1)
MED = {"med": "regression_l1"}


def _score(df, params) -> float:
    te, _, _ = train_predict(df, config.TRAIN_SEASONS, config.VAL_SEASON,
                             [config.VAL_SEASON], params=params, objectives=MED)
    return pd.Series(te.xp_med.values).corr(pd.Series(te.y_points.values), method="spearman")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    random.seed(args.seed)

    df = load_features()
    base = dict(FIXED, learning_rate=0.03, num_leaves=31, min_child_samples=40,
                colsample_bytree=0.8, subsample=0.8, reg_lambda=1.0)
    base_score = _score(df, base)
    print(f"baseline Spearman (current params): {base_score:.4f}\n")

    results = []
    seen = set()
    for i in range(args.iters):
        combo = {k: random.choice(v) for k, v in SEARCH.items()}
        key = tuple(sorted(combo.items()))
        if key in seen:
            continue
        seen.add(key)
        params = dict(FIXED, **combo)
        s = _score(df, params)
        results.append((s, combo))
        print(f"[{i+1:2}/{args.iters}] Spearman={s:.4f}  {combo}", flush=True)

    results.sort(reverse=True)
    print("\n=== top 5 ===")
    for s, combo in results[:5]:
        print(f"  {s:.4f}  {combo}")
    best_s, best = results[0]
    print(f"\nbest Spearman={best_s:.4f} (baseline {base_score:.4f}, "
          f"delta {best_s - base_score:+.4f})")
    print("paste into _LGB_COMMON:", dict(best, n_estimators=1500, subsample_freq=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
