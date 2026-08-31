"""Contract tests for the FastAPI solver API: /api/health, /api/meta, and
/api/solve. Every test bypasses _refresh()'s real network + model-artifact
load via monkeypatched _load_live/_pool and the autouse conftest fixture that
seeds a non-None artifact sentinel."""
from __future__ import annotations

import pandas as pd
import pytest

import config

# ---------------------------------------------------------------- fixtures

TEAMS = [{"id": i, "name": f"Club {i}", "short_name": f"C{i:02d}"} for i in range(1, 11)]


def fake_boot(n_per_pos=(3, 7, 7, 5)) -> dict:
    """Bootstrap-static shaped enough for snapshot/export builders."""
    elements, code = [], 1000
    for etype, n in zip((1, 2, 3, 4), n_per_pos):
        for k in range(n):
            code += 1
            elements.append({
                "id": code - 900, "code": code, "web_name": f"P{code}",
                "team": (code % 10) + 1, "element_type": etype, "status": "a",
                "chance_of_playing_next_round": None,
                "now_cost": 40 + (code % 25), "cost_change_event": 0,
                "cost_change_start": 0, "selected_by_percent": f"{(code % 50) / 2:.1f}",
                "transfers_in_event": code * 3 % 5000,
                "transfers_out_event": code * 7 % 5000,
                "ep_next": "2.5", "ep_this": "2.0", "event_points": 2,
                "form": "1.5", "total_points": 20, "minutes": 900, "news": "",
            })
    return {"elements": elements, "teams": TEAMS, "total_players": 1_000_000,
            "events": [{"id": 1, "is_next": True, "finished": False,
                        "deadline_time": "2026-09-04T17:30:00Z"}]}


def fake_pool(boot: dict) -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(0)
    pos = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    rows = [{"player_code": el["code"], "player_id": el["id"],
             "name": el["web_name"], "team": f"Club {el['team']}",
             "position": pos[el["element_type"]],
             "price_m": el["now_cost"] / 10.0,
             "xp": float(rng.uniform(0.5, 6.0))} for el in boot["elements"]]
    df = pd.DataFrame(rows)
    df["xp_capt"] = df.xp * 1.1
    df["actual"] = 0.0
    return df


# ---------------------------------------------------------------- health/meta

def test_health_and_meta_contract(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as m

    boot = fake_boot()
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))
    c = TestClient(m.app)

    r = c.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"ok", "gw", "pool_age_s"}
    assert body["ok"] is True

    r = c.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"gw", "deadline_utc", "season"}
    assert body["season"] == config.CURRENT_SEASON
    assert body["gw"] == 1
    assert body["deadline_utc"] == "2026-09-04T17:30:00Z"


def test_state_isolation_and_no_artifact_load(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as m

    # Autouse fixture ran: pristine state (minus the seeded artifact sentinel).
    assert m._state["boot"] is None
    assert m._solve_cache == {}

    boot = fake_boot()
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))

    def _raise_if_called(*args, **kwargs):
        raise AssertionError("joblib.load must never be called during tests")

    monkeypatch.setattr(m.joblib, "load", _raise_if_called)

    c = TestClient(m.app)
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/meta").status_code == 200


# ---------------------------------------------------------------- /api/solve

def test_solve_squad_contract(monkeypatch):
    """From-scratch squad response: full contract, lock honoured, bad lock 422."""
    from fastapi.testclient import TestClient
    import api.main as m

    boot = fake_boot()
    pool = fake_pool(boot)
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (pool, 1, boot))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)
    c = TestClient(m.app)

    lock_name = pool.iloc[0]["name"]
    r = c.post("/api/solve", json={"locks": [lock_name]})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"gw", "kind", "squad", "captain", "formation",
                                "cost", "xi_xp"}
    assert body["kind"] == "squad"
    assert len(body["squad"]) == 15
    assert sum(p["starting"] for p in body["squad"]) == 11
    assert sum(p["captain"] for p in body["squad"]) == 1
    for row in body["squad"]:
        assert set(row.keys()) == {"player_code", "name", "team", "position",
                                   "price_m", "xp", "starting", "captain"}
    assert body["cost"] <= config.BUDGET
    assert lock_name in [p["name"] for p in body["squad"]]

    bad = c.post("/api/solve", json={"locks": ["Nobody Real"]})
    assert bad.status_code == 422


BOUNDS_CASES = [
    ({"free_transfers": 0}, 200),
    ({"free_transfers": 5}, 200),
    ({"free_transfers": 6}, 422),
    ({"free_transfers": -1}, 422),
    ({"horizon": 1}, 200),
    ({"horizon": 6}, 200),
    ({"horizon": 0}, 422),
    ({"horizon": 7}, 422),
    ({"max_transfers": 0}, 200),
    ({"max_transfers": 15}, 200),
    ({"max_transfers": 16}, 422),
    ({"mode": "normal"}, 200),
    ({"mode": "tc"}, 200),
    ({"mode": "bb"}, 200),
    ({"mode": "wildcard"}, 422),
]


@pytest.mark.parametrize("payload,expected_status", BOUNDS_CASES)
def test_solve_request_bounds(monkeypatch, payload, expected_status):
    """SolveRequest bounds at each edge and one step outside."""
    from fastapi.testclient import TestClient
    import api.main as m

    boot = fake_boot()
    pool = fake_pool(boot)
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (pool, 1, boot))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)
    c = TestClient(m.app)

    r = c.post("/api/solve", json=payload)
    assert r.status_code == expected_status


def test_solve_resolution_and_rounding(monkeypatch):
    """Exact money/xp rounding and _resolve's name tie-break rules."""
    from fastapi.testclient import TestClient
    import api.main as m

    boot = fake_boot()
    pool = fake_pool(boot)
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (pool, 1, boot))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)
    c = TestClient(m.app)

    r = c.post("/api/solve", json={})
    assert r.status_code == 200
    body = r.json()
    P = pool.set_index("player_code")
    for row in body["squad"]:
        code = row["player_code"]
        assert row["price_m"] == float(P.price_m[code])
        assert row["xp"] == round(float(P.xp[code]), 2)

    # _resolve: exact match beats a substring danger ("saka" is a substring of
    # "wan-bissaka" — a naive substring scan would wrongly match it).
    saka_code, wanbissaka_code = 500001, 500002
    named = pool.iloc[:2].copy()
    named["player_code"] = [saka_code, wanbissaka_code]
    named["name"] = ["Saka", "Wan-Bissaka"]
    assert m._resolve(named, ["saka"]) == [saka_code]

    # _resolve: identical names tie-break to the higher-xp player.
    tie_lo, tie_hi = 500003, 500004
    tied = pool.iloc[:2].copy()
    tied["player_code"] = [tie_lo, tie_hi]
    tied["name"] = ["Duplicate Name", "Duplicate Name"]
    tied["xp"] = [3.0, 7.0]
    assert m._resolve(tied, ["Duplicate Name"]) == [tie_hi]
