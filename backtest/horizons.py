"""B.3: forecast quality at 1/2/3-gameweek horizons (OpenFPL benchmark protocol).

At a decision point before GW d we forecast GW d (k=1), d+1 (k=2), d+2 (k=3).
For k>1 the form features are FROZEN at d (only info through d-1) and the target
gameweek's fixture context (opponent FDR, home/away, DGW, rest) is grafted in —
identical to how the live multi-GW planner works, so these numbers describe the
planner's actual input quality.

Run (after models.train):
  python -m backtest.horizons
"""
from __future__ import annotations

import sys

import joblib
import numpy as np
import pandas as pd

import config
from backtest.walk_forward import FIXTURE_CTX
from models.train import load_features, predict_xp

ARTIFACT = config.ROOT / "models" / "artifacts" / "xp_model.joblib"


def horizon_pairs(te: pd.DataFrame, models: dict, cols: list, k: int):
    """(actual, predicted) for every target GW forecast k gameweeks ahead."""
    by_gw = {g: te[te.gw == g] for g in te.gw.unique()}
    actual, pred = [], []
    for d in sorted(by_gw):
        tgt = by_gw.get(d + k - 1)
        if tgt is None:
            continue
        form = by_gw[d].drop_duplicates("player_code").set_index("player_code")
        tgt = tgt[tgt.player_code.isin(form.index)]
        if tgt.empty:
            continue
        synth = form.loc[tgt.player_code].reset_index()
        for c in FIXTURE_CTX:
            synth[c] = tgt[c].values
        p = predict_xp(models, synth, cols, "med").clip(lower=0).values
        actual.append(tgt.y_points.values)
        pred.append(p)
    return np.concatenate(actual), np.concatenate(pred)


def main() -> int:
    art = joblib.load(ARTIFACT)
    models, cols = art["models"], art["cols"]
    df = load_features()
    te = df[df.season.isin(config.TEST_SEASONS)]

    print(f"Forecast quality by horizon — test {config.TEST_SEASONS[0]} "
          f"(form frozen at decision GW, fixture context grafted)\n")
    print(f"{'horizon':>8} {'n':>8} {'MAE':>7} {'RMSE':>7} {'Spearman':>9} {'Spearman(played)':>17}")
    for k in (1, 2, 3):
        y, p = horizon_pairs(te, models, cols, k)
        mae = np.abs(p - y).mean()
        rmse = np.sqrt(((p - y) ** 2).mean())
        sp = pd.Series(p).corr(pd.Series(y), method="spearman")
        played = y != 0   # proxy: rows with any points involve appearances
        spp = pd.Series(p[played]).corr(pd.Series(y[played]), method="spearman")
        print(f"{k:>7}w {len(y):>8,} {mae:>7.3f} {rmse:>7.3f} {sp:>9.3f} {spp:>17.3f}")
    print("\nDecay in Spearman across horizons ≈ how fast frozen form goes stale;"
          "\nthis is the input quality the multi-GW planner actually works with.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
