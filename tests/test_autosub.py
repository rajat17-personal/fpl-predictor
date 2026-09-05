"""B2 regression tests: autosubs must respect FPL formation rules."""
import pandas as pd

from backtest.season import _autosub


def _idx(rows):
    df = pd.DataFrame(rows).set_index("code")
    return df.position, df.minutes, df.xp


def _team(def_minutes_out=0):
    """3-4-3 XI + bench (GK, DEF, MID, FWD). Codes 1-15."""
    rows = []
    spec = [(1, "GK", 90), (2, "DEF", 90), (3, "DEF", 90), (4, "DEF", def_minutes_out),
            (5, "MID", 90), (6, "MID", 90), (7, "MID", 90), (8, "MID", 90),
            (9, "FWD", 90), (10, "FWD", 90), (11, "FWD", 90),
            (12, "GK", 90), (13, "DEF", 90), (14, "MID", 90), (15, "FWD", 90)]
    for code, p, m in spec:
        rows.append({"code": code, "position": p, "minutes": float(m),
                     "xp": 5.0 if p == "MID" else 3.0})   # MIDs look juicier
    return rows


def test_blank_def_at_minimum_gets_def_not_mid():
    """3 DEF, one blanks -> only the bench DEF may come in (never the higher-xP MID)."""
    pos, mins, xp = _idx(_team(def_minutes_out=0))
    starters, squad = list(range(1, 12)), list(range(1, 16))
    xi = _autosub(starters, squad, pos, mins, xp)
    assert 13 in xi and 14 not in xi
    assert sum(pos[c] == "DEF" for c in xi) == 3


def test_blank_def_no_bench_def_leaves_slot_unfilled():
    """No played bench DEF -> field 10; FPL will not break the 3-DEF minimum."""
    rows = _team(def_minutes_out=0)
    rows[12]["minutes"] = 0.0                     # bench DEF (code 13) also blanks
    pos, mins, xp = _idx(rows)
    xi = _autosub(list(range(1, 12)), list(range(1, 16)), pos, mins, xp)
    assert len(xi) == 10
    assert 14 not in xi and 15 not in xi          # MID/FWD may not fill a DEF slot


def test_blank_def_above_minimum_takes_best_xp():
    """4 DEF, one blanks -> minimum still met, so the best-xP bench player comes in."""
    rows = _team(def_minutes_out=0)
    rows[7] = {"code": 8, "position": "DEF", "minutes": 90.0, "xp": 3.0}  # 4-3-3 now
    pos, mins, xp = _idx(rows)
    xi = _autosub(list(range(1, 12)), list(range(1, 16)), pos, mins, xp)
    assert 14 in xi                                # the juicy MID is legal here
    assert len(xi) == 11


def test_gk_only_replaced_by_gk():
    rows = _team()
    rows[0]["minutes"] = 0.0                      # starting GK blanks
    pos, mins, xp = _idx(rows)
    xi = _autosub(list(range(1, 12)), list(range(1, 16)), pos, mins, xp)
    assert 12 in xi and sum(pos[c] == "GK" for c in xi) == 1
