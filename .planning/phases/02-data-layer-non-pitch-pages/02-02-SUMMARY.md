---
phase: 02-data-layer-non-pitch-pages
plan: 02
subsystem: infra
tags: [npm, package-legitimacy, react-markdown, fontsource, parity-ledger, supply-chain]

# Dependency graph
requires:
  - phase: 01-test-base-layer-app-skeleton
    provides: Human-approved 13-package install precedent (package-legitimacy gate discipline)
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-01's xP table (table header eyebrow chrome, StatusFlag, ErrorState/EmptyState reuse) — deviation entries 1, 2, 7 attribute to it"
provides:
  - "frontend/package.json/package-lock.json with react-markdown@10.1.0, @fontsource/archivo@5.3.0, @fontsource/ibm-plex-sans@5.3.0, @fontsource/ibm-plex-mono@5.3.0 pinned exactly — the single install for the whole phase, so no wave-2 plan collides on package.json"
  - "PARITY-DEVIATIONS.md (D-04) seeded with all eight known deviations plus the append rule governing the rest of the phase"
affects: [02-03, 02-04, 02-05, 02-06, 07]

# Actuals (#2632)
actuals:
  tokens: 16500
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: ["react-markdown@10.1.0", "@fontsource/archivo@5.3.0", "@fontsource/ibm-plex-sans@5.3.0", "@fontsource/ibm-plex-mono@5.3.0"]
  patterns:
    - "Package-legitimacy gate stays blocking-human even under auto_advance — this plan's Task 1 was answered by an explicit human decision routed through the checkpoint, not auto-approved"
    - "Versions re-verified against the live npm registry immediately before install (npm view), matching Phase 1's zero-drift installation discipline"

key-files:
  created:
    - .planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md
  modified:
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Human approved all four packages verbatim: \"Approve all four (Recommended)\" — recorded here and in STATE.md per the Phase 01 precedent."
  - "Ledger entry 7 (table header eyebrow/sub-14px chrome at the 14px Label token) attributed to plan 02-01, since XpTable.tsx's <th> elements already render with the text-label/uppercase/tracking-[0.08em] classes that constitute this deviation — confirmed by reading the shipped component, not assumed."

patterns-established:
  - "PARITY-DEVIATIONS.md's append rule: any further intentional difference from vanilla behaviour discovered mid-phase gets a new numbered row in the same commit as the change, or it counts as an unexplained parity defect at Phase 7's CUT-01 comparison."

requirements-completed: [UI-02, UI-05]

coverage:
  - id: D1
    description: "Package-legitimacy approval gate for the phase's four new npm dependencies was answered by an explicit human decision before any install ran."
    verification:
      - kind: manual_procedural
        ref: "Human checkpoint response: \"Approve all four (Recommended)\" — recorded verbatim below"
        status: pass
    human_judgment: true
    rationale: "This is the gate itself — a human approval decision, not a mechanically verifiable fact. The gate answer is the deliverable."
  - id: D2
    description: "frontend/package.json pins react-markdown@10.1.0, @fontsource/archivo@5.3.0, @fontsource/ibm-plex-sans@5.3.0, @fontsource/ibm-plex-mono@5.3.0 exactly under dependencies, with package-lock.json committed alongside; no unapproved package was added."
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "node --input-type=module -e \"...EXACT PINS OK check...\" (plan Task 2 automated verify)"
        status: pass
      - kind: other
        ref: "git status --short frontend/package.json (post-install diff limited to the four approved packages)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Phase 1 toolchain (Vitest suite, typecheck, build-purity script) still passes after the four installs."
    verification:
      - kind: other
        ref: "npm --prefix frontend run test (58/58 passed)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck (exit 0)"
        status: pass
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh (BUILD PURITY OK)"
        status: pass
    human_judgment: false
  - id: D4
    description: "PARITY-DEVIATIONS.md exists at the D-04 path with all eight seed entries (deviation + reason + introducing plan) and a stated append rule."
    requirement: "UI-02"
    verification:
      - kind: other
        ref: "plan Task 3 automated verify: LEDGER SEEDED (8 numbered rows) + APPEND RULE PRESENT"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-01
status: complete
---

# Phase 2 Plan 2: Package-Legitimacy Gate + Parity Deviation Ledger Summary

**Human-approved install of react-markdown and three self-hosted @fontsource packages at exact pins, plus the seeded PARITY-DEVIATIONS.md ledger (D-04) that Phase 7's cutover comparison will read as the complete list of explained deltas.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-01T14:10:00Z (approx.)
- **Completed:** 2026-09-01T14:35:00Z (approx.)
- **Tasks:** 3 (1 blocking-human checkpoint, 2 auto)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Cleared the package-legitimacy blocking-human checkpoint for this phase's four new npm dependencies — the gate is never auto-approvable, and was answered by an explicit human decision
- Re-verified all four package versions against the live npm registry immediately before install (zero drift from the audited versions)
- Installed `react-markdown@10.1.0`, `@fontsource/archivo@5.3.0`, `@fontsource/ibm-plex-sans@5.3.0`, `@fontsource/ibm-plex-mono@5.3.0` at exact pins under `dependencies`, confirmed no unapproved package was added, and confirmed the Phase 1 toolchain (58/58 Vitest tests, typecheck, build-purity) is unaffected
- Created `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` (D-04) with the eight UI-SPEC seed deviations, per-entry attribution to the plan that introduces each, and the append rule that governs the rest of the phase

## Task Commits

Each task was committed atomically (Task 1 is the checkpoint itself — no code change, no commit):

1. **Task 1: Package-legitimacy approval for this phase's four new npm dependencies** — checkpoint answered, no commit (approval-only gate)
2. **Task 2: Install the approved packages at exact pinned versions** - `029b690` (feat)
3. **Task 3: Create the parity deviation ledger** - `2f19db2` (docs)

## Files Created/Modified
- `frontend/package.json` - Added `react-markdown@10.1.0`, `@fontsource/archivo@5.3.0`, `@fontsource/ibm-plex-sans@5.3.0`, `@fontsource/ibm-plex-mono@5.3.0` to `dependencies`, all exact-pinned
- `frontend/package-lock.json` - Regenerated by the pinned install
- `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` - New: the eight-entry deviation ledger + append rule, per D-04

## Decisions Made
- **Package-legitimacy gate answer, recorded verbatim:** "Approve all four (Recommended)" — approving `react-markdown@10.1.0`, `@fontsource/archivo@5.3.0`, `@fontsource/ibm-plex-sans@5.3.0`, `@fontsource/ibm-plex-mono@5.3.0` as a set. This follows the same discipline STATE.md records for Phase 01's 13-package human-approved install (see STATE.md Decisions, also logged there for this plan).
- Attributed ledger entry 7 (table header eyebrow/sub-14px chrome → 14px Label token) to plan 02-01 after confirming `XpTable.tsx`'s `<th>` elements already render with the `font-label text-label ... uppercase tracking-[0.08em]` classes that constitute the deviation, rather than leaving it as a placeholder "whichever plan first renders that chrome."

## Deviations from Plan

None - plan executed exactly as written. The plan's own Task 2 action anticipated and pre-authorized the version re-verification and unapproved-package-removal checks; neither drift nor an unapproved package occurred, so no removal/deviation was needed.

---

**Total deviations:** 0
**Impact on plan:** None — installs matched the audited versions exactly, and no extraneous top-level dependency was introduced.

## Issues Encountered
None. `npm install` printed one informational warning (`esbuild@0.28.2`'s postinstall script blocked by `allowScripts`) — this is npm's standard third-party-postinstall-script safety behavior on a transitive build dependency already present before this plan, not a new issue introduced by the four packages installed here.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `frontend/package.json` now carries all packages any remaining Phase 2 plan needs — no later plan in this phase should need to touch `package.json`/`package-lock.json` again, avoiding wave-2 merge collisions.
- `PARITY-DEVIATIONS.md` exists and is ready for plans 02-03 (entries 3, 4), 02-04 (entry 5), and 02-05 (entry 8) to consume — and for any plan to append a new row per the stated rule.
- No blockers for the wave-2 plans (02-03 through 02-06).

## Self-Check: PASSED

`frontend/package.json` and `frontend/package-lock.json` verified present on disk with the four exact-pinned dependencies (`node --input-type=module` check reported `EXACT PINS OK`). `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` verified present with 8 numbered rows and the append-rule section. Both task commit hashes (`029b690`, `2f19db2`) verified present via `git log --oneline`. Full frontend suite (58/58), typecheck, and `scripts/verify_frontend_build.sh` (`BUILD PURITY OK`) all re-confirmed green immediately before writing this summary.

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-01*
