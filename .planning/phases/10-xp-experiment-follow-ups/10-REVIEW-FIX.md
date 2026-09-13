---
phase: 10-xp-experiment-follow-ups
fixed_at: 2026-09-12T09:41:18Z
review_path: .planning/phases/10-xp-experiment-follow-ups/10-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-09-12T09:41:18Z
**Source review:** .planning/phases/10-xp-experiment-follow-ups/10-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (fix_scope = critical_warning: CR-01, WR-01..04)
- Fixed: 5
- Skipped: 0

**Verification environment:** All fixes were applied and verified inside an
isolated git worktree (`workflow.use_worktrees` defaulted to `true` for this
project; no explicit opt-out was configured). `data/raw/`, `data/processed/`,
`models/artifacts/`, and `data/snapshots/` (gitignored regenerable pipeline
data, needed by several tests) were symlinked in from the main checkout for
the duration of verification only -- no commit touches or depends on those
symlinks, and they are discarded with the worktree on cleanup. Tests were run
with the conda `python314` interpreter
(`/home/sraja/miniconda3/envs/python314/bin/python`) per project convention.
Since the worktree is torn down after this report is written, these results
are reproducible by re-running the same pytest invocations against the main
checkout's own `data/raw/`, `data/processed/`, `models/artifacts/`, and
`data/snapshots/`.

## Fixed Issues

### CR-01: `tm_mod.attach()` read `gw_deadlines()` from a stale on-disk `player_gw.parquet` mid-build

**Files modified:** `data/availability.py`, `data/transfermarkt.py`
**Commit:** `2f27a7a`
**Applied fix:** Gave `data/availability.py::gw_deadlines()` an optional
`raw: pd.DataFrame | None = None` parameter -- when supplied, it is used
instead of re-reading `player_gw.parquet` from disk (still validated down to
`["season", "gw", "kickoff_time"]`). `data/transfermarkt.py::attach()` now
calls `gw_deadlines(raw=full)`, threading through the in-memory frame
`build_table.py::build()` is still assembling, exactly as CR-01's fix
suggested (mirroring `models/bracket/sequence.py::build_sequences`'s own
`raw=`/`feat=` override pattern already used elsewhere in this phase). No
change was needed in `data/build_table.py` itself -- it already passed `full`
into `tm_mod.attach(full)`; the staleness was entirely inside `attach()`'s
own re-read.

Verified with a standalone repro (not committed) that constructed an
in-memory `full` carrying one gameweek beyond the on-disk
`player_gw.parquet`'s max gameweek: `gw_deadlines()` (disk-reading) confirmed
missing the new gameweek, while `gw_deadlines(raw=full)` correctly included
it. `tests/test_availability.py` (22 tests) and `tests/test_transfermarkt.py`
pass unchanged.

### WR-04: `attach()` pre-filled the "not injured" baseline before checking deadline resolvability

**Files modified:** `data/transfermarkt.py`
**Commit:** `9e45db2`
**Applied fix:** Gated `covered_mask` (which drives the `0.0` "not injured"
baseline for `tm_injured`/`tm_days_out_so_far`/`tm_spells_prior_365d`/
`tm_days_out_prior_365d`) on `~pd.isna(deadline_ts)` in addition to id
coverage, per CR-01's own "Additionally" fix note and WR-04's independent
finding of the same code shape. A covered player whose row has no resolvable
`deadline_ts` (CR-01's now-fixed staleness window, or a gameweek with no
parseable `kickoff_time` at all) is now left `NaN` ("genuinely unknown"),
never a confident `0.0`. Also renamed the coverage print line from
"id-resolved coverage" to "id+deadline-resolved coverage" and updated the
`attach()` docstring, since the meaning of the underlying mask changed.
Committed separately from CR-01 to keep each finding's diff independently
reviewable, even though both touch the same function. `tests/test_transfermarkt.py`
and `tests/test_experiments.py` (61 tests total) pass unchanged.

### WR-01: `resolve_as_of`'s `kickoff_max` postponement guard is a mathematical no-op, but the docstrings/comments/test claimed it worked

**Files modified:** `data/availability.py`, `tests/test_availability.py`
**Commit:** `96c3a0f`
**Applied fix:** Took fix option (a) from the review (prove and document
why `deadline_ts` alone is what's actually enforced, rather than silently
removing the redundant comparison and risking unrelated breakage across
`tests/test_availability.py`/`tests/test_leakage.py`, both of which construct
and assert against `kickoff_max`). Rewrote: the module-level docstring's
leakage-rule paragraph, `gw_deadlines()`'s postponement caveat,
`resolve_as_of()`'s docstring and inline comment, and
`test_every_source_row_predates_its_gw_deadline`'s docstring -- all now state
plainly that `deadline_ts < kickoff_max` always holds given how both are
derived (same `kickoff_time` column, same groupby), so the `kickoff_max`
comparison is currently non-binding defensive redundancy, not an independent
postponement mitigation, and that a genuine fix for the postponement scenario
would need the pre-postponement scheduled kickoff time -- data not present in
`player_gw.parquet`'s already-updated `kickoff_time` column. Also corrected an
adjacent pre-existing docstring typo (`kickoff_max` was mislabeled as
`min(kickoff_time)`; it is `max(kickoff_time)`) found while editing the same
sentence. No code behavior changed -- this was a documentation-accuracy fix
per the review's own recommended option. `tests/test_availability.py` (29
tests) and `tests/test_leakage.py` pass unchanged.

### WR-02: `config.resolve_experiments()` silently dropped named flags when combined with `"none"`/`"all"`

**Files modified:** `config.py`
**Commit:** `3020260`
**Applied fix:** Applied the review's suggested fix essentially verbatim:
`"none"` or `"all"` combined with any other token now raises `ValueError`
naming the offending token list, instead of silently collapsing to
all-off/all-on. `"none"`/`"all"` alone still resolve as before. Manually
verified `resolve_experiments("none,capt_ceiling")` and
`resolve_experiments("all,transfermarkt_injury")` both now raise, and that
`resolve_experiments("none")`/`resolve_experiments("all")` still produce the
expected all-off/all-on dicts. `tests/test_experiments.py` (55 tests) pass
unchanged -- no existing test exercised the none/all + flag combination this
fix now rejects.

### WR-03: `predict/scoreboard.py::update()`'s bootstrap-static fetch had no `raise_for_status()`

**Files modified:** `predict/scoreboard.py`
**Commit:** `11e7e6b`
**Applied fix:** Applied the review's suggested fix exactly: split the
one-line `requests.get(...).json()` into `r = requests.get(...)`;
`r.raise_for_status()`; `boot = r.json()`, matching the existing
`fetch_actuals()` pattern in the same module. `tests/test_scoreboard.py` (23
tests) pass unchanged.

## Skipped Issues

None -- all in-scope findings were fixed.

---

_Fixed: 2026-09-12T09:41:18Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
