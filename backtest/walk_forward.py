"""Phase 6: multi-season walk-forward backtest with noise controls.

A single test season is too noisy to trust. This reduces noise three ways:
  1. MORE SEASONS      - expanding-window retrain + backtest over 6 seasons, so the
                         average has ~sqrt(6) tighter standard error.
  2. MULTIPLE TEAMS    - K jittered replicas of the model config per season (small
                         noise on xP -> different near-optimal squads) give a
                         WITHIN-season confidence band on realised points.
  3. ISOLATED CHIPS    - each chip's marginal value is measured on the SAME team
                         with vs without the chip that gameweek, stripping out the
                         path-dependence that made whole-season chip diffs unstable.

For each test season T: train on seasons before T-1, validate on T-1, simulate T.

Run:
  python -m backtest.walk_forward            # ~a few minutes
  python -m backtest.walk_forward --replicas 5
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

import config
from backtest.season import run_season
from models.train import load_features, predict_xp, train_predict

# Schedule-derived context known ahead of time — safe to graft onto a frozen-form row.
FIXTURE_CTX = ["fdr_self", "fdr_opp", "was_home", "is_dgw", "gw", "days_rest"]

DATA_SEASONS = config.SEASONS[:-1]                                  # drop 2026-27
TEST_SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
JITTER_FRAC = 0.05                                                  # 5% of xP sd


def _preds_for(df: pd.DataFrame, test_season: str):
    i = DATA_SEASONS.index(test_season)
    if i < 2:
        raise ValueError(f"{test_season}: need >=2 prior seasons")
    train, val = DATA_SEASONS[:i - 1], DATA_SEASONS[i - 1]
    # med = core selection objective; mean = captain-value model (the armband
    # doubles points, so the captain slot wants E[points], not the median).
    te, models, cols = train_predict(df, train, val, [test_season],
                                     objectives={"med": "regression_l1",
                                                 "mean": "regression"},
                                     calibrate=True)
    te = te.copy()
    te["xp_form"] = te["total_points_r5"].fillna(0)
    return te, models, cols


def _plan_col(preds: pd.DataFrame, horizon: int = 4, decay: float = 0.84) -> pd.DataFrame:
    """Add `xp_plan` = horizon-discounted forward sum of xp_med, for multi-GW
    transfer planning. Drives WHICH players to hold over an upcoming fixture run;
    scoring still uses actual points.

    Backtest caveat: this peeks at future GWs' predictions (which embed future
    form), so it is an OPTIMISTIC upper bound on multi-GW value. The leakage-safe
    live version rebuilds future xP from current form + known fixtures.
    """
    pg = (preds.groupby(["player_code", "gw"])["xp_med"].sum()
          .reset_index(name="pg").sort_values(["player_code", "gw"]))

    def fdec(a):
        a = a.values
        n = len(a)
        out = np.zeros(n)
        for k in range(horizon):
            if n - k <= 0:
                break
            out[:n - k] += (decay ** k) * a[k:]
        return out

    pg["xp_plan"] = pg.groupby("player_code")["pg"].transform(fdec)
    m = preds.merge(pg[["player_code", "gw", "xp_plan"]], on=["player_code", "gw"], how="left")
    nfix = m.groupby(["player_code", "gw"])["xp_med"].transform("size")   # split over DGW rows
    m["xp_plan"] = m["xp_plan"] / nfix
    return m


def leakage_safe_plan(te: pd.DataFrame, models: dict, cols: list, *,
                      horizon: int = 4, decay: float = 0.84) -> pd.DataFrame:
    """LEAKAGE-SAFE multi-GW plan value.

    At decision GW g, predict each future GW g+k using the player's form AS OF g
    (their GW-g feature row already only sees data through g-1) with GW g+k's real
    FIXTURE context grafted in (opponent/home/FDR/DGW — knowable ahead). No future
    form is used, so this is an honest estimate of multi-GW planning value.
    """
    by_gw = {g: te[te.gw == g] for g in te.gw.unique()}
    records = []
    for g, cur in by_gw.items():
        form = cur.drop_duplicates("player_code").set_index("player_code")  # frozen-form snapshot
        plan = pd.Series(0.0, index=form.index)
        for k in range(horizon):
            fut = by_gw.get(g + k)
            if fut is None:
                continue
            fut = fut[fut.player_code.isin(form.index)]
            if fut.empty:
                continue
            synth = form.loc[fut.player_code].reset_index()   # repeat form per future fixture (DGW ok)
            for c in FIXTURE_CTX:
                synth[c] = fut[c].values                       # graft the future fixture context
            pred = predict_xp(models, synth, cols, "med").clip(lower=0).values
            s = pd.Series(pred, index=fut.player_code.values).groupby(level=0).sum()
            plan = plan.add(s.mul(decay ** k), fill_value=0.0)
        records += [{"gw": g, "player_code": pc, "pg": v} for pc, v in plan.items()]

    pg = pd.DataFrame(records)
    m = te.merge(pg, on=["gw", "player_code"], how="left")
    nfix = m.groupby(["gw", "player_code"])["xp_med"].transform("size")
    m["xp_plan"] = (m["pg"] / nfix).fillna(0.0)
    return m


def _jitter(te: pd.DataFrame, xp_col: str, seed: int) -> pd.DataFrame:
    """Perturb xP to pick a different near-optimal team (replica 0 = true optimum)."""
    if seed == 0:
        return te
    rng = np.random.default_rng(seed)
    t = te.copy()
    t[xp_col] = t[xp_col] + rng.normal(0, JITTER_FRAC * t[xp_col].std(), len(t))
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", type=int, default=5, help="jittered teams per season")
    args = ap.parse_args(argv)

    df = load_features()
    rows, chip_recs = [], []
    for T in TEST_SEASONS:
        te, models, cols = _preds_for(df, T)
        # Multiple teams: jittered replicas of the core model config.
        totals = [int(run_season(_jitter(te, "xp_med", s), "xp_med",
                                 use_chips=False).points.sum())
                  for s in range(args.replicas)]
        # Full system (chips) — replica 0, and harvest isolated chip values.
        chips_df = run_season(te, "xp_med", use_chips=True, record_chips=True)
        chip_recs.extend({"season": T, **d} for d in chips_df.attrs["chip_deltas"])
        cdf = run_season(te, "xp_med", capt_col="xp_mean", use_chips=False)
        capt_mean = int(cdf.points.sum())
        capt_capture = cdf.capt_pts.sum() / max(cdf.best_pts.sum(), 1)
        m_safe = int(run_season(leakage_safe_plan(te, models, cols), "xp_plan",
                                use_chips=False).points.sum())                # leakage-safe
        form = int(run_season(te, "xp_form", use_chips=False).points.sum())
        hold = int(run_season(te, "xp_med", use_chips=False, max_transfers=0).points.sum())

        rows.append({"season": T, "model_mean": int(np.mean(totals)),
                     "model_std": int(np.std(totals)), "model+chips": int(chips_df.points.sum()),
                     "capt_mean": capt_mean, "capt_capture": round(capt_capture, 3),
                     "multi_safe": m_safe, "form": form, "hold": hold})
        print(f"[{T}] model={int(np.mean(totals))}±{int(np.std(totals))} "
              f"captMean={capt_mean}(cap{capt_capture:.0%}) multiGW={m_safe} "
              f"chips={int(chips_df.points.sum())} form={form} hold={hold}", flush=True)

    res = pd.DataFrame(rows).set_index("season")
    print("\n=== Walk-forward season totals ===")
    print(res.to_string())

    n = len(TEST_SEASONS)
    gm = res.mean().round(0).astype(int)
    se_model = res["model_mean"].std() / np.sqrt(n)
    print(f"\nAveraged over {n} seasons (season-to-season std in brackets):")
    print(f"  model (core, L1) : {gm['model_mean']}  "
          f"(±{int(res['model_mean'].std())}/season, SE {se_model:.0f})")
    print(f"  capt-by-mean     : {gm['capt_mean']}   -> vs core "
          f"{gm['capt_mean']-gm['model_mean']:+d} (captain slot uses E[pts])")
    print(f"  multi-GW (SAFE)  : {gm['multi_safe']}   -> vs myopic core "
          f"{gm['multi_safe']-gm['model_mean']:+d} (leakage-free, honest)")
    print(f"  model + chips    : {gm['model+chips']}")
    print(f"  form baseline    : {gm['form']}   -> model edge +{gm['model_mean']-gm['form']}")
    print(f"  hold (no xfers)  : {gm['hold']}   -> active mgmt +{gm['model_mean']-gm['hold']}")
    print(f"  within-season team spread (jitter): ~±{int(res['model_std'].mean())} pts")

    # Isolated chip value across all instances.
    cr = pd.DataFrame(chip_recs)
    if len(cr):
        print("\n=== Isolated chip value (same team, with vs without) ===")
        agg = cr.groupby("chip")["delta"].agg(["mean", "std", "count"]).round(1)
        print(agg.to_string())
        print("(positive = the chip added points on the week it was played)")

    res.to_csv(config.PROCESSED_DIR / "walk_forward_results.csv")
    print("\nsaved data/processed/walk_forward_results.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
