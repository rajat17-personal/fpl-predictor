# Data-Source Resilience: vaastav/Fantasy-Premier-League Gap

**Date:** 2026-09-08
**Author:** research pass (Claude Code)
**Status:** research complete, design proposed

**Sources checked (all on 2026-09-08):**

- https://api.github.com/repos/vaastav/Fantasy-Premier-League/contents/data/2026-27/gws — folder listing
- https://api.github.com/repos/vaastav/Fantasy-Premier-League/contents/data/2026-27 — season folder listing
- https://api.github.com/repos/vaastav/Fantasy-Premier-League/commits?per_page=5 — recent commits
- https://api.github.com/repos/vaastav/Fantasy-Premier-League/issues?state=open — open issues
- https://api.github.com/repos/vaastav/Fantasy-Premier-League/issues/205 — "Local Update and Scraper Usage"
- https://api.github.com/repos/vaastav/Fantasy-Premier-League/forks?sort=newest — fork network freshness
- https://api.github.com/repos/bojanivanovski/Fantasy-Premier-League/contents/data/2026-27/gws — freshest fork's GW folder
- https://github.com/olbauday/FPL-Core-Insights (formerly FPL-Elo-Insights) — alternative dataset
- https://api.github.com/repos/olbauday/FPL-Core-Insights/commits?per_page=3 — update cadence
- https://api.github.com/repos/theFPLkiwi/theFPLkiwi/commits?per_page=3 — theFPLkiwi freshness
- https://fantasy.premierleague.com/api/element-summary/1/ — live field inventory + retained rounds
- https://www.kaggle.com/datasets/calvinrostanto/fantasy-premier-league-2025-2026 — Kaggle 26/27 dataset
- https://fplform.com/fpl-player-data — fplform player data page

---

## 1. What we actually consume from vaastav

`data/ingest.py:fetch_vaastav_season()` downloads exactly **three files per season** from
`https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{season}/`:

| vaastav file | Columns used | Downstream consumer |
|---|---|---|
| `gws/merged_gw.csv` | The 38 keys of `config.MERGED_GW_COLUMNS` (`GW`, `element`, `name`, `position`, `team`, `opponent_team`, `was_home`, `kickoff_time`, `fixture`, `minutes`, `starts`, `total_points`, `xP`, goals/assists/CS/GC/OG/pens/saves/cards, `bonus`, `bps`, `expected_goals`/`assists`/`goal_involvements`/`goals_conceded`, `influence`/`creativity`/`threat`/`ict_index`, `value`, `selected`, `transfers_in/out/balance`, `team_h_score`, `team_a_score`) | `data/build_table.py:_load_merged_gw()` → `data/processed/player_gw.parquet` → `features/engineer.py` → `models/train.py`, `backtest/*` |
| `fixtures.csv` | `id`, `team_h_difficulty`, `team_a_difficulty` | `data/build_table.py:_join_fixture_difficulty()` (FDR features `fdr_self`, `fdr_opp`) |
| `players_raw.csv` | `id`, `code`, `web_name`, `first_name`, `second_name`, `element_type`, + `SET_PIECE_COLS` (`penalties_order`, `direct_freekicks_order`, `corners_and_indirect_freekicks_order`) | `data/id_map.py` → `id_map.parquet` (cross-season identity via `player_code`, position backfill, set-piece joins in `build_table`) |

### How the current season actually flows in today

- **Training/backtest do NOT need vaastav's 2026-27 data right now.** `config.TRAIN_SEASONS`
  end at 2023-24, `VAL_SEASON=2024-25`, `TEST_SEASONS=["2025-26"]`, and
  `backtest/walk_forward.py:34` explicitly drops 2026-27 (`DATA_SEASONS = config.SEASONS[:-1]`).
  `build_table.py` prints `[skip]` and continues when a season's `merged_gw.csv` is absent —
  and our local `data/raw/2026-27/` indeed has only `fixtures.csv` + `players_raw.csv`, no
  `merged_gw.csv`, so `player_gw.parquet` currently contains zero 2026-27 rows and nothing breaks.
- **Live rolling form already bypasses vaastav.** `data/live_history.py` fetches
  `element-summary/{id}/` per player from the official FPL API (called by `scripts/weekly.sh`
  and force-refreshed inside `predict/export.py:281`) and computes the same `ROLL_STATS`
  features "as of now". `data/id_map.py:_from_live_bootstrap()` already falls back to the live
  bootstrap when the current season has no `players_raw.csv`. `data/snapshot.py` captures
  daily bootstrap state (prices, ownership, `ep_next`/`ep_this`, transfer momentum) — cron'd
  in `scripts/daily.sh`.
- **So the gap is a time bomb, not a live outage:** (a) 2026-27 must eventually enter
  `player_gw.parquet` as training/validation/test rows (next retrain cycle promotes it), and
  (b) the FPL API's `element-summary` history **only covers the current season** — after the
  season rolls over, that history is gone from the API. If vaastav never publishes 2026-27
  and we didn't capture it ourselves, the season's per-GW rows are unrecoverable from official
  sources. Also note `live_history._FIELD_MAP` deliberately keeps only the 18 rolling-stat
  fields — it drops `opponent_team`, `was_home`, `fixture`, `value`, `selected`, transfers,
  cards, own-goals, pens, and team scores, so today's cache is NOT a full merged_gw substitute.

## 2. Current gap — verified 2026-27 state of the vaastav repo

Checked 2026-09-08 via the GitHub API (URLs above):

- `data/2026-27/gws/` contains **only `gw1.csv`, `merged_gw.csv`, `xP1.csv`** — i.e. GW1 only
  (merged_gw.csv can only contain GW1 given no other gw files exist).
  (https://api.github.com/repos/vaastav/Fantasy-Premier-League/contents/data/2026-27/gws)
- Per our cached `bootstrap-static.json`, **GWs 1-3 are finished** (GW3 deadline 2026-09-04,
  marked finished+current) and GW4's deadline is 2026-09-12. **Missing from vaastav: GW2 and
  GW3** — precisely the last two completed gameweeks.
- Last repo commit: **2026-08-28, "Add 26/27 gw1 data"** — 11 days ago, one GW behind then,
  two behind now. (https://api.github.com/repos/vaastav/Fantasy-Premier-League/commits)
- Season-level files (`fixtures.csv`, `players_raw.csv`, `teams.csv`, `cleaned_players.csv`,
  `player_idlist.csv`) exist for 2026-27, so identity/FDR inputs are fine — only per-GW data lags.
- Maintenance health: single maintainer (all recent commits by Vaastav Anand). Open issue
  **#219 "Add gw7 data" (2025-10-24)** shows the same multi-week lag pattern last season; open
  issue **#205 (2025-07-26)** has a community member asking how to run the scrapers locally
  "since this repository will be archived and no new data updates for future season" — the
  maintainer has not confirmed archival, but has not denied it either.
  (https://api.github.com/repos/vaastav/Fantasy-Premier-League/issues/205)
- Fork network: the only fork pushed in September 2026 (`bojanivanovski`, 2026-09-04) has the
  **same GW1-only** `2026-27/gws` content — no fork is ahead of upstream.
  (https://api.github.com/repos/bojanivanovski/Fantasy-Premier-League/contents/data/2026-27/gws)

**Conclusion: vaastav is chronically lagging with an uncommitted maintainer and no live fork.
Treat it as a past-season archive, not a current-season feed.**

## 3. Alternatives comparison

| Option | Column coverage vs `MERGED_GW_COLUMNS` | Update latency | Reliability / maintenance | Licensing | Integration effort |
|---|---|---|---|---|---|
| **A. Self-host from official FPL API** (bootstrap-static + element-summary) | 37/38 directly; `xP` (FPL's own prediction) reconstructable from our daily snapshots' `ep_next`/`ep_this` | Same day a GW finishes | Official source — as reliable as FPL itself; we already hit these endpoints daily/weekly | FPL API, same ToS we already operate under | **Low** (~1-2 days; extends `live_history` machinery) |
| **B. FPL-Core-Insights** (olbauday, ex-FPL-Elo-Insights) | All FPL per-GW stats via `player_gameweek_stats`/`playerstats` (FPL-ID aligned) + 60-metric `playermatchstats`, Elo, cups | GitHub Actions, auto-commits ~every 6h (verified commits 2026-09-07/08) | 211 stars, active, but single third-party maintainer — same class of risk as vaastav | "Free to use, attribution appreciated" | Medium (different schema/folder layout: `data/2026-2027/By Gameweek/GW{x}/`) |
| **C. vaastav forks** | Same as vaastav | Freshest fork (2026-09-04 push) still GW1-only | None ahead of upstream | MIT-ish (repo license) | Zero, but pointless — no data |
| **D. theFPLkiwi data** | n/a | Last commit **Dec 2023** — dead | Dead | — | — |
| **E. Kaggle** (e.g. calvinrostanto FPL 26/27) | Varies; typically bootstrap-derived weekly dumps | Weekly, manual | Hobbyist, no SLA; needs Kaggle API auth for automation | Per-dataset | Medium-high, low trust |
| **F. fplform / fplcache** | fplform serves current bootstrap-derived player data (not a per-GW archive); no maintained per-GW fplcache archive found for 2026-27 | Live | Website, no contract | Unclear | High, not fit for purpose |
| **G. Understat / FBref** (existing seams: `understatapi`, `data/fbref.py`) | **Cannot** provide FPL-official `total_points`, bonus, BPS, prices, ownership — enrichment only | 1-2 days | Understat OK; FBref blocked on Cloudflare/Chrome (known) | Scraping ToS grey | Already integrated as optional enrichment |

### Per-option notes

**A — Self-host (recommended primary).** Verified field inventory of
`element-summary/{id}/` `history` entries (https://fantasy.premierleague.com/api/element-summary/1/):
`element, fixture, opponent_team, total_points, was_home, kickoff_time, team_h_score,
team_a_score, round, minutes, goals_scored, assists, clean_sheets, goals_conceded, own_goals,
penalties_saved, penalties_missed, yellow_cards, red_cards, saves, bonus, bps, influence,
creativity, threat, ict_index, starts, expected_goals, expected_assists,
expected_goal_involvements, expected_goals_conceded, value, transfers_balance, selected,
transfers_in, transfers_out` — plus the new 2026-27 defensive-contribution fields
(`clearances_blocks_interceptions`, `recoveries`, `tackles`, `defensive_contribution`) that
vaastav's schema doesn't even carry (future feature upside). The endpoint **retains every
completed round of the current season** (rounds 1-3 present today), so the two missing GWs are
fully backfillable right now with one sweep. What element-summary lacks, we already have:
`name`/`team`/`position` come from bootstrap-static (cached by `ingest`, snapshotted daily);
vaastav's `xP` column ≈ FPL's `ep_this` at the GW deadline, which `data/snapshot.py` has been
capturing daily since day one (`ep_next`, `ep_this` in `_ELEMENT_COLS`). This is exactly how
vaastav's own scripts build their CSVs — we'd just run the same collection ourselves.

**B — FPL-Core-Insights (recommended secondary/fallback).** Automated (github-actions bot,
multiple commits per day verified), FPL-ID aligned, richer than vaastav
(https://github.com/olbauday/FPL-Core-Insights). Right choice as a *cross-check and emergency
fallback* feed, and a candidate future enrichment source (its `playermatchstats` overlaps what
`data/fbref.py` was meant to provide, without the Chrome/Cloudflare problem). Wrong choice as
sole primary: it is another solo-maintained community repo — adopting it as the only source
recreates the vaastav single point of failure.

**G — Understat/FBref** stay what they are: optional enrichment. They cannot emit FPL points,
bonus, BPS, prices or ownership, so they can never replace the per-GW official rows.

## 4. Recommended design: self-hosted GW capture, vaastav demoted to backfill

**Principle:** the official FPL API becomes the source of truth for the *current* season's
per-GW rows; vaastav is used only for past-season history already on disk (2016-17 … 2025-26,
all cached in `data/raw/`). No third party sits between us and current-season training data.

### New module: `data/gw_capture.py`

- **What it does:** after each completed GW, fetch `bootstrap-static` + every player's
  `element-summary/{id}/` (reuse the fetch loop/rate-limiting from `data/live_history.py`),
  and write **vaastav-schema-compatible** files under `data/raw/{CURRENT_SEASON}/`:
  - `gws/gw{N}.csv` — one file per finished GW (idempotent: skip if exists unless `--force`)
  - `gws/merged_gw.csv` — regenerated as the concat of all captured `gw{N}.csv`
  - `players_raw.csv` — refreshed from bootstrap `elements` (keeps `id_map` on its primary path)
  - `fixtures.csv` — refreshed from `{FPL_API}/fixtures/` (carries `team_h_difficulty`/`team_a_difficulty`, same fields `_join_fixture_difficulty` needs)
- **Schema mapping** (element-summary → vaastav column names, i.e. the *source* keys of
  `config.MERGED_GW_COLUMNS` so `build_table` needs **zero changes**):
  `round→GW`, `element` (from URL/id), `fixture→fixture`, `opponent_team→opponent_team`,
  stats copied 1:1 (`minutes`, `starts`, `total_points`, `goals_scored`, …,
  `expected_goals`, `value`, `selected`, `transfers_*`, `team_h_score`, `team_a_score`);
  `name`/`team`/`position` joined from bootstrap (`web_name` or `first_name+second_name`,
  team short name, `element_type` map); `xP` filled from the daily snapshot dated the GW's
  deadline day (`ep_this`; fall back to nearest snapshot ≤ deadline; NaN if none — build_table
  tolerates missing columns and `xp_fpl` is a baseline, not a model input).
  Additionally append the new defensive-contribution fields as extra columns (harmless to
  `build_table`, which selects only known columns; enables a later `MERGED_GW_COLUMNS` extension).
- **Idempotent & cron-friendly:** determines finished GWs from bootstrap `events[].finished`;
  exits 0 quickly when nothing new; atomic writes (tmp + `os.replace`, as in `snapshot.py`);
  failure reported via `ops.notify` like the other cron steps.

### Changes to existing modules

- `data/ingest.py`: for `config.CURRENT_SEASON`, stop downloading `gws/merged_gw.csv` from
  vaastav (or download only as a cross-check, never overwriting local capture). Past seasons
  unchanged. Add a one-line warning when vaastav 404s a requested season so staleness is visible.
- `scripts/daily.sh`: add `run_step data.gw_capture "$PY" -m data.gw_capture` after
  `data.snapshot` (daily is the right cadence: a GW finishes mid-week sometimes, and daily
  capture bounds our loss window to <24h; weekly.sh gets it implicitly via the files on disk).
- `data/live_history.py`: unchanged short-term. Optional later refactor: have it read from the
  gw_capture output instead of re-fetching element-summary (one API sweep instead of two).
- `data/build_table.py`, `data/id_map.py`, `features/`, `models/`: **no changes** — that is the
  point of writing vaastav-schema files into the vaastav-expected paths.

### Backfill of the two missing GWs

One command, today: `python -m data.gw_capture --backfill` sweeps element-summary (which still
holds rounds 1-3) and writes `gw1.csv`, `gw2.csv`, `gw3.csv` + `merged_gw.csv`. For GW1 the
vaastav copy exists as a cross-check (diff ours vs theirs to validate the mapping — a good
acceptance test). `xP` for GW1-3 comes from the snapshots already sitting in `data/snapshots/`
(daily since before the season started per MEMORY.md).

### Monitoring

Add a freshness check to `predict/scoreboard.py` or `ops.notify` path: after each finished GW,
assert `gws/gw{N}.csv` exists within 24h of `events[N].data_checked=true`, else alert. This is
what was silently missing with vaastav — nothing told us the feed stalled.

### Task sizing

1. **T1 (core, ~half day):** `data/gw_capture.py` — fetch sweep, schema mapping, per-GW +
   merged CSV writers, `--backfill`/`--force`, atomic writes, `ops.notify` on failure.
2. **T2 (~1-2h):** `data/ingest.py` current-season guard + `scripts/daily.sh` step + cron docs.
3. **T3 (~1-2h):** validation test — diff self-built `gw1.csv` vs vaastav's published GW1
   (row count, per-column equality on shared keys); pytest `tests/test_gw_capture.py` for
   schema completeness against `config.MERGED_GW_COLUMNS`; run `build_table` end-to-end and
   confirm 2026-27 rows appear with FDR/set-piece/position coverage.
4. **T4 (~1h):** freshness alert + short runbook note in the repo (where the data comes from
   now, how to backfill, vaastav's demoted role).

**Residual risk after this design:** none for current-season rows (official API, captured
within 24h, backfillable all season). Past-season history is already fully cached locally in
`data/raw/` — pin it with a one-off archive (tar to backup or git-LFS) so a vaastav deletion
costs nothing. FPL-Core-Insights is the documented emergency fallback if the FPL API itself
changes shape mid-season.
