---
phase: 08-self-hosted-gameweek-data-capture
plan: 04
subsystem: data-ingest
tags: [fpl-api, vaastav-demotion, current-season-guard, cross-check, runbook]

# Dependency graph
requires:
  - phase: 08-self-hosted-gameweek-data-capture
    provides: "08-01/08-02/08-03's complete, real-exercised data/gw_capture.py -- the module this plan gives undisputed ownership of the current season's three files to"
provides:
  - "data/ingest.py's current-season guard: fetch_vaastav_season declines all three current-season downloads under any flag, including --force"
  - "A cross_check=True escape hatch on fetch_vaastav_season that fetches vaastav's published current-season copy to a distinguishable .vaastav-crosscheck filename, never over the captured file"
  - "A season-level WARNING when a past season's files come back absent from vaastav, above the routine per-file MISS line"
  - "docs/runbooks/gameweek-data-capture.md: the operator runbook for provenance, running the module, the previous source's remaining role, measured gaps, the freshness alert, and the schema-change guard"
affects: [08-05-cron-wiring, any-future-plan-touching-data/ingest.py-or-data/gw_capture.py]

# Actuals (#2632)
actuals:
  tokens: 6200
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Current-season download guard keyed on config.CURRENT_SEASON inside fetch_vaastav_season itself, not in the CLI layer above it -- any future direct caller inherits the guard, not only python -m data.ingest"
    - "Distinguishable-filename escape hatch (.vaastav-crosscheck suffix, same directory) for fetching an independent copy of data a module already owns, without ever risking an overwrite of the owned file"
    - "Season-level [ingest]-tagged WARNING for an absent upstream file, layered above the existing per-file MISS line -- matches the codebase's [price]/[odds] module-tagged warning convention"

key-files:
  created:
    - docs/runbooks/gameweek-data-capture.md
  modified:
    - data/ingest.py
    - tests/test_gw_capture.py

key-decisions:
  - "The guard lives inside fetch_vaastav_season itself, keyed on config.CURRENT_SEASON, and holds regardless of the --force flag -- force's whole purpose (refresh an immutable past season) never applies to the current season, so there is no flag combination that reaches the three owned paths"
  - "cross_check=True writes to a `<stem>.vaastav-crosscheck<suffix>` filename in the same season directory rather than a separate directory or session-scratch path, making the cross-check output trivially discoverable next to the file it verifies -- and formalizing the check 08-03 hand-rolled outside the repository"
  - "The missing-past-season warning is season-level (one line naming every absent file for that season), layered above the existing per-file MISS line rather than replacing it -- the per-file line stays useful for isolating which of the three files vanished"
  - "The runbook is one document (provenance -> run -> previous-source role -> gaps -> alerting -> schema-change guard, in that order) rather than split across several, matching docs/decisions/pitch-kit-sourcing.md's operational, non-architectural tone and length"

patterns-established:
  - "A module-owned set of file paths gets its guard inside the function that could otherwise write them, not bolted on at the CLI argument-parsing layer, so the invariant holds for every caller"

requirements-completed: []

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "fetch_vaastav_season declines all three current-season downloads unconditionally, under --force too, and leaves pre-existing captured files byte-identical"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_current_season_call_issues_zero_http_requests_with_or_without_force"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_current_season_files_byte_identical_after_guarded_call"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_fetch_vaastav_season_signature_begins_with_season_and_force"
        status: pass
      - kind: other
        ref: "python -c ... reads merged_gw.csv back after the whole suite ran -- rounds=[1,2,3], rows=1890, matching 08-BACKFILL-EVIDENCE.md, proving the guard held against the real captured file throughout this plan"
        status: pass
    human_judgment: false
  - id: D2
    description: "A past season's call is unaffected (still downloads all three files)"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_past_season_call_still_downloads_all_three"
        status: pass
    human_judgment: false
  - id: D3
    description: "The cross_check escape hatch writes to a distinguishable filename and leaves the captured file byte-identical"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_cross_check_escape_hatch_writes_distinguishable_filename_leaves_captured_untouched"
        status: pass
    human_judgment: false
  - id: D4
    description: "A past season whose files come back absent produces a season-level warning naming it"
    verification:
      - kind: unit
        ref: "tests/test_gw_capture.py::test_past_season_absent_files_produce_warning_naming_the_season"
        status: pass
    human_judgment: false
  - id: D5
    description: "fetch_fpl_live and main() are unaffected by the guard; the module docstring states the ownership split"
    verification:
      - kind: other
        ref: "git diff shows zero lines changed inside fetch_fpl_live; python -c confirms predict.live.fetch_fpl_live is data.ingest.fetch_fpl_live and its signature is unchanged (single keyword-only force=False)"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_ingest_module_docstring_states_the_ownership_split"
        status: pass
    human_judgment: false
  - id: D6
    description: "docs/runbooks/gameweek-data-capture.md exists, agrees with the module's real --help flag set, and quotes 08-BACKFILL-EVIDENCE.md's measured numbers verbatim"
    verification:
      - kind: other
        ref: "python -m data.gw_capture --help flag set (--force, --gw, --retries, --backoff, --sleep) matches every flag documented in the runbook exactly; grep -c data.gw_capture docs/runbooks/gameweek-data-capture.md returns 12"
        status: pass
    human_judgment: false

# Metrics
duration: 28min
completed: 2026-09-12
status: complete
---

# Phase 8 Plan 04: Current-Season Ingestion Guard and Operator Runbook Summary

**Closed the ownership boundary Phase 8 opened: `data/ingest.py` now refuses under any flag to touch the three files `data/gw_capture.py` owns, gained a formal cross-check escape hatch, and a runbook records the whole arrangement for the next person who has to operate it under pressure.**

## Performance
- **Duration:** 28 min
- **Started:** 2026-09-12T07:24:00Z (approx, immediately after 08-03)
- **Completed:** 2026-09-12T07:52:10Z
- **Tasks:** 2 completed
- **Files modified:** 3 (1 created: `docs/runbooks/gameweek-data-capture.md`; 2 modified: `data/ingest.py`, `tests/test_gw_capture.py`)

## Accomplishments
- `fetch_vaastav_season` now declines all three current-season downloads unconditionally, including under `--force` -- the exact regression this task exists to prevent (the re-download flag replacing a full three-gameweek capture with vaastav's stalled single gameweek) is now structurally impossible, not just avoided by convention.
- A `cross_check=True` keyword escape hatch fetches vaastav's published current-season copy to a `.vaastav-crosscheck`-suffixed filename in the same directory, formalizing the check plan 08-03 hand-rolled outside the repository -- the next cross-check does not have to hand-roll a fetch again.
- A past season whose files come back absent from vaastav now prints a season-level `[ingest] WARNING` naming the season and the vanished files, above the existing routine per-file `MISS` line -- a source silently dropping a season (the failure this whole phase responds to) is now visible the day it happens.
- `fetch_fpl_live` and `main()` are byte-identical to before this plan (confirmed via `git diff` showing zero lines changed inside `fetch_fpl_live`, and a live signature/identity check against `predict.live`'s direct import).
- `docs/runbooks/gameweek-data-capture.md` records the provenance split, how to run the module (including that a plain first run *is* the backfill), what vaastav's copy is still for, the permanent GW1/GW2 `xP` null gap and the absent-upstream-source odds gap (both quoted verbatim from `08-BACKFILL-EVIDENCE.md`), the freshness alert's exact record shape and diagnostic order, and the schema-change guard's fix path -- verified word-for-word against the module's real `--help` output.
- 7 new regression tests added to `tests/test_gw_capture.py` (40 total, up from 33); full repository suite green at 419 passed, 1 skipped (up from the 08-03 baseline of 412 passed, 1 skipped).

## Task Commits
Each task was committed atomically:
1. **Task 1: Guard the current season's three captured files against the ingestion module** - `c2a53ca` (feat)
2. **Task 2: Write the operator runbook for the new data provenance** - `7519100` (docs)

## Files Created/Modified
- `data/ingest.py` - `fetch_vaastav_season` gains the current-season guard (holds under `--force`), a `cross_check` keyword escape hatch, `_crosscheck_path()` helper, a season-level absent-file `WARNING` for past seasons, and an updated module docstring stating the ownership split; `fetch_fpl_live`/`main()` untouched
- `tests/test_gw_capture.py` - 7 new tests: zero-HTTP-requests guard (plain + `--force`), byte-identical captured files, past-season download still works, cross-check hatch writes a distinguishable filename and leaves the captured file untouched, absent-past-season-files warning, signature ordering, docstring content
- `docs/runbooks/gameweek-data-capture.md` - new operator runbook (provenance, how to run, previous-source role, known gaps, freshness alert, schema-change guard)

## Decisions Made
- The guard lives inside `fetch_vaastav_season` itself, keyed on `config.CURRENT_SEASON`, rather than in the CLI argument-parsing layer -- any future direct caller of the function inherits the guard, not only `python -m data.ingest`.
- `cross_check=True` writes to a `<stem>.vaastav-crosscheck<suffix>` filename in the same season directory (never a separate directory or a session-scratch path outside the repo, as 08-03 used) -- the cross-check output is now trivially discoverable next to the file it verifies.
- The missing-past-season warning is layered above the existing per-file `MISS` line rather than replacing it, so isolating which of the three files specifically vanished still works from the per-file line.
- The runbook is a single document, ordered provenance -> how-to-run -> previous-source role -> known gaps -> freshness alert -> schema-change guard, matching `docs/decisions/pitch-kit-sourcing.md`'s operational, non-architectural tone and length rather than a longer specification-style document.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria for both tasks passed on the first implementation attempt after two isolated-test-environment fixes (below), no architectural questions, no auth gates.

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Test isolation fixture patched `config.RAW_DIR` outside `config.ROOT`, breaking `_download`'s existing `dest.relative_to(config.ROOT)` print**
- **Found during:** Task 1, first run of the four new tests that call `data.ingest.fetch_vaastav_season` (the SKIP print I added, and the pre-existing `_download` "saved" print, both compute `dest.relative_to(config.ROOT)`)
- **Issue:** `tests/test_gw_capture.py`'s shared `_isolate_raw_dir` autouse fixture (written in 08-01/08-02 for `data.gw_capture`, which never calls `_download`) only patches `config.RAW_DIR` to a `tmp_path` outside the repository, never `config.ROOT`. `data.ingest._download`'s print statement assumes `RAW_DIR` is always a descendant of `ROOT` (true in production, where `RAW_DIR = ROOT / "data" / "raw"`), so it raised `ValueError` the moment any of the four new `data.ingest` tests ran under the isolated fixture.
- **Fix:** The four affected tests additionally monkeypatch `config.ROOT` to the same `tmp_path`, keeping the isolation guarantee (no test ever touches the real `data/raw/2026-27/` tree) while satisfying `_download`'s existing path-relativity assumption. No production code changed for this fix.
- **Files modified:** `tests/test_gw_capture.py`
- **Verification:** All four tests pass; full `tests/test_gw_capture.py` suite green (40 passed).
- **Committed in:** `c2a53ca` (part of the task's single commit; discovered and fixed before the first commit, not a follow-up)

**2. [Rule 1 - Bug] Test asserted `responses.calls == []`, which `responses`' `CallList` never equals even when empty**
- **Found during:** Task 1, `test_current_season_call_issues_zero_http_requests_with_or_without_force`
- **Issue:** `responses.calls` is a `CallList` object, not a plain `list`; `CallList() == []` evaluates `False` regardless of length, so the test's own assertion could never pass even with the guard correctly issuing zero requests.
- **Fix:** Asserted `len(responses.calls) == 0` instead.
- **Files modified:** `tests/test_gw_capture.py`
- **Verification:** Test passes; confirmed independently via a standalone script showing `len(responses.calls) == 0` while `responses.calls == []` is `False` even inside an empty `@responses.activate` block.
- **Committed in:** `c2a53ca`

---
**Total deviations:** 2 auto-fixed (1 Rule 3 -- test-only isolation gap in a pre-existing print statement, 1 Rule 1 -- a test's own assertion bug against a third-party library's equality semantics). Neither touched `data/gw_capture.py`, `scripts/`, or `web/`; both fixes are confined to the new tests this plan added.
**Impact on plan:** None on production behavior -- both deviations were discovered and fixed while writing this plan's own new tests, before either was committed.

## Issues Encountered

- `web/data/watchlist.json` (modified) plus `web/data/history/gw4.json` and `web/data/scoreboard.json` (untracked) continue to show in `git status` -- confirmed present before this plan's session began and already documented as pre-existing in 08-01/08-02/08-03-SUMMARY.md. No file under `web/` or `scripts/` was created, modified, or deleted by any command this plan ran; `git status --porcelain web/ scripts/` after both commits shows exactly these three pre-existing entries and nothing new.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The ownership boundary the phase's tracer (08-01 Task 1) opened is now closed in code: `data.ingest` cannot write over `data.gw_capture`'s three current-season files under any flag, a vanishing past season is now loud, and the cross-check path lives in the module instead of being hand-rolled per use. The operator runbook exists and is verified word-for-word against the module's real CLI surface and the real measured gaps. Plan 08-05 (cron wiring into `scripts/daily.sh`/`scripts/weekly.sh`, gated on Phase 7's cutover per the milestone invariant) can proceed with a fully guarded, fully documented capture module. No blockers.

## Self-Check: PASSED

- `[ -f data/ingest.py ]` -> FOUND
- `[ -f tests/test_gw_capture.py ]` -> FOUND
- `[ -f docs/runbooks/gameweek-data-capture.md ]` -> FOUND
- `git log --oneline --all --grep="08-04"` -> not used as the grep key (commits use `feat(08-04)`/`docs(08-04)` scope prefixes); confirmed instead via `git log --oneline -3`: `7519100 docs(08-04)...`, `c2a53ca feat(08-04)...`
- `python -m pytest tests/test_gw_capture.py -q` -> 40 passed
- `python -m pytest -q` (full suite) -> 419 passed, 1 skipped, in 275.24s
- `python -m ruff check .` -> zero findings naming `data/ingest.py` or `tests/test_gw_capture.py` (same 3 pre-existing, unrelated `tests/test_ci_cd_artifacts.py` findings documented in 08-01's `deferred-items.md`)
- `python -c "... predict.live.fetch_fpl_live is data.ingest.fetch_fpl_live ..."` -> `live_import_ok True`, `live_params [('force', 'KEYWORD_ONLY', False)]`, `vaastav_params ['season', 'force', 'cross_check']`
- `python -c "... merged_gw.csv rounds/rows ..."` -> `rounds [1, 2, 3] rows 1890` -- unchanged from 08-03's captured evidence, proving the guard held
- `python -m data.gw_capture --help` -> flag set (`--force`, `--gw`, `--retries`, `--backoff`, `--sleep`) matches the runbook exactly
- `grep -c "data.gw_capture" docs/runbooks/gameweek-data-capture.md` -> 12
- `git status --porcelain web/ scripts/` -> only the three pre-existing, session-predating entries (documented above and in 08-01/08-02/08-03-SUMMARY.md), no new modification
- Plan-level `<verification>` block: all six items re-checked and green

---
*Phase: 08-self-hosted-gameweek-data-capture*
*Completed: 2026-09-12*
