# Phase 8: Self-Hosted Gameweek Data Capture - Research

**Researched:** 2026-09-11
**Domain:** Batch data-ingestion module (Python/pandas/requests) replacing a third-party GitHub CSV feed with direct FPL-API capture, into an existing leakage-safe ML pipeline
**Confidence:** HIGH

## Summary

This phase adds one new module, `data/gw_capture.py`, that reconstructs vaastav-schema
per-GW rows for the current season (2026-27) directly from the official FPL API
(`bootstrap-static`, `element-summary/{id}/`, `fixtures/`), because vaastav's repo has
stalled at GW1 (verified 2026-09-08 in `.planning/research/DATA-SOURCE-RESILIENCE.md`,
re-confirmed live today: current season is now at GW3 finished, GW4 deadline
2026-09-12T12:30:00Z — still one day before rollover risk becomes acute, but the two
missing gameweeks are still missing from vaastav). The milestone-level research
(`DATA-SOURCE-RESILIENCE.md`) already did the hard sourcing work — this document adds
what that research did not need to check: the **exact on-disk contract** three
downstream modules (`build_table.py`, `id_map.py`, `odds.py`) actually read, verified
by opening those files this session, plus one live API round-trip today to confirm the
field inventory hasn't drifted since 2026-09-08.

**Two corrections to the milestone research's proposed design, found by reading the
actual consumer code (not assumed from the vaastav repo's remote layout):**

1. **No `gws/` subdirectory locally.** The remote vaastav URL path is
   `.../data/{season}/gws/merged_gw.csv`, but `data/ingest.py:56-59` downloads it to
   `config.RAW_DIR / season / "merged_gw.csv"` — flat, no `gws/` folder — and
   `build_table.py:34` (`path = config.RAW_DIR / season / "merged_gw.csv"`) and
   `build_table.py:60` (`path = config.RAW_DIR / season / "fixtures.csv"`) read that
   same flat path. `data/raw/2026-27/` on disk today confirms this: it contains
   `fixtures.csv` and `players_raw.csv` directly, no `gws/` subfolder. `gw_capture.py`
   must write `merged_gw.csv` to `data/raw/2026-27/merged_gw.csv` (flat) for
   `build_table.py` to ever see it — per-GW `gw{N}.csv` files (if written at all) are
   an audit/idempotency artifact for `gw_capture.py`'s own bookkeeping, not a path any
   consumer reads.
2. **The `team` column is the full team name, not the short code.** A live fetch of
   vaastav's real 2025-26 `merged_gw.csv` today shows `team=Sunderland` (matching FPL
   bootstrap's `teams[].name`), not `SUN` (`teams[].short_name`). This matters because
   `build_table.py:135` joins odds onto `(season, _date, team, was_home)`, and
   `data/odds.py:80-86` expects the same full-name convention. `data/snapshot.py:73`
   builds its own `team` column from `short_name` — that is snapshot.py's own
   convention for a different consumer (the watchlist) and must **not** be copied into
   `gw_capture.py`.

**Primary recommendation:** build `gw_capture.py` as a `data/live_history.py`-shaped
module (full `element-summary` sweep with the same rate-limit/retry posture as
`data/snapshot.py`), writing exactly the three flat files `build_table.py`/`id_map.py`
already read (`merged_gw.csv`, `fixtures.csv`, `players_raw.csv`) under
`data/raw/{CURRENT_SEASON}/`, with zero changes to `build_table.py`/`id_map.py`. Wire
the `scripts/daily.sh` line and the `ingest.py` current-season guard in the same phase
plan, but do not execute the edit until Phase 7 completes (that file is frozen).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fetch current-season per-player GW history | Data Ingest (`data/gw_capture.py`, new) | — | Same tier as `data/live_history.py`/`data/snapshot.py` — direct FPL API consumers |
| Map element-summary fields -> vaastav schema | Data Ingest (`data/gw_capture.py`) | — | Pure transform, no persistence side-effects beyond the CSV writers |
| Resolve `xP` from daily snapshots | Data Ingest (`data/gw_capture.py`) reads `data/snapshot.py` output | Data Build (documents the gap when absent) | Snapshot data already exists as a separate cached artifact; gw_capture only reads it, never re-fetches |
| Persist vaastav-schema CSVs | Data Ingest (`data/raw/{season}/*.csv`) | — | Same location and format `data/ingest.py` already writes to for other seasons |
| Consume captured rows into canonical table | Data Build (`data/build_table.py`, `data/id_map.py`) | — | **Zero changes** — this is the entire point of matching vaastav's schema/paths exactly |
| Cron scheduling | Orchestration (`scripts/daily.sh`) | — | Frozen until Phase 7 CUT-01 completes; design the line now, land it after |
| Freshness/failure alerting | Observability (`ops/notify.py`) | — | Reuse the existing `report()` call, matching every other `data/*` cron step |

## User Constraints

No `08-CONTEXT.md` exists yet (phase directory contains only a placeholder
`.gitkeep`) — `/gsd-discuss-phase 8` has not run. There are no locked decisions or
discretion areas to copy verbatim. The planner should treat every design choice below
as **research-recommended, not user-locked** until a discuss-phase pass confirms it.

## Phase Requirements

Roadmap marks this phase `Requirements: TBD` — no `REQ-ID`s exist in
`REQUIREMENTS.md` for Phase 8 (it was added mid-milestone as an unplanned insertion,
per `STATE.md`'s Roadmap Evolution log: *"Phase 8 added: Self-Hosted Gameweek Data
Capture — vaastav repo stalled..."*). The planner should treat the phase goal
sentence in the roadmap as the acceptance contract in lieu of numbered requirements,
or run `/gsd-phase` to backfill IDs before planning if the project wants formal
traceability. This research supports the goal's four clauses directly:

| Goal clause | Research support |
|---|---|
| "reconstructs vaastav-schema per-GW rows (`gw{N}.csv`, `merged_gw.csv`, refreshed `players_raw.csv`/`fixtures.csv`) directly from the official FPL API into `data/raw/2026-27/`" | Schema Mapping Table + Flat-Path Pitfall below |
| "runs from `scripts/daily.sh`" | Cron Wiring section (post-Phase-7) |
| "backfills the already-finished GWs before season rollover" | Backfill section — GW1-3 confirmed still retrievable from `element-summary` today |
| "`build_table`/`id_map` consume the captured rows unchanged" | Verified by reading both files this session — zero code changes needed if the schema mapping is followed |

## Standard Stack

No new dependencies. `requests`, `pandas`, `argparse` are already pinned in
`requirements.txt` and used identically by `data/live_history.py` and
`data/snapshot.py`, the two closest precedents. This is an argument for structuring
`gw_capture.py` as "one more module in the same shape," not a new subsystem.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| A fresh independent `element-summary` fetch loop in `gw_capture.py` | Extend `data/live_history.py`'s cache (`element_history.parquet`) to carry the full field set, and have `gw_capture.py` build off that | Avoids a second ~656-request sweep per day, but `live_history._FIELD_MAP` (18 fields) deliberately drops `opponent_team`, `was_home`, `fixture`, `value`, `selected`, transfers, cards, own goals, pens, team scores — every field `merged_gw.csv` needs beyond rolling-form stats. Widening `_FIELD_MAP` changes a module Phase 4/6 already depend on (its cache feeds `predict.live`'s live rolling-form path) — **flag as an open question for discuss-phase**, default recommendation is a separate fetch loop copying the *pattern* (rate limit, retry, per-player try/except) but not the *cache file*. |
| Writing per-GW `gw{N}.csv` files that a consumer reads | Only write `merged_gw.csv` (the concatenation) since that's the only file `build_table.py` opens | Per-GW files are still useful as `gw_capture.py`'s own idempotency ledger ("has GW3 already been captured?") and as the cross-check artifact against vaastav's own GW1 file the milestone research proposed — keep them, but document clearly that they are *not* on any consumer's read path. |

## Package Legitimacy Audit

No external packages are introduced by this phase. `requests`/`pandas` are existing,
already-locked, already-audited dependencies (Phase 5's `requirements.txt` hash-lock).
No `checkpoint:human-verify` needed for package installs in this phase's plan.

## Architecture Patterns

### System Architecture Diagram

```
                    FPL official API (public, free)
        ┌───────────────────┬───────────────────┬──────────────────┐
        │ bootstrap-static/  │ element-summary/{id}/  │ fixtures/    │
        │ (players, teams,   │ (per-player completed  │ (FDR,        │
        │  events.finished)  │  GW history, current    │  scores)     │
        │                    │  season only)           │              │
        └─────────┬──────────┴───────────┬─────────────┴──────┬───────┘
                  │                       │                    │
                  ▼                       ▼                    ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  data/gw_capture.py  (NEW)                                    │
        │  1. determine finished GWs from bootstrap events[].finished   │
        │  2. sweep element-summary per player (rate-limited, retried,  │
        │     same posture as data/live_history.py / data/snapshot.py)  │
        │  3. map fields -> vaastav MERGED_GW_COLUMNS source-key names  │
        │  4. join name/team(full-name)/position from bootstrap         │
        │  5. resolve xP from nearest data/snapshot.py capture <= the   │
        │     GW's deadline (data/snapshots/*.parquet, may be NaN)      │
        │  6. atomic-write (tmp + os.replace, per data/snapshot.py      │
        │     precedent) into data/raw/{CURRENT_SEASON}/*.csv (flat)    │
        └───────────────────────────┬────────────────────────────────┘
                                     │  writes flat CSVs, vaastav-shaped
                                     ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  data/raw/2026-27/                                            │
        │    merged_gw.csv   <- ONLY file build_table.py reads          │
        │    fixtures.csv    <- ONLY file build_table.py's FDR join reads│
        │    players_raw.csv <- ONLY file id_map.py reads                │
        │    gws/gw{N}.csv   <- audit/idempotency ledger, NOT consumed   │
        └───────────────────────────┬────────────────────────────────┘
                                     │  UNCHANGED consumer code
                                     ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  data/build_table.py  ·  data/id_map.py   (zero code changes) │
        └───────────────────────────┬────────────────────────────────┘
                                     ▼
                    data/processed/player_gw.parquet (2026-27 rows now present)
                                     │
                                     ▼
                    features/engineer.py -> models/train.py, backtest/*
```

### Recommended Project Structure

```
data/
├── gw_capture.py         # NEW: this phase's only new production module
├── ingest.py             # EDIT (post-Phase-7): current-season vaastav guard
├── live_history.py       # UNCHANGED short-term (see Alternatives Considered)
├── snapshot.py           # UNCHANGED — read-only dependency (xP source)
scripts/
├── daily.sh              # EDIT (post-Phase-7): add run_step data.gw_capture
tests/
├── test_gw_capture.py    # NEW: schema-completeness + backfill + GW1 cross-check
```

### Pattern 1: Idempotent, atomic, per-finished-GW capture

**What:** Determine the set of finished GWs from `bootstrap-static`'s
`events[].finished`, skip any GW whose `gw{N}.csv` already exists on disk unless
`--force`, and write every output file via a tmp-file + `os.replace` swap.
**When to use:** Every write in `gw_capture.py` — this is the exact pattern
`data/snapshot.py:147-154` already uses and that this phase's own description calls
"idempotent" and "cron-friendly."
**Example (adapted from the verified precedent):**
```python
# Source: data/snapshot.py:137-156 (read this session), adapted
tmp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
try:
    df.to_csv(tmp, index=False)
    os.replace(tmp, out)
except Exception:
    if tmp.exists():
        tmp.unlink()
    raise
```

### Pattern 2: Schema mapping table (element-summary -> vaastav source-key names)

Verified live today (`GET element-summary/1/`) against `config.MERGED_GW_COLUMNS`
(`config.py:338-379`, read this session) and vaastav's real `merged_gw.csv` header
(fetched live today). Columns not in this table need a join from `bootstrap-static`.

| vaastav source key (`config.MERGED_GW_COLUMNS` LHS) | element-summary field | Direct? |
|---|---|---|
| `GW` | `round` | Yes |
| `element` | (the id used in the URL) | Yes |
| `name` | — | **Join**: `bootstrap.elements[].web_name` (or first+second name) |
| `position` | — | **Join**: `bootstrap.elements[].element_type` -> `{1:"GK",2:"DEF",3:"MID",4:"FWD"}` (same `_POS` map as `id_map.py:26`/`data/snapshot.py:34`) |
| `team` | — | **Join, full name**: `bootstrap.elements[].team` -> `bootstrap.teams[].name` (NOT `short_name` — see Pitfall 2) |
| `opponent_team` | `opponent_team` | Yes — already a numeric team ID in both sources |
| `was_home` | `was_home` | Yes |
| `kickoff_time` | `kickoff_time` | Yes — same ISO8601 format |
| `fixture` | `fixture` | Yes — same global FPL fixture ID space |
| `minutes`, `starts`, `total_points`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_missed`, `penalties_saved`, `saves`, `yellow_cards`, `red_cards`, `bonus`, `bps` | same names | Yes, 1:1 |
| `expected_goals`→`xg`, `expected_assists`→`xa`, `expected_goal_involvements`→`xgi`, `expected_goals_conceded`→`xgc` | same source names | Yes, 1:1 (element-summary returns them as strings, e.g. `"0.00"` — `build_table.py:46-47` already coerces via `pd.to_numeric`) |
| `influence`, `creativity`, `threat`, `ict_index` | same names | Yes, 1:1 (also string-typed) |
| `value` | `value` | Yes — same tenths-of-£m convention (verified: `value=60` == £6.0m both sides) |
| `selected` | `selected` | Yes |
| `transfers_in`, `transfers_out`, `transfers_balance` | same names | Yes |
| `team_h_score`, `team_a_score` | same names | Yes |
| `xP` | — | **No direct field.** Resolve from `data/snapshot.py`'s daily capture: nearest snapshot with `date <= ` the GW's deadline day, column `ep_this`. See Pitfall 3 — this will be NaN for GW1/GW2 given the current snapshot archive. |

### Anti-Patterns to Avoid

- **Writing `merged_gw.csv` under a `gws/` subfolder because that's where vaastav's
  remote URL puts it.** `build_table.py` never looks there locally — see Flat-Path
  Pitfall above. This would silently produce a `gw_capture.py` that "succeeds" but
  whose output `build_table.py` never sees (the existing `[skip] {season}: no
  merged_gw.csv` print in `build_table.py:36` would keep firing forever).
- **Reusing `data/snapshot.py`'s `team = team_id.map(short_name)` line verbatim.**
  Produces `"SUN"` where every downstream consumer (`odds.py`, `build_table.py`'s
  odds join) expects `"Sunderland"`.
- **Treating `ingest.py`'s per-file cache-if-exists behavior as the right default for
  `gw_capture.py`.** `data/ingest.py:32-48`'s `_download()` skips re-fetching if the
  destination file already exists — correct for immutable past-season vaastav data,
  wrong for `fixtures.csv`/`players_raw.csv` in the current season, which change
  continuously (prices, injuries, FDR re-ratings, newly-played fixtures). This phase's
  own goal text says "refreshed `players_raw.csv`/`fixtures.csv`" — the refresh must
  be unconditional (or condition on a freshness window), not `ingest.py`'s
  exists-then-skip pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry/backoff on the FPL API | A bespoke retry loop | The exact `_fetch_bootstrap` shape in `data/snapshot.py:100-134` (bounded retries, exponential backoff + jitter, retryable-status set `{429,500,502,503,504}`, non-retryable 4xx raises immediately) | Already reviewed, tested (`tests/test_cron.py`), and matches this project's REL-02 hardening bar |
| Atomic file writes | Direct `df.to_csv(path)` | tmp-file + `os.replace()`, per `data/snapshot.py:147-154` and `ops/jsonio.py:47-65` | A crash mid-write must never leave a truncated `merged_gw.csv` that `build_table.py` then partially reads |
| Failure alerting | `print()` to stderr only | `ops.notify.report(job, step, message)` (`ops/notify.py:29`) | Every other cron step in `scripts/daily.sh` reports through this single call site; a silent `gw_capture.py` failure recreates exactly the "nothing told us the feed stalled" problem this phase exists to fix |
| JSON reads of `bootstrap-static.json` | Bare `json.load(open(...))` | `ops.jsonio.read_json(path, what=..., remedy=...)` (`ops/jsonio.py:21`) | `tests/test_reliability.py` (read this session) scans every tracked `.py` file for bare `open()` calls repo-wide and fails the build on a new one — `data/id_map.py:53` and `data/live_history.py:48` already route through it for this exact payload |

**Key insight:** every piece of infrastructure `gw_capture.py` needs (retry/backoff,
atomic writes, alerting, safe JSON reads) already exists in this codebase in a
tested, hardened form from Phase 6. This phase is schema/mapping work wrapped around
already-solved plumbing, not new infrastructure.

## Runtime State Inventory

Phase 8 is not a rename/refactor, but it does redirect a live-pipeline data source and
writes into paths that already hold real (if stale) files, so the categories are worth
answering explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data/raw/2026-27/fixtures.csv` and `players_raw.csv` already exist on disk (dated 2026-08-21, pre-GW1) — no `merged_gw.csv` yet. Confirmed via `ls` this session. | `gw_capture.py` must overwrite both (they are stale — `fixtures.csv` still shows every fixture `finished=False`) and create `merged_gw.csv` for the first time. No migration of old rows needed; it's a full-file replace. |
| Live service config | None — `scripts/daily.sh` is frozen (Phase 7) and not yet wired; no live cron references this module. | Design the `run_step data.gw_capture ...` line now (this phase's plan), land it in a follow-up edit gated on Phase 7 completion. |
| OS-registered state | None. | — |
| Secrets/env vars | None — the FPL API is unauthenticated, matching every other `data/*` module. | — |
| Build artifacts | `data/raw/live/element_history.parquet` (the `live_history.py` cache) is unaffected unless the "extend `_FIELD_MAP`" alternative is chosen (see Alternatives Considered) — default recommendation leaves it untouched. | None under the default recommendation. |

## Common Pitfalls

### Pitfall 1: Writing per-GW files where no consumer looks

**What goes wrong:** `gw_capture.py` writes `data/raw/2026-27/gws/gw2.csv`,
mirroring vaastav's remote layout, and the pipeline silently keeps reporting `[skip]
2026-27: no merged_gw.csv` forever.
**Why it happens:** The remote vaastav repo layout (`.../data/{season}/gws/...`) and
the local cache layout (`config.RAW_DIR / season / "merged_gw.csv"`, flat) are
different, and it's easy to copy the remote shape by habit.
**How to avoid:** `merged_gw.csv` must land at `data/raw/{CURRENT_SEASON}/merged_gw.csv`
— verified directly against `build_table.py:34` and the real on-disk layout of
`data/raw/2025-26/` (also flat) this session.
**Warning signs:** `python -m data.build_table` still prints `[skip] 2026-27: no
merged_gw.csv (run ingest first)` after running `gw_capture.py`.

### Pitfall 2: Team name convention mismatch

**What goes wrong:** Odds enrichment (`build_table.py:135`, an existing optional
join) silently drops to 0% coverage for 2026-27 rows because `team` doesn't match
`odds.py`'s full-name convention.
**Why it happens:** `data/snapshot.py`'s own `team` column (short_name, "SUN") is the
nearest-looking precedent in the codebase and is easy to copy by analogy — but it
solves a different problem for a different consumer.
**How to avoid:** Build `team` from `bootstrap.teams[].name` (full name), verified
live today (vaastav's real `merged_gw.csv` shows `team=Sunderland`, and
`bootstrap-static`'s matching team entry has `name: "Sunderland"`, `short_name:
"SUN"`).
**Warning signs:** `build_table.py`'s printed `[odds]  coverage: X%` line drops
sharply for 2026-27 rows specifically (odds coverage is a pre-existing gap for
2016-19 anyway, per `config.TEAM_STRENGTH_COLS`'s comment, so a 2026-27-specific drop
is the signal to watch, not overall coverage).

### Pitfall 3: `xP` will be NaN or stale for the backfilled GWs — this is a real gap, not a bug

**What goes wrong:** A plan assumes, per the milestone research's phrasing ("`xP` for
GW1-3 comes from the snapshots already sitting in `data/snapshots/`"), that a
same-day-or-earlier snapshot exists for every finished GW's deadline. It doesn't.
**Why it happens:** `data/snapshots/` (checked this session: `2026-08-31.parquet`,
`2026-09-07.parquet`, `2026-09-11.parquet`, `2026-09-12.parquet`) only has 4 files.
GW1's deadline was 2026-08-21 and GW2's was 2026-08-28 — both **before** the
earliest available snapshot (2026-08-31). There is no pre-deadline snapshot at all
for GW1 or GW2; GW3 (deadline 2026-09-04) has one 4-day-stale option
(2026-08-31).
**How to avoid:** Design `gw_capture.py`'s xP-resolution step to tolerate and report
this (NaN when no snapshot precedes the deadline, exactly the existing
`_join_fixture_difficulty`-style tolerance already in `build_table.py`), rather than
raising or silently mis-attributing a later snapshot. `xp_fpl` (and its rolled
`xp_fpl_r3/r5/r10/rall` derivatives, confirmed live model features per
`features/engineer.py:39` and STATE.md's Phase 10 `ep_next_lag` decision log) will
simply carry more NaN for early 2026-27 rows than a normal season — acceptable since
`config.TRAIN_SEASONS`/`TEST_SEASONS` don't consume 2026-27 yet
(`backtest/walk_forward.py:46`: `DATA_SEASONS = config.SEASONS[:-1]  # drop
2026-27`), but worth a one-line note in the module's docstring so a future retrain
cycle doesn't mistake NaN-heavy early rows for a bug.
**Warning signs:** A future promotion of 2026-27 into `TRAIN_SEASONS` shows
anomalously high `xp_fpl_*` null rates for GW1-3 specifically, and someone spends
time debugging the join before checking snapshot coverage.

### Pitfall 4: `element-summary` sweep volume and rate limits

**What goes wrong:** A naive per-player fetch loop with no delay gets rate-limited
or blocked mid-sweep, corrupting a partial `merged_gw.csv`.
**Why it happens:** `bootstrap-static` today returns 656 elements (verified live this
session) — a full sweep is 656 HTTP requests.
**How to avoid:** Reuse `data/live_history.py:45-78`'s exact posture: `time.sleep(0.08)`
between requests, per-player `try/except requests.RequestException` that logs and
continues rather than aborting the whole sweep, and printed progress every 100
players. That module already does a full 656-player sweep daily/weekly without
incident.
**Warning signs:** Partial `merged_gw.csv` (fewer distinct `player_id` values than
`bootstrap-static.elements`) with no corresponding warning line in the run's stdout.

### Pitfall 5: Season rollover timing is not as urgent as GW-count alone suggests, but don't rely on that

**What goes wrong:** Treating "GW4 deadline is tomorrow" as the hard deadline, when
the actual hard deadline (per the milestone research and this phase's own goal text)
is **season rollover** (~June 2027), which deletes `element-summary` history for
*every* gameweek of 2026-27, not just the currently-unfinished ones.
**Why it happens:** The Phase description's framing ("2026-27 GWs 1-3 are already
finished... the missing GW2/GW3 rows must be reconstructed from element-summary
before rollover") can read as more time-pressured than it is — rollover is ~9 months
away, and `element-summary` still serves rounds 1-3 fine today (verified live this
session: `history rounds: [1, 2, 3]`).
**How to avoid:** Don't let planning treat this as an emergency same-day patch (it
isn't — GW1-3 are safely retrievable right now and will remain so for months); do
treat the backfill as unconditionally required before Phase 8 closes, since every
week that passes without a working `gw_capture.py` widens the gap vaastav will never
fill.
**Warning signs:** N/A — this is a planning-emphasis note, not a code defect to detect.

## Code Examples

### Retry/backoff precedent to copy the shape of, not call directly

```python
# Source: data/snapshot.py:100-134 (read this session) — copy this shape for
# gw_capture.py's own bootstrap-static fetch, and reuse the *sleep-per-request*
# idea (not this exact function) for the element-summary sweep loop below.
def _fetch_bootstrap(*, retries: int, backoff: float) -> dict:
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(f"{config.FPL_API}/bootstrap-static/", headers=_HEADERS, timeout=30)
            if r.status_code in _RETRYABLE_STATUS:
                raise requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            last_exc = exc
            is_last = attempt == retries
            ...
```

### Element-summary sweep precedent (field set needs widening, structure is right)

```python
# Source: data/live_history.py:45-78 (read this session) — the loop shape
# (per-player try/except, 0.08s sleep, progress every 100) is exactly right;
# gw_capture.py needs the FULL history dict per row, not the reduced _FIELD_MAP.
for i, pid in enumerate(ids):
    try:
        r = requests.get(f"{config.FPL_API}/element-summary/{pid}/",
                         headers=_HEADERS, timeout=20)
        r.raise_for_status()
        hist = r.json().get("history", [])
    except requests.RequestException as exc:
        print(f"  [warn] element {pid}: {exc}")
        continue
    for h in hist:
        ...  # gw_capture.py: keep every field, not just ROLL_STATS's 18
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| vaastav/Fantasy-Premier-League as sole current-season source | Official FPL API captured directly, vaastav demoted to past-season backfill only | This phase (2026-09-11 research; vaastav stall first observed 2026-09-08) | Removes a single-maintainer GitHub repo as a single point of failure for live training data; `element-summary`'s per-season retention window becomes the new hard constraint to track instead of a maintainer's commit cadence |

**Deprecated/outdated:** None — vaastav data for seasons 2016-17 through 2025-26 stays
fully valid and cached; only the *current*-season role changes.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `element-summary`'s field inventory (verified live 2026-09-08 and again 2026-09-11) will remain stable through the rest of this phase's execution window | Schema Mapping Table | Low — FPL added `defensive_contribution`-family fields mid-2026-27 already (visible in the live payload) without breaking older fields; the pattern is additive, but a future FPL schema change could still require a `gw_capture.py` update |
| A2 | Extending `data/live_history.py`'s `_FIELD_MAP` to also serve `gw_capture.py` is undesirable versus a second independent fetch loop | Alternatives Considered | Medium — this is a genuine design tradeoff (API call volume vs. blast radius on an existing, depended-upon module) that should be confirmed in `/gsd-discuss-phase 8`, not decided unilaterally by the planner |
| A3 | The daily cadence proposed by the milestone research (run `gw_capture.py` from `scripts/daily.sh`, bounding loss to <24h) is still the right cadence, unchanged since 2026-09-08 | Architecture Patterns / Pattern 1 | Low — no new information changes this; included for completeness since it's inherited, not independently re-verified this session |

## Open Questions

1. **Should `gw_capture.py` reuse or extend `data/live_history.py`'s cache, or run a fully independent element-summary sweep?**
   - What we know: `live_history.py`'s cache (`element_history.parquet`) already sweeps the same endpoint daily/weekly for `predict.live`'s rolling-form path, but deliberately drops the fields `merged_gw.csv` needs (`opponent_team`, `was_home`, `fixture`, `value`, `selected`, transfers, cards, own goals, pens, team scores — `live_history.py:33-42`'s `_FIELD_MAP`).
   - What's unclear: whether doubling the API call volume (two independent 656-request sweeps per day instead of one shared one) is acceptable, versus the blast-radius risk of widening a field map an existing, working module depends on.
   - Recommendation: default to an independent fetch loop in `gw_capture.py` (lowest blast radius, same rate-limit posture); raise as an explicit discretion item in discuss-phase since it's a real judgment call, not something the research can settle unilaterally.

2. **What should happen to `xp_fpl` NaN-heaviness for GW1/GW2 once 2026-27 is eventually promoted into `TRAIN_SEASONS`?**
   - What we know: no pre-deadline snapshot exists for GW1 or GW2 (Pitfall 3); this is a genuine, permanent data gap for those two gameweeks' `xp_fpl` feature.
   - What's unclear: whether a future retrain cycle needs an explicit fallback (e.g., treat pre-first-snapshot GWs as `xp_fpl = NaN` forever, vs. attempting a synthetic backfill from FPL's `dream_team`/`ep_next` historical archive if one exists).
   - Recommendation: document the gap in `gw_capture.py`'s own docstring/README note (this phase's Task 4, per the milestone research's task sizing) and defer any synthetic-backfill decision to whichever future phase actually promotes 2026-27 into training — out of scope here since `backtest/walk_forward.py:46` already excludes 2026-27.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| FPL official API (`fantasy.premierleague.com/api`) | Core fetch (`bootstrap-static`, `element-summary`, `fixtures`) | Yes — live-verified this session (200 OK, current schema matches milestone research) | n/a (public HTTP API, unversioned) | None needed — this phase's entire premise is that this is the most reliable source available |
| `requests`, `pandas` | HTTP + CSV/DataFrame handling | Yes — already pinned in `requirements.txt`, used identically by 3 sibling modules | pinned (Phase 5 hash-lock) | — |
| conda env `python314` | All Python execution | Assumed available per CLAUDE.md/project convention | 3.14 | — |

**Missing dependencies with no fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (config: `pytest.ini`) |
| Config file | `pytest.ini` (`addopts = -p no:playwright -p no:seleniumbase`, `testpaths = tests`) |
| Quick run command | `python -m pytest tests/test_gw_capture.py -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements -> Test Map

No numbered `REQ-ID`s exist for this phase (see Phase Requirements section). Mapping
against the roadmap goal's own clauses instead:

| Goal clause | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| Schema completeness | Every `config.MERGED_GW_COLUMNS` source key is produced by `gw_capture.py`'s output frame | unit | `pytest tests/test_gw_capture.py::test_schema_completeness -x` | ❌ Wave 0 |
| GW1 cross-check | Self-built GW1 row set matches vaastav's own published GW1 CSV on shared keys (row count + per-column equality) | integration | `pytest tests/test_gw_capture.py::test_gw1_matches_vaastav -x` | ❌ Wave 0 |
| Idempotency | Re-running `gw_capture.py` without `--force` is a no-op (matches `data/snapshot.py`'s own idempotency test pattern in `tests/test_cron.py`) | unit | `pytest tests/test_gw_capture.py::test_idempotent_without_force -x` | ❌ Wave 0 |
| End-to-end build | `build_table.py` run after `gw_capture.py` produces 2026-27 rows with position/FDR coverage, no code changes | integration | `pytest tests/test_gw_capture.py::test_build_table_ingests_captured_rows -x` | ❌ Wave 0 |
| Team-name convention | Captured `team` column matches `bootstrap.teams[].name` (full name), not `short_name` | unit | `pytest tests/test_gw_capture.py::test_team_column_is_full_name -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_gw_capture.py -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_gw_capture.py` — new file, covers every row in the Phase Requirements -> Test Map above. Follow `tests/test_availability.py`'s isolation discipline (`monkeypatch` any module-level path constants; `responses`-mock the FPL API, matching `tests/test_cron.py`'s `_isolate_snapshot_and_alerts` fixture pattern) so tests never touch the real `data/raw/2026-27/` files.
- [ ] No new shared fixtures needed — `tests/test_api.py::fake_boot` (already imported by `test_availability.py` and `test_cron.py`) is the existing bootstrap-static mock fixture; reuse it.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | FPL API is unauthenticated; no credentials involved |
| V3 Session Management | No | Stateless HTTP GETs |
| V4 Access Control | No | No access-control surface introduced |
| V5 Input Validation | Yes | Schema validation on `bootstrap-static`/`element-summary` payloads, matching the existing `REL-03` pattern (`data/id_map.py:53-54` and `data/live_history.py:48-49` already route through `ops.jsonio.read_json` with actionable `what`/`remedy` messages; extend the same posture to `gw_capture.py`'s own bootstrap read, and add an explicit "unrecognised field" guard on the element-summary response shape mirroring `data/availability.py`'s `_require_columns` pattern, `data/availability.py:121-127`) |
| V6 Cryptography | No | No secrets, no crypto operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Upstream API schema drift silently producing an all-NaN or malformed column | Tampering (of trust, not of data) | Fail loudly per `data/availability.py`'s `_require_columns`/unrecognised-status-code pattern (`data/availability.py:121-127`, `:360-368`) — raise naming the offending field rather than writing a corrupt `merged_gw.csv` that `build_table.py` then silently mis-trains on |
| Partial/interrupted write during the ~656-request sweep corrupting `merged_gw.csv` | Tampering | Atomic tmp-file + `os.replace()` (Pattern 1 above) — never a partial file visible at the final path |
| A stale cached `players_raw.csv`/`fixtures.csv` silently used forever because `ingest.py`'s cache-if-exists guard was copied verbatim | Repudiation (silent staleness, no signal) | Unconditional overwrite (or explicit freshness check) for current-season files, per Anti-Pattern above; alert via `ops.notify.report()` on fetch failure so staleness is visible the same day, matching this phase's own stated freshness-monitoring goal |

## Sources

### Primary (HIGH confidence)

- `.planning/research/DATA-SOURCE-RESILIENCE.md` (this project's own milestone-level research, dated 2026-09-08) — the sourcing comparison (vaastav vs. self-host vs. FPL-Core-Insights vs. others), the field-inventory verification, and the recommended module design this document builds on
- `data/ingest.py`, `data/build_table.py`, `data/id_map.py`, `data/snapshot.py`, `data/live_history.py`, `data/availability.py`, `config.py`, `ops/jsonio.py`, `ops/notify.py`, `scripts/daily.sh`, `scripts/snapshot_catchup.sh`, `tests/test_reliability.py`, `tests/test_leakage.py`, `tests/test_availability.py`, `tests/test_cron.py`, `backtest/walk_forward.py` — all opened and read this session
- `https://fantasy.premierleague.com/api/bootstrap-static/` — live fetch this session (2026-09-11), confirms GW1-3 finished, GW4 deadline 2026-09-12T12:30:00Z, `data_checked=True` for GW1-3
- `https://fantasy.premierleague.com/api/element-summary/1/` — live fetch this session, confirms `history` still serves rounds 1-3 with the full field set `DATA-SOURCE-RESILIENCE.md` documented on 2026-09-08 (including the new `defensive_contribution` family)
- `https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/2025-26/gws/merged_gw.csv` — live fetch this session, confirms the real column header and `team=Sunderland` (full-name) convention
- `data/raw/2026-27/` and `data/raw/2025-26/` (`ls` this session) — confirms the flat local layout (no `gws/` subfolder) that `build_table.py`/`id_map.py` actually read

### Secondary (MEDIUM confidence)

None beyond the above — no external web search was needed this session; all claims trace to either this session's direct code reads/live API calls or the prior milestone research document.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, reuses three already-hardened sibling modules verified by direct reading
- Architecture: HIGH — schema mapping and path contract verified against actual consumer code, not inferred from the vaastav repo's remote layout
- Pitfalls: HIGH — all five pitfalls are grounded in a file this session actually opened or a live API/CSV fetch performed this session, with exact line numbers and verbatim quotes

**Research date:** 2026-09-11
**Valid until:** 30 days (the FPL API's field inventory is stable season-to-season but the phase's own urgency argument — element-summary retention — means a re-check immediately before execution, especially of `bootstrap-static.events[].finished` state and the daily-snapshot archive's coverage, is cheap and worthwhile)
