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
