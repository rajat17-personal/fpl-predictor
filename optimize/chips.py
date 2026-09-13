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

import config

HALVES = {"H1": range(1, 20), "H2": range(20, 39)}
WC_SLOT = {"H1": 8, "H2": 28}
SCORED_DECAY = 0.84   # wc's forward-sum discount across the visibility window;
# matches backtest/walk_forward.py::_plan_col's multi-GW discount exactly.


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


def scored_schedule(preds: pd.DataFrame, xp_col: str = "xp_med", visibility: int = 4,
                    hysteresis: float | None = None,
                    capt_col: str | None = None) -> dict[int, str]:
    """xP-scored causal chip schedule ("fire now vs. best visible later").

    Keeps `causal_schedule`'s exact visibility-window shell (a decision at GW g
    only ever sees g..g+visibility -- the B3 causal fix) but replaces the
    fixture-structure if/elif decision body with a common scoring rule: fire
    chip c at gameweek g when c's score at g is within `hysteresis` of the best
    score c reaches anywhere in the visible window. An unused chip at the end
    of its half fires at the latest free gameweek instead of going unused
    (v1's end-of-half forcing rule, generalised to every chip).

    Reads only `xp_col`/`capt_col`, `gw`, `player_code`, `team` -- NEVER a
    realised-outcome column (`y_points`/`actual`/`y_minutes`), and the decision
    at g never looks at a gameweek beyond `g + visibility`.

    Proxy scores (the implementer's declared starting point, not received
    truth -- the harness judges them):
      - tc: the best single-player gameweek value at g, from `capt_col` when
        given (so an adopted ceiling-EV armband also drives the Triple
        Captain trigger) and from `xp_col` otherwise -- the extra captain
        multiple is exactly one more copy of the best captain.
      - bb: the sum of ranks 12-15 of the gameweek's descending xP vector --
        the bench of a top-15 proxy squad, which Bench Boost turns into points.
      - fh: the sum of ranks 1-11, scaled by the share of clubs blanking at g
        (`bgw_clubs / n_clubs`) -- the fraction of a normal squad that would
        otherwise score nothing.
      - wc: the visibility-window-discounted forward sum of ranks 1-11 across
        `window`, using the same 0.84 decay `backtest/walk_forward.py::
        _plan_col` uses, so a wildcard fires into the best visible fixture run
        rather than at a fixed calendar slot.
    """
    hysteresis = config.CHIPS_V2_HYSTERESIS if hysteresis is None else hysteresis
    struct = _fixture_structure(preds).set_index("gw")
    n_clubs = preds.team.nunique()

    gwp = preds.groupby(["gw", "player_code"])[xp_col].sum().reset_index()
    by_gw: dict[int, list[float]] = {
        g: sorted(v[xp_col].tolist(), reverse=True) for g, v in gwp.groupby("gw")
    }
    capt_source = capt_col or xp_col
    capt_gwp = (preds.groupby(["gw", "player_code"])[capt_source].sum().reset_index()
                if capt_col else gwp.rename(columns={xp_col: capt_source}))
    best_capt = capt_gwp.groupby("gw")[capt_source].max()

    def top11(g: int) -> float:
        return sum(by_gw.get(g, [])[:11])

    def bench4(g: int) -> float:
        return sum(by_gw.get(g, [])[11:15])

    schedule: dict[int, str] = {}
    for half, gws in HALVES.items():
        half_gws = [g for g in gws if g in struct.index]
        if not half_gws:
            continue
        remaining = {"wc", "fh", "bb", "tc"}

        # Precompute every chip's score at every gameweek of this half up front
        # -- each score depends only on that gameweek's own value (tc/bb/fh) or
        # on gameweeks within its own g..g+visibility window (wc), never on
        # anything the sequential firing loop below decides.
        scores: dict[str, dict[int, float]] = {c: {} for c in remaining}
        for g in half_gws:
            window = [w for w in half_gws if g <= w <= g + visibility]
            bgw_here = struct.loc[g, "bgw_clubs"]
            scores["tc"][g] = float(best_capt.get(g, 0.0))
            scores["bb"][g] = float(bench4(g))
            scores["fh"][g] = float(top11(g) * (bgw_here / n_clubs if n_clubs else 0.0))
            scores["wc"][g] = float(sum(
                (SCORED_DECAY ** (w - g)) * top11(w) for w in window))

        for g in half_gws:
            window = [w for w in half_gws if g <= w <= g + visibility]
            for c in ("wc", "fh", "bb", "tc"):
                if c not in remaining:
                    continue
                best_in_window = max(scores[c][w] for w in window)
                if scores[c][g] >= best_in_window - hysteresis:
                    schedule[g] = c
                    remaining.discard(c)
                    break   # one chip max per gameweek

        # End-of-half forcing rule (v1's spirit, generalised): a chip still
        # unused by the end of the half fires at the latest gameweek that
        # doesn't already have a chip, rather than being wasted.
        if remaining:
            free = [g for g in reversed(half_gws) if g not in schedule]
            for c in ("wc", "fh", "bb", "tc"):
                if c in remaining and free:
                    schedule[free.pop(0)] = c
                    remaining.discard(c)

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
