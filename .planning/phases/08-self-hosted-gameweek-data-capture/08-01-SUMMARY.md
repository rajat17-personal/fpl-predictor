---
phase: 08-self-hosted-gameweek-data-capture
plan: 01
subsystem: data-ingest
tags: [fpl-api, vaastav-schema, backfill, atomic-write, tdd]

# Dependency graph
requires:
  - phase: 06-security-reliability-observability-hardening
    provides: ops.notify.report (alerting), ops.jsonio (safe JSON reads), atomic-write precedent (data/snapshot.py)
provides:
  - "data/gw_capture.py: capture one finished gameweek from the official FPL API into vaastav's merged_gw schema"
  - "MERGED_GW_HEADER (46-column contract), season_dir(), finished_gws(), capture() skeleton that 08-02 expands with the full per-player sweep, players_raw/fixtures refresh, xP resolution, and idempotency ledger"
affects: [08-02-full-backfill-and-refresh, 08-03-backfill-evidence, 08-04-ingest-guard-and-runbook, 08-05-cron-wiring]

# Actuals (#2632)
actuals:
  tokens: 15000
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent, atomic, per-finished-GW capture: tmp-file + os.replace on every CSV write, ledger-file regeneration (not append) on every capture() call"
    - "finished-AND-data-checked gate on bootstrap events[] before any row is treated as final"

key-files:
  created:
    - data/gw_capture.py
    - tests/test_gw_capture.py
    - .planning/phases/08-self-hosted-gameweek-data-capture/deferred-items.md
  modified:
    - tests/test_api.py

key-decisions:
  - "Team column built from bootstrap.teams[].name (full club name), never short_name -- matches data/odds.py's join key and vaastav's own convention (verified live against the real 2025-26 merged_gw.csv)"
  - "xP emitted as a missing value for every captured row this plan -- a later plan resolves it from data/snapshot.py's daily archive; documented as a real data gap, not a bug, in the module docstring"
  - "One element-summary sweep per capture() call regardless of how many gameweeks are targeted -- histories cover every round, so a per-GW sweep would be 656x N wasted requests"
  - "merged_gw.csv is regenerated from the gws/ ledger on every capture() call (never appended to) -- makes a re-run safe and a partial prior write self-healing"

patterns-established:
  - "Pattern 1 (idempotent atomic capture) from 08-PATTERNS.md, applied verbatim: tmp-suffix write + os.replace, temp file removed on any exception"

requirements-completed: []

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "data/gw_capture.py captures one finished gameweek from the FPL API into data/raw/{season}/merged_gw.csv in vaastav's 46-column schema"
    verification:
      - kind: integration
        ref: "tests/test_gw_capture.py::test_end_to_end_capture_reads_back_through_build_table"
        status: pass
      - kind: unit
        ref: "python -c import data.gw_capture as g, config; assert len(g.MERGED_GW_HEADER)==46 and set(config.MERGED_GW_COLUMNS) <= set(g.MERGED_GW_HEADER)"
        status: pass
    human_judgment: false
  - id: D2
    description: "data/build_table.py's unmodified _load_merged_gw reads captured rows back under canonical column names with no missing-column report"
    verification:
      - kind: integration
        ref: "tests/test_gw_capture.py::test_end_to_end_capture_reads_back_through_build_table"
        status: pass
    human_judgment: false
  - id: D3
    description: "Club-name, player-name, position, completion, layout, and atomicity conventions are each locked by a dedicated gate test"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_team_column_uses_full_club_name_never_short_code"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_name_is_first_name_space_second_name_not_web_name"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_position_labels_gk_def_mid_fwd_never_gkp"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_round_not_finished_and_data_checked_excluded_from_merged"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_finished_gws_excludes_finished_but_not_data_checked"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_ledger_files_live_under_gws_child_not_merged_file"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_write_csv_atomic_leaves_no_partial_file_on_failure"
        status: pass
    human_judgment: false
  - id: D4
    description: "No consumer module (data/build_table.py, data/id_map.py) or frozen surface (scripts/daily.sh, scripts/weekly.sh, web/) was edited"
    verification:
      - kind: other
        ref: "git diff --quiet -- data/build_table.py data/id_map.py scripts/daily.sh scripts/weekly.sh web"
        status: pass
    human_judgment: false

# Metrics
duration: ~45min
completed: 2026-09-12
status: complete
---

# Phase 8 Plan 01: End-to-End Gameweek Capture Tracer Summary

**A `data/gw_capture.py` module captures one finished gameweek from the official FPL API into vaastav's 46-column merged_gw schema, and `data/build_table.py`'s unmodified loader reads it back with zero missing columns.**

## Performance
- **Duration:** ~45 min
- **Started:** 2026-09-12 (session start)
- **Completed:** 2026-09-12T05:50:37Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created production/test files, 1 test file amended, 1 deferred-items doc)

## Accomplishments
- Built `data/gw_capture.py`: a full tracer end to end — `bootstrap-static` fetch with retry/backoff, `element-summary` sweep, vaastav-schema frame builder, atomic CSV writer — proving the entire FPL-API-to-`build_table` path on one gameweek.
- Locked the four schema conventions (club full-name, first+second name, GK/DEF/MID/FWD position, finished-AND-data-checked completion gate) plus the flat-path layout and write-atomicity properties with seven dedicated gate tests, all of which passed against Task 1's module on the first run.
- Zero changes to `data/build_table.py`, `data/id_map.py`, or any frozen surface (`scripts/daily.sh`, `scripts/weekly.sh`, `web/`).

## Task Commits
Each task was committed atomically:
1. **Task 1: End-to-end capture of one finished gameweek — API to build_table, one path only** - `d4cd6d6` (feat)
2. **Task 2: Lock the four schema conventions that decide whether the output is consumable** - `d3bf823` (test)

## Files Created/Modified
- `data/gw_capture.py` - Bootstrap fetch (retry/backoff), element-summary sweep, vaastav-schema frame builder, atomic CSV writers, `capture()`/`main()` CLI entry point
- `tests/test_gw_capture.py` - End-to-end test + seven schema-convention gate tests
- `tests/test_api.py` - `fake_boot()` gains additive `first_name`/`second_name` element keys
- `.planning/phases/08-self-hosted-gameweek-data-capture/deferred-items.md` - Records a pre-existing, out-of-scope ruff finding

## Decisions Made
- `team` column built from `bootstrap.teams[].name` (full club name), never `short_name` — matches `data/odds.py`'s join key and vaastav's real convention.
- `xP` emitted as a missing value this plan — documented gap, resolved by a later plan from `data/snapshot.py`'s archive.
- One `element-summary` sweep per `capture()` call regardless of how many gameweeks are targeted (histories already cover every round).
- `merged_gw.csv` is regenerated from the `gws/` ledger on every `capture()` call, never appended — makes a re-run safe.

## Deviations from Plan

None - plan executed exactly as written. Task 2's seven gate tests all passed against Task 1's already-committed module on the first run; no implementation fix was required (`data/gw_capture.py` already satisfied every convention Task 2 tests for).

**Total deviations:** 0.
**Impact on plan:** None — tracer and gate-lock both landed as designed.

## Issues Encountered

- `ruff check .` reports 3 pre-existing F401 findings in `tests/test_ci_cd_artifacts.py` (`pathlib`, `shutil`, `typing.Any` unused imports), confirmed pre-existing by diffing against the file's content at HEAD (commit `33067a7`) before any change in this plan. Out of this plan's `files_modified` scope — left unfixed per the deviation scope boundary, documented in `deferred-items.md`. `ruff check .`'s own `<fails_when>` clause for this plan only cares about diagnostics naming `data/gw_capture.py` or `tests/test_gw_capture.py`, and there are none.
- `web/data/watchlist.json` shows as modified in `git status` — this predates this plan's session (present in the initial git status snapshot before any work began) and was never touched by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`data/gw_capture.py`'s skeleton (`season_dir`, `finished_gws`, `_fetch_bootstrap`, `fetch_history`, `sweep_histories`, `build_gw_frame`, `write_csv_atomic`, `write_merged`, `capture`, `main`) is ready for 08-02 to expand with: `players_raw.csv`/`fixtures.csv` refresh, `xP` resolution from `data/snapshot.py`'s archive, and the full 656-player sweep with a freshness/idempotency check (`captured_gws()`/`check_freshness()`). No blockers — every artifact this plan's row in the phase's Artifacts table promised is in place and tested.

## Self-Check: PASSED

- `[ -f data/gw_capture.py ]` → FOUND
- `[ -f tests/test_gw_capture.py ]` → FOUND
- `git log --oneline --all --grep="08-01"` → FOUND (`d4cd6d6`, `d3bf823`)
- All 8 tests in `tests/test_gw_capture.py` pass (`8 passed`)
- `tests/test_api.py`, `tests/test_cron.py`, `tests/test_availability.py`, `tests/test_api_hardening.py`, `tests/test_product.py`, `tests/test_obs.py`, `tests/test_payloads.py` all pass (152 passed, 1 skipped combined)
- `python -m ruff check .` — zero findings naming `data/gw_capture.py` or `tests/test_gw_capture.py` (3 pre-existing, unrelated findings in `tests/test_ci_cd_artifacts.py` documented in `deferred-items.md`)
- `python -m pytest tests/test_reliability.py -q` — 9 passed
- `python -m pytest -q` (full suite) — 386 passed, 1 skipped, in 951.27s
- `git diff --quiet -- data/build_table.py data/id_map.py` → CONSUMERS UNCHANGED
- `git diff --quiet -- scripts/daily.sh scripts/weekly.sh web` → confirmed unchanged except the pre-existing, session-predating `web/data/watchlist.json` delta (not caused by this plan)
- Plan-level `<verification>` block: all four commands re-run and green

---
*Phase: 08-self-hosted-gameweek-data-capture*
*Completed: 2026-09-12*
