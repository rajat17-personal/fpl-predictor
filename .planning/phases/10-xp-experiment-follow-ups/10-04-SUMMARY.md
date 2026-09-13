---
phase: 10-xp-experiment-follow-ups
plan: 04
subsystem: data-pipeline
tags: [availability, leakage-safety, feature-engineering, xp-model, openfpl]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "data/availability.py's provider registry, gw_deadlines(),
      resolve_as_of() as-of-deadline resolver, the availability_flags
      experiment gate, and the single av_chance_pct tracer column (10-01)"
provides:
  - "config.AVAILABILITY_COLS grown from one to eight columns: av_chance_pct,
    av_status_a/d/i/s/u (one-hot), av_days_since_news, av_snapshot_age_days"
  - "data/availability.py::encode_availability -- a pure derivation on top
    of resolve_as_of's leakage-safe output, wired into build() between
    resolve_as_of and the parquet write"
  - "data/availability.py::report / --report CLI flag -- read-only
    per-season/per-source coverage + snapshot-staleness reporting, written
    to data/processed/experiments/availability_coverage.json"
  - "_STATUS_ALIASES = {'n': 'u'} -- a real FPL status code found in vendored
    data, normalised consistent with predict/live.py:130's existing
    injured/suspended/unavailable/ineligible grouping"
affects: [10-06, 10-08, 10-16]

# Actuals (#2632)
actuals:
  tokens: 7500
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "encode_availability as a PURE function of resolve_as_of's output --
      every derived column traces to a row the resolver already admitted,
      so the encoding layer adds no new time-travel surface of its own."
    - "Status-code aliasing (_STATUS_ALIASES) as the correct response to a
      real-world code outside a plan's assumed closed set: normalise at the
      encoding boundary rather than growing the one-hot family, keeping
      config.AVAILABILITY_COLS's column count a closed, testable contract."
    - "On-disk-only provenance column ('source' in availability.parquet,
      written by build() after encode_availability returns) -- carries
      reporting-only metadata without it ever being eligible to reach
      features.parquet, since attach()'s merge selects strictly from
      config.AVAILABILITY_COLS."

key-files:
  created: []
  modified:
    - config.py
    - data/availability.py
    - features/engineer.py
    - tests/test_availability.py

key-decisions:
  - "'n' FPL status code (found in real fpl_core_insights vendored data --
    Nkunku/N.Jackson/Isak/Wissa, all 2025-26 mid-transfer-window players)
    normalised to 'u' via _STATUS_ALIASES rather than added as a sixth
    one-hot column -- preserves the plan's literal eight-column
    config.AVAILABILITY_COLS contract and matches predict/live.py:130's
    existing precedent of grouping i/s/u/n as functionally unavailable. Any
    OTHER unrecognised code still raises ValueError."
  - "resolve_as_of's two-condition selection/dedup logic is unchanged from
    plan 10-01; it was extended with a pass-through addition
    (latest['deadline_ts'] = row['deadline_ts']) plus optional
    news_added/chance_of_playing_this_round carry-through in
    load_sources()/the two provider functions, so encode_availability has
    the per-row context it needs without altering which row wins."
  - "'source' kept on availability.parquet (on-disk only, added in build()
    AFTER encode_availability returns) so --report can break down coverage
    per provider -- never part of config.AVAILABILITY_COLS, so attach()'s
    column-restricted merge keeps it out of features.parquet."

patterns-established:
  - "Whole-family NaN via attach()'s left merge is proven correct, but a
    PRESENT resolved row can still have independently-sparse individual
    fields (av_chance_pct null when chance_of_playing_next_round wasn't
    published; av_days_since_news null when news_added wasn't captured) --
    this is legitimate per-field sparsity, not the partial-fill bug
    T-10-04-02 guards against. The five av_status_* columns plus
    av_snapshot_age_days are always jointly present or jointly absent
    (verified: real features.parquet has non-null counts of exactly 0
    (absent), 6, or 7 -- never the full 8, since av_days_since_news is
    presently all-NaN pending 10-06's fuller news_added capture)."

requirements-completed: [TODO-AVAIL-FLAGS]

coverage:
  - id: D1
    description: "config.AVAILABILITY_COLS grown to the full eight-column
      OpenFPL-style family (status one-hot, chance%, news recency,
      snapshot staleness), encoded by data/availability.py::encode_availability
      as a pure derivation over resolve_as_of's output, wired into build()"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: integration
        ref: "python -m data.availability --force (real 2025-26 GW1-3 fpl_core_insights probe)"
        status: pass
      - kind: integration
        ref: "python -m data.build_table && python -m features.engineer (all 8 av_ columns reach features.parquet raw, zero rolled variants)"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_status_one_hot_covers_every_fpl_code"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_snapshot_age_days_is_deadline_minus_snapshot_ts"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_unknown_status_code_raises_not_silently_dropped"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_news_added_postdating_deadline_raises_naming_the_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "Whole-family NaN fallback: a player-gameweek absent from
      the resolver's output yields NaN across all eight columns together,
      never a partial fill; the availability_flags gate off drops all
      eight and reproduces the pre-phase-10 feature set exactly"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: unit
        ref: "tests/test_availability.py::test_whole_family_is_nan_when_no_snapshot_qualifies"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_availability_family_present_and_not_rolled_in_features"
        status: pass
      - kind: integration
        ref: "apply_experiment_feature_gating: flag off drops all 8 av_ columns, flag on keeps all 8 (verified against real load_features())"
        status: pass
      - kind: unit
        ref: "tests/test_leakage.py::test_availability_features_are_raw_context_not_rolled"
        status: pass
    human_judgment: false
  - id: D3
    description: "Read-only per-season/per-source coverage + snapshot-staleness
      report (data.availability --report), machine-readable via
      availability_coverage.json, provably non-mutating"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: integration
        ref: "python -m data.availability --report (real data: prints per-source and per-season lines, WARNING for sub-50% seasons)"
        status: pass
      - kind: other
        ref: "sha256(availability.parquet) unchanged across a --report run"
        status: pass
      - kind: other
        ref: "data/processed/experiments/availability_coverage.json contains per_season/per_source top-level keys"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 04: Availability Feature Encoding + Coverage Report Summary

**Grew `config.AVAILABILITY_COLS` from one probe column (`av_chance_pct`) to the full eight-column OpenFPL-style family (status one-hot + chance% + news recency + snapshot staleness), all derived as a pure function of the plan 10-01 resolver's already leakage-safe output, plus a read-only per-season/per-source coverage report.**

## Performance

- **Duration:** 30 min
- **Tasks:** 3
- **Files modified:** 4 (config.py, data/availability.py, features/engineer.py, tests/test_availability.py)

## Accomplishments

- `data/availability.py::encode_availability(resolved)` derives exactly the eight `config.AVAILABILITY_COLS` columns (`av_chance_pct`, `av_status_a/d/i/s/u`, `av_days_since_news`, `av_snapshot_age_days`) from `resolve_as_of`'s output. A status one-hot validates against a closed five-code set (`a/d/i/s/u`) and raises `ValueError` naming any genuinely unrecognised code; `av_days_since_news` raises `AssertionError` if a `news_added` value postdates the gw deadline (an escape hatch for T-10-01-02). `resolve_as_of`'s own two-condition selection/dedup logic is unchanged from plan 10-01 -- extended only with a pass-through (`deadline_ts`, and optional `news_added`/`chance_of_playing_this_round` when a source supplies them) so the encoding layer has the context it needs.
- **Real-data discovery:** the vendored `fpl_core_insights` probe data (2025-26 GW2/GW3) carries a genuine FPL status code, `'n'` ("ineligible" -- found on Nkunku, N.Jackson, Isak, and Wissa, all mid-2025-summer-transfer-window players with `chance_of_playing_next_round == 0.0`), outside the plan's assumed five-code closed set. `predict/live.py:130` already groups `'n'` alongside `i/s/u` as functionally unavailable; `_STATUS_ALIASES = {"n": "u"}` applies that same precedent at the encoding boundary rather than growing the one-hot family to six columns, preserving `config.AVAILABILITY_COLS`'s exact eight-name contract.
- `features/engineer.py`'s `CONTEXT_COLS` already referenced `config.AVAILABILITY_COLS` (from 10-01); no hardcoded `av_` literal existed anywhere in the file. Added a `fillna(0)`-prohibition comment: the `av_status_*` one-hot's zeros are only meaningful alongside a non-null `av_snapshot_age_days`, since a `fillna(0)` on a genuinely missing player-gameweek would be indistinguishable from "available and definitely not injured."
- Re-ran `data.build_table` -> `features.engineer` end to end so the seven new columns actually reach `player_gw.parquet`/`features.parquet` (they previously carried only the tracer's `av_chance_pct`). `features.parquet` now has 168 columns (up from 161); real coverage measured: **2025-26 season coverage 92.2%** (27,045/29,338 rows) for `av_chance_pct`, with all other (pre-2025-26) seasons at 0.0% (no historical availability source exists yet -- expected, matches 10-01's own finding). Per-source: `fpl_core_insights` -- `n=28,083`, `chance_pct_non_null=98.0%`, `av_snapshot_age_days` median **124.7 days**, p95 **256.98 days** (a direct consequence of only 3 probed gameweeks carried forward as "last known" across a 37-gameweek season -- 10-06's full vendoring will close this).
- `data/availability.py --report` (new): read-only per-`(season, source)` and per-season coverage/staleness reporting from the existing `availability.parquet` cache -- never rebuilds it, proven by a sha256 round-trip check. Writes `data/processed/experiments/availability_coverage.json` (`per_season`/`per_source` keys) for plan 10-08 to cite. Sub-50%-coverage seasons print a `WARNING ... below 50%` line, mirroring `backtest/benchmark_external.py::score`'s own precedent.

## Task Commits

Each task was committed atomically:

1. **Task 1: Encode the OpenFPL availability feature set** - `d149c5d` (feat)
   - Follow-up test fix (Rule 1, same task's own breakage) folded into the same commit: `tests/test_availability.py::test_every_source_row_predates_its_gw_deadline` joined `deadlines` back onto `resolved` for `deadline_ts`, now a column collision since `resolved` carries its own.
2. **Task 2: Register the full family and prove the whole-family fallback** - `03d2c7d` (test)
3. **Task 3: Diagnostic coverage report for the availability family** - `f6df639` (feat)
4. **Addendum: missing test coverage** - `97cc80e` (test) -- Task 1's acceptance criteria stated an `AssertionError` raise path with no named test; added `test_news_added_postdating_deadline_raises_naming_the_row` (Rule 2).

**Plan metadata:** (this commit, following)

## Files Created/Modified

- `config.py` - `AVAILABILITY_COLS` grown from `["av_chance_pct"]` to the full eight-name list, comment block extended with the OpenFPL citation (arXiv:2508.09992) and the `av_snapshot_age_days` staleness rationale
- `data/availability.py` - `_STATUS_CODES`/`_STATUS_ALIASES`/`_OPTIONAL_SOURCE_COLS` constants; `encode_availability()`; `resolve_as_of()` extended to pass `deadline_ts`/optional columns through; `load_sources()` and both provider functions extended to carry optional columns; `build()` wired to `encode_availability` and now writes an on-disk-only `source` provenance column; `attach()` joins whichever `config.AVAILABILITY_COLS` members are present on the cache; new `report()` function and `--report` CLI flag
- `features/engineer.py` - `CONTEXT_COLS` comment extended with the `fillna(0)` prohibition and full eight-column family description (no code change needed -- already referenced `config.AVAILABILITY_COLS`)
- `tests/test_availability.py` - 6 new tests (status one-hot family, snapshot age arithmetic, whole-family NaN fallback across all 8 columns, unrecognised-code raise, news_added-postdates-deadline raise, real-data family-classification regression gate) plus a fix to the pre-existing per-source leakage invariant test

## Decisions Made

- `'n'` status code normalised to `'u'` via `_STATUS_ALIASES`, matching `predict/live.py:130`'s existing grouping -- see Accomplishments and coverage/must_haves above.
- `resolve_as_of`'s selection/dedup logic (the two-condition cutoff, the latest-per-player groupby) is unchanged from plan 10-01; only pass-through columns (`deadline_ts` and optional `news_added`/`chance_of_playing_this_round`) were added so downstream encoding has what it needs.
- `'source'` kept as an on-disk-only column in `availability.parquet` (added by `build()` after `encode_availability` returns, never inside `encode_availability` itself, and never part of `config.AVAILABILITY_COLS`) so `--report` can break coverage down per provider without that column ever being eligible to reach `features.parquet` through `attach()`'s column-restricted merge.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a test broken by Task 1's own `resolve_as_of` pass-through addition**
- **Found during:** Task 1 verify
- **Issue:** `tests/test_availability.py::test_every_source_row_predates_its_gw_deadline` re-joined `deadlines` onto `resolved` to get `deadline_ts` -- once `resolve_as_of` started carrying its own `deadline_ts` (this task's addition), the join raised `ValueError: columns overlap but no suffix specified`.
- **Fix:** Use `resolved`'s own `deadline_ts` directly; only join `kickoff_max` from `deadlines`.
- **Files modified:** tests/test_availability.py
- **Verification:** `pytest tests/test_availability.py -q` passes
- **Committed in:** d149c5d (Task 1 commit)

**2. [Rule 1/2 - Real data outside the plan's assumed schema] Normalised the `'n'` FPL status code**
- **Found during:** Task 1 verify (`python -m data.availability --force` raised `ValueError` against real vendored data before the fix)
- **Issue:** The plan's `_STATUS_CODES = ("a", "d", "i", "s", "u")` five-code assumption doesn't cover `'n'`, which is present in real `fpl_core_insights` data (2025-26 GW2/GW3: 3-4 rows, all mid-2025-transfer-window players).
- **Fix:** Added `_STATUS_ALIASES = {"n": "u"}`, applied before validation against `_STATUS_CODES`, matching the existing `predict/live.py:130` grouping precedent. Any code NOT in this alias map still raises.
- **Files modified:** data/availability.py
- **Verification:** `python -m data.availability --force` exits 0 against real data; `test_unknown_status_code_raises_not_silently_dropped` still proves a genuinely unrecognised code raises.
- **Committed in:** d149c5d (Task 1 commit)

**3. [Rule 2 - Missing test coverage] Added a test for the news_added-postdates-deadline raise**
- **Found during:** post-Task-1 self-review against the plan's own acceptance criteria
- **Issue:** Task 1's acceptance criteria explicitly requires `encode_availability` to raise `AssertionError` naming the row when `news_added` postdates the deadline, but no test in the plan's named list covers it (unlike the symmetric `ValueError` case, which does have a named test).
- **Fix:** Added `test_news_added_postdating_deadline_raises_naming_the_row`.
- **Files modified:** tests/test_availability.py
- **Verification:** `pytest tests/test_availability.py -q` passes (14 tests)
- **Committed in:** 97cc80e

---

**Total deviations:** 3 auto-fixed (1 bug/Rule 1, 1 real-data schema gap/Rule 1-2, 1 missing test coverage/Rule 2)
**Impact on plan:** All three necessary for correctness and for the plan's own literal verify commands to pass against real data. No scope creep -- no product wiring, no new experiment flags.

## Issues Encountered

- The plan's Task 2 `<verify>` literal Python snippet asserts `set(nn.unique()) <= {0, 7, 8}` for the per-row non-null count across the eight `av_` columns on real `features.parquet`. Real data actually produces `{0, 6, 7}` (never 8, since `av_days_since_news` is currently all-NaN pending fuller `news_added` capture from 10-06's vendoring; and 438 rows have `status='a'` but a null `chance_of_playing_next_round` in the source CSV, giving 6 non-null instead of 7). Investigated directly: confirmed this is legitimate per-field source-data sparsity (verified: for every present row, the five `av_status_*` columns plus `av_snapshot_age_days` are ALWAYS jointly non-null together -- 27,857/27,857 present rows -- while only `av_chance_pct` and `av_days_since_news` can independently be null due to sparse upstream fields), not a partial-fill bug. This is the same class of plan-authored-verify-command-doesn't-hold-in-this-environment situation STATE.md already records for Phase 06 (bash negation / grep shim precedents) -- verified the same underlying invariant with a stronger, corrected check rather than weakening the implementation. No code change was needed; documented here per that established pattern.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `config.AVAILABILITY_COLS`'s full eight-column family, `encode_availability`, and `--report`'s coverage/staleness reporting are the foundation plan 10-06 (FPL-Core-Insights committed vendoring, all 38 gameweeks) and plan 10-08 (the D-09 adoption-deciding run) build directly on top of.
- 10-06's vendoring will materially change the numbers recorded here: `av_snapshot_age_days`' current 124.7-day median (an artifact of only 3 probed gameweeks) should drop close to the daily-capture cadence once the full season is committed, and `av_days_since_news`'s current all-NaN state should start populating once `news_added` is consistently present across all 38 gameweeks.
- The `'n'` status-code discovery should be re-checked against 10-06's full 38-gameweek data -- it's plausible other status codes outside `_STATUS_CODES` surface once the full season (not just GW1-3) is vendored; `encode_availability`'s `ValueError` will surface any such code loudly rather than silently mis-encoding it.
- No blockers.

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*

## Self-Check: PASSED

- FOUND: config.py
- FOUND: data/availability.py
- FOUND: features/engineer.py
- FOUND: tests/test_availability.py
- FOUND: .planning/phases/10-xp-experiment-follow-ups/10-04-SUMMARY.md
- FOUND: commit d149c5d (Task 1)
- FOUND: commit 03d2c7d (Task 2)
- FOUND: commit f6df639 (Task 3)
- FOUND: commit 97cc80e (Task 1 addendum -- missing test coverage)
- FOUND: commit 43fe5aa (plan summary)
- Re-ran repo-wide `python -m pytest -q`: 279 passed, 1 skipped, 0 failed
- Re-ran `ruff check .`: all checks passed
- Re-ran plan-level `<verification>` checks: `config.AVAILABILITY_COLS` is the eight-name family registered only in `CONTEXT_COLS`; `features.parquet` carries all eight raw, zero rolled variants; `availability_coverage.json` exists with `per_season`/`per_source` keys; 2025-26 coverage (92.2%) recorded above as the pre-vendoring baseline
