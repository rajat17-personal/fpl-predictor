# External data snapshot: FPL-Core-Insights (2025-26 availability)

A small, permanently committed snapshot used to close plan 10-01's own
correction to D-05's "optional" wording: `backtest/walk_forward.py::DATA_SEASONS`
drops the live season (2026-27), so this project's own daily snapshots
(`data/snapshots/`, first capture 2026-08-31) carry **zero** walk-forward
coverage. D-09's covered-season criterion is stated on 2025-26, which only
this one-time vendoring reaches. Committed under the same D-05/D-10
discipline `../README.md` (theFPLkiwi) already documents: the availability
provider must be reproducible forever with no network access, so the raw
upstream files are reduced and checked in here rather than re-fetched at
run time. Read by `data/availability.py`'s existing `fpl_core_insights`
provider (built by plan 10-01, extended by 10-04) -- see `## Leakage rule`
below for the directory-freeze rule that provider encodes.

## Source

- **Repository:** https://github.com/olbauday/FPL-Core-Insights
- **Raw base URL:** `https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/`
- **Vendor's own season directory name:** `2025-2026` (this project's own
  `"2025-26"` label maps onto it via `data/fpl_core_insights.py::_SEASON_DIR`
  and `data/availability.py::_fci_season_label`'s inverse translation)
- **Retrieval date:** 2026-09-10
- **Resolved revision:** the `main` branch resolved to commit
  `f15bf7b6dea6cb441c2dc1ad9a02e4d9749cc68f` ("Auto-update FPL data
  2026-09-10 12:19 UTC", authored by `github-actions[bot]`,
  2026-09-10T12:19:54Z) at retrieval time. This is a bot-maintained repository
  whose `main` branch moves roughly twice daily; this SHA is the
  retrieval-time pin, recorded so this vintage stays reproducible even as
  upstream continues to move.
- **Exact URLs fetched (all 38 gameweeks of the completed 2025-26 season):**
  - `https://api.github.com/repos/olbauday/FPL-Core-Insights/contents/data/2025-2026/By%20Gameweek`
    (lists the 38 `GW<n>` folders)
  - `https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/data/2025-2026/By%20Gameweek/GW<1..38>/playerstats.csv`
    (all 38 files published upstream, none missing -- 2025-26 is a fully
    completed past season by this project's current date, 2026-09-10)

## Attribution

Credit: **olbauday/FPL-Core-Insights** (https://github.com/olbauday/FPL-Core-Insights).

**No explicit licence file is published upstream** -- checked at Task 1's
blocking-human checkpoint by fetching `LICENSE` and `LICENSE.md` directly:
both returned HTTP 404. The GitHub API's own `license` field for the
repository is `null` (re-confirmed at execution time via
`GET /repos/olbauday/FPL-Core-Insights`). The repository's `README.md`
carries an explicit `## Using The Data` clause (fetched and quoted verbatim
at the checkpoint): *"Feel free to use the data from this repository in
whatever way works best for you -- whether for your website, blog posts, or
other projects. If possible, I'd greatly appreciate it if you could include
a link back to this repository as the data source."*

Per the human decision recorded at Task 1's checkpoint (verbatim answer:
**"A"** -- Option A, "Vendor under the theFPLkiwi posture"), this vintage is
vendored under the **same posture `../README.md` already records for
theFPLkiwi**: *no explicit licence, treated as a small research snapshot
with attribution*, here additionally satisfying the repository's own
explicit invitation to reuse the data with a link-back credit (the sentence
above). If olbauday ever requests removal, delete
`data/external/fpl_core_insights/` and `data/fpl_core_insights.py`;
`data/availability.py`'s `fpl_core_insights` provider already degrades to a
documented no-op when its directory is absent (the guarded-optional-
enrichment pattern used throughout this codebase), and
`config.EXPERIMENTS["availability_flags"]` stays default-off regardless.

## Regeneration

```
python -m data.fpl_core_insights --fetch
python -m data.fpl_core_insights --verify
```

`--fetch` re-lists the vendor's `By Gameweek` folder via the GitHub contents
API, re-downloads and re-reduces every `playerstats.csv` for 2025-26, and
overwrites the files in this directory. `--verify` re-runs the D-05
comparison against our own `data/snapshots/` captures (read-only, no
network) and rewrites
`data/processed/experiments/fpl_core_insights_verify.json`. Both are
deliberate, human-run, network-using (`--fetch`) or local (`--verify`)
steps -- **never wired into cron or CI** -- with at least 0.5s between
requests during `--fetch`.

## Reduction applied

Each upstream `playerstats.csv` is a wide per-gameweek export carrying 87
columns (identity, price/ownership/points-history, ICT/expected-stats,
set-piece order, and the injury/availability fields), verbatim (probed live
by plan 10-01, GW1 of 2025-2026):

```
id,status,chance_of_playing_next_round,chance_of_playing_this_round,now_cost,now_cost_rank,now_cost_rank_type,cost_change_event,cost_change_event_fall,cost_change_start,cost_change_start_fall,selected_by_percent,selected_rank,selected_rank_type,total_points,event_points,points_per_game,points_per_game_rank,points_per_game_rank_type,bonus,bps,form,form_rank,form_rank_type,value_form,value_season,dreamteam_count,transfers_in,transfers_in_event,transfers_out,transfers_out_event,ep_next,ep_this,expected_goals,expected_assists,expected_goal_involvements,expected_goals_conceded,expected_goals_per_90,expected_assists_per_90,expected_goal_involvements_per_90,expected_goals_conceded_per_90,influence,influence_rank,influence_rank_type,creativity,creativity_rank,creativity_rank_type,threat,threat_rank,threat_rank_type,ict_index,ict_index_rank,ict_index_rank_type,corners_and_indirect_freekicks_order,direct_freekicks_order,penalties_order,gw,set_piece_threat,first_name,second_name,web_name,news,news_added,minutes,goals_scored,assists,clean_sheets,goals_conceded,own_goals,penalties_saved,penalties_missed,yellow_cards,red_cards,saves,starts,defensive_contribution,corners_and_indirect_freekicks_text,direct_freekicks_text,penalties_text,saves_per_90,clean_sheets_per_90,goals_conceded_per_90,starts_per_90,defensive_contribution_per_90,tackles,clearances_blocks_interceptions,recoveries
```

`data/fpl_core_insights.py::_KEEP_COLS` -- the exact six columns approved at
Task 1's blocking-human checkpoint (an allowlist, not a denylist:
T-10-06-05) -- are retained, **everything else is dropped**:

| Column kept | Meaning |
|---|---|
| `id` | The vendor's raw FPL element id for that season -- kept UNCHANGED (never translated to `player_code` at reduction time); `data/availability.py::_fpl_core_insights_source()` does that translation itself via `data/id_map.py`'s (season, player_id) -> player_code join, the same mechanism this snapshot's own `--verify` step uses |
| `status` | FPL's own single-letter availability code (a/d/i/s/u, plus the real-world `'n'` code `data/availability.py::_STATUS_ALIASES` normalises to `'u'`, discovered in this same vendored data by plan 10-04) |
| `chance_of_playing_next_round` | Percent chance of playing the gameweek this file's folder freezes ahead of |
| `chance_of_playing_this_round` | Percent chance for the gameweek that was CURRENT when the vendor captured the row (a different reference frame -- captured but deliberately left unencoded by `encode_availability`, per its own docstring) |
| `news` | Free-text injury/availability note |
| `news_added` | ISO timestamp the note was added -- feeds `av_days_since_news` |

**Footprint:** the three probed raw files (plan 10-01: GW1 = 254,574 bytes,
GW2 = 172,599 bytes, GW3 = 173,208 bytes; average ~200.1 KB/file) extrapolate
to **~7.6 MB raw** across all 38 gameweeks. The actual reduced, committed
footprint (measured at execution time, `du -sk
data/external/fpl_core_insights`) is **1,016 KB** (`934.7 KB` summed across
the 38 individual CSV files) -- roughly an 8x reduction, well under this
project's 20 MB D-05 verify gate. CSVs only: no parquet, no full-table
copies.

## PII spot-check (D-10)

The 38 committed `GW<n>_playerstats.csv` files were checked column-by-column
against the six declared columns above -- `id, status,
chance_of_playing_next_round, chance_of_playing_this_round, news,
news_added` -- and contain **no columns beyond these six**. No player name,
first/last name, photo, or any other personally identifying field is
present (the raw upstream file's `first_name`, `second_name`, and `web_name`
columns were dropped by the `_KEEP_COLS` allowlist). `id` is a public FPL
element id, the same public identifier already present in every FPL API
response and this project's own `data/processed/id_map.parquet`. The
vendor's files carry **no FPL manager/entry identity** of any kind (no
squad, league, or team-name data) -- `playerstats.csv` is a
league-wide public player table, not a per-manager export.

## Leakage rule

D-05's rule, made executable and enforced by the shared resolver, not by
this module: **a folder labelled gameweek N freezes at gameweek N's END** --
after that gameweek's deadline and after all its in-week news. A folder
covering gameweek N is therefore only ever valid as the state known BEFORE
gameweek **N+1**'s deadline, never for gameweek N itself.
`data/availability.py::_fpl_core_insights_source()` encodes this by tagging
every row from a GW-N file with
`snapshot_ts = max(kickoff_time over (season, N))` (the moment that folder
actually froze) and letting `resolve_as_of()`'s shared as-of-deadline
resolver perform the N-1 offset -- no special-cased arithmetic anywhere.
Locked on synthetic data by
`tests/test_availability.py::test_vendored_provider_uses_prior_gw_folder`.

## Verification against our own snapshots

The D-05 gate's result (`python -m data.fpl_core_insights --verify`, read
from `data/processed/experiments/fpl_core_insights_verify.json`): the
vendored snapshot's LATEST committed gameweek (**GW38**, the end of the
completed 2025-26 season) was compared against our own
`data/snapshots/*.parquet` captures on the two dates this project has
actually taken (**2026-08-31** and **2026-09-07**). Both of those dates fall
in season **2026-27**, roughly four months after 2025-26's GW38 -- so this
is a **schema and value-semantics check** on the 946 players resolvable in
both sources, not a season overlap; genuine drift (transfers, recovered
injuries, new injuries) over four months is expected, not a defect.

- **Status agreement:** 69.2% (946 players pooled across both dates;
  70.8% on 2026-08-31, 67.7% on 2026-09-07)
- **`chance_of_playing_next_round` agreement:** 27.6% (27.1% / 28.1% by
  date) -- **a genuine, explained source-semantics difference, not a bug**:
  FPL's own live API leaves `chance_of_playing_next_round` **null** for most
  fully-fit players with no injury doubt flag (our own `data/snapshots/`
  captures this raw), while FPL-Core-Insights' vendored data backfills many
  of those same "available" players' values to `100.0` instead of leaving
  them null. Spot-checked directly: of 484 `status == 'a'` rows in our own
  2026-09-07 snapshot, 422 (87%) carry a null `chance_of_playing_next_round`
  versus only 62 at `100.0`; the vendor's GW38 file shows the reverse split
  (352 at `100.0` vs 211 null). Both sources agree on the underlying fact
  (the player is available) but encode "no doubt" differently.
- **698 total disagreements** out of 946 compared; a 10-row sample (both
  values shown) is recorded in the verify JSON's `disagreement_sample`
  field.
- **Column comparison:** `columns_ours_only` and `columns_theirs_only` are
  both **empty** -- our own `data/snapshots/` captures (extended by plan
  10-01 for exactly this reason) already carry the identical six-field
  availability family this snapshot vendors, once `id`/`player_code` are
  treated as the shared join key.
