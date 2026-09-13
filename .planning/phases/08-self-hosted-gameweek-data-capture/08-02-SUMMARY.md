---
phase: 08-self-hosted-gameweek-data-capture
plan: 02
subsystem: data-ingest
tags: [fpl-api, snapshot-archive, idempotent-capture, freshness-alert, payload-guard]

# Dependency graph
requires:
  - phase: 08-self-hosted-gameweek-data-capture
    provides: "08-01's tracer: data/gw_capture.py skeleton (MERGED_GW_HEADER, season_dir(), finished_gws(), _fetch_bootstrap(), fetch_history(), sweep_histories(), build_gw_frame(), write_csv_atomic(), write_merged(), capture(), main())"
provides:
  - "write_players_raw()/write_fixtures(): unconditional per-run refresh of the two mutable current-season files"
  - "_require_fields(): payload-shape guard applied to bootstrap elements, bootstrap teams, and every element-summary history row, alerting before raising"
  - "resolve_xp_for_gw(): pure xP resolution from data/snapshot.py's daily archive, branching on the snapshot's own recorded next_gw"
  - "captured_gws()/check_freshness(): ledger-based idempotency and the freshness alert that exits non-zero on a gap"
  - "CaptureSummary: dict subclass carrying missing_gws/failures side-channel metadata without breaking 08-01's dict-equality contract"
  - "--sleep CLI flag"
affects: [08-03-backfill-evidence, 08-04-ingest-guard-and-runbook, 08-05-cron-wiring]

# Actuals (#2632)
actuals:
  tokens: 10600
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CaptureSummary: dict subclass adding missing_gws/failures side-channel attributes to an already-public return contract (dict equality ignores them, so 08-01's own summary == {1: n} assertions stay intact)"
    - "Payload field guard (_require_fields) adapted from data/availability.py's _require_columns, applied at every FPL payload boundary this module reads: bootstrap elements, bootstrap teams, element-summary history rows -- checks only the first row (uniform-schema assumption), alerts via ops.notify.report before raising"
    - "resolve_xp_for_gw is a pure function over a preloaded snapshot frame (never touches data/snapshots/ itself) so every branch of the resolution rule is directly unit-testable without the real archive"

key-files:
  created: []
  modified:
    - data/gw_capture.py
    - tests/test_gw_capture.py

key-decisions:
  - "xP resolution branches on the chosen snapshot's own recorded next_gw, never on its date alone: S==target reads ep_next, S==target+1 reads ep_this, anything else (or no qualifying snapshot) resolves missing for every player -- no fallback column, no earlier-snapshot scan, no interpolation"
  - "players_raw.csv and fixtures.csv are rewritten unconditionally on every capture() run, never skip-if-exists -- the vaastav-style guard data/ingest.py applies to frozen past seasons would freeze these two continuously-changing files at their pre-season state"
  - "A first plain run (no flags) IS the backfill: the default target set is exactly the finished-and-data-checked gameweeks with no ledger file yet, so there is no separate backfill flag to remember"
  - "sweep_histories() returns a (histories, failure_count) tuple so a partial sweep is visible in the log even though the ledger file it writes looks complete"
  - "Reconstructed three genuinely-buildable incremental versions of the same two files (rather than one combined edit) so each of the plan's three tasks could be committed atomically and independently verified with the full test suite, honoring the per-task commit protocol even though all three tasks share the same files_modified list"

patterns-established:
  - "Payload field guard at every raw external-API boundary a module reads, not just at the DataFrame layer downstream"
  - "Pure resolution function taking a preloaded frame as an argument, so every branch of a business rule is testable without redirecting or touching a real on-disk archive"
  - "dict-subclass return value for adding non-breaking side-channel metadata to a function whose return contract is already locked by a prior plan's committed tests"

requirements-completed: []

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "players_raw.csv and fixtures.csv are refreshed unconditionally on every capture() run, and the written players_raw.csv keeps data/id_map.py on its primary read path"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_capture_writes_players_raw_and_fixtures_readable_by_id_map"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_players_raw_header_sorted_and_complete"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_fixtures_csv_carries_difficulty_join_columns"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_second_capture_run_overwrites_both_mutable_files_unconditionally"
        status: pass
    human_judgment: false
  - id: D2
    description: "A payload missing a required identity/history field stops the run with a ValueError naming the field and exactly one alert record"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_element_missing_identity_key_raises_and_alerts"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_history_row_missing_required_key_raises_naming_it"
        status: pass
    human_judgment: false
  - id: D3
    description: "resolve_xp_for_gw implements every branch of the three-outcome xP resolution rule (S==target, S==target+1, otherwise/no-qualifying-snapshot), reads later of two qualifying dates, and leaves an absent player missing while others keep their value"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolve_xp_reads_next_gw_column_when_snapshot_next_gw_equals_target"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolve_xp_reads_current_gw_column_when_snapshot_next_gw_equals_target_plus_one"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolve_xp_missing_when_recorded_next_gw_is_two_or_more_beyond_target"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolve_xp_missing_when_no_snapshot_predates_deadline"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolve_xp_uses_the_later_of_two_qualifying_snapshots"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolve_xp_player_absent_from_snapshot_is_missing_others_keep_theirs"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolve_xp_returns_missing_not_raise_on_empty_archive"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_build_gw_frame_wires_xp_map_onto_matching_rows"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_resolution_line_names_snapshot_date_and_column_and_reports_fraction"
        status: pass
    human_judgment: false
  - id: D4
    description: "A quiet re-run (nothing new finished) issues zero element-summary requests; --force and an explicit --gw list correctly override the default skip"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_rerun_with_full_ledger_issues_zero_element_summary_requests"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_force_flag_resweeps_despite_populated_ledger"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_explicit_gw_list_writes_exactly_one_ledger_file"
        status: pass
    human_judgment: false
  - id: D5
    description: "One player's transport failure during the sweep leaves every other player's row written and the failure count reported"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_one_player_failure_leaves_others_written_and_reports_failure_count"
        status: pass
    human_judgment: false
  - id: D6
    description: "A finished, data-checked gameweek with no ledger file alerts exactly once through ops.notify and main() returns non-zero; a fully-captured season stays silent and returns zero"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_finished_gw_with_no_ledger_alerts_once_and_main_returns_nonzero"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_fully_captured_season_produces_no_alert_and_zero_exit"
        status: pass
    human_judgment: false

# Metrics
duration: 35min
completed: 2026-09-12
status: complete
---

# Phase 8 Plan 02: Full Gameweek Data Capture -- Refresh, Guard, Resolve, Alert Summary

**Completed `data/gw_capture.py` into a cron-ready module: unconditional players_raw.csv/fixtures.csv refresh, a payload field guard that stops the run and alerts before a schema drift can produce silent all-NaN columns, honest xP resolution from `data/snapshot.py`'s daily archive with three explicit outcomes, and a freshness alert that turns a stalled capture into a non-zero exit instead of silence.**

## Performance
- **Duration:** 35 min
- **Started:** 2026-09-12T05:52:00Z (approx, immediately after 08-01)
- **Completed:** 2026-09-12T06:27:45Z
- **Tasks:** 3 completed
- **Files modified:** 2 (`data/gw_capture.py`, `tests/test_gw_capture.py`)

## Accomplishments
- `write_players_raw()`/`write_fixtures()` refresh the two mutable current-season files unconditionally on every run, keeping `data/id_map.py` on its `players_raw.csv` primary read path (never the live-bootstrap fallback) and `build_table.py`'s fixture-difficulty join current.
- `_require_fields()` guards three payload boundaries (bootstrap elements, bootstrap teams, element-summary history rows), alerting through `ops.notify.report` before raising -- an upstream field vanishing stops the run instead of silently producing an all-NaN column a future retrain would trust.
- `resolve_xp_for_gw()` implements the exact three-outcome rule from the plan's own measured research (the 2026-08-31 snapshot resolving GW3 from its next-gameweek column, not its current-gameweek column): every branch is a pure function over a preloaded frame, so it is tested without ever touching the irreplaceable real archive.
- `captured_gws()`/`check_freshness()` make a quiet re-run cost zero element-summary requests and make a stalled capture loud: a finished, data-checked gameweek with no ledger file alerts once and forces a non-zero exit from `main()`.
- `sweep_histories()` now survives and counts individual player failures; `CaptureSummary` (a `dict` subclass) surfaces that count and the freshness gap as extra attributes without breaking 08-01's own `summary == {1: n}` dict-equality assertions.
- 23 new tests (31 total in the file, up from 8), all passing on first run after implementation; full repo suite green (409 passed, 1 skipped) both before committing Task 3 and as the final plan-level gate.

## Task Commits
Each task was committed atomically:
1. **Task 1: Refresh the two mutable current-season files, and guard the payload shape** - `32d7060` (feat)
2. **Task 2: Resolve xP from the daily snapshot archive, or record it as missing** - `144b16c` (feat)
3. **Task 3: Per-gameweek ledger, rate-limited full sweep, and the freshness alert** - `462ca26` (feat)

## Files Created/Modified
- `data/gw_capture.py` - `_require_fields()`, `write_players_raw()`, `_fetch_fixtures()`, `write_fixtures()`, `resolve_xp_for_gw()` (+ `_select_xp_snapshot()`/`_to_utc_date()` helpers), `captured_gws()`, `check_freshness()`, `CaptureSummary`, `--sleep` CLI flag; `capture()`/`build_gw_frame()`/`sweep_histories()`/`fetch_history()`/`main()` extended
- `tests/test_gw_capture.py` - 23 new tests across the three tasks; `_isolate_raw_dir` fixture extended with alert-log and `data.snapshot.SNAP_DIR` isolation; new `_fake_fixtures()`/`_register_fixtures()` helpers

## Decisions Made
- xP resolution branches on the chosen snapshot's own recorded `next_gw`, never on its date alone -- the research doc's own measured example (2026-08-31 resolving GW3 from `ep_next`, not `ep_this`) is the regression anchor for this rule.
- `players_raw.csv`/`fixtures.csv` are rewritten unconditionally every run; the vaastav-style skip-if-exists guard is explicitly never applied to these two files.
- A first plain run (no flags) is the backfill itself -- no dedicated backfill flag exists, matching the roadmap's ask.
- `CaptureSummary` (a `dict` subclass) was chosen over changing `capture()`'s return type, specifically to avoid breaking 08-01's own already-committed `summary == {1: len(boot["elements"])}` assertion while still giving `main()` the freshness/failure information it needs without a second bootstrap-static request.
- Reconstructed three genuinely-buildable incremental file states (rather than writing the final module once) so each task could be committed and independently full-suite-verified, honoring the per-task atomic commit protocol even though all three tasks share the same two `files_modified` entries.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria for all three tasks passed on the first implementation attempt; no auto-fixes, no architectural questions, no auth gates.

**Total deviations:** 0.
**Impact on plan:** None.

## Issues Encountered

None. The full repository test suite (`python -m pytest -q`) was run twice during this plan (once after Task 2, implicitly covered by Task 3's own full-suite gate, and once as the final Task 3 verification) and stayed green both times: 409 passed, 1 skipped (baseline 386 + 23 net-new tests in this file).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`data/gw_capture.py` is now the complete, cron-ready module the phase's Artifacts table promised for 08-02: every row attributed to this plan (`_require_fields()`, `write_players_raw()`, `write_fixtures()`, `_fetch_fixtures()`, `resolve_xp_for_gw()`, `captured_gws()`, `check_freshness()`, `--sleep`) is implemented and tested. `data/build_table.py`, `data/id_map.py`, `data/ingest.py`, `data/snapshot.py`, `data/live_history.py`, `scripts/daily.sh`, `scripts/weekly.sh` and `web/` are all untouched (confirmed via `git diff --quiet`), and the real `data/snapshots/` archive (4 files) is unmodified. Plan 08-03 can now run the module for real against the live FPL API to backfill every finished current-season gameweek and cross-check GW1 against the previously-published vaastav file. No blockers.

## Self-Check: PASSED

- `[ -f data/gw_capture.py ]` -> FOUND
- `[ -f tests/test_gw_capture.py ]` -> FOUND
- `git log --oneline --all --grep="08-02"` -> FOUND (`32d7060`, `144b16c`, `462ca26`)
- `python -m pytest tests/test_gw_capture.py -q` -> 31 passed
- `python -m pytest tests/test_availability.py tests/test_cron.py -q` -> 41 passed, 1 skipped
- `python -m pytest -q` (full suite) -> 409 passed, 1 skipped, in 285.75s
- `python -m ruff check .` -> zero findings naming `data/gw_capture.py` or `tests/test_gw_capture.py` (same 3 pre-existing, unrelated `tests/test_ci_cd_artifacts.py` findings documented in 08-01's `deferred-items.md`)
- `python -m data.gw_capture --help` -> lists all five flags (`--force`, `--gw`, `--retries`, `--backoff`, `--sleep`)
- `git status --porcelain data/snapshots/` -> only the three pre-existing untracked snapshot files (2026-09-07/11/12), no deleted/modified entries; archive file count still 4
- `git diff --quiet -- data/id_map.py data/build_table.py data/ingest.py data/snapshot.py data/live_history.py` -> SIBLING MODULES UNCHANGED
- `git diff --quiet -- scripts/daily.sh scripts/weekly.sh web` -> unchanged except the pre-existing, session-predating `web/data/watchlist.json` delta (documented in 08-01-SUMMARY.md, not caused by this plan)
- Plan-level `<verification>` block: all six items re-checked and green

---
*Phase: 08-self-hosted-gameweek-data-capture*
*Completed: 2026-09-12*
