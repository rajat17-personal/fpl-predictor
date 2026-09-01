---
gsd_state_version: 1.0
current_phase: 2
current_phase_name: Data Layer & Non-Pitch Pages
status: planning
stopped_at: Phase 2 context gathered
last_updated: "2026-09-01T12:01:42.120Z"
last_activity: 2026-09-01
last_activity_desc: Phase 01 complete, transitioned to Phase 2
state_head: cffa2bd4982f580e4ae3eec187c7dc2bad7b57cf
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 6
  completed_plans: 6
  percent: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-01)

**Core value:** The weekly recommendations (xP table, squad, captains, transfers) must keep flowing reliably — every change must leave the pipeline, API, and site at least as correct and more trustworthy than before.
**Current focus:** Phase 2 — Data Layer & Non-Pitch Pages

## Current Position

Phase: 2 — Data Layer & Non-Pitch Pages
Plan: Not started
Status: Ready to plan
Last activity: 2026-09-01 — Phase 01 complete, transitioned to Phase 2

Progress: [█░░░░░░░░░] 14% (1/7 phases, 6 plans complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 6
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 6 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 6min | 2 tasks | 77 files |
| Phase 01 P02 | 14min | 2 tasks | 3 files |
| Phase 01 P04 | 21min | 3 tasks | 20 files |
| Phase 01 P03 | 12min | 3 tasks | 2 files |
| Phase 01-test-base-layer-app-skeleton P05 | 17min | 3 tasks | 19 files |
| Phase 01 P06 | 13min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: React (Vite) rebuild, full 8-page parity, not incremental vanilla enhancement
- Roadmap: API tests come before Playwright — E2E on an untested API inverts the pyramid
- Roadmap: CI ends at a published Docker image, not a live deploy (hosting not purchased)
- Roadmap: Cutover (CUT-01) is its own phase, gated on a full real gameweek cycle
- [Phase 01]: Human approved full 13-package [SUS] install set for Phase 1 (react-router@7, @tanstack/react-query@5, vite@7.3.6, @vitejs/plugin-react@5.2.0, lucide-react, typescript-eslint, eslint-plugin-react-refresh, @types/node, vitest, @testing-library/react, @testing-library/jest-dom, responses[PyPI]) plus clean-verdict packages and two deliberate downgrade pins (typescript@6.0.3, vite@7.3.6+plugin-react@5.2.0) — Verbatim answer: Approved. Delivered via blocking-human gate, unblocks installs in plans 01-03/01-04.
- [Phase 01]: Task 2 tdd=true task writes contract tests against an already-correct, unmodified production endpoint (test-only file list) — RED phase does not apply; all 17 new tests passed on first run as characterization tests, documented in SUMMARY TDD Gate Compliance section.
- [Phase 01]: [Phase 01 Plan 04]: All frontend installs pinned --save-exact to plan 01-01's approved package-legitimacy list; re-verified against the live npm registry immediately before each install with zero drift (typescript@6.0.3, vite@7.3.6, @vitejs/plugin-react@5.2.0, react-router@7.18.3, @tanstack/react-query@5.102.8, lucide-react@1.38.0, tailwindcss@4.3.3, @tailwindcss/vite@4.3.3, @types/node@26.4.0, vitest@4.1.11, jsdom@30.0.1, @testing-library/react@16.3.3, @testing-library/jest-dom@7.0.1).
- [Phase 01]: [Phase 01 Plan 04]: Removed oxlint (create-vite@9.2.0's new default devDependency, not on the approved package list) before the first npm install, since this plan has no linting task in scope.
- [Phase 01]: [Phase 01 Plan 03]: Task 1's plan-authored <verify> command called responses.__version__, which does not exist on installed responses==0.26.3 (within the approved >=0.25,<0.27 pin). Verified the same fact -- pin installed and recorded -- via importlib.metadata.version('responses') instead; documented as a Rule 3 deviation in the plan's verify command, not the implementation.
- [Phase 01-test-base-layer-app-skeleton]: Split router.tsx's errorElement wiring into a plain ErrorState (no router hooks) plus a separate RouteErrorBoundary that calls useRouteError, so ErrorState stays safe to unit-test outside a data-router context. — useRouteError() throws outside a data-router context, so folding it into the presentational component would have broken direct unit tests of ErrorState.
- [Phase 01-test-base-layer-app-skeleton]: NAV_LINKS order follows the UI-SPEC Routes table (not vanilla web/index.html's nav order); label text still reuses the vanilla nav's copy for parity. — The plan's Task 1 action and acceptance criteria explicitly specify UI-SPEC Routes-table order for both router registration and NAV_LINKS.
- [Phase 01]: [Phase 01-test-base-layer-app-skeleton]: [Plan 01-06]: Moved the 16px horizontal gutter (px-4), not just the 68rem width cap, onto the contained inner wrapper for both header and footer -- keeping it on the outer element (a literal reading of gap G-01-3's missing-item text) would have left chrome content 16px wider per side than main's content, replacing the stranded-nav bug with a new misalignment. — Vanilla's .wrap owns both the 68rem cap and the 16px gutter, and header.site/footer.site nest inside it -- so this restores true vanilla parity rather than a literal-but-broken reading of the gap's missing-item wording. Documented in the plan's gap_coverage_audit as a deliberate, in-scope extension of the same single concern (chrome containment geometry), not scope creep.

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- **Time-critical, independent of this milestone:** the daily snapshot cron must run every day — price-model history cannot be backfilled (first snapshot 2026-08-31; model unlocks at 14 days). Phase 6 cron changes must not interrupt it.
- **Phase 3 unknown:** FPL shirt/kit CDN URL patterns are unverified community knowledge. Must be captured from live devtools before building the shirt component; trademark posture must be documented, not deferred.
- **Phase 5 unknown:** Python 3.14 (`cp314`) wheel availability for LightGBM, scikit-learn, PyArrow, PuLP is in flux. Verify on PyPI before finalizing the lockfile.
- **Milestone invariant:** the vanilla site stays live and authoritative until CUT-01 completes.
- Payment gateway / merchant-of-record choice still pending with the user — out of scope here, but PITCH-01's trademark disclaimer feeds the eventual gateway review.
- **[Phase 01 → Phase 4]:** G-01-3 pixel-geometry assertion deferred to E2E-01 — at a 1720px viewport, assert the header's inner wrapper is ≤1088px, centered, and shares `<main>`'s content x-range (see `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md`). Human-verified visually in Phase 01 UAT (2026-09-01).

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-01T12:01:42.088Z
Stopped at: Phase 2 context gathered
Resume file: .planning/phases/02-data-layer-non-pitch-pages/02-CONTEXT.md
