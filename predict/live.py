"""Phase 7: live weekly recommendation from the official FPL API.

Pulls current prices, availability and the real upcoming fixtures, predicts xP for
the next gameweek with the trained model, then either:
  - (no team id / preseason) recommends the optimal squad from scratch, or
  - (--entry ID) fetches your current squad + bank and recommends transfers,
    starting XI and captain.

Fixture changes are picked up automatically (the API is re-fetched each run), and
the chip note is computed from the current fixture list.

Cold-start note: early in a season there is little current-season form, so rolling
features are sparse (NaN) and predictions lean on price / fixture / position priors
— which is exactly the information available preseason. Once gameweeks are played,
re-running the data pipeline for the live season sharpens the rolling features.

Run:
  python -m predict.live                 # optimal squad for the next GW
  python -m predict.live --entry 1234567 --free-transfers 1
"""
from __future__ import annotations

import argparse
import logging
import sys

import joblib
import pandas as pd
import requests

import config
from data import live_history, live_odds
from data.ingest import fetch_fpl_live
from models.train import predict_xp
from ops.jsonio import PayloadError, read_json
from ops.jsonlog import log_event
from optimize.squad_ilp import pick_squad
from optimize.transfers import optimize_gw

_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}
_LOGGER = logging.getLogger(__name__)


_INGEST_REMEDY = "run `python -m data.ingest` to regenerate the live cache"


def _read_live_json(path, *, what: str):
    """read_json wrapped with the `payload.unreadable` structured log event
    every CLI/API prediction flow chokes through on a missing/corrupt file."""
    try:
        return read_json(path, what=what, remedy=_INGEST_REMEDY)
    except PayloadError:
        log_event(_LOGGER, "payload.unreadable", level="error", path=str(path), what=what)
        raise


def _load_live(force: bool = True):
    fetch_fpl_live(force=force)
    boot = _read_live_json(config.RAW_DIR / "live" / "bootstrap-static.json",
                           what="FPL bootstrap-static payload")
    fixtures = _read_live_json(config.RAW_DIR / "live" / "fixtures.json",
                               what="FPL fixtures payload")
    return boot, fixtures


def _next_gw(boot: dict) -> int:
    for e in boot["events"]:
        if e.get("is_next"):
            return e["id"]
    unfinished = [e["id"] for e in boot["events"] if not e["finished"]]
    return unfinished[0] if unfinished else boot["events"][-1]["id"]


def _team_fixtures(fixtures: list, gw: int) -> dict[int, list[dict]]:
    """team_id -> list of {was_home, fdr_self, fdr_opp, days_rest} for the gameweek.

    days_rest = days since the team's previous scheduled fixture (NaN for the
    season opener) — a top-importance DEF/GK feature the model was trained on.
    """
    kicks: dict[int, list] = {}
    for f in fixtures:
        ko = f.get("kickoff_time")
        if not ko:
            continue
        ko = pd.Timestamp(ko)
        kicks.setdefault(f["team_h"], []).append(ko)
        kicks.setdefault(f["team_a"], []).append(ko)
    for t in kicks:
        kicks[t].sort()

    def rest(team, ko):
        if not ko:
            return float("nan")
        ko = pd.Timestamp(ko)
        prev = [k for k in kicks.get(team, []) if k < ko]
        return (ko - prev[-1]).total_seconds() / 86400 if prev else float("nan")

    out: dict[int, list[dict]] = {}
    for f in fixtures:
        if f.get("event") != gw:
            continue
        ko = f.get("kickoff_time")
        out.setdefault(f["team_h"], []).append(
            {"was_home": True, "fdr_self": f["team_h_difficulty"],
             "fdr_opp": f["team_a_difficulty"], "days_rest": rest(f["team_h"], ko)})
        out.setdefault(f["team_a"], []).append(
            {"was_home": False, "fdr_self": f["team_a_difficulty"],
             "fdr_opp": f["team_h_difficulty"], "days_rest": rest(f["team_a"], ko)})
    return out


def _availability(el: dict) -> float:
    """Fraction of the match we expect the player available (live injury/suspension)."""
    if el.get("status") in ("i", "s", "u", "n"):     # injured/suspended/unavailable/ineligible
        return 0.0
    chance = el.get("chance_of_playing_next_round")
    return 1.0 if chance is None else chance / 100.0


def _gw_pool(boot: dict, fixtures: list, gw: int, artifact: dict) -> pd.DataFrame:
    """Per-player model xP (x availability) for a single gameweek."""
    cols = artifact["cols"]
    teams = {t["id"]: t["name"] for t in boot["teams"]}
    tf = _team_fixtures(fixtures, gw)
    total = boot["total_players"]

    rows, meta = [], []
    for el in boot["elements"]:
        fx = tf.get(el["team"], [])
        if not fx:                                    # blank gameweek for this club
            continue
        is_dgw = len(fx) > 1
        for f in fx:
            rows.append({
                "player_id": el["id"],
                "position": _POS[el["element_type"]],
                "was_home": f["was_home"], "is_dgw": is_dgw,
                "days_rest": f["days_rest"],
                "fdr_self": f["fdr_self"], "fdr_opp": f["fdr_opp"],
                "price_m": el["now_cost"] / 10.0,
                "selected": float(el["selected_by_percent"]) / 100.0 * total,
                "transfers_balance": el["transfers_in_event"] - el["transfers_out_event"],
                "gw": gw,
                **{c: el.get(c) for c in config.SET_PIECE_COLS}})
            meta.append({
                "player_code": el["code"], "name": el["web_name"],
                "team": teams[el["team"]], "position": _POS[el["element_type"]],
                "price_m": el["now_cost"] / 10.0, "avail": _availability(el)})

    if not rows:
        return pd.DataFrame(columns=["player_code", "name", "team", "position", "price_m", "xp"])
    X = pd.DataFrame(rows)
    # Current-season rolling form (data.live_history cache); NaN preseason.
    form = live_history.current_form()
    if form is not None:
        X = X.merge(form, on="player_id", how="left",
                    suffixes=("", "_form"))
        X["apps_prior"] = X["apps_prior"].fillna(0.0)
    else:
        X["apps_prior"] = 0.0
    # Live forward odds (needs ODDS_API_KEY; NaN otherwise) — see data/live_odds.py.
    m = pd.DataFrame(meta)
    odds = live_odds.fetch_live_odds()
    if odds is not None:
        X = (pd.concat([X, m[["team"]].reset_index(drop=True)], axis=1)
             .merge(odds, on=["team", "was_home"], how="left")
             .drop(columns=["team"]))
        print(f"  [odds] live odds merged for {odds.team.nunique()} teams")
    X = X.reindex(columns=list(dict.fromkeys(["position"] + cols)))
    xp = predict_xp(artifact["models"], X, cols, "med").clip(lower=0)
    # Captain value: armband doubles points, so the captain slot uses E[points]
    # (mean-objective model), while selection stays on the median model.
    xp_capt = predict_xp(artifact["models"], X, cols, "mean").clip(lower=0)
    m = pd.DataFrame(meta)
    m["xp"] = xp.values * m["avail"]                  # zero out injured/suspended
    m["xp_capt"] = xp_capt.values * m["avail"]
    return (m.groupby(["player_code", "name", "team", "position"])
            .agg(xp=("xp", "sum"), xp_capt=("xp_capt", "sum"),
                 price_m=("price_m", "first")).reset_index())


def build_pool(boot: dict, fixtures: list, gw: int, artifact: dict) -> pd.DataFrame:
    pool = _gw_pool(boot, fixtures, gw, artifact)
    pool["actual"] = 0.0                              # future GW: outcome unknown
    return pool


def build_horizon_pool(boot: dict, fixtures: list, gw: int, artifact: dict,
                       horizon: int, decay: float = 0.84) -> pd.DataFrame:
    """Multi-GW planning pool. Selection xP = decayed sum of the model's xP over the
    next `horizon` gameweeks (current form held fixed, each GW's real fixture applied
    — leakage-free live). Keeps `xp_next` for captaincy on the immediate GW."""
    base = _gw_pool(boot, fixtures, gw, artifact)
    events = sorted({f["event"] for f in fixtures if f.get("event")})
    plan = pd.Series(0.0, index=base.player_code)
    for k, g in enumerate(g for g in events if gw <= g < gw + horizon):
        gp = _gw_pool(boot, fixtures, g, artifact).set_index("player_code")["xp"]
        plan = plan.add(gp.mul(decay ** k), fill_value=0.0)
    base["xp_next"] = base["xp"]
    base["xp"] = base.player_code.map(plan).fillna(0.0)   # drives selection/transfers
    base["actual"] = 0.0
    return base


def _fetch_entry(entry_id: int, gw: int):
    """Current squad (player codes), bank, from the last finished gameweek picks."""
    last = gw - 1
    r = requests.get(f"{config.FPL_API}/entry/{entry_id}/event/{last}/picks/",
                     headers=_HEADERS, timeout=30)
    if r.status_code != 200:
        return None
    data = r.json()
    boot = read_json(config.RAW_DIR / "live" / "bootstrap-static.json",
                     what="FPL bootstrap-static payload", remedy=_INGEST_REMEDY)
    id2code = {e["id"]: e["code"] for e in boot["elements"]}
    codes = [id2code[p["element"]] for p in data["picks"]]
    bank = data["entry_history"]["bank"] / 10.0
    return codes, bank


def _chip_note(fixtures: list, gw: int) -> str:
    tf = _team_fixtures(fixtures, gw)
    all_teams = {f["team_h"] for f in fixtures} | {f["team_a"] for f in fixtures}
    dgw = sum(1 for v in tf.values() if len(v) > 1)
    bgw = len(all_teams) - len(tf)
    if dgw:
        return f"GW{gw} is a DOUBLE for {dgw} clubs — consider Bench Boost / Triple Captain."
    if bgw:
        return f"GW{gw} has {bgw} blank clubs — consider Free Hit."
    return f"GW{gw}: standard fixtures (no double/blank)."


def _resolve_names(pool: pd.DataFrame, names: str) -> list:
    """Map comma-separated player names to player_codes (case-insensitive match)."""
    codes = []
    for nm in (n.strip() for n in names.split(",") if n.strip()):
        m = pool[pool.name.str.contains(nm, case=False, na=False)]
        if len(m):
            codes.append(int(m.iloc[0].player_code))
            print(f"  locking in: {m.iloc[0]['name']} ({m.iloc[0].team}, £{m.iloc[0].price_m}m)")
        else:
            print(f"  [warn] '{nm}' not found in this gameweek's pool")
    return codes


def _print_pool_top(pool: pd.DataFrame, n=10):
    top = pool.sort_values("xp", ascending=False).head(n)
    print(f"\nTop {n} projected players (GW):")
    for _, r in top.iterrows():
        print(f"  {r.position:3} {r['name'][:20]:20} {r.team[:14]:14} £{r.price_m:4.1f}  xP={r.xp:.2f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", type=int, default=None, help="your FPL team (entry) id")
    ap.add_argument("--free-transfers", type=int, default=1)
    ap.add_argument("--budget", type=float, default=config.BUDGET)
    ap.add_argument("--horizon", type=int, default=1,
                    help="multi-GW planning horizon (1 = myopic next GW)")
    ap.add_argument("--force", default="",
                    help="comma-separated names to lock into the squad, e.g. 'Haaland,Saka'")
    ap.add_argument("--purchase-prices", default=None,
                    help="JSON file {web_name: purchase_price_m} for exact selling prices")
    args = ap.parse_args(argv)

    artifact = joblib.load(config.ROOT / "models" / "artifacts" / "xp_model.joblib")
    boot, fixtures = _load_live()
    gw = _next_gw(boot)
    print(f"Next gameweek: GW{gw}")
    if args.horizon > 1:
        print(f"(multi-GW planning over {args.horizon} gameweeks)")
        pool = build_horizon_pool(boot, fixtures, gw, artifact, args.horizon)
    else:
        pool = build_pool(boot, fixtures, gw, artifact)
    _print_pool_top(pool)

    entry = _fetch_entry(args.entry, gw) if args.entry else None
    if entry is not None:
        codes, bank = entry
        # Holdings metadata straight from the bootstrap: correct position/team/price
        # even for players blanking this GW (they may be absent from the pool).
        boot_meta = {el["code"]: {
            "position": _POS[el["element_type"]], "name": el["web_name"],
            "team": el["team"], "price": el["now_cost"] / 10.0,
        } for el in boot["elements"]}
        held_meta = {c: boot_meta[c] for c in codes if c in boot_meta}
        # Purchase prices: default = current price (public API omits them, so the
        # 50% sell-on fee is ignored — slightly optimistic). Override via JSON
        # {web_name: purchase_price_in_millions} for exact selling prices.
        squad = {c: held_meta.get(c, {}).get("price", 0.0) for c in codes}
        if args.purchase_prices:
            overrides = read_json(args.purchase_prices, what="purchase-prices override file")
            by_name = {m["name"]: c for c, m in held_meta.items()}
            for nm, price in overrides.items():
                if nm in by_name:
                    squad[by_name[nm]] = float(price)
                else:
                    print(f"  [warn] purchase-price name not in squad: {nm}")
        else:
            print("  (no --purchase-prices file: assuming purchase == current price)")
        print(f"\nEntry {args.entry}: bank £{bank:.1f}m, {args.free_transfers} FT")
        r = optimize_gw(pool, squad, bank, args.free_transfers, mode="normal",
                        holdings_meta=held_meta)
        print(f"\n=== GW{gw} recommendation (transfers) ===")
        print(f"transfers={r['transfers']} (hits {r['hits']}), captain: {r['captain']}, "
              f"projected XI xP={r['xi_xp']}")
    else:
        reason = "no --entry given" if args.entry is None else "no current picks (preseason)"
        print(f"\n({reason}) -> recommending optimal squad from scratch.")
        res = pick_squad(pool, budget=args.budget, force=_resolve_names(pool, args.force))
        from optimize.squad_ilp import print_result
        print_result(res, gw)

    print("\nChip note: " + _chip_note(fixtures, gw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
