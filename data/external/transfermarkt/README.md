# External data snapshot: Transfermarkt injury history

A committed, normalized injury-spell table used as a leakage-safe pre-match
feature family (`config.INJURY_COLS`, `data/transfermarkt.py`). Committed
under D-07 (mirroring `data/external/README.md`'s theFPLkiwi precedent): the
model feature must be reproducible without re-scraping, so the derived
table is checked in here rather than re-fetched at run time.

## Source

- **Site:** [transfermarkt.com](https://www.transfermarkt.com) (unofficial;
  no public API — this project scrapes the public injury-history HTML page).
- **URL pattern:** `https://www.transfermarkt.com/spieler/verletzungen/spieler/{tm_id}`
  (each player's own injury-history page), plus Transfermarkt's own public
  (undocumented) search endpoint
  (`https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query=<name>`)
  used once per player to resolve their `tm_id`.
- **Retrieval date range:** first backfilled 2026-09-10 onward. Every row's
  own underlying HTML fetch is cached under gitignored `data/raw/transfermarkt/`
  (per D-07, raw pages never committed); the committed CSV is the derived,
  normalized table only.
- **Access evidence:** plan 10-05's real 8-page probe (this session,
  2026-09-10) measured Transfermarkt's injury-history pages as **mostly
  open** to plain `requests` + a realistic Chrome `User-Agent`
  (`_MIN_INTERVAL_S=3.0` throttle): 7/8 pages parsed with real data, 0
  anti-bot challenges, 1 `id_unresolved` (a name-resolution gap in the
  search endpoint for an FPL abbreviated display name — addressed in this
  plan via `data.id_crosswalk.resolve_by_name`, never a second matcher). See
  `IMPROVEMENTS.md`'s `### transfermarkt_injury: go/no-go decision` entry
  for the full evidence chain and the developer's verbatim go decision
  (Option A — full backfill, all seasons 2016-17+, background killable job).

## Attribution

Transfermarkt (`transfermarkt.com`), a publicly viewable football statistics
and injury-history site. This project scrapes only publicly displayed player
injury-history pages (season, injury type, date range, days out, games
missed) — no paywalled, authenticated, or non-public content. No official
API or bulk-download offering exists for this data as of 2026-09-10; the
project's own `data/fotmob.py`/`data/understat.py` conventions (kill switch,
per-URL HTML cache, throttle, crosswalk-based identity join) are reused
here.

## Regeneration

```
python -m data.transfermarkt --build
python -m data.transfermarkt --build --seasons 2024-25,2025-26   # restrict scope
python -m data.transfermarkt --build --no-resume                 # re-attempt failures too
```

This is a **deliberate, human-run, network-using step — never wired into cron or CI**.
It is **resumable and safe to kill**: HTML pages are cached
per-URL under `data/raw/transfermarkt/`, resolved Transfermarkt player ids
are cached per-`player_code` in `tm_id_map.csv` (below), and a player already
recorded in the on-disk `_processed.csv` log (gitignored, under
`data/raw/transfermarkt/`) is skipped entirely on the next `--resume` run
(the default) — a kill loses at most a handful of players' worth of work.
Launch it detached for a multi-hour run, following `scripts/experiment_run.sh`'s
own convention:

```
nohup /home/sraja/miniconda3/envs/python314/bin/python -m data.transfermarkt \
  --build > data/processed/experiments/transfermarkt_build-<ts>.log 2>&1 & disown
tail -f data/processed/experiments/transfermarkt_build-<ts>.log
```

## Reduction applied

Two files are committed here:

- **`injury_spells.csv`** — one row per `(player_code, from_date)`, reduced
  from each player's raw injury-history HTML table down to eight columns:

  | Column | Meaning |
  |--------|---------|
  | `player_code` | This project's canonical FPL player identity key |
  | `tm_player_id` | Transfermarkt's own numeric player id |
  | `season_label` | Transfermarkt's own season label as served (e.g. `24/25`) — kept verbatim as provenance; the feature join never keys on this |
  | `injury` | Transfermarkt's own injury-type text (e.g. `Muscle injury`) |
  | `from_date` | Spell start date |
  | `until_date` | Spell end date, or null for a spell still ongoing as of the retrieval date |
  | `days_out` | Transfermarkt's own reported days-out count for the spell |
  | `games_missed` | Transfermarkt's own reported games-missed count, or null for a still-ongoing spell |

- **`tm_id_map.csv`** — the `player_code -> tm_player_id` resolution cache
  (`player_code` unique), so a rebuild never re-searches an already-resolved
  player.

Raw scraped HTML pages (the full injury-history page, and each player's
search-result page) stay **uncommitted** under gitignored
`data/raw/transfermarkt/` per D-07 — only the derived, eight-column
normalized table above is committed.

## PII spot-check

Both committed files carry only a player's Transfermarkt numeric id and
publicly published injury-history facts (injury type, date range, days out,
games missed) already displayed on Transfermarkt's own public pages — no
email, address, date of birth, medical record beyond the publicly reported
injury type/duration, or any other sensitive personal data. `player_code`
is this project's own pre-existing internal identity key (already used
throughout `data/`), not new personal data.

## ToS and redistribution posture

What is committed here is a **derived, normalized, eight-column table** —
never raw scraped HTML pages, and never Transfermarkt's own page markup,
styling, or branding. This mirrors `data/external/README.md`'s existing
posture for theFPLkiwi's snapshot: a small, attributed, non-commercial
research/product-feature dataset, not a redistribution of Transfermarkt's
own site content. No explicit machine-readable licence or ToS API is
published for bulk redistribution of Transfermarkt's data; per plan 10-05's
checkpoint (developer go decision, Option A), the backfill proceeds on the
same access-confirmed-first, derived-table-only discipline this project
already applies to every other unofficial source (`data/fotmob.py`,
`data/understat.py`). If Transfermarkt ever requests removal, delete
`data/external/transfermarkt/` and the code paths that read it
(`data/transfermarkt.py`) degrade to a documented no-op, per the
guarded-optional-enrichment pattern used throughout this codebase.
