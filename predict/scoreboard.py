"""Post-gameweek accuracy scoreboard: our xP vs FPL's ep_next vs what happened.

The public trust engine. predict.export freezes each gameweek's predictions
(with FPL's own ep_next captured at the same moment) into web/data/history/;
after the gameweek finishes this job fetches realised points and appends one
entry to web/data/scoreboard.json. Nothing is ever recomputed from hindsight —
a gameweek with no frozen prediction file simply never appears.

Two Tier-3 diagnostic benchmark columns (Phase 10-02) also land here: top-100
overall-league consensus ownership (`data/fpl_standings.py`) and fplreview's
free-model weekly capture (`data/fplreview.py`). Both are DIAGNOSTIC ONLY --
neither is ever a model input, and the fplreview figures are never
redistributed beyond this repository (ToS). Each is independently optional:
when its source data is absent for a gameweek, the entry produced is
byte-identical to today's (no keys added, none dropped).

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
import data.fpl_standings
import data.fplreview
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

    # Tier-3 diagnostic 1: top-100 consensus ownership (data/fpl_standings.py).
    # Consensus ownership is a PERCENTAGE, not points -- an MAE against actual
    # points would be a meaningless number in a published trust artifact, so
    # only Spearman (rank agreement) is scored for this column.
    consensus = data.fpl_standings.load_consensus(frozen["gw"])
    if consensus is not None:
        cpred = pred.merge(consensus, on="player_id", how="inner")
        if len(cpred):
            entry["n_consensus"] = len(cpred)
            entry["spearman_consensus"] = round(
                float(spearmanr(cpred.consensus_pct, cpred.actual).statistic), 3)
            entry["spearman_consensus_vs_model"] = round(
                float(spearmanr(cpred.consensus_pct, cpred.xp).statistic), 3)

    # Tier-3 diagnostic 2: fplreview's free-model weekly capture
    # (data/fplreview.py). Diagnostic only -- never a model input, never
    # redistributed (ToS). Played-only rows, matching
    # backtest/benchmark_external.py's own basis so the two numbers stay
    # comparable.
    season = frozen.get("meta", {}).get("season") or config.SEASONS[-1]
    fpr = data.fplreview.load_gw(season, frozen["gw"])
    if fpr is not None:
        joined = pred.merge(fpr[["player_code", "proj_pts"]], on="player_code", how="inner")
        joined = joined[joined.minutes > 0]
        if len(joined):
            entry["n_fplreview"] = len(joined)
            entry["mae_fplreview"] = round(
                float((joined.proj_pts - joined.actual).abs().mean()), 3)
            entry["spearman_fplreview"] = round(
                float(spearmanr(joined.proj_pts, joined.actual).statistic), 3)

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
    if "spearman_consensus" in df:
        out["spearman_consensus"] = round(float(df.spearman_consensus.mean()), 3)
        out["spearman_consensus_vs_model"] = round(
            float(df.spearman_consensus_vs_model.mean()), 3)
    if "mae_fplreview" in df:
        out["mae_fplreview"] = round(float(df.mae_fplreview.mean()), 3)
        out["spearman_fplreview"] = round(float(df.spearman_fplreview.mean()), 3)
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
