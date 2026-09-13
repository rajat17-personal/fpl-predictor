---
phase: 10-xp-experiment-follow-ups
plan: 01
subsystem: data-pipeline
tags: [availability, leakage-safety, experiment-flags, xp-model, fpl-core-insights]

# Dependency graph
requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: config.EXPERIMENTS flag registry, backtest/walk_forward.py's
      apply_experiment_feature_gating seam, IMPROVEMENTS.md Phase F ledger
      discipline
provides:
  - "data/availability.py: a THIRD leakage-safe feature family (point-in-time
    snapshot, as-of-deadline) -- provider registry, gw_deadlines(),
    resolve_as_of(), build/load_availability/attach/main"
  - "config.AVAILABILITY_COLS, config.EXPERIMENTS['availability_flags']
    (11th key, default False)"
  - "av_chance_pct wired through data/build_table.py -> features/engineer.py's
    CONTEXT_COLS -> backtest/walk_forward.py's feature-selection gate"
  - "data/snapshot.py captures chance_of_playing_this_round/news/news_added
    from 2026-09-10 onward"
  - "IMPROVEMENTS.md ## Phase G: every Phase 10 adoption criterion (incl. the
    exact D-02 0.500 trigger) on paper before any measuring run"
affects: [10-02, 10-04, 10-06, 10-08, 10-16]

# Actuals (#2632)
actuals:
  tokens: 11300
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Third feature family (point-in-time snapshot, as-of-deadline) alongside
      ROLL_STATS (match outcomes, shift-then-roll) and CONTEXT_COLS's static
      per-fixture members -- registered in CONTEXT_COLS, never ROLL_STATS,
      because resolve_as_of's deadline boundary is already leakage-safe on
      its own terms."
    - "Provider registry pattern (SOURCES: name -> zero-arg callable) applied
      to a genuinely new axis (multiple independent sources of ONE signal,
      long-format union) rather than data/fotmob.py's single-source shape."

key-files:
  created:
    - data/availability.py
    - tests/test_availability.py
  modified:
    - config.py
    - features/engineer.py
    - data/build_table.py
    - backtest/walk_forward.py
    - data/snapshot.py
    - tests/test_leakage.py
    - tests/test_experiments.py
    - IMPROVEMENTS.md

key-decisions:
  - "fpl_core_insights provider directory layout: <base>/<season-as-in-source-repo>/GW<n>_playerstats.csv, flat -- not a full mirror of the source repo's 'By Gameweek/GW<n>/' tree, since only playerstats.csv is consumed. 10-06 has not run yet, so this is this plan's own layout choice, documented in data/availability.py's module docstring."
  - "resolve_as_of implemented as a per-season, per-gameweek cutoff = min(deadline_ts, kickoff_max) filter rather than pandas merge_asof, since merge_asof's by= grouping does not cleanly express 'latest row before a computed per-row cutoff that itself varies by (season, gw)' without a second join; the plain-loop version is O(seasons x gameweeks) and reads directly as the two-condition rule the tests assert."
  - "daily_snapshot provider rows are tagged season = config.CURRENT_SEASON (a snapshot only ever describes the live season at capture time); since player_gw.parquet carries no 2026-27 rows yet, those rows correctly resolve to zero joined gameweeks this run -- the tracer's entire measured 10.8% coverage comes from the fpl_core_insights probe (GW1/GW2 data resolving into GW2/GW3)."

requirements-completed: [TODO-AVAIL-FLAGS, PHASE10-CRITERIA]

coverage:
  - id: D1
    description: "data/availability.py end-to-end: provider registry, gw_deadlines, resolve_as_of's two-boundary as-of-deadline selection, build/attach, wired through data/build_table.py -> features/engineer.py -> backtest/walk_forward.py's gate"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: integration
        ref: "python -m data.availability --force (real GW1-3 FPL-Core-Insights probe data)"
        status: pass
      - kind: integration
        ref: "python -m data.build_table (no [availability] skipped)"
        status: pass
      - kind: integration
        ref: "python -m features.engineer (av_chance_pct present, no rolled variant)"
        status: pass
      - kind: integration
        ref: "backtest/walk_forward.py --tag t1_av_off / t1_av_on -- opposite availability_flags states recorded, both produce a model+chips integer"
        status: pass
    human_judgment: false
  - id: D2
    description: "As-of-deadline leakage rule, D-10 NaN fallback, raw-not-rolled family classification, and the 11-key default-off flag registry, each locked by a named passing test"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: unit
        ref: "tests/test_availability.py::test_every_source_row_predates_its_gw_deadline"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_missing_snapshot_degrades_to_nan_not_raise"
        status: pass
      - kind: unit
        ref: "tests/test_leakage.py::test_availability_features_are_raw_context_not_rolled"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py::test_experiments_registry_default_off"
        status: pass
    human_judgment: false
  - id: D3
    description: "data/snapshot.py captures chance_of_playing_this_round, news, news_added from today onward"
    requirement: "TODO-AVAIL-FLAGS"
    verification:
      - kind: unit
        ref: "tests/test_availability.py::test_snapshot_frame_carries_new_availability_columns"
        status: pass
      - kind: unit
        ref: "tests/test_availability.py::test_take_snapshot_persists_new_columns_end_to_end"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every Phase 10 adoption criterion, including D-02's exact Spearman trigger, written to IMPROVEMENTS.md before any adoption-deciding run"
    requirement: "PHASE10-CRITERIA"
    verification:
      - kind: other
        ref: "grep -c 'Phase G' IMPROVEMENTS.md; token-presence + pending-count script (see plan 10-01 Task 3 verify block)"
        status: pass
    human_judgment: false

duration: 42min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 01: Availability Spine Tracer + Criteria Lock Summary

**One `av_chance_pct` availability column proven end-to-end (real FPL-Core-Insights GW1-3 probe data -> as-of-deadline resolver -> features.parquet -> the experiment gate -> a completed walk-forward run), plus every Phase 10 adoption criterion locked into IMPROVEMENTS.md before any measuring run.**

## Performance

- **Duration:** 42 min
- **Tasks:** 3
- **Files modified:** 10 (2 created, 8 modified)

## Accomplishments

- Built `data/availability.py`: a genuinely new THIRD leakage-safe feature family (point-in-time snapshot, as-of-deadline resolution) distinct from `ROLL_STATS` (match outcomes) and `CONTEXT_COLS`'s static-per-fixture members. Provider registry (`daily_snapshot`, `fpl_core_insights`), `gw_deadlines()` derived offline from `player_gw.parquet`, `resolve_as_of()`'s two-condition selection (predates the derived deadline AND every kickoff that gameweek -- the postponement guard), `_require_columns` failing loudly on a schema break (V5 / T-10-01-01).
- Probed FPL-Core-Insights live (GitHub API + raw CSV) before designing against it, per 10-RESEARCH.md Pitfall 2. Confirmed `id` is the season's FPL element id (cross-checked `id=1` == Raya against `data/processed/id_map.parquet` for season 2025-26) and `chance_of_playing_next_round` is present with real values (e.g. Gabriel: 0.0, "Thigh injury"; Saliba: 75.0, "Ankle injury - 75% chance of playing").
- Wired `av_chance_pct` through the full pipeline: `data/build_table.py`'s fourth optional-enrichment block, `features/engineer.py`'s `CONTEXT_COLS` (never `ROLL_STATS`), `backtest/walk_forward.py::apply_experiment_feature_gating`'s new `av_*` drop branch keyed on `availability_flags`.
- Extended `data/snapshot.py`'s daily capture with `chance_of_playing_this_round`, `news`, `news_added` -- accruing from today so no later plan starts from zero history.
- Locked every Phase 10 adoption criterion (primary >=2,280 bar, D-09's dual +25pt/+0.03-Spearman availability criterion, D-02's exact 0.500 news-sentiment trigger, D-15's bracket cheap gate, D-11 split verdicts, D-13/D-19 compute budgets, D-10's flip-only-after-fallback-test rule) into `IMPROVEMENTS.md`'s new `## Phase G` section, plus the nine pending experiment-flag rows and the per-source provenance/access-risk table.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end tracer -- one availability column reaches the harness** - `4ef8e1f` (feat)
2. **Task 2: Extend daily capture, lock leakage/fallback/registry contracts (TDD)** - `ba849a2` (test)
3. **Task 3: Write Phase G declared criteria to IMPROVEMENTS.md** - `f417eaa` (docs)

**Plan metadata:** (this commit, following)

## Files Created/Modified

- `data/availability.py` - Provider registry, `gw_deadlines`, `resolve_as_of`, `build`/`load_availability`/`attach`/`main`, `_require_columns`
- `tests/test_availability.py` - 11 tests: extended-capture columns, `_require_columns`' named error, `resolve_as_of`'s two boundaries, D-10 NaN fallback, the provider-invariant test, raw-not-rolled companion check
- `config.py` - `AVAILABILITY_COLS = ["av_chance_pct"]`, `EXPERIMENTS["availability_flags"] = False` (11th key)
- `features/engineer.py` - `AVAILABILITY_COLS` appended to `CONTEXT_COLS`
- `data/build_table.py` - fourth optional-enrichment try/except block (`avail_mod.attach`)
- `backtest/walk_forward.py` - `av_*` drop branch in `apply_experiment_feature_gating`, docstring updated
- `data/snapshot.py` - `_ELEMENT_COLS` +3 fields, numeric coercion for `chance_of_playing_this_round`
- `tests/test_leakage.py` - `test_availability_features_are_raw_context_not_rolled`
- `tests/test_experiments.py` - `availability_flags` added to `_EXPERIMENT_KEYS` (11 total); fixed a pre-existing E402 mid-file import while touching this file's import block
- `IMPROVEMENTS.md` - `## Phase G` section (declared criteria, nine-row pending results table, provenance table, unverified-priors note)

## Probe Results (recorded per plan's `<output>` contract)

**FPL-Core-Insights `playerstats.csv` verbatim column list** (GW1, 2025-2026, probed 2026-09-10 via `https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/data/2025-2026/By%20Gameweek/GW1/playerstats.csv`):

```
id,status,chance_of_playing_next_round,chance_of_playing_this_round,now_cost,now_cost_rank,now_cost_rank_type,cost_change_event,cost_change_event_fall,cost_change_start,cost_change_start_fall,selected_by_percent,selected_rank,selected_rank_type,total_points,event_points,points_per_game,points_per_game_rank,points_per_game_rank_type,bonus,bps,form,form_rank,form_rank_type,value_form,value_season,dreamteam_count,transfers_in,transfers_in_event,transfers_out,transfers_out_event,ep_next,ep_this,expected_goals,expected_assists,expected_goal_involvements,expected_goals_conceded,expected_goals_per_90,expected_assists_per_90,expected_goal_involvements_per_90,expected_goals_conceded_per_90,influence,influence_rank,influence_rank_type,creativity,creativity_rank,creativity_rank_type,threat,threat_rank,threat_rank_type,ict_index,ict_index_rank,ict_index_rank_type,corners_and_indirect_freekicks_order,direct_freekicks_order,penalties_order,gw,set_piece_threat,first_name,second_name,web_name,news,news_added,minutes,goals_scored,assists,clean_sheets,goals_conceded,own_goals,penalties_saved,penalties_missed,yellow_cards,red_cards,saves,starts,defensive_contribution,corners_and_indirect_freekicks_text,direct_freekicks_text,penalties_text,saves_per_90,clean_sheets_per_90,goals_conceded_per_90,starts_per_90,defensive_contribution_per_90,tackles,clearances_blocks_interceptions,recoveries
```

`chance_of_playing_next_round` maps directly onto the derived `av_chance_pct` column; no mapping had to be invented.

**Measured `av_chance_pct` join coverage:**
- Standalone `python -m data.availability --force` (dedup keys against `player_gw.parquet`): **11.1%** (28,083 resolved rows from 1 active source -- `fpl_core_insights`; `daily_snapshot` rows exist but resolve to zero rows since `player_gw.parquet` has no 2026-27 rows yet).
- `python -m data.build_table`'s own `attach()` print (row-level, includes DGW duplicate rows): **10.8%**.
- Because only GW1-3 of 2025-26 were probed and D-05's freeze-at-gameweek-end rule means a GW-N file is only eligible from GW N+1 onward, coverage in this tracer comes entirely from the two usable offsets (GW1->GW2, GW2->GW3) carried forward as the "last known" value for every later gameweek in the season with no fresher probed data -- an accurate reflection of a 3-gameweek probe, not a bug. 10-06's full 38-gameweek vendoring will close this.

**Two tagged `model+chips` figures** (`backtest.walk_forward --seasons 2025-26 --replicas 1`):
- `wf_t1_av_off` (`availability_flags: false`): **model+chips = 2172**
- `wf_t1_av_on` (`availability_flags: true`): **model+chips = 2172**

Identical on this single-season/single-replica tracer run -- expected: one low-signal column with 10.8% coverage on a deterministic LightGBM fit is not expected to move `model+chips` measurably at this stage. The gate itself is proven correct (`av_chance_pct` present with the flag on, absent with it off, 27,419 non-null rows) independent of whether this particular number moves; a real adoption verdict is plan 10-08's job, over the full 6-season harness against the D-09 dual criterion recorded below.

**D-02 number locked in `IMPROVEMENTS.md`:** pooled played-only `spearman_xp_med` **< 0.500** (after both Tier-1 experiments) triggers building the news-sentiment experiment; **>= 0.500** is recorded not-triggered. The 0.383 -> 0.579 arithmetic midpoint (**0.481**) is on record alongside it for context.

## Decisions Made

- `fpl_core_insights` provider directory layout is `<base>/<season-as-in-source-repo>/GW<n>_playerstats.csv` (flat), not a full mirror of the source repo's tree -- documented in `data/availability.py`'s module docstring since 10-06 (the committed vendoring plan) has not run yet and this plan owns the choice.
- `resolve_as_of` implemented as an explicit per-(season, gw) loop with `cutoff = min(deadline_ts, kickoff_max)` rather than `pandas.merge_asof`, since the two-condition rule reads directly off the loop body and is what the tests assert against (`grep -c "min"` acceptance criterion).
- `daily_snapshot` provider rows are tagged `season = config.CURRENT_SEASON`; correctly contribute zero joined rows this run since `player_gw.parquet` has no 2026-27 rows yet (`DATA_SEASONS` drops it) -- not a bug, matches the plan's "Correction to D-05's optional" note.

## Deviations from Plan

None — plan executed exactly as written. The `data.availability --force` CLI additionally prints its own `[availability] joined; coverage` line (computed against `player_gw.parquet`'s keys) so the plan's own `<verify>` block's first command demonstrates real join coverage without requiring `data.build_table` to run first — an implementation detail within Task 1's own `<action>` discretion, not a deviation from anything specified.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `data/availability.py`'s provider registry, `resolve_as_of`, and the `CONTEXT_COLS`/gate wiring are the foundation plan 10-04 (fallback hardening) and 10-06 (FPL-Core-Insights committed vendoring) build directly on top of.
- Plan 10-06 is a hard prerequisite of 10-08 (the D-09 adoption-deciding run) per this plan's "Correction to D-05's optional" note -- 2025-26 walk-forward coverage requires the vendored backfill, not our own daily snapshots.
- `IMPROVEMENTS.md`'s `## Phase G` declared-criteria block is now in place for every later Phase 10 plan (10-02 through 10-16) to measure against and fill in.
- No blockers.

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*

## Self-Check: PASSED

- FOUND: data/availability.py
- FOUND: tests/test_availability.py
- FOUND: .planning/phases/10-xp-experiment-follow-ups/10-01-SUMMARY.md
- FOUND: commit 4ef8e1f (Task 1)
- FOUND: commit ba849a2 (Task 2)
- FOUND: commit f417eaa (Task 3)
- Re-ran repo-wide `python -m pytest -q`: 246 passed, 1 skipped, 0 failed
- Re-ran `ruff check .`: all checks passed
- Re-ran plan-level `<verification>` checks: features.parquet carries `av_chance_pct` with no rolled variant; both tagged wf_t1_av_off.json/wf_t1_av_on.json exist recording opposite `availability_flags` states; `config.EXPERIMENTS` has 11 keys, all False; `IMPROVEMENTS.md` `## Phase G` exists with nine pending flag rows and all Phase A-F anchors intact
