"""Phase 5: chip scheduling (heuristic, foresight limited to the fixture list).

Chips are timed off the published fixture structure — double gameweeks (DGW, a
club plays twice) and blank gameweeks (BGW, a club doesn't play) — which a manager
knows weeks ahead. We deliberately do NOT peek at realised points to time chips.

2026/27 rule: two of each chip, one set per half (GW1-19, GW20-38). We schedule at
most one chip per gameweek:
  - Triple Captain (tc) & Bench Boost (bb): the two biggest DGWs in each half.
  - Free Hit (fh): the biggest BGW in each half (if any).
  - Wildcard (wc): a fixed sensible slot per half.
"""
from __future__ import annotations

import pandas as pd

HALVES = {"H1": range(1, 20), "H2": range(20, 39)}
WC_SLOT = {"H1": 8, "H2": 28}


def _fixture_structure(preds: pd.DataFrame) -> pd.DataFrame:
    """Per (gw): how many clubs have a double (2 fixtures) or blank (0).

    Fixture-level predictions have one row per player per fixture, so a player
    with 2 rows in a gameweek played a double; a club is a DGW club if any of
    its players doubles, and a blank club is one with no players featuring.
    """
    per_player = (preds.groupby(["gw", "player_code", "team"]).size()
                  .rename("nfix").reset_index())
    all_teams = preds.team.nunique()
    rows = []
    for gw, g in per_player.groupby("gw"):
        dgw = g[g.nfix >= 2].team.nunique()          # clubs with a double
        bgw = all_teams - g.team.nunique()           # clubs with no fixture
        rows.append({"gw": gw, "dgw_clubs": dgw, "bgw_clubs": bgw})
    return pd.DataFrame(rows).sort_values("gw")


def causal_schedule(preds: pd.DataFrame, xp_col: str = "xp_med",
                    visibility: int = 4) -> dict[int, str]:
    """Chip schedule where the decision at GW g only sees fixture structure within
    g..g+visibility — matching real announcement lead times. `default_schedule`
    reads the season's FINAL fixture list, which in a backtest is look-ahead
    (doubles are created mid-season by postponements); use this for backtests.

    Rules per gameweek (one chip max, priority wc > fh > bb > tc):
      wc at its fixed slot; fh on a blank that is the biggest visible; bb on a
      double that is the biggest visible; tc on a further visible double, else a
      late-half fallback on the best visible captain gameweek.
    """
    struct = _fixture_structure(preds).set_index("gw")
    gwp = preds.groupby(["gw", "player_code"])[xp_col].sum().reset_index()
    best_capt = gwp.groupby("gw")[xp_col].max()

    schedule: dict[int, str] = {}
    for half, gws in HALVES.items():
        half_gws = [g for g in gws if g in struct.index]
        remaining = {"wc", "fh", "bb", "tc"}
        half_end = max(half_gws) if half_gws else 0
        for g in half_gws:
            window = [w for w in half_gws if g <= w <= g + visibility]
            dgw_here = struct.loc[g, "dgw_clubs"]
            bgw_here = struct.loc[g, "bgw_clubs"]
            dgw_max = max(struct.loc[w, "dgw_clubs"] for w in window)
            bgw_max = max(struct.loc[w, "bgw_clubs"] for w in window)

            chip = None
            if "wc" in remaining and g >= WC_SLOT[half]:
                chip = "wc"
            elif "fh" in remaining and bgw_here > 0 and bgw_here >= bgw_max:
                chip = "fh"
            elif "bb" in remaining and dgw_here > 0 and dgw_here >= dgw_max:
                chip = "bb"
            elif "tc" in remaining and dgw_here > 0 and "bb" not in remaining:
                chip = "tc"
            elif ("tc" in remaining and g >= half_end - 5 and dgw_max == 0
                  and best_capt.get(g, 0) >= max(best_capt.get(w, 0) for w in window)):
                chip = "tc"
            if chip:
                schedule[g] = chip
                remaining.discard(chip)
    return schedule


def default_schedule(preds: pd.DataFrame, xp_col: str = "xp_med") -> dict[int, str]:
    """Schedule chips per half (GW1-19, GW20-38), timed CONDITIONALLY.

    Empirically, forcing Bench Boost / Free Hit into slots with no real double /
    blank loses points (e.g. an early-season Bench Boost on an unsettled squad),
    so those two only fire on genuine DGW / BGW. Triple Captain and Wildcard time
    well anywhere, so they always fire (TC via a best-captain fallback):
      - Bench Boost    -> biggest DGW only (else unused this half)
      - Triple Captain -> next DGW, else the GW with the single best captain xP
      - Free Hit       -> biggest BGW only (else unused this half)
      - Wildcard       -> a fixed slot
    """
    struct = _fixture_structure(preds).set_index("gw")
    gwp = preds.groupby(["gw", "player_code"])[xp_col].sum().reset_index()
    best_capt = gwp.groupby("gw")[xp_col].max()                     # best single captain

    def top_gw(metric: pd.Series, half_gws, used: set[int]) -> int | None:
        cand = metric[metric.index.isin(half_gws) & ~metric.index.isin(used)]
        return int(cand.idxmax()) if len(cand) else None

    schedule: dict[int, str] = {}
    for half, gws in HALVES.items():
        half_gws = list(gws)
        s = struct[struct.index.isin(half_gws)]
        used: set[int] = set()
        dgw = list(s[s.dgw_clubs > 0].sort_values("dgw_clubs", ascending=False).index)

        # Bench Boost -> biggest double only.
        if dgw:
            gw = int(dgw.pop(0))
            schedule[gw] = "bb"
            used.add(gw)

        # Triple Captain -> next double, else best single-fixture captain.
        gw = int(dgw.pop(0)) if dgw else top_gw(best_capt, half_gws, used)
        if gw is not None:
            schedule[gw] = "tc"
            used.add(gw)

        # Free Hit -> biggest blank only.
        bgw = s[s.bgw_clubs > 0].sort_values("bgw_clubs", ascending=False)
        if len(bgw):
            gw = int(bgw.iloc[0].name)
            if gw not in used:
                schedule[gw] = "fh"
                used.add(gw)

        # Wildcard -> fixed slot (nudge off any collision).
        gw = WC_SLOT[half]
        while gw in schedule:
            gw += 1
        schedule[gw] = "wc"

    return schedule
