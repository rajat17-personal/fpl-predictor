"""Pure, offline tests for data/backfill_snapshot.py's date/ordering logic.

Deliberately imports only the pure helpers (missing_days, pick_capture,
parse_days) -- none of these touch SNAP_DIR, requests, or archive.org, so
this file needs no mocks, no fixtures, and no monkeypatching to be
meaningful, and passes with the network unavailable.
"""
import datetime as dt

import pytest

from data.backfill_snapshot import missing_days, parse_days, pick_capture


def _d(iso: str) -> dt.date:
    return dt.date.fromisoformat(iso)


def test_missing_days_real_archive_shape():
    # Present: 08-31, 09-07, 09-11, 09-12, 09-13. Today: 09-13.
    existing = {_d(s) for s in
                ("2026-08-31", "2026-09-07", "2026-09-11", "2026-09-12", "2026-09-13")}
    today = _d("2026-09-13")
    result = missing_days(existing, today)
    expected = [_d(s) for s in (
        "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05",
        "2026-09-06", "2026-09-08", "2026-09-09", "2026-09-10",
    )]
    assert result == expected


def test_missing_days_contiguous_run_is_empty():
    existing = {_d("2026-09-01"), _d("2026-09-02"), _d("2026-09-03")}
    today = _d("2026-09-04")
    assert missing_days(existing, today) == []


def test_missing_days_empty_archive_is_empty():
    assert missing_days(set(), _d("2026-09-13")) == []


def test_missing_days_never_includes_today():
    existing = {_d("2026-09-01")}
    today = _d("2026-09-13")
    result = missing_days(existing, today)
    assert today not in result
    assert result[-1] == _d("2026-09-12")


def test_pick_capture_orders_by_closeness_to_target():
    # target_min default is 150 (02:30 UTC).
    timestamps = [
        "20260910070148",  # 07:01 -> 271 min -> |271-150| = 121
        "20260910023000",  # 02:30 exact -> 0
        "20260910000028",  # 00:00 -> 150 min away
    ]
    ordered = pick_capture(timestamps)
    assert ordered[0] == "20260910023000"
    assert ordered[-1] == "20260910070148"


def test_pick_capture_ties_broken_by_earlier_timestamp():
    # Both equidistant from 02:30 (150 min): 01:00 (60 min away) and 04:00 (90
    # min away) are not a tie -- construct a genuine tie: 01:30 (60 min) and
    # 03:30 (60 min) are both 60 away from 150? 01:30=90min -> |90-150|=60;
    # 03:30=210min -> |210-150|=60. Genuine tie; earlier wins.
    timestamps = ["20260910033000", "20260910013000"]
    ordered = pick_capture(timestamps)
    assert ordered[0] == "20260910013000"


def test_parse_days_round_trips():
    result = parse_days("2026-09-01, 2026-09-02,2026-09-03")
    assert result == [_d("2026-09-01"), _d("2026-09-02"), _d("2026-09-03")]


def test_parse_days_rejects_malformed_token():
    with pytest.raises(SystemExit):
        parse_days("2026-09-01,not-a-date")
