"""Phase 5: weekly transfer optimisation (myopic / single-GW lookahead).

Given the squad you carry into a gameweek (with each holding's purchase price),
your bank, and how many free transfers you have, decide which players to sell/buy
to maximise this gameweek's XI xP + captain, minus 4 points per transfer beyond
your free ones. Selling prices honour the 50% sell-on fee (see pricing.py).

Chip modes: "normal", "tc" (triple captain), "bb" (bench boost). Wildcard / free
hit are handled at the season level by re-picking from scratch (optimize.squad_ilp).

Lookahead is one gameweek: it uses only the current GW's leakage-safe xP. True
multi-GW planning needs future xP that isn't knowable at decision time, so it is
left as a refinement.
"""
from __future__ import annotations

import pandas as pd
import pulp

import config
from optimize.pricing import selling_price

CAPT_BONUS = {"normal": 1, "bb": 1, "tc": 2}   # extra multiples on top of starting 1x
POINT_MULT = {"normal": 2, "bb": 2, "tc": 3}   # captain scoring multiplier


def _extend_pool(pool: pd.DataFrame, squad: dict[int, float],
                 holdings_meta: dict | None) -> pd.DataFrame:
    """Ensure every currently-held player has a row (blank-GW holds get xp 0).

    `holdings_meta` maps player_code -> {"position", "team", "name"} for held
    players. Padding a player with a guessed position would corrupt the squad
    composition constraints (e.g. a blank GK counted as MID), so metadata is
    required for any held player missing from the pool.
    """
    have = set(pool.player_code)
    missing = [c for c in squad if c not in have]
    if not missing:
        return pool
    unknown = [c for c in missing if not (holdings_meta or {}).get(c, {}).get("position")]
    if unknown:
        raise ValueError(
            f"held players missing from pool with unknown position: {unknown} — "
            "pass holdings_meta (position/team/name) for blank-GW holdings")
    pad = pd.DataFrame([{
        "player_code": c, "name": holdings_meta[c].get("name", f"held_{c}"),
        "team": holdings_meta[c].get("team", "?"),
        "position": holdings_meta[c]["position"], "xp": 0.0,
        "price_m": squad[c], "actual": 0.0,
        # only pad columns the pool actually carries (avoid NaN-ing others)
        **({"xp_capt": 0.0} if "xp_capt" in pool.columns else {})}
        for c in missing])
    return pd.concat([pool, pad], ignore_index=True)


def optimize_gw(pool: pd.DataFrame, squad: dict[int, float], bank: float,
                free_transfers: int, *, mode: str = "normal",
                bench_weight: float = 0.1, max_transfers: int | None = None,
                holdings_meta: dict | None = None,
                force: list | None = None, exclude: list | None = None) -> dict:
    """Solve the transfer + XI + captain ILP for one gameweek.

    `force` / `exclude`: player_codes that must / must not end up in the 15.
    Forcing a non-held player buys them; excluding a held player sells them —
    both count as transfers like any other move.
    """
    pool = _extend_pool(pool, squad, holdings_meta).reset_index(drop=True)
    idx = list(pool.index)
    code = pool.player_code.to_dict()
    xp = pool.xp.to_dict()
    xpc = (pool.xp_capt if "xp_capt" in pool.columns else pool.xp).to_dict()
    price = pool.price_m.to_dict()
    pos = pool.position.to_dict()
    club = pool.team.to_dict()
    held = {i: (code[i] in squad) for i in idx}
    sell = {i: (selling_price(squad[code[i]], price[i]) if held[i] else 0.0) for i in idx}

    m = pulp.LpProblem("fpl_transfers", pulp.LpMaximize)
    sq = pulp.LpVariable.dicts("sq", idx, cat="Binary")
    st = pulp.LpVariable.dicts("st", idx, cat="Binary")
    cap = pulp.LpVariable.dicts("cap", idx, cat="Binary")
    hits = pulp.LpVariable("hits", lowBound=0, cat="Integer")

    # Objective: bench boost counts all 15; otherwise XI + discounted bench.
    if mode == "bb":
        squad_pts = pulp.lpSum(sq[i] * xp[i] for i in idx)
    else:
        squad_pts = pulp.lpSum(st[i] * xp[i] + bench_weight * (sq[i] - st[i]) * xp[i]
                               for i in idx)
    m += squad_pts + pulp.lpSum(CAPT_BONUS[mode] * cap[i] * xpc[i] for i in idx) \
        - config.TRANSFER_HIT * hits

    for i in idx:
        m += st[i] <= sq[i]
        m += cap[i] <= st[i]

    # Squad composition, budget, club cap.
    m += pulp.lpSum(sq[i] for i in idx) == config.SQUAD_SIZE
    for p, q in config.POSITION_QUOTA.items():
        m += pulp.lpSum(sq[i] for i in idx if pos[i] == p) == q
    # Club cap, grandfathered: a mid-season club move (January window) can leave a
    # legally-acquired squad holding 4 of one club — FPL only enforces <=3 at
    # transfer time, so cap at max(3, currently-held count) rather than a hard 3.
    held_count: dict = {}
    for i in idx:
        if held[i]:
            held_count[club[i]] = held_count.get(club[i], 0) + 1
    for c in set(club.values()):
        club_cap = max(config.MAX_PER_CLUB, held_count.get(c, 0))
        m += pulp.lpSum(sq[i] for i in idx if club[i] == c) <= club_cap
    money_in = pulp.lpSum(sell[i] * (1 - sq[i]) for i in idx if held[i])
    money_out = pulp.lpSum(price[i] * sq[i] for i in idx if not held[i])
    m += money_out <= bank + money_in + 0.049   # tolerance vs MILP rounding drift

    # Locked / banned players (interactive planner).
    code2idx = {code[i]: i for i in idx}
    for c in (force or []):
        if c in code2idx:
            m += sq[code2idx[c]] == 1
    for c in (exclude or []):
        if c in code2idx:
            m += sq[code2idx[c]] == 0

    # Transfers and hits.
    transfers = pulp.lpSum(sq[i] for i in idx if not held[i])   # buys == sells (size fixed)
    m += hits >= transfers - free_transfers
    if max_transfers is not None:
        m += transfers <= max_transfers

    # Starting XI + formation + captain.
    m += pulp.lpSum(st[i] for i in idx) == 11
    m += pulp.lpSum(st[i] for i in idx if pos[i] == "GK") == 1
    for p, lo, hi in [("DEF", 3, 5), ("MID", 2, 5), ("FWD", 1, 3)]:
        m += pulp.lpSum(st[i] for i in idx if pos[i] == p) >= lo
        m += pulp.lpSum(st[i] for i in idx if pos[i] == p) <= hi
    m += pulp.lpSum(cap[i] for i in idx) == 1

    m.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[m.status] != "Optimal":
        raise RuntimeError(f"transfer solve: {pulp.LpStatus[m.status]}")

    chosen = [i for i in idx if sq[i].value() > 0.5]
    starters = [i for i in chosen if st[i].value() > 0.5]
    cap_i = next(i for i in chosen if cap[i].value() > 0.5)
    n_transfers = sum(1 for i in chosen if not held[i])
    n_hits = max(0, n_transfers - free_transfers)

    # New squad dict: kept holdings retain purchase price; buys enter at current price.
    new_squad = {code[i]: (squad[code[i]] if held[i] else price[i]) for i in chosen}
    money_in_val = sum(sell[i] for i in idx if held[i] and i not in chosen)
    money_out_val = sum(price[i] for i in chosen if not held[i])
    # Keep the TRUE bank (may be a rounding hair below zero from the MILP
    # tolerance) — clamping to 0 would gift free money week after week.
    bank_after = round(bank + money_in_val - money_out_val, 2)

    mult = POINT_MULT[mode]
    scoring = chosen if mode == "bb" else starters
    xi_actual = sum(pool.actual[i] for i in scoring) + (mult - 1) * pool.actual[cap_i]
    xi_xp = sum(xp[i] for i in scoring) + (mult - 1) * xp[cap_i]

    return {
        "squad": new_squad, "bank": bank_after,
        "transfers": n_transfers, "hits": n_hits,
        "captain": pool.name[cap_i], "captain_code": code[cap_i],
        "xi_xp": round(xi_xp, 2),
        "points": xi_actual - config.TRANSFER_HIT * n_hits,  # net of hits
        "points_gross": xi_actual,
        "starters": [code[i] for i in starters],
        "mode": mode,
    }
