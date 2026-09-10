# External data snapshot: fplreview.com Free Model

A weekly, permanently committed set of small CSV captures used only for a
diagnostic scoreboard benchmark (`predict/scoreboard.py`, via
`data/fplreview.py`). Unlike `data/external/kiwi/`, these files are captured
**manually** every gameweek, one CSV at a time, not fetched in bulk by a
script.

## Source

- **URL:** https://app.fplreview.com/free
- **Acquisition method:** manual. No automated retrieval is attempted because
  their site returns **HTTP 403 Forbidden** to automated access (observed
  live 2026-09-10, `WebFetch` of `fplreview.com/terms-of-service/`). This is
  a deliberate, confirmed access constraint, not a temporary error to retry.
- **Retrieval cadence:** once per gameweek, before that gameweek's deadline.

## Attribution

Credit: **FPL Review** (fplreview.com), for the Free Model's weekly point
projections.

## Regeneration

Before each gameweek deadline: open `https://app.fplreview.com/free`, export
or copy the current gameweek's projection table, and save it as

```
data/external/fplreview/fplreview_<season>_gw<NN>.csv
```

with at minimum these columns (case-insensitive, whitespace-stripped on
read): `name`, `team`, `position`, `proj_pts` (the player's projected points
for the upcoming gameweek). Validate the fresh capture immediately with:

```
python -m data.fplreview --season <season> --gw <NN>
```

This is a **deliberate, human-run, network-using step — never wired into cron or CI.** A gameweek that passes without a manual capture is data permanently lost; there is no way to backfill a missed week.

## Reduction applied

Only `name` / `team` / `position` / `proj_pts` are kept by
`data/fplreview.py::load_gw` — every other column fplreview's own export
table carries is dropped at read time (never re-derived, never guessed).

## PII spot-check

The only personal data present in a capture is a player's publicly published
name, exactly as it already appears in this project's own
`data/processed/id_map.parquet` and every FPL API response — no email,
address, date of birth, or other sensitive personal data is present in the
kept columns.

## ToS and redistribution posture

These captures are a **local diagnostic benchmark only**: they are never
redistributed beyond this repository, never published (they never reach
`web/data/scoreboard.json` as raw rows, only as aggregate MAE/Spearman
figures), and never used as a model input — enforced by the fact that no
`config.EXPERIMENTS` flag and no `config.*_COLS` constant references this
directory or `data/fplreview.py`.
