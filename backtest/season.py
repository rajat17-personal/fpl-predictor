"""Phase 5/6: step a full season gameweek-by-gameweek with a live squad.

Starts from an optimal GW1 squad, then each gameweek either makes free/hit
transfers (myopic optimiser) or plays a scheduled chip (wc/fh/tc/bb), carrying
bank, free transfers, and per-holding purchase prices forward. Reports realised
points (net of hits) versus what each pick actually scored.

Caveats (honest): single-GW transfer lookahead; autosubs not simulated (bench
insurance is ignored, so totals are marginally conservative); chip timing uses
fixture structure only.

Run:
  python -m backtest.season --xp xp_mean            # with chips
  python -m backtest.season --xp xp_med --no-chips
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

import config
from optimize import chips
from optimize.pricing import selling_price
from optimize.squad_ilp import build_gw_pool, pick_squad
from optimize.transfers import optimize_gw, POINT_MULT

_POS_MAX = {"GK": 1, "DEF": 5, "MID": 5, "FWD": 3}


_POS_MIN = {"GK": 1, "DEF": 3, "MID": 2, "FWD": 1}   # FPL formation minima


def _half_of(gw: int) -> str:
    for half, gws_ in chips.HALVES.items():
        if gw in gws_:
            return half
    raise ValueError(f"gw {gw} is not in any half")


def _autosub(starters: list[int], squad: list[int], pos, mins, xp) -> list[int]:
    """Replace non-playing starters with bench players who played, exactly.

    FPL's autosub engine works per blank slot and never breaks formation limits:
    a blank starter of position p may be replaced by a bench player of the SAME
    position, or by any position only if p stays at/above its formation minimum
    (>=3 DEF, >=2 MID, >=1 FWD) and the incomer stays within its maximum. If no
    eligible bench player exists, the slot goes UNFILLED (you field fewer) — FPL
    will not fix a broken minimum with a different position. Bench order is
    approximated by xP (what an optimal manager would set).
    """
    bench = [c for c in squad if c not in starters]
    final = [c for c in starters if mins[c] > 0]

    # Goalkeeper slot: exactly one; backup comes in only if the starter blanked.
    if not any(pos[c] == "GK" for c in final):
        for c in bench:
            if pos[c] == "GK" and mins[c] > 0:
                final.append(c)
                break

    blanks = [c for c in starters if mins[c] == 0 and pos[c] != "GK"]
    avail = sorted((c for c in bench if pos[c] != "GK" and mins[c] > 0),
                   key=lambda c: -xp[c])
    cnt = {p: sum(pos[x] == p for x in final) for p in _POS_MAX}

    # Most-constrained blanks first (their position already below minimum).
    for blank in sorted(blanks, key=lambda c: cnt[pos[c]] < _POS_MIN[pos[c]],
                        reverse=True):
        if len(final) >= 11:
            break
        for b in avail:
            same_pos = pos[b] == pos[blank]
            frees_min = cnt[pos[blank]] >= _POS_MIN[pos[blank]]
            if (same_pos or frees_min) and cnt[pos[b]] + 1 <= _POS_MAX[pos[b]]:
                final.append(b)
                cnt[pos[b]] += 1
                avail.remove(b)
                break
    return final


def _score(pool_idx: pd.DataFrame, starters: list[int], squad: list[int],
           captain: int, mode: str) -> float:
    """Realised points for a gameweek, with autosubs, captain (x2/x3) and
    vice-captain fallback if the captain didn't play."""
    pos, act, mins, xp = (pool_idx.position, pool_idx.actual,
                          pool_idx.minutes, pool_idx.xp)
    xpc = pool_idx.xp_capt if "xp_capt" in pool_idx.columns else xp
    xi = list(squad) if mode == "bb" else _autosub(starters, squad, pos, mins, xp)
    pts = sum(act[c] for c in xi)

    vc = max((c for c in starters if c != captain), key=lambda c: xpc[c], default=None)
    armband = captain if mins[captain] > 0 else (vc if vc is not None and mins[vc] > 0 else None)
    if armband is not None and armband in set(xi):
        pts += (POINT_MULT[mode] - 1) * act[armband]
    return float(pts)


def _pick_lists(res: dict):
    s = res["squad"]
    starters = list(s.loc[s.starting == 1, "player_code"])
    squad = list(s.player_code)
    captain = int(s.loc[s.is_captain == 1, "player_code"].iloc[0])
    return starters, squad, captain


def _squad_from_pick(res: pd.DataFrame):
    """Extract squad dict + meta from a pick_squad result frame."""
    s = res["squad"]
    squad = dict(zip(s.player_code, s.price_m))
    meta = {c: {"position": p, "team": t, "name": n, "price": pr}
            for c, p, t, n, pr in zip(s.player_code, s.position, s.team,
                                      s["name"], s.price_m)}
    return squad, meta


def _pad_holdings(pool: pd.DataFrame, squad: dict, meta: dict) -> pd.DataFrame:
    """Add rows for held players who blank this GW, using tracked metadata."""
    have = set(pool.player_code)
    missing = [c for c in squad if c not in have]
    if not missing:
        return pool
    pad = pd.DataFrame([{
        "player_code": c, "name": meta[c]["name"], "team": meta[c]["team"],
        "position": meta[c]["position"], "xp": 0.0, "xp_capt": 0.0,
        "price_m": meta[c]["price"],
        "actual": 0.0, "minutes": 0.0} for c in missing])   # blank => 0 minutes
    return pd.concat([pool, pad], ignore_index=True)


def _team_value(squad: dict, pool: pd.DataFrame, meta: dict) -> float:
    """Sell value of the whole squad (bank not included)."""
    price_now = dict(zip(pool.player_code, pool.price_m))
    return round(sum(selling_price(purchase, price_now.get(c, meta[c]["price"]))
                     for c, purchase in squad.items()), 1)


def _update_meta(meta: dict, pool: pd.DataFrame, squad: dict) -> None:
    """Refresh full metadata (position/team/name/price) for held players in pool."""
    info = pool.set_index("player_code")[["position", "team", "name", "price_m"]]
    for c in squad:
        if c in info.index:
            row = info.loc[c]
            meta[c] = {"position": row.position, "team": row.team,
                       "name": row["name"], "price": row.price_m}


def run_season(preds: pd.DataFrame, xp_col: str, *, use_chips: bool = True,
               max_transfers: int | None = None, record_chips: bool = False,
               capt_col: str | None = None, scheduler: str = "v1",
               chips_hysteresis: float | None = None,
               rl_seed: int | None = None) -> pd.DataFrame:
    """capt_col: separate prediction column for the captain slot (e.g. "xp_mean" —
    the armband doubles points, so mean-objective xP is the right captain value).

    scheduler: "v1" (default) uses the fixture-structure heuristic
    (`chips.causal_schedule`); "v2" uses the xP-scored causal scheduler
    (`chips.scored_schedule`, Phase 9 chips_v2 experiment); "rl" replays a
    trained MaskablePPO policy (Phase 9 plan 09-07, `optimize/rl_train.py`)
    gameweek by gameweek, deciding BOTH the chip and the transfer count for
    that gameweek -- unlike v1/v2, which only decide chip timing and leave
    transfers to the myopic optimiser under the top-level `max_transfers` cap.
    Chip *application* below is otherwise identical across all three schedulers
    -- only the choice of WHEN each chip fires (and, for "rl", how many
    transfers to make) changes. `chips_hysteresis` only affects scheduler="v2"
    (None -> that function's own config.CHIPS_V2_HYSTERESIS default).
    `rl_seed` selects which of `config.RL_SEEDS`' trained policies to load for
    scheduler="rl" (required in that case) -- `optimize/rl_env.py::load_policy`
    raises `SystemExit` naming the training command if the policy is missing."""
    if scheduler not in ("v1", "v2", "rl"):
        raise ValueError(f"unknown scheduler {scheduler!r} -- expected one of 'v1', 'v2', 'rl'")
    gws = sorted(preds.gw.unique())
    use_rl = use_chips and scheduler == "rl"
    # Causal scheduler: chip decisions only see fixtures a few GWs ahead, like a
    # real manager (default_schedule reads the final fixture list = look-ahead).
    if not use_chips:
        schedule = {}
    elif scheduler == "v2":
        schedule = chips.scored_schedule(preds, xp_col, capt_col=capt_col,
                                         hysteresis=chips_hysteresis)
    elif scheduler == "rl":
        schedule = {}   # decided per-gameweek by the policy below, not precomputed
    else:
        schedule = chips.causal_schedule(preds, xp_col)
    chip_deltas: list[dict] = []   # isolated marginal chip value (same team, w/ vs w/o)

    rl_policy = None
    rl_chip_used: dict[str, set[str]] = {"H1": set(), "H2": set()}
    rl_gws_by_code: dict[int, set[int]] = {}
    if use_rl:
        if rl_seed is None:
            raise ValueError("scheduler='rl' requires rl_seed (see config.RL_SEEDS)")
        seasons_here = preds["season"].unique() if "season" in preds.columns else []
        if len(seasons_here) != 1:
            raise ValueError(
                "scheduler='rl' requires preds for exactly one season (a 'season' "
                f"column with one unique value), got {list(seasons_here)}")
        # Deferred import: optimize.rl_env pulls in gymnasium (and, via
        # load_policy, torch/sb3-contrib) -- a D-09-isolated, dev-only stack
        # (requirements-rl.txt). Importing it at module load time here would
        # also be circular (optimize.rl_env imports this module). Importing it
        # only inside this "rl"-only branch means the weekly product's normal
        # v1/v2 path never requires the RL dependency stack to be installed.
        from optimize import rl_env as rl_env_mod
        rl_policy = rl_env_mod.load_policy(str(seasons_here[0]), rl_seed)
        rl_gws_by_code = preds.groupby("player_code")["gw"].apply(set).to_dict()

    # --- GW1: build the initial squad from scratch ---
    g0 = gws[0]
    pool = build_gw_pool(preds, g0, xp_col, capt_col)
    res = pick_squad(pool, budget=config.BUDGET)
    squad, meta = _squad_from_pick(res)
    bank = round(config.BUDGET - res["cost"], 1)
    ft = 1
    starters, squad_codes, captain = _pick_lists(res)
    pool_idx0 = pool.set_index("player_code")
    pts0 = _score(pool_idx0, starters, squad_codes, captain, "normal")
    log = [{"gw": g0, "chip": "-", "transfers": 0, "hits": 0,
            "points": pts0, "captain": res["captain"], "bank": bank,
            "capt_pts": float(pool_idx0.actual.get(captain, 0.0)),
            "best_pts": float(max(pool_idx0.actual.get(c, 0.0) for c in starters))}]

    for gw in gws[1:]:
        pool = build_gw_pool(preds, gw, xp_col, capt_col)
        pool = _pad_holdings(pool, squad, meta)
        pool_idx = pool.set_index("player_code")
        if use_rl:
            chip, rl_max_transfers = rl_env_mod.decide_action(
                rl_policy, preds, gw, squad, meta, bank, ft, rl_chip_used, rl_gws_by_code)
        else:
            chip = schedule.get(gw, "-")
            rl_max_transfers = None

        if chip in ("wc", "fh"):
            budget = _team_value(squad, pool, meta) + bank
            r = pick_squad(pool, budget=budget)
            starters, squad_codes, captain = _pick_lists(r)
            capt_code = captain
            pts = _score(pool_idx, starters, squad_codes, captain, "normal")
            # Free Hit / Wildcard isolated value vs simply holding the current
            # squad this gameweek (zero transfers) -- measured against the
            # PRE-reset squad/bank, before wc's permanent replacement below, so
            # the baseline reflects the team the manager actually had. This is
            # the same same-gameweek isolation FH/BB/TC already use, so all
            # four are directly comparable; a wildcard's real value is largely
            # the multi-gameweek squad it leaves behind, which this delta does
            # NOT capture -- that shows up in the whole-season model+chips
            # figure instead.
            if record_chips and chip in ("fh", "wc"):
                r0 = optimize_gw(pool, squad, bank, 0, mode="normal", max_transfers=0)
                base = _score(pool_idx, r0["starters"], list(r0["squad"]),
                              r0["captain_code"], "normal")
                chip_deltas.append({"gw": gw, "chip": chip, "delta": pts - base})
            if chip == "wc":                       # permanent reset
                squad, meta = _squad_from_pick(r)
                bank = round(budget - r["cost"], 1)
            n_tr, n_hit, capt = 0, 0, r["captain"]
            ft = min(config.MAX_FREE_TRANSFERS, ft + 1)
            if use_rl:
                rl_chip_used[_half_of(gw)].add(chip)
        else:
            mode = chip if chip in ("tc", "bb") else "normal"
            eff_max_transfers = rl_max_transfers if use_rl else max_transfers
            r = optimize_gw(pool, squad, bank, ft, mode=mode, max_transfers=eff_max_transfers)
            squad, bank = r["squad"], r["bank"]
            starters, capt_code = r["starters"], r["captain_code"]
            gross = _score(pool_idx, r["starters"], list(r["squad"]), r["captain_code"], mode)
            # TC/BB value: the SAME team scored with vs without the chip (isolates it).
            if record_chips and mode in ("tc", "bb"):
                base = _score(pool_idx, r["starters"], list(r["squad"]),
                              r["captain_code"], "normal")
                chip_deltas.append({"gw": gw, "chip": mode, "delta": gross - base})
            pts = gross - config.TRANSFER_HIT * r["hits"]
            n_tr, n_hit, capt = r["transfers"], r["hits"], r["captain"]
            ft = min(config.MAX_FREE_TRANSFERS, max(0, ft - n_tr) + 1)
            if use_rl and chip != "-":
                rl_chip_used[_half_of(gw)].add(chip)

        _update_meta(meta, pool, squad)
        log.append({"gw": gw, "chip": chip, "transfers": n_tr, "hits": n_hit,
                    "points": pts, "captain": capt, "bank": bank,
                    "capt_pts": float(pool_idx.actual.get(capt_code, 0.0)),
                    "best_pts": float(max(pool_idx.actual.get(c, 0.0)
                                          for c in starters))})

    df = pd.DataFrame(log)
    df["cumulative"] = df.points.cumsum()
    df.attrs["chip_deltas"] = chip_deltas
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xp", default="xp_med", help="xp_med | xp_mean (xp_med wins the backtest)")
    ap.add_argument("--no-chips", action="store_true")
    ap.add_argument("--start-gw", type=int, default=None,
                    help="mid-season entry: build the initial squad at this GW")
    args = ap.parse_args(argv)

    preds = pd.read_parquet(config.PROCESSED_DIR / "test_predictions.parquet")
    if args.start_gw:
        preds = preds[preds.gw >= args.start_gw]
    df = run_season(preds, args.xp, use_chips=not args.no_chips)

    total = int(df.points.sum())
    hits = int(df.hits.sum())
    print(f"season: {config.TEST_SEASONS[0]}  |  xP={args.xp}  |  "
          f"chips={'off' if args.no_chips else 'on'}"
          + (f"  |  from GW{args.start_gw}" if args.start_gw else ""))
    print(df.to_string(index=False))
    print(f"\nTOTAL: {total} pts over {len(df)} GWs "
          f"({total/len(df):.1f}/GW)  |  transfers={int(df.transfers.sum())}  "
          f"hits taken={hits} (-{hits*config.TRANSFER_HIT} pts)")
    hit_rate = (df.capt_pts >= df.best_pts).mean()
    capture = df.capt_pts.sum() / max(df.best_pts.sum(), 1)
    print(f"captaincy: hit-rate {hit_rate:.0%} (captain was XI's top scorer), "
          f"capture {capture:.0%} of best-possible captain points "
          f"({df.capt_pts.mean():.1f} vs {df.best_pts.mean():.1f}/GW)")
    if not args.no_chips:
        chip_rows = df[df.chip != "-"]
        print("chips:", ", ".join(f"GW{r.gw}:{r.chip}({int(r.points)})"
                                  for r in chip_rows.itertuples()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
