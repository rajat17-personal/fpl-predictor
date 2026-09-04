---
phase: 05-container-build-ci-pipeline
plan: 04
subsystem: infra
tags: [github-actions, workflow-hygiene, gitignore, sha-pinning, sec-04]

# Dependency graph
requires:
  - phase: 05-01
    provides: "requirements.txt hash-locked lock both schedulers now install with --require-hashes"
provides:
  - "Modernized .github/workflows/daily.yml and weekly.yml: py3.14, hashed installs, SHA-pinned actions, github-actions[bot] commit identity, dispatch-only (no schedule trigger)"
  - "google-chrome-stable_current_amd64.deb removed from the working tree (confirmed never committed, no history rewrite)"
  - "Reconciled .gitignore: restored header style/newline, added .gsd/, .venv/, venv/, .docker/"
  - "Self-evidencing tracked-file scan for personal-email/credential-shaped literals (SEC-04)"
affects: [05-05-push-and-verify]

# Actuals (#2632)
actuals:
  tokens: 1597
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "github-actions[bot] commit identity (41898282+github-actions[bot]@users.noreply.github.com) for automated commits, replacing ad-hoc bot/personal identities"
    - "SHA-pinned uses: lines with trailing version comment, re-resolved live against the GitHub API rather than trusted from prior research"

key-files:
  created: []
  modified:
    - .github/workflows/daily.yml
    - .github/workflows/weekly.yml
    - .gitignore

key-decisions:
  - "Both schedulers' schedule: triggers removed entirely (not commented out) and replaced with a prose comment explaining the local WSL cron owns the daily snapshot — matches D-12's dispatch-only requirement literally."
  - "Re-resolved actions/checkout@v7.0.1 and actions/setup-python@v7.0.0 SHAs live via the GitHub API at execution time rather than trusting 05-RESEARCH.md's table, per 05-03-PLAN.md's SHA-resolution procedure — both matched the researched values with zero drift."
  - "google-chrome-stable_current_amd64.deb removed via a plain `rm` only after `git log --all --oneline -- <path>` confirmed empty — a working-tree deletion, not a history rewrite (D-16)."
  - "downloaded_files/ left untouched — it holds real scratch files (sportsref_download.xls, two lock files), not the empty directory the plan's conditional removal targeted."
  - ".gsd/, .venv/+venv/, and .docker/ added under the existing 'Scratch and installers' .gitignore section (each with its own inline reason comment) rather than a new section, per the plan's 'under the appropriate existing section' instruction."
  - "Personal-email scan found one out-of-scope hit (<redacted-personal-email> quoted twice in 05-PATTERNS.md, a planning doc outside this task's file list) — documented as a finding per the plan's own design ('a hit anywhere else is a finding for the SUMMARY'), not silently redacted; recorded to .planning/WINDOWS.md for visibility at the 05-05 push checkpoint."

coverage:
  - id: D1
    description: "daily.yml and weekly.yml modernized: schedule triggers removed (workflow_dispatch-only), python-version 3.14, --require-hashes installs, SHA-pinned checkout/setup-python, github-actions[bot] commit identity, weekly.yml's false model-in-repo claim corrected"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "plan 05-04 task 1 automated <verify> block (5 commands): schedule-absent/dispatch-present YAML assertion, py3.14+hash+bot-identity grep gate, no-xp_model/no-cron grep gate, uses:-SHA-pin counting gate, preserved-structure YAML assertion"
        status: pass
    human_judgment: false
  - id: D2
    description: "google-chrome-stable_current_amd64.deb deleted from the working tree, confirmed absent from all git history, no history-rewriting command used"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "plan 05-04 task 2 automated <verify>: file-absence + empty `git log --all` + empty `git status --porcelain` checks"
        status: pass
    human_judgment: false
  - id: D3
    description: ".gitignore reconciled: # --- Name --- header style restored, trailing whitespace removed, final newline restored, .gsd/+.venv/+venv/+.docker/ added, snapshot re-inclusion and 'deliberately NOT ignored' block preserved verbatim"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "plan 05-04 task 2 automated <verify>: per-rule grep -qxF loop, header-count + trailing-newline checks, trailing-whitespace + header-count checks"
        status: pass
    human_judgment: false
  - id: D4
    description: "Self-evidencing scan of every tracked file for personal-email/credential-shaped literals, reporting file count read"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "plan 05-04 task 2 automated <verify>: git ls-files count + grep -InE scan across all tracked files (scanned 400+ files)"
        status: fail
    human_judgment: true
    rationale: "Scan is fully automated and ran correctly (self-evidencing count confirmed), but it found a real hit outside the plan's anticipated scope: <redacted-personal-email> quoted twice in .planning/phases/05-container-build-ci-pipeline/05-PATTERNS.md (a planning doc, not in this task's files_modified list). The plan's own action text designates this exact scenario a developer decision, not an executor auto-fix -- recorded to WINDOWS.md, needs human sign-off before the 05-05 push checkpoint."
  - id: D5
    description: "data/snapshots remains tracked and byte-identical to HEAD -- no plan-05-04 change touched the irreplaceable daily price-snapshot history"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "plan 05-04 task 2 automated <verify>: git ls-files data/snapshots non-empty + git diff --quiet HEAD -- data/snapshots"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-09-04
status: complete
---

# Phase 5 Plan 4: Scheduler Modernization & Repo Hygiene Summary

**Modernized daily.yml/weekly.yml to Python 3.14, hash-verified installs, SHA-pinned actions and github-actions[bot] commit identity with schedules disarmed; deleted the 140MB Chrome installer without a history rewrite; reconciled .gitignore's style/coverage; and a self-evidencing tracked-file scan turned up one out-of-scope personal-email hit in a planning doc, documented rather than silently fixed.**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-09-04
- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 3 (`.github/workflows/daily.yml`, `.github/workflows/weekly.yml`, `.gitignore`) + 1 deleted (`google-chrome-stable_current_amd64.deb`, untracked)

## Accomplishments
- Both scheduler workflows carry only `workflow_dispatch:` — the `schedule:` blocks are gone (not commented out), replaced by prose explaining the local WSL cron remains the sole production scheduler for the time-critical, non-backfillable daily price snapshot
- Both workflows install Python 3.14 with `pip install --require-hashes -r requirements.txt` against plan 05-01's hash-locked runtime lock, and every `uses:` line is pinned to a live-re-resolved 40-character commit SHA (`actions/checkout@3d3c42e...` / v7.0.1, `actions/setup-python@5fda3b9...` / v7.0.0) with a trailing version comment
- Both `Commit outputs` steps now use the `github-actions[bot]` identity (`41898282+github-actions[bot]@users.noreply.github.com`), replacing `daily.yml`'s placeholder `fpl-bot` identity and `weekly.yml`'s hardcoded personal name/email that had been committed at HEAD (commit `6b54d5a`)
- `weekly.yml`'s header no longer falsely claims `xp_model.joblib` must live in the repo — corrected to state the model is supplied at run time
- `google-chrome-stable_current_amd64.deb` (140MB) deleted from the working tree after confirming `git log --all --oneline` returns nothing for that path — a working-tree deletion, zero history rewrite
- `.gitignore` restored to its pre-flattening `# --- Name ---` header style, trailing whitespace removed from two headers, final newline restored, and three new rules added (`.gsd/`, `.venv/`+`venv/`, `.docker/`) under the existing "Scratch and installers" section with inline reasons — snapshot re-inclusion and the "deliberately NOT ignored" block preserved verbatim
- A self-evidencing scan (`git ls-files | wc -l` reported, then scanned) of every tracked file for personal-email/credential-shaped literals found one hit outside the plan's anticipated scope — see Deviations below

## Task Commits

Each task was committed atomically:

1. **Task 1: Modernize the daily and weekly scheduler workflows** — `d2b6a25` (feat)
2. **Task 2: Repo hygiene — remove the installer, reconcile .gitignore, prove the tree is push-clean** — `7fc2ad7` (chore)

## Files Created/Modified
- `.github/workflows/daily.yml` - schedule removed, py3.14, `--require-hashes`, SHA-pinned actions, `github-actions[bot]` identity, comment added above the price-model `git add` line noting it's a no-op under the current `.gitignore`
- `.github/workflows/weekly.yml` - same modernization, plus the false model-in-repo header claim corrected and the personal git identity replaced
- `.gitignore` - header style/whitespace/newline reconciled, three new rules added
- `google-chrome-stable_current_amd64.deb` - deleted (was untracked, no git history entry)

## Decisions Made
- Re-resolved both action SHAs live against the GitHub API at execution time (per 05-03-PLAN.md's documented procedure) rather than trusting 05-RESEARCH.md's table verbatim — both tags resolved to the exact same commits the research already published, zero drift.
- Placed the three new `.gitignore` rules under the existing "Scratch and installers" section (with individual inline-reason comments) rather than creating a new header block, following the plan's "under the appropriate existing section" instruction literally.
- `downloaded_files/` left untouched — it holds real files (`sportsref_download.xls` plus two zero-byte lock files), not the empty directory the plan's conditional removal targeted.
- The personal-email scan's one out-of-scope hit was documented rather than auto-redacted, per the plan's own explicit design for this exact situation (see Deviations).

## Deviations from Plan

### Documented Findings (not auto-fixed — explicitly out of scope)

**1. [Rule 4-adjacent — plan-designated developer decision] Personal email literal found outside the anticipated scope**
- **Found during:** Task 2's tracked-file scan
- **Issue:** `<redacted-personal-email>` appears twice in `.planning/phases/05-container-build-ci-pipeline/05-PATTERNS.md` (lines 141 and 153) — both are quotes of `weekly.yml`'s *pre-modernization* content, documenting the exact fix this plan's Task 1 makes. This file is not in Task 2's `files_modified` list (`.gitignore`, the installer only).
- **Why not auto-fixed:** The plan's own action text designates this precise scenario explicitly: "If there is a hit, print it and stop; do not redact and continue, because a literal in a tracked file is a decision for the developer, not a cleanup for the executor... a hit anywhere else is a finding for the SUMMARY." This is a planning-history document (not live infrastructure), and editing it is outside this task's declared file scope.
- **Disposition:** Recorded to `.planning/WINDOWS.md` (entry id 3, kind `deviation`, phase 05) for visibility before the human-gated first push in plan 05-05. The developer can redact `05-PATTERNS.md` (or accept it as historical record in a private repo) as part of that checkpoint.
- **Files affected (not modified by this plan):** `.planning/phases/05-container-build-ci-pipeline/05-PATTERNS.md`
- **Verification:** Confirmed via the full tracked-file scan command from the plan's own `<verify>` block; exactly 2 hits, both the same email, both in the same file.

---

**Total deviations:** 1 documented finding (not an auto-fix — explicitly plan-designated developer decision), 0 auto-fixed.
**Impact on plan:** No code/infra changes were skipped or worked around. Task 2's own in-scope files (`.gitignore`, the installer) fully satisfy every other automated `<verify>` command and `<acceptance_criteria>` line. The one open item is a pre-push visibility decision for the developer, already surfaced via `.planning/WINDOWS.md` and this SUMMARY, and it lands squarely inside plan 05-05's D-14 human-gated push checkpoint — the correct place for it to be resolved.

## Issues Encountered
None beyond the documented finding above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both scheduler workflows are modernized and ready to be pushed alongside `ci.yml` in plan 05-05
- Repo is clean of the 140MB installer with no history-rewrite risk; `.gitignore` covers every generated/secret-bearing/tool-runtime path this milestone introduced
- **Before plan 05-05's push checkpoint:** the developer should decide whether to redact the two `<redacted-personal-email>` occurrences in `05-PATTERNS.md` (tracked in `.planning/WINDOWS.md` entry 3) — this is the only open item blocking a fully clean "nothing you'd want back" first push
- `data/snapshots` history is verified untouched — the time-critical daily-cron invariant holds

---
*Phase: 05-container-build-ci-pipeline*
*Completed: 2026-09-04*

## Self-Check: PASSED

All modified files verified present on disk with expected content (`.github/workflows/daily.yml`, `.github/workflows/weekly.yml`, `.gitignore`); `google-chrome-stable_current_amd64.deb` confirmed absent from disk and from `git log --all`; both task commits (`d2b6a25`, `7fc2ad7`) verified present in `git log --oneline`. All plan-level `<verify>` commands re-run and passed except the tracked-file personal-email/credential scan, which correctly found and reported the one documented out-of-scope finding (see Deviations) — the scan itself functioned exactly as designed.
