---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 02
subsystem: ml-experimentation
tags: [external-data, benchmark, player-identity, crosswalk, theFPLkiwi, spearman, mae]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, backtest/walk_forward.py --seasons/--tag CLI, Phase F ledger in IMPROVEMENTS.md)"
provides:
  - "data/external/kiwi/ snapshot: theFPLkiwi's ID_Dictionary.csv + three seasons of tidy per-gameweek projection CSVs, committed forever, attributed, reproducible with no network access (D-10)"
  - "backtest/benchmark_external.py: --fetch (network, human-run) + default no-network scoring mode reporting MAE/Spearman for xp_med/xp_mean/xp_fpl/proj_pts on played-only common rows"
  - "data/id_crosswalk.py: build()/load_crosswalk()/resolve_by_name() -- the one player_code-keyed alias table plans 09-08/09-09 resolve foreign player names through"
  - "IMPROVEMENTS.md Phase F benchmark reading, recorded before any feature-accuracy experiment in this phase runs (D-01)"
affects: [09-08, 09-09]

actuals:
  tokens: 7700
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "External data snapshot: fetch (deliberate, human-run, network) vs default (no-network, committed-cache-only) two-step design, mirroring data/fbref.py"
    - "Positional CSV parsing (never by column name) when a source's own column names repeat across sections/vary by vintage"
    - "player_code-keyed alias table with drop_duplicates + is_unique assertion, the reapplied guard from IMPROVEMENTS.md Phase E's fbref join-corruption incident"

key-files:
  created:
    - backtest/benchmark_external.py
    - data/external/README.md
    - data/external/kiwi/ID_Dictionary.csv
    - data/external/kiwi/kiwi_projections_2021-22.csv
    - data/external/kiwi/kiwi_projections_2022-23.csv
    - data/external/kiwi/kiwi_projections_2023-24.csv
    - data/id_crosswalk.py
    - tests/test_crosswalk.py
  modified:
    - IMPROVEMENTS.md

key-decisions:
  - "Positional column parsing keyed on non-numeric-header-column index (always index 11 for the projection block), not on block label text -- live verification found theFPLkiwi's block labels vary not just by season vintage as the plan's measured_facts stated, but even between a season's own GW1 file (which omits the trailing Goals/npG block, yielding 12 non-numeric columns instead of 13) and every later gameweek file in the same season"
  - "id_crosswalk.py's alias table is add-alongside, not a replacement for data/id_map.py -- player_code stays the sole canonical join key everywhere; the crosswalk only maps foreign names/ids onto it (per the plan's own assumption-delta decision)"

patterns-established:
  - "Guarded optional-enrichment two-step module shape (fetch vs. score/attach, no-op on missing cache) for any future external data source"

requirements-completed: []

coverage:
  - id: D1
    description: "theFPLkiwi snapshot fetched, positionally reduced to 8 tidy columns, committed under data/external/kiwi/ (1.7 MB, well under the 10 MB budget), attributed with source URL/retrieval date/resolved revision/licence posture/PII spot-check in data/external/README.md, and reproducible forever with no network access"
    requirement: null
    verification:
      - kind: integration
        ref: "python -m backtest.benchmark_external --fetch (38/27/4 files -> 21,355/14,942/1,786 rows across the three seasons)"
        status: pass
      - kind: unit
        ref: "schema + placeholder-row + size + git-check-ignore verify commands from 09-02-PLAN.md Task 1"
        status: pass
    human_judgment: false
  - id: D2
    description: "One shared player_code-keyed identity crosswalk (data/id_crosswalk.py) serving every enrichment source in this phase, with resolve_by_name() as the mandatory fallback for Understat (no Understat id column exists upstream)"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/test_crosswalk.py (6 tests: _norm accent-stripping, build() uniqueness, name_key/fbref_key presence, resolve_by_name hit, resolve_by_name miss, merge row-count preservation)"
        status: pass
      - kind: integration
        ref: "python -m data.id_crosswalk (454 rows; 16.6% coverage of id_map.parquet's 2,737 distinct player_code values)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Our xP scored against theFPLkiwi and FPL's own ep_next-equivalent baseline on played-only common rows, per season and pooled, recorded in IMPROVEMENTS.md's Phase F before any feature-accuracy experiment in this phase runs, with an explicit statement that it prunes nothing"
    requirement: null
    verification:
      - kind: integration
        ref: "python -m backtest.benchmark_external --tag phase9 (pooled n=17,488 played-only rows, join coverage 84.4%/57.5%)"
        status: pass
      - kind: other
        ref: "IMPROVEMENTS.md token-presence check (Phase F, theFPLkiwi, Spearman) + full pytest -q (190 passed, 1 skipped) + ruff check ."
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 2: External-Projection Benchmark + Player-Identity Crosswalk Summary

**Committed a 1.7 MB theFPLkiwi snapshot, built the one player_code-keyed identity crosswalk every later enrichment plan resolves through, and scored our xP against theFPLkiwi and FPL's own baseline on played-only common rows — finding our model and theFPLkiwi land in the same MAE/Spearman neighbourhood while FPL's own official expected points ranks noticeably better on these two historical seasons.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-09-08T11:58:00Z
- **Completed:** 2026-09-08T12:20:00Z
- **Tasks:** 3
- **Files modified:** 9 (8 created, 1 modified)

## Accomplishments

- `data/external/kiwi/` — theFPLkiwi's `ID_Dictionary.csv` (62 KB, verbatim) plus three
  seasons of tidy per-gameweek projection CSVs (`2021-22`: 21,355 rows/38 gws,
  `2022-23`: 14,942 rows/27 gws, `2023-24`: 1,786 rows/4 gws), reduced from ~60 MB of
  raw wide exports to 1.7 MB, committed permanently and not gitignored (D-10).
  `data/external/README.md` documents source URLs, retrieval date, resolved upstream
  revision (`166503a`), attribution, the no-licence-file posture, the exact
  regeneration command, and a PII spot-check confirming only the eight declared tidy
  columns are present.
- `backtest/benchmark_external.py` — two-step module mirroring `data/fbref.py`:
  `--fetch` (network, human-run) downloads and positionally reduces theFPLkiwi's CSVs;
  the default mode (no network) builds leakage-safe predictions via
  `backtest.walk_forward._preds_for`, collapses to one row per `(season, player_id,
  gw)`, inner-joins to the committed snapshot, filters to played-only rows (the B8
  fix), and reports MAE + Spearman for `xp_med`, `xp_mean`, `xp_fpl` (FPL's own
  baseline) and `proj_pts` (theFPLkiwi), per season and pooled. `--tag` writes a JSON
  summary via `ops.jsonio.write_json`.
- `data/id_crosswalk.py` — `build()`/`load_crosswalk()`/`resolve_by_name()` over the
  committed `ID_Dictionary.csv`: a `player_code`-unique alias table (`drop_duplicates`
  + an explicit `is_unique` assertion, reapplying the exact guard that stopped a
  many-to-many join from corrupting a whole backtest in `data/fbref.py`, per
  IMPROVEMENTS.md Phase E). `resolve_by_name()` normalises via `_norm` (NFKD strip +
  lowercase, copied verbatim from `data/fbref.py`) against `name_key` then
  `fbref_key`, with a `_NAME_FIXUPS` manual-override hook for future misses.
- **Finding, recorded in IMPROVEMENTS.md Phase F, worth carrying forward:**
  theFPLkiwi's committed `ID_Dictionary.csv` carries **no Understat identifier column**
  at all — this settles 09-RESEARCH.md's Open Question 3 and assumption A5 in the
  negative, and makes `resolve_by_name()` load-bearing (not merely a fallback) for
  plan 09-08's Understat integration.
- **Benchmark reading** (played-only common rows, pooled over 2021-22/2022-23, n=17,488;
  2023-24 explicitly skipped — its committed snapshot only carries 4 gameweeks):
  our xP (`xp_med` MAE 1.978, Spearman 0.383) and theFPLkiwi's projections (`proj_pts`
  MAE 2.059, Spearman 0.383) land in the same neighbourhood — neither is clearly ahead.
  FPL's own `xp_fpl` baseline ranks noticeably better (Spearman 0.579) despite a
  comparable MAE (1.975). Recorded before any feature-accuracy experiment in this
  phase runs, per D-01's sequencing intent, and explicitly stated to prune nothing —
  all six experiments still run in the fixed order.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fetch, reduce and permanently commit theFPLkiwi snapshot with attribution** - `44e28fe` (feat)
2. **Task 2: One shared player-identity crosswalk keyed on player_code** - `b607e70` (test)
3. **Task 3: Score our xP against theFPLkiwi and record the reading** - `4f2d37c` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `backtest/benchmark_external.py` (new) - `--fetch`/`--seasons`/`--tag` CLI; positional CSV reduction; leakage-safe scoring against the walk-forward harness
- `data/external/README.md` (new) - source, attribution, regeneration command, reduction, PII spot-check
- `data/external/kiwi/ID_Dictionary.csv` (new) - committed verbatim, 62 KB
- `data/external/kiwi/kiwi_projections_2021-22.csv` / `_2022-23.csv` / `_2023-24.csv` (new) - tidy per-gameweek projections
- `data/id_crosswalk.py` (new) - `build()`, `load_crosswalk()`, `resolve_by_name()`, `_NAME_FIXUPS`
- `tests/test_crosswalk.py` (new) - 6 tests
- `IMPROVEMENTS.md` - new Phase F benchmark sub-section (table + interpretation)

## Decisions Made

- Column-block location keyed on a fixed non-numeric-header-column INDEX (always 11),
  not on block label text or a fixed 13-column assumption. Live verification during
  execution found the block layout varies not just by the season vintages the plan's
  own measured_facts described (2021-22/2022-23 vs 2023-24 label text), but ALSO
  within a single season: 2021-22's own `FPL_GW1.csv` omits the trailing Goals block
  entirely (12 non-numeric header columns, not 13) while every later gameweek file in
  the same season carries 13. The fix generalizes the plan's own "locate positionally,
  never by name" instruction one level further — the block position (index 11) is
  invariant even when the total column count and trailing block presence are not.
- `data/id_crosswalk.py` is deliberately add-alongside `data/id_map.py`, not a
  replacement or a generic identity abstraction — matches the plan's own
  assumption-delta decision verbatim; `player_code` remains the sole canonical join
  key everywhere in this codebase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Positional column-block assertion was too strict for a real upstream layout variant**
- **Found during:** Task 1's own `--fetch` verify command
- **Issue:** The plan's measured_facts described exactly 13 non-numeric header columns
  per projection CSV (5 identity + 3 summary + 5 block labels). Live fetching hit an
  `AssertionError` on `Old_Seasons/FPL_projections_21_22/FPL_GW1.csv`: that file has
  only 12 non-numeric header columns because it omits the trailing Goals/npG block
  entirely (theFPLkiwi evidently didn't publish goals data in the season's very first
  weekly projection file).
- **Fix:** Verified across a sample of files spanning all three seasons that the
  target block (points-if-played's sibling, the actual per-gameweek projection) is
  always the 12th non-numeric header column (0-based index 11) regardless of whether
  a 13th (Goals) block follows it. Relaxed the assertion to `len(label_idx) >= 12`
  and kept the positional lookup at a fixed index 11, with a code comment recording
  the observed variance for future maintainers.
- **Files modified:** `backtest/benchmark_external.py`
- **Verification:** Re-ran `--fetch`; all three seasons produced schema-correct tidy
  CSVs (`kiwi_projections_2021-22.csv`: 38 distinct gameweeks, `_2022-23.csv`: 27,
  `_2023-24.csv`: 4) with zero placeholder (`fpl_id == 0`) rows surviving.
- **Committed in:** `44e28fe` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug, discovered via live network verification
against upstream data the plan's own measured_facts had only sampled from a subset of
gameweek files).
**Impact on plan:** Necessary for `--fetch` to complete at all on every season present
in the upstream repository; no scope creep — the fix only widens the acceptable
column-count range while keeping the exact same positional-lookup discipline the plan
itself mandated.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The committed `data/external/kiwi/` snapshot and `data/id_crosswalk.py` are ready for
  plans 09-08 (Understat, via the now load-bearing `resolve_by_name()` fallback) and
  09-09 (FotMob/FBref) to consume without inventing their own name matchers.
- The Phase F benchmark reading is recorded and explicitly non-pruning, so plans
  09-03 through 09-10 proceed exactly as sequenced in D-01 with this reading as
  interpretive context.
- No blockers. `predict/live.py`, `predict/export.py`, `data/build_table.py` and
  `features/engineer.py` are untouched — the weekly product surface is unaffected by
  this plan.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (backtest/benchmark_external.py, data/external/README.md,
data/external/kiwi/ID_Dictionary.csv, data/external/kiwi/kiwi_projections_2021-22.csv,
data/external/kiwi/kiwi_projections_2022-23.csv, data/external/kiwi/kiwi_projections_2023-24.csv,
data/id_crosswalk.py, tests/test_crosswalk.py) exist on disk; all three task commits
(44e28fe, b607e70, 4f2d37c) found in git log; full pytest suite (190 passed, 1 skipped)
and ruff both green; `python -m backtest.benchmark_external` and
`python -m data.id_crosswalk` both re-run clean with no network access required for
the former's default mode.
