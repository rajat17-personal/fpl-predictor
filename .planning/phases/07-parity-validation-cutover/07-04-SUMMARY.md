---
phase: 07-parity-validation-cutover
plan: 04
subsystem: testing
tags: [parity, cron-evidence, playwright, cutover-cycle]

# Dependency graph
requires:
  - phase: 07-parity-validation-cutover/07-03
    provides: "PARITY-REPORT.md's pre-deadline stage fully closed (8/8 pages, manual eyeball, D-08 solver comparison), with 5 defects closed and 0 remaining unexplained deltas"
provides:
  - "PARITY-REPORT.md's mid-gameweek stage closed: 8/8 scripted page rows (34 fields, 11 explained, 0 defects), the D-16 cron-green citation, and the observation that ledger entry 4 (deadline-passed banner copy) is genuinely exercised for the first time this stage"
  - "A committed live web/data snapshot (chore(07-04)) establishing the mid-gameweek in-flight data state (GW4, deadline passed, scoreboard.json holds only a GW3 entry) as a traceable artifact"
  - "A recorded, unfixed observation that the local WSL crontab is missing the documented weekly.sh line -- flagged for the user, not auto-installed (cron lines are read-only for this phase)"
affects: [07-05, 07-06]

# Actuals (#2632)
actuals:
  tokens: 9500
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Baseline snapshot commit (chore) landing the live web/data working-tree state immediately before a parity pass, so the pass's own git-diff-quiet acceptance check has a clean tree to assert against without editing pipeline files themselves -- same pattern 07-03 established (ac489ca)"

key-files:
  created: []
  modified:
    - .planning/phases/07-parity-validation-cutover/PARITY-REPORT.md
    - web/data/captains.json
    - web/data/meta.json
    - web/data/squad.json
    - web/data/watchlist.json
    - web/data/xp_table.json
    - web/data/history/gw4.json
    - web/data/scoreboard.json

key-decisions:
  - "Committed the live web/data snapshot as a separate baseline chore commit before running the diff, rather than letting the pre-existing cron-produced modifications sit uncommitted -- otherwise the task's own `git diff --quiet -- scripts/daily.sh scripts/weekly.sh web/data` acceptance check would fail on dirt the task itself did not create. Mirrors 07-03's `ac489ca` precedent exactly."
  - "Recorded (did not fix) that the local crontab is missing the documented `0 8 * * fri weekly.sh` line -- the phase's own threat model marks cron lines read-only for the whole of Phase 7 (T-07-04-05), and GW4's own weekly export already landed pre-deadline via a manual run, so no cycle evidence is missing; the gap is flagged for the user to close before GW5's Friday export is due."
  - "Deferred the `<verify>` block's manual eyeball pass (PARITY-CHECKLIST.md Part 1) to end-of-phase UAT per `workflow.human_verify_mode=end-of-phase`, rather than halting for a checkpoint -- this is an automated-task human-check, not a `type=\"checkpoint:*\"` gate, so per the standard checkpoint protocol it is harvested into the end-of-phase pass. D-08's interactive solver comparison was not re-required this stage (PARITY-CHECKLIST.md Part 2 is a once-per-cycle check, already completed and recorded in the pre-deadline stage)."
  - "Left `CUT-01` unmarked in REQUIREMENTS.md -- it is a single phase-wide, multi-stage requirement (07-03's Deviation #4 already established this); it is only complete once 07-06's cutover gate finishes."

patterns-established: []

requirements-completed: []  # CUT-01 is phase-wide and multi-stage (07-03's precedent); do not mark complete until 07-06 (the cutover gate) finishes.

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "PARITY-REPORT.md's mid-gameweek stage table filled with 8 page rows against GW4 (same validation gameweek as the pre-deadline run header), 0 defects, and a D-16 cron-green citation covering every row"
    requirement: "CUT-01"
    verification:
      - kind: other
        ref: "node e2e/parity/parity-diff.mjs --all --stage mid-gameweek --vanilla-origin http://127.0.0.1:8010 --react-origin http://127.0.0.1:8011 -> TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects, exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Re-verification pass (Task 2): full 8-page scripted diff re-run clean, frontend build/test green, e2e suite green -- confirms zero defects needed closing and no code changed"
    requirement: "CUT-01"
    verification:
      - kind: other
        ref: "node e2e/parity/parity-diff.mjs --all (post-Task-1 re-run) -> TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects, exit 0"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run build && npm --prefix frontend test -> 374/374 passed"
        status: pass
      - kind: e2e
        ref: "npm --prefix e2e run test -> 42/42 passed (one earlier full-suite run flaked on shell-geometry.spec.ts's D-07 overflow check; reproduced clean both in isolation and on immediate full-suite re-run, so treated as environmental flake, not a regression -- no frontend code was touched by this plan)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Manual eyeball pass (PARITY-CHECKLIST.md Part 1) for the mid-gameweek stage"
    requirement: "CUT-01"
    verification: []
    human_judgment: true
    rationale: "workflow.human_verify_mode=end-of-phase defers this automated-task <human-check> to the end-of-phase UAT pass rather than a mid-flight checkpoint; the task's own acceptance criteria govern only the scripted eight-page table, which is fully closed above."

duration: 18min
completed: 2026-09-12
status: complete
---

# Phase 7 Plan 04: Mid-Gameweek Parity Pass Summary

**Ran the second of three D-07 cycle stages against live GW4 (deadline passed, scoreboard not yet run): 8/8 pages clean at 34 fields/11 explained/0 defects, the deadline-passed banner (ledger #4) genuinely exercised for the first time, and a D-16 cron-green citation recording two clean daily cron runs plus a flagged-but-unfixed missing weekly cron line.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-09-12T13:09:57Z (session start, per STATE.md's prior `last_updated`)
- **Completed:** 2026-09-12T13:22:11Z
- **Tasks:** 2
- **Files modified:** 8 (1 report + 7 web/data export files)

## Accomplishments

- Confirmed the mid-gameweek precondition live before recording anything: GW4 (matching the pre-deadline run header), `deadline_utc` now in the past, `web/data/scoreboard.json` present but holding only a GW3 entry — the gameweek is in flight, not finished.
- Committed the live `web/data` working-tree state as a baseline snapshot (`0756b34`) so the task's own pipeline-untouched acceptance check had a clean tree to assert against, before touching anything else.
- Booted `dual_site.sh` on override ports 8010/8011 (port 8000 held by an unrelated pre-existing `uvicorn`), ran the full eight-page scripted diff with `--stage mid-gameweek`, then stopped both servers — `TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects`, exit 0.
- Recorded the mid-gameweek run header, the filled stage table, and the D-16 cron-green citation in `PARITY-REPORT.md`: `data/cron.log`'s two clean `[daily]` runs since the pre-deadline pass, `data/alerts.jsonl`'s continued absence, and the `web/data` git history since `ac489ca`.
- Called out explicitly that this stage is the first to genuinely exercise `PARITY-DEVIATIONS.md` ledger entry 4 (the deadline-passed banner copy) — even though `extract.mjs`'s `deltaDetailCell()` only cites the first declared ledger number (`#3`) per field, both `#3` and `#4` are declared on the banner field's `knownDeviations` list, so nothing is unlisted.
- Found and recorded (without fixing — cron lines are read-only for the whole phase) that the local WSL crontab is currently missing the documented `0 8 * * fri weekly.sh` line; GW4's own weekly export already landed pre-deadline via a manual run, so this cycle's evidence chain is unaffected, but the gap is flagged for the user before GW5's Friday export comes due.
- Re-ran the full eight-page diff, the frontend build/test suite, and the e2e Playwright suite in Task 2 to confirm the zero-defect finding held and nothing needed closing — all green, zero React code changed, zero new ledger rows needed.

## Task Commits

1. **Baseline: Land mid-gameweek GW4 weekly export snapshot** - `0756b34` (chore)
2. **Task 1: Mid-gameweek scripted pass across all eight pages** - `0e77936` (feat)
3. **Task 2: Close every mid-gameweek defect (0 found) and re-verify** - `a5efd7d` (docs)

**Plan metadata:** this SUMMARY's own commit (below)

## Files Created/Modified

- `.planning/phases/07-parity-validation-cutover/PARITY-REPORT.md` - Filled the mid-gameweek run header, stage table, cron-green citation, ledger-#4-exercised note, crontab-gap observation, and updated "Cutover readiness" totals
- `web/data/captains.json`, `web/data/meta.json`, `web/data/squad.json`, `web/data/watchlist.json`, `web/data/xp_table.json`, `web/data/history/gw4.json`, `web/data/scoreboard.json` - Live pipeline output, committed as a baseline snapshot (no logic change — these are cron/manual-export artifacts landed to keep the working tree clean for the pipeline-untouched check)

## Decisions Made

- Committed the current live `web/data` state as a standalone baseline `chore` commit before running the diff, mirroring 07-03's `ac489ca` precedent exactly — otherwise this task's own `git diff --quiet -- scripts/daily.sh scripts/weekly.sh web/data` acceptance check would have failed on pre-existing cron output the task did not create.
- Recorded, rather than fixed, the missing weekly cron line in the local crontab. The phase's own threat model (T-07-04-05) makes `scripts/daily.sh`, `scripts/weekly.sh`, and their cron lines read-only for the whole of Phase 7 — installing a crontab line would violate that even in service of a "fix". GW4's weekly export already landed pre-deadline by a manual `predict.export` run, so no evidence gap exists for this cycle; the finding is purely forward-looking (GW5's Friday export).
- Deferred the `<human-check>` eyeball pass to end-of-phase UAT per `workflow.human_verify_mode=end-of-phase`, since it is an automated-task human-check, not a `type="checkpoint:*"` gate. D-08's interactive solver comparison was not re-required at this stage (checked once per cycle, already recorded pre-deadline).
- Left `CUT-01` unmarked in `REQUIREMENTS.md`, per 07-03's established precedent — it is phase-wide and multi-stage, closing only at 07-06's cutover gate.

## Deviations from Plan

None - plan executed exactly as written. (The one non-trivial judgment call — citing ledger #4 explicitly in prose since the tool's own delta-detail cell only shows `#3` — is a reporting clarification, not a deviation from any instruction; the plan's own action text asked for exactly this attention.)

## Issues Encountered

- One full `npm --prefix e2e run test` run reported 1 failed spec (`shell-geometry.spec.ts`'s "team page has no horizontal overflow at 390px (D-07)"). Re-running the same spec in isolation passed immediately, and a second full-suite run passed 42/42 with no changes made in between — treated as an environmental flake (likely resource contention from the concurrent multi-webServer Playwright config), not a regression, since this plan touched zero frontend source files.
- Local e2e runs require `E2E_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python` (the base `python` on `PATH` lacks `uvicorn`) — matches `e2e/playwright.config.ts`'s own documented local-run instruction, not a new finding.

## User Setup Required

- **Reinstall the weekly cron line before GW5's Friday export is due.** `crontab -l` on this host currently lists only `30 2 * * * .../daily.sh` and `@reboot .../snapshot_catchup.sh`. The `0 8 * * fri /home/sraja/fpl/scripts/weekly.sh >> /home/sraja/fpl/data/cron.log 2>&1` line documented in `06-USER-SETUP.md`/`06-05-SUMMARY.md` is missing. Not blocking this phase (GW4's weekly export already landed manually), but needed before the next gameweek's automated Friday export.

## Next Phase Readiness

- Mid-gameweek stage of the D-07 three-pass cycle is fully closed: 8/8 scripted pages clean, cron-green citation recorded, ledger #4 confirmed exercised, no carry-forward from pre-deadline needed.
- Post-finish stage (07-05, per the roadmap) remains — it needs GW4's scoreboard to actually run (`predict.scoreboard` scoring GW4, which `data/cron.log` shows has not happened yet: `scored GWs none` as of 2026-09-12). That plan is calendar-gated exactly like this one was.
- No blockers for 07-05 beyond the calendar: once GW4 finishes and the scoreboard scores it, the same `dual_site.sh` + `parity-diff.mjs --stage post-finish` sequence applies.
- The crontab weekly-line gap is a real but non-blocking finding for the user to address before GW5.

---
*Phase: 07-parity-validation-cutover*
*Completed: 2026-09-12*
