---
phase: 01-test-base-layer-app-skeleton
reviewed: 2026-09-01T11:40:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - .gitignore
  - api/main.py
  - tests/conftest.py
  - tests/test_api.py
  - requirements.txt
  - scripts/verify_dev_proxy.sh
  - scripts/verify_frontend_build.sh
  - frontend/index.html
  - frontend/package.json
  - frontend/vite.config.ts
  - frontend/vitest.config.ts
  - frontend/tsconfig.json
  - frontend/tsconfig.app.json
  - frontend/tsconfig.node.json
  - frontend/src/main.tsx
  - frontend/src/router.tsx
  - frontend/src/index.css
  - frontend/src/lib/api.ts
  - frontend/src/test/setup.ts
  - frontend/src/test/harness.test.tsx
  - frontend/src/components/PageShell.tsx
  - frontend/src/components/PageShell.test.tsx
  - frontend/src/components/Spinner.tsx
  - frontend/src/components/ErrorState.tsx
  - frontend/src/components/EmptyState.tsx
  - frontend/src/components/PlaceholderPage.tsx
  - frontend/src/components/NotFoundPage.tsx
  - frontend/src/components/ErrorState.test.tsx
  - frontend/src/components/Spinner.test.tsx
  - frontend/src/routes/routeIsolation.test.tsx
  - frontend/src/routes/XpTable.tsx
  - frontend/src/routes/Team.tsx
  - frontend/src/routes/Fixtures.tsx
  - frontend/src/routes/Prices.tsx
  - frontend/src/routes/League.tsx
  - frontend/src/routes/Scoreboard.tsx
  - frontend/src/routes/Differentials.tsx
  - frontend/src/routes/Methodology.tsx
findings:
  critical: 0
  warning: 3
  info: 7
  total: 10
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-09-01T11:40:00Z
**Depth:** standard
**Files Reviewed:** 37 (35 listed paths; `frontend/tsconfig.json` + `frontend/tsconfig.app.json`/`tsconfig.node.json` counted individually)
**Status:** issues_found

## Summary

Reviewed the Phase 1 backend test-seam changes (`api/main.py`'s `_initial_state()` extraction, `tests/conftest.py`, `tests/test_api.py`) and the full React/Vite app-skeleton scaffold (`frontend/`) plus the two verification shell scripts and repo-level config (`.gitignore`, `requirements.txt`).

Both test suites were actually run, not just read: `pytest tests/test_api.py` (41 passed), `npx vitest run` (7 passed), and `npm run build` (`tsc -b && vite build`, succeeds) plus `scripts/verify_frontend_build.sh` (BUILD PURITY OK). No crashes, no failing assertions, no dangerous patterns (`eval`, `innerHTML`, hardcoded secrets, empty catches) found anywhere in scope.

`api/main.py`'s diff for this phase is confirmed (via `git show`) to be exactly the `_initial_state()` factory extraction — a pure refactor, same six keys, same defaults. Everything else in that file is pre-existing and out of phase scope; any note on it below is Info-only per the review brief. The already-known `npm run typecheck` no-op (deferred-items.md) and the backstop suite's `grep -Eic` count-not-verified-≥3 weakness (01-SECURITY.md T-05-04) are not re-reported here.

The issues found are concentrated in two places: (1) a foundational frontend pattern — the unchecked `as T` cast in the shared `fetchJson`/`fetchApi` helper that every future route will inherit, and a TS project-reference gap that silently excludes `vitest.config.ts` from any type-check; and (2) a coverage gap where the router's per-route `errorElement`/`RouteErrorBoundary` mechanism — the mechanism 01-SECURITY.md's T-05-01 and 01-VALIDATION.md's 01-05-03 cite as proven — is never actually exercised by any test in the suite; every "route failure" test triggers a `useQuery` `isError` branch handled entirely inside the component, not a render-time throw caught by `errorElement`.

None of these rise to Blocker/Critical: nothing crashes, no security boundary is bypassed, and the gaps are all either forward-looking (will matter once real data-fetching routes are built in Phase 2) or documentation-accuracy issues (a claimed "closed" mitigation whose test doesn't prove what it claims).

## Warnings

### WR-01: Shared API fetch helper trusts an unchecked type assertion

**File:** `frontend/src/lib/api.ts:10-16`
**Issue:** `fetchAndCheck<T>` does `return (await res.json()) as T;` with no runtime shape validation. `fetchJson`/`fetchApi` are explicitly documented as "the discipline" every future route should use (per the file's own header comment), so this pattern will propagate to every one of the remaining 7 routes as they gain real fetches in Phase 2. If the backend contract in `web/data/*.json` or an `/api/*` response drifts (renamed/missing/retyped field), TypeScript gives false confidence — the mismatch surfaces at runtime as `undefined` values silently flowing into JSX rather than a caught, reportable error. `Spinner.test.tsx`'s own fixture (`{ gw: 5, season: "2026-27" }`, missing `horizon`/`deadline_utc`/`generated_utc`/`model_mtime_utc` required by `MetaResponse`) demonstrates the gap is real: it passes today only because `XpTable` happens not to read the missing fields.
**Fix:** At minimum, narrow the assertion to a defensive runtime check on the fields the caller actually needs (e.g., a small `assertShape` helper or a lightweight schema validator such as `zod`) before returning, so a contract break throws a catchable error instead of shipping `undefined`s into the UI.

### WR-02: `vitest.config.ts` is excluded from every TypeScript project reference

**File:** `frontend/vitest.config.ts`, `frontend/tsconfig.node.json:22`, `frontend/tsconfig.json:3-6`
**Issue:** `tsconfig.json` (the solution file) references only `tsconfig.app.json` (`include: ["src"]`) and `tsconfig.node.json` (`include: ["vite.config.ts"]`). `vitest.config.ts` lives at the project root and matches neither include list. Confirmed with `npx tsc -b --dry`, which reports it will build only `tsconfig.app.json` and `tsconfig.node.json` — `vitest.config.ts` is never mentioned. This means even after the already-logged `npm run typecheck` no-op (deferred-items.md) is fixed to use `tsc -b`, `vitest.config.ts` will still never be type-checked by any script in `package.json`. A future edit that breaks its types (e.g., a bad `defineConfig` option) will pass both `npm run typecheck` and `npm run build` silently.
**Fix:** Add `"vitest.config.ts"` to `tsconfig.node.json`'s `include` array (it already targets Node-context config files and already type-checks `vite.config.ts` the same way).

### WR-03: The per-route `errorElement`/`RouteErrorBoundary` isolation mechanism has zero test coverage

**File:** `frontend/src/router.tsx:20-67`, `frontend/src/components/ErrorState.tsx:43-49` (`RouteErrorBoundary`), `frontend/src/components/ErrorState.test.tsx`, `frontend/src/routes/routeIsolation.test.tsx`
**Issue:** 01-SECURITY.md marks T-05-01 ("one route unmounting the whole SPA") "closed", citing `routeIsolation.test.tsx`; 01-VALIDATION.md's row 01-05-03 makes the same claim. In practice, every "route failure" scenario in the test suite (`ErrorState.test.tsx`'s "UI-SPEC E2 error backstop" and `routeIsolation.test.tsx`'s "keeps the nav and a sibling route interactive" tests) mocks `globalThis.fetch` to reject, which `XpTable`'s own `useQuery` `isError` branch catches and renders `<ErrorState/>` directly — a normal component render path, not a thrown exception. `RouteErrorBoundary`/`useRouteError()` is only invoked by React Router when a route's render (or a loader, of which there are none here) *throws*, which none of the 8 routes currently do (`useQuery`'s default `throwOnError` is `false`). Confirmed by `grep -rn "RouteErrorBoundary\|errorElement\|useRouteError" frontend/src --include="*.test.tsx"` returning no matches. So the actual isolation behavior this mitigation is supposed to provide — "a route that throws during render doesn't take the header nav down with it" — is unverified. The passing tests would still pass identically even if `errorElement` were deleted from every route in `router.tsx`, since nothing in the test flow ever reaches it.
**Fix:** Add at least one test that forces an actual render-time throw inside a routed component (e.g., a test-only component that throws synchronously, mounted via `createMemoryRouter` with its own `errorElement`), and assert the boundary renders `ErrorState` while a sibling route/nav stays interactive — this is the scenario T-05-01 and UI-01 (01-05-03) actually claim to cover.

## Info

### IN-01: Unreachable `EmptyState` branch in the tracer route

**File:** `frontend/src/routes/XpTable.tsx:25-27`
**Issue:** `if (!data) return <EmptyState />;` is dead in practice: with `useQuery` (TanStack Query v5, always-enabled, no `placeholderData`), `data` is guaranteed defined whenever `isPending` and `isError` are both false. `meta.json` is also always a non-empty object, never an empty array/collection, so there is no real "zero rows" case for this endpoint. No test exercises this branch.
**Fix:** Either drop the branch here (reserve `EmptyState` for a route that actually returns a collection, e.g., `xp_table.json`), or add a comment noting it is intentionally defensive/future-proofing so a future reader doesn't assume it's reachable today.

### IN-02: Redundant `.gitignore` entries

**File:** `.gitignore:7-10`
**Issue:** `frontend/node_modules/` (line 8) and `frontend/dist/` (line 9) are already covered by the generic `node_modules/` (line 7) and `dist/` (line 10) patterns immediately adjacent to them — a gitignore pattern with no leading slash matches at any depth, so the more specific lines do no independent work.
**Fix:** Drop the two redundant lines, or add a comment explaining they're intentionally kept for readability/discoverability if that's the goal.

### IN-03: Catch-all route is the only one without an `errorElement`

**File:** `frontend/src/router.tsx:64`
**Issue:** All 8 concrete routes declare their own `errorElement`; `{ path: "*", element: <NotFoundPage /> }` does not. Risk is negligible since `NotFoundPage` is static markup with no fetch/render branching, but it's an inconsistency against the file's own stated pattern ("Each concrete route carries its OWN errorElement").
**Fix:** Add `errorElement: <RouteErrorBoundary resource="this page" />` for consistency, or note in the comment why the catch-all is deliberately exempt.

### IN-04: Hardcoded developer-machine path as script default

**File:** `scripts/verify_dev_proxy.sh:11`
**Issue:** `PY="${PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"` falls back to one developer's absolute conda path. This matches the documented project convention (CLAUDE.md pins this exact environment) and is overridable via `$PYTHON`, but on a fresh clone/CI runner without that env var set, the script fails with a not-found error rather than falling back to a `PATH`-resolved `python3`.
**Fix:** Consider `${PYTHON:-python3}` as the ultimate fallback, or explicitly document that `$PYTHON` (or the conda env) must be set before running this script in CI (Phase 5 concern).

### IN-05: `SolveRequest.budget` has no bounds validation (pre-existing)

**File:** `api/main.py:240`
**Issue:** Pre-existing code, out of this phase's diff (only `_initial_state()` was extracted here) — noted as Info per review scope. `free_transfers`, `horizon`, and `max_transfers` all use `Field(..., ge=..., le=...)`, but `budget: float | None = None` has no lower/upper bound, so a negative or absurd budget value passes request validation and reaches `pick_squad`.
**Fix:** Add a sane bound, e.g. `Field(None, gt=0, le=200)`, when this endpoint is next touched.

### IN-06: Concurrency backstop test's wait window is short and unexplained

**File:** `frontend/src/routes/routeIsolation.test.tsx:115-119`
**Issue:** After `release()`, the test awaits only two `setTimeout(resolve, 0)` macrotask ticks before asserting `rejectionHandler` was never called. TanStack Query's internal retryer may resolve/settle an abandoned query's promise over more than two macrotasks; if so, this assertion could pass without the abandoned query's promise chain having actually finished processing, giving a weaker guarantee than the test name ("raises no unhandled promise rejection") implies. The test currently passes (verified via `npx vitest run`), so this is a latent reliability concern, not a proven failure.
**Fix:** Either document why two ticks is sufficient (e.g., cite TanStack Query's internal scheduling), or use `await vi.waitFor(...)`/a longer deterministic drain (e.g., `await Promise.resolve().then(...)` chained to the query's own settled state) instead of a fixed tick count.

---

_Reviewed: 2026-09-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Incremental Review — Plan 01-06 (gap closure)

**Reviewed:** 2026-09-01T11:40:00Z
**Scope:** `frontend/src/components/PageShell.tsx` (diff only — the containment-wrapper rework), `frontend/src/components/PageShell.test.tsx` (new file, containment-parity regression test)

Confirmed via `git log -p` that the `PageShell.tsx` diff for commit `06b70d8` (plan 01-06) is exactly: (1) stripping layout/gutter classes off the outer `<header>`, leaving `border-b border-line py-4` only; (2) adding an inner `<div className="mx-auto flex w-full max-w-[68rem] flex-wrap items-center gap-[18px] px-4">` wrapping brand + nav + meta-banner slot; (3) applying the identical correction to the footer paragraph (`w-full` and `px-4` added alongside the pre-existing `mx-auto max-w-[68rem]`, with `px-4` dropped from the outer `<footer>`). `main`'s classes are unchanged (`mx-auto w-full max-w-[68rem] flex-1 px-4` was already correct before this plan).

Verified by running the actual test suite and build, not just reading: `npx vitest run src/components/PageShell.test.tsx` (2 passed), `npx vitest run` (full suite, 9 passed across 5 files), `npm run build` (`tsc -b && vite build`, succeeds). No regressions in the rest of the suite from the structural change.

Traced the resulting DOM against both new tests: header's `firstElementChild` (the containment div), `main`, and the footer `<p>` all carry the exact token set `mx-auto w-full max-w-[68rem] px-4`; the outer `<header>`/`<footer>` carry only `border-b`/`border-t` + `py-4`, no `max-w-*`/`px-*`. This is a correct, structurally-sound fix for UAT gap G-01-3 — header, main, and footer content now share one containment geometry while the borders stay full-bleed. No accessibility regression: `nav aria-label="Site"` and touch-target sizing are untouched by this diff.

No Critical or Warning-level defects found in the two files. One new Info-level maintainability observation:

### IN-07: Containment class string is now triplicated with no single source of truth

**File:** `frontend/src/components/PageShell.tsx:32,59,64`, `frontend/src/components/PageShell.test.tsx:12`
**Issue:** The literal string `"mx-auto w-full max-w-[68rem] px-4"` (as a substring of a larger class list) now appears independently at three call sites in `PageShell.tsx` — the header's inner div (line 32), `<main>` (line 59), and the footer `<p>` (line 64) — plus a fourth independent copy of the same four tokens as `CONTAINMENT` in the new test (line 12). This is precisely the defect class that produced UAT gap G-01-3 in the first place: the header wrapper was originally added without the same containment classes as `main`, and drifted. The new `PageShell.test.tsx` mitigates the immediate risk (it will catch a future edit that updates only 1 or 2 of the 3 sites, since it independently checks all three elements against the same `CONTAINMENT` array), so this is not elevated to Warning — but there is still no single exported constant (e.g. `const CONTENT_WIDTH = "mx-auto w-full max-w-[68rem] px-4"`) that the three JSX sites and the test both derive from, so a deliberate width change (e.g. `68rem` → `72rem`) still requires four manual, uncoordinated edits to stay in sync.
**Fix:** Extract a shared `const CONTENT_WIDTH = "mx-auto w-full max-w-[68rem] px-4";` in `PageShell.tsx`, apply it at all three call sites via template literals, and import/derive the test's `CONTAINMENT` array from the same constant (e.g. `CONTENT_WIDTH.split(" ")`) so there is exactly one place to change the column width.

---

_Reviewed: 2026-09-01T11:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
