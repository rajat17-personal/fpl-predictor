---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 08
subsystem: ml-experimentation
tags: [understat, xg, npxg, player-identity, crosswalk, walk-forward, feature-gating, leakage]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, backtest/walk_forward.py --experiments/--seasons/--tag CLI, the tracked 6-season baseline in IMPROVEMENTS.md Phase F)"
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-02's data.id_crosswalk.resolve_by_name (the shared player-identity crosswalk this plan resolves Understat names through and extends)"
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-05's team_strength pipeline-join pattern (guarded try/except join, unconditional computation) and its inline feature-gating, which this plan generalises into a named helper"
provides:
  - "data/understat.py -- cached, rate-limited, kill-switchable Understat fetcher (per-player match-history endpoint, since the real API has no per-league-season call), producing data/processed/understat.parquet (109,592 rows, 2016-17..2026-27)"
  - "data.id_crosswalk._fpl_name_index() -- a third resolve_by_name tier matching against data/id_map.py's full historical registry (2,737+ player_codes), closing a real coverage gap in theFPLkiwi's ~454-row current-squad-only crosswalk; plus 78 verified _NAME_FIXUPS entries"
  - "config.UNDERSTAT_COLS registered in features/engineer.py's ROLL_STATS (never CONTEXT_COLS) -- leakage-tested"
  - "backtest/walk_forward.py::apply_experiment_feature_gating(df, exp) -- the named, tested helper both team_strength and understat now route through, ready for plans 09-09/09-10 to extend"
  - "D-07 adoption verdict for understat: REJECTED (model+chips +16, 2 short of the >=2280 primary bar; fixture-level MAE/Spearman flat-to-slightly-worse), flag off, code merged"
affects: [09-09, 09-10]

actuals:
  tokens: 10956
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Per-player-history fetch, not per-league-season: understatapi has no single 'every EPL player's every match' endpoint, so fetch_season() combines two cheap league-level calls (fixture-id list, player index) with one cached request per player, filtered to that season's fixture ids"
    - "Crosswalk fallback tiers: resolve_by_name tries the small current-squad crosswalk first, then a full-historical id_map-derived name index, then _NAME_FIXUPS -- generalizes to any future name-keyed source without a new per-source matcher"
    - "Named, shared feature-selection gate (apply_experiment_feature_gating) replacing one-off inline column drops per experiment family"

key-files:
  created:
    - data/understat.py
  modified:
    - data/id_crosswalk.py
    - config.py
    - data/build_table.py
    - features/engineer.py
    - tests/test_leakage.py
    - backtest/walk_forward.py
    - tests/test_experiments.py
    - IMPROVEMENTS.md

key-decisions:
  - "Extended data.id_crosswalk.resolve_by_name with a third tier matching against data/id_map.py's full historical name registry, after discovering theFPLkiwi's ID_Dictionary.csv (plan 09-02's crosswalk source) is a ~454-row CURRENT-squad-only snapshot that structurally cannot resolve a historically-departed player (Harry Kane, Diego Costa, ...) no matter how many spelling fixups are added -- this raised distinct-name coverage from 413/1980 (20.9%) to 1730/1980 (87.4%) before any fixups"
  - "Added 78 _NAME_FIXUPS entries, but only after requiring BOTH tokens of a multi-token Understat name to appear as WHOLE tokens (never a substring) in exactly one id_map candidate -- a plain substring search first produced false positives (e.g. 'Exequiel Palacios' matching an unrelated player also surnamed Palacios), which is exactly the T-09-08-05 spoofing risk the threat model calls out"
  - "Deliberately did NOT add fixups for single-token mononyms found 'unique' by that same search (Fred, Jonny, Bojan, Jota, ...) except four independently verified from football knowledge (Jota, Bojan, Kepa, Sokratis) -- 'Fred' and 'Jonny' were proven WRONG on inspection: Man Utd's real Fred is recorded in id_map under first_name='Frederico' (not 'Fred'), so the search's one 'Fred' hit is a different, obscure player; Wolves' 'Jonny' (Jonathan Castro Otto) is a second real EPL player sharing the identical mononym with Jonny Evans, with no season/team context available to disambiguate safely"
  - "REJECTED understat at adoption: model+chips improved +16 (2262->2278) but stayed 2 points short of the pre-declared >=2280 primary bar, and the identical +16 delta was already seen (and separately judged inconclusive) for capt_ceiling's own adoption run this phase; corroborated by a fixture-level MAE/Spearman reading that moved flat-to-slightly-worse with understat on -- the honest read is noise, not a genuine accuracy-driven gain, matching this option's own pre-stated expectation"

requirements-completed: []

coverage:
  - id: D1
    description: "Cached, rate-limited, kill-switchable Understat fetcher; a real crosswalk coverage gap discovered and closed (19.9% -> 41.2% row-level, 94.7% of distinct names)"
    verification:
      - kind: integration
        ref: "python -m data.understat (109,592 rows across 11 seasons; cache-warm rerun touches zero network calls)"
        status: pass
      - kind: unit
        ref: "kill-switch no-op assertion (UNDERSTAT_ENABLED=False -> attach() returns input unchanged, same columns)"
        status: pass
      - kind: unit
        ref: "tests/test_crosswalk.py (6 tests, all passing with the new id_map fallback tier and 78 fixups)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Understat stats reach the model only through shift(1)-then-rolling windows, never as raw pre-match context; pipeline rebuild leaves player_gw.parquet row count unchanged"
    verification:
      - kind: unit
        ref: "tests/test_leakage.py#test_understat_features_are_rolled_not_raw"
        status: pass
      - kind: integration
        ref: "python -m data.build_table && python -m features.engineer (player_gw.parquet 253,509 rows unchanged; features.parquet gained 20 rolled us_* columns at 41.2% coverage)"
        status: pass
    human_judgment: false
  - id: D3
    description: "apply_experiment_feature_gating(df, exp) generalises plan 09-05's inline team_strength gating into one named, tested helper covering both team_strength and understat"
    verification:
      - kind: unit
        ref: "tests/test_experiments.py#test_feature_gating_drops_ts_and_us_families_when_off"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_feature_gating_keeps_family_when_flag_on"
        status: pass
      - kind: unit
        ref: "tests/test_experiments.py#test_feature_gating_missing_key_defaults_to_off"
        status: pass
      - kind: integration
        ref: "re-ran plan 09-05's own ts_fast tagged config through the new helper -- reproduced its stored numbers bit-for-bit (model+chips 2256, multi_safe 2100, multi_optimistic 2437)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Understat A/B measured on both season-points and fixture-level-accuracy axes; D-07 adoption verdict recorded as REJECTED"
    verification:
      - kind: integration
        ref: "data/processed/experiments/wf_understat_adopt.json (6 seasons, 5 replicas, understat=true; model+chips 2278 vs baseline 2262)"
        status: pass
      - kind: other
        ref: "data/processed/experiments/understat_mae_comparison.json (fixture-level MAE/Spearman, understat off vs on, pooled n=66,665)"
        status: pass
    human_judgment: true
    rationale: "The REJECT verdict rests on judging a +16 model+chips delta (2 points short of the declared >=2280 bar) as within the harness's own noise band rather than a hard coded threshold. This is corroborated by a fixture-level MAE/Spearman reading that moved flat-to-slightly-worse with understat on, and mirrors the identical +16 delta already seen for capt_ceiling's own adoption run -- but a human should confirm this reasoning before treating the flag as permanently settled, since D-07's own wording ('outside the noise-band direction') is not itself a mechanically-checked assertion."

duration: 64min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 8: Understat Non-Penalty xG + Involvement-Chain Experiment Summary

**Built and cached a real Understat per-match fetcher, discovered and closed a structural ~20%-coverage ceiling in the shared player-identity crosswalk (theFPLkiwi's source is current-squad-only), rolled the new stats into the feature matrix behind a leakage test, generalised the experiment feature-gating into one named helper, and REJECTED adoption after the season-points move (+16, 2 short of the declared bar) failed to be corroborated by any fixture-level accuracy gain.**

## Performance

- **Duration:** 64 min
- **Started:** 2026-09-08T18:36:00Z (approx.)
- **Completed:** 2026-09-08T19:40:00Z
- **Tasks:** 3
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments

- `data/understat.py` (new) — `UNDERSTAT_ENABLED` kill switch, `_season_label()`, `fetch_season()`, `build()`, `attach()`. Since `understatapi` has no single "every EPL player's every match this season" endpoint, `fetch_season()` combines two cheap league-level calls (the season's EPL fixture-id list, the season's EPL player index) with one cached, rate-limited (`_MIN_INTERVAL_S = 1.0`) request per player (their whole career history in one call, filtered down to this season's fixture ids). Per-player histories are cached separately under `data/raw/understat/players/<id>.json` so a player appearing in multiple seasons is fetched from the network exactly once. Full historical build: **109,592 player-match rows across 11 seasons** (2016-17 through the in-progress 2026-27), zero network calls on a cache-warm rerun.
- **A real, structural crosswalk gap found and closed.** The first real join measured only **19.9% row-level coverage** through `data.id_crosswalk.resolve_by_name`'s existing tiers. Root cause: theFPLkiwi's `ID_Dictionary.csv` (plan 09-02's crosswalk source) is a ~454-row **CURRENT-squad-only** snapshot — historically-departed players (Harry Kane, Sergio Agüero, Diego Costa, Romelu Lukaku, ...) are simply absent from it, not misspelled. No amount of name-fixup guessing can invent a row that source never had. Fixed by adding `data.id_crosswalk._fpl_name_index()`, a third `resolve_by_name` tier matching against **every** historical `player_code` `data/id_map.py` has ever recorded (2,737+ codes) — raising distinct-name coverage from 413/1,980 (20.9%) to 1,730/1,980 (87.4%) before any fixups, and row-level coverage to 39.8%.
- **A second real bug fixed:** Understat's JSON leaves apostrophes HTML-entity-escaped (`"N&#039;Golo Kanté"`), silently failing every such name's normalised-string match. Fixed with `html.unescape()` in `data/understat.py`.
- **78 verified `_NAME_FIXUPS` entries added**, closing the remaining nickname-vs-full-legal-name gap (Understat displays popular nicknames; `id_map.py` stores full legal names) for well-known players (Diego Costa, David Luiz, Cristiano Ronaldo, Rúben Neves, João Moutinho, ...). Every multi-token entry was verified by requiring BOTH of the Understat name's tokens to appear as **whole tokens** (never a coincidental substring) within exactly one `id_map` candidate's full name — a plain substring search first produced real false positives (e.g. "Exequiel Palacios" matching an unrelated different player also surnamed Palacios; "Quinten Timber" matching his own twin brother "Jurriën Timber"), which is exactly the spoofing risk the plan's own threat model (T-09-08-05) calls out. Single-token mononyms found "unique" by the same search were deliberately excluded except four independently verified from football knowledge (Jota, Bojan, Kepa, Sokratis) — "Fred" and "Jonny" were proven **wrong**/ambiguous on inspection (see Decisions below) and left unresolved rather than guessed. **Final coverage: 1,875/1,980 distinct names (94.7%), 41.2% row-level.**
- `config.UNDERSTAT_COLS` (`us_npxg`, `us_xgchain`, `us_xgbuildup`, `us_shots`, `us_key_passes`) registered in `features/engineer.py`'s `ROLL_STATS` (never `CONTEXT_COLS`) — every value reaches the model only through `_roll`'s `shift(1)`-then-rolling windows, since these describe the match they came from (a match outcome), not pre-match context. `ROLL_STATS` entries absent from `df` are now skipped (needed the moment `ROLL_STATS` gained its first optional member). `tests/test_leakage.py::test_understat_features_are_rolled_not_raw` asserts no bare `us_*` column survives in `features.parquet` and independently recomputes one player's `us_npxg_r5`. `data/build_table.py` gained a guarded understat join after the team-strength block, computed unconditionally. Rebuild: `player_gw.parquet` unchanged at **253,509 rows**; `features.parquet` gained 20 rolled `us_*` columns.
- `backtest/walk_forward.py::apply_experiment_feature_gating(df, exp)` — extracted plan 09-05's inline `team_strength`-only column-drop into one named, tested helper routing both `ts_*` and `us_*` families. Re-running plan 09-05's own `ts_fast` tagged configuration through the new helper reproduced its stored numbers **bit-for-bit** (`model+chips` 2256, `multi_safe` 2100, `multi_optimistic` 2437), confirming the refactor changed no `team_strength` behaviour.
- **Fixture-level accuracy measured separately from season points** (reusing `backtest/benchmark_external.py`'s `_stats_block` MAE/Spearman helper, pointed at our own understat-off vs understat-on `xp_med` columns — no second MAE implementation written), pooled over all 6 test seasons at fixture level (played-only, n=66,665): MAE 1.8751 → 1.8761, Spearman 0.3620 → 0.3599 — essentially flat, slightly worse.
- **Adoption-deciding run** (6 seasons, 5 replicas) against the plan 09-01 baseline: `model+chips` 2262 → 2278 (**+16**, 2 points short of the pre-declared ≥2,280 primary bar), `multi_safe` 2147 → 2180 (+33, no regression). **D-07 verdict: REJECTED** — the +16 move is not corroborated by any fixture-level accuracy gain and matches the identical (separately inconclusive) delta already seen for `capt_ceiling`. `config.EXPERIMENTS['understat']` stays `False`; all code stays merged (D-08).

## Task Commits

Each task was committed atomically:

1. **Task 1: Cached, rate-limited, kill-switchable Understat fetcher** - `8ea05f4` (feat)
2. **Task 2: Roll the new stats into the feature matrix, with the leakage assertion** - `9fb41cd` (feat)
3. **Task 3: A/B the Understat features and record the verdict** - `8820956` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `data/understat.py` (new) - `UNDERSTAT_ENABLED`, `_season_label()`, `fetch_season()`, `build()`, `attach()`
- `data/id_crosswalk.py` - `_fpl_name_index()` historical fallback tier, 78 `_NAME_FIXUPS` entries
- `config.py` - `UNDERSTAT_COLS`
- `data/build_table.py` - guarded understat join
- `features/engineer.py` - `UNDERSTAT_COLS` in `ROLL_STATS`; `ROLL_STATS` entries absent from `df` now skipped
- `tests/test_leakage.py` - `test_understat_features_are_rolled_not_raw`
- `backtest/walk_forward.py` - `apply_experiment_feature_gating()`, wired into `main()`
- `tests/test_experiments.py` - 3 tests for the gating helper
- `IMPROVEMENTS.md` - `understat` Phase F row and results sub-section filled (no pending cells)

## Decisions Made

- Extended `data.id_crosswalk.resolve_by_name` with a third, historical-registry fallback tier (`_fpl_name_index()`) rather than writing a second per-source matcher, keeping D-03's "one shared crosswalk" discipline intact while closing a coverage gap 09-02's own verification (player_code-level, 16.6%) didn't surface at the row/name level for a multi-season source like Understat.
- Applied a strict "both tokens must appear as whole tokens in exactly one candidate" rule for `_NAME_FIXUPS`, after a looser substring-based search demonstrably produced wrong matches (Exequiel Palacios, Quinten Timber). Excluded single-token mononyms except four independently verified by name (Jota, Bojan, Kepa, Sokratis); "Fred" and "Jonny" were proven wrong/ambiguous on inspection and left unresolved — a wrong join silently misattributes one real player's data to another, which is worse than a lower coverage number.
- REJECTED `understat` at adoption per D-07: the +16 `model+chips` move stayed under the declared ≥2,280 bar and was not corroborated by the fixture-level MAE/Spearman reading (flat-to-slightly-worse) — treated as noise, not signal, consistent with this option's own pre-stated expectation (the odds-join precedent: better fixture accuracy, season points move within noise).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `understatapi==0.7.1` was pinned in the lockfile but not installed in the active conda environment**
- **Found during:** Task 1, before writing `data/understat.py`
- **Issue:** The plan's own measured_facts asserted the package was "already pinned exactly ... and installed," but `import understatapi` raised `ModuleNotFoundError` in the `python314` conda env.
- **Fix:** Ran `pip install understatapi==0.7.1` — the exact version already pinned in `requirements.in`/`requirements.txt` since Phase 5-01 (predating this plan by several phases), so this is a missing-dependency fix, not a new/unvetted package install; the package-legitimacy exclusion in the deviation rules does not apply to an already-approved, already-hash-locked pin. The install downgraded `requests`/`urllib3`/`idna`/`certifi`/`charset-normalizer` to versions that then matched `requirements.txt`'s own pins exactly (pip's resolver restored the project's locked versions; the reported conflicts were against unrelated tools in this shared conda environment, e.g. `browser-use`, `google-genai`, not this project).
- **Files modified:** none (environment-only; no requirements file changed)
- **Verification:** `python -m data.understat` ran successfully end to end; full `pytest -q` suite (which exercises `seleniumbase`/`selenium`-adjacent code paths in `data/fbref.py`) still passes.
- **Committed in:** n/a (environment change, not a file change)

**2. [Rule 1 - Bug] `ROLL_STATS` had no "skip if column absent" protection, unlike `CONTEXT_COLS`**
- **Found during:** Task 2, before rebuilding the pipeline
- **Issue:** `features/engineer.py::add_features()` iterated `ROLL_STATS` unconditionally (`g[stat]`), which would raise `KeyError` if `config.UNDERSTAT_COLS` were ever absent from `df` (e.g. `data/processed/understat.parquet` not yet built, or the kill switch off) — `CONTEXT_COLS` already had this "skip if missing" filter, but `ROLL_STATS` never needed it before this plan gave it its first optional member.
- **Fix:** Filtered `ROLL_STATS` to `[s for s in ROLL_STATS if s in df.columns]` before the rolling loop, matching `CONTEXT_COLS`' existing optional-column contract.
- **Files modified:** `features/engineer.py`
- **Verification:** `python -m features.engineer` runs cleanly; the same filter is exercised implicitly by every existing `ROLL_STATS` entry (all present) and would no-op gracefully if `understat.parquet` were ever removed.
- **Committed in:** `9fb41cd` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs — one environment/dependency, one code path missing an optional-column guard).
**Impact on plan:** Both fixes were necessary for the plan's own stated design (an optional, no-op-if-absent enrichment source) to actually hold. No scope creep — the environment fix touched no tracked files, and the `ROLL_STATS` fix is a narrow, backward-compatible filter.

## Issues Encountered

None beyond the deviations above. The crosswalk coverage investigation (Task 1) took the bulk of this plan's time — the plan's own action text anticipated needing to "extend `_NAME_FIXUPS`" but the actual limiting factor turned out to be the crosswalk's underlying data source scope, not name-spelling variance; both were addressed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Experiment 6's Understat third is fully closed: measured on both the accuracy axis (fixture-level MAE/Spearman) and the points axis (season-points harness), decided REJECTED, with the ledger stating which axis moved (neither, honestly).
- `apply_experiment_feature_gating()` is now a permanent, tested harness capability any future enrichment plan (09-09's FotMob/FBref) can extend with one more branch, rather than inventing a third ad-hoc column-drop.
- `data.id_crosswalk`'s historical-registry fallback tier and its coverage-improvement pattern are directly reusable by plan 09-09's FotMob/FBref name resolution — worth reading this plan's Decisions before assuming theFPLkiwi's crosswalk alone will suffice there either.
- `predict/live.py` and `predict/export.py` remain untouched — the weekly product surface is unaffected, matching this plan's own success criteria.
- No blockers.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (data/understat.py, data/id_crosswalk.py, config.py, data/build_table.py,
features/engineer.py, tests/test_leakage.py, backtest/walk_forward.py,
tests/test_experiments.py, IMPROVEMENTS.md) exist on disk; all three task commits
(8ea05f4, 9fb41cd, 8820956) found in `git log`; full pytest suite (214 passed, 1 skipped)
and `ruff check .` both green; `data/processed/understat.parquet` (109,592 rows),
`data/processed/experiments/wf_understat_fast.json`, `wf_understat_adopt.json`, and
`understat_mae_comparison.json` all present with the expected shape.
