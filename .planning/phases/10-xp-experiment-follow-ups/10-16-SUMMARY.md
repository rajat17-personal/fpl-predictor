---
phase: 10-xp-experiment-follow-ups
plan: 16
subsystem: xp-model-experiments
tags: [close-out, honest-harness, split-verdicts, decisions-audit, ledger]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-08's Tier-1 verdicts (availability_flags/transfermarkt_injury REJECTED, D-02 trigger fired), 10-14's bracket close (7/7 HOLD, D-17 not triggered, news_sentiment heading), 10-15's dead-tail closes (fbref_v2 acquisition-format defect, RL notes-only)"
provides:
  - "The D-11 split-verdict combined run (data/processed/experiments/wf_combined_phase10.json, 5 replicas/6 seasons, no --experiments flag): model+chips = 2262, bit-for-bit identical to Phase 9's own final_combined and the phase-open baseline, 18 short of the >=2,280 bar"
  - "A genuine no-op default: config.py byte-identical before/after this plan; tests/test_experiments.py left untouched since zero flags adopted"
  - "tests/test_product.py::test_phase10_flags_default_off_leaves_export_contract_unchanged -- greps every real web/data/*.json payload for av_/tm_/nw_/bracket_ keys, locking the product-contract boundary as a regression"
  - "IMPROVEMENTS.md's three Phase G close-out subsections: Final combined run (D-11 split verdicts), Decisions audit (D-01 through D-21, plus all eight resolves_phase:10 todos named), and What this phase did not resolve"
affects: []

# Actuals (#2632)
actuals:
  tokens: 89000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Empty full-coverage-winner-set combined run: when the ledger's mechanical classification yields zero winners, the D-11 combined run is launched with no --experiments flag at all, reproducing the shipped default exactly -- mirrors Phase 9's own final_combined precedent for the identical empty-winner-set shape"
    - "Real end-to-end python -m predict.export run + git diff --stat, not a fixture-only assertion, to prove the product contract's keys are stable while values legitimately refresh with a fresh model run -- same standard 09-10 set for this class of regression test"

key-files:
  created: []
  modified:
    - tests/test_product.py
    - IMPROVEMENTS.md

key-decisions:
  - "The full-coverage winner set is empty: mechanically classifying all nine Phase 10 flags from their own recorded ledger verdicts (availability_flags/transfermarkt_injury REJECTED, news_sentiment DECLINED ON COST, all six bracket_* HOLD) leaves nothing to combine -- the plan's own instruction for this case (run with no --experiments flag, record the baseline-by-construction outcome as legitimate) was followed exactly, per Phase 9's own precedent for the identical shape"
  - "config.py and tests/test_experiments.py are byte-identical before and after this plan -- a genuine no-op default change, not merely an unchanged file that happened not to need editing. The shipped Phase 10 config equals the Phase 9 config equals the Phase 10 opening baseline."
  - "D-10's fallback test was run and passed (test_missing_snapshot_degrades_to_nan_not_raise) even though availability_flags' own D-09 verdict already forbids the flip independent of D-10 -- the plan's own verify block requires this gate to run first regardless of whether a flip is actually pending on it"
  - "Fixed a Rule 1 bug in the new test_product.py test immediately after its own commit: it read web/data/*.json via a bare open(path).read(), which tripped tests/test_reliability.py's repo-wide ops.jsonio bare-file-handle scanner. Switched to pathlib.Path(path).read_text() (the scanner's accepted idiom) in a small separate fix commit rather than amending."
  - "The fbref_v2 'did not resolve' item is recorded as a stronger finding than the plan's own anticipated shape (a leakage limitation on usable columns) -- the actual finding is that the three source columns are 100% empty across all 5,454 rows/ten seasons, confirmed live on FBref's own page, so no leakage question ever arose because there was no data to be leaky or safe with"
  - "Two hypothetical deferred-wiring items the plan's own action text named (a data/build_table.py news-attach block; a requirements.in onnxruntime promotion) are recorded as genuinely moot rather than silently omitted -- neither item's upstream trigger (news_sentiment adoption; a torch bracket candidate clearing D-15's gate) ever fired, so neither artifact was ever created to defer"

requirements-completed: [TODO-AVAIL-FLAGS, TODO-TM-INJURY, TODO-BRACKET, TODO-NEWS, TODO-TOP100, TODO-FPLREVIEW, TODO-FBREF-MANUAL, TODO-RL-SHAPING, PHASE10-CRON, PHASE10-COLAB-SEAM, PHASE10-CRITERIA]

coverage:
  - id: D1
    description: "The D-11 split-verdict combined run: full-coverage winner set mechanically derived as empty from the ledger, run launched with no --experiments flag, model+chips=2262 measured and reconciled against the 2,262 baseline and 2,280 bar, availability_flags verified absent from the combined flag set"
    requirement: PHASE10-CRITERIA
    verification:
      - kind: integration
        ref: "data/processed/experiments/wf_combined_phase10.json -- replicas=5, seasons=6, model+chips=2262, availability_flags not in enabled flag set (all False)"
        status: pass
      - kind: unit
        ref: "python -m pytest tests/test_availability.py::test_missing_snapshot_degrades_to_nan_not_raise -q -- 1 passed (D-10 gate)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Single reviewable default-change commit: config.py byte-identical before/after (zero flags adopted), tests/test_experiments.py left untouched, verified programmatically that every flag flipped True is named in the registry test (vacuously true here since zero flags flipped)"
    requirement: PHASE10-CRITERIA
    verification:
      - kind: other
        ref: "git diff --stat config.py -- empty; python -m pytest tests/test_experiments.py -q -- 49 passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Product surface proven unchanged: new test_phase10_flags_default_off_leaves_export_contract_unchanged greps every real web/data/*.json payload for av_/tm_/nw_/bracket_ keys (none found); real python -m predict.export run completed; git diff --stat web/data classified as key-stable value-refresh (5 files changed, single-line JSON rewrites, key sets byte-identical before/after per a scripted key-set diff)"
    requirement: TODO-AVAIL-FLAGS
    verification:
      - kind: unit
        ref: "tests/test_product.py::test_phase10_flags_default_off_leaves_export_contract_unchanged -- 1 passed"
        status: pass
      - kind: integration
        ref: "python -m predict.export -- real run, GW4, 656 players; git diff --stat web/data -- captains/meta/squad/xp_table.json changed (2 chars each, single-line rewrites), fixtures/chips/leaders/standings unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every D-01 through D-21 decision audited with an outcome and evidence citation; all eight resolves_phase:10 todos named by file stem with their resolution; Phase 10 results table has zero unfilled cells; all Phase A-F anchors (incl. Phase 9's own decisions-audit and did-not-resolve headings) intact"
    requirement: TODO-BRACKET
    verification:
      - kind: other
        ref: "python -c checks against IMPROVEMENTS.md -- all 21 D-NN tokens present in the Decisions audit section; all 8 todo stems named in Phase G; results table has zero pending cells; five prior anchor headings intact"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full repo test suite stays green after every edit this plan made"
    requirement: TODO-NEWS
    verification:
      - kind: integration
        ref: "python -m pytest -q -- 329 passed, 1 pre-existing skip, 0 failed (297.90s)"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-09-11
status: complete
---

# Phase 10 Plan 16: Phase Close-Out -- D-11 Split-Verdict Combined Run, D-01..D-21 Decisions Audit, Honest Residue Summary

**The D-11 split-verdict combined run measured `model+chips` = 2262 -- bit-for-bit identical to Phase 9's own close and Phase 10's own open, 18 short of the >=2,280 bar -- because the full-coverage winner set derived mechanically from the ledger is empty (all nine Phase 10 flags REJECTED/HOLD/DECLINED); the shipped `config.py` default is therefore a genuine no-op, the product contract was proven key-stable by a real `python -m predict.export` run, and every one of D-01 through D-21 plus all eight `resolves_phase: 10` todos now carries a recorded outcome in `IMPROVEMENTS.md`.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-11T15:20:00Z
- **Completed:** 2026-09-11T16:15:00Z
- **Tasks:** 3 of 3 executed with commits
- **Files modified:** 2 source files (`tests/test_product.py`, `IMPROVEMENTS.md`) + 4 refreshed `web/data/*.json` value-only payloads from the real export run

## Accomplishments

- **Task 1: the D-11 split-verdict combined run and the single default change.** Classified all nine Phase 10 flags mechanically from their own recorded ledger verdicts:

  | flag | class | verdict |
  |---|---|---|
  | `availability_flags` | partial-coverage (D-09) | REJECTED -- dual criterion, neither leg met |
  | `transfermarkt_injury` | full-coverage | REJECTED -- 6-season `model+chips` regressed -20 |
  | `news_sentiment` | full-coverage (conditional) | DECLINED ON COST -- never built |
  | `bracket_ridge`/`bracket_xgb`/`bracket_catboost`/`bracket_mlp` | full-coverage | HOLD -- D-15 gate |
  | `bracket_rnn`/`bracket_transformer` | partial-coverage (single-season Colab) | HOLD -- D-15 gate, own baseline |

  The full-coverage winner set is **empty**. Per the plan's own instruction, ran `scripts/experiment_run.sh combined_phase10 --replicas 5` with **no `--experiments` flag** -- a background run monitored via its own log (`data/processed/experiments/combined_phase10-20260911T152104Z.log`) to completion. Result: `data/processed/experiments/wf_combined_phase10.json`, 5 replicas over 6 seasons, `model+chips = 2262` -- **bit-for-bit identical** to `wf_final_combined.json` (Phase 9's own close) and to the plan 09-01/10-01 baseline, 18 short of the `>=2,280` bar. `availability_flags` verified absent from the combined run's enabled flag set (all 18 registry keys `False`) per D-11's split rule -- its own dual-criterion verdict stands separately in the "availability_flags: dual-criterion adoption verdict (plan 10-08)" ledger section. D-10's fallback gate (`tests/test_availability.py::test_missing_snapshot_degrades_to_nan_not_raise`) was run first and passed, though moot since D-09's own verdict already forbids the flip. Since nothing adopted: **`config.py` is byte-identical before and after this plan** (`git diff --stat config.py` empty) and `tests/test_experiments.py::test_experiments_registry_default_off` was **left untouched** -- no commit was needed or made for this task's own file changes, matching the plan's own "record the no-op explicitly" instruction.
- **Task 2: proved the weekly product surface is unchanged unless a flag adopted.** Added `test_phase10_flags_default_off_leaves_export_contract_unchanged` to `tests/test_product.py`, greping every real `web/data/*.json` payload for `av_`/`tm_`/`nw_`/`bracket_`-prefixed keys (none found). Ran a real end-to-end `python -m predict.export` (live FPL API, live model artifact, GW4, 656 players). `git diff --stat web/data`: `captains.json`, `meta.json`, `squad.json`, `xp_table.json` each changed by 2 lines (the whole file is one JSON line, so this is a full-file value rewrite); `fixtures.json`, `chips.json`, `leaders.json`, `standings.json` unchanged. A scripted key-set diff (old vs. new, per file) confirmed every changed file's top-level/row key set is **byte-identical before and after** -- pure value refresh from a fresh live-data model run, not any key addition, removal, or Phase 10 flag effect (since nothing adopted, no flag-attributable value delta exists to report either -- this run's value changes are purely due to time/data drift between the pre-plan and post-plan export runs). `web/data/watchlist.json`'s pre-existing uncommitted modification (present before this session started, not written by `predict.export`, which never touches that file) was correctly left out of the commit.
- **Task 3: decisions audit and the honest record of what this phase did not resolve.** Wrote three subsections under `## Phase G` in `IMPROVEMENTS.md`:
  - `### Final combined run (plan 10-16, D-11 split verdicts)` -- the command, artifact path, 6-season table, the reconciliation against 2,262/2,280, the explicit split statement, and the shipped-default before/after (unchanged).
  - `### Decisions audit (plan 10-16, D-01 through D-21)` -- a `decision | what it required | outcome | evidence` row for every one of the 21 Phase 10 implementation decisions from `10-CONTEXT.md`, plus a "Todos resolved" table naming all eight `resolves_phase: 10` todo file stems with the plan that closed each.
  - `### What this phase did not resolve` -- the unmoved 2,280 bar; both genuinely-measured-and-rejected Tier-1 experiments; `news_sentiment`'s declined-on-cost (not not-triggered) status; the 7/7 HOLD bracket result; the `fbref_v2` acquisition-format defect (a stronger finding than a leakage limitation -- the source columns are 100% empty, not merely leakage-unsafe); both hypothetical deferred-wiring items recorded as genuinely moot (neither ever had an upstream trigger fire); both unverifiable priors (`10.2478/ijcss-2025-0008`, `danielfrees/mlpremier`); the un-extended single-season Colab candidates with their unknown per-season Colab unit cost; and the EXP-1 benchmark's zero-`availability_flags`-coverage structural caveat.

  All five prior Phase A-F anchor headings (including Phase 9's own `### Decisions audit (plan 09-10, D-01 through D-16)` and `### What this phase did not resolve`) confirmed intact by a scripted check. The Phase 10 results table (9 rows) has zero unfilled cells.
- **Deviation found and fixed mid-plan:** the new `test_phase10_flags_default_off_leaves_export_contract_unchanged` initially read payloads via a bare `open(path).read()`, tripping the repo-wide `ops.jsonio` bare-file-handle scanner (`tests/test_reliability.py`). Fixed with `pathlib.Path(path).read_text()` in a small separate commit (Rule 1 -- see Deviations below).
- **Repo-wide `python -m pytest -q`: 329 passed, 1 pre-existing skip, 0 failed** (297.90s), re-confirmed after every edit this plan made.

## Task Commits

1. **Task 1: the split-verdict combined run and the single default change** -- no commit (measurement-only; `config.py`/`tests/test_experiments.py` both byte-identical, a genuine no-op; the combined-run artifact is gitignored under `data/processed/`)
2. **Task 2: prove the weekly product surface is unchanged unless a flag adopted** -- `f715aab` (test), plus a Rule 1 fix -- `78374af` (fix)
3. **Task 3: decisions audit and the honest record of what this phase did not resolve** -- `7ebe62b` (docs)

**Plan metadata:** (this commit, following)

## Files Created/Modified

- `tests/test_product.py` -- new `test_phase10_flags_default_off_leaves_export_contract_unchanged`, reading real `web/data/*.json` payloads via `pathlib.Path.read_text()`
- `IMPROVEMENTS.md` -- three new `## Phase G` close-out subsections (Final combined run, Decisions audit D-01..D-21, What this phase did not resolve)
- `web/data/captains.json`, `meta.json`, `squad.json`, `xp_table.json` -- refreshed by the real `python -m predict.export` run this task required (value-only, key sets unchanged)
- `config.py`, `tests/test_experiments.py` -- confirmed byte-identical, no commit (the plan's own required no-op outcome)

## Decisions Made

See `key-decisions` in frontmatter. Headline: the full-coverage winner set is genuinely empty (every Phase 10 flag REJECTED/HOLD/DECLINED), so this plan's own close-out reproduces Phase 9's own "baseline by construction" shape exactly -- the combined run, the config no-op, and the unchanged product contract are all downstream of that one mechanical fact.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] New export-contract test used a bare `open()`, tripping the repo-wide file-handle scanner**
- **Found during:** Task 2, immediately after committing the new test
- **Issue:** `test_phase10_flags_default_off_leaves_export_contract_unchanged` read `web/data/*.json` payloads via `open(path).read()`, a bare file handle that `tests/test_reliability.py::test_no_bare_file_handles_in_tracked_python` (Phase 6's `ops.jsonio` chokepoint gate) correctly flagged.
- **Fix:** Switched to `pathlib.Path(path).read_text()` -- the scanner's own accepted idiom, appropriate here since this test only greps raw text for a key-prefix substring and has no JSON-parsing need `ops.jsonio` would otherwise serve.
- **Files modified:** `tests/test_product.py`
- **Verification:** `pytest tests/test_reliability.py::test_no_bare_file_handles_in_tracked_python tests/test_product.py -q` -- 12 passed (was 1 failed, 11 passed before the fix)
- **Committed in:** `78374af` (separate small fix commit, not folded into the prior commit -- per the executor protocol's "never amend" rule)

---

**Total deviations:** 1 (Rule 1 -- a bug in my own new test code, caught by an existing repo-wide regression gate before it could land unnoticed)
**Impact on plan:** None on the plan's actual deliverables -- the export-contract test's real behavior (greping for `av_`/`tm_`/`nw_`/`bracket_` keys) was correct from the start; only its file-reading idiom needed correcting to satisfy an unrelated, pre-existing repo-wide invariant.

## Issues Encountered

None beyond the deviation above. The combined walk-forward run (6 seasons x 5 replicas) and the real `predict.export` run were both long-running (the combined run several minutes; the live-data export ~2 minutes fetching 656 players' match history from the live FPL API) and were run to completion via background monitoring per the project's own long-run convention -- no failures, no interruption.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- **Phase 10 is fully closed.** The combined run's `model+chips` (2262) is identical to both its own opening baseline and Phase 9's own closing figure -- the phase's honest walk-forward frontier is unchanged at close. `config.py`'s shipped defaults are byte-identical to Phase 9's and to Phase 10's own open: every experiment flag stays `False`.
- **Every D-01 through D-21 decision and all eight `resolves_phase: 10` todos have a recorded outcome** in `IMPROVEMENTS.md`'s `## Phase G` section -- no ambiguous or silently-dropped item remains from this phase's scope.
- **The product surface (`predict/live.py`, `predict/export.py`) needed zero wiring changes** -- proven by a real end-to-end export run and a new permanent regression test, matching Phase 9's own precedent for this exact situation (an empty-adoption phase).
- **Open items carried forward, all explicitly recorded, none silent:** the `>=2,280` primary bar remains uncleared (an open question for a future phase, not this one's to answer); `fbref_v2`'s acquired-but-defective data snapshot sits as a permanent evidentiary record (ten CSVs + README) for any future revisit; the RL reward-shaping notes are on record for anyone training that policy again; the EXP-1 benchmark's zero-`availability_flags`-coverage structural gap needs a different benchmark basis before it can be usefully re-attempted.
- No blockers. This was the final plan in Phase 10's own sequence.

## Self-Check: PASSED

- FOUND: `data/processed/experiments/wf_combined_phase10.json` (5 replicas, 6 seasons, `model+chips`=2262, `availability_flags` absent from enabled set)
- FOUND: `tests/test_product.py` (`test_phase10_flags_default_off_leaves_export_contract_unchanged`)
- FOUND: `IMPROVEMENTS.md` (three new Phase G subsections, all 21 D-NN decisions audited, all 8 todos named)
- FOUND: commits `f715aab`, `78374af`, `7ebe62b` in `git log --oneline`
- Re-ran `python -m pytest tests/test_availability.py::test_missing_snapshot_degrades_to_nan_not_raise -q`: 1 passed
- Re-ran `python -m pytest tests/test_experiments.py -q`: 49 passed
- Re-ran `python -m pytest tests/test_product.py -q`: 12 passed
- Re-ran repo-wide `python -m pytest -q`: 329 passed, 1 pre-existing skip, 0 failed
- Re-ran the plan's own Task 1/2/3 `<verify>` python one-liners: all pass (combined-run assertions, config no-op assertion, product-contract grep, decisions-audit/todo-naming/results-table/anchor-intactness checks)
- `git diff --stat config.py`: empty (confirmed no-op)
- `config.EXPERIMENTS`: all 18 flags still `False`

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-11*
