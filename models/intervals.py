"""Empirical prediction intervals for xP (Tier-2: uncertainty on live output).

No retraining: intervals come from the held-out test season's residuals
(data/processed/test_predictions.parquet, never seen in training). Per position,
fixture-level predictions are bucketed by xp quantile and each bucket stores the
empirical q10/q90 of (y_points - xp_med). At inference the player's bucket lends
its quantiles: p10/p90 = xp + q10/q90, floored at 0.

Approximation, stated honestly: quantiles are fit on single fixtures, and live
pools aggregate double gameweeks by summing — a DGW player's band is slightly
narrow (adds quantiles, not distributions). DGWs are rare; the alternative
(convolving residual distributions) isn't worth the machinery.

Run:
  python -m models.intervals        # fit + report held-out coverage
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

import config
from ops.jsonio import read_json, write_json

ARTIFACT = config.ROOT / "models" / "artifacts" / "intervals.json"
N_BINS = 8
QUANTILES = {"q10": 0.10, "q25": 0.25, "q75": 0.75, "q90": 0.90}


def fit_intervals(preds: pd.DataFrame, xp_col: str = "xp_med") -> dict:
    """Per-position xp-bucketed residual quantiles. Returns the artifact dict."""
    out: dict = {"xp_col": xp_col, "n_bins": N_BINS, "positions": {}}
    for pos, g in preds.groupby("position"):
        resid = g["y_points"] - g[xp_col]
        # Quantile bin edges over xp (dedup: low-xp mass collapses edges).
        edges = np.unique(np.quantile(g[xp_col], np.linspace(0, 1, N_BINS + 1)))
        bins = np.clip(np.searchsorted(edges, g[xp_col], side="right") - 1,
                       0, len(edges) - 2)
        rows = []
        for b in range(len(edges) - 1):
            r = resid[bins == b]
            if len(r) < 30:                       # too thin: widen with neighbours
                r = resid[np.abs(bins - b) <= 1]
            rows.append({k: float(np.quantile(r, q)) for k, q in QUANTILES.items()})
        out["positions"][pos] = {"edges": [float(e) for e in edges], "bins": rows}
    return out


def apply_intervals(pool: pd.DataFrame, artifact: dict,
                    xp_col: str = "xp") -> pd.DataFrame:
    """Attach p10/p25/p75/p90 columns to a pool with `position` and `xp_col`."""
    pool = pool.copy()
    for k in QUANTILES:
        pool[k.replace("q", "p")] = np.nan
    for pos, spec in artifact["positions"].items():
        m = pool.position == pos
        if not m.any():
            continue
        edges = np.asarray(spec["edges"])
        b = np.clip(np.searchsorted(edges, pool.loc[m, xp_col], side="right") - 1,
                    0, len(edges) - 2)
        for k in QUANTILES:
            q = np.asarray([spec["bins"][i][k] for i in b])
            pool.loc[m, k.replace("q", "p")] = (
                pool.loc[m, xp_col].to_numpy() + q).clip(min=0.0).round(2)
    return pool


def coverage_report(preds: pd.DataFrame, artifact: dict,
                    xp_col: str = "xp_med") -> dict:
    """Held-out coverage of the p10–p90 band (target ≈ 0.80)."""
    p = apply_intervals(preds.rename(columns={xp_col: "xp"}), artifact)
    inside = (p.y_points >= p.p10) & (p.y_points <= p.p90)
    by_pos = p.assign(inside=inside).groupby("position")["inside"].mean()
    return {"overall": float(inside.mean()),
            **{f"cov_{k}": float(v) for k, v in by_pos.items()}}


def load_artifact() -> dict | None:
    if not ARTIFACT.exists():
        return None
    return read_json(ARTIFACT, what="p10/p90 intervals artifact",
                      remedy="python -m models.intervals")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xp-col", default="xp_med")
    args = ap.parse_args(argv)
    preds = pd.read_parquet(config.PROCESSED_DIR / "test_predictions.parquet")
    art = fit_intervals(preds, args.xp_col)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    write_json(art, ARTIFACT, indent=1)
    cov = coverage_report(preds, art, args.xp_col)
    print(f"[intervals] saved {ARTIFACT.name}; p10-p90 coverage "
          + ", ".join(f"{k}={v:.3f}" for k, v in cov.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
