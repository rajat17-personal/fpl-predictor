---
gsd_state_version: 1.0
current_phase: 03
current_phase_name: Pitch Renderer & Squad Views
status: executing
stopped_at: Completed 03-01-PLAN.md
last_updated: "2026-09-03T04:26:58.304Z"
last_activity: 2026-09-03
last_activity_desc: Phase 03 execution started
state_head: 4c868a8fdbb55f59201a9b93c72f97e40f3e5cfb
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 18
  completed_plans: 15
  percent: 29
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-02)

**Core value:** The weekly recommendations (xP table, squad, captains, transfers) must keep flowing reliably — every change must leave the pipeline, API, and site at least as correct and more trustworthy than before.
**Current focus:** Phase 03 — Pitch Renderer & Squad Views

## Current Position

Phase: 03 (Pitch Renderer & Squad Views) — EXECUTING
Plan: 2 of 4
Status: Ready to execute
Last activity: 2026-09-03 — Phase 03 execution started

Progress: [███░░░░░░░] 29% (2/7 phases, 14 plans complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 14
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 6 | - | - |
| 02 | 8 | - | - |

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
| Phase 02 P01 | 35min | 3 tasks | 19 files |
| Phase 02 P02 | 25min | 3 tasks | 3 files |
| Phase 02 P03 | 40min | 3 tasks | 15 files |
| Phase 02 P04 | 20min | 2 tasks | 12 files |
| Phase 02 P05 | 25min | 2 tasks | 8 files |
| Phase 02 P06 | 25min | 2 tasks | 6 files |
| Phase 02 P07 | 25min | 3 tasks | 7 files |
| Phase 02-data-layer-non-pitch-pages P08 | 2min | 3 tasks | 4 files |
| Phase 03 P01 | 55min | 3 tasks | 24 files |

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
- [Phase 02]: Preserved vanilla's literal 'undefined' text for a null captains-table ownership value (R18/Pitfall 3) instead of unifying it with the main table's en-dash fallback — Documented parity requirement per D-01/D-04 — not a bug to fix
- [Phase 02]: Added aria-label 'xP table' / 'Captain picks' to the two tables — Disambiguates rows in tests and assistive tech once both tables can render overlapping player names
- [Phase 02]: [Phase 02]: [Plan 02-02]: Human approved this phase's four new npm dependencies (react-markdown@10.1.0, @fontsource/archivo@5.3.0, @fontsource/ibm-plex-sans@5.3.0, @fontsource/ibm-plex-mono@5.3.0) via the blocking-human package-legitimacy gate — verbatim answer: "Approve all four (Recommended)". Installed at exact pins, zero registry drift, Phase 1 toolchain (58/58 tests, typecheck, build purity) confirmed unaffected. — Follows the same package-legitimacy discipline STATE.md records for Phase 01's approved 13-package install set — new dependencies discovered by research still route through a blocking human gate before any install.
- [Phase 02]: [Phase 02]: [Plan 02-02]: Created PARITY-DEVIATIONS.md (D-04) seeded with all eight UI-SPEC-identified deviations, attributed per-entry to the plan that introduces it; ledger entry 7 (table header eyebrow chrome) attributed to 02-01 after confirming XpTable.tsx already renders it, not left as a placeholder. — Phase 7 (CUT-01) treats this ledger as the complete list of explained deltas between vanilla and the React rebuild; entries skipped mid-phase cannot be reconstructed later.
- [Phase 02]: [Phase 02]: [Plan 02-03]: Added a --font-mono token to index.css's @theme block (IBM Plex Mono) since the UI-SPEC's Numeric modifier requires it for the GW banner and it didn't exist yet, even though the three @fontsource packages were already installed in 02-02.
- [Phase 02]: [Phase 02]: [Plan 02-03]: GwBanner takes a minimal { status, data } prop shape (TanStack Query's own status union) instead of the full UseQueryResult<MetaResponse> generic, keeping it trivially unit-testable with plain object literals per state.
- [Phase 02]: [Phase 02]: [Plan 02-03]: Implemented the sub-hour per-second countdown granularity (D-19's discretion item) since the interval-switching logic already needed the conditional to support it.
- [Phase 02]: FdrCell's accessible description is a plain aria-label on a non-interactive span, not StatusFlag's click-toggle button pattern — a literal per-chip button would have populated the fixtures table with interactive elements, contradicting its own not-sortable/no-buttons requirement. — Fixtures/Prices tables must have zero interactive cells to stay parity-correct with vanilla's non-sortable tables; verified by queryAllByRole('button') being empty.
- [Phase 02]: WatchlistRow.prob/proj_tonight marked optional in lib/api.ts after cross-checking models/price.py directly — official-mode rows never carry a prob key, heuristic/model-mode rows never carry proj_tonight. — The stricter tsc -b build-mode typecheck failed against the previous non-optional typing once the heuristic/model watchlist fixtures accurately omitted those keys per real pipeline output.
- [Phase 02]: Widened ScoreboardSummary.mae_fpl/spearman_fpl to number | null in lib/api.ts (was optional-only) to match ScoreboardEntry's nullable typing — The stricter tsc -b build-mode check rejected the plan-required null summary.mae_fpl fixture value against the previous optional-only type
- [Phase 02]: Dropped the plan-authored node:fs-based Vitest test for the Scoreboard.tsx bypass-comment acceptance criterion; verified via direct grep instead — frontend/tsconfig.app.json's src include has no node types (only vite/client), so node:fs/node:path/process fail the build-mode tsc -b check
- [Phase 02]: [Phase 02]: [Plan 02-06]: Exported diffOwnershipCell(ownership) as a standalone function so R41's null-ownership no-en-dash-fallback case (always excluded from the page's own rendered output by the R39 filter) is directly unit-testable.
- [Phase 02]: [Phase 02]: [Plan 02-06]: Styled react-markdown's output via its components prop (tag->token-class map) rather than a CSS-cascade wrapper class, keeping the markdown-to-typography mapping declared once in Methodology.tsx.
- [Phase 02]: [Phase 02]: [Plan 02-07]: Lockstep over divergence for the G-02-1 dark-neutral palette fix -- changed the four dark hexes in both frontend/src/index.css and web/assets/style.css in one commit rather than diverging the React palette (D-01/D-04), since the values were byte-identical before the fix and vanilla stays authoritative until CUT-01. — Diverging would have been the first palette divergence in PARITY-DEVIATIONS.md, forcing Phase 7's side-by-side pass to eyeball-exempt every surface on every page.
- [Phase 02]: [Phase 02]: [Plan 02-08]: Adopted vanilla's mono family and 0.75 venue-tag opacity for the fixture chip but deliberately did not adopt vanilla's smaller chip/venue font sizes, per the plan's gap-coverage audit -- already governed by PARITY-DEVIATIONS.md entry 7 (sub-14px vanilla chrome renders at the 14px Label token); no new ledger entry required since every change in this plan moves the port toward vanilla.
- [Phase 03]: [Phase 3] [Plan 01]: View-only default Squad tab (no lock/exclude/solve controls on the model-squad pitch) — Loaded-team flow (plan 03-04) already fully covers that interaction surface; keeps this plan's scope aligned with its success criteria (03-RESEARCH.md Open Question 1).
- [Phase 03]: [Phase 3] [Plan 01]: splitPitchRows made generic over T extends SquadRow (Rule 3 deviation) — Plain tsc --noEmit missed the narrowing loss (PitchPlayer[] -> SquadRow[] buckets) that the stricter tsc -b build-mode check (npm run build) caught, per bash scripts/verify_frontend_build.sh.
- [Phase 03]: [Phase 3] [Plan 01]: PITCH-01 trademark posture settled — docs/decisions/pitch-kit-sourcing.md committed, footer disclaimer sentence added sitewide, nav/title renamed to My team — Retires the STATE.md blocker for this phase by documented decision, not by capturing FPL CDN URLs (which D-01 makes moot).

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

Last session: 2026-09-03T04:26:58.246Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
