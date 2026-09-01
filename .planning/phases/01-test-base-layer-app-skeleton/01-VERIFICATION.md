---
phase: 01-test-base-layer-app-skeleton
verified: 2026-09-01T02:00:00Z
status: human_needed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
behavior_unverified_items: []
coincidental_reliance_items: []
human_verification:
  - test: "api/main.py diff is a pure refactor"
    expected: "Same six _state keys, same defaults, same order; no change to _refresh, _pool, _solve_cache, or CORSMiddleware"
    why_human: "Documented as verification: judgment in 01-02-PLAN.md's prohibitions and as a plan-level <human-check>. Independently re-verified by this verifier via `git show 7313446 -- api/main.py` and `git diff --quiet HEAD -- api/main.py` in later commits — diff is confined exactly to the _initial_state() extraction. Recorded here per protocol since the plan explicitly required human sign-off; the evidence is already conclusive."
  - test: "No third-party manager PII in tests/test_api.py's responses fixtures"
    expected: "All manager/team/entry identities are synthetic"
    why_human: "Documented as verification: judgment in 01-03-PLAN.md. Independently re-verified by this verifier via grep — only 'Test FC', 'Test Manager', entry 12345, and keys k1/k2/nope appear. Recorded here per protocol; evidence is already conclusive."
  - test: "App shell visual conformance: nav active-state accent, 375px flex-wrap, footer disclaimer wording, live ErrorState+Retry recovery with uvicorn stopped/restarted"
    expected: "Nav highlights the active link, wraps without a hamburger at 375px, footer reads the exact three-sentence disclaimer, and stopping/restarting uvicorn shows ErrorState then recovers via Retry without a full reload"
    why_human: "Visual layout, touch-target comfort, and live dev-server interaction are not mechanically checkable from source. Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase (01-04 and 01-05 <human-check> blocks; 01-VALIDATION.md 'Manual-Only Verifications')."
  - test: "Package legitimacy sign-off scope"
    expected: "Human reviewed and approved the 13 [SUS]-flagged packages before any install"
    why_human: "gate=\"blocking-human\" trust decision, by protocol never auto-passable. Already recorded as answered ('Approved') in 01-01-SUMMARY.md; listed here for completeness of the human-verification ledger, not because it is outstanding."
---

# Phase 1: Test Base Layer & App Skeleton Verification Report

**Phase Goal:** The API has a real test safety net, and a React app talks to it through a proven runtime seam.
**Verified:** 2026-09-01T02:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | pytest exercises /solve, /rate, /team, /health, and /meta against a mocked FPL API, and fails on contract/error regressions | ✓ VERIFIED | Ran `python -m pytest -q` independently: **67 passed**, 0 failed, 2.6s. `tests/test_api.py` (508 lines) covers all 5 endpoints: `test_health_and_meta_contract`, `test_solve_squad_contract`, `test_solve_request_bounds` (15 parametrized cases), `test_solve_resolution_and_rounding`, `test_team_endpoint_contract`, `test_team_endpoint_missing_picks`, `test_team_endpoint_summary_failure_is_best_effort`, `test_rate_endpoint_contract`, `test_rate_endpoint_missing_history_leaves_free_transfers_null`. All FPL HTTP calls are intercepted via `@responses.activate` with exact-URL registration (no catch-all) — confirmed by reading the fixture registrations; an unregistered URL raises inside the test by the library's own default. |
| 2 | require_key() covered in all three modes (open/valid/invalid) so a future auth swap is a verified diff | ✓ VERIFIED | Ran `pytest tests/test_api.py -q -k "require_key or stay_open" --collect-only`: **16 collected** (parametrized matrix, exceeds the plan's ≥10 gate). Ran the filtered suite: 6 passed. Confirmed via source read that the matrix covers unset/empty/comma/whitespace-only `FPL_API_KEYS` (open), a two-key list with both keys valid, a wrong key, and a missing header, across both `/api/solve` and `/api/rate/{entry}`, plus `/api/health`+`/api/meta` proven open in every mode. `api/main.py`'s `require_key()` itself is confirmed byte-unchanged since plan 01-02 (`git diff --quiet HEAD -- api/main.py` semantics verified via `git show`/`git log` — only one commit, `7313446`, ever touched the file, and that diff is the `_initial_state()` extraction only). |
| 3 | A concurrent solve + pool-refresh test runs green repeatedly, making the cache/lock race observable in tests | ✓ VERIFIED | Independently re-ran `pytest tests/test_api.py -k concurrent -x -q` **5 consecutive times**: all 5 green (1 passed each run). Read `test_concurrent_solve_and_refresh`: 20 `POST /api/solve` calls across `ThreadPoolExecutor(max_workers=8)` sharing one `TestClient`, varying `horizon`/`free_transfers` so cache-hit and cache-miss paths overlap; assertions limited to "no exception, all 200s, well-formed bodies, `_state[\"pools\"]` still a dict" — matches the code's actual guarantee, no over-claim. |
| 4 (UI-01) | React/Vite scaffold proves the dev-proxy runtime seam, all 8 routes render with error isolation, vanilla web/ untouched | ✓ VERIFIED | `npm --prefix frontend run test` independently re-run: **7 passed** (4 files). `npm --prefix frontend run build` succeeds (tsc -b && vite build, 727ms). `router.tsx` registers all 8 UI-SPEC paths plus a `*` catch-all, each concrete route with its own `errorElement={<RouteErrorBoundary/>}`. Wrote and ran an ad-hoc scratch test (deleted after use) that forced a genuine render-time throw inside `/team`'s element and confirmed the `errorElement` mechanism actually catches it — `ErrorState`'s "Couldn't load this page" heading renders and all 8 nav links remain present — directly resolving 01-REVIEW.md's WR-03 concern that the mechanism was unexercised (see Anti-Patterns section). `git status --porcelain web/` is empty and `comm -12` between `frontend/dist`'s built filenames and `web/data/*.json`'s filenames returns nothing (no pipeline JSON reached the build). |

**Score:** 4/4 roadmap truths verified (all four map to 8 underlying must-have truths across the 5 plans' frontmatter, also independently checked — see Required Artifacts and Key Link sections below).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.gitignore` | Root ignore rules covering caches, node_modules, regenerable data, secrets | ✓ VERIFIED | Exists, contains `node_modules`, `!data/snapshots/` negation confirmed working (`git ls-files data/snapshots` returns a tracked parquet file) |
| `api/main.py` (`_initial_state()`) | DI seam, single source of truth for `_state` shape | ✓ VERIFIED | `grep -c 'def _initial_state'` = 1; diff confirmed pure refactor via `git show 7313446` |
| `tests/conftest.py` | Autouse fixture resetting module globals + artifact sentinel | ✓ VERIFIED | Exists, `autouse=True` present, referenced by all test runs (confirmed via passing suite) |
| `tests/test_api.py` | APIT-01/02/03 contract, auth, concurrency tests | ✓ VERIFIED | 508 lines, 41 test functions/cases collected under this file alone, all passing |
| `requirements.txt` (`responses` pin) | HTTP-mocking dependency pinned | ✓ VERIFIED | `grep '^responses' requirements.txt` → `responses>=0.25,<0.27`; installed version 0.26.3 confirmed within range |
| `frontend/vite.config.ts` | Dev proxy for `/api` and `/data` to `localhost:8000` | ✓ VERIFIED | Both proxy keys present in source; `bash scripts/verify_dev_proxy.sh` (re-run) prints `DEV PROXY OK` |
| `frontend/src/lib/api.ts` | `fetchJson`/`fetchApi` throwing descriptive errors | ✓ VERIFIED | Both exported; WR-01 (unchecked `as T` cast) noted as a forward-looking Info/Warning item, not a functional failure this phase |
| `frontend/src/router.tsx` | 8 routes + catch-all, each with `errorElement` | ✓ VERIFIED | All 9 path entries present; per-route `errorElement` confirmed on all 8 concrete routes; catch-all intentionally exempt (IN-03, non-blocking) |
| `frontend/src/components/{Spinner,ErrorState,EmptyState,PlaceholderPage,NotFoundPage}.tsx` | UI-SPEC shell states | ✓ VERIFIED | All 5 exist, exported, and match the Copywriting Contract text verbatim (heading strings independently grepped) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/conftest.py` | `api/main.py` | `_initial_state()` call rebuilding `_state` | ✓ WIRED | Confirmed by passing `test_state_isolation_and_no_artifact_load` |
| `tests/test_api.py` | `api/main.py` | `monkeypatch.setattr` on `_pool`/`_load_live` | ✓ WIRED | No outbound network in any test; full suite green with 0 network egress required |
| `tests/test_api.py` | `api/main.py` (`_fetch_team`/`_free_transfers`) | `responses.add` exact-URL registration | ✓ WIRED | `test_team_endpoint_contract`/`test_rate_endpoint_contract` pass; unregistered-URL-raises behavior is the `responses` library default, not overridden |
| `frontend/vite.config.ts` | `api/main.py` | `server.proxy` → `localhost:8000` | ✓ WIRED | `scripts/verify_dev_proxy.sh` independently re-run, prints `DEV PROXY OK` against live uvicorn+vite processes |
| `frontend/src/router.tsx` | `frontend/src/components/ErrorState.tsx` | `errorElement={<RouteErrorBoundary/>}` | ✓ WIRED (behaviorally confirmed, see below) | Static wiring confirmed by source read; **functional** behavior (catches a render-time throw) confirmed via this verifier's own ad-hoc test — see Behavioral Spot-Checks |
| `frontend/src/routes/XpTable.tsx` | `frontend/src/lib/api.ts` | `fetchJson('/data/meta.json')` in `useQuery` | ✓ WIRED | Relative path, no absolute URL/env var; confirmed by source read and passing dev-proxy check |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `XpTable.tsx` | `data` (gw, season) | `useQuery` → `fetchJson('/data/meta.json')` → Vite proxy → uvicorn `StaticFiles` mount → `web/data/meta.json` | Yes | ✓ FLOWING |
| `Team.tsx`, `Fixtures.tsx`, `Prices.tsx`, `League.tsx`, `Scoreboard.tsx`, `Differentials.tsx`, `Methodology.tsx` | n/a — static placeholder title/body | `PlaceholderPage` props, hardcoded per UI-SPEC | N/A | Intentional — these 7 routes are explicitly scoped to render placeholders only in this phase (UI-01 prohibition: "MUST NOT build page content ... every one of the 8 renders a placeholder this phase"); not a stub-detection false positive |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend full suite is real and green | `python -m pytest -q` | 67 passed, 0 failed, 2.6s | ✓ PASS |
| Auth matrix collects the claimed case count | `pytest tests/test_api.py -q -k "require_key or stay_open" --collect-only` | 16 collected | ✓ PASS |
| Concurrency test is stable, not flaky | `pytest tests/test_api.py -k concurrent -x -q` x5 | 5/5 green | ✓ PASS |
| Frontend test suite is real and green | `npm --prefix frontend run test` | 7 passed (4 files) | ✓ PASS |
| Frontend build succeeds and stays pure | `npm --prefix frontend run build` + filename `comm` against `web/data/*.json` | build succeeds; zero filename overlap | ✓ PASS |
| Dev proxy seam is live, not just documented | `bash scripts/verify_dev_proxy.sh` | `DEV PROXY OK` | ✓ PASS |
| `errorElement` mechanism actually intercepts a render-time throw (resolves 01-REVIEW.md WR-03) | Ad-hoc scratch test: forced `/team`'s element to throw synchronously, rendered via `createMemoryRouter` | `ErrorState` heading rendered, all 8 nav links present; scratch file deleted after use, suite re-confirmed at 7/7 | ✓ PASS |
| `api/main.py` diff since 01-02 is a pure refactor | `git show 7313446 -- api/main.py` | Confined exactly to the `_initial_state()` extraction; no other line touched in any later commit | ✓ PASS |
| `require_key()` unmodified while auth tests were written | `git log --oneline --all -- api/main.py` | Only one commit (`7313446`) ever touches the file | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| APIT-01 | 01-01, 01-02, 01-03 | TestClient contract tests for /solve, /rate, /team, /health, /meta with mocked FPL API | ✓ SATISFIED | 67 passing tests, all 5 endpoints covered, zero network egress |
| APIT-02 | 01-03 | require_key covered open/valid/invalid | ✓ SATISFIED | 16-case parametrized matrix, both protected endpoints |
| APIT-03 | 01-03 | Concurrency test with autouse state-reset fixture | ✓ SATISFIED | 5-consecutive-run stable, autouse fixture in `tests/conftest.py` |
| UI-01 | 01-01, 01-04, 01-05 | React/Vite app, 8 routes, dev proxy, runtime-fetched JSON | ✓ SATISFIED | All 8 routes + catch-all registered, dev proxy proven live, build purity confirmed |

No orphaned requirements: REQUIREMENTS.md's traceability table maps exactly APIT-01, APIT-02, APIT-03, UI-01 to Phase 1, matching every plan's `requirements:` frontmatter field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/lib/api.ts:10-16` | — | Unchecked `as T` cast in `fetchAndCheck` (WR-01, pre-existing finding) | ⚠️ Warning (non-blocking) | Forward risk for Phase 2 routes; demonstrated real via `Spinner.test.tsx`'s incomplete `MetaResponse` fixture passing silently. Not a phase-1 functional defect — no phase-1 route currently depends on the missing fields. |
| `frontend/vitest.config.ts` | — | Excluded from every `tsconfig` project reference (WR-02) | ⚠️ Warning (non-blocking) | A future bad `defineConfig` edit would pass both `typecheck` and `build` silently. Documentation/config-completeness gap, not a current failure. |
| `frontend/src/router.tsx:20-67`, `ErrorState.tsx` | — | Per-route `errorElement` mechanism had zero committed test coverage exercising an actual render-time throw (WR-03) | ⚠️ Warning — **independently resolved by this verification's behavioral spot-check** (see above); the mechanism works, but the repo's committed regression suite still does not prove it (coverage gap for future regressions) | The functional claim ("one route's failure can't take down the nav") is TRUE today, confirmed by direct test. The risk is regression-proofing: if `errorElement` were accidentally removed from a route in Phase 2, no test in the current suite would catch it, because every existing "route failure" test exercises `useQuery`'s `isError` component branch instead. |
| `frontend/package.json` (`typecheck` script) | — | `tsc --noEmit` against a TS solution file with `files: []` checks 0 files (Advisory Finding #1 in 01-SECURITY.md, already logged in `deferred-items.md`) | ⚠️ Warning (non-blocking, explicitly deferred to Phase 5 CI-01/CI-02) | Independently reproduced: `npm run typecheck` prints only the command echo and exits 0 with no diagnostics, checking nothing. Every "typecheck exits 0" acceptance criterion across plans 01-04/01-05 was vacuous. Real type-checking only happens via `npm run build`'s `tsc -b` step, which the review confirms does catch errors (e.g., the `process`-typing bug in 01-05). This is already tracked as a named follow-up owned by Phase 5 and is not this phase's scope to fix, but it means one of this phase's own repeatedly-cited acceptance gates ("npm run typecheck exits 0") does not test what its name implies. |

No 🛑 Blocker-severity anti-patterns found. No unreferenced TBD/FIXME/XXX markers in any file touched this phase.

## Human Verification Required

### 1. Live dev-server visual/interaction check

**Test:** Run `npm --prefix frontend run dev`, open http://localhost:5173, click through all 8 nav links, resize to 375px, and stop/restart the `uvicorn` process while on `/`.
**Expected:** Active nav link shows the accent colour; nav wraps to a second row (no hamburger) at 375px; footer shows the exact three-sentence disclaimer (statistics-not-certainty / no contests / no PL affiliation); with uvicorn stopped, `/` shows "Couldn't load this page" + Retry with no leaked URL/status/stack trace; clicking Retry after restarting uvicorn shows the live gameweek without a full page reload.
**Why human:** Visual layout, colour distinguishability, touch-target comfort, and live network-interruption recovery are not mechanically verifiable from source or a jsdom test environment. This is explicitly named in both plan 01-04's and 01-05's `<human-check>` blocks and in 01-VALIDATION.md's "Manual-Only Verifications" table, and is deferred to end-of-phase UAT by `workflow.human_verify_mode=end-of-phase`.

### 2. Package-legitimacy and PII sign-offs (recorded, listed for completeness)

**Test:** No action needed — already answered.
**Expected:** N/A.
**Why human:** These two items (13-package registry sign-off; PII-free fixture skim) both carry `verification: judgment` in their plans' `must_haves.prohibitions` and both already have a recorded human answer ("Approved" in 01-01-SUMMARY.md) that this verifier independently corroborated via git/grep evidence above. They surface here only because the plan-level protocol designates them `gate="blocking-human"`/human-check items that a verifier cannot itself close out as VERIFIED without a human's own confirmation trail — the trail exists, but per protocol these remain human-attributed decisions rather than mechanically-passed truths.

## Gaps Summary

No blocking gaps. All roadmap Success Criteria and every plan-level `must_haves.truth` were independently re-verified against the running code (not just read from SUMMARY.md), including re-running the full backend suite, the 5x concurrency stability gate, the frontend test/build/typecheck commands, the live dev-proxy script, and a from-scratch behavioral spot-check of the one mechanism (`errorElement`/`RouteErrorBoundary`) that 01-REVIEW.md flagged as functionally unverified by the committed suite (WR-03). That spot-check confirms the mechanism works correctly today.

The three Warning-level findings already surfaced by `01-REVIEW.md` (WR-01, WR-02, WR-03) and the Advisory Finding in `01-SECURITY.md` (typecheck no-op) are real, already documented, already routed to future phases (Phase 2 for the fetch-validation pattern, Phase 5 for CI wiring and the tsconfig reference gap), and do not block this phase's goal — they are coverage/regression-proofing gaps, not functional failures in what Phase 1 delivers today. They are carried forward here rather than re-litigated as new gaps.

The phase resolves to `human_needed` rather than `passed` solely because of the outstanding visual/live-interaction UAT item (item 1 above), which is explicitly scoped as end-of-phase human verification by this project's own workflow configuration, not a defect discovered by this verification pass.

---

_Verified: 2026-09-01T02:00:00Z_
_Verifier: Claude (gsd-verifier)_
