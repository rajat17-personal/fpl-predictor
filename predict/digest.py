"""Weekly email digest from the exported JSON (Tier-1: the retention loop).

Renders web/data/ into web/data/digest.html + digest.txt: deadline, top xP,
captain pick, one differential, price watchlist, scoreboard line. Sending is a
separate concern — pipe digest.html into Buttondown/SES/whatever once an email
provider is chosen; this module owns only the content.

Run (after predict.export):
  python -m predict.digest
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import sys

from ops.jsonio import read_json
from predict.export import WEB_DATA

DIFFERENTIAL_MAX_OWN = 10.0     # % ownership ceiling for the differential pick


def _load(name: str):
    p = WEB_DATA / name
    if not p.exists():
        return None
    return read_json(p, what=f"exported {name}", remedy="python -m predict.export")


def build_digest() -> dict:
    meta, table = _load("meta.json"), _load("xp_table.json")
    if not (meta and table):
        raise SystemExit("[digest] run predict.export first")
    captains = _load("captains.json") or []
    watch = _load("watchlist.json")
    board = _load("scoreboard.json")

    top5 = table[:5]
    diff = next((r for r in table
                 if (r.get("ownership") or 100) < DIFFERENTIAL_MAX_OWN
                 and r.get("status") == "a"), None)
    deadline = meta.get("deadline_utc")
    when = (dt.datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            .strftime("%A %d %B, %H:%M UTC") if deadline else "TBC")
    summary = (board or {}).get("summary") or {}
    return {"gw": meta["gw"], "deadline": when, "top5": top5,
            "captain": captains[0] if captains else None, "differential": diff,
            "watchlist": watch, "scoreline": summary}


def to_text(d: dict) -> str:
    L = [f"FPL ML — GW{d['gw']} digest", f"Deadline: {d['deadline']}", ""]
    L.append("Top projected players:")
    L += [f"  {r['name']:18} {r['team_short']:4} £{r['price_m']:.1f}  "
          f"xP {r['xp']:.2f} ({r['p10']:.1f}–{r['p90']:.1f})" for r in d["top5"]]
    if d["captain"]:
        c = d["captain"]
        L += ["", f"Captain pick: {c['name']} ({c['team']}) — armband xP {c['xp_capt']:.2f}"]
    if d["differential"]:
        f = d["differential"]
        L += ["", f"Differential: {f['name']} ({f['team_short']}, "
              f"{f['ownership']}% owned) — xP {f['xp']:.2f}"]
    if d["watchlist"]:
        w = d["watchlist"]
        tag = " (heuristic)" if w["mode"] == "heuristic" else ""
        L += ["", f"Price watch{tag}:",
              "  rising: " + ", ".join(r["name"] for r in w["risers"][:5]),
              "  falling: " + ", ".join(r["name"] for r in w["fallers"][:5])]
    if d["scoreline"]:
        s = d["scoreline"]
        line = (f"Model so far: MAE {s['mae_model']} vs FPL {s.get('mae_fpl', '—')} "
                f"over {s['gameweeks']} GW(s)")
        L += ["", line]
    L += ["", "Not affiliated with the Premier League."]
    return "\n".join(L)


def to_html(d: dict) -> str:
    # Deliberately plain: email clients reward simple, inline-styled HTML.
    e = html.escape
    rows = "".join(
        f"<tr><td style='padding:4px 10px'>{e(r['name'])}</td>"
        f"<td style='padding:4px 10px'>{e(r['team_short'])}</td>"
        f"<td style='padding:4px 10px' align='right'>£{r['price_m']:.1f}</td>"
        f"<td style='padding:4px 10px' align='right'><b>{r['xp']:.2f}</b> "
        f"<span style='color:#777'>({r['p10']:.1f}–{r['p90']:.1f})</span></td></tr>"
        for r in d["top5"])
    parts = [
        f"<h2 style='margin:0 0 4px'>FPL ML — GW{d['gw']}</h2>",
        f"<p style='margin:0 0 14px;color:#555'>Deadline: {e(d['deadline'])}</p>",
        "<table style='border-collapse:collapse;font-size:14px'>"
        "<tr><th align='left' style='padding:4px 10px'>Player</th>"
        "<th style='padding:4px 10px'>Team</th><th style='padding:4px 10px'>£</th>"
        f"<th style='padding:4px 10px'>xP (10–90%)</th></tr>{rows}</table>",
    ]
    if d["captain"]:
        c = d["captain"]
        parts.append(f"<p><b>Captain:</b> {e(c['name'])} ({e(c['team'])}) — "
                     f"armband xP {c['xp_capt']:.2f}</p>")
    if d["differential"]:
        f = d["differential"]
        parts.append(f"<p><b>Differential:</b> {e(f['name'])} "
                     f"({e(f['team_short'])}, {f['ownership']}% owned) — "
                     f"xP {f['xp']:.2f}</p>")
    if d["watchlist"]:
        w = d["watchlist"]
        tag = " <i>(heuristic)</i>" if w["mode"] == "heuristic" else ""
        parts.append(
            f"<p><b>Price watch{tag}:</b> rising — "
            + ", ".join(e(r["name"]) for r in w["risers"][:5])
            + "; falling — "
            + ", ".join(e(r["name"]) for r in w["fallers"][:5]) + "</p>")
    if d["scoreline"]:
        s = d["scoreline"]
        parts.append(f"<p style='color:#555'>Model so far: MAE {s['mae_model']} vs "
                     f"FPL {s.get('mae_fpl', '—')} over {s['gameweeks']} GW(s)</p>")
    parts.append("<p style='color:#999;font-size:12px'>Not affiliated with the "
                 "Premier League.</p>")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser().parse_args(argv)
    d = build_digest()
    (WEB_DATA / "digest.txt").write_text(to_text(d))
    (WEB_DATA / "digest.html").write_text(to_html(d))
    print(f"[digest] GW{d['gw']} -> web/data/digest.{{txt,html}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
