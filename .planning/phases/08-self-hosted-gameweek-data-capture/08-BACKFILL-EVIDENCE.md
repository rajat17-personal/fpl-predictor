# Phase 8 Plan 03: Backfill Evidence

Real capture against the live FPL API, cross-checked against the previously published
source, and ingested into the canonical table — recorded verbatim from the runs
executed on this machine on 2026-09-12.

## 1. Live facts re-established immediately before capture

Read at 2026-09-12T06:35Z, on this machine, before running `data.gw_capture`:

| Fact | Value |
|---|---|
| Finished and data-checked gameweeks | 1, 2, 3 (identical to the plan's day-old baseline table — no fourth gameweek has settled) |
| Elements in the live bootstrap | 656 |
| Next event | GW4, deadline `2026-09-12T12:30:00Z` (not yet finished/data-checked) |
| `element-summary/1/` round retention | still serves rounds `[1, 2, 3]` — the backfill window has not closed |

Precondition for Task 1 confirmed met before any capture ran.

## 2. Task 1 — Real capture run

**Command:** `/home/sraja/miniconda3/envs/python314/bin/python -m data.gw_capture` (no flags)
**Started:** 2026-09-12T06:37:22Z

Run output (verbatim, element-summary sweep progress lines collapsed):

```
  fetched 0/656 players
  fetched 100/656 players
  ...
  fetched 600/656 players
[gw_capture] GW1 xP: no snapshot dated on or before the deadline -- missing for all players
[gw_capture] GW2 xP: no snapshot dated on or before the deadline -- missing for all players
[gw_capture] GW3 xP: snapshot 2026-08-31 column ep_next -- 100% resolved (626/626)
[gw_capture] GW1: 610 rows
[gw_capture] GW2: 626 rows
[gw_capture] GW3: 654 rows
```

Exit code: `0`. No `ALERT` line, no player-fetch-failure line — **zero per-player request
failures this run.**

### Captured row counts vs. the live element count (656)

| GW | Rows captured | % of 656 elements | Within 10%? |
|---|---|---|---|
| 1 | 610 | 93.0% | Yes |
| 2 | 626 | 95.4% | Yes |
| 3 | 654 | 99.7% | Yes |

### Confirmed by inspection

- One ledger file per captured gameweek: `data/raw/2026-27/gws/gw1.csv`, `gw2.csv`, `gw3.csv` — exactly 3, matching the 3 finished-and-data-checked gameweeks.
- `data/raw/2026-27/merged_gw.csv`: 1,890 rows, **46 columns**, `missing_source_keys` against `config.MERGED_GW_COLUMNS` = `[]` (empty — every source key present).
- Per-GW row counts inside `merged_gw.csv` (`groupby('round')`): `{1: 610, 2: 626, 3: 654}` — matches the ledger exactly.
- `players_raw.csv`: 656 rows, mtime `2026-09-12T06:56:39Z` (this run) — was `2026-08-21` before.
- `fixtures.csv`: 380 rows, mtime `2026-09-12T06:56:39Z` (this run) — was `2026-08-21` before.

### Expected-points (`xP`) null rate per captured gameweek

| GW | Deadline | Resolution outcome | `xP` non-null fraction |
|---|---|---|---|
| 1 | 2026-08-21 | No snapshot dated on or before the deadline (earliest snapshot is 2026-08-31, 10 days later) | **0.0%** |
| 2 | 2026-08-28 | No snapshot dated on or before the deadline (earliest snapshot is 3 days later) | **0.0%** |
| 3 | 2026-09-04 | Snapshot `2026-08-31` (4 days stale), column `ep_next` (that snapshot's recorded `next_gw` equalled GW3) | **95.72%** resolved (626/626 in the mapping resolved; 654 rows captured, so 28 GW3 players fall outside the 626-player snapshot and read as missing via the plain dict-lookup miss — expected per the module's own contract, never a fallback or interpolation) |

**GW1/GW2's 0% `xP` rate is the documented, permanent gap this phase exists to record — not
a bug.** Both gameweeks' deadlines (2026-08-21, 2026-08-28) precede the earliest daily
snapshot in the archive (2026-08-31); `data/snapshot.py`'s archive did not exist yet at
either deadline, so there is no pre-deadline snapshot to resolve from and never will be
one for these two gameweeks specifically. A future promotion of 2026-27 into
`TRAIN_SEASONS`/`TEST_SEASONS` must read this as a real, permanent data gap for GW1/GW2's
`xp_fpl` feature, not evidence of a broken join.

### Frozen-surface check

`git status --porcelain web/ scripts/` after the run:
```
 M web/data/watchlist.json
?? web/data/history/gw4.json
?? web/data/scoreboard.json
```
These three entries **predate this plan's entire session** — confirmed present in the
git-status snapshot taken before any command in this plan ran (also documented as
pre-existing in 08-01-SUMMARY.md and 08-02-SUMMARY.md). No file under `web/` or
`scripts/` was created, modified, or deleted by this plan's own actions.

`git status --porcelain data/snapshots/`:
```
?? data/snapshots/2026-09-07.parquet
?? data/snapshots/2026-09-11.parquet
?? data/snapshots/2026-09-12.parquet
```
Three pre-existing untracked snapshot files — no deleted or modified entries, matching
08-02-SUMMARY.md's own recorded baseline. No regression.

## 3. Task 2 — Gameweek-1 cross-check against the previously published file

**Oracle fetch:** `GET https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2026-27/gws/gw1.csv`
**Response:** `200`, 104,994 bytes, 611 lines (610 data rows + header) — the oracle is
still served and not truncated.

The published file was fetched into the session scratch directory (outside the repo
working tree, never under `data/`), loaded alongside the captured `data/raw/2026-27/gws/gw1.csv`.

### First run — before any fix

Comparing on the natural key `(element, fixture)`:

| Metric | Value |
|---|---|
| Our row count | 610 |
| Published row count | 610 |
| Keys in both | 610 |
| Keys only in published (`only_theirs`) | **0** |
| Keys only in ours (`only_ours`) | **0** |

Perfect key-set agreement on the first run — no missing element, no round-filter drop, no
extra row.

Per-column agreement (41 shared columns, excluding the two deliberate exclusions `xP` and
`modified`):

**Finding — `team` disagreed on 17 of 610 rows.** Two concrete examples:

| `(element, fixture)` | Ours | Published |
|---|---|---|
| `(28, 7)` | `Chelsea` | `Aston Villa` |
| `(91, 2)` | `Coventry City` | `Brentford` |

**Diagnosis:** `build_gw_frame` joined `team` from the player's **current** bootstrap
team assignment (`bootstrap.elements[].team`, resolved at capture time — 2026-09-12),
not from the team they were actually playing for at the time of the GW1 fixture
(2026-08-21). Both example players have transferred clubs since GW1 (element 28,
Emiliano Martínez, moved to Chelsea; element 91, Ethan Pinnock, moved to Coventry
City) — the published file was captured near GW1's own deadline, before either
transfer, and correctly shows their club at the time. Confirmed by cross-referencing
the live bootstrap (`elements[].team` → current club) against the `fixtures/` payload's
own `team_h`/`team_a` for those two fixture ids, which match the published file, not
ours.

**This is a real bug in `data/gw_capture.py`, not a schema-mapping ambiguity** — the
fault is ours. Per the plan's own prohibition, it was fixed in code and the affected
gameweeks re-captured with `--force`, never patched in the data:

- **Fix commit:** `bbc0e4c` — `fix(08-03): resolve captured team from the fixture, not the player's current club`. `build_gw_frame` now resolves `team` from the row's own fixture (`fixtures[].team_h`/`team_a`, keyed by `was_home`) with a fallback to the old current-team join only when fixtures data isn't supplied (keeps existing direct-call tests unaffected). Two new regression tests (`test_build_gw_frame_resolves_team_from_the_fixture_not_the_players_current_club`, `test_build_gw_frame_falls_back_to_current_team_when_fixture_not_supplied`) lock both halves.
- **Re-capture:** `python -m data.gw_capture --force`, run at 2026-09-12T06:56:39Z. Same row counts (610/626/654), same zero-failure sweep, exit code `0`.

### Re-run after the fix — post-fix numbers

| Metric | Value |
|---|---|
| Our row count | 610 |
| Published row count | 610 |
| Keys in both | 610 |
| Keys only in published | 0 |
| Keys only in ours | 0 |
| Shared columns compared | 41 |
| **Disagreeing columns** | **[] — empty** |

Every one of the 41 shared columns now agrees on all 610 keys.

### Deliberate exclusions

| Column | Ours | Published | Reason excluded |
|---|---|---|---|
| `xP` | 0/610 non-null (0.0%) | 610/610 non-null (100%) | By design: ours is missing for GW1 because its deadline precedes the earliest daily snapshot (see §2); the published file carries FPL's own `ep_this`/`ep_next` figure captured live near the deadline. Not a schema-mapping claim — a stated, permanent data gap. |
| `modified` | all `False` | all `False` | A transient publisher-side field (whether the row was edited after initial capture) that may legitimately differ run-to-run; declared exempt from the equality verdict regardless of outcome. In this run both files happened to agree, but the exclusion stands on its own terms. |

### Verdict

**The schema mapping is confirmed** after one code fix (team resolution from the
fixture, not the player's current club) — every non-excluded shared column agrees
exactly across all 610 shared keys, and the key sets are identical in both directions.

`git status --porcelain` shows no untracked CSV anywhere under `data/` — the published
oracle file was written to the session scratch directory outside the repository working
tree, never into `data/raw/`.

## 4. Task 3 — Canonical table rebuild

### id-map rebuild

**Command:** `python -m data.id_map`

```
Building id_map:
  [ok]   2016-17:  683 players (players_raw)
  [ok]   2017-18:  647 players (players_raw)
  [ok]   2018-19:  624 players (players_raw)
  [ok]   2019-20:  666 players (players_raw)
  [ok]   2020-21:  713 players (players_raw)
  [ok]   2021-22:  737 players (players_raw)
  [ok]   2022-23:  778 players (players_raw)
  [ok]   2023-24:  865 players (players_raw)
  [ok]   2024-25:  804 players (players_raw)
  [ok]   2025-26:  841 players (players_raw)
  [ok]   2026-27:  656 players (players_raw)

id_map: 8,014 (season, player) rows, 2,772 unique player codes
wrote data/processed/id_map.parquet
```

**Source confirmed correct**: the current season is sourced from `players_raw` (the file
this phase now writes), **not** the live-bootstrap fallback (`_from_live_bootstrap`) —
proving the stale-cache risk the read_first note called out did not materialize, because
Task 1's unconditional `players_raw.csv` refresh landed before this rebuild ran.

### Table build

**Command:** `python -m data.build_table`

Key printed lines:
```
  [ok]   2026-27:  1,890 rows
  [clean] dropped 322 AM (manager) rows, 69 duplicate rows
  [odds]  coverage: 63.8%
  [team_strength] joined; coverage 99.3%
  [understat] joined; coverage 41.2%
  [fotmob] joined; coverage 40.5%
  [availability] joined; coverage 10.8%
  [transfermarkt] joined; id-resolved coverage 79.6%, active-spell rate (of resolved) 11.0%
  [pos]   position coverage after backfill: 100.0%

rows        : 255,399
seasons     : 2016-17, 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26, 2026-27
```

**Eleven seasons printed, no skip line for the current season.**

### Before-and-after per-season row counts

| Season | Baseline (pre-Phase-8) | This rebuild | Match? |
|---|---|---|---|
| 2016-17 | 23,679 | 23,679 | Yes |
| 2017-18 | 22,467 | 22,467 | Yes |
| 2018-19 | 21,790 | 21,790 | Yes |
| 2019-20 | 22,501 | 22,501 | Yes |
| 2020-21 | 24,365 | 24,365 | Yes |
| 2021-22 | 25,447 | 25,447 | Yes |
| 2022-23 | 26,505 | 26,505 | Yes |
| 2023-24 | 29,725 | 29,725 | Yes |
| 2024-25 | 27,283 | 27,283 | Yes |
| 2025-26 | 29,747 | 29,747 | Yes |
| **2026-27** | 0 (did not exist) | **1,890** | New |

Programmatic regression check (`regressions` dict comparing every baseline season against
`df.groupby('season').size()` on the rebuilt parquet): **`{}` — empty. Zero regressions.**
(Note: the per-season lines `build_table` prints during loading are pre-`_clean()` raw
file counts, before the AM-row-drop and exact-duplicate-drop step; the number that must
match the baseline — and does — is the final post-clean count read back from the written
parquet, shown in the table above.)

### Current-season coverage

| Metric | Value | Threshold | Pass? |
|---|---|---|---|
| Current-season rows | 1,890 | > 0 | Yes |
| Position coverage | 100.0% (1.0) | ≥ 1.0 | Yes |
| Fixture-difficulty (`fdr_self`) coverage | 100.0% (1.0) | ≥ 0.95 | Yes |
| Stable-player-code (`player_code`) coverage | 100.0% (1.0) | ≥ 0.98 | Yes |
| Expected-points (`xp_fpl`) coverage, GW1 | 0.0% | documented gap | n/a — see §2 |
| Expected-points (`xp_fpl`) coverage, GW2 | 0.0% | documented gap | n/a — see §2 |
| Expected-points (`xp_fpl`) coverage, GW3 | 95.7% | — | matches §2's resolution outcome |

Position coverage reaching 1.0 (rather than relying on the older-season backfill path) is
expected: the captured file carries `position` directly from `build_gw_frame`'s bootstrap
join, never NaN for the current season. Stable-code coverage at 1.0 (above the 0.98 gate)
directly confirms the id-map rebuild above picked up every one of the 656 elements
registered since the pre-season `players_raw.csv` snapshot — no player silently dropped
for lacking a `player_code`.

### Current-season odds coverage — diagnosed as absent upstream source, not a club-name mismatch

**Current-season `odds_pwin` coverage: 0.0%** (against an overall table-wide coverage of
63.8%, so this is a current-season-specific gap, not the pre-existing 2016-19 hole
`config.TEAM_STRENGTH_COLS`'s own comment already documents).

**Diagnosis:** the cached `data/raw/odds/2026-27.csv` (dated 2026-08-21, pre-season) is
not a valid odds CSV at all — it is football-data.co.uk's own "300 Multiple Choices"
HTML error page, returned because `/mmz4281/2627/E0.csv` does not yet exist on their
server for this season:

```html
<title>300 Multiple Choices</title>
The document name you requested (<code>/mmz4281/2627/E0.csv</code>) could not be found on this server.
```

This is confirmed as an **absent upstream source**, not the club-name-mismatch failure
mode `08-RESEARCH.md`'s Pitfall 2 warns about: the `team` column produced by this
phase's own captured rows is verified correct in §3 above (full club name, matching the
odds join's expected convention exactly), so a real 2026-27 odds file would join
correctly once football-data.co.uk publishes one. `data/odds.py` is outside this plan's
`files_modified` scope (only `08-BACKFILL-EVIDENCE.md` and the two Rule-1 fixes above
were touched) and is not fixed here; the pre-season-cached error page silently staying
"authoritative" forever if never re-fetched is a pre-existing `data/odds.py` cache-freshness
gap, unrelated to and not introduced by this plan.

### Features and model: confirmed untouched

`features/engineer.py` was not run and no model was retrained in this plan. This is
correct, not an oversight: `backtest/walk_forward.py:46` defines
`DATA_SEASONS = config.SEASONS[:-1]  # drop 2026-27`, so the current season is
excluded from every training/validation/test season list the walk-forward harness
consumes. The canonical table gaining 2026-27 rows changes zero model input under the
currently configured seasons.

### Full-suite verification and frozen-surface confirmation

`/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q`:

```
412 passed, 1 skipped, 1238 warnings in 286.47s
```

(409 baseline from 08-02 + 2 new `data/gw_capture.py` team-resolution regression tests +
1 new `data/team_strength.py` in-progress-season regression test = 412.)

`git status --porcelain web/ scripts/ data/build_table.py data/id_map.py`:
```
 M web/data/watchlist.json
?? web/data/history/gw4.json
?? web/data/scoreboard.json
```
Same three pre-existing, session-predating entries as §2 — `data/build_table.py` and
`data/id_map.py` print no output at all (confirmed byte-identical via
`git diff --quiet -- data/build_table.py data/id_map.py`), and no file under `scripts/`
appears. Both consumer modules remain unmodified for the whole plan.

## 5. Deviations from the plan — auto-fixed issues

Both deviations were discovered by this plan's own cross-check and full-suite gates,
diagnosed as genuine bugs directly caused by exercising already-written code (from plans
08-01/08-02) against real data for the first time, fixed per Rule 1 (auto-fix bugs), and
locked with regression tests. Neither required an architectural change or user input.

**1. [Rule 1 - Bug] `team` column joined the player's current club instead of the
historical fixture's club**
- **Found during:** Task 2's GW1 cross-check (17/610 rows disagreed)
- **Issue:** `build_gw_frame` resolved `team` from `bootstrap.elements[].team` (today's
  club) rather than from the specific historical fixture being captured, silently
  retro-dating a since-transferred player's entire history onto their new club.
- **Fix:** `team` now resolves from `fixtures[].team_h`/`team_a` (keyed by `was_home`),
  falling back to the old current-team join only when no matching fixture is supplied.
- **Files modified:** `data/gw_capture.py`, `tests/test_gw_capture.py`
- **Verification:** Cross-check re-run against the published GW1 file dropped
  `disagreeing_cols` from `[('team', 17)]` to `[]`; both new tests pass; full
  `tests/test_gw_capture.py` suite (33 tests) green.
- **Commit:** `bbc0e4c`

**2. [Rule 1 - Bug] `team_strength.build_matches` raised on the first-ever in-progress
current season in `player_gw.parquet`**
- **Found during:** Task 3's `pytest -q` full-suite gate
  (`tests/test_leakage.py::test_team_strength_ratings_reproducible_from_prior_matches`)
- **Issue:** the systemic-reconstruction-failure guard (`counts < 370` fixtures per
  season) had never before had to tolerate a season that is simply not finished yet —
  every prior `player_gw.parquet` build only ever held complete past seasons. Rebuilding
  it with the current season's 3 finished gameweeks (30 reconstructed fixtures) tripped
  the same alarm meant for a genuinely broken past season.
- **Fix:** `build_matches` now exempts `config.CURRENT_SEASON` from the systemic-failure
  raise (a genuinely broken **past** season with the same fixture count still raises);
  the Dixon-Coles leakage guarantee itself (`fit_ratings_as_of` never sees a match at or
  after the target gameweek) is unchanged.
- **Files modified:** `data/team_strength.py`, `tests/test_leakage.py`
- **Verification:** `tests/test_leakage.py` (13 tests) green; new regression test proves
  both halves (current-season shortfall tolerated, identical past-season shortfall still
  raises); full suite green (412 passed, 1 skipped).
- **Commit:** `e995a0f`

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs directly caused by this plan's own
first real exercise of previously-written, untested-against-real-data code).
**Impact on plan:** Both fixes were minimal, scoped exactly to the failing behavior, and
each is locked by a dedicated regression test. Neither touched `data/build_table.py`,
`data/id_map.py`, `scripts/`, or `web/`. The phase's core claim — captured rows flow into
the canonical table with zero change to either consumer module — is intact.

## 6. Summary

| Success criterion | Result |
|---|---|
| The two gameweeks the previous source never published are on disk | GW2 (626 rows) and GW3 (654 rows) captured from the official API, alongside GW1 (610 rows) |
| Schema mapping confirmed against an independent GW1 copy | Confirmed after one code fix — zero disagreeing columns, zero one-sided keys |
| Canonical table ingests captured rows with no consumer change | 2026-27 now has 1,890 rows in `player_gw.parquet`; `data/build_table.py`/`data/id_map.py` byte-identical to before this plan |
| Nothing regressed | Ten past-season row counts identical to baseline; frozen surfaces (`web/`, `scripts/`) untouched by this plan; no model retrained |
| Every measured number, including the honest gap, is recorded | `xP` null rate GW1/GW2 = 100%, GW3 = 4.3%, documented as permanent for GW1/GW2 above |
