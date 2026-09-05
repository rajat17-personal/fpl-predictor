---
gsd_state_version: 1.0
current_phase: 6
current_phase_name: Security, Reliability & Observability Hardening
status: planning
stopped_at: Phase 05 complete, ready to plan Phase 6
last_updated: "2026-09-05T09:48:55.028Z"
last_activity: 2026-09-05
last_activity_desc: Phase 05 complete, transitioned to Phase 6
state_head: 3616b7e3f520954e81fc86868a0c459ab5d3cd34
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 32
  completed_plans: 32
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-04)

**Core value:** The weekly recommendations (xP table, squad, captains, transfers) must keep flowing reliably — every change must leave the pipeline, API, and site at least as correct and more trustworthy than before.
**Current focus:** Phase 05 — Container Build & CI Pipeline

## Current Position

Phase: 6 — Security, Reliability & Observability Hardening
Plan: Not started
Status: Ready to plan
Last activity: 2026-09-05 — Phase 05 complete, transitioned to Phase 6

Progress: [██████░░░░] 57% (4/7 phases, 27 plans complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 32
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 6 | - | - |
| 02 | 8 | - | - |
| 03 | 5 | - | - |
| 04 | 8 | - | - |
| 05 | 5 | - | - |

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
| Phase 03 P02 | 62min | 3 tasks | 17 files |
| Phase 03 P03 | 48min | 3 tasks | 9 files |
| Phase 03 P04 | 42min | 3 tasks | 7 files |
| Phase 03 P05 | 7min | 2 tasks | 4 files |
| Phase 04 P01 | 55min | 3 tasks | 28 files |
| Phase 04 P02 | 75min | 3 tasks | 7 files |
| Phase 04 P03 | 20 min | 3 tasks | 24 files |
| Phase 04 P04 | 35 min | 3 tasks | 1 files |
| Phase 04 P05 | 45min | 3 tasks | 3 files |
| Phase 04 P06 | 25min | 2 tasks | 3 files |
| Phase 04 P07 | 12min | 2 tasks | 2 files |
| Phase 04 P08 | 12min | 3 tasks | 7 files |
| Phase 05 P01 | 10min | 3 tasks | 12 files |
| Phase 05 P02 | 5min | 2 tasks | 3 files |
| Phase 05 P04 | 12min | 2 tasks | 3 files |
| Phase 05 P03 | 18min | 3 tasks | 1 files |
| Phase 05 P05 | 153min | 2 tasks | 7 files |

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
- [Phase 03]: [Phase 3 Plan 3]: Single-pitch arrangement for the best-XI/diff layout — one <Pitch> under the verbatim 'Your best XI for GW{n}' heading with diffs/ghost layered onto it, satisfying D-18's single-pitch rule and D-19's copy-preservation rule at once.
- [Phase 03]: [Phase 3 Plan 3]: Corrected rate_response.json's best_move fixture (Havertz(FWD, starting)->Haaland(FWD, not owned)) — the inherited Egan/Gvardiol pairing put the out card on a bench player and the buy target on an already-owned starter, which cannot satisfy the ghost-same-row acceptance criterion.
- [Phase 03]: [Phase 3 Plan 3]: PlanTransfers.tsx uses local useState for the plan request lifecycle rather than TanStack Query's useMutation — no existing precedent for useMutation in this codebase.
- [Phase 03]: [Phase 03]: [Phase 3 Plan 4]: freeTransfersEstimate resolved as null with a fallback-to-1 default -- the only endpoint returning that estimate is /api/rate/{entry}, and D-20 forbids the Squad tab firing a rate-cost fetch just to prefill one input.
- [Phase 03]: [Phase 03]: [Phase 3 Plan 4]: Extracted useSolveController() as an exported hook, tested via renderHook, because jsdom/React suppress a simulated second click on a genuinely-disabled DOM button regardless of DOM-level attribute manipulation -- a real double-click reproduction of the ordering-safety guard was not reliable in this test environment.
- [Phase 03]: [Phase 03]: [Phase 3 Plan 4]: SolveResultsBar's Hold condition checks result.buys.length, not pairMoves()'s own output length -- pairMoves buckets by the sells side and would still produce non-empty pairs (with a '?' buyName) if pairs.length itself were the check. Matches PlanTransfers.tsx's identical week.buys.length > 0 rule.
- [Phase 03]: [Phase 03 Plan 05]: Continuous flex centering (flex-basis: calc((100% - (parts-1)*gap)/parts), parts=max(5,cardCount)) replaces integer CSS-grid start-column placement in PitchRow, closing G-03-1 -- the old scheme was exact only when row cardinality and the 5-column track count shared parity
- [Phase 03]: [Phase 03 Plan 05]: Deferred Task 1's human visual re-check of UAT test 1 to the next verify-work/UAT pass -- HUMAN_VERIFY_MODE is end-of-phase project-wide and no Playwright/screenshot tooling exists yet in this milestone; all 6 automated verify gates passed and the dev server (localhost:5173/team) plus API (localhost:8000) remain live for that check
- [Phase 04]: [Phase 04-01] Task 1 checkpoint:decision (gate=blocking-human) -- manager-field capture policy: scrub-names. entries/6980093/summary.json blanks player_first_name/player_last_name; team name and all numeric season figures (overall points/rank, gw points) captured verbatim. Applied to summary.json only; picks_event2.json/history.json carry no name fields. — tests/test_api.py's adjacent convention is synthetic-identity-only for committed fixtures (a permanent public record); scrub-names keeps a recognisable team name for debuggability while never committing the two genuinely personal free-text name fields.
- [Phase 04]: [Phase 04-01] Rebound predict.live._gw_pool (the single model-inference leaf), not _pool/_gw_pools, so build_pool/build_horizon_pool's real aggregation and horizon-decay math still run over the frozen per-gameweek inputs in fixture mode. — build_pool/build_horizon_pool resolve _gw_pool from predict.live's own module globals at call time, so rebinding only api.main's imported name would not affect them -- both api.main._gw_pool and live._gw_pool must be rebound.
- [Phase 04]: [Phase 04-02] Task 1 checkpoint:decision (gate=blocking-human) -- approve-with-deps for @playwright/test@1.62.1 (registry re-verified, zero drift); Chromium ultimately installed browser-binary-only (no sudo) after root's PATH resolved system Node 18 under sudo, verified via in-process launch that WSL2 already has every required shared library.
- [Phase 04]: [Phase 04-02] Two unplanned package-legitimacy checkpoints beyond Task 1's single-package surface: @types/node@26.4.1 (tsconfig types/process/path support) and typescript@6.0.3 (matching frontend's pin) -- both human-approved individually. Discovered via a concrete near-miss: npx tsc without a local typescript install silently resolves an unrelated deprecated registry package literally named 'tsc', not the real compiler.
- [Phase 04]: [Phase 04-02] Corrected verify-command form for later plans: (cd e2e && npx tsc --noEmit -p tsconfig.json), not npx tsc --noEmit -p e2e/tsconfig.json from repo root -- typescript is installed only in e2e/node_modules, isolated from frontend/ (a sibling, not an ancestor, directory).
- [Phase 04]: [Phase 04-03] Selection rule executed exactly as specified: sort fixtures.json's 20 ticker rows ascending by short; first six = BLANK clubs (ARS, AVL, BHA, BOU, BRE, CHE), first four = DOUBLE clubs (ARS, AVL, BHA, BOU) -- recorded in MANIFEST.md and hardcoded identically in every variant spec.
- [Phase 04]: [Phase 04-03] Playwright's getByText() is case-insensitive substring matching by default and getByLabel() can match repeated identical aria-labels across rows/gameweeks -- specs must scope locators to the specific cell under test and add { exact: true } to short legend labels, not rely on page-wide queries.
- [Phase 04]: [Phase 04] [Phase 4 Plan 04] Captains sub-table's literal 'undefined' ownership fallback (R18) and the top-50 status-flag reveal have no exercisable row in the immutable v1 capture (zero null captain ownership, zero non-'a' status in top 50) -- documented and skipped rather than mutating the frozen fixture. — D-08 forbids editing v1 fixtures in place; a future v2 cut would need to deliberately include such rows to exercise these two vanilla-parity code paths.
- [Phase 04]: [Phase 04] [Phase 4 Plan 04] The full 651-row frozen xp_table.json has zero rows with a null price_m/ownership/xp_capt anywhere -- the plan's suggested position-filter fallback for the null-key sort test cannot surface one, so that assertion is skipped and documented rather than worked around. — Confirmed by scripting an inspection of the entire committed fixture (not just the top 50) before writing any assertion; every other Task 2 requirement (glyphs, both directions, two independent tie groups, text-column sort) is fully covered.
- [Phase 04]: [Phase 04-05] Rule 1 fix: SquadTab.tsx's teamQuery used fetchApi (discards a non-ok response's detail), unlike this file's own postSolve/RateTab's fetchRate/PlanTransfers' postPlan — added fetchTeam() mirroring the established custom-fetch pattern. — The failure-path E2E test's own required assertion ('Couldn't load that team' including the API's detail text) was unsatisfiable against the pre-fix code, which rendered only a bare status code.
- [Phase 04]: [Phase 04-05] The plan's prescribed /api/solve failure-copy trigger (a lock naming a nonexistent player) cannot be reached through the real UI (locks/excludes are numeric-only, D-15) — resolved by wrapping window.fetch in-page to inject one bogus string lock into the outgoing request body, a real round trip to the real server, not a Playwright route mock. — Keeps D-15's numeric-only client invariant fully intact while still proving the server's real _resolve() player-not-found error path end to end.
- [Phase 04]: [Phase 04] [Phase 04-06] Ghost card and outgoing label land in different pitch rows when the rating's best_move sells a benched (not starting) player -- Pitch.tsx keys the ghost's row off the buy's position only, never the sell target's actual row; discovered against the real immutable v1 fixture, logged to deferred-items.md and WINDOWS.md rather than fixed (out of this plan's file scope) or worked around by mutating the frozen fixture (D-08).
- [Phase 04]: [Phase 04-07] Restored all three fixture-mode bindings (api.main._gw_pool, predict.live._gw_pool, api.main._load_live) in an explicit else-branch rather than relying on api.main's own re-import to self-correct, since that re-import reads predict.live's already-polluted module global on a second reload -- closes CR-01.
- [Phase 04]: [Phase 04-07] Test's captured original _gw_pool reference is discriminated by __module__ ('predict.live' vs 'api.main'), not compared against live._gw_pool_production, so the regression proof stays independent of the attribute the production fix itself writes.
- [Phase 04]: Kept BENCH out of VALID_PITCH_ROWS; reachable only via the resolved sell row's starting field, never an API-supplied position string. — T-04-08-01 mitigation: an attacker-controlled position string can never produce a BENCH ghost.
- [Phase 04]: Re-pinned rate-my-team.spec.ts's Forwards/Bench row counts (2/5) from a real Playwright run, per D-15, rather than trusting the plan's derived arithmetic outright. — The live run confirmed the derived numbers were correct.
- [Phase 05]: [Phase 05]: [Phase 05-01]: Human approved installing both [SUS]-verdict tools (uv==0.12.9, ruff==0.16.6) via the Task 1 blocking-human package-legitimacy checkpoint — verbatim answer: approve-both. Both pins re-verified against the live PyPI registry immediately before install with zero drift; uv is dev-only per D-01 and never enters either .in file.
- [Phase 05]: [Phase 05]: [Phase 05-01]: -c requirements.txt alongside --generate-hashes worked without needing the plan's documented same-session-resolution fallback — shared-pin parity (pandas==3.0.5 identical in both locks) confirmed on the first attempt.
- [Phase 05]: No compiler added to Docker builder stage — plan 05-01 confirmed a clean-wheel install with zero source compilation across the whole lock, so D-03's from-source fallback stays dormant
- [Phase 05]: Kept PuLP's bundled PULP_CBC_CMD rather than switching to pulp[cbc]/COIN_CMD; only apt-get install libstdc++6 was needed in the runtime stage
- [Phase 05]: [Phase 05-04] Personal-email scan found <redacted-personal-email> quoted twice in 05-PATTERNS.md (planning doc, out of task scope) -- documented as a finding per the plan's own design, not auto-redacted; recorded to WINDOWS.md for the 05-05 push checkpoint. — Plan explicitly designates a hit outside weekly.yml as a developer decision, not an executor cleanup.
- [Phase 05]: [Phase 05-04] github-actions[bot] identity (41898282+github-actions[bot]@users.noreply.github.com) adopted for both daily.yml and weekly.yml commit-outputs steps, replacing fpl-bot placeholder and a hardcoded personal identity baked into HEAD by commit 6b54d5a. — D-11 modernization requirement.
- [Phase 05]: [Phase 05-03] Re-resolved all 12 distinct actions (26 uses: lines) live against the GitHub API at execution time; every SHA matched 05-RESEARCH.md's published table exactly, zero drift. — Plan mandates re-resolving every SHA, not trusting prior research, since a tag can be repointed between research and execution.
- [Phase 05]: [Phase 05-03] Built ci.yml in three additive stages (lint-build+test, then +e2e, then +image+publish) with a commit after each task's own <verify> block passed, rather than one commit for the whole 257-line file. — Preserves per-task atomic-commit discipline even though all three tasks share the same single files_modified entry.
- [Phase 05]: [Phase 05] [Phase 05-05] Redacted (not waived) the personal email found in 05-PATTERNS.md before the first push, per developer decision -- closed WINDOWS.md entry 3.
- [Phase 05]: [Phase 05] [Phase 05-05] First real CI push surfaced two genuine environment bugs invisible to local preflight: bare pytest omitting CWD from sys.path (fixed via python -m pytest, 11cd68e) and missing libgomp1 in the runtime image for LightGBM's dlopen (fixed 65cd2e7) -- third PR run and the main-branch run (incl. publish) both went green.

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- **Time-critical, independent of this milestone:** the daily snapshot cron must run every day — price-model history cannot be backfilled (first snapshot 2026-08-31; model unlocks at 14 days). Phase 6 cron changes must not interrupt it.
- **Phase 5 unknown:** Python 3.14 (`cp314`) wheel availability for LightGBM, scikit-learn, PyArrow, PuLP is in flux. Verify on PyPI before finalizing the lockfile.
- **Milestone invariant:** the vanilla site stays live and authoritative until CUT-01 completes.
- Payment gateway / merchant-of-record choice still pending with the user — out of scope here, but PITCH-01's trademark disclaimer feeds the eventual gateway review.
- **[Phase 4 → Phase 5]:** pytest's SPA-fallback test (`tests/test_fixture_mode.py`) requires a built `frontend/dist/` (gitignored, never built by the pytest path) — CI must build the frontend before the backend suite or the test 500s (04-REVIEW.md critical finding). Also: bare `open()` calls in `api/main.py` fixture reads and `e2e/scripts/capture_fixtures.py` (04-REVIEW.md warning; folds into the Phase 6 file-handle-leak work).
- **[Phase 4]:** Security enforcement is on but no 04-SECURITY.md exists — run `/gsd-secure-phase 4` before advancing past Phase 5 planning.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-05T07:08:57.926Z
Stopped at: Phase 05 complete, ready to plan Phase 6
Resume file: None
