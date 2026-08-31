"""Phase 4: squad selection via integer linear programming.

Given a pool of players for one gameweek (each with predicted xP, price, position,
club), pick the provably optimal legal FPL team:

  - 15-man squad: 2 GK / 5 DEF / 5 MID / 3 FWD, <= £100m, <= 3 per club
  - a legal starting XI (exactly 1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD)
  - one captain (points doubled)

Objective: XI xP + captain xP (the extra 1x) + a small bench weight (bench players
have option value via autosubs). This is the "from scratch" squad problem (initial
team / wildcard). Weekly transfer constraints come in Phase 5.

Run a demo on the saved test predictions:
  python -m optimize.squad_ilp            # picks for a sample gameweek
  python -m optimize.squad_ilp --gw 20 --xp xp_mean
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd
import pulp

import config


def build_gw_pool(preds: pd.DataFrame, gw: int, xp_col: str,
                  capt_col: str | None = None) -> pd.DataFrame:
    """Collapse fixture-level predictions to one row per player for gameweek `gw`.

    Double gameweeks sum their xP and actual points; price/position/club are
    constant within the gameweek.
    """
    g = preds[preds.gw == gw]
    agg = dict(xp=(xp_col, "sum"), price_m=("price_m", "first"),
               actual=("y_points", "sum"),
               # Captain value: the armband doubles points, so the optimal captain
               # is argmax MEAN points — pass e.g. capt_col="xp_mean" to captain by
               # the mean-objective model while still selecting the XI by xp_col.
               xp_capt=(capt_col or xp_col, "sum"))
    if "y_minutes" in g.columns:                       # for autosubs
        agg["minutes"] = ("y_minutes", "sum")
    pool = g.groupby(["player_code", "name", "team", "position"]).agg(**agg).reset_index()
    if "minutes" not in pool.columns:
        pool["minutes"] = 90                            # unknown -> assume played
    return pool


def pick_squad(pool: pd.DataFrame, *, budget: float = config.BUDGET,
               bench_weight: float = 0.1, force: list | None = None,
               force_start: list | None = None) -> dict:
    """Solve the squad + XI + captain ILP. Returns a result dict.

    `force` / `force_start`: player_codes to lock into the 15-man squad / starting XI
    (e.g. always own Haaland). The rest of the team is optimised around them.
    """
    P = pool.reset_index(drop=True)
    idx = list(P.index)
    code2idx = dict(zip(P["player_code"], P.index))
    xp = P["xp"].to_dict()
    xpc = (P["xp_capt"] if "xp_capt" in P.columns else P["xp"]).to_dict()
    price = P["price_m"].to_dict()
    pos = P["position"].to_dict()
    club = P["team"].to_dict()

    prob = pulp.LpProblem("fpl_squad", pulp.LpMaximize)
    squad = pulp.LpVariable.dicts("squad", idx, cat="Binary")
    start = pulp.LpVariable.dicts("start", idx, cat="Binary")
    capt = pulp.LpVariable.dicts("capt", idx, cat="Binary")

    # Objective: starters + captain bonus (by captain-value xpc) + discounted bench.
    prob += pulp.lpSum(
        start[i] * xp[i] + capt[i] * xpc[i] + bench_weight * (squad[i] - start[i]) * xp[i]
        for i in idx)

    # Linking: can only start if in squad; can only captain if starting.
    for i in idx:
        prob += start[i] <= squad[i]
        prob += capt[i] <= start[i]

    # Squad composition.
    prob += pulp.lpSum(squad[i] for i in idx) == config.SQUAD_SIZE
    for p, q in config.POSITION_QUOTA.items():
        prob += pulp.lpSum(squad[i] for i in idx if pos[i] == p) == q
    prob += pulp.lpSum(price[i] * squad[i] for i in idx) <= budget
    for c in set(club.values()):
        prob += pulp.lpSum(squad[i] for i in idx if club[i] == c) <= config.MAX_PER_CLUB

    # Starting XI + formation.
    prob += pulp.lpSum(start[i] for i in idx) == 11
    prob += pulp.lpSum(start[i] for i in idx if pos[i] == "GK") == 1
    prob += pulp.lpSum(start[i] for i in idx if pos[i] == "DEF") >= 3
    prob += pulp.lpSum(start[i] for i in idx if pos[i] == "DEF") <= 5
    prob += pulp.lpSum(start[i] for i in idx if pos[i] == "MID") >= 2
    prob += pulp.lpSum(start[i] for i in idx if pos[i] == "MID") <= 5
    prob += pulp.lpSum(start[i] for i in idx if pos[i] == "FWD") >= 1
    prob += pulp.lpSum(start[i] for i in idx if pos[i] == "FWD") <= 3
    prob += pulp.lpSum(capt[i] for i in idx) == 1

    # Locked players (force into squad / XI).
    for c in (force or []):
        if c in code2idx:
            prob += squad[code2idx[c]] == 1
    for c in (force_start or []):
        if c in code2idx:
            prob += start[code2idx[c]] == 1

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        raise RuntimeError(f"solver status: {status} "
                           "(forced picks may be over budget / break club or position limits)")

    P = P.assign(
        in_squad=[int(squad[i].value()) for i in idx],
        starting=[int(start[i].value()) for i in idx],
        is_captain=[int(capt[i].value()) for i in idx],
    )
    chosen = P[P.in_squad == 1].copy()
    xi = chosen[chosen.starting == 1]
    cap_row = chosen[chosen.is_captain == 1].iloc[0]
    formation = "-".join(str((xi.position == p).sum()) for p in ["DEF", "MID", "FWD"])

    return {
        "squad": chosen,
        "cost": chosen.price_m.sum(),
        "captain": cap_row["name"],
        "formation": formation,
        "xp_xi": xi.xp.sum() + cap_row.xp,               # incl captain doubling
        "actual_xi": xi.actual.sum() + cap_row.actual,   # realised, captain doubled
    }


def print_result(res: dict, gw: int) -> None:
    ch = res["squad"].sort_values(
        ["starting", "position"],
        key=lambda s: s.map({"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}) if s.name == "position" else s,
        ascending=[False, True])
    print(f"\n=== Optimal squad — GW{gw}  ({res['formation']}, £{res['cost']:.1f}m) ===")
    print(f"{'':2}{'pos':4}{'name':22}{'club':16}{'£m':>5}{'xP':>7}{'act':>6}")
    for _, r in ch.iterrows():
        mark = "C" if r.is_captain else ("*" if r.starting else " ")
        print(f"{mark:2}{r.position:4}{r['name'][:21]:22}{r.team[:15]:16}"
              f"{r.price_m:5.1f}{r.xp:7.2f}{r.actual:6.0f}")
    print(f"\nCaptain: {res['captain']}  |  XI predicted xP={res['xp_xi']:.1f}  "
          f"|  XI actual (C doubled)={res['actual_xi']:.0f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gw", type=int, default=None, help="gameweek (default: mid-season)")
    ap.add_argument("--xp", default="xp_mean", help="xP column: xp_mean | xp_med")
    args = ap.parse_args(argv)

    preds = pd.read_parquet(config.PROCESSED_DIR / "test_predictions.parquet")
    gw = args.gw if args.gw is not None else int(preds.gw.median())
    pool = build_gw_pool(preds, gw, args.xp)
    print(f"pool: {len(pool)} players for GW{gw} (xP column: {args.xp})")
    res = pick_squad(pool)
    print_result(res, gw)
    print("\nNext: Phase 5 transfers/chips, Phase 6 season backtest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
