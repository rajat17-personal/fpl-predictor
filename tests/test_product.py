"""Tests for the product layer: intervals, snapshot, export builders, price
model dataset, solver locks/excludes, the API, and the digest."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

import config
from ops.jsonio import write_json

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


# ---------------------------------------------------------------- intervals

def test_intervals_fit_apply_coverage():
    from models.intervals import apply_intervals, coverage_report, fit_intervals
    rng = np.random.default_rng(1)
    n = 4000
    preds = pd.DataFrame({
        "position": rng.choice(["GK", "DEF", "MID", "FWD"], n),
        "xp_med": rng.gamma(2, 1, n),
    })
    preds["y_points"] = preds.xp_med + rng.normal(0, 1.5, n)
    art = fit_intervals(preds)
    out = apply_intervals(preds.rename(columns={"xp_med": "xp"}), art)
    assert {"p10", "p90"} <= set(out.columns)
    assert (out.p10 <= out.p90 + 1e-9).all()
    assert (out.p10 >= 0).all()
    cov = coverage_report(preds, art)["overall"]
    assert 0.70 <= cov <= 0.95          # nominal 0.80, clipping widens it


# ---------------------------------------------------------------- snapshot

def test_snapshot_frame_shape():
    from data.snapshot import snapshot_frame
    df = snapshot_frame(fake_boot(), dt.datetime(2026, 8, 31, tzinfo=dt.timezone.utc))
    assert len(df) == 22
    assert {"player_code", "price_m", "net_gw", "position"} - set(df.columns) == {"net_gw"}
    assert df.next_gw.iloc[0] == 1
    assert df.position.isin(["GK", "DEF", "MID", "FWD"]).all()
    assert df.selected_by_percent.dtype.kind == "f"


# ---------------------------------------------------------------- export

def test_export_builders():
    from predict.export import build_captains, build_chips, build_table, build_ticker
    boot = fake_boot()
    pool = fake_pool(boot)
    table = build_table(pool, boot)
    assert len(table) == len(pool)
    assert table[0]["xp"] == max(r["xp"] for r in table)
    assert {"ownership", "status", "team_short"} <= set(table[0])
    caps = build_captains(table, n=3)
    assert len(caps) == 3
    assert caps[0]["xp_capt"] >= caps[-1]["xp_capt"]

    fixtures = [{"event": 1, "team_h": 1, "team_a": 2, "team_h_difficulty": 2,
                 "team_a_difficulty": 4, "kickoff_time": "2026-09-05T14:00:00Z"},
                {"event": 2, "team_h": 2, "team_a": 1, "team_h_difficulty": 3,
                 "team_a_difficulty": 3, "kickoff_time": "2026-09-12T14:00:00Z"}]
    ticker = build_ticker(boot, fixtures, 1)
    assert len(ticker) == len(TEAMS)
    t1 = next(t for t in ticker if t["short"] == "C01")
    assert t1["gws"][0]["fixtures"][0]["opp"] == "C02"
    chips = build_chips(fixtures, 1)
    assert chips["structure"][0] == {"gw": 1, "dgw_clubs": 0, "bgw_clubs": 0}
    dgw = build_chips(fixtures + [{"event": 1, "team_h": 1, "team_a": 3,
                                   "team_h_difficulty": 2, "team_a_difficulty": 2,
                                   "kickoff_time": "2026-09-06T14:00:00Z"}], 1)
    assert dgw["structure"][0]["dgw_clubs"] == 1        # club 1 plays twice
    assert dgw["structure"][1]["bgw_clubs"] == 1        # club 3 misses GW2


# ------------------------------------------------ export contract (Phase 9 plan 09-10)
#
# T-09-10-01: the web/data/*.json export contract's file set and each file's
# top-level key set must not change silently -- both the vanilla site and the
# React rebuild consume this schema unchanged (PROJECT.md's Contract
# constraint), and Phase 4's frozen E2E fixtures assert it independently.
# This is the fast, always-on regression guard for the same invariant.

EXPORT_CONTRACT_FILES = {"meta.json", "xp_table.json", "captains.json",
                         "squad.json", "fixtures.json", "chips.json",
                         "standings.json", "leaders.json"}

EXPORT_CONTRACT_DICT_KEYS = {
    "meta.json": {"gw", "horizon", "deadline_utc", "generated_utc",
                 "model_mtime_utc", "season"},
    "squad.json": {"squad", "captain", "formation", "cost", "xi_xp"},
    "chips.json": {"note", "structure"},
    "leaders.json": {"points", "goals", "assists", "clean_sheets", "cards"},
}

EXPORT_CONTRACT_LIST_ROW_KEYS = {
    "xp_table.json": {"player_code", "player_id", "name", "team", "team_short",
                      "position", "price_m", "xp", "xp_capt", "p10", "p90",
                      "ownership", "status", "news"},  # 14 keys (build_table's `cols`)
    "captains.json": {"name", "team", "team_short", "position", "price_m",
                      "xp", "xp_capt", "ownership"},
    "fixtures.json": {"team", "short", "gws", "ease", "xg_next", "xgc_next"},
    "standings.json": {"team", "short", "played", "won", "drawn", "lost",
                       "gf", "ga", "gd", "points"},
}

_MODEL_ARTIFACT = config.ROOT / "models" / "artifacts" / "xp_model.joblib"
needs_model_artifact = pytest.mark.skipif(
    not _MODEL_ARTIFACT.exists(),
    reason="models/artifacts/xp_model.joblib is gitignored/untracked -- "
           "run `python -m models.train` first")


def _export_fixture_files() -> dict:
    """Build every file predict.export.export() writes, the same way it does,
    on deterministic fixture data (no network) -- mirrors export()'s own
    `files` dict construction so a change to either place is caught here."""
    from predict.export import (build_captains, build_chips, build_leaders,
                                build_meta, build_squad, build_standings,
                                build_table, build_ticker)
    boot = fake_boot()
    # The real predict.live._gw_pool never carries player_id through its own
    # groupby aggregation (only _boot_meta below supplies it, via the
    # player_code join) -- drop fake_pool's own player_id so this fixture
    # matches that real shape instead of colliding on merge (pandas would
    # otherwise suffix both sides' player_id into player_id_x/_y and silently
    # drop the plain column build_table's own `cols` list expects).
    pool = fake_pool(boot).drop(columns=["player_id"])
    fixtures = [{"event": 1, "team_h": 1, "team_a": 2, "team_h_difficulty": 2,
                "team_a_difficulty": 4, "kickoff_time": "2026-09-05T14:00:00Z"}]
    gw = 1
    table = build_table(pool, boot)
    return {
        "meta.json": build_meta(boot, gw, 1),
        "xp_table.json": table,
        "captains.json": build_captains(table),
        "squad.json": build_squad(pool),
        "fixtures.json": build_ticker(boot, fixtures, gw),
        "chips.json": build_chips(fixtures, gw),
        "standings.json": build_standings(boot, fixtures),
        "leaders.json": build_leaders(boot),
    }


@needs_model_artifact
def test_export_contract_file_set_and_key_sets():
    """The export contract's file set and each file's top-level key set are
    exactly what plan 09-10 measured before touching predict/live.py or
    predict/export.py -- fails by name if either widens/narrows/renames a key
    or drops/adds a file, closing T-09-10-01."""
    files = _export_fixture_files()
    assert set(files) == EXPORT_CONTRACT_FILES

    for name, expected_keys in EXPORT_CONTRACT_DICT_KEYS.items():
        assert set(files[name].keys()) == expected_keys, (name, sorted(files[name]))

    for name, expected_keys in EXPORT_CONTRACT_LIST_ROW_KEYS.items():
        rows = files[name]
        assert rows, f"{name} produced no rows against the fixture pool"
        assert set(rows[0].keys()) == expected_keys, (name, sorted(rows[0]))


_PHASE10_FEATURE_PREFIXES = ('"av_', '"tm_', '"nw_', '"bracket_')


def test_phase10_flags_default_off_leaves_export_contract_unchanged():
    """Phase 10 closed with all nine flags (availability_flags,
    transfermarkt_injury, news_sentiment [never registered -- declined on
    cost], bracket_ridge/xgb/catboost/mlp/rnn/transformer) staying
    default-off (see IMPROVEMENTS.md Phase G's results table -- every row
    REJECTED/HOLD/DECLINED). The av_/tm_/nw_/bracket_ column families are
    training-time features and a bracket-internal model choice; none of
    them belongs in the product contract regardless of any flag's state.
    Checks the REAL emitted web/data/*.json payloads (not a fixture build),
    matching plan 09-10's own real-export-run precedent for this class of
    regression test. A future phase that adopts one of these flags and
    deliberately wires it into the export must update this assertion."""
    import glob

    payload_paths = sorted(glob.glob(str(config.ROOT / "web" / "data" / "*.json")))
    assert payload_paths, "no web/data/*.json payloads found -- run python -m predict.export first"

    bad = []
    for path in payload_paths:
        text = open(path).read()
        for prefix in _PHASE10_FEATURE_PREFIXES:
            if prefix in text:
                bad.append((path, prefix))
    assert not bad, f"training-time feature keys leaked into the product contract: {bad}"


def test_no_adopted_experiment_flags_needed_product_wiring():
    """Phase 9 closed with every experiment flag default-off (see
    IMPROVEMENTS.md Phase F's results table -- all eight REJECTED/not
    triggered/not acquirable) -- so this plan's own acceptance criterion
    ("wire nothing for a flag that stayed off") means predict/live.py and
    predict/export.py needed no behavioural changes, and the export contract
    above is exactly the pre-phase-9 contract, not a widened one. A future
    phase that adopts a flag must update this assertion deliberately."""
    assert not any(config.EXPERIMENTS.values()), (
        "an experiment flag flipped default-on -- predict/live.py and/or "
        "predict/export.py need wiring for it (see plan 09-10's Task 2 "
        "instructions for the capt_ceiling/capt_mc/chips_v2/team_strength/"
        "understat/fotmob/fbref_v2/rl_strategy seams)")


# ---------------------------------------------------------------- price model

def test_price_dataset_labels():
    from models.price import build_dataset
    days = pd.date_range("2026-08-01", periods=5).date
    rows = []
    for i, d in enumerate(days):
        rows.append({"player_id": 1, "date": str(d), "price_m": 5.0 + 0.1 * (i >= 3),
                     "selected_by_percent": 10.0, "total_players": 1_000_000,
                     "transfers_in_event": 1000 * i, "transfers_out_event": 100,
                     "status": "a", "form": "1.0", "cost_change_event": 0,
                     "cost_change_start": 0, "name": "A", "team": "X",
                     "position": "MID"})
    ds = build_dataset(pd.DataFrame(rows))
    assert len(ds) == 4                              # 5 days -> 4 consecutive pairs
    assert ds.label.tolist() == [0, 0, 1, 0]         # rise lands on day 3->4
    assert "net_per_owner" in ds.columns


# ---------------------------------------------------------------- optimizer

def test_optimize_gw_force_exclude():
    from optimize.transfers import optimize_gw
    boot = fake_boot()
    pool = fake_pool(boot)
    squad_codes = (list(pool[pool.position == "GK"].player_code[:2])
                   + list(pool[pool.position == "DEF"].player_code[:5])
                   + list(pool[pool.position == "MID"].player_code[:5])
                   + list(pool[pool.position == "FWD"].player_code[:3]))
    squad = {c: float(pool.set_index("player_code").price_m[c]) for c in squad_codes}
    target_buy = int(pool[~pool.player_code.isin(squad_codes)].player_code.iloc[0])
    target_sell = squad_codes[3]
    r = optimize_gw(pool, squad, bank=5.0, free_transfers=2,
                    force=[target_buy], exclude=[target_sell])
    assert target_buy in r["squad"]
    assert target_sell not in r["squad"]


# ---------------------------------------------------------------- API

def test_api_solve_and_resolve(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as m
    boot = fake_boot()
    pool = fake_pool(boot)
    monkeypatch.setattr(m, "_pool", lambda horizon=1: m.PoolSnapshot(pool, 1, boot, 0))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)
    c = TestClient(m.app)

    lock_name = pool.iloc[0]["name"]
    r = c.post("/api/solve", json={"locks": [lock_name]})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "squad" and len(body["squad"]) == 15
    assert lock_name in [p["name"] for p in body["squad"]]
    assert sum(p["starting"] for p in body["squad"]) == 11
    assert sum(p["captain"] for p in body["squad"]) == 1

    # name resolution: exact beats substring
    two = pd.concat([pool, pool.iloc[[0]].assign(name="X " + lock_name,
                                                 player_code=99999, xp=99.0)],
                    ignore_index=True)
    assert m._resolve(two, [lock_name]) == [int(pool.iloc[0].player_code)]

    # bad player -> 422, auth gate -> 401
    assert c.post("/api/solve", json={"locks": ["Nobody Real"]}).status_code == 422
    monkeypatch.setenv("FPL_API_KEYS", "k1")
    assert c.post("/api/solve", json={}).status_code == 401


def test_free_transfer_accrual():
    from api.main import ft_from_history

    def ev(g, t):
        return {"event": g, "event_transfers": t}

    # untouched: +1 per week, capped at 5
    h = {"current": [ev(g, 0) for g in range(1, 9)], "chips": []}
    assert ft_from_history(h, 3) == 2
    assert ft_from_history(h, 7) == 5     # 1+1+1+1+1 caps
    assert ft_from_history(h, 9) == 5
    # spending: 2 transfers in GW2 with 1 FT -> hits, floor at 0, then +1
    h = {"current": [ev(1, 0), ev(2, 2)], "chips": []}
    assert ft_from_history(h, 3) == 1
    # wildcard week neither spends nor loses the stock
    h = {"current": [ev(1, 0), ev(2, 8)], "chips": [{"name": "wildcard", "event": 2}]}
    assert ft_from_history(h, 3) == 2


# ---------------------------------------------------------------- digest

def test_digest_render(tmp_path, monkeypatch):
    import predict.digest as dg
    (tmp_path / "history").mkdir()
    meta = {"gw": 9, "deadline_utc": "2026-10-24T10:00:00Z"}
    table = [{"name": f"P{i}", "team_short": "AAA", "team": "AAA", "price_m": 5.0,
              "xp": 5.0 - i * 0.1, "xp_capt": 6.0 - i * 0.1, "p10": 1.0,
              "p90": 9.0, "ownership": 5.0 + i, "status": "a"} for i in range(8)]
    write_json(meta, tmp_path / "meta.json")
    write_json(table, tmp_path / "xp_table.json")
    write_json(table[:3], tmp_path / "captains.json")
    monkeypatch.setattr(dg, "WEB_DATA", tmp_path)
    d = dg.build_digest()
    txt, html = dg.to_text(d), dg.to_html(d)
    assert "GW9" in txt and "Deadline" in txt
    assert "Captain pick: P0" in txt
    assert "Differential: P0" in txt              # ownership 5% < 10% cap
    assert "Not affiliated" in txt and "Not affiliated" in html
