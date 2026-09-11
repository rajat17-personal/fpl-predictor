# External data snapshot: FBref manual Player Defensive Actions export (2016-17..2025-26)

A ten-season snapshot of FBref's Premier League "Player Defensive Actions" table,
manually acquired by the developer (plan 10-15, Task 1 decision "A" — go, all ten
seasons). **Not joined into the pipeline.** `data/fbref.py`, `config.FBREF_COLS`,
and `features/engineer.py` are all unchanged by this snapshot: the acquired CSVs do
not contain the columns the join was designed around (see "Acquisition-format
defect" below), so no reader/join code (`load_manual_snapshot`) or leakage test was
written. This directory exists only to preserve the acquisition as evidence for any
future revisit, per the project's "never dropped silently" ledger discipline
(IMPROVEMENTS.md Phase E/`fbref_v2` precedent).

## Source

- **Site:** https://fbref.com/en/comps/9/ — Premier League seasons, "Player
  Defensive Actions" table (`#all_stats_defense`; table id `stats_defense`).
- **Method:** manual browser download, one season at a time, via FBref's own
  "Share & Export" menu -> "Get table as CSV", passing the Cloudflare
  `Just a moment...` interstitial interactively each time (the same barrier that
  makes automated access confirmed-dead per Phase 9's `fbref_v2` finding).
- **Retrieval date:** 2026-09-11 (all ten files retrieved in one session,
  10:48-10:55 per file mtimes).
- **Seasons:** 2016-17, 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23,
  2023-24, 2024-25, 2025-26 — the full range authorised by the "A" decision.
- **File naming:** `fbref_<season>_defense.csv`, one file per season, matching
  the plan 10-15 `user_setup` instruction verbatim.
- **Row counts (data rows, excluding the two header lines; `pd.read_csv(f, header=1)`
  row count per file):** 2016-17: 543, 2017-18: 529, 2018-19: 508, 2019-20: 522,
  2020-21: 532, 2021-22: 546, 2022-23: 569, 2023-24: 580, 2024-25: 574,
  2025-26: 551 (5,454 total).

## Attribution

FBref / Sports Reference (Sports Reference LLC). FBref's terms permit manual
export of table data via its own "Share & Export" UI for personal/research use;
no automated scraping infrastructure was built or used to obtain this snapshot
(D-04) — every file was downloaded by a human clicking through the site.

## Regeneration

There is no automated regeneration path, and — per the finding below — **one
would not currently help**. The manual steps, for the record:

```
For each season 2016-17..2025-26:
  1. Open https://fbref.com/en/comps/9/<fbref-season>/defense/<fbref-season>-Premier-League-Stats
  2. Pass the Cloudflare challenge interactively.
  3. On the "Player Defensive Actions" table: Share & Export -> Get table as CSV.
  4. Save as data/external/fbref/fbref_<season>_defense.csv
```

This is a deliberate, human-run, browser-only step — never wired into cron or CI,
and (unlike `data/external/kiwi/` or `data/external/transfermarkt/`) there is no
`--fetch`/backfill script that reproduces it, because no code was written to
consume this snapshot.

## Reduction applied

None — each CSV is committed exactly as exported (verbatim, no columns dropped,
no rows filtered). Total footprint: 496 KB for all ten files, well under any
reasonable budget for a committed data snapshot.

The verbatim exported header (two lines: FBref's grouped super-header, then the
real column-name row), identical across all ten files:

```
,,,,,,,,Tackles,Tackles,Tackles,Tackles,Tackles,Challenges,Challenges,Challenges,Challenges,Blocks,Blocks,Blocks,,,,,,-additional
Rk,Player,Nation,Pos,Squad,Age,Born,90s,Tkl,TklW,Def 3rd,Mid 3rd,Att 3rd,Tkl,Att,Tkl%,Lost,Blocks,Sh,Pass,Int,Tkl+Int,Clr,Err,Matches,-9999
```

## PII spot-check

Only public professional-footballer names, nationalities, ages, birth years,
clubs and public match-statistics are present — the same category of data
already recorded in this project's own `data/processed/id_map.parquet` and every
FPL API response. No email, address, or other sensitive personal data.

## Acquisition-format defect (why no join was built)

**Finding (plan 10-15, Task 2 investigation):** across all ten files, only nine
of the twenty-six exported columns are ever populated: `Rk`, `Player`, `Nation`,
`Pos`, `Squad`, `Age`, `Born`, `90s`, `TklW` (tackles won), `Int` (interceptions),
plus the two trailing link/hash columns (`Matches`, `-9999`). Every other declared
column — `Tkl` (total tackles), `Def 3rd`/`Mid 3rd`/`Att 3rd` (tackle zones),
the "Challenges" block (`Tkl`, `Att`, `Tkl%`, `Lost`), the "Blocks" block
(`Blocks`, `Sh`, `Pass`), `Tkl+Int`, `Clr` (clearances), and `Err` (errors) — is
**100% empty in every row of every one of the 5,446 acquired player-seasons**,
including 2025-26 (the current, presumably-highest-quality season) and including
known heavy-tackling players (e.g. Idrissa Gueye 2016-17: `TklW=103, Int=77`
populated, `Tkl`/`Blocks`/`Clr`/`Tkl+Int` blank; N'Golo Kanté 2016-17: same
pattern). This rules out sparse/real missingness — the pattern is a whole-column,
whole-file phenomenon, not per-player data gaps.

Critically, `config.FBREF_COLS`'s three columns derivable from this table
(`fb_tkl_int_90` from `Tkl+Int`, `fb_blocks_90` from `Blocks`, `fb_clr_90` from
`Clr`) are exactly the three that are universally blank. Only `TklW` and `Int`
— which are *not* the metrics `config.FBREF_COLS` names — are real.

**Root cause confirmed, not assumed.** The initial hypothesis was an export-
widget artifact (FBref's "Get table as CSV" clipboard tool capturing only a
subset of rendered cell values). This was **ruled out**: the developer took a
live browser screenshot of
`https://fbref.com/en/comps/9/2025-2026/defense/2025-2026-Premier-League-Stats#all_stats_defense`
showing the *page itself* rendering only `TklW` and `Int` for the Player
Defensive Actions table — `Tkl`, the zone/challenge breakdown, `Blocks`,
`Sh`/`Pass`, `Tkl+Int`, `Clr`, and `Err` all visually blank on the live site, not
just in the CSV export. The developer then re-tested in an incognito window with
browser extensions disabled and reported, verbatim: **"stil blank"**.

**Conclusion:** FBref is not currently serving these columns' underlying data to
logged-out visitors at all (a site-side content/entitlement change, not an
export-tool limitation, a Cloudflare-access block, or a caching artifact this
project's tooling could work around). No re-export or different export
mechanism would recover them. The CSVs in this directory faithfully captured
what the site actually rendered.

**Outcome:** decision "C" (of the three-way finding presented mid-plan) — drop
the join, record as an **acquisition-format defect**, explicitly distinct from a
declined-on-cost outcome: the developer did complete all ten manual downloads per
the "A" decision; the acquisition itself succeeded; the *source's currently-served
data* is what is deficient. `data/fbref.py`, `config.FBREF_COLS`, and
`features/engineer.py` are unchanged. `config.EXPERIMENTS["fbref_v2"]` stays
`False`. The full ledger entry is in `IMPROVEMENTS.md` under
"`### fbref_v2: manual snapshot — acquisition decision and outcome (plan 10-15)`".

These CSVs are retained (not deleted) as evidence of both the acquisition effort
and the defect, and as a small permanent record should FBref ever restore full
column-serving to logged-out visitors (or should a future revisit try
authenticated/logged-in access) — a future contributor re-reading this directory
can compare a fresh single-season download against this snapshot's column-null
pattern before re-attempting any join.
