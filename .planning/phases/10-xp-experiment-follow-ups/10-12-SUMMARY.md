---
phase: 10-xp-experiment-follow-ups
plan: 12
subsystem: xp-model-experiments
tags: [d-02-trigger, news-sentiment, decision-checkpoint, ledger, declined-on-cost]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-08's D-02 trigger measurement (post-Tier-1 pooled played-only spearman_xp_med = 0.3874, read from data/processed/experiments/benchmark_tier1.json) and its IMPROVEMENTS.md D-02 section, which this plan reads and routes on"
provides:
  - "IMPROVEMENTS.md's D-02 declined-on-cost ledger entry: the trigger fired (0.3874 < 0.500) but the human declined to build, with the projected 9.0-14.1 day fetch cost, the governing danielfrees/mlpremier negative prior, and the availability-coverage structural caveat all quoted verbatim and distinguished from a not-triggered outcome"
  - "Phase 10 results table's news_sentiment row filled (DECLINED ON COST, not pending, not REJECTED)"
affects: [10-14, 10-16]

# Actuals (#2632)
actuals:
  tokens: 1800
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Declined-on-cost is recorded as its own ledger shape, distinct from both 'not triggered' (mechanical, no human judgment) and 'REJECTED' (built and measured, failed the bar) -- a pre-declared trigger firing does not obligate a build if a human overrides on cost, but the override and its reasoning must be as permanently on record as an adoption verdict would be"

key-files:
  created: []
  modified:
    - IMPROVEMENTS.md

key-decisions:
  - "Human answered the Task 1 blocking-human checkpoint with the verbatim decision 'DECLINE' -- the D-02 trigger had fired (0.3874 < 0.500), but the projected GDELT-throttled fetch cost (9.0 days at the 6-season measurement scope, 14.1 days at the full config.SEASONS scope matching data/transfermarkt.py's own 'full authorised scope' precedent) was judged not worth spending against the danielfrees/mlpremier (arXiv 2405.02412) negative prior for this exact feature and the structural caveat that the fired trigger's own movement (+0.0042) is entirely attributable to transfermarkt_injury, not availability -- meaning the number doesn't specifically evidence that a news-sentiment feature would help"
  - "Tasks 2 and 3 skipped entirely per Task 2's own <precondition> ('Task 1's checkpoint recorded BUILD. On NOT TRIGGERED or DECLINE, skip this task and Task 3 entirely -- the ledger entry Task 1 wrote is this plan's whole output'). No data/news.py, no config.NEWS_COLS, no measurement run."

patterns-established:
  - "A pre-declared conditional trigger firing is necessary but not sufficient to obligate a build -- a human cost override is a legitimate, distinct outcome that must be ledgered with the same rigor as a measured verdict, quoting the exact projected cost that motivated the decision so a future revisit can re-evaluate against updated numbers rather than re-deriving them"

requirements-completed: [TODO-NEWS]

coverage:
  - id: D1
    description: "D-02 trigger read from the measured artifact (0.3874 < 0.500 -> fired) and the mechanical BUILD outcome stated, before any override is applied"
    requirement: TODO-NEWS
    verification:
      - kind: other
        ref: "data/processed/experiments/benchmark_tier1.json pooled.spearman_xp_med = 0.3874, read live via python -c, quoted in the checkpoint and in IMPROVEMENTS.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "Projected build wall clock computed live from features.parquet (not estimated from memory): 244,425 distinct (season,gw,player_code) windows at full config.SEASONS scope (~339.5h / 14.1 days) and 156,075 at the 6-season measurement scope (~216.8h / 9.0 days), both at the locked _GDELT_MIN_INTERVAL_S=5.0"
    requirement: TODO-NEWS
    verification:
      - kind: other
        ref: "python -c pandas query against data/processed/features.parquet, counted distinct (season,gw,player_code) triples for config.SEASONS and for the 6-season protocol subset; both figures quoted verbatim in the checkpoint and in IMPROVEMENTS.md's declined-on-cost entry"
        status: pass
    human_judgment: false
  - id: D3
    description: "The verbatim DECLINE answer is recorded in IMPROVEMENTS.md's D-02 section as 'declined on cost', explicitly distinguished from a 'not triggered' outcome, and the Phase 10 results table's news_sentiment row reflects DECLINED ON COST rather than pending or REJECTED"
    requirement: TODO-NEWS
    verification:
      - kind: other
        ref: "IMPROVEMENTS.md new '### D-02 news-sentiment: declined on cost, NOT not-triggered (plan 10-12)' subsection, commit e243e66; results-table news_sentiment row updated in the same commit"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-09-11
status: complete
---

# Phase 10 Plan 12: D-02 News-Sentiment Trigger -- Declined on Cost Summary

**The pre-declared D-02 trigger fired (measured post-Tier-1 pooled played-only `spearman_xp_med` = 0.3874 < the locked 0.500 threshold, per plan 10-08's `benchmark_tier1.json`), but the human declined to build the GDELT + Guardian news-sentiment experiment on cost grounds after a live-computed projected fetch of 9.0-14.1 days at the locked `_GDELT_MIN_INTERVAL_S = 5.0` throttle, weighed against `danielfrees/mlpremier`'s (arXiv 2405.02412) documented negative result for this exact feature. Recorded in `IMPROVEMENTS.md` as "declined on cost" -- explicitly distinct from "not triggered" -- so a future revisit knows the experiment was authorised by measurement but never actually run.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-09-11T12:45:26Z
- **Tasks:** 1 of 3 (Tasks 2 and 3 skipped per their own `<precondition>` on a non-BUILD route)
- **Files modified:** 1 (`IMPROVEMENTS.md`)

## Accomplishments

- **Task 1 (decision checkpoint)** read the D-02 trigger from the measured artifact rather than from memory: `data/processed/experiments/benchmark_tier1.json`'s `pooled.spearman_xp_med` = **0.3874**, below the locked **0.500** threshold declared in plan 10-01 Task 3 before any Tier-1 run. The trigger mechanically fired (BUILD), but the checkpoint also surfaced the governing negative prior (`danielfrees/mlpremier`, arXiv 2405.02412 -- the exact repo the source todo cites, which found no strong predictive signal for Guardian news-sentiment, underperforming both its own CNN and its Ridge/LightGBM baselines) and the structural caveat plan 10-08 recorded (the benchmark's two scoreable seasons carry zero `availability_flags` coverage, so the entire +0.0042 movement from the fresh base is attributable to `transfermarkt_injury` alone -- the fired number doesn't specifically evidence a news-sentiment payoff).
- **Projected build cost computed live**, not assumed, from `features.parquet`'s real distinct `(season, gw, player_code)` windows:
  - Full `config.SEASONS` scope (2016-17..2026-27, `data/transfermarkt.py`'s own "full authorised scope" precedent, since this plan's fetcher is explicitly modeled on that file's resumable-backfill shape): **244,425 windows** -> **1,222,125 s ~ 339.5 hours ~ 14.1 days** of continuous GDELT fetching at `_GDELT_MIN_INTERVAL_S = 5.0`, before any Guardian pass or retry overhead.
  - Narrower 6-season measurement scope (2020-21..2025-26, the only seasons the eventual `wf_news_base6`/`wf_news_on6` walk-forward runs would consume): **156,075 windows** -> **780,375 s ~ 216.8 hours ~ 9.0 days**.
- **Human decision:** verbatim **"DECLINE"** -- the trigger fired, but the projected 9-14 day cost was judged not worth spending against the mlpremier negative prior and the structural caveat.
- **Ledger write:** `IMPROVEMENTS.md` gained a new `### D-02 news-sentiment: declined on cost, NOT not-triggered (plan 10-12)` subsection under the existing D-02 trigger-evaluation section, quoting every figure above verbatim, and the Phase 10 results table's `news_sentiment` row was updated from `pending`/`pending` to the measured trigger outcome and `DECLINED ON COST (not "not triggered" -- trigger fired, build never run)`.
- **Tasks 2 and 3 skipped entirely**, per Task 2's own `<precondition>`: no `data/news.py`, no `config.NEWS_COLS`, no gating branch, no measurement run. The ledger entry Task 1 wrote is this plan's whole output, exactly as the plan's own objective anticipated for a non-BUILD route.

## Task Commits

1. **Task 1: Read the D-02 trigger and route this plan** -- `e243e66` (docs) -- routing outcome recorded in `IMPROVEMENTS.md`

Tasks 2 and 3 not executed (precondition unmet on DECLINE route). No plan-metadata commit beyond the one Task 1 commit and the STATE/ROADMAP update commit that follows this SUMMARY.

## Files Created/Modified

- `IMPROVEMENTS.md` -- new `### D-02 news-sentiment: declined on cost, NOT not-triggered (plan 10-12)` subsection (verbatim decision, both projected-cost figures, the governing prior, the structural caveat, the explicit distinction from "not triggered"); `news_sentiment` row in the Phase 10 results table filled with the DECLINED ON COST verdict

## Decisions Made

- Human declined the D-02 trigger's mechanical BUILD outcome on cost grounds (verbatim "DECLINE"), after being presented the measured trigger value, the locked threshold, the live-computed projected fetch cost at two candidate season scopes, the governing negative prior, and the structural caveat. Recorded as "declined on cost" per the plan's own instruction -- distinct from "not triggered" because the trigger genuinely fired; the distinction matters for any future revisit deciding whether to re-open this experiment.
- Season scope for the cost estimate followed `data/transfermarkt.py`'s own "full authorised scope" precedent (`config.SEASONS`) as the primary figure, with the narrower 6-season measurement-only scope quoted alongside it, since the plan's Task 2 action text explicitly models `data/news.py` on `data/transfermarkt.py`'s resumable-backfill shape and that file's own docstring names `config.SEASONS` as its default authorised scope.

## Deviations from Plan

None -- plan executed exactly as written for the DECLINE route. Task 2's `<precondition>` explicitly authorizes skipping Tasks 2 and 3 on a non-BUILD outcome, and the plan's own `<output>` spec anticipates this: "either a recorded not-triggered ledger entry and no new code, or `data/news.py`...". This plan produced the ledger-entry-only output (declined-on-cost variant), matching that anticipated shape.

## Issues Encountered

None.

## User Setup Required

None -- the DECLINE route required no external service configuration. (The plan's `user_setup` block, `GUARDIAN_API_KEY` via the Guardian Open Platform, only applies to the BUILD route and was never reached.)

## Next Phase Readiness

- Plan 10-14 (which owns `IMPROVEMENTS.md`'s ledger writes for the bracket verdicts) has nothing further to do for `news_sentiment` -- this plan already wrote its own ledger entry directly, since Task 3's "hand the ledger write to plan 10-14" instruction only applied on the BUILD route where a measurement exists to hand off. On DECLINE, Task 1's checkpoint action explicitly instructs writing the outcome to `IMPROVEMENTS.md` directly.
- Plan 10-16's close-out should confirm the Phase 10 results table's `news_sentiment` row is no longer `pending` (it is now `DECLINED ON COST`) alongside the six `bracket_*` rows still pending from other plans.
- No `data/build_table.py` wiring follow-up exists for this plan (unlike a BUILD route would have produced) -- there is no `attach()` to wire in, since `data/news.py` was never created.
- No blockers for subsequent Phase 10 plans.

## Self-Check: PASSED

- FOUND: commit `e243e66` in `git log --oneline`
- FOUND: `IMPROVEMENTS.md` contains `### D-02 news-sentiment: declined on cost, NOT not-triggered (plan 10-12)`
- FOUND: `IMPROVEMENTS.md` results table `news_sentiment` row reads `DECLINED ON COST (not "not triggered" -- trigger fired, build never run)`
- Confirmed no `data/news.py` was created (`ls data/news.py` -> not found, as intended for this route)
- Confirmed `config.EXPERIMENTS` carries no `news_sentiment` key (unchanged from before this plan -- it was never actually registered by plan 10-10 despite plan 10-12's own frontmatter artifact note, verified live via `grep -n news_sentiment config.py` returning no hits; irrelevant to the DECLINE route since no flag needed adding)
- Re-ran the plan's own Task 1 `<verify>` automated check against the committed `IMPROVEMENTS.md`: `routing outcome recorded`

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-11*
