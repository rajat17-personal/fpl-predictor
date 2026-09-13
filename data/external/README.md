# External data snapshot: theFPLkiwi

A small, permanently committed snapshot used only for a one-time evaluation
benchmark (`backtest/benchmark_external.py`) and for the player-identity
crosswalk (`data/id_crosswalk.py`). Committed under D-10: the benchmark must
be reproducible forever with no network access, so the raw upstream files are
reduced and checked in here rather than re-fetched at run time.

## Source

- **Repository:** https://github.com/theFPLkiwi/theFPLkiwi
- **Raw base URL:** `https://raw.githubusercontent.com/theFPLkiwi/theFPLkiwi/main/`
- **Retrieval date:** 2026-09-08
- **Resolved revision:** the `main` branch resolved to commit
  `166503a39724e4a891f9a57e0c40310dad954c1d` (2023-12-21) at retrieval time —
  the repository has not been updated since, so `main` and this SHA are
  equivalent as of the retrieval date.
- **Exact URLs fetched:**
  - `https://raw.githubusercontent.com/theFPLkiwi/theFPLkiwi/main/ID_Dictionary.csv`
  - `https://raw.githubusercontent.com/theFPLkiwi/theFPLkiwi/main/Old_Seasons/FPL_projections_21_22/FPL_GW<1..38>.csv`
    (39 files listed upstream; `FPL_GW14_2.csv` skipped as a mid-week
    re-issue duplicating GW14, not a distinct gameweek)
  - `https://raw.githubusercontent.com/theFPLkiwi/theFPLkiwi/main/Old_Seasons/FPL_projections_22_23/FPL_GW<n>.csv`
    (27 files upstream: GW1-22, GW25-28, GW32, GW33 — GW23/24/29-31/34-38 were
    never published upstream)
  - `https://raw.githubusercontent.com/theFPLkiwi/theFPLkiwi/main/FPL_projections_23_24/FPL_GW<n>.csv`
    (only 4 files published upstream: GW1, GW3, GW4, GW18 — this vintage is
    too thin to score and is reported as skipped by
    `backtest/benchmark_external.py`, not silently dropped)

## Attribution

theFPLkiwi publishes this data for the FPL community. Credit: **theFPLkiwi** —
[Twitter/X @theFPLkiwi](https://twitter.com/theFPLkiwi),
[reddit u/theFPLkiwi](https://www.reddit.com/u/theFPLkiwi),
[ko-fi.com/thefplkiwi](https://ko-fi.com/thefplkiwi), and Discord in the FPL
Analytics Community & FPL Review servers (per the upstream repository's own
`README.md` credit block).

**No explicit licence file is published upstream** (checked at
`LICENSE`/`LICENSE.md`, both 404; the GitHub API's own `license` field for the
repository is `null`). This is therefore treated as a small research snapshot
used for a benchmark comparison with attribution and the upstream author's
contact recorded above, not a redistribution under any stated licence terms.
If theFPLkiwi ever requests removal, delete `data/external/kiwi/` and the code
paths that read it (`backtest/benchmark_external.py`, `data/id_crosswalk.py`)
degrade to a documented no-op, per the guarded-optional-enrichment pattern
used throughout this codebase.

## Regeneration

```
python -m backtest.benchmark_external --fetch
```

This re-downloads the ID dictionary and every per-gameweek projection CSV
listed above, re-applies the same positional reduction, and overwrites the
files in this directory. It is a deliberate, human-run, network-using step —
never wired into cron or CI — with at least 0.5s between requests.

## Reduction applied

`ID_Dictionary.csv` (62,142 bytes) is committed **verbatim** — small enough
on its own (well under the 10 MB budget) that no reduction is needed. It
supplies the FPL↔fbref ID crosswalk `data/id_crosswalk.py` builds from.

Each upstream `FPL_GW<n>.csv` projection file is a wide, per-gameweek export
(~950 KB apiece; ~60 MB for the whole raw set across three seasons) carrying
five repeated block layouts (minutes, points-if-played, probability-to-play,
points, goals) with one column per remaining gameweek in the season. Only the
**projection for the file's own gameweek** is kept — located positionally off
the header row (never by column name, since names repeat across blocks and
vary between the 2021-22/2022-23 and 2023-24 label vintages) — reduced down
to eight tidy columns per row:

| Column | Meaning |
|--------|---------|
| `season` | This project's season label (`2021-22`, `2022-23`, `2023-24`) |
| `gw` | Gameweek number the file itself was published for |
| `fpl_id` | theFPLkiwi's `ID` column — the season-local FPL element id (matches this project's `player_id`, not `player_code`) |
| `name` | Player name as published by theFPLkiwi |
| `pos` | Position as published by theFPLkiwi |
| `team` | Club, theFPLkiwi's abbreviation |
| `price` | Price at the time of that gameweek's projection |
| `proj_pts` | theFPLkiwi's pre-deadline projected points for that gameweek |

Rows with `fpl_id == 0` are dropped: theFPLkiwi's own `README.md` states those
are placeholder entries for players not yet in the game (not-yet-signed
transfers, youth players, loan returnees), always priced at £3.0 with 0
minutes/points by construction — not real projections.

This reduces the committed footprint from ~60 MB of raw wide exports to
~1.7 MB of tidy CSVs (`du -sk data/external` reports well under the 10 MB
budget), while keeping every gameweek's actual prediction.

## PII spot-check (D-10)

The three tidy `kiwi_projections_<season>.csv` files were checked
column-by-column against the eight declared columns above — `season, gw,
fpl_id, name, pos, team, price, proj_pts` — and contain **no columns beyond
these eight**. The only personal data present is a player's publicly
published name, exactly as it already appears in this project's own
`data/processed/id_map.parquet` and every FPL API response — no email,
address, date of birth, or other sensitive personal data is present in the
tidy projection files. (`ID_Dictionary.csv`, kept verbatim, does carry a
`DOB` column — the same publicly published professional-athlete date of
birth already implied by every football statistics site; it is not reduced
because it is committed unmodified as a small crosswalk reference file, not
processed as bulk data.)
