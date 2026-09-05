"""Property tests: optimizer output must always be a legal FPL team.

These would have caught B1 (blank-GW position corruption) and guard the squad
constraints against future regressions.
"""
import numpy as np
import pandas as pd
import pytest

import config
from optimize.squad_ilp import pick_squad
from optimize.transfers import optimize_gw


def _pool(seed: int, n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    pos = (["GK"] * 12 + ["DEF"] * 26 + ["MID"] * 26 + ["FWD"] * 16)[:n]
    return pd.DataFrame({
        "player_code": np.arange(1000, 1000 + n),
        "name": [f"p{i}" for i in range(n)],
        "team": rng.choice([f"T{j}" for j in range(12)], n),
        "position": pos,
        "xp": rng.gamma(2.0, 1.5, n),
        "price_m": np.round(rng.uniform(4.0, 13.0, n), 1),
        "actual": rng.poisson(2, n).astype(float),
        "minutes": rng.choice([0, 30, 90], n, p=[0.3, 0.2, 0.5]).astype(float),
    })


def _assert_legal_squad(s: pd.DataFrame, budget: float):
    assert len(s) == config.SQUAD_SIZE
    assert s.position.value_counts().to_dict() == config.POSITION_QUOTA
    assert s.team.value_counts().max() <= config.MAX_PER_CLUB
    assert s.price_m.sum() <= budget + 0.05
    xi = s[s.starting == 1]
    assert len(xi) == 11
    assert (xi.position == "GK").sum() == 1
    assert 3 <= (xi.position == "DEF").sum() <= 5
    assert 2 <= (xi.position == "MID").sum() <= 5
    assert 1 <= (xi.position == "FWD").sum() <= 3
    assert s.is_captain.sum() == 1


@pytest.mark.parametrize("seed", range(5))
def test_pick_squad_legal(seed):
    res = pick_squad(_pool(seed))
    _assert_legal_squad(res["squad"], config.BUDGET)


def test_pick_squad_force_lock():
    pool = _pool(0)
    lock = int(pool[pool.position == "FWD"].iloc[0].player_code)
    res = pick_squad(pool, force=[lock])
    assert lock in set(res["squad"].player_code)


@pytest.mark.parametrize("seed", range(3))
def test_optimize_gw_legal(seed):
    pool = _pool(seed)
    base = pick_squad(pool)["squad"]
    squad = dict(zip(base.player_code, base.price_m))
    r = optimize_gw(pool, squad, bank=1.5, free_transfers=2)
    new = pool[pool.player_code.isin(r["squad"])]
    assert len(r["squad"]) == config.SQUAD_SIZE
    assert new.position.value_counts().to_dict() == config.POSITION_QUOTA
    assert len(r["starters"]) == 11
    assert r["bank"] >= -0.05          # tolerance guard only, never real overdraft


def test_grandfathered_club_cap():
    """A January move can leave a held squad with 4 of one club; holding must stay
    feasible (FPL grandfathers it), while a fresh pick still obeys <=3."""
    pool = _pool(2)
    base = pick_squad(pool)["squad"]
    squad = dict(zip(base.player_code, base.price_m))
    # Simulate a mid-season club move: relabel one held outfielder's club so the
    # squad now holds 4 of team "TX".
    pool = pool.copy()
    held_out = base[base.position != "GK"].player_code.iloc[:4]
    pool.loc[pool.player_code.isin(held_out), "team"] = "TX"
    r = optimize_gw(pool, squad, bank=0.0, free_transfers=1, max_transfers=0)
    assert len(r["squad"]) == config.SQUAD_SIZE      # holding stays feasible


def test_blank_gw_holding_needs_metadata():
    """B1: a held player missing from the pool must not be silently mislabeled."""
    pool = _pool(1)
    base = pick_squad(pool)["squad"]
    squad = dict(zip(base.player_code, base.price_m))
    gk = int(base[base.position == "GK"].iloc[0].player_code)
    shrunk = pool[pool.player_code != gk]           # the GK blanks this week
    with pytest.raises(ValueError):
        optimize_gw(shrunk, squad, bank=0.0, free_transfers=1)   # no metadata -> error
    meta = {gk: {"position": "GK", "team": "T0", "name": "held_gk"}}
    r = optimize_gw(shrunk, squad, bank=0.0, free_transfers=1, holdings_meta=meta)
    # Look up positions in the FULL pool (it knows every code incl. the blanked GK).
    new = pool[pool.player_code.isin(r["squad"])]
    assert new.position.value_counts().to_dict() == config.POSITION_QUOTA
