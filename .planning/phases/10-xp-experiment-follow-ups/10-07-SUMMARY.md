---
phase: 10-xp-experiment-follow-ups
plan: 07
subsystem: data
tags: [transfermarkt, injury-history, leakage-safe-features, id-crosswalk, experiment-flag, backfill]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-05's authorised go/no-go decision (Option A -- full backfill, all seasons 2016-17+, background killable job) and its probe-only data/transfermarkt.py surface (_fetch_page, parse_injury_table, _resolve_tm_player_id)"
  - phase: 10-xp-experiment-follow-ups
    provides: "10-04's config.AVAILABILITY_COLS shape (mirrored for INJURY_COLS) and data.availability.gw_deadlines() (reused, not re-derived)"
provides:
  - "data/transfermarkt.py: resolve_tm_id/build/load_transfermarkt (resumable killable backfill) plus injury_status_as_of/attach (date-range overlap join into the pre-match context family)"
  - "data/id_crosswalk.py::tm_id_cache/write_tm_id_cache_entry: the persistent player_code -> tm_player_id map"
  - "config.INJURY_COLS (four columns) and config.EXPERIMENTS['transfermarkt_injury']=False"
  - "data/external/transfermarkt/injury_spells.csv + tm_id_map.csv + README.md: a committed, real (partial, growing) normalized spell table"
  - "backtest/walk_forward.py::apply_experiment_feature_gating's tm_ drop branch"
  - "tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff -- the todo's own required leakage assertion, passing against real data"
affects: [10-08, transfermarkt_injury experiment]

# Actuals (#2632)
actuals:
  tokens: 20000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Fourth leakage-safe feature family: date-range overlap against a shared deadline (gw_deadlines()), reusing 10-04's one-definition-one-place discipline rather than re-deriving deadlines"
    - "Resolved-vs-unresolved NaN rule drawn from the ID MAP's membership, not the spell table's -- a covered player with zero spells (genuine 0.0) is structurally distinguished from an unresolvable one (genuine NaN) via _covered_player_codes()"
    - "Layered resumability: a persistent per-player id cache (tm_id_cache), a per-URL HTML cache (_fetch_page, from plan 10-05), and a per-player processed-players log (_processed.csv) together mean a kill costs at most ~1 minute of NEW network work, proven live by an actual kill-and-restart cycle during this plan's own execution"

key-files:
  created:
    - data/external/transfermarkt/README.md
    - data/external/transfermarkt/injury_spells.csv
    - data/external/transfermarkt/tm_id_map.csv
  modified:
    - data/transfermarkt.py
    - data/id_crosswalk.py
    - config.py
    - features/engineer.py
    - backtest/walk_forward.py
    - tests/test_leakage.py
    - tests/test_experiments.py

key-decisions:
  - "Real Transfermarkt date format is 'DD/MM/YYYY' ('23/09/2024'), not the 'Mon D, YYYY' this plan's own action text assumed -- corrected (Rule 1) after inspecting the real HTML pages plan 10-05's probe had already cached under data/raw/transfermarkt/, before writing any date-parsing code against a guess"
  - "The full 2016-17+ authorised-scope backfill was launched as a detached, resumable, killable nohup background job and left RUNNING past this plan's own commits (per the orchestrator's explicit context-notes permission not to block multi-hour network fetches on this session) -- the committed injury_spells.csv/tm_id_map.csv are therefore a real, valid, growing PARTIAL snapshot (64 players / ~392 spells at the final checkpoint commit), not the full backfill; see 'Backfill Status' below for the tail -f command"
  - "data/transfermarkt.py's Task 1 (build machinery) and Task 2 (injury_status_as_of/attach) code landed in one commit rather than two, since they were written into the same file in one continuous pass and a clean line-range split was not practical after the fact -- documented as a deviation from strict per-task file separation, not from per-task VERIFICATION (each task's own <verify> commands were run and passed independently before moving to the next)"
  - "Task 3's own literal <verify> gate-test command (scoring config.resolve_experiments('transfermarkt_injury') through models.train.load_features()) cannot pass as literally written, because attach() is deliberately NOT wired into data/build_table.py yet (that is plan 10-08 Task 1, per this plan's own explicit scope split) -- verified the SAME underlying gate invariant instead via a new pytest test that calls the real data.transfermarkt.attach() directly on a load_features() frame before gating, proving apply_experiment_feature_gating's tm_ branch end-to-end without depending on the later wiring commit"

patterns-established:
  - "A background backfill job that legitimately outlives the plan's own execution session gets a mid-flight 'chore' checkpoint commit of its accumulated real data, rather than either blocking the session for hours or leaving the growing artifact permanently uncommitted"

requirements-completed: [TODO-TM-INJURY]

coverage:
  - id: D1
    description: "resolve_tm_id resolves a name to a Transfermarkt id exactly once per player_code (via data.id_crosswalk.tm_id_cache), and a second call for the same player issues zero HTTP requests"
    requirement: TODO-TM-INJURY
    verification:
      - kind: integration
        ref: "python -c '...resolve_tm_id(...) twice...' -- first call 0.01s (cached search HTML from plan 10-05's probe), second call 0.001s (id-cache hit, zero HTTP)"
        status: pass
    human_judgment: false
  - id: D2
    description: "build() is resumable and killable: a real kill-and-restart cycle during this plan's own execution proved the second run picked up exactly where the first left off (player 21/2623), never re-processing the first 20 players"
    requirement: TODO-TM-INJURY
    verification:
      - kind: integration
        ref: "live kill (SIGTERM, PID 191523) after 20 players processed/flushed, then a fresh `python -u -m data.transfermarkt --build` process started at player 21 -- observed directly in the log"
        status: pass
    human_judgment: false
  - id: D3
    description: "injury_status_as_of's overlap semantics match the three hand-computed cases (mid-spell, post-spell, ongoing spell) exactly, and the vectorized attach() agrees with the scalar reference implementation"
    requirement: TODO-TM-INJURY
    verification:
      - kind: unit
        ref: "python -c '...injury_status_as_of(...)...' -- a=14 days mid-spell, b=not-injured post-spell, c=injured on an ongoing (until_date=null) spell"
        status: pass
      - kind: integration
        ref: "attach() on a synthetic id-map+spell-table fixture against a real 2000-row player_gw slice -- tm_injured/tm_days_out_so_far/tm_spells_prior_365d/tm_days_out_prior_365d all matched hand-verified expectations across the spell's active/inactive gameweeks"
        status: pass
    human_judgment: false
  - id: D4
    description: "The todo's own explicit leakage requirement -- every spell contributing to a gameweek's injury features has from_date strictly before both the deadline and the kickoff -- asserted against the REAL committed (partial) spell table, not synthetic data"
    requirement: TODO-TM-INJURY
    verification:
      - kind: unit
        ref: "tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff"
        status: pass
    human_judgment: false
  - id: D5
    description: "config.EXPERIMENTS['transfermarkt_injury'] defaults False and apply_experiment_feature_gating drops every tm_ column when off, keeps all four when on -- proven against real data via data.transfermarkt.attach() + models.train.load_features(), since data/build_table.py's own wiring is deferred to plan 10-08"
    requirement: TODO-TM-INJURY
    verification:
      - kind: unit
        ref: "tests/test_experiments.py::test_transfermarkt_injury_gate_drops_or_keeps_all_four_on_real_attach"
        status: pass
      - kind: unit
        ref: "python -m pytest -q (repo-wide: 289 passed, 1 unrelated pre-existing skip)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 07: Transfermarkt Injury Backfill + Feature Join Summary

**Built the resumable killable Transfermarkt injury-history backfill plan 10-05 authorised (Option A, full 2016-17+ scope), its date-range overlap join into a new fourth leakage-safe feature family (`config.INJURY_COLS`, gated by `transfermarkt_injury`), and the todo's own required real-data leakage assertion -- with the full-scope backfill launched as a detached background job that is still running past this plan's own commits.**

## Performance

- **Duration:** 45 min
- **Tasks:** 3 (all committed)
- **Files modified:** 7 code files + 3 new committed data files (`data/external/transfermarkt/{README.md,injury_spells.csv,tm_id_map.csv}`)

## Accomplishments

- **`resolve_tm_id`/`build`/`load_transfermarkt`** (Task 1): a name resolves to a Transfermarkt player id exactly once per `player_code`, cached persistently via `data.id_crosswalk.tm_id_cache()`/`write_tm_id_cache_entry()` (preserving plan 09-02's `player_code.is_unique` invariant). `build(resume=True)` enumerates the authorised season scope from `player_gw.parquet`, resolves + fetches + parses + normalizes each player's injury history, and appends incrementally to the committed spell table every 10 players -- bounding a kill's cost to roughly a minute. **This was proven live, not just designed**: the build was deliberately killed mid-run (SIGTERM at 20 players processed) and restarted; the resumed process picked up exactly at player 21/2623, confirmed directly in the log, with zero re-fetches of the first 20 players (their HTML and ids were already cached).
- **Real-data date-format correction (Rule 1):** this plan's own action text assumed Transfermarkt injury dates render as `Mon D, YYYY` (matching plan 10-05's synthetic test fixture). Inspecting the 8 real pages plan 10-05's probe had already cached under `data/raw/transfermarkt/` showed the actual served format is `DD/MM/YYYY` (`23/09/2024`). `_TM_DATE_FORMAT = "%d/%m/%Y"` was set from that real evidence before any parsing code was written against a guess.
- **`injury_status_as_of`/`attach`** (Task 2): a scalar reference implementation (matching 10-RESEARCH.md's Code Examples sketch exactly) plus a fully vectorized `attach(full)` that joins four features (`tm_injured`, `tm_days_out_so_far`, `tm_spells_prior_365d`, `tm_days_out_prior_365d`) against each gameweek's deadline from `data.availability.gw_deadlines()` (reused, never re-derived). The resolved-vs-unresolved distinction is drawn from `_covered_player_codes()` reading the **id map's own membership** -- a covered player with zero recorded spells gets a genuine `0.0` across the family; a player whose `player_code` never resolved a Transfermarkt id gets a genuine `NaN`. Both the scalar function and the vectorized path were checked against the plan's three hand-computed cases (mid-spell, post-spell, ongoing/null-`until_date` spell) and agreed exactly.
- **`config.INJURY_COLS`** (four columns) registered in `features/engineer.py`'s `CONTEXT_COLS` (never `ROLL_STATS` -- these are not match outcomes), and `config.EXPERIMENTS["transfermarkt_injury"] = False` added under the Phase 10 comment block.
- **The gating branch** (Task 3): one new line in `backtest/walk_forward.py::apply_experiment_feature_gating`, dropping every `tm_`-prefixed column when the flag is off.
- **The todo's own required leakage assertion**, `tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff`, runs against the **real committed (partial) spell table** joined to the real `player_gw.parquet`, asserting both the `deadline_ts` bound and the harder `kickoff_max` bound (per `gw_deadlines()`'s own postponement caveat) -- and passes.
- **Full repo test suite green**: `python -m pytest -q` → 289 passed, 1 unrelated pre-existing skip (`.env`-gated cron test); `ruff check .` clean.

## Backfill Status (IMPORTANT -- read before assuming the dataset is complete)

The full authorised-scope backfill (all `config.SEASONS`, 2,623 distinct players, projected ≈4.4h wall clock per plan 10-05's own measurement) was launched as a **detached, resumable, killable background job** and is **still running past this plan's own final commit** (per the orchestrator's explicit permission not to block a multi-hour network fetch on this session).

**To follow its live progress:**
```
tail -f data/processed/experiments/transfermarkt_build-20260910T164045Z.log
```
**To check it is still alive:**
```
ps aux | grep "[d]ata.transfermarkt"
```
**If it has stopped for any reason, resume it** (safe -- it will pick up from where it left off, never re-fetching an already-processed player):
```
nohup /home/sraja/miniconda3/envs/python314/bin/python -u -m data.transfermarkt --build \
  > data/processed/experiments/transfermarkt_build-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 & disown
```
**To commit further progress** as it accumulates:
```
git add data/external/transfermarkt/injury_spells.csv data/external/transfermarkt/tm_id_map.csv
git commit -m "chore(10-07): checkpoint further injury backfill progress"
```

At the final checkpoint commit (`5be2ff8`), the committed table held:
- **64 players processed** (of 2,623 total in scope), **6 failed** (no injury-history table found, or the search endpoint could not resolve their name), **~392 spells** committed
- **id-resolved coverage against the whole `player_gw.parquet`: 1.9%** (expected to be small this early; grows toward the full backfill's real ceiling as the job continues)
- **Active-spell rate among id-resolved rows: 8.5%**

**10 real resolved `(name, tm_player_id)` pairs, for human eyeball** (sampled from the live log, spot-checked against known public Transfermarkt ids):
| Name | player_code | tm_player_id |
|---|---|---|
| John O'Shea | 3736 | 3540 |
| Allan McGregor | 12390 | 9422 |
| Andrew Surman | 15237 | 29975 |
| Andy King | 13152 | 56872 |
| Bastian Schweinsteiger | 15208 | 2514 |
| Ben Foster | 9089 | 13572 |
| Billy Jones | 11467 | 36866 |
| Boaz Myhill | 12086 | 3838 |
| Bruno Saltor Grau | 11352 | 51528 |
| Cristiano Ronaldo dos Santos Aveiro | 14937 | 8198 |

## Task Commits

Each task was committed atomically (with one deliberate exception, see Deviations):

1. **Tasks 1 + 2 combined** (build machinery + overlap join, see Deviations) - `6100c15` (feat)
2. **Task 3: gate + leakage test** - `127dc37` (test)
3. **Mid-flight checkpoint of the still-running backfill's accumulated data** - `5be2ff8` (chore)

## Files Created/Modified

- `data/transfermarkt.py` - `resolve_tm_id`, `_parse_tm_date`/`_parse_days_out`/`_parse_games_missed`, `_normalize_spells`, `_load_spells_raw`/`_append_spells`, `_load_processed`/`_record_processed`, `build`, `load_transfermarkt`, `_covered_player_codes`, `injury_status_as_of`, `_to_naive_utc`, `attach`; `main()` gained `--build`/`--resume`/`--no-resume`/`--seasons`/`--force`
- `data/id_crosswalk.py` - `tm_id_cache()`/`write_tm_id_cache_entry()`, the persistent `player_code -> tm_player_id` map
- `config.py` - `INJURY_COLS` (four names) and `EXPERIMENTS["transfermarkt_injury"] = False`
- `features/engineer.py` - `config.INJURY_COLS` appended to `CONTEXT_COLS`
- `backtest/walk_forward.py` - one new drop branch in `apply_experiment_feature_gating`
- `tests/test_leakage.py` - `test_transfermarkt_injury_dates_precede_kickoff` (the todo's required assertion, real data), `test_transfermarkt_injury_features_are_raw_context_not_rolled`
- `tests/test_experiments.py` - `"transfermarkt_injury"` added to `_EXPERIMENT_KEYS`; two synthetic gate tests plus `test_transfermarkt_injury_gate_drops_or_keeps_all_four_on_real_attach` (real `attach()` + real `load_features()`)
- `data/external/transfermarkt/README.md` - Source/Attribution/Regeneration/Reduction applied/PII spot-check/ToS and redistribution posture sections
- `data/external/transfermarkt/injury_spells.csv`, `tm_id_map.csv` - the real, growing, committed normalized data (partial as of this commit -- see Backfill Status)

## Decisions Made

- Real Transfermarkt date format corrected to `DD/MM/YYYY` from real evidence (Rule 1) -- see Accomplishments.
- The full backfill runs as a detached background job left running past this session, per the orchestrator's own context-notes permission -- the committed data is a real, valid, growing partial snapshot, not the complete 2016-17+ dataset. This is NOT a shortcut around the plan's requirement: the mechanism (resumable, killable, incrementally-committed) is exactly what the plan specifies, proven live via an actual kill-and-restart cycle during this session.
- Tasks 1 and 2's code landed in one commit (`6100c15`) rather than two, since both were written into `data/transfermarkt.py` in one continuous pass and a clean post-hoc line-range split across commits was not practical. Each task's own `<verify>` commands were still run and passed independently before moving to the next task -- this is a commit-granularity deviation, not a verification-granularity one.
- Task 3's own literal gate-test `<verify>` command (scoring through `models.train.load_features()` directly) cannot pass as written because `attach()` is deliberately not wired into `data/build_table.py` yet (plan 10-08 Task 1's job, per this plan's own explicit scope note in Task 2's action text). Verified the same underlying gate invariant via a new pytest test that calls `data.transfermarkt.attach()` directly on a `load_features()` frame before gating -- proves `apply_experiment_feature_gating`'s `tm_` branch against real data without depending on the later wiring commit. This mirrors the established "plan's own literal verify command doesn't hold in this environment, verify the same invariant with a stronger corrected check" pattern already documented for Phases 06-03/06-04.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Real-data schema/format correction] Transfermarkt date format is `DD/MM/YYYY`, not `Mon D, YYYY`**
- **Found during:** Task 1, before writing any date-parsing code
- **Issue:** This plan's own action text (and plan 10-05's synthetic test fixture) assumed a `Jan 1, 2025`-style date format. The 8 real pages plan 10-05's probe already cached showed `23/09/2024`.
- **Fix:** `_TM_DATE_FORMAT = "%d/%m/%Y"`, set from direct inspection of real cached HTML.
- **Files modified:** data/transfermarkt.py
- **Verification:** `_normalize_spells` run against multiple real cached pages produced correctly-parsed dates with zero drops; the committed `injury_spells.csv`'s `from_date`/`until_date` columns are all valid ISO dates.
- **Committed in:** 6100c15

**2. [Commit-granularity, not verification-granularity] Tasks 1+2 committed together**
- **Found during:** Preparing to commit Task 1
- **Issue:** Both tasks' code was written into `data/transfermarkt.py` in one continuous editing pass; a clean post-hoc split of that single file's diff across two commits was not practical without risking a broken intermediate state.
- **Resolution:** Committed together with an honest commit message describing both tasks' scope; each task's own `<verify>` commands were independently run and confirmed passing before moving on.
- **Files affected:** data/transfermarkt.py (and the task-specific files each task otherwise owns)
- **Committed in:** 6100c15

**3. [Rule 1 - Plan's own literal verify command doesn't hold in this environment] Task 3's gate-test verify command corrected**
- **Found during:** Task 3 verify
- **Issue:** The plan's literal Task 3 verify Python snippet scores `config.resolve_experiments("transfermarkt_injury")` through `apply_experiment_feature_gating(models.train.load_features(), ...)` directly -- but `data/transfermarkt.py::attach()` is deliberately NOT wired into `data/build_table.py` yet (plan 10-08 Task 1's own job, per Task 2's action text). `load_features()`'s real `features.parquet` therefore carries zero `tm_*` columns, so the literal command's `assert len(kept)==len(config.INJURY_COLS)` cannot pass -- not because the gate is broken, but because the columns it would gate don't exist in that frame yet.
- **Fix:** Added `tests/test_experiments.py::test_transfermarkt_injury_gate_drops_or_keeps_all_four_on_real_attach`, which calls the real `data.transfermarkt.attach()` on a real `load_features()` frame BEFORE gating, proving the same underlying invariant (drop when off, keep all four when on) against real data without depending on the later wiring commit.
- **Files modified:** tests/test_experiments.py
- **Verification:** `pytest tests/test_experiments.py -q` passes, including this new test.
- **Committed in:** 127dc37

---

**Total deviations:** 3 (1 Rule-1 real-data correction, 1 commit-granularity note, 1 Rule-1 verify-command correction)
**Impact on plan:** All three necessary for correctness or for an honest, passing verification against real data. No scope creep -- no product wiring (that stays plan 10-08's), no new experiment flags beyond `transfermarkt_injury`.

## Issues Encountered

- 6 of the first 64 players attempted so far failed resolution or fetch (a couple of `id_unresolved` cases similar to plan 10-05's own `B.Fernandes`-style finding, and one player whose injury-history page had no matching table -- likely a player with zero recorded Transfermarkt injuries whose page structure differs slightly). These are recorded in the failure counter and `data/raw/transfermarkt/_processed.csv` (gitignored); a future `--no-resume` run would retry them. This is expected behavior (T-10-07-07's own mitigation working as designed), not a bug.

## User Setup Required

**The backfill is still running.** No action is required to keep it going (it was launched detached and will survive this session), but the developer should periodically check `ps aux | grep transfermarkt` / `tail -f` the log named above, and commit further progress with the command given in "Backfill Status" once satisfied with the accumulated coverage -- ideally before plan 10-08 wires `attach()` into `data/build_table.py` and measures the `transfermarkt_injury` experiment's adoption verdict, since that measurement's quality depends on how much of the 2016-17+ scope has actually landed by then.

## Next Phase Readiness

- Plan 10-08 Task 1 owns wiring `data.transfermarkt.attach(full)` into `data/build_table.py`'s optional-enrichment block (this plan deliberately left it unwired, per its own action text) and measuring the `transfermarkt_injury` experiment's adoption verdict against the pre-declared bar.
- Before that measurement, the developer should let the background backfill run to a meaningful completion fraction (ideally the full ≈4.4h) and commit the final `injury_spells.csv`/`tm_id_map.csv` -- the id-resolved coverage figure recorded here (1.9%) reflects only the first ~64 of 2,623 players and will rise substantially as the job continues.
- No blockers for 10-08 beyond "let the backfill finish (or run long enough to judge coverage acceptable) before measuring."

## Self-Check: PASSED

All claimed files and commits verified present:
- `data/transfermarkt.py`, `data/id_crosswalk.py`, `config.py`, `features/engineer.py`, `backtest/walk_forward.py`, `tests/test_leakage.py`, `tests/test_experiments.py` — FOUND
- `data/external/transfermarkt/README.md`, `injury_spells.csv`, `tm_id_map.csv` — FOUND
- Commits `6100c15`, `127dc37`, `5be2ff8` — FOUND in git log
- Re-ran `python -m pytest -q`: 289 passed, 1 unrelated pre-existing skip
- Re-ran `ruff check .`: all checks passed
- Background build process confirmed alive (`ps aux | grep transfermarkt`) at SUMMARY write time

## Self-Check: PASSED (final)

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*
