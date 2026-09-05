"""Reliability check for the stage-1 P(play) classifier.

The hurdle model multiplies P(play) into every xP, so stage-1 must be CALIBRATED,
not just discriminative: among fixtures where we say "70% to play", ~70% should
actually play. This prints a decile reliability table per position on the
untouched test season, plus expected calibration error (ECE).

Run (after models.train):
  python -m models.calibration
"""
from __future__ import annotations

import sys

import joblib
import numpy as np
import pandas as pd

import config
from models.train import _prep, load_features

ARTIFACT = config.ROOT / "models" / "artifacts" / "xp_model.joblib"


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    rows = []
    for b in range(bins):
        m = idx == b
        if m.sum() == 0:
            continue
        rows.append({"bin": f"{edges[b]:.1f}-{edges[b+1]:.1f}", "n": int(m.sum()),
                     "p_mean": p[m].mean(), "actual": y[m].mean(),
                     "gap": p[m].mean() - y[m].mean()})
    return pd.DataFrame(rows)


def main() -> int:
    art = joblib.load(ARTIFACT)
    models, cols = art["models"], art["cols"]
    df = load_features()
    te = df[df.season.isin(config.TEST_SEASONS)]

    print(f"Stage-1 P(play) calibration — test season {config.TEST_SEASONS[0]}\n")
    for pos in config.POSITIONS:
        sub = te[te.position == pos]
        m = models[pos]
        p = m["clf"].predict_proba(_prep(sub, cols))[:, 1]
        if m.get("cal") is not None:            # measure DEPLOYED probabilities
            p = m["cal"].predict(p)
        y = sub.y_played.values.astype(float)
        rel = reliability(y, p)
        ece = (rel.n / rel.n.sum() * rel.gap.abs()).sum()
        worst = rel.gap.abs().max()
        print(f"[{pos}] n={len(sub):,}  base rate={y.mean():.3f}  "
              f"ECE={ece:.4f}  worst-bin gap={worst:+.3f}")
        print(rel.round(3).to_string(index=False), "\n")
    print("Rule of thumb: ECE < 0.02 is well calibrated for this use; a large gap in"
          "\nthe 0.4-0.8 bins would distort xP for rotation-risk players the most.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
