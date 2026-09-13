---
phase: 08-self-hosted-gameweek-data-capture
reviewed: 2026-09-12T08:37:34Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - data/gw_capture.py
  - data/ingest.py
  - data/team_strength.py
  - docs/runbooks/gameweek-data-capture.md
  - tests/test_api.py
  - tests/test_gw_capture.py
  - tests/test_leakage.py
  - tests/test_ci_cd_artifacts.py
  - tests/test_crosswalk.py
  - tests/test_experiments.py
  - tests/test_rl_env.py
  - tests/test_rl_isolation.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-09-12T08:37:34Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Phase 08 self-hosted gameweek capture module (`data/gw_capture.py`), the
`data/ingest.py` current-season guard/cross-check escape hatch, the small `data/team_strength.py`
in-progress-season carve-out, the accompanying runbook, and `tests/test_gw_capture.py` /
`tests/test_api.py` / `tests/test_leakage.py`. The remaining five test files
(`test_ci_cd_artifacts.py`, `test_crosswalk.py`, `test_experiments.py`, `test_rl_env.py`,
`test_rl_isolation.py`) were changed inside the diff window by earlier Phase 5/Phase 9 commits, not
Phase 08 — findings from those files are attributed accordingly below.

The core capture path is well-guarded against upstream schema drift (`_require_fields`, the
import-time `MERGED_GW_HEADER` assertion) and the atomic-write / ledger-regeneration design is
sound. However, one genuine BLOCKER survives: the `--gw N` explicit-capture path can write a
permanent, silently-poisoned empty ledger for a gameweek that hasn't finished yet, defeating both
the default backfill logic and the freshness alert this whole module exists to provide. Three
further WARNING-level robustness gaps and two INFO-level nits round out the findings.

## Critical Issues

### CR-01: Explicit `--gw N` capture of an unfinished gameweek writes a permanent, silent empty ledger that defeats the freshness alert

**File:** `data/gw_capture.py:409-411, 444-450, 453-461, 513-519`
**Issue:**

`capture()`'s target resolution lets an explicit `gws=` argument "always win" and sweep in full
(line 513-514), bypassing the `finished_gws(boot)` filter entirely. If the named gameweek has not
yet been played (no `element-summary` history rows have `round == gw` yet), `build_gw_frame`
(lines 409-411) filters every history row out, producing a 0-row `DataFrame` that is still written
to `data/raw/<season>/gws/gw<n>.csv` via `write_csv_atomic` (line 531).

From that point on:

- `captured_gws()` (lines 444-450) determines "already captured" purely from **ledger file
  presence** (`gw*.csv` existing on disk), not row count or content.
- `check_freshness()` (lines 453-461) — the function whose entire job is "make a stalled capture
  never silent" — subtracts `captured_gws()` from `finished_gws(boot)`, so once the empty file
  exists, this gameweek is permanently excluded from the freshness alert.
- The default plain-run backfill logic (`already = captured_gws(); targets = [gw for gw in
  finished if gw not in already]`, lines 518-519) will never re-target this gameweek once it
  actually finishes, because it already "has a ledger file."

The result: one accidental `python -m data.gw_capture --gw <future-gw>` (e.g. during ad-hoc
debugging, or a script that pre-seeds every gameweek number in a range) creates a real gameweek's
data permanently as an empty stub — no exception, no `ops.notify.report` alert, and no future
plain run or freshness check will ever flag or fix it. This is exactly the "stalled capture is
never silent" failure mode the module's own docstring (lines 28-31) and the runbook's "When the
freshness alert fires" section claim to have eliminated — but only for the *implicit* backfill
path, not the explicit `--gw` path.

**Fix:** Either (a) refuse to write a ledger file for a target gameweek with zero matched history
rows (treat it the same as a failed capture, and alert), or (b) exclude zero-row gameweeks from
`captured_gws()`'s definition of "captured" so `check_freshness`/the default backfill can still see
and repair them:

```python
def capture(...):
    ...
    for gw in targets:
        deadline = _event_deadline(boot, gw)
        xp_map = resolve_xp_for_gw(gw, deadline, snaps) if deadline else {}
        frame = build_gw_frame(histories, boot, gw, xp_map, fixtures)
        if frame.empty and gw in finished:
            # a finished GW that produced zero rows is a real capture failure,
            # not a legitimate empty result -- never write a poisoned ledger.
            report(_JOB, "empty-capture",
                   f"GW{gw} reported finished but produced 0 rows -- ledger not written")
            continue
        write_csv_atomic(frame, ledger_dir / f"gw{gw}.csv")
```

## Warnings

### WR-01: `build_matches`'s systemic-reconstruction-failure guard is unconditionally disabled for the current season for nearly the whole season

**File:** `data/team_strength.py:105-117`
**Issue:** The new `in_progress = counts.index == config.CURRENT_SEASON` carve-out excludes the
current season from the `systemic` assertion whenever its fixture count is below
`MIN_FIXTURES_PER_SEASON` (370) — which is true for essentially the entire season (370/380
fixtures is reached only in the final few gameweeks). This is the right fix for the specific
false-positive it targets (a legitimately partial in-progress season), but as written it also
silences the assertion for a *genuine* reconstruction bug in the current season's own data (e.g. a
future regression in `gw_capture`/`build_table` that drops most of a season's fixtures via a
fixture-id join bug) for essentially the whole season — the exact class of bug this assertion was
added to catch. The only feedback in that case is an informational print
(`"... fixtures reconstructed so far (season in progress, not a reconstruction failure)"`), which
looks identical to the expected/healthy case.
**Fix:** Compare the current season's count against a season-progress-aware floor instead of
disabling the check outright, e.g. `expected_so_far ≈ current_gw * teams_count / 2` (rough matches-
per-gameweek), or track `finished_gws` count from `data.gw_capture` and require
`count >= 0.9 * finished_gws * 10` before allowing the "in progress" pass-through — anything that
still trips for a season losing an implausible fraction of its own finished fixtures.

### WR-02: Schema safety-net relies on a bare `assert`, which `python -O` silently strips

**File:** `data/gw_capture.py:94-97`
**Issue:** The module's own docstring (and the runbook, "What to check after a schema change
upstream") advertises this as an unconditional guarantee: *"`data.gw_capture` will refuse to even
load if a source key `config.MERGED_GW_COLUMNS` depends on stops being a member of the output
header."* That guarantee is implemented as a bare `assert`, which Python strips entirely when run
under `-O`/`-OO` (or when `PYTHONOPTIMIZE` is set) — a real risk in a project already shelling out
to `python -m <module>` from cron scripts, where an optimize flag could be set anywhere upstream in
the environment without this file's author knowing.
**Fix:**
```python
if not (set(config.MERGED_GW_COLUMNS) <= set(MERGED_GW_HEADER)):
    raise AssertionError(
        "MERGED_GW_HEADER is missing a config.MERGED_GW_COLUMNS source key: "
        f"{sorted(set(config.MERGED_GW_COLUMNS) - set(MERGED_GW_HEADER))}"
    )
```

### WR-03: `_fetch_bootstrap` and `_fetch_fixtures` are near-verbatim duplicates

**File:** `data/gw_capture.py:168-229`
**Issue:** The two functions differ only in the URL fragment (`bootstrap-static/` vs `fixtures/`)
and the human-readable name used in log/report messages — the retry loop, backoff/jitter math,
retryable-status check, and non-retryable-4xx short-circuit are byte-for-byte identical (~30 lines
duplicated). Any future fix to the retry logic (e.g. respecting a `Retry-After` header) has to be
applied twice and will drift.
**Fix:** Extract a single `_fetch_json(url: str, *, what: str, retries: int, backoff: float) ->
Any` helper and have both call sites pass their URL/name.

## Info

### IN-01: `build_gw_frame` silently drops a player's row when the id is absent from bootstrap `elements`, with no visibility

**File:** `data/gw_capture.py:405-408`
**Issue:** `el = elements.get(pid); if el is None: continue` silently skips the player's entire
history row with no counter, log line, or alert — unlike every other failure path in this module
(missing payload fields, per-player transport failures), which alert loudly per the module's own
design principle. If the FPL API ever fully drops a player id from `bootstrap-static` mid-season
(rare but not impossible — e.g. a data-protection removal), a subsequent `--force` re-sweep would
silently erase that player's previously-correct historical rows from `merged_gw.csv` with zero
trace in logs or `ops.notify`.
**Fix:** Count and report skipped ids, mirroring `sweep_histories`'s `failures` pattern:
```python
skipped_ids = {pid for pid in histories if pid not in elements}
if skipped_ids:
    print(f"[gw_capture] GW{gw}: {len(skipped_ids)} player id(s) in history "
          f"absent from bootstrap elements, dropped: {sorted(skipped_ids)}")
```

### IN-02: Missing f-string prefix produces a literal `{word}` in an assertion message

**File:** `tests/test_rl_isolation.py:89` (added by an earlier Phase 9 commit, not Phase 08)
**Issue:**
```python
raise AssertionError(
    f"{file_path.name}:{line_num}: pip install references "
    "'{word}', which must remain dev-only"
)
```
The second string literal lacks the `f` prefix, so if this assertion ever actually fires, the
failure message reads the literal text `'{word}'` instead of the offending lockfile name — reduced
diagnosability for a check whose entire purpose is naming the offending reference precisely.
**Fix:** `f"'{word}', which must remain dev-only"`.

---

_Reviewed: 2026-09-12T08:37:34Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
