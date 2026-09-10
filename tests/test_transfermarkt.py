"""Offline tests for data/transfermarkt.py's probe-only surface (plan 10-05).

All three tests run with zero network access: `parse_injury_table` is
exercised against small in-memory HTML strings (never a real captured page,
per D-07's "raw page cache may stay uncommitted" posture), and `probe` is
exercised with `data.transfermarkt._fetch_page` monkeypatched.
"""
from __future__ import annotations

import pandas as pd
import pytest

import data.transfermarkt as tm

_INJURY_TABLE_HTML = """
<table>
  <thead>
    <tr>
      <th>Season</th><th>Injury</th><th>from</th><th>until</th>
      <th>Days</th><th>Games missed</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>24/25</td><td>Thigh strain</td><td>Jan 1, 2025</td><td>Jan 15, 2025</td>
      <td>14</td><td>3</td>
    </tr>
    <tr>
      <td>23/24</td><td>Ankle sprain</td><td>Mar 3, 2024</td><td>Mar 20, 2024</td>
      <td>17</td><td>4</td>
    </tr>
  </tbody>
</table>
"""

_CHALLENGE_PAGE_HTML = """
<!DOCTYPE html>
<html>
  <head><title>Just a moment...</title></head>
  <body>Checking your browser before accessing transfermarkt.com.</body>
</html>
"""


def test_parse_injury_table_on_saved_fixture():
    df = tm.parse_injury_table(_INJURY_TABLE_HTML, what="test fixture")
    assert list(df.columns) == ["season", "injury", "from_date", "until_date",
                                 "days_out", "games_missed"]
    assert len(df) == 2
    assert df.iloc[0]["injury"] == "Thigh strain"
    assert df.iloc[1]["games_missed"] == 4


def test_parse_injury_table_raises_on_challenge_page():
    with pytest.raises(ValueError, match="anti-bot challenge page detected"):
        tm.parse_injury_table(_CHALLENGE_PAGE_HTML, what="test fixture")


def test_probe_records_verdict_per_page_without_raising(monkeypatch):
    # Total-block case: every fetch (search AND injury-page) returns None,
    # exactly as a real DataDome/Cloudflare block would look from this
    # module's own perspective -- probe() must still return one dict per
    # requested page, each carrying a 'verdict' key, and must never raise.
    monkeypatch.setattr(tm, "_fetch_page", lambda *a, **k: None)

    class _FakeSnapshot:
        pass

    fake_df = pd.DataFrame({
        "name": [f"Player {i}" for i in range(8)],
        "player_code": list(range(8)),
        "selected_by_percent": list(range(8, 0, -1)),
    })
    monkeypatch.setattr(
        tm, "_select_probe_players",
        lambda n: fake_df.head(n)[["name", "player_code"]].assign(resolved_player_code=None))
    monkeypatch.setattr(tm, "write_json", lambda *a, **k: None)

    rows = tm.probe(n=8)

    assert len(rows) == 8
    for row in rows:
        assert "verdict" in row
        assert row["verdict"] in {"ok", "challenge", "http_error", "parse_error", "id_unresolved"}
        # every fetch (search included) returned None -> id never resolved
        assert row["verdict"] == "id_unresolved"
