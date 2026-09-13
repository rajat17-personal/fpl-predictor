"""Phase 9 plan 09-04 regression tests: the xP-scored causal chip scheduler
(`optimize.chips.scored_schedule`, the `chips_v2` experiment) and the
untouched v1 heuristic scheduler (`optimize.chips.causal_schedule`)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import season as season_mod
from optimize import chips


def _fixture_preds(seed: int, gws=range(1, 16), n: int = 40) -> pd.DataFrame:
    """Fixture-level preds shaped for `backtest.season.run_season`: one row
    per player per gameweek, position/team/price constant per player, xP /
    realised points / minutes randomized per gameweek. Small enough position
    counts and a narrow price band keep every gameweek's squad solve legal
    (budget, quotas, formations) without a real trained model."""
    rng = np.random.default_rng(seed)
    pos = (["GK"] * 4 + ["DEF"] * 12 + ["MID"] * 14 + ["FWD"] * 10)[:n]
    teams = rng.choice([f"T{j}" for j in range(10)], n)
    prices = np.round(rng.uniform(4.0, 8.0, n), 1)
    names = [f"p{i}" for i in range(n)]
    codes = np.arange(2000, 2000 + n)
    rows = []
    for gw in gws:
        xp = rng.gamma(2.0, 1.5, n)
        y_pts = rng.poisson(2, n).astype(float)
        y_mins = rng.choice([0, 60, 90], n, p=[0.2, 0.2, 0.6]).astype(float)
        for i in range(n):
            rows.append({
                "gw": gw, "player_code": codes[i], "name": names[i],
                "team": teams[i], "position": pos[i], "price_m": prices[i],
                "xp_med": xp[i], "y_points": y_pts[i], "y_minutes": y_mins[i],
            })
    return pd.DataFrame(rows)


def _make_preds(gws, n_players_per_team=3, n_teams=4, seed=0,
                dgw_map=None, bgw_map=None) -> pd.DataFrame:
    """Synthetic fixture-level predictions: `n_teams` clubs, `n_players_per_team`
    players each, one row per player per fixture. `dgw_map`/`bgw_map` map
    gw -> set of club codes that double / blank that gameweek, matching the
    shape `_fixture_structure` expects (columns: gw, player_code, team)."""
    rng = np.random.default_rng(seed)
    dgw_map = dgw_map or {}
    bgw_map = bgw_map or {}
    rows = []
    teams = [f"T{i}" for i in range(n_teams)]
    for gw in gws:
        blanks = set(bgw_map.get(gw, []))
        doubles = set(dgw_map.get(gw, []))
        for team in teams:
            if team in blanks:
                continue
            nfix = 2 if team in doubles else 1
            for _ in range(nfix):
                for p in range(n_players_per_team):
                    pc = f"{team}_{p}"
                    rows.append({"gw": gw, "player_code": pc, "team": team,
                                "xp_med": float(rng.uniform(1, 8))})
    return pd.DataFrame(rows)


# --- scored_schedule structural invariants ----------------------------------

def test_scored_schedule_one_chip_per_gw_and_per_half():
    """At most one chip per gameweek (trivially true of a dict keyed by gw),
    and at most one of each chip per half."""
    preds = _make_preds(range(1, 13))
    sched = chips.scored_schedule(preds, "xp_med")
    assert sched   # the synthetic frame should schedule at least one chip
    for half, gws in chips.HALVES.items():
        picked = [c for g, c in sched.items() if g in gws]
        assert len(picked) == len(set(picked)), (half, picked)


# --- leakage proof: blind to realised points --------------------------------

def test_scored_schedule_ignores_shuffled_y_points():
    """Adding a y_points column and shuffling it must not change the schedule
    -- scored_schedule reads only xp_col/capt_col, gw, player_code, team."""
    preds = _make_preds(range(1, 13))
    rng = np.random.default_rng(1)
    with_pts = preds.assign(y_points=rng.uniform(0, 10, len(preds)))
    sched1 = chips.scored_schedule(with_pts, "xp_med")

    shuffled = with_pts.assign(
        y_points=rng.permutation(with_pts["y_points"].to_numpy()))
    sched2 = chips.scored_schedule(shuffled, "xp_med")

    assert sched1 == sched2


# --- visibility proof: blind to anything beyond g + visibility --------------

def test_scored_schedule_blind_to_next_half():
    """H1's schedule must be identical whether or not H2 data is even present
    in the frame -- a decision inside H1 never reads H2 fixtures."""
    preds_h1_only = _make_preds(range(1, 13))
    sched_h1_only = chips.scored_schedule(preds_h1_only, "xp_med")

    preds_with_h2 = pd.concat(
        [preds_h1_only, _make_preds(range(20, 25), seed=2)], ignore_index=True)
    sched_with_h2 = chips.scored_schedule(preds_with_h2, "xp_med")

    h1_part = {g: c for g, c in sched_with_h2.items() if g <= 19}
    assert h1_part == sched_h1_only


def test_scored_schedule_blind_beyond_visibility_window():
    """Inflating xP for gameweeks beyond g + visibility must not change the
    chip already scheduled at g -- the decision at g never saw that data."""
    gws = list(range(1, 16))
    preds = _make_preds(gws, seed=3)
    sched = chips.scored_schedule(preds, "xp_med", visibility=4)

    candidates = [g for g in sched if g + 4 < max(gws)]
    assert candidates, "test setup: no fired gameweek with room beyond its window"
    g_fired = candidates[0]

    inflated = preds.copy()
    beyond = inflated.gw > g_fired + 4
    inflated.loc[beyond, "xp_med"] = inflated.loc[beyond, "xp_med"] * 100
    sched2 = chips.scored_schedule(inflated, "xp_med", visibility=4)

    assert sched2.get(g_fired) == sched.get(g_fired)


# --- hysteresis degenerate control ------------------------------------------

def test_hysteresis_huge_fires_earliest_possible_for_every_chip():
    """A hysteresis larger than the whole score range makes the "fire now vs.
    best later" condition trivially true everywhere, so each chip fires at the
    earliest gameweek still available to it (wc first by priority, then fh,
    bb, tc) -- i.e. every chip fires as early as its half's slots allow,
    rather than waiting for a genuinely better later gameweek."""
    gws = list(range(1, 10))
    preds = _make_preds(gws, seed=4)
    sched = chips.scored_schedule(preds, "xp_med", hysteresis=1e9)

    fired_gws = sorted(sched)
    assert fired_gws[:4] == gws[:4]
    assert {sched[g] for g in fired_gws[:4]} == {"wc", "fh", "bb", "tc"}


# --- regression guard: v1 untouched by this task's edits --------------------

def test_causal_schedule_unchanged_regression_guard():
    """causal_schedule's output on a fixed synthetic frame must be identical
    to the value recorded when scored_schedule was added (2026-09-08) --
    proves the v1 path was extended alongside, never modified."""
    preds = _make_preds(range(1, 13))
    sched = chips.causal_schedule(preds, "xp_med")
    assert sched == {7: "tc", 8: "wc"}


# --- v1 vs v2 sanity (mirrors the plan's own live-data verify) -------------

def test_scored_schedule_differs_from_causal_schedule():
    preds = _make_preds(range(1, 13))
    v1 = chips.causal_schedule(preds, "xp_med")
    v2 = chips.scored_schedule(preds, "xp_med")
    assert v2, "v2 scheduled no chips at all"
    assert v1 != v2, "v2 produced an identical schedule to v1"


# --- Task 2: Wildcard's isolated value --------------------------------------

def test_wc_chip_delta_recorded_against_zero_transfer_hold(monkeypatch):
    """A synthetic season with a scheduled wildcard produces exactly one `wc`
    chip_deltas entry, computed against a zero-transfer hold baseline (the
    same same-gameweek isolation FH/BB/TC already use), and the pre-existing
    fh/bb/tc entries are still recorded alongside it."""
    preds = _fixture_preds(seed=7)
    monkeypatch.setattr(
        season_mod.chips, "causal_schedule",
        lambda preds, xp_col: {5: "wc", 10: "fh", 12: "bb", 14: "tc"})

    df = season_mod.run_season(preds, "xp_med", use_chips=True, record_chips=True)
    deltas = df.attrs["chip_deltas"]
    by_chip: dict[str, list[dict]] = {}
    for d in deltas:
        by_chip.setdefault(d["chip"], []).append(d)

    assert len(by_chip.get("wc", [])) == 1, by_chip
    wc_delta = by_chip["wc"][0]["delta"]
    assert np.isfinite(wc_delta)
    assert "fh" in by_chip and "bb" in by_chip and "tc" in by_chip
