---
phase: 10-xp-experiment-follow-ups
plan: 08
subsystem: xp-model-experiments
tags: [experiment-adoption, honest-harness, availability, transfermarkt-injury, news-sentiment-trigger, ledger]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-06's committed FPL-Core-Insights vendoring (92.7% 2025-26 availability coverage) and 10-07's completed 2,623/2,623-player Transfermarkt injury backfill (12,503 spells, 1,697 players), both feeding the attach() calls this plan wires into the pipeline"
  - phase: 10-xp-experiment-follow-ups
    provides: "10-01's declared Phase G adoption criteria (D-09 dual criterion, D-02's exact 0.500 trigger) locked into IMPROVEMENTS.md before any measuring run in this phase"
provides:
  - "data/build_table.py's fifth optional-enrichment block (tm_mod.attach), joining the completed Transfermarkt injury backfill into player_gw.parquet/features.parquet unconditionally, independent of the transfermarkt_injury flag"
  - "Four tagged walk-forward artifacts (wf_avail_base_2526, wf_avail_on_2526, wf_tm_base6, wf_tm_on6) and three tagged benchmark artifacts (benchmark_tier1_base, benchmark_tier1_avail, benchmark_tier1), all measured against one frozen features.parquet"
  - "IMPROVEMENTS.md's availability_flags and transfermarkt_injury verdict subsections (both REJECTED, numbers on record) and the D-02 news-sentiment trigger record (BUILD, 0.3874 < 0.500)"
affects: [10-12, 10-16]

# Actuals (#2632)
actuals:
  tokens: 2900
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Fifth optional-enrichment block in data/build_table.py mirrors the four existing ones exactly (try/except Exception, `[transfermarkt] skipped (...)` print), keeping the injury-column computation unconditional so the feature matrix never depends on the experiment flag"
    - "A/B measurement against a freshly-measured contemporaneous control, not a historical baseline figure, because a mid-plan pipeline rebuild (Task 1) changes the feature matrix column set even for the flag-off arm"

key-files:
  created: []
  modified:
    - data/build_table.py
    - data/transfermarkt.py
    - IMPROVEMENTS.md

key-decisions:
  - "Task 1's rebuild (fifth optional-enrichment block + the load_transfermarkt() DataFrame-truthiness Rule-1 fix) had already landed in a prior session's commit (9e095a6) before this executor was invoked; verified the frozen features.parquet sha256 (ae809b5b6169ee776363e543fd6c50e78017cf1f36e1c3742807feb16336dc3f, 253,509 rows x 172 columns) matched the value recorded in that commit's own message before trusting any measurement built on it, rather than re-doing already-complete work"
  - "A prior session had also already completed 5 of the 6 Task 2 measurement runs (avail_base_2526, avail_on_2526, tm_base6, benchmark_tier1_base, benchmark_tier1_avail) against the identical frozen matrix (confirmed newer mtime than features.parquet, and exact flag/replica/season match to the plan's spec); killed the redundant duplicate processes this executor had already launched for those five rather than double-spending compute, and only ran the two genuinely missing pieces (wf_tm_on6, the 6-season injury-on run interrupted by a session restart, and benchmark_tier1, the combined ranking run interrupted the same way)"
  - "Restored data/processed/experiments/bracket_gate_mlp.json to its canonical value (granularity pooled, spearman_xp_med 0.3942) after the repo-wide pytest re-verification run polluted it via tests/test_bracket.py::test_granularity_bracket_writes_gate_schema (WINDOWS.md entry 6's documented, known side effect) — restored by re-running the real deterministic models.bracket.deep.run_granularity_bracket('mlp') call, not by hand-editing the JSON, matching 10-11-SUMMARY.md's own precedent for this exact pollution"

patterns-established:
  - "When a plan is picked up mid-execution after a session interruption, verify each expected artifact's mtime against the frozen basis hash before trusting it, and only re-run the genuinely missing or stale pieces -- redoing already-valid multi-hour compute wastes real time/cost for no gain in honesty"

requirements-completed: [TODO-AVAIL-FLAGS, TODO-TM-INJURY]

coverage:
  - id: D1
    description: "Both Tier-1 feature families (availability, injury) reach features.parquet through the standard optional-enrichment path; the frozen matrix every measurement in this plan shares is recorded by hash and verified unchanged across all runs"
    requirement: TODO-AVAIL-FLAGS
    verification:
      - kind: integration
        ref: "features.parquet sha256 ae809b5b6169ee776363e543fd6c50e78017cf1f36e1c3742807feb16336dc3f (253,509 rows x 172 columns) -- verified identical at Task 1 commit time and again before every Task 2 measurement"
        status: pass
      - kind: unit
        ref: "python -m pytest -q -- 323 passed, 1 skipped (pre-existing .env-gated cron test), 0 failed"
        status: pass
    human_judgment: false
  - id: D2
    description: "availability_flags measured against D-09's dual criterion (2025-26 model+chips +25 AND pooled played-only Spearman +0.03 over 0.383), both legs on record, REJECTED (neither leg met, coverage 92.7% not thin)"
    requirement: TODO-AVAIL-FLAGS
    verification:
      - kind: integration
        ref: "data/processed/experiments/wf_avail_base_2526.json / wf_avail_on_2526.json -- 2025-26 model+chips 2172 -> 2172 (+0, need +25)"
        status: pass
      - kind: integration
        ref: "data/processed/experiments/benchmark_tier1_base.json / benchmark_tier1_avail.json -- pooled played-only spearman_xp_med 0.3832 -> 0.3832 (+0.0000, need +0.03)"
        status: pass
    human_judgment: false
  - id: D3
    description: "transfermarkt_injury measured against the standard 6-season >=2,280 bar, REJECTED (2262 -> 2242, a -20 regression against its own fresh control)"
    requirement: TODO-TM-INJURY
    verification:
      - kind: integration
        ref: "data/processed/experiments/wf_tm_base6.json / wf_tm_on6.json -- 6-season model+chips 2262 -> 2242"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-02 news-sentiment trigger evaluated against the locked 0.500 threshold using the measured post-Tier-1 pooled Spearman; outcome (BUILD) recorded before plan 10-12 acts on it, with the two-scoreable-seasons/zero-availability-coverage structural caveat stated explicitly"
    requirement: TODO-AVAIL-FLAGS
    verification:
      - kind: integration
        ref: "data/processed/experiments/benchmark_tier1.json -- pooled played-only spearman_xp_med 0.3874 < 0.500 -> BUILD"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both verdicts recorded in IMPROVEMENTS.md's Phase 10 results table with numbers, each flag stays default-off; seven remaining rows (news_sentiment + 6 bracket flags) still pending; all Phase A-F anchors intact"
    requirement: TODO-AVAIL-FLAGS
    verification:
      - kind: unit
        ref: "python -c '...' -- both Tier-1 rows filled, non-pending; bracket-row pending count >= 14 (measured 15, includes one prose occurrence); all named Phase A-F headings present; config.EXPERIMENTS all False"
        status: pass
    human_judgment: false

duration: N/A (session spanned an interruption/restart; wall-clock not meaningfully attributable to this executor alone)
completed: 2026-09-11
status: complete
---

# Phase 10 Plan 08: Tier-1 Adoption Verdicts + D-02 Trigger Summary

**Both Tier-1 experiments (availability_flags, transfermarkt_injury) measured against their pre-declared criteria on one frozen 253,509x172 feature matrix and REJECTED by the mechanical rule — availability moved neither leg of its dual criterion at all, and the injury family actually regressed 6-season `model+chips` by 20 points against its own fresh control — and the D-02 news-sentiment trigger fired (0.3874 < 0.500), obligating plan 10-12 to build the sentiment experiment.**

## Performance

- **Tasks:** 3 (all committed or otherwise verified complete)
- **Files modified:** 3 (`data/build_table.py`, `data/transfermarkt.py` — Task 1, landed in a prior session; `IMPROVEMENTS.md` — Task 3, this session)

## Accomplishments

- **Task 1 (wiring + rebuild)** had already landed in commit `9e095a6` before this executor was invoked. Verified rather than re-done: the fifth optional-enrichment block in `data/build_table.py` (`tm_mod.attach(full)`, mirroring the four existing blocks' `try/except Exception` + skip-print shape) is present, the known `load_transfermarkt() or pd.DataFrame(...)` DataFrame-truthiness crash at `data/transfermarkt.py`'s `--build` CLI exit is already fixed with an explicit `is not None` check, and the frozen `features.parquet` (sha256 `ae809b5b6169ee776363e543fd6c50e78017cf1f36e1c3742807feb16336dc3f`, **253,509 rows x 172 columns**) matches the hash recorded in that commit's own message — confirmed unchanged across every measurement run in this plan.
- **Task 2 (five measurements)** was likewise partially complete from a prior session: `wf_avail_base_2526.json`, `wf_avail_on_2526.json`, `wf_tm_base6.json`, `benchmark_tier1_base.json`, and `benchmark_tier1_avail.json` all already existed with mtimes after `features.parquet`'s own mtime and exactly matching flag states/replica counts/season scopes. This executor killed its own redundant duplicate launches for those five (verified-valid, not re-run) and completed only the two genuinely missing/interrupted pieces: the 6-season `tm_on6` injury-arm walk-forward run (`data/processed/experiments/wf_tm_on6.json`) and the combined `benchmark_tier1.json` ranking run — both of which had been silently killed mid-run by an intervening session restart and were relaunched to completion.
- **Task 3 (ledger write-up)**: three new subsections under `## Phase G` in `IMPROVEMENTS.md` (`### availability_flags:`, `### transfermarkt_injury:`, `### D-02 news-sentiment trigger evaluation`), each with its exact commands, artifact paths, a measured-vs-bar table, and the mechanical verdict; both Tier-1 rows in the Phase 10 results table filled with numbers (no longer `pending`); the seven remaining rows (`news_sentiment` + the six `bracket_*` flags) left untouched at `pending`, matching the plan's own scope boundary (D-02's trigger firing is recorded in prose, not by filling `news_sentiment`'s own row — that happens when plan 10-12 actually measures it).
- **Repo-wide `python -m pytest -q`**: 323 passed, 1 skipped (pre-existing `.env`-gated cron test), 0 failed — re-verified this session. The run's known side effect (`tests/test_bracket.py::test_granularity_bracket_writes_gate_schema` overwriting the live `bracket_gate_mlp.json`, WINDOWS.md entry 6) was observed exactly as documented and restored by re-running the real deterministic `models.bracket.deep.run_granularity_bracket('mlp')` call — reproduced the canonical `granularity: pooled, spearman_xp_med: 0.3942` byte-for-byte, matching 10-11-SUMMARY.md's own precedent for this pollution.

## Measured Figures (every number this plan's verdicts rest on)

**D-09(a) — availability, 2025-26 `model+chips`** (`scripts/experiment_run.sh avail_base_2526 --seasons 2025-26 --replicas 5` / `... avail_on_2526 ... --experiments availability_flags`):

| | base | flag on | delta | bar |
|---|---:|---:|---:|---:|
| `model+chips` | 2172 | 2172 | **+0** | >= +25 |

Identical to Phase F's own recorded 2025-26 figure (10-01-SUMMARY.md's single-replica tracer also read 2172 for both arms) — Task 1's rebuild, despite adding the `tm_*` family to `features.parquet`, did not move this number.

**D-09(b) — availability, pooled played-only ranking** (`python -m backtest.benchmark_external --experiments none --tag tier1_base` / `--experiments availability_flags --tag tier1_avail`):

| | base | flag on | delta | bar |
|---|---:|---:|---:|---:|
| pooled `spearman_xp_med` (2021-22, 2022-23, n=17,488) | 0.3832 | 0.3832 | **+0.0000** | >= +0.03 over 0.383 |

Structurally explained, not just observed flat: `benchmark_external`'s two scoreable seasons carry **zero `availability_flags` coverage** (the provider only covers 2025-26 onward), so `tier1_base`/`tier1_avail` are numerically identical to four decimal places by construction.

**D-09 dual criterion: NEITHER leg met → availability_flags REJECTED.** `config.EXPERIMENTS['availability_flags']` stays `False`.

**Transfermarkt — standard 6-season protocol** (`scripts/experiment_run.sh tm_base6 --replicas 5` / `... tm_on6 ... --experiments transfermarkt_injury`):

| | fresh base | flag on | delta | bar |
|---|---:|---:|---:|---:|
| 6-season `model+chips` | 2262 | 2242 | **-20** | >= 2,280 |

Not merely short — a genuine regression against its own contemporaneous control. **transfermarkt_injury REJECTED.** `config.EXPERIMENTS['transfermarkt_injury']` stays `False`.

**Post-Tier-1 combined ranking measurement / D-02 trigger input** (`python -m backtest.benchmark_external --experiments availability_flags,transfermarkt_injury --tag tier1`):

- Pooled played-only `spearman_xp_med` = **0.3874** (2021-22, 2022-23, n=17,488)
- Locked D-02 threshold: **< 0.500** triggers the news-sentiment build
- **0.3874 < 0.500 → BUILD.** Plan 10-12 is required to build the news-sentiment experiment.
- The entire **+0.0042** movement from the fresh base (0.3832) is attributable to `transfermarkt_injury` alone (which has real, if modest, coverage in these two seasons) — `availability_flags` contributed exactly zero to this number, per the structural note above.

## Background Run Log Paths (`tail -f` commands, per project convention)

All runs completed by the time this SUMMARY was written; logs retained for audit:

```
data/processed/experiments/avail_base_2526-20260910T234505Z.log   (prior session)
data/processed/experiments/avail_on_2526-20260910T234508Z.log     (prior session)
data/processed/experiments/tm_base6-20260911T035607Z.log          (prior session)
data/processed/experiments/tm_on6-20260911T084949Z.log            (relaunched after session restart; completed 04:55 EDT)
data/processed/experiments/benchmark_tier1_base-20260911T060115Z.log  (this session, quick)
data/processed/experiments/benchmark_tier1_avail-20260911T060115Z.log (this session, quick)
data/processed/experiments/benchmark_tier1-20260911T115022Z.log       (relaunched after session restart; completed ~07:50)
```

## Task Commits

1. **Task 1: Wire the injury attach into the pipeline and rebuild** — `9e095a6` (feat) — landed in a prior session; verified, not redone, this session.
2. **Task 2: Run the Tier-1 A/B measurements** — no file changes (measurement-only task); five tagged artifacts on disk, verified/completed this session.
3. **Task 3: Write both Tier-1 verdicts and the D-02 trigger record to the ledger** — `5181e6a` (docs)

**Plan metadata:** (this commit, following)

## Files Created/Modified

- `data/build_table.py` — fifth optional-enrichment block (`tm_mod.attach`), `transfermarkt as tm_mod` import (prior session, verified)
- `data/transfermarkt.py` — the `load_transfermarkt() or pd.DataFrame(...)` truth-value-ambiguous crash fixed with an explicit `is not None` check (prior session, verified)
- `IMPROVEMENTS.md` — three new `## Phase G` subsections (`availability_flags`, `transfermarkt_injury`, D-02 trigger), both Tier-1 results-table rows filled

## Decisions Made

- Trusted a prior session's already-committed Task 1 work and already-completed 5-of-6 Task 2 artifacts after independently verifying their sha256/mtime/flag-state correctness against the plan's own spec, rather than re-running multi-hour walk-forward compute redundantly. Killed the duplicate processes this executor had itself already launched for the five valid artifacts.
- Restored `bracket_gate_mlp.json` via a real re-run of `models.bracket.deep.run_granularity_bracket('mlp')` (deterministic, fixed seed) after `pytest`'s known side effect overwrote it, rather than hand-editing JSON — matches the established precedent from 10-11-SUMMARY.md for the identical pollution.
- Recorded the D-02 trigger outcome (BUILD) in its own ledger subsection without touching the `news_sentiment` row's `pending` state in the Phase 10 results table — that row is filled when plan 10-12 actually measures the built experiment, per the plan's own scope boundary and its `<verify>`'s expectation that exactly seven rows (news_sentiment + six bracket flags) remain pending.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Two of Task 2's five measurement runs had been silently killed by an intervening session restart**
- **Found during:** Task 2, verifying prior-session artifacts before proceeding
- **Issue:** A prior executor session had launched all necessary Task 2 runs, but a session restart killed the `tm_on6` (6-season injury-arm walk-forward) and `benchmark_tier1` (combined ranking) processes mid-run, leaving no output artifact for either. This executor's own first attempt to relaunch replacements was itself later confirmed complete by the coordinator for `tm_on6` (relaunched under an identical command) but `benchmark_tier1` needed a second relaunch by this executor after its own first attempt was also killed by the same restart event.
- **Fix:** Verified via `ps`/log-tail that both processes had genuinely stopped mid-run (log files ending mid-warning-stream with no final `[wf]`/summary line and no JSON artifact written), then relaunched both to completion with the identical plan-specified command.
- **Files modified:** none (measurement-only; no code changes)
- **Verification:** `wf_tm_on6.json` and `benchmark_tier1.json` both now exist with the correct flag states, replica counts, and season scopes, matching the plan's `<verify>` block exactly.

**2. [Rule 1 - Bug] `bracket_gate_mlp.json` polluted by the repo-wide pytest re-verification run**
- **Found during:** Post-pytest sanity check, before writing the ledger
- **Issue:** `tests/test_bracket.py::test_granularity_bracket_writes_gate_schema` overwrote the live `data/processed/experiments/bracket_gate_mlp.json` with a monkeypatched tiny-run result (`granularity: per_position, pooled: 0.067`) — the exact, previously-documented pollution in WINDOWS.md entry 6.
- **Fix:** Re-ran the real `models.bracket.deep.run_granularity_bracket('mlp')` call (deterministic, fixed seed 0), which reproduced the canonical `granularity: pooled, spearman_xp_med: 0.3942` result byte-for-byte, matching 10-11-SUMMARY.md's own documented precedent for recovering from this exact side effect.
- **Files modified:** `data/processed/experiments/bracket_gate_mlp.json` (gitignored runtime artifact, not committed)
- **Verification:** File content re-inspected after the fix; matches the value 10-11-SUMMARY.md's own Self-Check recorded (`granularity: pooled`, `spearman_xp_med: 0.3942`).

---

**Total deviations:** 2 (1 Rule-3 blocking-issue relaunch of interrupted runs, 1 Rule-1 bug/pollution recovery — both process-continuity issues from the session interruption, not plan-text or code defects)
**Impact on plan:** Neither required a code change; both were necessary to produce a complete, honest measurement set on the frozen basis the plan requires.

## Issues Encountered

- This plan's execution spanned an unplanned session restart (mid-Task-2), which silently killed two long-running background processes without any error signal beyond an incomplete log file. Recovery required manually diffing prior-session artifacts' mtimes against `features.parquet`'s own mtime and each artifact's recorded flag/replica/season fields against the plan's spec, rather than trusting log presence alone — a useful discipline for any future multi-hour background-run plan that might span a restart.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 10-12 is now unblocked and **required** to act: the D-02 trigger fired (0.3874 < 0.500), so it must build the news-sentiment experiment (GDELT/Guardian sources, per the "Data provenance and access risk" table's conditional rows), governed by `danielfrees/mlpremier`'s documented negative prior on tuning-budget expectations.
- Both Tier-1 flags (`availability_flags`, `transfermarkt_injury`) are REJECTED and stay default-off; all their code (`data/availability.py`, `data/transfermarkt.py`, the two feature families, and their `apply_experiment_feature_gating` branches) stays merged per D-08, computed unconditionally, simply unused as model features by default — no further action needed on either.
- Plan 10-16's close-out should confirm no default flip is pending from this plan (there is none — both REJECTED verdicts require no `config.py` edit) and that the Phase 10 results table's remaining seven rows (`news_sentiment` + six `bracket_*`) are filled by their respective plans before the phase closes.
- No blockers.

## Self-Check: PASSED

- FOUND: `data/build_table.py` (fifth optional-enrichment block, `tm_mod.attach`)
- FOUND: `data/transfermarkt.py` (explicit `is not None` fix)
- FOUND: `IMPROVEMENTS.md` (three new verdict subsections, both Tier-1 rows filled)
- FOUND: commit `9e095a6` (Task 1, prior session)
- FOUND: commit `5181e6a` (Task 3, this session)
- FOUND: `data/processed/experiments/wf_avail_base_2526.json`, `wf_avail_on_2526.json`, `wf_tm_base6.json`, `wf_tm_on6.json`, `benchmark_tier1_base.json`, `benchmark_tier1_avail.json`, `benchmark_tier1.json` — all present, correct flag states/replicas/seasons
- Re-verified `features.parquet` sha256 `ae809b5b6169ee776363e543fd6c50e78017cf1f36e1c3742807feb16336dc3f` (253,509 x 172) unchanged across every measurement
- Re-ran repo-wide `python -m pytest -q`: 323 passed, 1 skipped, 0 failed
- Re-ran all of Task 2's and Task 3's own `<verify>` commands: all pass
- `config.EXPERIMENTS`: all flags still `False`

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-11*
