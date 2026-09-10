---
phase: 10-xp-experiment-follow-ups
plan: 02
subsystem: predict
tags: [scoreboard, fpl-api, diagnostics, benchmarking, spearman, pandas]

# Dependency graph
requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: id_crosswalk (name resolution), predict/scoreboard.py's existing score_gw/running_summary scaffold, ops.jsonio read/write conventions
provides:
  - Top-100 overall-league consensus ownership fetcher (data/fpl_standings.py), aggregated to player_id counts with zero manager identity persisted
  - fplreview manual-capture slot with a validating reader (data/fplreview.py) and a committed six-section README documenting the ToS-driven manual workflow
  - Two independently-optional diagnostic columns wired into predict/scoreboard.py::score_gw/running_summary
affects: [predict/scoreboard.py, any future phase-10 tier work reading the scoreboard for a Spearman-vs-ep_next trigger check (D-02)]

# Actuals (#2632)
actuals:
  tokens: 8908
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-enrichment fetcher skeleton (kill switch + throttle + on-disk JSON cache + _require shape validation + build/load-or-None) mirrored from data/fotmob.py for data/fpl_standings.py"
    - "Zero-HTTP-client-import as the code-level ToS enforcement mechanism (data/fplreview.py never imports requests/httpx/urllib -- confirmed by verify grep)"
    - "Additive, independently-optional scoreboard blocks: each new diagnostic only adds keys when its source data exists; absence reproduces today's output byte-for-byte"

key-files:
  created:
    - data/fpl_standings.py
    - data/fplreview.py
    - data/external/fplreview/README.md
    - tests/test_scoreboard.py
  modified:
    - predict/scoreboard.py

key-decisions:
  - "OVERALL_LEAGUE_ID=314 kept as a keyword-default argument, never inlined into a URL f-string, so a future correction (if 314 turns out wrong) is a one-line change -- 10-RESEARCH.md Assumptions Log A3"
  - "No mae_consensus key: consensus ownership is a percentage, not points, so an MAE against actual points would be a meaningless number in a published trust artifact (web/data/scoreboard.json) -- only Spearman rank agreement is scored"
  - "fplreview join filtered to minutes > 0 (played-only), matching backtest/benchmark_external.py's own basis so the two benchmark numbers stay comparable"
  - "Removed a redundant, actively-breaking autouse test fixture (_no_benchmarks_by_default) that shadowed the real load_consensus/load_gw for every test in the module -- the pre-existing per-test tmp-dir isolation fixtures already guarantee absent-by-default naturally"

patterns-established:
  - "Diagnostic scoreboard benchmark = fetch/capture module with its own load_<x>(gw) -> DataFrame | None, joined into score_gw as an additive if-block, summarized in running_summary via an 'in df' conditional"

requirements-completed: [TODO-TOP100, TODO-FPLREVIEW]

coverage:
  - id: D1
    description: "Top-100 overall-league consensus ownership fetcher (data/fpl_standings.py) -- paginated FPL standings fetch, per-manager picks fetch with graceful 404 degradation, aggregation to player_id owner counts with zero manager identity persisted"
    requirement: "TODO-TOP100"
    verification:
      - kind: unit
        ref: "tests/test_scoreboard.py::test_consensus_ownership_counts_distinct_owners_never_double_counting -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_fetch_standings_stops_on_empty_page -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_fetch_entry_picks_one_unavailable_manager_does_not_kill_the_others -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_build_writes_parquet_and_load_consensus_returns_it -- pass"
        status: pass
      - kind: other
        ref: "python -m data.fpl_standings --gw 1 --force (real live FPL API run, 103s wall clock, 103 requests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "fplreview manual-capture slot: validating CSV reader (data/fplreview.py) with zero HTTP-client imports (the code-level ToS mitigation), and a six-section committed README documenting the weekly manual workflow"
    requirement: "TODO-FPLREVIEW"
    verification:
      - kind: unit
        ref: "tests/test_scoreboard.py::test_validate_raises_naming_all_missing_columns_at_once -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_validate_raises_when_proj_pts_entirely_non_numeric -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_load_gw_resolves_names_and_drops_unresolved -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_load_gw_duplicate_player_names_raises -- pass"
        status: pass
      - kind: other
        ref: "grep -cE http-client-import data/fplreview.py == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both benchmarks scored in predict/scoreboard.py::score_gw/running_summary as independently-optional additive blocks; both-absent entry is byte-identical to today's key set"
    verification:
      - kind: unit
        ref: "tests/test_scoreboard.py::test_score_gw_both_absent_reproduces_todays_key_set -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_score_gw_adds_consensus_keys_when_present -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_score_gw_adds_fplreview_keys_on_played_rows_only -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_running_summary_averages_each_new_key_only_over_carrying_entries -- pass"
        status: pass
      - kind: unit
        ref: "tests/test_scoreboard.py::test_rescore_with_force_gains_new_keys_without_losing_existing -- pass"
        status: pass
      - kind: integration
        ref: "tests/test_product.py -- pass (export-contract regression, product surface untouched)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 02: Tier-3 Diagnostic Benchmarks (Top-100 Consensus + fplreview) Summary

**Two near-zero-cost diagnostic benchmark columns landed in `predict/scoreboard.py`: top-100 overall-league consensus ownership (fetched live from the FPL API, zero manager identity persisted) and fplreview's ToS-restricted free-model weekly capture, both independently optional and never touching the weekly product surface.**

## Performance

- **Duration:** 25 min (this session's verification/completion pass; Tasks 1-2 code was already committed from a prior interrupted session)
- **Started:** 2026-09-10T11:35:00Z
- **Completed:** 2026-09-10T12:00:58Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `data/fpl_standings.py`: paginated FPL top-100 standings fetch, per-manager picks fetch that degrades gracefully (returns `[]`, never raises) on a single unavailable manager, `consensus_ownership()` aggregation to `player_id`/`n_owners`/`consensus_pct`/`consensus_rank` with zero manager identity ever persisted, committed-parquet caching via `build()`/`load_consensus()`
- `data/fplreview.py`: a validating reader for the manual weekly capture with **zero HTTP-client imports** (the code-level ToS mitigation, verify-enforced), naming every missing required column at once, rejecting an all-non-numeric projection column, and raising on a within-gameweek duplicate `player_code`
- `data/external/fplreview/README.md`: the six-section committed-snapshot doc (Source/Attribution/Regeneration/Reduction applied/PII spot-check/ToS and redistribution posture) documenting the exact manual weekly workflow and filename contract
- `predict/scoreboard.py`: two additive, independently-optional blocks in `score_gw` (`n_consensus`/`spearman_consensus`/`spearman_consensus_vs_model`; `n_fplreview`/`mae_fplreview`/`spearman_fplreview`) plus matching conditionals in `running_summary`; both-absent output is byte-identical to today's
- Real live run confirmed the `OVERALL_LEAGUE_ID = 314` assumption (10-RESEARCH.md A3): `python -m data.fpl_standings --gw 1 --force` fetched 100 managers' standings + picks in 103 requests / 103s wall clock, printing the required top-3 spot-check:
  1. @Maunarokclothes . (WILDCARDGW4) — 307 total pts
  2. Jasper Leveillee (Sonic Dynamos Albion) — 306 total pts
  3. Paul Walters (Paul's Team) — 305 total pts
  137 distinct players owned across the top 100 managers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Top-100 consensus ownership fetcher** - `534470a` (feat) — committed in a prior session
2. **Task 2: fplreview manual-capture slot with a validating reader** - `3b40891` (feat) — committed in a prior session
3. **Task 3: Score both benchmarks in the post-gameweek scoreboard** - `e3bdfb7` (feat) — committed this session, includes the Rule 1 test-fixture fix

**Plan metadata:** (this commit)

_Note: Tasks 1 and 2's implementation and commits were already present in the working tree at the start of this session (from a prior interrupted executor run that never reached a SUMMARY). This session verified all three tasks' acceptance criteria against the actual code, completed and committed Task 3 (which was implemented but uncommitted), fixed a test bug discovered during verification, ran a real live `--gw 1` standings fetch to fulfil the plan's own required evidence, and closed out the plan._

## Files Created/Modified
- `data/fpl_standings.py` - top-100 consensus ownership fetcher (Task 1)
- `data/fplreview.py` - fplreview manual-capture validating reader, zero HTTP-client imports (Task 2)
- `data/external/fplreview/README.md` - six-section committed-snapshot doc for the manual weekly capture (Task 2)
- `predict/scoreboard.py` - two additive diagnostic blocks in `score_gw`/`running_summary` (Task 3)
- `tests/test_scoreboard.py` - 23 tests across all three tasks; the first dedicated test file `predict/scoreboard.py` has ever had

## Decisions Made
- `OVERALL_LEAGUE_ID = 314` kept as a keyword-default argument (never inlined into a URL f-string) so a future correction, if the community-documented id ever proves wrong, is a one-line change — confirmed correct this session by the real spot-check run above
- No `mae_consensus` key: consensus ownership is a percentage, not points; an MAE against actual points would be a meaningless number in a published trust artifact
- fplreview join filtered to `minutes > 0` (played-only), matching `backtest/benchmark_external.py`'s own basis so the two diagnostic numbers stay comparable to each other and to the existing `ep_next` benchmark

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed a test fixture that shadowed the functions it was meant to test**
- **Found during:** Task 3 verification (running `pytest tests/test_scoreboard.py` for the first time this session)
- **Issue:** `tests/test_scoreboard.py` had a module-wide `autouse=True` fixture, `_no_benchmarks_by_default`, added while wiring Task 3's scoreboard tests. Because it was autouse at module scope (not scoped to the scoreboard test section), it monkeypatched `sb.data.fpl_standings.load_consensus` and `sb.data.fplreview.load_gw` to always return `None` for **every** test in the file — including the Task 1/2 tests that call those exact functions directly to prove they work (`test_build_writes_parquet_and_load_consensus_returns_it`, `test_load_gw_resolves_names_and_drops_unresolved`, `test_load_gw_duplicate_player_names_raises`, `test_load_gw_lowercases_and_strips_header_whitespace`). Since `sb.data.fpl_standings` and `sb.data.fplreview` are the exact same module objects imported directly in the test file (`import data.fpl_standings as standings`, `import data.fplreview as fplreview`), the monkeypatch replaced the real implementation module-wide, not just within `predict.scoreboard`'s own namespace.
- **Fix:** Removed the fixture entirely. The pre-existing per-test tmp-dir isolation fixtures (`_isolate_standings_cache`, `_isolate_fplreview_dir`) already guarantee both loaders return `None` naturally when no consensus parquet/capture CSV was written for a given gameweek in that test's isolated tmp directory — the extra fixture was redundant even where it didn't actively break something.
- **Files modified:** `tests/test_scoreboard.py`
- **Verification:** `pytest tests/test_scoreboard.py -q` went from 4 failed/19 passed to 23/23 passed
- **Committed in:** `e3bdfb7` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correctness fix to the test suite itself; no production code or scope change. All 23 tests in the plan's own test file now genuinely exercise the code paths they claim to.

## Issues Encountered
None beyond the deviation above.

## User Setup Required

None - no external service configuration required this session (the plan's `user_setup` entry documents the **ongoing weekly** manual fplreview capture workflow, which is now fully documented in `data/external/fplreview/README.md` and ready to use starting this gameweek; it is not a one-time setup step this plan itself performs).

## Next Phase Readiness
- Both Tier-3 diagnostic benchmarks are live and will accumulate automatically: the top-100 consensus column scores on every `predict.scoreboard` run once a gameweek finishes (no further action needed), and the fplreview column will score for any gameweek where the user completes the weekly manual capture before the deadline (per D-01's own rationale: a missed gameweek is data permanently lost, so this capability existing now — rather than after the rest of Phase 10 — was the entire point of sequencing Tier 3 first).
- Repo-wide `pytest` (269 passed, 1 skipped), `ruff check .` (clean), and `tests/test_product.py` (export-contract regression) all confirm the weekly product surface (`predict/live.py`, `predict/export.py`) is completely untouched by this plan.
- Ready for the next Phase 10 plan (Tier 1: availability flags / Transfermarkt injury history).

## Self-Check: PASSED

All key files present on disk (`data/fpl_standings.py`, `data/fplreview.py`, `data/external/fplreview/README.md`, `tests/test_scoreboard.py`, `predict/scoreboard.py`). All three task commits (`534470a`, `3b40891`, `e3bdfb7`) confirmed present in `git log`. All plan-level `<verification>` commands re-run and passing: `pytest tests/test_scoreboard.py -q` (23 passed), repo-wide `pytest -q` (269 passed, 1 skipped), `ruff check .` (clean), `grep -c "requests" data/fplreview.py` (0), real `python -m data.fpl_standings --gw 1 --force` run completed with top-3 recorded above, `tests/test_product.py` passing (export contract unchanged).

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*
