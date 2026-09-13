# Runbook: gameweek data capture

**Status:** Active
**Date:** 2026-09-12
**Phase:** 08-self-hosted-gameweek-data-capture

vaastav's Fantasy-Premier-League repo — the training-data source this project relied on since
Phase 1 — stalled at 2026-27 GW1 (confirmed 2026-09-08, `.planning/research/DATA-SOURCE-RESILIENCE.md`).
`data.gw_capture` self-hosts the current season directly from the official FPL API instead. This
document is what to read when that breaks.

## Where the data comes from

The **official FPL API** is the source of truth for the current season's (`config.CURRENT_SEASON`)
per-player per-gameweek rows. Three endpoints, all unauthenticated:

- `bootstrap-static/` — player/team identity, prices, injury status, gameweek metadata
- `fixtures/` — the season's fixture list and difficulty ratings
- `element-summary/{id}/` — one player's full match-by-match history

The **previously-published vaastav repository** (`config.VAASTAV_RAW`) is the source for the ten
cached past seasons — `2016-17` through `2025-26` — and **nothing else**. Those seasons stay fully
cached and unchanged under `data/raw/<season>/`.

`data.gw_capture` writes four files per season, all under `data/raw/<season>/`:

| File | Path | Role |
|---|---|---|
| `merged_gw.csv` | flat, `data/raw/<season>/merged_gw.csv` | read by `data.build_table` — the pipeline's real entry point |
| `players_raw.csv` | flat, `data/raw/<season>/players_raw.csv` | read by `data.id_map` and `data.build_table` |
| `fixtures.csv` | flat, `data/raw/<season>/fixtures.csv` | read by `data.build_table`'s fixture-difficulty join |
| `gw<n>.csv` | ledger directory, `data/raw/<season>/gws/gw<n>.csv` | **bookkeeping only — no consumer opens these.** One file per captured gameweek; `merged_gw.csv` is regenerated from this directory on every run, so it is always safe to delete a single ledger file and re-capture that one gameweek. |

## How to run it

```bash
python -m data.gw_capture
```

On a **quiet day** (no gameweek has newly finished-and-data-checked since the last run): the two
mutable files (`players_raw.csv`, `fixtures.csv`) refresh unconditionally — prices, injury status
and fixture difficulty change continuously even between gameweeks — but zero `element-summary`
requests are made, because every finished gameweek already has a ledger file. Cost: 2 requests.

On a day a **gameweek has just settled** (newly `finished` and `data_checked` in the bootstrap
payload): the same two-file refresh happens, then a full `element-summary` sweep over every player
(currently 656), one ledger file per newly-finished gameweek, and `merged_gw.csv` is regenerated
from the complete ledger directory.

**The backfill the roadmap asked for is exactly what a plain first run does** — there is no
separate backfill flag. The default target set is every finished-and-data-checked gameweek with no
ledger file yet, so running the plain command against an empty `data/raw/2026-27/gws/` directory
captures every settled gameweek in one run.

Other flags:

- `--force` — re-sweep every finished gameweek regardless of ledger presence. The right answer
  after fixing a bug in the capture logic itself (see the Task 2 team-attribution fix in
  `08-BACKFILL-EVIDENCE.md` — the affected gameweeks were re-captured with `--force`), or after an
  upstream schema change is fixed and you need every previously-captured row rebuilt under the new
  mapping. **Not** the right answer for a routine re-run — that is what the plain command already
  does for anything missing.
- `--gw N [N ...]` — capture only the named gameweek(s), regardless of ledger state. The targeted
  single-gameweek recapture: use this to re-pull one gameweek without re-sweeping every other
  finished gameweek.
- `--retries` / `--backoff` — tune outage tolerance for the bootstrap/fixtures fetch (default 3
  retries, base-2 exponential backoff).
- `--sleep` — delay between `element-summary` requests during the sweep (default `0.08`s) — tune
  this down only if you are prepared to be less polite to the FPL API.

## What the previous source is still for

vaastav's repository remains the source for the ten cached past seasons, and nothing else.
`data.ingest.fetch_vaastav_season` (the module that used to own the current season too) now
**declines to download `config.CURRENT_SEASON`'s three files under any flag, including
`--force`** — vaastav's own copy of the current season stalled at a single published gameweek,
so re-running `python -m data.ingest --force` would have replaced this module's full
multi-gameweek capture with that one stale gameweek. The guard holds unconditionally; there is no
flag combination that lets `data.ingest` write over a file `data.gw_capture` owns.

The one remaining use of the previous source for the current season is the **cross-check escape
hatch**, added alongside the guard:

```bash
python -c "from data.ingest import fetch_vaastav_season; fetch_vaastav_season('2026-27', cross_check=True)"
```

This fetches vaastav's published current-season copy and writes it to a `.vaastav-crosscheck`
suffixed filename in the same season directory (e.g. `merged_gw.vaastav-crosscheck.csv`) —
**never** over the captured file. It exists to verify `data.gw_capture`'s own schema mapping
against an independent source, the same check `08-03` hand-rolled against a session-scratch
directory outside the repository before this escape hatch existed. Expect its `xP` column to
disagree with the captured file by design (see the known gap below) and its `team` column to
agree, since both are drawn from the same underlying match data.

## Known gaps

### Expected-points (`xP` / `xp_fpl`) — permanent for GW1 and GW2

Measured on the real 2026-27 capture (`08-BACKFILL-EVIDENCE.md`, §2):

| GW | `xP` non-null fraction |
|---|---|
| 1 | **0.0%** |
| 2 | **0.0%** |
| 3 | **95.72%** resolved (626/626 players in the resolving snapshot; 654 rows captured, so 28 GW3 players outside that snapshot read as missing via a plain dict-lookup miss — expected, not a bug) |

**Reason:** `resolve_xp_for_gw` reads FPL's own expected-points projection from
`data/snapshot.py`'s daily archive, keyed to the gameweek's deadline date. GW1's deadline
(2026-08-21) and GW2's deadline (2026-08-28) both precede the archive's earliest snapshot
(2026-08-31) — the archive did not exist yet at either deadline. There is no earlier snapshot to
fall back to, and the resolution rule never interpolates or reads a later snapshot's *current*
projection to backfill an earlier gameweek's *next* projection.

**Retrain implication:** this is a real, permanent data gap, not a bug a future join fix would
close. When 2026-27 is eventually promoted into `TRAIN_SEASONS`/`TEST_SEASONS`, read GW1/GW2's
null `xp_fpl` as missing data for that feature specifically — the row itself, and every other
column on it, is otherwise complete and correct.

### Current-season odds coverage — absent upstream source, not a join bug

Current-season `odds_pwin` coverage measured at **0.0%** (against a table-wide coverage of 63.8%).
Diagnosed (`08-BACKFILL-EVIDENCE.md`, §4) as `data/odds.py`'s cached `data/raw/odds/2026-27.csv`
being football-data.co.uk's own pre-season "300 Multiple Choices" error page — the file does not
exist on their server yet. This is outside `data.gw_capture`'s and `data.ingest`'s scope; nothing
in this runbook fixes it. The cache-if-exists guard in `data/odds.py` will keep serving that stale
error page forever unless something re-fetches it once the real file is published.

## When the freshness alert fires

`data.gw_capture`'s `main()` checks, at the end of every run, whether any finished-and-data-checked
gameweek still has no ledger file. If one does, it:

1. Calls `ops.notify.report("gw_capture", "freshness", "finished, data-checked gameweek(s) with no captured ledger: [...]")`
2. Prints `[gw_capture] ALERT: finished gameweek(s) with no captured ledger: [...]` to stderr
3. Returns exit code `1` from `main()`

The alert record (one JSON object per line) is appended to `FPL_ALERT_LOG` if set, otherwise
`data/alerts.jsonl` (`config.DATA_DIR / "alerts.jsonl"`), and POSTed to `FPL_ALERT_WEBHOOK` if that
env var is configured. The record carries `ts`, `job` (`"gw_capture"`), `step` (`"freshness"` for a
stalled capture, `"schema"` for a payload-shape guard trip, `"fetch"` for a retry-exhausted
bootstrap/fixtures fetch), `level`, `message` and `host`.

**Diagnostic order when this fires:**

1. Check whether the FPL API itself reports the gameweek as `finished` and `data_checked` yet — an
   event can flip to `finished` before its bonus points and defensive-contribution stats settle;
   if `data_checked` is still `false`, this is not a bug, just early.
2. Check whether the ledger file (`data/raw/2026-27/gws/gw<n>.csv`) exists on disk — a run that
   crashed mid-sweep (transport error, disk full) can leave a finished gameweek uncaptured.
3. Check the per-player failure count in the run's own log output (`[gw_capture] sweep completed
   with N player fetch failure(s)`) — a nonzero count without a full alert means individual players
   failed but the gameweek was still written; a `--force` re-sweep of that one gameweek is usually
   enough to pick up the stragglers.
4. Re-run with `--gw <n> --force` for the specific stalled gameweek.

`data.gw_capture` is not yet wired into `scripts/daily.sh` or `scripts/weekly.sh` — those two
scripts are frozen pending Phase 7's cutover, and wiring this module into the cron schedule is
plan `08-05`'s job. Until then, run it manually or from an ad hoc scheduled job outside those two
scripts.

## What to check after a schema change upstream

`data.gw_capture._require_fields` guards every FPL payload boundary the module reads — bootstrap
elements, bootstrap teams, and every `element-summary` history row — against the field sets it
expects (`_ELEMENT_IDENTITY_KEYS`, `_TEAM_IDENTITY_KEYS`, `_HISTORY_KEYS`). If any of those fields
vanish from an upstream response, the guard **alerts through `ops.notify.report` (step `"schema"`)
and then raises `ValueError` naming the missing field(s)**, before a single all-NaN column could
ever reach `data.build_table`.

The fix for a genuine upstream schema change is a mapping change in `data/gw_capture.py` itself —
update the relevant key list (`_HISTORY_KEYS`, `_ELEMENT_IDENTITY_KEYS`, or `_TEAM_IDENTITY_KEYS`)
to match the new field name or drop a field FPL has removed. Separately, `MERGED_GW_HEADER` is
asserted against `config.MERGED_GW_COLUMNS` **at import time** — `data.gw_capture` will refuse to
even load if a source key `config.MERGED_GW_COLUMNS` depends on stops being a member of the
output header, so a silently-dropped column that a future retrain would trust is not a possible
outcome; the failure surfaces the moment the module is imported, not weeks later at retrain time.

## Related

- `.planning/research/DATA-SOURCE-RESILIENCE.md` — the original finding that vaastav's repo stalled
- `.planning/phases/08-self-hosted-gameweek-data-capture/08-BACKFILL-EVIDENCE.md` — every measured
  number quoted above, captured verbatim from the real 2026-09-12 run
- `data/gw_capture.py` — the module this runbook documents; its own docstring and `--help` output
  are the authoritative CLI surface
- `data/ingest.py` — the current-season guard and cross-check escape hatch on the demoted source
