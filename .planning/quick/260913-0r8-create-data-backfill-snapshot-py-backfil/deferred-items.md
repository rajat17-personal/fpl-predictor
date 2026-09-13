# Deferred Items — quick-260913-0r8

## Pre-existing schema drift in two cron-captured snapshots (out of scope)

**Found during:** Task 3 verification (column-identity check across all 14 days).

**Issue:** `data/snapshots/2026-08-31.parquet` and `data/snapshots/2026-09-07.parquet`
(both pre-existing, cron-captured before this quick task ran, not in this
plan's `files_modified` list) have 31 columns, not 34 — missing
`chance_of_playing_this_round`, `news`, `news_added`. These three columns
were added to `data/snapshot.py`'s `_ELEMENT_COLS` by a later Phase 10 plan
(per `config.py`'s own Phase 10 plan 10-04 commentary), so the two earliest
archived snapshots predate the column addition at the *code* level, not just
at the data level. The plan's measured fact 2 (missing-column safety) only
applies when `snapshot_frame()` is invoked with the *current* `_ELEMENT_COLS`
— it cannot retroactively add a column to a file written by an older version
of the function.

`2026-09-11.parquet`, `2026-09-12.parquet`, `2026-09-13.parquet` (also
pre-existing, cron-captured) already have all 34 columns, confirming the
schema change landed in the cron path sometime between the 09-07 and 09-11
captures.

**Why deferred, not fixed:** `data/snapshot.py` must stay byte-identical
(explicit plan constraint) and `2026-08-31.parquet`/`2026-09-07.parquet` are
real historical cron captures, not files this plan created or is permitted
to touch (not in `files_modified`; rewriting them would fabricate history
those two days never actually had). Per the Scope Boundary rule, only issues
directly caused by this task's own changes are auto-fixed — this is a
pre-existing condition in unrelated, untouched files.

**Impact:** None on this plan's own deliverable. All 9 newly-backfilled
files (`2026-09-01` through `2026-09-06`, `2026-09-08`, `2026-09-09`,
`2026-09-10`) have the full current 34-column schema, verified
column-for-column identical to `2026-09-12.parquet`. `load_snapshots()`
concatenates all 14 days without error (pandas fills the 3 missing columns
with NaN for the two older files). `models/price.py` and any other
`_ELEMENT_COLS`-derived consumer already tolerate NaN in these columns by
design (measured fact 2).

**Recommendation:** No action needed unless a future plan specifically
requires `chance_of_playing_this_round`/`news`/`news_added` to be non-null
for 2026-08-31/2026-09-07 — in which case a *separate*, explicitly-scoped
plan should decide whether to re-backfill those two specific days from
Wayback (if a suitable capture exists) rather than editing the cron-captured
files in place.
