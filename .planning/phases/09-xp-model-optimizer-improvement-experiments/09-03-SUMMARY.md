---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 03
subsystem: ml-experimentation
tags: [experiment-flags, captaincy, lambda-sweep, walk-forward, adoption-decision]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, backtest/walk_forward.py --experiments/--seasons/--tag CLI, models/captaincy.py::add_ceiling_ev, the tracked 6-season baseline in IMPROVEMENTS.md Phase F)"
provides:
  - "backtest/walk_forward.py --capt-lambda CLI override, threaded into models.captaincy.add_ceiling_ev(), echoed in [wf] and tagged JSON"
  - "config.CAPT_CEILING_LAMBDA pinned to the harness-measured winner (0.5) with the sweep tag/capture recorded inline"
  - "D-06/D-07 adoption verdict for captaincy ceiling EV: REJECTED (capture delta +1.5pt, below the +2pt bar), flag stays default-off"
  - "D-08 recorded non-decision for the Monte-Carlo captaincy variant: not triggered, gated on the same +1.5pt < +0.02 number"
affects: [09-10]

actuals:
  tokens: 1800
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Lambda sweep via a single CLI override thread (--capt-lambda -> config default override -> add_ceiling_ev(lam=)), never a hardcoded per-run edit to config.py during iteration"
    - "Branch-condition decisions read a prior task's own recorded number (Task 3 reads Task 2's capture delta) rather than re-deriving it"

key-files:
  created: []
  modified:
    - config.py
    - backtest/walk_forward.py
    - IMPROVEMENTS.md

key-decisions:
  - "Winning lambda (0.5) chosen by highest 6-season-mean capt_capture (0.578) among {0.0, 0.25, 0.5, 0.75, 1.0} swept at 1 replica/6 seasons -- no tie-break needed, 0.578 was strictly highest"
  - "capt_ceiling REJECTED per D-07's mechanical rule: adoption run measured +1.5pt absolute capture improvement (0.563->0.578), below the pre-declared >=+2pt bar; model+chips improved +16/season with no regression, but the criterion is capture, not points, and capture did not clear"
  - "capt_mc (Monte-Carlo variant) NOT built: Branch B taken per the plan's own gating rule -- the quantile variant's capture delta (+0.015) fell short of the +0.02 trigger for building models/simulate.py; recorded as a numbered non-decision in IMPROVEMENTS.md, not a silent skip"

requirements-completed: []

coverage:
  - id: D1
    description: "Lambda sweep on the honest harness with a lambda-0 control proving the ceiling column is wired through the same seam as captain-by-mean"
    verification:
      - kind: integration
        ref: "python -m backtest.walk_forward --experiments capt_ceiling --capt-lambda 0.0 --replicas 1 --tag capt_lam_0.0 (capt_capture 0.563, matches baseline 0.563 exactly)"
        status: pass
      - kind: integration
        ref: "5-point sweep {0.0,0.25,0.5,0.75,1.0} at 6 seasons/1 replica each, wf_capt_lam_*.json; winner 0.5 at capture 0.578"
        status: pass
    human_judgment: false
  - id: D2
    description: "config.CAPT_CEILING_LAMBDA pinned to the swept winner with an inline comment naming the sweep and measured capture"
    verification:
      - kind: unit
        ref: "python -c assertion: str(config.CAPT_CEILING_LAMBDA) in the 5 swept tags, and config.EXPERIMENTS['capt_ceiling'] is False"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full-replica 6-season adoption-deciding run and the mechanical D-07 verdict applied against the pre-declared D-06 criterion"
    verification:
      - kind: integration
        ref: "scripts/experiment_run.sh capt_ceiling_adopt --experiments capt_ceiling -> wf_capt_ceiling_adopt.json (6 seasons, 5 replicas, capt_ceiling: true, capt_capture 0.578 vs baseline 0.563 = +1.5pt, model+chips 2278 vs 2262 = +16)"
        status: pass
      - kind: unit
        ref: "python -c assertion: config.EXPERIMENTS['capt_ceiling'] == (measured delta >= 0.02) -- both False, consistent"
        status: pass
      - kind: other
        ref: "IMPROVEMENTS.md capt_ceiling row: no 'pending' text, quotes both deltas against the named baseline"
        status: pass
    human_judgment: false
  - id: D4
    description: "Monte-Carlo captaincy variant branch decision (build vs skip) taken from Task 2's own recorded number, and the non-construction recorded with a number rather than forgotten"
    verification:
      - kind: unit
        ref: "python -c assertion: os.path.exists('models/simulate.py') == (capture delta >= 0.02) -- both False, consistent (Branch B)"
        status: pass
      - kind: other
        ref: "IMPROVEMENTS.md capt_mc row: 'not run -- gated on capt_ceiling capture delta of +0.015, below the +0.02 trigger', verdict 'not triggered'"
        status: pass
      - kind: other
        ref: "python -m pytest -q (190 passed, 1 skipped) and ruff check . both green after all three commits"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-08
status: complete
---

# Phase 9 Plan 3: Captaincy Ceiling EV — Lambda Sweep and Adoption Verdict Summary

**Swept the captaincy ceiling-EV lambda to a measured winner (0.5, capture 0.578), ran the full-replica 6-season adoption-deciding measurement, and applied D-07's mechanical rule: REJECTED — the +1.5 percentage-point capture gain over captain-by-mean falls short of the pre-declared +2 bar, so the flag stays default-off and the gated Monte-Carlo variant was never built.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-08T12:15:00Z (approx.)
- **Completed:** 2026-09-08T12:57:02Z
- **Tasks:** 3
- **Files modified:** 3 (config.py, backtest/walk_forward.py, IMPROVEMENTS.md — no files created)

## Accomplishments

- **`--capt-lambda` CLI override** added to `backtest/walk_forward.py`, threaded into `models.captaincy.add_ceiling_ev(lam=...)`, echoed in both the `[wf]` summary line and the tagged JSON summary (`capt_lambda` key). Unflagged/default behaviour unchanged.
- **Lambda-0 control confirmed the wiring**: `capt_lam_0.0`'s `capt_capture` (0.563) matched the plan 09-01 baseline (0.563) to within floating-point noise, proving the ceiling column rides the exact same captaincy seam as plain captain-by-mean before any real sweep number could be trusted.
- **5-point sweep** at 6 seasons / 1 replica each — {0.0: 0.563 (control), 0.25: 0.576, **0.5: 0.578 (winner)**, 0.75: 0.572, 1.0: 0.547} — picked lambda **0.5** by highest 6-season-mean `capt_capture`, no tie-break needed. Pinned to `config.CAPT_CEILING_LAMBDA` with an inline comment naming the sweep and the winning number.
- **Adoption-deciding run** (`scripts/experiment_run.sh capt_ceiling_adopt --experiments capt_ceiling`, 6 seasons at the harness's default 5 replicas): `capt_capture` 0.578 vs the plan 09-01 baseline's 0.563 — a **+1.5 percentage-point** absolute improvement (D-06's own criterion, restated in this plan's `<criterion_reading>`, requires **≥ +2 pts absolute**). `model+chips` improved to 2278 from the 2262 baseline (+16/season, no regression).
- **D-07 auto-adopt verdict: REJECTED.** `config.EXPERIMENTS['capt_ceiling']` stays `False` since the measured delta (+1.5pt) does not clear the +2pt bar. Per D-08 the code stays merged — nothing deleted. No `tests/test_experiments.py` change was needed since the default flag set is unchanged.
- **Monte-Carlo captaincy variant (`capt_mc`) gated OFF, Branch B taken.** The plan's pre-declared trigger for building `models/simulate.py` was a `capt_ceiling` capture delta ≥ +0.02; the measured delta (+0.015) fell short. `models/simulate.py` was left uncreated (no placeholder file), `config.EXPERIMENTS['capt_mc']` stays `False`. This is a recorded, numbered non-decision in IMPROVEMENTS.md, not a silent skip — the file both plans' verify commands checked for its absence confirmed no file exists.
- **IMPROVEMENTS.md Phase F** updated: `capt_ceiling` and `capt_mc` results rows both carry non-`pending` cells, plus two new prose sub-sections (`capt_ceiling: lambda sweep and adoption verdict`, `capt_mc: Monte-Carlo variant not triggered`) quoting the sweep table and the adoption run's numbers in the established Phase A–E style.

## Criterion Reading (restated per this plan's own instruction)

D-06's "captaincy capture ≥ +2 pts absolute over captain-by-mean" is a **percentage-point** reading of the harness's `capt_capture` fraction field (e.g. baseline 0.563 = 56.3%). "+2 pts absolute" therefore means a 6-season-mean `capt_capture` at least 0.02 above the plan 09-01 baseline. Every delta in this SUMMARY uses that reading. Measured delta: **+0.015** (1.5 percentage points) — below the 0.02 (2 percentage-point) bar.

## Task Commits

Each task was committed atomically:

1. **Task 1: Sweep lambda on the honest harness and pin the measured winner** - `0bca5d6` (feat)
2. **Task 2: Adoption-deciding run and the D-07 auto-adopt verdict** - `da742ec` (docs)
3. **Task 3: Monte-Carlo captaincy variant — build it only if the quantile variant earned it** - `ba7e6c5` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `backtest/walk_forward.py` - `--capt-lambda` CLI option, threaded into `add_ceiling_ev()`, echoed in `[wf]` line and tagged JSON summary
- `config.py` - `CAPT_CEILING_LAMBDA` pinned to 0.5 with inline sweep-provenance comment; `EXPERIMENTS['capt_ceiling']`/`['capt_mc']` unchanged (both stay `False`)
- `IMPROVEMENTS.md` - Phase F `capt_ceiling`/`capt_mc` results rows filled (non-pending), two new prose sub-sections with the sweep table and adoption-run numbers

## Decisions Made

- Winning lambda (0.5) chosen by highest 6-season-mean `capt_capture` (0.578) among the five swept values; no tie-break needed since 0.578 was strictly the highest.
- `capt_ceiling` rejected per D-07's mechanical rule applied to the measured capture delta (+1.5pt < +2pt bar) — `model+chips` improving (+16/season) does not override the capture criterion, since D-06 explicitly names capture as the adoption metric for this experiment.
- `capt_mc` (Monte-Carlo variant) not built: the plan's own sequencing rule (research doc option 1) gates the Monte-Carlo layer on the quantile variant proving the ceiling direction pays; +0.015 < +0.02 means it has not yet earned the extra machinery. Recorded as a numbered non-decision, not a silent omission.

## Deviations from Plan

None - plan executed exactly as written. The single-season timeout hit during the sweep (lambda 0.75's run was interrupted mid-batch by a 10-minute shell timeout while chained with 0.25/0.5 in one command) was resolved by re-running the remaining lambda values individually with a longer per-command timeout — no code or scope change, purely a shell-batching adjustment.

## Issues Encountered

- A chained shell loop over `{0.25, 0.5, 0.75, 1.0}` hit the 10-minute Bash tool timeout partway through 0.75's run (harness runs are slow: ~2-3 min per 6-season/1-replica run). Resolved by running 0.75 and 1.0 as separate, individually-timed commands. No data was lost or corrupted — the interrupted 0.75 run had not yet written its JSON, so the retry produced a clean result.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Experiment 2 (captaincy / Triple-Captain ceiling EV) is fully closed: both its variants (quantile-based `capt_ceiling` and Monte-Carlo `capt_mc`) have a measured number and a recorded verdict in IMPROVEMENTS.md, and neither flag flipped the shipped default.
- `predict/live.py` and `predict/export.py` remain untouched (verified via `git log` on those paths across this plan's three commits) — the weekly product surface is unaffected, matching this plan's own success criteria.
- Plan 09-10 (results table finalization) has both `capt_ceiling` and `capt_mc` rows ready with no `pending` cells remaining.
- No blockers.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-08*

## Self-Check: PASSED

All key files (config.py, backtest/walk_forward.py, IMPROVEMENTS.md) exist on disk and carry the expected changes; all three task commits (0bca5d6, da742ec, ba7e6c5) found in `git log`; full pytest suite (190 passed, 1 skipped) and `ruff check .` both green after the final commit; `models/simulate.py` confirmed absent (Branch B); `config.EXPERIMENTS['capt_ceiling']` and `['capt_mc']` both confirmed `False` matching their measured non-adoption verdicts.
