---
phase: 04-e2e-regression-suite
plan: 02
subsystem: testing
tags: [e2e, playwright, chromium, fixture-mode, geometry-regression, tracer]

requires:
  - phase: 04-e2e-regression-suite (plan 01)
    provides: "The FPL_FIXTURE_DIR/FPL_FIXTURE_DATA_DIR seam in api/main.py, the frontend postbuild 404.html hook, and the immutable e2e/fixtures/v1/normal/ capture (GW3) this plan's webServer and specs read from"
provides:
  - "e2e/package.json + e2e/tsconfig.json: an isolated, exact-pinned npm project (@playwright/test@1.62.1, @types/node@26.4.1, typescript@6.0.3) separate from frontend/"
  - "e2e/playwright.config.ts: single-command lifecycle owner -- chains `npm --prefix frontend run build` ahead of fixture-mode uvicorn, pins locale=en-GB/timezoneId=UTC, Chromium-only, port block starting at 8100 (never 8000), E2E_PORT/E2E_PYTHON/E2E_VARIANTS env knobs with variant servers+projects gated behind E2E_VARIANTS"
  - "e2e/helpers/page.ts: gotoReady() (clock-pin-before-nav, font-wait-after-nav) and watchOrigin() (network-isolation proof via first-navigation-establishes-origin), reused by every later spec in this phase"
  - "e2e/specs/smoke.spec.ts: the phase's tracer -- one Chromium run proving the exact frozen xP table row + deadline banner on `/`, the SPA 404.html fallback + fixture-mode /api/team/{entry} branch via direct navigation to `/team?entry=6980093`, and zero cross-origin requests"
  - "e2e/specs/shell-geometry.spec.ts: browser-only bounding-box regression locks for G-01-3 (1720px header containment, Phase 1 handoff) and G-03-1 (pitch row left/right gap symmetry at 1280px and 390px, Phase 3 regression class), plus D-07's 390px no-horizontal-overflow promise"
affects: [e2e-suite-wave-3, ci-02, cutover]

actuals:
  tokens: 5930
  tasks: 3
  commits: 2

tech-stack:
  added:
    - "@playwright/test@1.62.1 (e2e/package.json devDependency, exact pin)"
    - "@types/node@26.4.1 (e2e/package.json devDependency, exact pin)"
    - "typescript@6.0.3 (e2e/package.json devDependency, exact pin, matches frontend/'s already-approved pin)"
  patterns:
    - "webServer array chains `npm --prefix frontend run build && uvicorn ...` in ONE command so Playwright's health-check polling cannot start against a stale/empty dist/ -- the build is the slow part (180s timeout), not uvicorn's own boot"
    - "gotoReady(page, path, opts): pin page.clock.setFixedTime(FROZEN_NOW) BEFORE page.goto (a clock installed after navigation misses already-scheduled timers/Date reads from the initial render), then await document.fonts.ready AFTER navigation (bounding-box measurements need the swapped-in @fontsource metrics) -- no fixed-duration sleep anywhere in the suite"
    - "watchOrigin(page): the test origin is NOT read from page.url() at call time (still about:blank before the first navigation) -- the first top-level main-frame navigation request establishes the origin baseline, every request after (including later same-origin navigations to /team) is compared against it"
    - "Row-centring regression guard asserts on MEASURED bounding boxes (leftGap === rightGap within 1px), not on the placement algorithm's internals -- catches a regression of the G-03-1 integer-grid-column defect class regardless of which future mechanism reintroduces it"
    - "Row/bench card counts for shell-geometry.spec.ts are derived from the committed fixture's `starting` flags at test time (a structural count, not formatted display output) rather than hardcoded as an assumed formation -- stays honest if a future fixture re-cut changes the frozen squad's shape"

key-files:
  created:
    - e2e/package.json
    - e2e/package-lock.json
    - e2e/tsconfig.json
    - e2e/playwright.config.ts
    - e2e/helpers/page.ts
    - e2e/specs/smoke.spec.ts
    - e2e/specs/shell-geometry.spec.ts
  modified: []

key-decisions:
  - "[Task 1 checkpoint:decision, gate=blocking-human] Verbatim answer: approve-with-deps -- approved installing @playwright/test@1.62.1 (--save-exact, registry re-verified immediately before install: repository.url=git+https://github.com/microsoft/playwright.git, latest dist-tag matches, zero drift) and installing the Chromium browser with OS dependencies via `npx playwright install --with-deps chromium`."
  - "[checkpoint:human-verify, gate=blocking-human, mid-Task-2] A second npm package (@types/node) was required beyond Task 1's single-package install surface: e2e/tsconfig.json's `types: [\"node\"]` plus playwright.config.ts's `path`/`process.env.*` usage have no ambient type declarations without it, and @playwright/test's own dependency tree does not bundle it. Escalated per the package-manager-install exclusion (never auto-fixable). Verbatim answer: 'approve @types/node@26.4.1' -- installed --save-exact into e2e/package.json, isolated from frontend/'s own @types/node@26.4.0 copy (frontend/ is a sibling of e2e/, not an ancestor, so Node module resolution cannot see across)."
  - "[checkpoint:human-verify, gate=blocking-human, mid-Task-2] A THIRD npm package (typescript) was required, discovered via a concrete near-miss: `npx tsc --version` with no local typescript installed silently fell back to fetching an unrelated, deprecated npm-registry package literally named `tsc` (2.3kB no-op shim, `deps: none`, prints a warning banner and exits) instead of running the real TypeScript compiler -- npm's npx bin-name resolution falls back to a registry package matching the BIN name (`tsc`), not the PACKAGE name (`typescript`), whose own bin happens to also be named `tsc`. Contained: the decoy package only touched npm's ephemeral ~/.npm/_npx/ cache, never e2e/package.json/package-lock.json/node_modules. Verbatim answer: 'approve-6.0.3' -- installed typescript@6.0.3 --save-exact, matching the version already human-approved for frontend/package.json in Phase 1's gate."
  - "[Item 1 resolution, no checkpoint needed] The approved approve-with-deps Chromium install (`sudo npx playwright install --with-deps chromium`) failed for the user interactively -- not a missing-password problem but root's PATH resolving system Node 18.19.1 (unaffected by the user's own nvm Node 24 switch), and Playwright refuses to run under Node <20. Per the coordinator's fallback instructions: ran `npx playwright install chromium` (browser binary only, no sudo, no system changes) as this agent's own shell, then verified via an in-process `chromium.launch()` + render that WSL2 already provides every shared library Chromium needs -- the `sudo env \"PATH=$PATH\" npx playwright install-deps chromium` PATH-preserving fallback was never actually needed."
  - "The install surface for this plan closed at exactly three human-approved packages (@playwright/test@1.62.1, @types/node@26.4.1, typescript@6.0.3) -- no further package was installed without a new checkpoint."

patterns-established:
  - "e2e/ is a fully isolated npm project (own package.json/tsconfig.json/node_modules) at the repo root, sibling to frontend/ -- keeps Vitest's default spec glob from ever collecting a Playwright spec file, and means every e2e-scoped devDependency (including ones already present in frontend/, like @types/node and typescript) must be installed a second time here rather than assumed to resolve via Node's upward-only module resolution."
  - "Any plan-authored `<verify>`/acceptance-criteria command invoking a locally-scoped binary via bare `npx <bin>` (not `npm --prefix <dir> run <script>`) must be run with that package's own directory as cwd, or npx's bin-name fallback can silently resolve an unrelated registry package sharing the bin name instead of erroring -- `npx tsc --noEmit -p e2e/tsconfig.json` from the repo root does NOT run TypeScript; `(cd e2e && npx tsc --noEmit -p tsconfig.json)` does."

requirements-completed: [E2E-01]

coverage:
  - id: D1
    description: "Playwright harness scaffold (isolated npm project, single-command server lifecycle, shared gotoReady/watchOrigin helpers) plus the phase's tracer spec proving build->fixture-mode-uvicorn->real-API->Chromium end to end with exact frozen literals and zero network egress"
    requirement: "E2E-01"
    verification:
      - kind: e2e
        ref: "E2E_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python E2E_VARIANTS=0 npm --prefix e2e run test -- specs/smoke.spec.ts --project=chromium (2 passed)"
        status: pass
      - kind: other
        ref: "(cd e2e && npx tsc --noEmit -p tsconfig.json) exits 0; exact-pin/config-pin/suite-discipline grep gates all pass; npm --prefix frontend run test unaffected (363 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Browser-only geometry regression locks: G-01-3 header containment at 1720px, G-03-1 pitch row left/right gap symmetry at 1280px+390px, D-07 no-horizontal-overflow at 390px"
    requirement: "E2E-01"
    verification:
      - kind: e2e
        ref: "E2E_PYTHON=... E2E_VARIANTS=0 npm --prefix e2e run test -- specs/shell-geometry.spec.ts --project=chromium (4 passed); full non-variant suite together (6 passed, 2 parallel workers, no cross-contamination)"
        status: pass
      - kind: other
        ref: "node coverage-grep over shell-geometry.spec.ts (GEOMETRY COVERAGE OK); Group A's assertion (headerBox.width <= 1088) confirmed by inspection to fail a widened cap without needing to actually widen PageShell.tsx"
        status: pass
    human_judgment: false

duration: 75min (active; spans one host-session interruption/resume and three human checkpoint round-trips)
completed: 2026-09-04
status: complete
---

# Phase 4 Plan 02: Playwright Harness + Tracer + Shell Geometry Summary

**Stood up an isolated Playwright/Chromium harness that a single `npm --prefix e2e run test` command drives end to end — building the React app, booting fixture-mode uvicorn, and asserting exact frozen literals on both a static page and an API-backed deep link — then locked the pixel geometry (1720px header containment from Phase 1, pitch row centring symmetry from Phase 3) that only a real browser's layout engine can measure.**

## Performance
- **Duration:** ~75min active work (spread across a host-session interruption mid-Task-2 and three human checkpoint round-trips — see Issues Encountered)
- **Started:** 2026-09-03 (immediately following 04-01)
- **Completed:** 2026-09-04T01:22:11Z
- **Tasks:** 3 (1 checkpoint:decision + 1 tracer + 1 auto)
- **Files modified:** 7 (all new)

## Accomplishments
- Task 1's package-legitimacy checkpoint approved `@playwright/test@1.62.1` (`approve-with-deps`), registry-reverified immediately before install with zero drift.
- Built `e2e/package.json`/`e2e/tsconfig.json` as a fully isolated npm project (own `node_modules`, sibling to `frontend/`) so Vitest's default glob never collects a Playwright spec file and vice versa.
- `e2e/playwright.config.ts` owns the entire server lifecycle in one place: `webServer.command` chains `npm --prefix frontend run build` ahead of fixture-mode uvicorn (so `dist/`/`dist/404.html` always exist before the health check can pass), pins `locale: "en-GB"` / `timezoneId: "UTC"` (mandatory — `deadline.ts`'s `fmtAbs` is locale/timezone-dependent), uses a non-8000 port block (8100+) so a developer's own live-data uvicorn is never silently adopted, and gates the `chromium-blank`/`chromium-dgw` variant servers+projects behind `E2E_VARIANTS` (default ON).
- `e2e/helpers/page.ts` gives every spec two primitives: `gotoReady` (clock pinned before navigation, web fonts awaited after) and `watchOrigin` (network-isolation proof via first-navigation-establishes-origin, since `page.url()` is still `about:blank` when a spec attaches the listener before navigating).
- `e2e/specs/smoke.spec.ts` (the tracer) proved the whole stack for the first time in a real browser: the frozen `xP table`'s first row (B.Fernandes, MID, MUN, £12.0m, 48.6% owned, 5.90 Captain xP) and the exact deadline banner string (`GW3 deadline: Fri 4 Sept, 17:30 · in 1d 1h` / `generated just now`, hand-derived from `frozen_now_utc`/`deadline_utc`/`generated_utc` and verified against Node's own `Intl` before hardcoding) on `/`; direct navigation to `/team?entry=6980093` (never a nav click) rendering the loaded team's real 4-4-2 formation (`rajat · GW3` heading, reconstructed via `selectLoadedSquad`'s DEF/MID/FWD search: 4 DEF/4 MID/2 FWD maximise joined xp at 21.47 over every legal split) with all 15 player cards across the five `role="group"` rows; and zero cross-origin requests on both pages.
- `e2e/specs/shell-geometry.spec.ts` regression-locked Group A (1720px header inner wrapper ≤1088px, centred, sharing `<main>`'s x-range — the exact G-01-3 handoff from `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md`), Group B (left/right gap symmetry within 1px across all five pitch rows at both 1280px and 390px — the G-03-1 bug class from `.planning/debug/pitch-row-centering-drift.md`, with row/bench card counts derived from the frozen squad fixture's `starting` flags rather than assumed), and Group C (390px team page produces no horizontal overflow, D-07).
- Tracer feedback gate: re-ran all of Task 2's automated `<verify>` commands after completion (interactive mode, `human_verify_mode=end-of-phase`, verify carried only `<automated>` entries) — all green — logged `⚡ Tracer verified end-to-end — expanding` and proceeded directly to Task 3 with no checkpoint, per protocol.
- Full non-variant suite (both spec files, 6 tests, 2 parallel Playwright workers, one shared uvicorn process) passed with no cross-contamination — confirms the plan's flagged concurrency assumption (frozen pool immutable within a run; `_solve_cache` keys on a full-body sha1) held in practice, though this plan's specs never exercise `/api/solve` directly.
- Re-ran the full pytest suite (76 passed) and `npm --prefix frontend run test` (363 passed) after both commits — neither regressed.

## Task Commits
1. **Task 1: Package-legitimacy gate for @playwright/test** — checkpoint:decision, no commit (verbatim answer `approve-with-deps` recorded above and in STATE.md)
2. **Task 2: End-to-end tracer** — `bb4db08` (feat) — `e2e/package.json`, `e2e/package-lock.json`, `e2e/tsconfig.json`, `e2e/playwright.config.ts`, `e2e/helpers/page.ts`, `e2e/specs/smoke.spec.ts`
3. **Task 3: Pin the shell and pitch geometry** — `b72421f` (test) — `e2e/specs/shell-geometry.spec.ts`

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `e2e/package.json` / `e2e/package-lock.json` - isolated npm project; devDependencies `@playwright/test@1.62.1`, `@types/node@26.4.1`, `typescript@6.0.3`, all `--save-exact`, all individually human-approved
- `e2e/tsconfig.json` - standalone ESM project config (`module`/`moduleResolution` for bundler-style ESM node resolution, `lib: ["ES2022", "DOM"]` so `page.evaluate()` callbacks type-check against `document`, `strict`, `resolveJsonModule`, `types: ["node"]`)
- `e2e/playwright.config.ts` - full server-lifecycle owner; port block, locale/timezone pins, Chromium-only projects, `E2E_VARIANTS`-gated variant servers/projects
- `e2e/helpers/page.ts` - `gotoReady`, `watchOrigin`, and the re-exported `FROZEN_NOW`/`GW`/`ENTRY`/`PICKS_EVENT` constants every later spec in this phase will import rather than restate
- `e2e/specs/smoke.spec.ts` - the tracer: 2 tests, exact frozen literals, zero-egress proof
- `e2e/specs/shell-geometry.spec.ts` - 4 tests: header containment, row symmetry ×2 viewports, no-overflow

## Decisions Made
See `key-decisions` in frontmatter — three separate human checkpoints (Task 1's planned package gate, plus two unplanned ones for `@types/node` and `typescript`) and one self-resolved item (Chromium install form) are the load-bearing decisions for this plan.

## Deviations from Plan

**1. [Rule 3 - blocking, escalated via checkpoint] Second npm package required: `@types/node`**
- **Found during:** Task 2, while wiring `e2e/tsconfig.json`'s `types: ["node"]` requirement and `playwright.config.ts`'s `path`/`process.env.*` usage per the plan's own `<action>` text.
- **Issue:** Task 1's checkpoint framed this phase as a single-package install surface; a second package was actually required for the plan's own literal instructions to typecheck.
- **Fix:** Escalated via a new `checkpoint:human-verify` (package-manager installs are never auto-fixable, per this project's deviation rules). Human approved `@types/node@26.4.1`; installed `--save-exact`.
- **Files modified:** `e2e/package.json`, `e2e/package-lock.json`
- **Verification:** `(cd e2e && npx tsc --noEmit -p tsconfig.json)` exits 0
- **Commit:** `bb4db08`

**2. [Rule 3 - blocking, escalated via checkpoint] Third npm package required: `typescript`**
- **Found during:** Task 2, while preparing to run the `npx tsc --noEmit -p e2e/tsconfig.json` acceptance criterion — discovered that without a local `typescript` install, `npx tsc` silently fetches and runs an unrelated, deprecated registry package literally named `tsc` (a 2.3kB no-op shim with `deps: none`) instead of the real compiler, because npx resolves by BIN name, not package name.
- **Issue:** A third package, beyond Task 1's approved single-package surface, was required for a plan-mandated acceptance-criteria command to actually test anything.
- **Fix:** Escalated via `checkpoint:human-verify`. Human approved `approve-6.0.3` (matching `frontend/`'s already-vetted pin); installed `--save-exact`.
- **Files modified:** `e2e/package.json`, `e2e/package-lock.json`
- **Verification:** re-ran `npx tsc --version` from `e2e/` — confirmed it now resolves the real, locally-installed compiler
- **Commit:** `bb4db08`

**3. [Rule 3 - corrected verify command, no package change] `npx tsc` acceptance-criteria command needs `e2e/` as its working directory**
- **Found during:** Task 2, verifying the plan's literal acceptance criterion `npx tsc --noEmit -p e2e/tsconfig.json`.
- **Issue:** Run from the repo root (as every other repo-root-relative verify command in this plan is), that exact command resolves the same `tsc` decoy package described in deviation 2 — `typescript` lives only in `e2e/node_modules`, and Node module resolution does not search into a sibling directory (`frontend/` and `e2e/` are siblings, not ancestor/descendant).
- **Fix:** Used the functionally equivalent `(cd e2e && npx tsc --noEmit -p tsconfig.json)` for every `tsc`-based verification in this plan and documented the corrected form here for later plans that reuse this command.
- **Files modified:** none (verification-only)
- **Verification:** `(cd e2e && npx tsc --noEmit -p tsconfig.json)` → `E2E TYPES OK`
- **Commit:** n/a (documentation of a verify-step correction, not an implementation change)

**Total deviations:** 3 (2 auto-escalated package installs, both human-approved before proceeding; 1 verify-command correction, no code change).
**Impact:** Small, contained expansion of the install surface (2 additional packages beyond Task 1's approved one, both already-vetted/well-known and each individually re-approved by the human before install) plus one documentation fix to a plan-authored verify command. No architectural change, no unapproved installs, no silent package substitution.

## Issues Encountered

- **Host session interruption mid-Task-2:** the executing session exited partway through Task 2 (after `@types/node`/`typescript` were installed and the config/helper files were written, before the spec files existed). Resumed cleanly from coordinator-verified on-disk state (`e2e/package.json` had exactly the three approved packages; `e2e/specs/` was empty; no 04-02 commits existed) — no rework needed beyond re-confirming `(cd e2e && npx tsc --noEmit -p tsconfig.json)` still passed before continuing.
- **`npx tsc` decoy-package near-miss:** see Deviation 2 above. Confirmed contained — the decoy `tsc@2.0.4` package only ever touched npm's ephemeral `~/.npm/_npx/` cache, never `e2e/package.json`, `e2e/package-lock.json`, or `e2e/node_modules`.
- **Approved `approve-with-deps` Chromium install failed for an unanticipated reason (not a missing password):** `sudo npx playwright install --with-deps chromium` failed in the user's interactive terminal because `sudo`'s PATH resolves the system's Node 18.19.1 rather than the user's own nvm-managed Node 24 (switching the user's own shell to `nvm use --lts` had no effect on root's PATH), and Playwright requires Node ≥20. Per the coordinator's fallback instructions: ran `npx playwright install chromium` (browser binary only, this agent's own shell, no `sudo`, no system changes) and verified Chromium actually launches via an in-process `chromium.launch()` + render — succeeded immediately. WSL2 already provided every shared library Chromium needs, so the `sudo env "PATH=$PATH" npx playwright install-deps chromium` PATH-preserving fallback documented for this exact scenario was never actually needed.

## User Setup Required

None. Local runs need `E2E_PYTHON` set to the conda interpreter (documented in `playwright.config.ts`'s header comment and used throughout this plan's own verification: `E2E_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python`); CI (Phase 5) relies on `python` already being correctly on `PATH`.

## Next Phase Readiness

The harness this plan proves is the foundation every remaining plan in this phase adds spec files to — nothing about `e2e/playwright.config.ts`, `e2e/helpers/page.ts`, `e2e/package.json`'s three approved dependencies, or the port-block/variant-gating scheme should need to change. Later plans that need the `blank`/`dgw` fixture variants can rely on `E2E_VARIANTS` (default ON) already starting and gating those servers/projects correctly — they just need to populate `e2e/fixtures/v1/blank/web-data/` and `e2e/fixtures/v1/dgw/web-data/` and add `e2e/specs/variants/{blank,dgw}-*.spec.ts`. Installed versions for later plans to assume without re-installing: `@playwright/test@1.62.1`, Chromium `151.0.7922.34` (playwright build v1234), `@types/node@26.4.1`, `typescript@6.0.3`. No blockers.

## Self-Check: PASSED

- `e2e/package.json`, `e2e/package-lock.json`, `e2e/tsconfig.json`, `e2e/playwright.config.ts`, `e2e/helpers/page.ts`, `e2e/specs/smoke.spec.ts`, `e2e/specs/shell-geometry.spec.ts` — all FOUND on disk
- `git log --oneline --all --grep="04-02"` — commits `bb4db08` and `b72421f` both carry a `(04-02)` scope and are present in `git log --oneline -5`
- Re-ran all acceptance criteria for Task 2 and Task 3: all pass (smoke 2/2, shell-geometry 4/4, full non-variant suite 6/6 with 2 parallel workers, `(cd e2e && npx tsc --noEmit -p tsconfig.json)` exits 0, config-pin/exact-pin/suite-discipline/geometry-coverage grep gates all pass, `npm --prefix frontend run test` 363 passed)
- Re-ran plan-level `<verification>`: `E2E_VARIANTS=0 npm --prefix e2e run test -- --project=chromium` green (6 passed); `(cd e2e && npx tsc --noEmit -p tsconfig.json)` exits 0; `npm --prefix frontend run test` unaffected (363 passed); `bash scripts/verify_frontend_build.sh` prints `BUILD PURITY OK`; full pytest suite unaffected (76 passed)
