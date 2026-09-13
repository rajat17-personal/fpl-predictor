---
phase: 10-xp-experiment-follow-ups
plan: 06
subsystem: data-pipeline
tags: [availability, leakage-safety, fpl-core-insights, vendoring, license-gate]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "data/availability.py's provider registry, gw_deadlines(),
      resolve_as_of() as-of-deadline resolver, the availability_flags
      experiment gate (10-01), and the full eight-column OpenFPL-style
      encoding + --report coverage tooling (10-04)"
provides:
  - "data/external/fpl_core_insights/2025-2026/GW<1..38>_playerstats.csv --
    the committed, license-gated, all-38-gameweek 2025-26 availability
    vintage data/availability.py's fpl_core_insights provider was already
    coded (10-01/10-04) to read but had no committed home for"
  - "data/fpl_core_insights.py -- --fetch/--verify/--license CLI
    (backtest/benchmark_external.py's two-step shape)"
  - "data/processed/experiments/fpl_core_insights_verify.json -- the D-05
    gate's measured status/chance agreement result against our own
    data/snapshots/ captures"
  - "2025-26 availability coverage now materially non-zero (92.7%) with
    fresher, non-stale per-gameweek values -- unblocks plan 10-08's D-09
    covered-season measurement"
affects: [10-08, 10-16]

# Actuals (#2632)
actuals:
  tokens: 42000
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Vendored the committed snapshot into the READER's already-tested,
      already-coded path (data/availability.py::_fpl_core_insights_source's
      nested <season_dir>/GW<n>_playerstats.csv layout, written by 10-01/
      10-04) rather than the plan text's literal flat _OUT_DIR/fpl_core_
      insights_2025-26_gw<NN>.csv naming, since the reader's glob
      (GW*_playerstats.csv nested under a season subdirectory) cannot
      discover flat files under a different name pattern -- zero changes
      to data/availability.py needed, and the pipeline works end to end on
      the first --force rebuild after --fetch."
    - "verify()'s low chance_of_playing_next_round agreement rate (27.6%)
      is a genuine, explained source-semantics difference (FPL's own API
      leaves the field null for most fully-fit players; the vendor
      backfills many of those to 100.0), not a bug -- spot-checked directly
      against real snapshot data before writing it up, per the established
      'investigate before dismissing an odd verify number' precedent
      (Phase 06/Phase 10-04's own documented examples of this same
      discipline)."

key-files:
  created:
    - data/fpl_core_insights.py
    - data/external/fpl_core_insights/README.md
    - data/external/fpl_core_insights/2025-2026/GW1_playerstats.csv (and GW2-38, 38 files total)
  modified:
    - tests/test_availability.py

key-decisions:
  - "Task 1 checkpoint: license posture Option A (theFPLkiwi pattern --
    attribution + retrieval date + revision SHA + reduction record),
    human-approved verbatim as 'A'. Full evidence recorded below."
  - "Committed CSV layout matches data/availability.py's existing nested
    read path (<base>/2025-2026/GW<n>_playerstats.csv) rather than the
    plan action text's literal flat _OUT_DIR/fpl_core_insights_2025-26_gw<NN>.csv
    naming -- a deliberate deviation from the plan's literal filename
    instruction to honor the SAME task's read_first instruction to match
    what the already-built, already-tested provider actually reads. See
    Deviations section."
  - "_KEEP_COLS kept at exactly the six columns named in Task 1's checkpoint
    (id, status, chance_of_playing_next_round, chance_of_playing_this_round,
    news, news_added) -- no name column, so data.id_crosswalk.resolve_by_name's
    fallback (mentioned in the plan's action text) has no column to operate
    on and is not invoked; identity resolution uses only data.id_map.load_id_map's
    existing (season, player_id) -> player_code join, matching what the
    reader itself already does."
  - "verify()'s comparison point is the vendored snapshot's LATEST committed
    gameweek (GW38, end of the completed 2025-26 season) against both
    overlap dates -- the temporally closest vendored data point to our own
    2026-08-31/2026-09-07 captures."

requirements-completed: [TODO-AVAIL-FLAGS]

coverage:
  - id: D1
    description: "License read and posture decision recorded before any commit (D-05 costly-reversibility gate)"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: other
        ref: "Task 1 checkpoint: LICENSE/LICENSE.md 404, GitHub API license field null, README 'Using The Data' clause quoted verbatim, main SHA resolved, human decision 'A' recorded"
        status: pass
    human_judgment: true
  - id: D2
    description: "All 38 available 2025-26 gameweeks fetched, reduced to the approved six-column footprint, and committed under 20 MB"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: integration
        ref: "python -m data.fpl_core_insights --fetch (real network run, 38/38 gameweeks written)"
        status: pass
      - kind: other
        ref: "du -sk data/external/fpl_core_insights -> 1,028 KB (well under 20,000)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Vendored snapshot verified against our own captures with a real, printed agreement rate"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: integration
        ref: "python -m data.fpl_core_insights --verify -> data/processed/experiments/fpl_core_insights_verify.json (status_agreement, chance_agreement, per_gw present)"
        status: pass
    human_judgment: false
  - id: D4
    description: "N-1 leakage offset proven on synthetic data, plus the missing-column raise"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: unit
        ref: "tests/test_availability.py::test_vendored_provider_uses_prior_gw_folder"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_reduce_gw_csv_raises_on_missing_availability_column"
        status: pass
    human_judgment: false
  - id: D5
    description: "2025-26 availability coverage measurably non-zero and improved after vendoring"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: integration
        ref: "python -m data.availability --report: 2025-26 coverage 92.2% -> 92.7% (27,195/29,338 rows)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 06: FPL-Core-Insights Committed Vendoring Summary

**Vendored all 38 available 2025-26 gameweeks of FPL-Core-Insights availability data (934.7 KB reduced CSVs, 1,028 KB on disk) into `data/availability.py`'s already-coded but previously-empty committed provider directory, gated on a human-approved license posture, verified against our own snapshot captures, and pushed 2025-26 availability coverage from 92.2% to 92.7% -- unblocking plan 10-08's D-09 covered-season criterion.**

## Performance

- **Duration:** 55 min
- **Tasks:** 3 (Task 1 was a checkpoint resumed from a prior executor's pause; Tasks 2-3 executed in this session)
- **Files modified:** 41 (1 new module, 38 new CSVs, 1 new README, 1 modified test file)

## Accomplishments

- **Task 1 (checkpoint, resolved this session):** the license/footprint evidence a prior executor gathered was reused per the resume instructions (no re-fetch needed to re-verify); the human's decision -- verbatim **"A"** (Option A: vendor under the theFPLkiwi posture) -- is recorded below and in `data/external/fpl_core_insights/README.md`'s `## Attribution` section.
- Built `data/fpl_core_insights.py`: a two-step `--fetch`/`--verify`/`--license` CLI in `backtest/benchmark_external.py`'s shape. `fetch()` lists FPL-Core-Insights' 38 `GW<n>` folders for 2025-26 via the GitHub contents API, downloads each `playerstats.csv`, and reduces it to the exact six columns approved at the checkpoint (`id, status, chance_of_playing_next_round, chance_of_playing_this_round, news, news_added`).
- **Real, full network fetch executed**: all 38 gameweeks (2025-26 is a fully completed past season as of 2026-09-10) downloaded and reduced successfully, none 404'd. Total committed footprint: **934.7 KB** summed across files (**1,028 KB** on disk per `du -sk`), well under the 20 MB D-05 gate -- an ~8x reduction from the extrapolated ~7.6 MB raw footprint (3 probed raw files averaging ~200.1 KB/gw, per 10-01's own probe).
- `verify()` (read-only, no network) compared the vendored snapshot's latest gameweek (GW38, end of the completed 2025-26 season) against our own `data/snapshots/*.parquet` captures on the two dates this project has actually taken (2026-08-31, 2026-09-07). Result: **69.2% status agreement, 27.6% `chance_of_playing_next_round` agreement** (946 players compared, 698 disagreements). The chance-agreement gap was investigated directly rather than dismissed: of 484 `status == 'a'` rows in our own 2026-09-07 snapshot, 422 (87%) carry a **null** `chance_of_playing_next_round` (FPL's own API convention for "no doubt flag raised"), while the vendor's GW38 file shows the reverse split (352 at `100.0` vs 211 null) -- both sources agree the player is available, they just encode "no doubt" differently. This is recorded as a genuine finding in the README, not glossed over.
- Full pipeline re-run end to end: `data.build_table` -> `features.engineer` -> `data.availability --report`. **2025-26 availability coverage: 92.2% -> 92.7% (27,195/29,338 rows)**, with individually fresher (less-stale) per-gameweek values across the season now that 35 additional gameweeks are available for `resolve_as_of`'s N-1 selection, rather than the prior 3-gameweek probe's near-total forward-carry from GW2.
- Wrote `data/external/fpl_core_insights/README.md`: seven sections (`## Source`, `## Attribution`, `## Regeneration`, `## Reduction applied`, `## PII spot-check`, `## Leakage rule`, `## Verification against our own snapshots`), following `../README.md`'s (theFPLkiwi) established shape, plus a 40-hex resolved commit SHA (`f15bf7b6dea6cb441c2dc1ad9a02e4d9749cc68f`). `data/external/README.md` itself was confirmed unmodified.
- Added `tests/test_availability.py::test_vendored_provider_uses_prior_gw_folder` (the D-05 N-1 leakage offset, proven end to end on a synthetic single-gameweek vendored directory against the real resolver and real 2025-26 kickoff data) and `test_reduce_gw_csv_raises_on_missing_availability_column` (T-10-06-02's missing-column raise).

## Task Commits

Each task was committed atomically:

1. **Task 1: License read and commit posture** — resolved via this session's checkpoint resume (no standalone commit; the decision and its evidence are recorded in this SUMMARY per the plan's own `<output>` contract)
2. **Task 2: Fetch, reduce, and verify the 2025-26 vendored snapshot** — `9c3c56e` (feat)
3. **Task 3: Committed-snapshot README** — `2411026` (docs)

**Plan metadata:** (this commit, following)

## Files Created/Modified

- `data/fpl_core_insights.py` — `_RAW_BASE`, `_API_CONTENTS`, `_OUT_DIR`, `_SEASON_DIR`, `_KEEP_COLS`, `_REQUEST_DELAY_S`, `_list_gw_files`, `_gw_from_filename`, `_reduce_gw_csv`, `fetch`, `license_check`, `_per_gw_stats`, `verify`, `main`
- `data/external/fpl_core_insights/2025-2026/GW1_playerstats.csv` through `GW38_playerstats.csv` — 38 reduced CSVs (759-841 rows each, six columns)
- `data/external/fpl_core_insights/README.md` — seven-section vendoring record
- `tests/test_availability.py` — 2 new tests (16 total in the file now), `id_map`/`fpl_core_insights` imports added

## Task 1 Checkpoint Record (per plan's `<output>` contract)

**License fetch result (verbatim, gathered at the checkpoint, reused per resume instructions):**
- `curl https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/LICENSE` → **404**
- `curl https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/LICENSE.md` → **404**
- GitHub API `license` field for the repository → **`null`** (re-confirmed at Task 3 execution time)
- README.md `## Using The Data` clause (verbatim): *"Feel free to use the data from this repository in whatever way works best for you—whether for your website, blog posts, or other projects. If possible, I'd greatly appreciate it if you could include a link back to this repository as the data source."*

**Resolved `main` commit SHA:** `f15bf7b6dea6cb441c2dc1ad9a02e4d9749cc68f` ("Auto-update FPL data 2026-09-10 12:19 UTC", `github-actions[bot]`, 2026-09-10T12:19:54Z) — a bot-maintained repository whose `main` moves roughly twice daily; this is the retrieval-time pin.

**Extrapolated footprint (as presented at the checkpoint):** ~198.7 KB/GW raw, ~6 of 87 columns kept → ~520 KB estimated committed footprint, CSVs only, no parquet, no full-table copies. (**Actual measured footprint after the real fetch: 934.7 KB / 1,028 KB on disk** — higher than the pre-fetch estimate but still ~8x smaller than the ~7.6 MB raw total, and well under the 20 MB gate.)

**Posture decision (verbatim):** **"A"** — Option A) Vendor under the theFPLkiwi posture: attribution + retrieval date + revision SHA + reduction record in `data/external/fpl_core_insights/README.md`.

## Decisions Made

- License posture Option A, human-approved verbatim as "A" (see checkpoint record above and `data/external/fpl_core_insights/README.md`'s `## Attribution`).
- Committed CSV layout follows `data/availability.py::_fpl_core_insights_source`'s existing nested read path (`<base>/2025-2026/GW<n>_playerstats.csv`), not the plan action text's literal flat `_OUT_DIR/fpl_core_insights_2025-26_gw<NN>.csv` naming — see Deviations.
- `_KEEP_COLS` fixed at exactly the six checkpoint-approved columns; `data.id_crosswalk.resolve_by_name` fallback not invoked since no name column exists in that footprint (identity resolution uses only `data.id_map.load_id_map`, matching the reader).
- `verify()` compares against the vendored snapshot's latest gameweek (GW38) — the temporally closest point to our own capture dates.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Committed CSV layout matches the existing reader's nested directory convention, not the plan's literal flat filename instruction**
- **Found during:** Task 2 design, before any fetch ran
- **Issue:** The plan's `<action>` text literally specifies `fetch()` writing flat files named `_OUT_DIR / f"fpl_core_insights_2025-26_gw{gw:02d}.csv"` directly under `data/external/fpl_core_insights/`. But `data/availability.py::_fpl_core_insights_source()` (built by 10-01, extended by 10-04, explicitly named in this same task's `<read_first>` list) already reads a NESTED layout: `<base>/<season_dir>/GW<n>_playerstats.csv`, discovered via `season_dir.glob("GW*_playerstats.csv")` over subdirectories. A flat file named per the plan's literal instruction would never match that glob (it doesn't start with `GW`), so `_fpl_core_insights_source()` would find zero files and every downstream verify gate requiring increased 2025-26 coverage (`python -m data.availability --report` strictly above the 92.2% baseline) would fail.
- **Fix:** Wrote into the reader's actual, already-tested read path instead: `data/external/fpl_core_insights/2025-2026/GW<n>_playerstats.csv` (the vendor's own directory naming, exactly matching `_fci_season_label`'s translation). Zero changes to `data/availability.py` (outside this plan's `files_modified` scope) were needed as a result.
- **Files modified:** data/fpl_core_insights.py (the module's own design, not a later patch)
- **Verification:** `python -m data.availability --force`/`--report` both correctly discovered and joined all 38 vendored gameweeks; 2025-26 coverage measurably increased (92.2% → 92.7%); `test_vendored_provider_uses_prior_gw_folder` passes against the real reader.
- **Impact:** No file outside the plan's declared `files_modified` scope was touched; the deviation is confined to `data/fpl_core_insights.py`'s own internal layout choice, which the plan's `<acceptance_criteria>` textual filename pattern (`fpl_core_insights_2025-26_gw<NN>.csv`) does not literally match, but no automated `<verify>` command in Task 2 or Task 3 checks the exact filename — every actual gate (row counts, `du -sk`, the verify JSON's required keys, the coverage increase, both new tests, `data/external/README.md` unchanged) passes.

---

**Total deviations:** 1 auto-fixed (Rule 1, plan-text/existing-code layout conflict, resolved in favor of the already-built and already-tested reader)
**Impact on plan:** Necessary for every downstream verify gate to pass against real data; the objective ("fill the fpl_core_insights provider's committed home") is met exactly as intended.

## Issues Encountered

- A background-process race during the full pipeline re-run: two `features.engineer` invocations ran concurrently after a tool-level 120s backgrounding split one `&&`-chained command into a second parallel run. Both processes wrote toward the same `data/processed/features.parquet` target. Caught immediately via `ps aux`; the later-started duplicate (and its `timeout` wrapper) was killed with `SIGKILL` before either could corrupt the other's output, then the original process was waited out to a clean completion. `features.parquet` was verified afterward (168 columns, all 8 `av_*` columns present, zero rolled variants, real Haaland leakage-check trace intact) — no corruption occurred, but this is recorded here as a near-miss for future executors running multi-minute pipeline steps under a background-task harness.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `data/external/fpl_core_insights/` (38 committed gameweeks, README) and `data/fpl_core_insights.py` are now in place; `data/availability.py`'s `fpl_core_insights` provider picks them up automatically on the next `--force` rebuild, no code change required.
- Plan 10-08's D-09 covered-season criterion for 2025-26 is now measurable: 92.7% coverage, up from the pre-vendoring 92.2% baseline, with fresher (non-stale) per-gameweek values across 37 of 38 gameweeks (only GW1 has no predecessor folder and correctly resolves to NaN, per the N-1 leakage rule).
- The `--verify` gate's honest 27.6% chance-agreement finding (explained, not a defect) and 69.2% status-agreement finding (real player-status drift over ~4 months) are both recorded in the README for plan 10-08 or any later plan to cite without re-deriving.
- No blockers.

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*

## Self-Check: PASSED

- FOUND: data/fpl_core_insights.py
- FOUND: data/external/fpl_core_insights/README.md
- FOUND: .planning/phases/10-xp-experiment-follow-ups/10-06-SUMMARY.md
- FOUND: commit 9c3c56e (Task 2)
- FOUND: commit 2411026 (Task 3)
- Re-ran repo-wide `python -m pytest -q`: 284 passed, 1 skipped, 0 failed
- Re-ran `ruff check .`: all checks passed
- Re-ran plan-level `<verification>` checks: `data/external/fpl_core_insights/` measures 1,028 KB (`du -sk`, well under 20 MB), 38 CSVs, zero parquet; `fpl_core_insights_verify.json` carries `status_agreement`/`chance_agreement`/`per_gw`; `data.availability --report` shows 2025-26 coverage 92.7% (> 10-04's 92.2% baseline); README has all seven sections plus a 40-hex revision SHA; `data/external/README.md` confirmed unmodified and free of any `fpl_core_insights` reference
