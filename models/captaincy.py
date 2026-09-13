"""Phase 9: captaincy ceiling EV -- an upside-weighted armband value.

The captain slot doubles points, so the naive optimum is E[points] (`xp_mean`,
adopted in Phase 6). But a manager choosing between two similar-mean captains
often prefers the one with higher UPSIDE, since the armband only pays off big
on a good week. This module attaches a `xp_capt_ceiling` column that blends
mean value with a fraction of the player's p90 upside:

    xp_capt_ceiling = xp_mean + CEILING_LAMBDA * (p90 - xp_med)

No new sub-model, no retraining: this reuses `models/intervals.py`'s existing
empirical p10-p90 quantile machinery as a post-hoc column. That discipline is
deliberate -- IMPROVEMENTS.md Phase C's clean-sheet decomposition (-50/season)
is exactly what happens when a captaincy idea gets its own trained sub-model
instead of riding the existing xP + intervals pipeline.

Leakage note: `models/intervals.py`'s shipped artifact (models/artifacts/
intervals.json) is fit on `data/processed/test_predictions.parquet`, i.e. the
2025-26 test season. Reusing it inside `backtest/walk_forward.py`'s 6-season
loop would inject 2025-26 residuals into a captaincy decision made in an
earlier test season (e.g. 2020-21) -- leakage. `fit_ceiling_artifact` instead
refits the same quantile artifact on the validation season immediately prior
to whichever test season is under evaluation, so every captaincy decision
stays leakage-safe.

Run:
  python -m models.captaincy        # smoke check against the frozen test-season pool
  python -m models.captaincy --lam 0.3
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

import config
from models.intervals import apply_intervals, fit_intervals, load_artifact
from models.train import predict_xp

CEILING_LAMBDA = config.CAPT_CEILING_LAMBDA


def fit_ceiling_artifact(models: dict, df: pd.DataFrame, val_season: str,
                         cols: list[str]) -> dict:
    """Fit a p10/p25/p75/p90 residual-quantile artifact for the ceiling EV,
    using the validation season immediately prior to the test season under
    evaluation (see module docstring for why -- reusing the shipped
    test-season artifact would leak future residuals into an earlier
    season's captaincy decision).
    """
    rows = df[df.season == val_season]
    frame = rows[["position", "y_points"]].copy()
    frame["xp_med"] = predict_xp(models, rows, cols, "med")
    return fit_intervals(frame, xp_col="xp_med")


def add_ceiling_ev(preds: pd.DataFrame, artifact: dict, *,
                   lam: float | None = None) -> pd.DataFrame:
    """Attach `xp_capt_ceiling` = xp_mean + lam*(p90 - xp_med) to `preds`.

    `preds` must already carry `position`, `xp_med` and `xp_mean` columns.
    `apply_intervals` attaches p10/p25/p75/p90 (already floored at 0) bucketed
    on `xp_med`. `lam` defaults to `CEILING_LAMBDA`; `lam=0.0` reproduces
    `xp_mean` exactly.
    """
    lam = CEILING_LAMBDA if lam is None else lam
    pool = apply_intervals(preds, artifact, xp_col="xp_med")
    pool["xp_capt_ceiling"] = pool["xp_mean"] + lam * (pool["p90"] - pool["xp_med"])
    return pool


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lam", type=float, default=CEILING_LAMBDA)
    args = ap.parse_args(argv)

    preds = pd.read_parquet(config.PROCESSED_DIR / "test_predictions.parquet")
    artifact = load_artifact()
    if artifact is None:
        raise SystemExit("Missing models/artifacts/intervals.json. Run `python -m models.intervals`.")
    pool = add_ceiling_ev(preds, artifact, lam=args.lam)
    print(f"[captaincy] lam={args.lam} xp_mean:         mean={pool['xp_mean'].mean():.3f} "
          f"max={pool['xp_mean'].max():.3f}")
    print(f"[captaincy] lam={args.lam} xp_capt_ceiling: mean={pool['xp_capt_ceiling'].mean():.3f} "
          f"max={pool['xp_capt_ceiling'].max():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
