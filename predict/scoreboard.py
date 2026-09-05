"""Post-gameweek accuracy scoreboard: our xP vs FPL's ep_next vs what happened.

The public trust engine. predict.export freezes each gameweek's predictions
(with FPL's own ep_next captured at the same moment) into web/data/history/;
after the gameweek finishes this job fetches realised points and appends one
entry to web/data/scoreboard.json. Nothing is ever recomputed from hindsight —
a gameweek with no frozen prediction file simply never appears.

Run (post-GW cron, or manually after a gameweek ends):
  python -m predict.scoreboard
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd
import requests
from scipy.stats import spearmanr

import config
from ops.jsonio import read_json, write_json
from predict.export import WEB_DATA

SCOREBOARD = WEB_DATA / "scoreboard.json"
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}


def fetch_actuals(gw: int) -> pd.DataFrame:
    """Realised per-player points for a finished gameweek (DGW fixtures summed)."""
    r = requests.get(f"{config.FPL_API}/event/{gw}/live/", headers=_HEADERS, timeout=30)
    r.raise_for_status()
    rows = [{"player_id": e["id"],
             "actual": e["stats"]["total_points"],
             "minutes": e["stats"]["minutes"]} for e in r.json()["elements"]]
    return pd.DataFrame(rows)


def score_gw(frozen: dict, actuals: pd.DataFrame) -> dict:
    """One scoreboard entry from a frozen prediction file + realised points."""
    pred = pd.DataFrame(frozen["players"]).merge(actuals, on="player_id", how="inner")
    entry: dict = {"gw": frozen["gw"], "n_players": len(pred),
                   "generated_utc": frozen.get("meta", {}).get("generated_utc")}

    entry["mae_model"] = round(float((pred.xp - pred.actual).abs().mean()), 3)
    entry["spearman_model"] = round(float(spearmanr(pred.xp, pred.actual).statistic), 3)
    fpl = pred.dropna(subset=["ep_next"])
    if len(fpl):
        entry["mae_fpl"] = round(float((fpl.ep_next - fpl.actual).abs().mean()), 3)
        entry["spearman_fpl"] = round(
            float(spearmanr(fpl.ep_next, fpl.actual).statistic), 3)

    # The public calls: our captain pick and our top-5 xP, vs what they scored.
    cap = pred.sort_values("xp_capt", ascending=False).iloc[0]
    entry["captain"] = {"name": cap["name"], "team": cap["team"],
                        "points": int(cap.actual)}
    entry["top5"] = [{"name": r["name"], "xp": round(float(r.xp), 2),
                      "points": int(r.actual)}
                     for _, r in pred.sort_values("xp", ascending=False)
                     .head(5).iterrows()]
    best = pred.sort_values("actual", ascending=False).iloc[0]
    entry["best_player"] = {"name": best["name"], "points": int(best.actual)}
    return entry


def running_summary(entries: list[dict]) -> dict:
    df = pd.DataFrame(entries)
    out = {"gameweeks": len(df),
           "mae_model": round(float(df.mae_model.mean()), 3),
           "spearman_model": round(float(df.spearman_model.mean()), 3),
           "captain_avg_points": round(
               float(pd.DataFrame([e["captain"] for e in entries]).points.mean()), 2)}
    if "mae_fpl" in df:
        out["mae_fpl"] = round(float(df.mae_fpl.mean()), 3)
        out["spearman_fpl"] = round(float(df.spearman_fpl.mean()), 3)
    return out


def update(*, force: bool = False) -> list[int]:
    """Score every finished GW that has a frozen prediction file. Returns new GWs."""
    boot = requests.get(f"{config.FPL_API}/bootstrap-static/",
                        headers=_HEADERS, timeout=30).json()
    finished = {e["id"] for e in boot["events"] if e["finished"]}
    board_remedy = "delete web/data/scoreboard.json to rebuild it from web/data/history/"
    board = (read_json(SCOREBOARD, what="accuracy scoreboard", remedy=board_remedy)
             if SCOREBOARD.exists() else {"entries": [], "summary": {}})
    have = {e["gw"] for e in board["entries"]}

    added = []
    for f in sorted((WEB_DATA / "history").glob("gw*.json")):
        frozen = read_json(f, what="frozen gameweek prediction file",
                           remedy="python -m predict.export")
        gw = frozen["gw"]
        if gw not in finished or (gw in have and not force):
            continue
        entry = score_gw(frozen, fetch_actuals(gw))
        board["entries"] = [e for e in board["entries"] if e["gw"] != gw] + [entry]
        added.append(gw)
    if added or force:
        board["entries"].sort(key=lambda e: e["gw"])
        board["summary"] = running_summary(board["entries"]) if board["entries"] else {}
        write_json(board, SCOREBOARD)
    print(f"[scoreboard] scored GWs {added or 'none'} "
          f"({len(board['entries'])} total on the board)")
    return added


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rescore existing GWs")
    args = ap.parse_args(argv)
    update(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
