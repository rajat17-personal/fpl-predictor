"""Phase D: true multi-period transfer planning (MILP over a rolling horizon).

Unlike the decayed-sum heuristic (which only biases SELECTION toward fixture
runs), this plans TRANSFERS across the next H gameweeks jointly: when to bank a
free transfer, when a hit pays for itself, which buys serve the whole window.
Used receding-horizon: solve H weeks, execute only week 0, re-solve next week.

Inputs are per-week pools sharing player_code/price (prices held static over the
horizon): pools[t] must contain xp (that week's xP; 0/absent = blank) and
optionally xp_capt. Candidate pruning keeps the MILP tractable: the current squad
plus the top-N non-held players by horizon xP.

FT dynamics (2026/27): roll up to 5, each extra transfer -4. Chips are not
decided here (they stay with the season-level scheduler).
"""
from __future__ import annotations

import pandas as pd
import pulp

import config


def solve_multi_period(pools: list[pd.DataFrame], squad: dict[int, float],
                       bank: float, free_transfers: int, *,
                       sell_values: dict[int, float] | None = None,
                       decay: float = 0.9, bench_weight: float = 0.1,
                       top_n: int = 150) -> dict:
    """Plan over len(pools) weeks; return week-0 decisions + planned schedule."""
    H = len(pools)
    # --- assemble the candidate universe -----------------------------------
    info: dict[int, dict] = {}
    xp = [dict() for _ in range(H)]
    xpc = [dict() for _ in range(H)]
    horizon_sum: dict[int, float] = {}
    for t, p in enumerate(pools):
        for r in p.itertuples(index=False):
            c = int(r.player_code)
            info.setdefault(c, {"pos": r.position, "club": r.team,
                                "price": float(r.price_m), "name": r.name})
            xp[t][c] = float(r.xp)
            xpc[t][c] = float(getattr(r, "xp_capt", r.xp))
            horizon_sum[c] = horizon_sum.get(c, 0.0) + float(r.xp) * decay ** t
    keep = set(squad) | set(pd.Series(horizon_sum).nlargest(top_n).index)
    cand = [c for c in keep if c in info]
    sell_values = sell_values or {c: squad[c] for c in squad}

    m = pulp.LpProblem("fpl_multi_period", pulp.LpMaximize)
    T = range(H)
    sq = pulp.LpVariable.dicts("sq", (cand, T), cat="Binary")
    st = pulp.LpVariable.dicts("st", (cand, T), cat="Binary")
    cp = pulp.LpVariable.dicts("cp", (cand, T), cat="Binary")
    buy = pulp.LpVariable.dicts("buy", (cand, T), cat="Binary")
    sell = pulp.LpVariable.dicts("sell", (cand, T), cat="Binary")
    hits = pulp.LpVariable.dicts("hits", T, lowBound=0, cat="Integer")
    ft = pulp.LpVariable.dicts("ft", T, lowBound=1,
                               upBound=config.MAX_FREE_TRANSFERS, cat="Integer")
    bankv = pulp.LpVariable.dicts("bank", T, lowBound=-0.05)

    m += pulp.lpSum(
        decay ** t * (st[c][t] * xp[t].get(c, 0.0)
                      + cp[c][t] * xpc[t].get(c, 0.0)
                      + bench_weight * (sq[c][t] - st[c][t]) * xp[t].get(c, 0.0))
        for c in cand for t in T) - config.TRANSFER_HIT * pulp.lpSum(hits[t] for t in T)

    held0 = {c: (c in squad) for c in cand}
    club_held: dict = {}
    for c in cand:
        if held0[c]:
            club_held[info[c]["club"]] = club_held.get(info[c]["club"], 0) + 1

    for t in T:
        # Squad evolution: week 0 evolves from the incoming squad.
        for c in cand:
            prev = (1 if held0[c] else 0) if t == 0 else sq[c][t - 1]
            m += sq[c][t] == prev + buy[c][t] - sell[c][t]
            m += buy[c][t] + sell[c][t] <= 1
            m += st[c][t] <= sq[c][t]
            m += cp[c][t] <= st[c][t]
        # Composition / clubs (grandfathered) / formation / captain.
        m += pulp.lpSum(sq[c][t] for c in cand) == config.SQUAD_SIZE
        for p, q in config.POSITION_QUOTA.items():
            m += pulp.lpSum(sq[c][t] for c in cand if info[c]["pos"] == p) == q
        for club in {info[c]["club"] for c in cand}:
            cap_n = max(config.MAX_PER_CLUB, club_held.get(club, 0))
            m += pulp.lpSum(sq[c][t] for c in cand if info[c]["club"] == club) <= cap_n
        m += pulp.lpSum(st[c][t] for c in cand) == 11
        m += pulp.lpSum(st[c][t] for c in cand if info[c]["pos"] == "GK") == 1
        for p, lo, hi in [("DEF", 3, 5), ("MID", 2, 5), ("FWD", 1, 3)]:
            m += pulp.lpSum(st[c][t] for c in cand if info[c]["pos"] == p) >= lo
            m += pulp.lpSum(st[c][t] for c in cand if info[c]["pos"] == p) <= hi
        m += pulp.lpSum(cp[c][t] for c in cand) == 1
        # Money: sells credit the sell value (week 0) / price (later, approx).
        inflow = pulp.lpSum(sell[c][t] * (sell_values.get(c, info[c]["price"])
                                          if t == 0 else info[c]["price"])
                            for c in cand)
        outflow = pulp.lpSum(buy[c][t] * info[c]["price"] for c in cand)
        prev_bank = bank if t == 0 else bankv[t - 1]
        m += bankv[t] == prev_bank + inflow - outflow
        # Transfers vs free transfers.
        transfers_t = pulp.lpSum(buy[c][t] for c in cand)
        prev_ft = free_transfers if t == 0 else ft[t - 1]
        m += hits[t] >= transfers_t - prev_ft
        m += ft[t] <= prev_ft - transfers_t + hits[t] + 1
        m += ft[t] >= 1

    m.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=60))
    if pulp.LpStatus[m.status] not in ("Optimal", "Not Solved"):
        raise RuntimeError(f"multi-period solve: {pulp.LpStatus[m.status]}")

    chosen0 = [c for c in cand if sq[c][0].value() > 0.5]
    starters0 = [c for c in chosen0 if st[c][0].value() > 0.5]
    captain0 = next(c for c in chosen0 if cp[c][0].value() > 0.5)
    bought0 = [c for c in cand if buy[c][0].value() > 0.5]
    sold0 = [c for c in cand if sell[c][0].value() > 0.5]
    new_squad = {c: (squad[c] if c in squad else info[c]["price"]) for c in chosen0}
    n_hits = int(round(hits[0].value()))

    # Full planned schedule, week by week (week 0 is the executable decision;
    # later weeks are the plan under current information — re-solve weekly).
    def week(t: int) -> dict:
        chosen = [c for c in cand if sq[c][t].value() > 0.5]
        starters = [c for c in chosen if st[c][t].value() > 0.5]
        capt = next(c for c in chosen if cp[c][t].value() > 0.5)
        xi_xp = (sum(xp[t].get(c, 0.0) for c in starters) + xpc[t].get(capt, 0.0))
        def rows(codes):
            return [{"player_code": c, "name": info[c]["name"],
                     "position": info[c]["pos"], "team": info[c]["club"],
                     "price_m": info[c]["price"],
                     "xp": round(xp[t].get(c, 0.0), 2)} for c in codes]
        return {
            "buys": rows([c for c in cand if buy[c][t].value() > 0.5]),
            "sells": rows([c for c in cand if sell[c][t].value() > 0.5]),
            "hits": int(round(hits[t].value())),
            "captain": info[capt]["name"],
            "xi_xp": round(xi_xp, 2),
            "bank": round(bankv[t].value(), 2),
            "free_transfers_after": int(round(ft[t].value())),
            "squad": [{**r, "starting": c in set(starters), "captain": c == capt}
                      for c, r in ((c, rows([c])[0]) for c in chosen)],
        }

    return {"squad": new_squad, "bank": round(bankv[0].value(), 2),
            "starters": starters0, "captain_code": captain0,
            "transfers": len(bought0), "hits": n_hits,
            "bought": [info[c]["name"] for c in bought0],
            "sold": [info[c]["name"] for c in sold0],
            "captain": info[captain0]["name"],
            "planned_transfers": [int(sum(buy[c][t].value() > 0.5 for c in cand))
                                  for t in T],
            "plan": [week(t) for t in T]}
