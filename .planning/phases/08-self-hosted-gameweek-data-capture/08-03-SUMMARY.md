---
phase: 08-self-hosted-gameweek-data-capture
plan: 03
subsystem: data-ingest
tags: [fpl-api, vaastav-schema, backfill, cross-check, canonical-table]

# Dependency graph
requires:
  - phase: 08-self-hosted-gameweek-data-capture
    provides: "08-01/08-02's complete data/gw_capture.py module (bootstrap+fixtures fetch, element-summary sweep, vaastav-schema frame builder, xP resolution, per-GW ledger, freshness alert) -- this plan is its first real exercise against the live API"
provides:
  - "Real captured current-season data: data/raw/2026-27/{merged_gw.csv, gws/gw1.csv, gws/gw2.csv, gws/gw3.csv, players_raw.csv, fixtures.csv} -- GW1 610 rows, GW2 626 rows, GW3 654 rows, zero per-player fetch failures"
  - "GW1 schema mapping confirmed against vaastav's own published file, after fixing a real team-attribution bug found by the cross-check"
  - "data/processed/player_gw.parquet rebuilt: 1,890 current-season rows ingested via data/build_table.py/data/id_map.py with zero code changes to either, zero regression across the ten past seasons"
  - "08-BACKFILL-EVIDENCE.md: every measured number from the real run, including the permanent GW1/GW2 xP null gap and the diagnosed-absent (not mismatched) current-season odds source"
affects: [08-04-ingest-guard-and-runbook, 08-05-cron-wiring, any-future-phase-promoting-2026-27-into-training-seasons]

# Actuals (#2632)
actuals:
  tokens: 9500
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Historical team attribution resolved from the row's own fixture (team_h/team_a keyed by was_home), never from a player's current bootstrap team assignment -- the only way to keep a since-transferred player's past rows correctly attributed to their club at the time"
    - "A hard per-season fixture-count 'systemic reconstruction failure' assertion must exempt the one season that is legitimately still in progress, while still raising for any genuinely broken complete season"

key-files:
  created:
    - .planning/phases/08-self-hosted-gameweek-data-capture/08-BACKFILL-EVIDENCE.md
  modified:
    - data/gw_capture.py
    - data/team_strength.py
    - tests/test_gw_capture.py
    - tests/test_leakage.py

key-decisions:
  - "team resolution bug found by the live GW1 cross-check (17/610 rows) was fixed in data/gw_capture.py and the affected gameweeks re-captured with --force, never patched in the captured CSV data -- per the plan's own integrity prohibition"
  - "team_strength.build_matches' systemic-failure guard exempts config.CURRENT_SEASON specifically (not a blanket fixture-count relaxation) so a genuinely broken PAST season still raises -- verified by a regression test asserting both halves"
  - "data/odds.py's 2026-27 cache (a stale pre-season 'HTTP 300 Multiple Choices' error page from football-data.co.uk) was diagnosed as an absent upstream source, not the club-name-mismatch failure mode the research doc warned about, and left unfixed as out of this plan's file scope -- recorded as a measured fact, not silently worked around"
  - "features/engineer.py was not re-run and no model was retrained, per config: backtest/walk_forward.py's DATA_SEASONS excludes config.SEASONS[-1] (2026-27), so the canonical table gaining current-season rows changes zero model input under the currently configured training/test seasons"

patterns-established:
  - "Cross-check against an independent, differently-built copy of the same real-world data is the only oracle strong enough to catch a schema-mapping bug (team attribution) that every prior test (schema-convention gates, end-to-end wiring) missed because they never exercised a player who had transferred since the historical fixture they were tested against"

requirements-completed: []

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Every finished, data-checked current-season gameweek (GW1-3) is captured on disk from the live FPL API in vaastav's 46-column schema, with zero per-player fetch failures"
    verification:
      - kind: other
        ref: "python -m data.gw_capture (real run, 2026-09-12T06:37Z) -- GW1: 610 rows, GW2: 626 rows, GW3: 654 rows, exit code 0, no ALERT/failure line"
        status: pass
      - kind: other
        ref: "post-run inspection: merged_gw.csv 1890 rows/46 cols, missing_source_keys=[], ledger files gw1/gw2/gw3.csv present"
        status: pass
    human_judgment: false
  - id: D2
    description: "The self-built GW1 rows agree with the previously-published vaastav GW1 file key-for-key and column-for-column (excluding the two declared deliberate exclusions), or every disagreement is diagnosed and fixed"
    verification:
      - kind: integration
        ref: "live cross-check against https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2026-27/gws/gw1.csv -- both=610, only_theirs=0, only_ours=0, disagreeing_cols=[] after the team-resolution fix"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_build_gw_frame_resolves_team_from_the_fixture_not_the_players_current_club"
        status: pass
      - kind: unit
        ref: "tests/test_gw_capture.py::test_build_gw_frame_falls_back_to_current_team_when_fixture_not_supplied"
        status: pass
    human_judgment: false
  - id: D3
    description: "data/build_table.py and data/id_map.py ingest the captured rows into player_gw.parquet with zero code changes to either, and zero regression in any of the ten past seasons' row counts"
    verification:
      - kind: other
        ref: "python -m data.id_map (current season sourced from players_raw, not live-bootstrap fallback); python -m data.build_table (11 seasons printed, no skip line)"
        status: pass
      - kind: other
        ref: "python -c 'regressions = {} against the 10-season baseline'; git diff --quiet -- data/build_table.py data/id_map.py"
        status: pass
      - kind: unit
        ref: "tests/test_leakage.py::test_build_matches_tolerates_a_partial_current_season_but_not_a_partial_past_one"
        status: pass
      - kind: other
        ref: "python -m pytest -q -- 412 passed, 1 skipped"
        status: pass
    human_judgment: false
  - id: D4
    description: "Current-season position/fixture-difficulty/stable-code coverage meets the gate, and every measured gap (xP nulls for GW1/GW2, current-season odds absence) is recorded with its cause"
    verification:
      - kind: other
        ref: "position_cov=1.0, fdr_cov=1.0, code_cov=1.0 (all >= gates); xp_cov_by_gw={1: 0.0, 2: 0.0, 3: 0.957}; current-season odds_pwin coverage=0.0%, diagnosed as an absent (HTTP 300 error page cached), not mismatched, upstream source"
        status: pass
    human_judgment: false

# Metrics
duration: 53min
completed: 2026-09-12
status: complete
---

# Phase 8 Plan 03: Real Backfill, GW1 Cross-Check, and Canonical Rebuild Summary

**Ran the capture module for real against the live FPL API (GW1/2/3, 1,890 rows, zero fetch failures), found and fixed a genuine team-attribution bug via an independent GW1 cross-check, and rebuilt the canonical table proving the captured rows ingest into `player_gw.parquet` with zero regression across ten past seasons and zero changes to either consumer module.**

## Performance
- **Duration:** 53 min
- **Started:** 2026-09-12T06:29:32Z
- **Completed:** 2026-09-12T07:22:39Z
- **Tasks:** 3 completed
- **Files modified:** 5 (1 created evidence doc, 4 modified: 2 production fixes + 2 test files)

## Accomplishments
- Captured every finished, data-checked gameweek of the current season (2026-27 GW1/2/3) directly from the live FPL API for the first time — the two gameweeks vaastav's stalled repo never published (GW2, GW3) are now on disk in vaastav's own schema, before the `element-summary` retention window that made this possible closes.
- Cross-checked the self-built GW1 against vaastav's own independently-captured published file — the only external oracle this phase has — and found a real bug: `team` was joined from a player's CURRENT bootstrap club, silently retro-dating every since-transferred player's historical fixtures onto their new club (17/610 GW1 rows affected). Fixed in `data/gw_capture.py` per the plan's own integrity rule (code fix + `--force` re-capture, never a data edit), verified down to zero disagreeing columns.
- Rebuilt `data/processed/id_map.parquet` and `data/processed/player_gw.parquet` for real: 1,890 current-season rows now flow through `data/build_table.py`/`data/id_map.py` with **zero code changes to either module**, position/fixture-difficulty/stable-code coverage all at 100%, and all ten past-season row counts identical to the pre-phase baseline.
- Found and fixed a second real bug, this one in `data/team_strength.py`, surfaced by the plan's own full-suite gate: rebuilding `player_gw.parquet` with a legitimately in-progress current season for the first time tripped a "systemic reconstruction failure" assertion meant for a genuinely broken *complete* season. Fixed with a targeted exemption, locked by a regression test proving the exemption doesn't weaken the check for an actually-broken past season.
- Diagnosed (without fixing, correctly out of scope) a third finding: current-season odds coverage is 0% because `data/odds.py`'s cached 2026-27 file is football-data.co.uk's own pre-season "300 Multiple Choices" error page — an absent upstream source, not the club-name-mismatch failure mode the research doc anticipated (confirmed by this plan's own `team` column now being correct).
- Recorded every measured number — including the honest, permanent GW1/GW2 expected-points null gap (their deadlines precede the earliest daily snapshot and always will) — in `08-BACKFILL-EVIDENCE.md`.

## Task Commits
Each task's real work was verified live before committing; the two auto-fixes and the consolidated evidence document were each committed atomically:
1. **Task 2 fix: team resolved from the fixture, not the player's current club** - `bbc0e4c` (fix)
2. **Task 3 fix: tolerate an in-progress current season in build_matches** - `e995a0f` (fix)
3. **Tasks 1-3: real backfill, GW1 cross-check, and canonical rebuild evidence** - `ec408d9` (docs)

## Files Created/Modified
- `.planning/phases/08-self-hosted-gameweek-data-capture/08-BACKFILL-EVIDENCE.md` - Every measured number from the real run: per-GW row/failure counts, the GW1 cross-check verdict (before and after the fix), the id-map/table rebuild's before-and-after per-season counts, and every coverage/gap number
- `data/gw_capture.py` - `build_gw_frame` now takes an optional `fixtures` argument and resolves `team` from the row's own fixture (`team_h`/`team_a` keyed by `was_home`), falling back to the prior current-bootstrap-team join only when fixtures data isn't supplied
- `data/team_strength.py` - `build_matches`'s systemic-reconstruction-failure check now exempts `config.CURRENT_SEASON` specifically, printing a distinct "season in progress" line instead of raising
- `tests/test_gw_capture.py` - 2 new regression tests locking the team-from-fixture resolution and its fallback
- `tests/test_leakage.py` - 1 new regression test locking the current-season exemption without weakening the past-season systemic-failure guard

## Decisions Made
- The team-attribution bug found by the cross-check was fixed in code and the affected gameweeks re-captured with `--force`, per the plan's own prohibition against ever patching captured data to make a cross-check agree.
- `team_strength.py`'s fix is a narrow exemption keyed on `config.CURRENT_SEASON`, not a blanket fixture-count relaxation — a genuinely broken past season with the identical low fixture count still raises, proven by the new test's second half.
- The current-season odds coverage gap (0%) was diagnosed as an absent upstream source (a cached pre-season HTTP error page) and left unfixed, since `data/odds.py` is outside this plan's file scope and the diagnosis itself — not a fix — is what the plan's acceptance criteria require.
- No feature rebuild, no model retrain: `backtest/walk_forward.py`'s `DATA_SEASONS` already excludes the current season, so this plan's canonical-table change touches zero model input under the currently configured seasons.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `team` column joined the player's current club instead of the historical fixture's club**
- **Found during:** Task 2's GW1 cross-check (17/610 rows disagreed: e.g. element 28 showed "Chelsea" instead of the published "Aston Villa"; element 91 showed "Coventry City" instead of "Brentford")
- **Issue:** `build_gw_frame` resolved `team` from `bootstrap.elements[].team` (the player's CURRENT club, as of the capture run) rather than the club they played for at the time of that specific historical fixture — a since-transferred player's entire history was silently retro-dated onto their new club.
- **Fix:** `team` now resolves from the row's own fixture (`fixtures[].team_h`/`team_a`, keyed by `was_home`), with a fallback to the prior current-team join only when fixtures data isn't supplied to `build_gw_frame` directly (keeps every existing direct-call test, which never registers a matching fixture id, unaffected).
- **Files modified:** `data/gw_capture.py`, `tests/test_gw_capture.py`
- **Verification:** Re-ran the cross-check after `--force` re-capturing GW1/2/3 — `disagreeing_cols` dropped from `[('team', 17)]` to `[]`; `tests/test_gw_capture.py` full file green (33 passed, up from 31).
- **Committed in:** `bbc0e4c`

**2. [Rule 1 - Bug] `team_strength.build_matches` raised on the first-ever in-progress current season present in `player_gw.parquet`**
- **Found during:** Task 3's full-suite verification gate (`python -m pytest -q`), which surfaced `tests/test_leakage.py::test_team_strength_ratings_reproducible_from_prior_matches` failing with `AssertionError: season(s) with far fewer than 380 fixtures recovered ... {'2026-27': 30}`
- **Issue:** the "systemic reconstruction failure" guard (any season under 370 reconstructed fixtures) had never before had to tolerate a season still in progress, because every prior `player_gw.parquet` build only ever held complete past seasons. Rebuilding it with the current season's 3 finished gameweeks (30 fixtures) tripped an alarm meant for a broken pipeline, not a season that simply hasn't finished yet.
- **Fix:** `build_matches` now exempts `config.CURRENT_SEASON` from the systemic-failure raise and prints a distinct "season in progress" line for it; a genuinely broken past season with the exact same fixture count still raises. The Dixon-Coles leakage guarantee itself (`fit_ratings_as_of` never sees a match at or after the target gameweek) is untouched.
- **Files modified:** `data/team_strength.py`, `tests/test_leakage.py`
- **Verification:** `tests/test_leakage.py` full file green (13 passed, up from 12); new regression test asserts both the current-season tolerance and the still-raises-for-a-past-season behavior; full repo suite green (412 passed, 1 skipped, up from the 08-02 baseline of 409 passed, 1 skipped).
- **Committed in:** `e995a0f`

---
**Total deviations:** 2 auto-fixed (both Rule 1 — bugs directly caused by this plan's own first real exercise of previously-written code against real, live data; no architectural changes, no auth gates, no user input needed).
**Impact on plan:** Both fixes were minimal and scoped exactly to the failing behavior. Neither touched `data/build_table.py`, `data/id_map.py`, `scripts/`, or `web/` — the phase's central claim (captured rows flow into the canonical table with zero consumer-module change) held throughout.

## Issues Encountered

- `web/data/watchlist.json` (modified) plus `web/data/history/gw4.json` and `web/data/scoreboard.json` (untracked) all show in `git status` — confirmed present in the git-status snapshot taken before this plan's session began (also documented as pre-existing in 08-01-SUMMARY.md and 08-02-SUMMARY.md). Not caused by this plan; no file under `web/` was created, modified, or deleted by any command this plan ran.
- Current-season odds coverage is 0% because `data/raw/odds/2026-27.csv` is a stale, pre-season-cached HTTP "300 Multiple Choices" error page from football-data.co.uk (the 2026-27 odds CSV does not exist on their server yet) — diagnosed and recorded in `08-BACKFILL-EVIDENCE.md`, not fixed (out of this plan's file scope; `data/odds.py` is not part of `files_modified`).

## User Setup Required

None — no external service configuration required. The FPL API is unauthenticated.

## Next Phase Readiness

The canonical table now genuinely carries current-season data end to end: real captured CSVs on disk, a confirmed schema mapping, and a rebuilt `player_gw.parquet` with full current-season coverage and zero regression. Plans 08-04 (ingest guard + runbook) and 08-05 (cron wiring, gated on Phase 7 completion per the milestone invariant) can proceed against a `data/gw_capture.py` that has now been proven against the real FPL API, not just against mocked tests. No blockers. One pre-existing, out-of-scope gap is flagged for a future plan or owner: `data/odds.py`'s cache-if-exists behavior will keep serving the stale pre-season error-page CSV for 2026-27 forever unless something re-fetches it once football-data.co.uk publishes the real file.

## Self-Check: PASSED

- `[ -f .planning/phases/08-self-hosted-gameweek-data-capture/08-BACKFILL-EVIDENCE.md ]` -> FOUND
- `[ -f data/raw/2026-27/merged_gw.csv ]` -> FOUND (1,890 rows, 46 columns)
- `[ -f data/raw/2026-27/gws/gw1.csv ]`, `gw2.csv`, `gw3.csv` -> all FOUND
- `git log --oneline --all --grep="08-03"` -> FOUND (`bbc0e4c`, `e995a0f`, `ec408d9`)
- `python -m pytest tests/test_gw_capture.py -q` -> 33 passed
- `python -m pytest tests/test_leakage.py -q` -> 13 passed
- `python -m pytest -q` (full suite) -> 412 passed, 1 skipped, in 286.47s
- `git diff --quiet -- data/build_table.py data/id_map.py` -> CONSUMERS UNCHANGED
- `git status --porcelain web/ scripts/` -> only the three pre-existing, session-predating entries (documented above and in 08-01/08-02-SUMMARY.md), no new modification
- `git status --porcelain data/snapshots/` -> only the three pre-existing untracked snapshot files, no deleted/modified entries
- Plan-level `<verification>` block: all six items re-checked and green (ledger+46-col merged_gw, zero-disagreement cross-check, 11-season build with zero regression, 100%/100%/100% current-season coverage gates, full pytest green, frozen-surface silence modulo the documented pre-existing web/ entries)

---
*Phase: 08-self-hosted-gameweek-data-capture*
*Completed: 2026-09-12*
