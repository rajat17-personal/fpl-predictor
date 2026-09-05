"""Phase D evaluation: season sim driven by the multi-period MILP planner.

Each gameweek d: build pools for weeks d..d+H-1 (week 0 = native predictions;
later weeks = form frozen at d with that week's real fixture context grafted —
identical to the leakage-safe horizon machinery), solve the multi-period MILP,
execute only week 0, score with autosubs, roll forward. No chips (compare against
the no-chip configs).

Run (after models.train):
  python -m backtest.multi_period_season --horizon 3
"""
from __future__ import annotations

import argparse
import sys

import joblib
import pandas as pd

import config
from backtest.season import (_pad_holdings, _pick_lists, _score,
                             _squad_from_pick, _update_meta)
from backtest.walk_forward import FIXTURE_CTX
from models.train import load_features, predict_xp
from optimize.multi_period import solve_multi_period
from optimize.pricing import selling_price
from optimize.squad_ilp import build_gw_pool, pick_squad

ARTIFACT = config.ROOT / "models" / "artifacts" / "xp_model.joblib"


def _future_pool(te_by_gw, models, cols, d: int, k: int) -> pd.DataFrame | None:
    """Week d+k pool from form frozen at d + that week's fixture context."""
    tgt = te_by_gw.get(d + k)
    form_src = te_by_gw.get(d)
    if tgt is None or form_src is None:
        return None
    form = form_src.drop_duplicates("player_code").set_index("player_code")
    tgt = tgt[tgt.player_code.isin(form.index)]
    if tgt.empty:
        return None
    synth = form.loc[tgt.player_code].reset_index()
    for c in FIXTURE_CTX:
        synth[c] = tgt[c].values
    med = predict_xp(models, synth, cols, "med").clip(lower=0).values
    mean = predict_xp(models, synth, cols, "mean").clip(lower=0).values
    out = pd.DataFrame({
        "player_code": tgt.player_code.values, "name": tgt.name.values,
        "team": tgt.team.values, "position": tgt.position.values,
        "price_m": tgt.price_m.values, "xp": med, "xp_capt": mean})
    return (out.groupby(["player_code", "name", "team", "position"], as_index=False)
            .agg(price_m=("price_m", "first"), xp=("xp", "sum"),
                 xp_capt=("xp_capt", "sum")))


def run(horizon: int = 3) -> pd.DataFrame:
    art = joblib.load(ARTIFACT)
    models, cols = art["models"], art["cols"]
    df = load_features()
    te = df[df.season.isin(config.TEST_SEASONS)].copy()
    for tag in ("med", "mean"):
        te[f"xp_{tag}"] = predict_xp(models, te, cols, tag)
    te_by_gw = {g: te[te.gw == g] for g in te.gw.unique()}
    gws = sorted(te_by_gw)

    pool = build_gw_pool(te, gws[0], "xp_med", "xp_mean")
    res = pick_squad(pool, budget=config.BUDGET)
    squad, meta = _squad_from_pick(res)
    bank = round(config.BUDGET - res["cost"], 1)
    ft = 1
    starters, squad_codes, captain = _pick_lists(res)
    pts = _score(pool.set_index("player_code"), starters, squad_codes, captain, "normal")
    log = [{"gw": gws[0], "transfers": 0, "hits": 0, "points": pts,
            "captain": res["captain"]}]

    for d in gws[1:]:
        pool0 = _pad_holdings(build_gw_pool(te, d, "xp_med", "xp_mean"), squad, meta)
        pools = [pool0]
        for k in range(1, horizon):
            fp = _future_pool(te_by_gw, models, cols, d, k)
            if fp is not None:
                pools.append(fp)
        sells = {c: selling_price(p, float(pool0.set_index("player_code")
                                          .price_m.get(c, p)))
                 for c, p in squad.items()}
        r = solve_multi_period(pools, squad, bank, ft, sell_values=sells)
        squad, bank = r["squad"], r["bank"]
        gross = _score(pool0.set_index("player_code"), r["starters"],
                       list(r["squad"]), r["captain_code"], "normal")
        pts = gross - config.TRANSFER_HIT * r["hits"]
        ft = min(config.MAX_FREE_TRANSFERS, max(0, ft - r["transfers"]) + 1)
        _update_meta(meta, pool0, squad)
        log.append({"gw": d, "transfers": r["transfers"], "hits": r["hits"],
                    "points": pts, "captain": r["captain"]})
    return pd.DataFrame(log)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=3)
    args = ap.parse_args(argv)
    df = run(args.horizon)
    total = int(df.points.sum())
    print(df.to_string(index=False))
    print(f"\nMULTI-PERIOD (H={args.horizon}) TOTAL: {total} over {len(df)} GWs "
          f"({total/len(df):.1f}/GW) | transfers={int(df.transfers.sum())} "
          f"hits={int(df.hits.sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
