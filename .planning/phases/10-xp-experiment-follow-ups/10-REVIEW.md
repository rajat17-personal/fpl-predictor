---
phase: 10-xp-experiment-follow-ups
reviewed: 2026-09-11T00:00:00Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - backtest/walk_forward.py
  - config.py
  - data/availability.py
  - data/build_table.py
  - data/fpl_core_insights.py
  - data/fpl_standings.py
  - data/fplreview.py
  - data/id_crosswalk.py
  - data/snapshot.py
  - data/transfermarkt.py
  - features/engineer.py
  - models/train.py
  - models/bracket/__init__.py
  - models/bracket/classical.py
  - models/bracket/deep.py
  - models/bracket/gate.py
  - models/bracket/gbdt.py
  - models/bracket/recurrent.py
  - models/bracket/registry.py
  - models/bracket/sequence.py
  - models/bracket/transformer.py
  - predict/scoreboard.py
  - scripts/daily.sh
  - scripts/snapshot_catchup.sh
  - tests/test_availability.py
  - tests/test_bracket.py
  - tests/test_cron.py
  - tests/test_experiments.py
  - tests/test_leakage.py
  - tests/test_product.py
  - tests/test_scoreboard.py
  - tests/test_transfermarkt.py
  - requirements.in / requirements.txt / requirements-dev.txt / requirements-experiments.in / requirements-experiments.txt
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-09-11
**Depth:** standard
**Files Reviewed:** 30 source files (+ 5 requirements files spot-checked for alarming pins)
**Status:** issues_found

## Summary

Phase 10 is a large, unusually well-documented drop: the new as-of-deadline
availability family (`data/availability.py`), the Transfermarkt injury
backfill + date-range join (`data/transfermarkt.py`), the model-class
bracket (`models/bracket/*`), several diagnostic scoreboard scrapers, and the
experiment-gating seams in `backtest/walk_forward.py`/`config.py`. The known
already-fixed items were re-verified and confirmed fixed:

- `data/transfermarkt.py:564-565` — the DataFrame-truthiness bug is fixed;
  `build()` now returns via `loaded if loaded is not None else ...`, not a
  bare-truthiness check on a DataFrame.
- No test-pollution (writes to the real `data/snapshots/`,
  `config.EXPERIMENTS_DIR`, or live `bracket_gate_*.json` artifacts) was
  found in any Phase 10 test file; every test that touches on-disk state
  uses `tmp_path`/`monkeypatch` correctly, including the specific artifact
  guarded against in the quick-260911-7fy fix.

One genuine correctness bug was found in the new Transfermarkt
build-pipeline wiring (below), plus four maintainability/robustness
Warnings and two Info items. The bracket registry, sequence builder, and
padding/masking logic in the deep-learning candidates were traced carefully
(the sequence builder's `kickoff_time`-based history cutoff, the GRU/
transformer padding-mask invariance, the D-15 gate's train/val/test season
separation) and found leakage-safe and correctly implemented.

## Critical Issues

### CR-01: `tm_mod.attach()` is wired inline into `build_table.py`, but reads `gw_deadlines()` from a stale on-disk `player_gw.parquet` — the newest gameweek's injury features are silently wrong every incremental pipeline run

**File:** `data/build_table.py:204-207`, `data/transfermarkt.py:619-654`, `data/availability.py:130-148`
**Issue:**

`data/build_table.py::build()` calls `tm_mod.attach(full)` **while still
constructing** the in-memory `full` frame — the very frame that will become
the *next* `player_gw.parquet`:

```python
# data/build_table.py
full = pd.concat(frames, ignore_index=True)   # in-memory, not yet on disk
...
try:
    full = tm_mod.attach(full)                # called here, mid-build
except Exception as exc:
    print(f"  [transfermarkt] skipped ({exc})")
...
return full

def main() -> int:
    df = build()
    out = config.PROCESSED_DIR / "player_gw.parquet"
    df.to_parquet(out, index=False)           # written only AFTER build() returns
```

`tm_mod.attach()` internally calls `data.availability.gw_deadlines()`
(`data/transfermarkt.py:651-654`), which does:

```python
# data/availability.py::gw_deadlines()
raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                      columns=["season", "gw", "kickoff_time"])
```

This reads `player_gw.parquet` **from disk** — the file written by the
*previous* run of `data.build_table`, not the `full` DataFrame currently
being assembled. Every ordinary pipeline re-run (ingest new gameweek data →
`python -m data.build_table`) is therefore a case where the on-disk file is
strictly behind the in-memory `full`: the newest `(season, gw)` the current
run just ingested has **no entry** in `gw_deadlines()`'s output, because
that gameweek didn't exist in `player_gw.parquet` the last time it was
written.

The consequence is not merely a missing feature — `data/transfermarkt.py::attach()`
sets the "not injured" baseline **unconditionally** for every `covered`
player, before checking whether a deadline resolved for that row:

```python
covered_mask = out["player_code"].astype("Int64").isin(covered).to_numpy()
out.loc[covered_mask, "tm_injured"] = 0.0          # set regardless of deadline_ts
out.loc[covered_mask, "tm_days_out_so_far"] = 0.0
...
# only rows with a resolvable deadline_ts are later overwritten by the
# real spell-overlap computation (the `valid = ~pd.isna(as_of)` filter)
```

So for the current gameweek (the one that matters most for a live weekly
recommendation — the project's stated Core Value), a genuinely injured
covered player is reported as `tm_injured=0.0` ("not injured") instead of
either the correct computed status or an honest NaN. This silently
contradicts the module's own carefully-documented resolved-vs-unresolved
invariant ("a covered player with zero spells is genuinely NOT injured —
0.0, never NaN" / "a player who never resolved is genuinely UNKNOWN — NaN"):
here, a *covered, genuinely injured* player also gets 0.0, because the
missing-deadline case was never distinguished from the zero-spells case.

This is invisible to `tests/test_experiments.py::test_transfermarkt_injury_gate_drops_or_keeps_all_four_on_real_attach`
because that test calls `tm.attach(d)` against `d = load_features()` (an
already-fully-built, internally-consistent `features.parquet`/
`player_gw.parquet` pair from a *prior* completed build), which never
exercises the inline mid-build staleness window.

**Fix:** `tm_mod.attach()` (and transitively `gw_deadlines()`) must operate
on the in-memory frame being built, not re-read `player_gw.parquet` from
disk. The simplest fix is to change `gw_deadlines()` to accept an optional
`raw: pd.DataFrame | None = None` parameter (mirroring
`models/bracket/sequence.py::build_sequences`'s own `raw=`/`feat=` override
pattern already used elsewhere in this phase) and have
`data/build_table.py::build()` pass its own `full` into `tm_mod.attach(full)`
so it can forward it through to `gw_deadlines(raw=full)`:

```python
# data/availability.py
def gw_deadlines(raw: pd.DataFrame | None = None) -> pd.DataFrame:
    if raw is None:
        raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                              columns=["season", "gw", "kickoff_time"])
    else:
        raw = raw[["season", "gw", "kickoff_time"]]
    ...

# data/transfermarkt.py::attach()
deadlines = gw_deadlines(raw=full)[["season", "gw", "deadline_ts"]]...

# data/build_table.py
full = tm_mod.attach(full)   # attach() already receives `full`; just thread it through
```

Additionally, `attach()` should leave `tm_injured`/etc. `NaN` (not `0.0`)
for a covered player whose row has no resolvable `deadline_ts`, rather than
pre-filling the baseline before checking deadline availability — this keeps
the "unknown" vs "not injured" distinction correct even after the staleness
fix, for the genuine edge case of a gameweek with no parseable
`kickoff_time` anywhere.

## Warnings

### WR-01: `resolve_as_of`'s second ("postponement") leakage guard is mathematically a no-op — the extensive docstring and its dedicated test give false confidence

**File:** `data/availability.py:130-148`, `data/availability.py:266-318`
**Issue:** `gw_deadlines()` computes, from the *same* `kickoff_time` column
and the *same* groupby:

```python
out["deadline_ts"] = out["kickoff_min"] - _DEADLINE_LEAD   # kickoff_min - 90min
# kickoff_max = the same group's max(kickoff_time)
```

Since `kickoff_min <= kickoff_max` always (same source data), `deadline_ts
= kickoff_min - 90min` is *always* strictly less than `kickoff_max`. In
`resolve_as_of`:

```python
cutoff = min(row["deadline_ts"], row["kickoff_max"])
```

`cutoff` therefore always equals `deadline_ts` — the `kickoff_max` half of
the `min()` can never bind. Verified directly:

```python
>>> deadline < kmax   # for any kmin <= kmax, deadline = kmin - 90min
True   # always
```

The module docstring (lines 41-50) and `gw_deadlines()`'s own docstring
describe this second condition as the fix for a real leakage risk — a
postponed first fixture pushing `deadline_ts` later than it "should" be —
but as coded, it can never additionally exclude a row `deadline_ts` alone
wouldn't already exclude. `tests/test_availability.py` and the assertion in
`resolve_as_of`'s own docstring
(`test_every_source_row_predates_its_gw_deadline`) check *both* conditions,
but since one is always implied by the other, the test cannot actually
distinguish "the guard works" from "the guard is dead code" — it passes
either way. If the postponement scenario the docstring worries about is a
genuine concern (a fully-postponed gameweek's `kickoff_min` moving much
later than the originally-scheduled deadline would have been), there is
currently no functioning mitigation for it despite the code and tests
appearing to provide one.

**Fix:** Either (a) prove and document why `deadline_ts` alone is
sufficient (in which case delete the dead `kickoff_max` comparison and the
now-misleading docstring claims), or (b) if the postponement scenario is a
real risk, the guard needs a genuinely independent second bound — e.g. the
*original* scheduled kickoff time before any postponement, which isn't
derivable from `player_gw.parquet`'s already-updated `kickoff_time` column
at all. Either way, the current code and its accompanying test should not
claim protection they don't provide.

### WR-02: `config.resolve_experiments()` silently drops named flags when combined with `"none"`/`"all"` — a silent-failure path in experiment-flag resolution

**File:** `config.py:306-332`
**Issue:**

```python
tokens = [t.strip() for t in spec.split(",")] if spec else []
tokens = [t for t in tokens if t]
if not tokens:
    return result
if "none" in tokens:
    return {k: False for k in result}     # <- any OTHER token in tokens is silently ignored
if "all" in tokens:
    return {k: True for k in result}      # <- same here
for t in tokens:
    if t not in result:
        raise ValueError(...)
    result[t] = True
```

`FPL_EXPERIMENTS=none,capt_ceiling` (or `--experiments none,capt_ceiling`)
returns every flag off, silently dropping `capt_ceiling` — no warning, no
error, even though `capt_ceiling` is validated as a real flag name by the
same function when given alone. A typo like `all,transfermarkt_injury`
(intending "all flags on, extra emphasis on transfermarkt_injury") would
similarly silently collapse to "all on" without complaint (harmless there,
but the asymmetric silent-drop behavior is the same bug). This is exactly
the kind of silent-failure path the review brief calls out — a researcher
running a bracket/experiment sweep could believe a named flag is active
when it was silently dropped.

**Fix:** Reject `"none"`/`"all"` combined with any other token explicitly:

```python
if "none" in tokens or "all" in tokens:
    if len(tokens) > 1:
        raise ValueError(
            f"'none'/'all' cannot be combined with other flags: {tokens}")
    return {k: (t == "all") for k in result} if tokens[0] in ("none", "all") else result
```

(or simply document and assert that `"none"`/`"all"` must be the sole
token).

### WR-03: `predict/scoreboard.py::update()` — bootstrap-static fetch has no `raise_for_status()`, inconsistent with the rest of the file

**File:** `predict/scoreboard.py:129-130`
**Issue:**

```python
boot = requests.get(f"{config.FPL_API}/bootstrap-static/",
                    headers=_HEADERS, timeout=30).json()
```

Unlike `fetch_actuals()` in the same module (which correctly calls
`r.raise_for_status()` before `.json()`), this call has no status check. An
HTTP error response (5xx during an FPL outage, a 403 from a CDN/WAF, etc.)
either raises an opaque `JSONDecodeError` several lines removed from the
real cause, or — if the error page happens to be valid JSON with no
`"events"` key — raises a confusing `KeyError` at `boot["events"]` instead
of a clear, actionable HTTP error. Given this runs from `scripts/daily.sh`'s
post-GW cron step, a clearer failure mode matters for triage.

**Fix:**

```python
r = requests.get(f"{config.FPL_API}/bootstrap-static/", headers=_HEADERS, timeout=30)
r.raise_for_status()
boot = r.json()
```

### WR-04: `data/transfermarkt.py::attach()` pre-fills the "not injured" baseline before checking deadline resolvability

**File:** `data/transfermarkt.py:656-671`
**Issue:** (Related to, but distinct from, CR-01 — this is the specific
code shape that turns CR-01's staleness window into wrong data rather than
missing data.)

```python
covered_mask = out["player_code"].astype("Int64").isin(covered).to_numpy()
out.loc[covered_mask, "tm_injured"] = 0.0
out.loc[covered_mask, "tm_days_out_so_far"] = 0.0
out.loc[covered_mask, "tm_spells_prior_365d"] = 0.0
out.loc[covered_mask, "tm_days_out_prior_365d"] = 0.0
```

This baseline is set purely from `covered_mask` (identity resolution),
never checking whether that row's `deadline_ts` was actually resolvable
(the subsequent per-player-code loop only overwrites rows where
`valid = ~pd.isna(as_of)`). A covered player whose row has no matching
`gw_deadlines()` entry — whether from CR-01's staleness window, or the
narrower case of a gameweek with no parseable `kickoff_time` at all —
receives a confident `0.0` ("not injured") rather than the module's own
documented "genuinely unknown → NaN" contract, which is reserved (per the
module docstring) only for players who never resolved a Transfermarkt id
at all.

**Fix:** Only set the `0.0` baseline for covered rows whose `deadline_ts`
is non-null; leave the rest `NaN`, e.g. compute `deadline_ts` first and gate
`covered_mask` on `covered_mask & ~pd.isna(deadline_ts)` before the
baseline assignment.

## Info

### IN-01: Six `bracket_*` experiment flags in `config.EXPERIMENTS` are entirely unconsumed — inert configuration state

**File:** `config.py:257-262`, `backtest/walk_forward.py` (whole file)
**Issue:** `bracket_ridge`, `bracket_xgb`, `bracket_catboost`, `bracket_mlp`,
`bracket_rnn`, and `bracket_transformer` are declared in `config.EXPERIMENTS`
but grepping the whole tree confirms no non-test code ever reads any of
them — `backtest/walk_forward.py::apply_experiment_feature_gating` and
`main()` never branch on a `bracket_*` key to choose `stage2=` when calling
`train_predict`/`_preds_for`. This is presumably deliberate given the D-15
gate's all-HOLD verdict (`tests/test_bracket.py::test_gate_advance_rule_is_mechanical_over_the_seven_recorded_candidates`),
but as written a future user flipping `FPL_EXPERIMENTS=bracket_xgb` would
see **zero effect** on any real run, with nothing in the code signalling
that. A one-line comment next to the six flags (or in `resolve_experiments`)
noting they are currently unwired/inert would prevent confusion.

### IN-02: `data/fpl_core_insights.py::fetch()` is not resumable on a mid-loop network failure

**File:** `data/fpl_core_insights.py:155-192`
**Issue:** Unlike `data/transfermarkt.py::build()` (explicitly designed
resumable/killable per plan 10-07's own requirement, with a `_processed.csv`
checkpoint log), `fetch()`'s loop over ~38 gameweeks has no per-request
try/except: `resp.raise_for_status()` on any single GW's request (line 179)
propagates uncaught and aborts the whole run. Already-written GW files on
disk are preserved, but a re-run restarts iteration from GW1 rather than
skipping already-fetched gameweeks (it always re-downloads and
overwrites). Low impact — this is a deliberate one-time, human-run,
non-cron task over a small, mostly-static vendor dataset — but worth a
`try/except requests.RequestException: continue` per-GW if this is ever
re-run against a live, still-updating season.

---

_Reviewed: 2026-09-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
