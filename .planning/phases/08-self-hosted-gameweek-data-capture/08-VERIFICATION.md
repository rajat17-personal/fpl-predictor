---
phase: 08-self-hosted-gameweek-data-capture
verified: 2026-09-12T09:15:00Z
status: gaps_found
score: 12/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "The daily cron runs the capture module every day, so a newly-finished gameweek is bounded to a one-day capture window (goal clause: '...runs from scripts/daily.sh...')"
    status: failed
    reason: "scripts/daily.sh has no `run_step data.gw_capture` line — confirmed by direct file read and by `git log -1 -- scripts/daily.sh` showing the last touching commit (9ded4f3, a Phase 10 commit) predates any Phase 8 work. This is Wave 5 (08-05-PLAN.md Task 2), which never ran: Task 1's blocking-human decision gate asked whether Phase 7's freeze on scripts/daily.sh had lifted, and the developer answered `defer` on 2026-09-12 (verbatim, recorded in 08-05-SUMMARY.md) because Phase 7 (Parity Validation & Cutover) has only 3 of 6 plans complete and CUT-01 is recorded as Pending in REQUIREMENTS.md. This is a correctly-executed, developer-approved halt of an explicit blocking gate — not an oversight, not silent, and not a bug in the executed plans. The interim path (manual `python -m data.gw_capture` per docs/runbooks/gameweek-data-capture.md) is real and functional, confirmed by the actual captured files on disk. But the roadmap's own goal text names 'runs from scripts/daily.sh' as part of what Phase 8 delivers, and that clause is not yet true in the codebase — reporting `passed` would misrepresent that."
    artifacts:
      - path: "scripts/daily.sh"
        issue: "No `data.gw_capture` step exists; file is byte-identical to its pre-Phase-8 state"
    missing:
      - "Re-run 08-05-PLAN.md Task 1 once Phase 7's CUT-01 requirement is marked complete in REQUIREMENTS.md; on `proceed`, Task 2 adds the step (already fully scoped) and its ordering regression test to tests/test_cron.py"
deferred: []
---

# Phase 8: Self-Hosted Gameweek Data Capture Verification Report

**Phase Goal:** Remove vaastav/Fantasy-Premier-League as a single point of failure for training data. A new `data/gw_capture.py` reconstructs vaastav-schema per-GW rows (`gw{N}.csv`, `merged_gw.csv`, refreshed `players_raw.csv`/`fixtures.csv`) directly from the official FPL API into `data/raw/2026-27/`, runs from `scripts/daily.sh`, and backfills the already-finished GWs before season rollover makes them unrecoverable. vaastav is demoted to past-season backfill; `build_table`/`id_map` consume the captured rows unchanged.

**Verified:** 2026-09-12T09:15:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `data/gw_capture.py` captures a finished gameweek from the official FPL API into vaastav's 46-column `merged_gw.csv` schema, read back unchanged by `data/build_table.py`'s loader | ✓ VERIFIED | Module exists (26,982 bytes); `tests/test_gw_capture.py::test_end_to_end_capture_reads_back_through_build_table` passes; direct read of the real `data/raw/2026-27/merged_gw.csv` confirms 46 columns, `missing_source_keys=[]` against `config.MERGED_GW_COLUMNS` |
| 2 | Club-full-name, first+second-name, GK/DEF/MID/FWD position, finished-AND-data-checked completion gate, flat-path layout, and write-atomicity conventions are each locked by a dedicated test | ✓ VERIFIED | `tests/test_gw_capture.py` — 40 tests, all pass (verified directly: `40 passed in 1.82s`) |
| 3 | `players_raw.csv`/`fixtures.csv` are refreshed unconditionally on every run (never skip-if-exists) | ✓ VERIFIED | `write_players_raw`/`write_fixtures` called unconditionally in `capture()`; real files carry mtime `2026-09-12` (was `2026-08-21` pre-phase per 08-BACKFILL-EVIDENCE.md); tests assert a second run changes on-disk content with no flag |
| 4 | A payload field vanishing upstream stops the run and alerts, naming the field, instead of silently producing an all-NaN column | ✓ VERIFIED | `_require_fields()` present in `data/gw_capture.py`, applied to bootstrap elements, teams, and history rows; tests D2 (08-02-SUMMARY) cover the raise + single alert record |
| 5 | `xP` is resolved from a real daily snapshot taken while the target gameweek was upcoming, or left missing — never backfilled, interpolated, or carried across gameweeks | ✓ VERIFIED | `resolve_xp_for_gw()` implements the exact 3-branch rule; real run: GW1/GW2 = 0.0% (documented permanent gap, deadlines precede earliest snapshot), GW3 = 95.7% resolved from the correct `ep_next` column of the 2026-08-31 snapshot — matches 08-BACKFILL-EVIDENCE.md exactly, confirmed by direct read of `merged_gw.csv` |
| 6 | Re-running with nothing new finished issues zero `element-summary` requests | ✓ VERIFIED | `captured_gws()`/ledger-presence check in `capture()`; test `test_rerun_with_full_ledger_issues_zero_element_summary_requests` passes |
| 7 | A finished, data-checked gameweek left uncaptured alerts through `ops.notify` and exits non-zero | ✓ VERIFIED (default path) — see WARNING below | `check_freshness()` runs at end of every plain/`--force` run; tests cover the alert-and-nonzero-exit and the fully-captured/zero-exit cases. **However**, 08-REVIEW.md's CR-01 (critical, unfixed, code-reviewed and committed as advisory) shows the explicit `--gw N` path can write a permanent empty ledger for an unplayed gameweek, which then permanently defeats this exact freshness check for that gameweek — confirmed present in the current code (`data/gw_capture.py` lines ~505-535: `gws=` list bypasses `finished_gws` filtering, and `captured_gws()` counts by ledger-file presence only, not row count) |
| 8 | Every finished, data-checked gameweek of the current season is captured on disk, including the two vaastav never published | ✓ VERIFIED | Real run 2026-09-12: GW1 610 rows, GW2 626 rows, GW3 654 rows, zero per-player failures; confirmed by direct file read of `data/raw/2026-27/merged_gw.csv` (`per-gw {1: 610, 2: 626, 3: 654}`) and `data/raw/2026-27/gws/{gw1,gw2,gw3}.csv` all present on disk |
| 9 | The self-built GW1 rows agree with vaastav's published GW1 file, key-for-key and column-for-column, or every disagreement is diagnosed | ✓ VERIFIED | 08-BACKFILL-EVIDENCE.md §3: first run found a real bug (`team` joined from current club, not the historical fixture — 17/610 rows), fixed in code (commit `bbc0e4c`) per the plan's own no-data-edit prohibition, re-captured with `--force`; post-fix comparison shows 0 keys-only-in-published, 0 keys-only-in-ours, 0 disagreeing columns across all 41 shared columns |
| 10 | `build_table`/`id_map` ingest the captured rows into `player_gw.parquet` with zero code changes to either, and zero regression across the ten past seasons | ✓ VERIFIED | Direct spot-check: `git status --porcelain data/build_table.py data/id_map.py` empty; `player_gw.parquet` current-season rows = 1,890, position coverage = 1.0 (both re-read directly, matching 08-BACKFILL-EVIDENCE.md exactly); evidence doc's ten-season regression table shows `{}`  — empty diff against baseline |
| 11 | vaastav is demoted in code: `data/ingest.py`'s `fetch_vaastav_season` declines the current season's three files under any flag including `--force`; a vanished past-season file now warns | ✓ VERIFIED | Direct code read: module docstring states the ownership split; `is_current = season == config.CURRENT_SEASON` guard present; 7 tests in `tests/test_gw_capture.py` cover the zero-request guard (with/without `--force`), byte-identical files, past-season still downloads, and the absent-past-season warning |
| 12 | A written runbook states data provenance, how to run/backfill, vaastav's remaining role, and the known `xP`/odds gaps | ✓ VERIFIED | `docs/runbooks/gameweek-data-capture.md` exists (11,450 bytes, 9 sections in the specified order); numbers quoted in it (GW1/GW2 0% xP, GW3 95.7%) match `08-BACKFILL-EVIDENCE.md` verbatim; flag set matches `python -m data.gw_capture --help` exactly per 08-04-SUMMARY.md |
| 13 | The daily cron runs the capture module every day (goal clause: "runs from `scripts/daily.sh`") | ✗ FAILED | `scripts/daily.sh` has no `data.gw_capture` step — confirmed by direct file read; last commit touching it (`9ded4f3`) is an unrelated Phase 10 commit. Deliberately halted: 08-05 Task 1's blocking-human gate asked whether Phase 7's cron-script freeze had lifted; developer answered `defer` (verbatim, 2026-09-12) because Phase 7 is 3/6 plans complete and CUT-01 is `Pending` in REQUIREMENTS.md. Recorded, not silent — but the codebase does not yet make this truth hold |

**Score:** 12/13 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/gw_capture.py` | Complete capture module | ✓ VERIFIED | Exists, 40 passing tests, exercised against the live API for real (not just mocks) |
| `tests/test_gw_capture.py` | Full behavior/gate coverage | ✓ VERIFIED | 40 tests, all pass |
| `data/raw/2026-27/merged_gw.csv` + `gws/gw{1,2,3}.csv` | Real captured current-season data | ✓ VERIFIED | Present on disk, 1,890 rows / 46 cols, matches evidence doc exactly |
| `.planning/phases/08-.../08-BACKFILL-EVIDENCE.md` | Measured backfill/cross-check/rebuild evidence | ✓ VERIFIED | Present, every number independently spot-checked and matched |
| `data/ingest.py` current-season guard | Demotes vaastav for current season | ✓ VERIFIED | Present, tested, docstring states split |
| `docs/runbooks/gameweek-data-capture.md` | Operator runbook | ✓ VERIFIED | Present, content verified against real CLI and evidence numbers |
| `scripts/daily.sh` capture step | Daily cron wiring | ✗ MISSING | Not present — Wave 5 halted on the Phase 7 freeze (developer `defer`) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `data/gw_capture.py` | `data/build_table.py` | `config.RAW_DIR/{season}/merged_gw.csv` flat path | ✓ WIRED | `_load_merged_gw` reads the file with zero missing columns; `data/build_table.py` is byte-identical to pre-phase (`git diff --quiet`) |
| `data/gw_capture.py` | `data/snapshot.py` | `load_snapshots()` for xP resolution | ✓ WIRED | Real run resolved GW3's xP from the real 2026-08-31 snapshot via `ep_next` |
| `data/gw_capture.py` | `ops/notify.py` | `report()` on schema drift / freshness gap | ✓ WIRED | Tested; zero-failure real run produced no alert (expected — nothing was stalled) |
| `data/ingest.py` | `data/gw_capture.py` | current-season file ownership handoff | ✓ WIRED | `fetch_vaastav_season` guard confirmed by direct code read and tests |
| `scripts/daily.sh` | `data/gw_capture.py` | daily cron step | ✗ NOT_WIRED | No step exists; this is the recorded, deferred Wave 5 gap |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Captured file is real, current, and matches the evidence doc | `python -c "...pd.read_csv('data/raw/2026-27/merged_gw.csv')..."` | `rows 1890 cols 46`, `per-gw {1: 610, 2: 626, 3: 654}`, `missing_source_keys []` | ✓ PASS |
| `data/build_table.py`/`data/id_map.py` untouched | `git status --porcelain data/build_table.py data/id_map.py scripts/weekly.sh` | (empty output) | ✓ PASS |
| Current-season rows genuinely flow into the canonical table | `python -c "...pd.read_parquet(player_gw.parquet)..."` | `current_rows 1890`, `position_cov 1.0` | ✓ PASS |
| `data/ingest.py` states and implements the ownership split | direct code read | docstring + `is_current` guard present | ✓ PASS |
| Runbook content matches real numbers/CLI | direct file read + `--help` cross-reference (per 08-04-SUMMARY.md) | 9 sections, numbers match verbatim | ✓ PASS |
| `tests/test_gw_capture.py` full file | `python -m pytest tests/test_gw_capture.py -q` | `40 passed in 1.82s` | ✓ PASS |
| Full repository suite (single run, not per-truth filtering) | `python -m pytest -q` | `419 passed, 1 skipped, ... in 284.79s`, exit code 0 | ✓ PASS |
| `scripts/daily.sh` contains the capture step | direct file read | Confirmed absent — 5 existing steps only, no `gw_capture` line | ✗ FAIL (expected — this is the recorded gap) |

### Requirements Coverage

No requirement IDs are declared for Phase 8. `.planning/ROADMAP.md`'s Phase 8 entry reads `**Requirements**: TBD`, and all five plans' `requirements:` frontmatter fields are empty (confirmed by reading each PLAN's frontmatter). `.planning/REQUIREMENTS.md` maps no requirement ID to Phase 8 — the only Phase-adjacent ID present (`CUT-01`) is explicitly attributed to Phase 7, not Phase 8, and is correctly still `Pending`. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `data/gw_capture.py` | ~409-535 | CR-01 (08-REVIEW.md, critical): explicit `--gw N` capture of an unfinished gameweek writes a permanent, silent empty ledger, which then permanently defeats `check_freshness()` and the default backfill's re-targeting for that gameweek — confirmed present in the current code | 🛑 Blocker-class defect, but **advisory/committed** per the code review's own disposition and the executor's recorded choice not to auto-fix a review finding outside the plan's scope | Only reachable via the explicit `--gw` flag on an unplayed gameweek — the wired (deferred) cron step and the documented runbook command both use the plain, no-flag form, so the default operating path is unaffected today. Real risk if the flag is ever used ad hoc (e.g. debugging) against a future gameweek |
| `data/team_strength.py` | 105-117 | WR-01 (08-REVIEW.md, warning): current-season exemption from the systemic-reconstruction-failure guard is unconditional for nearly the whole season, so a genuine future reconstruction bug in the current season's own data would also go unflagged | ⚠️ Warning | Reduces a safety net for the in-progress season specifically; past seasons' guard is unaffected (verified by a dedicated regression test) |
| `data/gw_capture.py` | 94-97 | WR-02 (08-REVIEW.md, warning): the `MERGED_GW_HEADER ⊇ config.MERGED_GW_COLUMNS` guarantee is a bare `assert`, stripped under `python -O`/`PYTHONOPTIMIZE` | ⚠️ Warning | Low likelihood in this project's run pattern, but the module's own docstring/runbook claims an unconditional guarantee this implementation doesn't provide under `-O` |
| `data/gw_capture.py` | 168-229 | WR-03 (08-REVIEW.md, warning): `_fetch_bootstrap`/`_fetch_fixtures` near-duplicate retry logic | ℹ️ Info/Warning | Maintainability only, no behavioral risk |
| — | — | No `TBD`/`FIXME`/`XXX` debt markers found in any file this phase modified (`data/gw_capture.py`, `data/ingest.py`, `data/team_strength.py`, `tests/test_gw_capture.py`, `docs/runbooks/gameweek-data-capture.md`) | — | Debt-marker gate: clean |

CR-01/WR-01/WR-02/WR-03 are pre-existing findings from `08-REVIEW.md` (2026-09-12), independently re-confirmed by direct code reading during this verification. They were reviewed and left as documented, committed advisory findings rather than blocking the phase — that disposition is the executor's own recorded choice, not a gap this verification is inventing. They do not change the phase-goal verdict (already `gaps_found` for the cron-wiring reason above) but are surfaced here because CR-01 in particular is a real, unfixed correctness defect in the freshness-alert guarantee the phase's own goal and 08-02's must-haves promise.

### Human Verification Required

None. Every truth above is either directly verifiable in the codebase (and was) or is a plainly-recorded, developer-already-decided gate (08-05's `defer`) that needs no further human judgment to classify — it needs Phase 7's CUT-01 to land, which is out of this phase's control.

### Gaps Summary

Phase 8 delivered four of its five waves in full, and the fifth wave's own Task 1 is *by design* a blocking-human decision gate — it ran exactly as scripted, gathered the required evidence, asked the question, and the developer answered `defer` because Phase 7 (Parity Validation & Cutover) has not yet lifted its freeze on `scripts/daily.sh` (3/6 plans complete, `CUT-01` still `Pending`). That is not an execution failure; `08-05-PLAN.md` explicitly anticipates and instructs this exact halt path.

However, the roadmap's own phase-goal text explicitly includes "runs from `scripts/daily.sh`" as part of what Phase 8 delivers, and that is objectively not yet true in the codebase: `scripts/daily.sh` has no capture step. Reporting `status: passed` would misstate that. The correct, honest status is `gaps_found`, with the single gap fully attributed to an external, already-identified blocker (Phase 7's CUT-01) rather than to any defect in the four completed waves.

**Everything else genuinely works and was independently re-verified against the live filesystem, not just against SUMMARY.md's narrative:** the module, the real captured data (1,890 rows across GW1-3), the cross-check-confirmed schema mapping (after a real bug was found and fixed, not papered over), the canonical-table ingestion with zero consumer-module changes and zero regression across ten past seasons, the vaastav demotion in code, the operator runbook, and a green 419-passed/1-skipped full test suite (re-run fresh during this verification, not taken on faith).

**This looks intentional and already well-documented.** If the developer wants Phase 8 to read as fully resolved pending only an external unblock (rather than as an open gap), the appropriate action is not to force `passed` here but to accept an explicit override once ready:

```yaml
overrides:
  - must_have: "The daily cron runs the capture module every day (runs from scripts/daily.sh)"
    reason: "Wave 5 Task 1 is a blocking-human decision gate; developer chose defer because Phase 7's CUT-01 requirement is still Pending (3/6 plans complete). Interim manual operation via docs/runbooks/gameweek-data-capture.md is the accepted stand-in until Phase 7 completes and 08-05 Task 2 can run."
    accepted_by: "<developer>"
    accepted_at: "<ISO timestamp>"
```

Separately — not blocking, but worth a decision — CR-01 (the `--gw`-of-an-unplayed-gameweek empty-ledger defect) remains unfixed in the committed code. It was reviewed and recorded as advisory in `08-REVIEW.md` rather than fixed. Since the currently-wired usage path (plain, no-flag runs, per the runbook) never triggers it, it does not block this phase's core claim, but it should be tracked so it is not forgotten before the `--gw` flag is ever used operationally.

---

*Verified: 2026-09-12T09:15:00Z*
*Verifier: Claude (gsd-verifier)*
