"""Export the weekly prediction run as versioned JSON for the static site.

This is the product contract: everything downstream (web/, digest, scoreboard,
CSV licensing) reads these files and nothing else. The CLI (predict.live) stays
the source of truth for interactive use; this module reuses its pool builders so
the backtest keeps validating the exact code the product serves.

Files written to web/data/:
  meta.json        gameweek, deadline, model + run stamps
  xp_table.json    every player: xP + p10/p90 band, price, ownership, status
  captains.json    top captain picks (mean-objective model, the armband metric)
  squad.json       optimal 15/XI from scratch (the "template" squad)
  fixtures.json    team x next-6-GW difficulty ticker
  chips.json       DGW/BGW structure ahead + chip note
  history/gw{N}.json  frozen predictions + FPL's ep_next, for the scoreboard

Run (after the weekly pipeline):
  python -m predict.export
  python -m predict.export --horizon 3     # planner xp over 3 GWs in the table
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

import joblib
import pandas as pd

import config
from models import intervals
from optimize.squad_ilp import pick_squad
from predict.live import (_availability, _chip_note, _load_live, _next_gw,
                          build_horizon_pool, build_pool)

WEB_DATA = config.ROOT / "web" / "data"
TICKER_GWS = 6


def _boot_meta(boot: dict) -> pd.DataFrame:
    """Per-player live metadata keyed by player_code (ownership, status, ep_next)."""
    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    rows = [{
        "player_code": el["code"], "player_id": el["id"],
        "team_short": teams[el["team"]],
        "ownership": float(el["selected_by_percent"]),
        "status": el.get("status", "a"),
        "avail": _availability(el),
        "ep_next": pd.to_numeric(el.get("ep_next"), errors="coerce"),
        "news": el.get("news") or "",
    } for el in boot["elements"]]
    return pd.DataFrame(rows)


def build_table(pool: pd.DataFrame, boot: dict) -> list[dict]:
    """xp_table.json rows: pool + ownership/status + interval band."""
    t = pool.merge(_boot_meta(boot), on="player_code", how="left")
    art = intervals.load_artifact()
    if art is not None:
        t = intervals.apply_intervals(t, art)
    t = t.sort_values("xp", ascending=False)
    cols = ["player_code", "player_id", "name", "team", "team_short", "position",
            "price_m", "xp", "xp_capt", "p10", "p90", "ownership", "status", "news"]
    t = t[[c for c in cols if c in t.columns]].round({"xp": 2, "xp_capt": 2})
    return json.loads(t.to_json(orient="records"))


def build_captains(table: list[dict], n: int = 10) -> list[dict]:
    ranked = sorted(table, key=lambda r: r.get("xp_capt") or 0, reverse=True)[:n]
    return [{k: r.get(k) for k in ("name", "team", "team_short", "position",
                                   "price_m", "xp", "xp_capt", "ownership")}
            for r in ranked]


def build_squad(pool: pd.DataFrame) -> dict:
    """Optimal from-scratch squad (the free 'template' view)."""
    res = pick_squad(pool)
    ch = res["squad"]
    rows = [{"player_code": int(r.player_code), "name": r["name"], "team": r.team,
             "position": r.position, "price_m": float(r.price_m),
             "xp": round(float(r.xp), 2), "starting": bool(r.starting),
             "captain": bool(r.is_captain)} for _, r in ch.iterrows()]
    return {"squad": rows, "captain": res["captain"],
            "formation": res["formation"], "cost": round(float(res["cost"]), 1),
            "xi_xp": round(float(res["xp_xi"]), 2)}


def _team_xg(boot: dict) -> dict[int, dict]:
    """Season-to-date team xG / xG-conceded per game from the element-history
    cache. Team xG = sum of its players' xg that GW; team xGC = the xgc of the
    fullest-minutes player (a full-match player's xgc equals the team's)."""
    cache = config.RAW_DIR / "live" / "element_history.parquet"
    if not cache.exists():
        return {}
    h = pd.read_parquet(cache)
    id2team = {el["id"]: el["team"] for el in boot["elements"]}
    h = h.assign(team_id=h.player_id.map(id2team)).dropna(subset=["team_id"])
    for c in ("xg", "xgc"):
        h[c] = pd.to_numeric(h[c], errors="coerce")
    per_gw = (h.groupby(["team_id", "gw"])
              .apply(lambda g: pd.Series({
                  "xg": g.xg.sum(),
                  "xgc": g.sort_values("minutes").xgc.iloc[-1]}),
                  include_groups=False)
              .reset_index())
    agg = per_gw.groupby("team_id").agg(xg=("xg", "mean"), xgc=("xgc", "mean"),
                                        games=("gw", "count"))
    # Shrink small samples toward the league mean (k=4 pseudo-games): one odd
    # match must not make a team look impenetrable or hopeless.
    K = 4
    for c, avg in (("xg", agg.xg.mean()), ("xgc", agg.xgc.mean())):
        agg[c] = (agg[c] * agg.games + avg * K) / (agg.games + K)
    return {int(t): {"xg_pg": round(float(r.xg), 2),
                     "xgc_pg": round(float(r.xgc), 2), "games": int(r.games)}
            for t, r in agg.iterrows()}


def _next_fixture_xg(boot: dict, fixtures: list, gw: int) -> dict[int, dict]:
    """Opponent-adjusted xG forecast for each team's NEXT fixture.

    Poisson-style strength model on season-to-date rates: a team's expected
    goals against opponent O = own xG/gm x (O's xGC/gm / league average),
    nudged ±10% for venue. Early season this leans on tiny samples — the page
    labels it as a forecast, and it sharpens weekly.
    """
    form = _team_xg(boot)
    if not form:
        return {}
    avg = sum(v["xg_pg"] for v in form.values()) / max(len(form), 1)
    nxt: dict[int, dict] = {}
    for f in sorted(fixtures, key=lambda f: (f.get("event") or 99)):
        e = f.get("event")
        if e is None or e < gw:
            continue
        for tid, opp, home in ((f["team_h"], f["team_a"], True),
                               (f["team_a"], f["team_h"], False)):
            if tid in nxt or tid not in form or opp not in form:
                continue
            venue = 1.1 if home else 0.9
            nxt[tid] = {
                "xg_next": round(form[tid]["xg_pg"]
                                 * (form[opp]["xgc_pg"] / avg) * venue, 2),
                "xgc_next": round(form[tid]["xgc_pg"]
                                  * (form[opp]["xg_pg"] / avg) / venue, 2),
            }
    return nxt


def build_ticker(boot: dict, fixtures: list, gw: int) -> list[dict]:
    """Per-team next-6-GW fixture difficulty (FPL FDR, 1 easy - 5 hard)."""
    teams = {t["id"]: {"short": t["short_name"], "name": t["name"]}
             for t in boot["teams"]}
    xg = _next_fixture_xg(boot, fixtures, gw)
    grid: dict[int, dict[int, list]] = {t: {} for t in teams}
    for f in fixtures:
        e = f.get("event")
        if e is None or not (gw <= e < gw + TICKER_GWS):
            continue
        grid[f["team_h"]].setdefault(e, []).append(
            {"opp": teams[f["team_a"]]["short"], "home": True,
             "fdr": f["team_h_difficulty"]})
        grid[f["team_a"]].setdefault(e, []).append(
            {"opp": teams[f["team_h"]]["short"], "home": False,
             "fdr": f["team_a_difficulty"]})
    out = []
    for tid, byegw in grid.items():
        gws = [{"gw": g, "fixtures": byegw.get(g, [])}
               for g in range(gw, gw + TICKER_GWS)]
        played = [fx["fdr"] for g in gws for fx in g["fixtures"]]
        ease = round(sum(6 - d for d in played) / max(len(played), 1), 2)
        out.append({"team": teams[tid]["name"], "short": teams[tid]["short"],
                    "gws": gws, "ease": ease,
                    "xg_next": xg.get(tid, {}).get("xg_next"),
                    "xgc_next": xg.get(tid, {}).get("xgc_next")})
    return sorted(out, key=lambda r: r["ease"], reverse=True)


def build_chips(fixtures: list, gw: int) -> dict:
    """DGW/BGW structure for the remaining season + the note for next GW."""
    per_gw: dict[int, dict[int, int]] = {}
    all_teams: set[int] = set()
    for f in fixtures:
        all_teams |= {f["team_h"], f["team_a"]}
        e = f.get("event")
        if e is None:
            continue
        for t in (f["team_h"], f["team_a"]):
            per_gw.setdefault(e, {}).setdefault(t, 0)
            per_gw[e][t] += 1
    structure = []
    for e in sorted(per_gw):
        if e < gw:
            continue
        counts = per_gw[e]
        structure.append({"gw": e,
                          "dgw_clubs": sum(1 for v in counts.values() if v > 1),
                          "bgw_clubs": len(all_teams) - len(counts)})
    return {"note": _chip_note(fixtures, gw), "structure": structure}


def build_standings(boot: dict, fixtures: list) -> list[dict]:
    """Premier League table from finished fixtures (W/D/L, GF/GA, points)."""
    teams = {t["id"]: {"team": t["name"], "short": t["short_name"], "played": 0,
                       "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0}
             for t in boot["teams"]}
    for f in fixtures:
        if not (f.get("finished") or f.get("finished_provisional")):
            continue
        hs, as_ = f.get("team_h_score"), f.get("team_a_score")
        if hs is None or as_ is None:
            continue
        h, a = teams[f["team_h"]], teams[f["team_a"]]
        h["played"] += 1; a["played"] += 1
        h["gf"] += hs; h["ga"] += as_; a["gf"] += as_; a["ga"] += hs
        if hs > as_:   h["won"] += 1; a["lost"] += 1
        elif hs < as_: a["won"] += 1; h["lost"] += 1
        else:          h["drawn"] += 1; a["drawn"] += 1
    rows = []
    for t in teams.values():
        t["gd"] = t["gf"] - t["ga"]
        t["points"] = 3 * t["won"] + t["drawn"]
        rows.append(t)
    return sorted(rows, key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))


def build_leaders(boot: dict, n: int = 10) -> dict:
    """Season-to-date player leaderboards from the bootstrap."""
    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    pos = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    df = pd.DataFrame([{
        "name": el["web_name"], "team": teams[el["team"]],
        "position": pos[el["element_type"]],
        "goals": el.get("goals_scored", 0), "assists": el.get("assists", 0),
        "clean_sheets": el.get("clean_sheets", 0),
        "cards": el.get("yellow_cards", 0) + el.get("red_cards", 0),
        "points": el.get("total_points", 0), "bonus": el.get("bonus", 0),
    } for el in boot["elements"]])
    def top(frame, col):
        t = frame[frame[col] > 0].nlargest(n, col)
        return json.loads(t[["name", "team", "position", col]]
                          .rename(columns={col: "value"}).to_json(orient="records"))
    return {"points": top(df, "points"), "goals": top(df, "goals"),
            "assists": top(df, "assists"),
            "clean_sheets": top(df[df.position.isin(["GK", "DEF"])], "clean_sheets"),
            "cards": top(df, "cards")}


def build_meta(boot: dict, gw: int, horizon: int) -> dict:
    ev = next((e for e in boot["events"] if e["id"] == gw), {})
    model_path = config.ROOT / "models" / "artifacts" / "xp_model.joblib"
    return {
        "gw": gw, "horizon": horizon,
        "deadline_utc": ev.get("deadline_time"),
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "model_mtime_utc": dt.datetime.fromtimestamp(
            model_path.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds"),
        "season": config.CURRENT_SEASON,
    }


def export(horizon: int = 1) -> dict:
    artifact = joblib.load(config.ROOT / "models" / "artifacts" / "xp_model.joblib")
    boot, fixtures = _load_live()
    gw = _next_gw(boot)
    # Rolling-form features are only as fresh as the element-history cache; a
    # stale cache silently skews every prediction toward whoever shone in the
    # gameweeks it does contain. Always re-fetch on export (~1 min).
    from data import live_history
    live_history.fetch(force=True)
    pool = (build_horizon_pool(boot, fixtures, gw, artifact, horizon)
            if horizon > 1 else build_pool(boot, fixtures, gw, artifact))
    if horizon > 1:                       # table shows next-GW xp; planner xp kept
        pool = pool.rename(columns={"xp": "xp_plan", "xp_next": "xp"})

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    (WEB_DATA / "history").mkdir(exist_ok=True)
    table = build_table(pool, boot)
    files = {
        "meta.json": build_meta(boot, gw, horizon),
        "xp_table.json": table,
        "captains.json": build_captains(table),
        "squad.json": build_squad(pool),
        "fixtures.json": build_ticker(boot, fixtures, gw),
        "chips.json": build_chips(fixtures, gw),
        "standings.json": build_standings(boot, fixtures),
        "leaders.json": build_leaders(boot),
    }
    for name, payload in files.items():
        json.dump(payload, open(WEB_DATA / name, "w"))
    # Frozen copy for the post-GW scoreboard: predictions + FPL's own ep_next.
    hist = [{k: r.get(k) for k in ("player_id", "player_code", "name", "team",
                                   "position", "xp", "xp_capt", "ep_next")}
            for r in table]
    json.dump({"gw": gw, "meta": files["meta.json"], "players": hist},
              open(WEB_DATA / "history" / f"gw{gw}.json", "w"))
    print(f"[export] GW{gw}: {len(table)} players -> {WEB_DATA}")
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=1)
    args = ap.parse_args(argv)
    export(horizon=args.horizon)
    return 0


if __name__ == "__main__":
    sys.exit(main())
