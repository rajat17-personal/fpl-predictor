# Phase 4: E2E Regression Suite - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Protect the critical user flows of the rebuilt React site with a deterministic Playwright browser suite: team/pitch + solver flow (E2E-02), xP table + captains with exact cell values and sort order (E2E-03), rate-my-team end to end (E2E-04), and the fixtures & prices pages (E2E-05) — all backed by frozen versioned JSON snapshots (normal, blank GW, double GW) plus a mocked FPL API (E2E-01), so the suite behaves identically on deadline day and mid-week with zero live-data dependence. Tests pass or fail on code, never on the calendar.

This phase also discharges the Phase 1 handoff: the G-01-3 pixel-geometry assertion (1720px viewport header containment) that jsdom could not prove.

Out of this phase: wiring the suite into GitHub Actions (Phase 5, CI-02), and any new app features — the suite tests what Phases 1–3 shipped.

</domain>

<decisions>
## Implementation Decisions

### System-under-test topology
- **D-01:** **One real full-stack process, fixture-fed.** Playwright runs against uvicorn serving the real FastAPI app; a new **env-var fixture seam in `api/main.py`** (e.g. `FPL_FIXTURE_DIR`) makes the API load frozen FPL-upstream payloads from disk instead of calling `fantasy.premierleague.com`. The real FastAPI code paths, caching, and ILP solver run end to end — E2E genuinely covers the wire between React and FastAPI. Playwright `route()` mocks of `/api/*` were explicitly rejected (they'd leave the React↔API contract browser-untested). — **Reversibility:** costly — Phase 5's CI-02 job ("Playwright against uvicorn serving the built frontend with fixture data") is built on this seam; switching to browser-layer mocks later restructures both the suite and the CI job.
- **D-02:** **The same seam switches the static mount:** in fixture/E2E mode uvicorn serves `frontend/dist` instead of the vanilla `web/` directory. Production default stays `web/` (milestone invariant: vanilla is live until CUT-01); Phase 7's cutover flips this same switch. A separate test-only ASGI app was rejected (drift risk).
- **D-03:** **Local runs are CI-identical, always.** `npm run build` → uvicorn serves `dist/` + fixture data. No dev-server variant, no `E2E_DEV` flag — one topology, zero "works locally, fails in CI" drift.
- **D-04:** **Open auth mode** (`FPL_API_KEYS` unset) — matches today's production posture; the three-mode auth behavior is already covered by Phase 1's APIT-02 tests. No keyed-mode E2E.
- **D-05:** **Playwright's `webServer` config owns the server lifecycle** (build + uvicorn command, port/health readiness, reuse locally, strict in CI). `npx playwright test` is the single entry point; no shell-script orchestration.

### Fixture provenance & GW scenarios (E2E-01)
- **D-06:** **Real capture + synthesized variants.** Freeze one real week's `web/data/*.json` export as the "normal" set — real player names and realistic magnitudes for humans debugging failures. Derive the **blank** and **double-GW** sets from it by scripted transformation (no real blank/DGW export exists yet this season). Committed once; never auto-refreshed.
- **D-07:** **Coherent same-week API-side capture.** The fixture-mode API's FPL-upstream payloads (bootstrap-static, fixtures, entry **6980093** picks) are captured in the same freeze as the `web/data` snapshot, so `/api` and `/data` describe the same gameweek universe — solve results and page data stay mutually consistent. Trim payloads to the fields the API actually reads.
- **D-08:** **Versioned as immutable dirs + manifest:** `e2e/fixtures/v1/{normal,blank,dgw}/` (exact layout is planner's) with a `MANIFEST.md` recording capture date, GW, source, and the synthesis rules for the variants. A contract change cuts `v2` alongside `v1`; **v1 is never edited in place** — this is what keeps the hardcoded goldens (D-15) from rotting. — **Reversibility:** costly — D-15's literal assertions and the pinned solver golden (D-11) all reference v1 values; mutating v1 invalidates the goldens silently.
- **D-09:** **Normal set backs the five flow suites; blank/DGW back targeted specs** for the surfaces those scenarios actually change (chip timeline DGW/BGW callouts, fixtures ticker with missing/double rows, xP table under a blank week). A full suite × 3-scenarios matrix was rejected (3× runtime, 3× golden maintenance, little signal).

### Solver-flow determinism
- **D-10:** **Frozen prediction pool, no model artifact at test time.** The fixture set includes the solver's input pool (per-player xP/prices etc.) frozen at capture; fixture mode loads it directly, bypassing model inference. The real ILP still solves over it. No `xp_model.joblib` in git, nothing to load in CI, and weekly retrains can't shift expected values — the "never the calendar" guarantee.
- **D-11:** **Invariants everywhere + one pinned golden.** Every solve test asserts structural invariants: legal 15-man squad (2/5/5/3), locks present, excludes absent, results bar consistent with the pitch, bank arithmetic. One canonical solve on the frozen pool additionally pins the exact XI/transfers as a golden — if a CBC version bump ever flips an optimal tie, exactly one test needs re-pinning, not the whole suite.
- **D-12:** **Plan flow is tested for real at minimum horizon:** a real `/api/plan` solve on the frozen pool at 2 GWs (a few seconds) with a generous per-test timeout — the flow, wait copy, and per-week rendering are exercised in-browser. Skipping the plan flow and full-horizon solves were both rejected.

### Assertion depth & test matrix
- **D-13:** **Chromium only.** The regressions this suite hunts (contract drift, sort semantics, solver flows) are engine-independent; WebKit/Firefox are addable later as Playwright projects without rewriting tests.
- **D-14:** **Viewports:** standard desktop (e.g. 1280×720) for the flow suites; a dedicated **1720px spec for G-01-3** (header inner wrapper ≤1088px, horizontally centered, x-range matching `<main>`'s content box — per the Phase 1 handoff); **phone-width specs (e.g. 390px) for the team/pitch page** asserting Phase 3's D-07 promise — full formation plus bench fit the viewport with no horizontal overflow.
- **D-15:** **Exact expected values are hardcoded literals** hand-derived once from the immutable v1 fixtures (cell strings, row order). Re-deriving expectations from fixture JSON at test time was rejected — it re-implements the formatting logic under test, so a shared bug would pass silently.
- **D-16:** **Geometry via `boundingBox()` assertions, no screenshot baselines.** Pitch layout is guarded the G-01-3 way: row-centering symmetry (the G-03-1 class of bug), cards within viewport at phone width, bench alignment. Screenshot testing was rejected for environment flake (WSL2 local vs CI runners, font rendering).

### Claude's Discretion
- Exact env-var name(s) and internal design of the fixture seam in `api/main.py`; how the frozen pool is loaded (parquet vs JSON) and where it hooks into pool-building.
- Directory layout and naming under `e2e/` (or `frontend/e2e/`), spec file organization, and npm script names.
- The blank/DGW synthesis script's language and location.
- Exact viewport pixel choices beyond the mandated 1720px; per-test timeout values; retry policy.
- Whether dark-mode gets an E2E spot-check (not discussed; Vitest covers the toggle).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase handoffs (mandatory test content)
- `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md` — the G-01-3 handoff: exact 1720px assertions this suite must implement; also documents the `npm run typecheck` no-op trap (don't use it as a gate)
- `.planning/debug/nav-text-not-responsive.md` — full G-01-3 diagnosis backing those assertions

### App under test (flows and behaviors the specs assert)
- `.planning/phases/03-pitch-renderer-squad-views/03-CONTEXT.md` — team-page decisions the specs must respect: D-10 no auto-load (model squad default), D-11 `?entry=`/`?tab=` deep links auto-load/auto-rate, D-13 lock/exclude popover, D-16 in-place pitch update + results bar, D-18 single-pitch rate diff
- `.planning/phases/02-data-layer-non-pitch-pages/02-CONTEXT.md` — page behaviors: D-02 top-50 cap, D-07 ephemeral sort/filter state, D-18–D-22 GW banner states
- `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` — intentional vanilla deltas; E2E must assert the React behavior, not vanilla's, where they differ

### Backend seam (the fixture-mode change lands here)
- `api/main.py` — `_state`/`_initial_state()`, `_load_live`, pool builders, solve cache, `require_key` stub, static mount; the env-var fixture seam extends this file
- `tests/test_api.py` + `tests/conftest.py` — Phase 1's mocking patterns (`fake_boot`, `_reset_api_state`, `responses`) — the in-process precedent the on-disk fixture seam mirrors
- `pytest.ini` — the `-p no:playwright -p no:seleniumbase` plugin disables (why the Node runner is mandatory)

### Data contract & fixtures
- `web/data/` — the live export contract; the "normal" capture freezes one week of these files
- `frontend/src/test/fixtures/` — existing Vitest fixtures (19 files incl. `chips_dgw.json`); shape reference for the E2E sets, deliberately NOT promoted to E2E fixtures (D-06)
- `predict/export.py` — the export builders that produce `web/data/*.json`; source of truth for the contract the frozen snapshots must match

### Testing conventions
- `.planning/codebase/TESTING.md` — both test stacks' conventions; E2E suite should feel native alongside them

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/test/fixtures/*.json` — contract-correct shapes for every endpoint/file; blueprint for what the E2E capture must contain (including `rate_response.json`'s corrected `best_move` semantics)
- `tests/test_api.py` `fake_boot()` — documents exactly which FPL bootstrap fields the API reads; use it to decide what the trimmed real capture keeps (D-07)
- `api/main.py` `_initial_state()` seam (built in Phase 1 for tests) — the natural anchor point for the fixture-mode branch
- Vanilla `web/team.html` wait copy already ported verbatim (Phase 3 D-15) — E2E can assert the literal wait strings during solve/plan

### Established Patterns
- Package-legitimacy gate: `@playwright/test` (and any helper packages) needs the blocking human approval gate with exact `--save-exact` pins before install
- Node runner mandatory: `pytest.ini` disables both Python browser plugins over the `--browser` flag collision — the suite is `@playwright/test`, not pytest
- `web/data/*.json` is fetched at runtime, never bundled — the built `dist/` under uvicorn must still fetch `/data/*.json` from the server (this is itself worth an E2E assertion)
- Frontend `npm run typecheck` is currently a no-op (solution tsconfig with `files: []`) — do not use it as a verification gate; `npm run build` (`tsc -b`) is the real check

### Integration Points
- `api/main.py` — env-var fixture seam + `dist/` static mount (D-01/D-02); the only production file this phase touches
- `frontend/package.json` / root — E2E scripts, `playwright.config.ts` with `webServer` (D-05)
- Phase 5 CI-02 consumes this suite verbatim: cached browsers, uvicorn + built frontend + fixture data — keep every command CI-invocable
- Phase 7 (CUT-01) reuses the D-02 mount switch for cutover

</code_context>

<specifics>
## Specific Ideas

- "Pass or fail on code, never on the calendar" is the phase's north star — every choice (frozen pool, immutable v1 fixtures, no live FPL calls, no screenshots) traces back to it
- Real player names in fixtures matter: when a test fails, the human debugging it should see a recognizable page, not synthetic `P1023` rows
- Entry 6980093 (the user's real team) is the team-flow fixture entry — per PROJECT.md, never entry 1
- G-03-1 (pitch rows drifting half a column) is the canonical example of the bug class D-16's geometry assertions must catch

</specifics>

<deferred>
## Deferred Ideas

- **WebKit/Firefox engine coverage** — revisit as a pre-launch pass (FPL managers are phone-heavy → iOS/WebKit); addable as Playwright projects without rewriting tests
- **Screenshot/visual-regression baselines** — reconsider only if geometry assertions prove insufficient; would need a docker-normalized environment (Phase 5+)
- **Keyed-auth E2E spot-check** — belongs with the Supabase JWT milestone (PAID-02), when the frontend actually sends keys
- **Schema drift guard** (pytest comparing export-builder output keys against frozen fixture keys) — nice-to-have hardening; fits Phase 6's validation work if wanted

</deferred>

---

*Phase: 4-E2E Regression Suite*
*Context gathered: 2026-09-03*
