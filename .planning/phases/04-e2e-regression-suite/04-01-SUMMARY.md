---
phase: 04-e2e-regression-suite
plan: 01
subsystem: testing
tags: [e2e, fastapi, fixture-mode, playwright-prep, static-mount, spa-fallback]

requires:
  - phase: 03-pitch-renderer-squad-views
    provides: "The rebuilt React app (frontend/dist build output) and the unchanged web/data/*.json export contract this seam replays"
provides:
  - "e2e/fixtures/v1/normal/**: an immutable, verifiable, versioned fixture set (GW3) covering api/ (trimmed bootstrap/fixtures, 6 frozen per-gameweek pools, intervals, entry 6980093's picks/summary/history) and web-data/ (the real predict/export.py builders' output for the same capture)"
  - "e2e/scripts/capture_fixtures.py --capture/--verify: the capture + offline-coherence-check tool, reusable for a future v2 cut"
  - "FPL_FIXTURE_DIR / FPL_FIXTURE_DATA_DIR seam in api/main.py: every outbound-network and model-artifact call site branches to disk, the static mount splits into /data + / against frontend/dist, production (unset env) is byte-identical to before"
  - "frontend/package.json postbuild hook producing dist/404.html so Starlette's StaticFiles(html=True) SPA fallback works for client-side routes"
  - "tests/test_fixture_mode.py: in-process proof the seam is network-free and artifact-free across health/meta/team/solve/rate/plan/data + the unset-env production-default assertion"
affects: [e2e-suite, playwright-webserver, ci-02, cutover]

actuals:
  tokens: 297667
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Runtime env-var seam generalizing tests/conftest.py's per-test monkeypatch (_reset_api_state) into a real uvicorn-process branch: rebind the single model-inference leaf (_gw_pool) on BOTH api.main's own imported name and predict.live's module global, since build_pool/build_horizon_pool resolve _gw_pool from predict.live's own globals at call time"
    - "Dual StaticFiles mount (/data before the catch-all /) with check_dir=False so a fixture-mode server can boot before the frontend build finishes; dist/404.html as a byte-copy of dist/index.html is the entire SPA-fallback mechanism (Starlette's html=True already implements it, no custom routing needed)"
    - "Fixture files trimmed to exactly the keys the reading code touches, keeping every row (never trimming element/team/fixture counts) — keeps the offline capture verifiable and small (<1MB) without losing coherence"

key-files:
  created:
    - e2e/scripts/capture_fixtures.py
    - e2e/fixtures/v1/MANIFEST.md
    - e2e/fixtures/v1/normal/api/bootstrap-static.json
    - e2e/fixtures/v1/normal/api/fixtures.json
    - e2e/fixtures/v1/normal/api/intervals.json
    - e2e/fixtures/v1/normal/api/capture.json
    - e2e/fixtures/v1/normal/api/pools/gw3.json..gw8.json
    - e2e/fixtures/v1/normal/api/entries/6980093/picks_event2.json
    - e2e/fixtures/v1/normal/api/entries/6980093/summary.json
    - e2e/fixtures/v1/normal/api/entries/6980093/history.json
    - e2e/fixtures/v1/normal/web-data/meta.json
    - e2e/fixtures/v1/normal/web-data/xp_table.json
    - e2e/fixtures/v1/normal/web-data/captains.json
    - e2e/fixtures/v1/normal/web-data/squad.json
    - e2e/fixtures/v1/normal/web-data/fixtures.json
    - e2e/fixtures/v1/normal/web-data/chips.json
    - e2e/fixtures/v1/normal/web-data/standings.json
    - e2e/fixtures/v1/normal/web-data/leaders.json
    - e2e/fixtures/v1/normal/web-data/watchlist.json
    - tests/test_fixture_mode.py
  modified:
    - api/main.py
    - frontend/package.json
    - .gitignore

key-decisions:
  - "[Task 1 checkpoint:decision, gate=blocking-human] Manager-field capture policy for entry 6980093's summary.json: scrub-names — player_first_name/player_last_name blanked to empty strings, team name (`name`) and every numeric season figure (summary_overall_points, summary_overall_rank, summary_event_points) captured verbatim. Applied to summary.json only; picks_event2.json and history.json carry no name fields and are captured verbatim regardless. User's verbatim answer: 'scrub-names'."
  - "Captured GW3 (not a preordained gameweek) — _next_gw(boot) derived it from the currently-cached data/raw/live/bootstrap-static.json at capture time; frozen_now_utc = 2026-09-03T16:02:38Z, pool_gws = [3,4,5,6,7,8]."
  - "Fixture-mode _refresh() seeds _state['artifact'] = 'fixture-mode' (a non-None string sentinel), never joblib.load, mirroring tests/conftest.py's existing artifact-sentinel precedent generalized to a real runtime branch."
  - "_pool()/_gw_pools() themselves are NOT branched — only the single _gw_pool leaf is rebound (on both api.main and predict.live), so build_pool/build_horizon_pool's real aggregation and horizon-decay math still run over the frozen per-gameweek inputs."
  - "Static mount split keeps the production else-branch's mount statement text byte-identical to the pre-existing line (app.mount(\"/\", StaticFiles(directory=config.ROOT / \"web\", html=True), name=\"site\")); only fixture-mode adds a new if-branch above it."

patterns-established:
  - "Fixture-mode branch discipline: every requests.get/joblib.load call site gets an if _FIXTURE_ROOT: branch reading committed JSON from disk — verified by grep counting exactly 3 requests.get(  call sites, all inside three extracted single-purpose helpers (_fetch_entry_history, _fetch_entry_picks, _fetch_entry_summary)"

requirements-completed: [E2E-01]

coverage:
  - id: D1
    description: "Immutable, offline-verifiable v1 'normal' E2E fixture set (GW3), including the Task 1 scrub-names policy applied to entry 6980093's summary.json"
    requirement: "E2E-01"
    verification:
      - kind: integration
        ref: "python e2e/scripts/capture_fixtures.py --verify"
        status: pass
      - kind: other
        ref: "git ls-files e2e/fixtures/v1 | wc -l (>=20); git check-ignore -q e2e/fixtures (non-zero exit, tracked); grep -rl fantasy.premierleague.com e2e/fixtures/v1/ (empty)"
        status: pass
    human_judgment: false
  - id: D2
    description: "FPL_FIXTURE_DIR/FPL_FIXTURE_DATA_DIR seam in api/main.py: every outbound-network + model-artifact call site branches to disk, dual static mount, production default unchanged"
    requirement: "E2E-01"
    verification:
      - kind: integration
        ref: "pytest tests/test_fixture_mode.py -x -q (9 passed, requests.get/joblib.load poisoned to raise)"
        status: pass
      - kind: integration
        ref: "pytest -q (full existing suite, 76 passed)"
        status: pass
      - kind: other
        ref: "grep -c 'requests.get(' api/main.py == 3; grep -c FPL_FIXTURE_DIR/FPL_FIXTURE_DATA_DIR api/main.py >= 1 each"
        status: pass
    human_judgment: false
  - id: D3
    description: "frontend/package.json postbuild hook producing dist/404.html for the SPA client-route fallback"
    requirement: "E2E-01"
    verification:
      - kind: integration
        ref: "bash scripts/verify_frontend_build.sh && cmp frontend/dist/index.html frontend/dist/404.html"
        status: pass
      - kind: other
        ref: "git diff --exit-code -- scripts/verify_frontend_build.sh (clean — script untouched)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 01: Fixture Seam + Immutable v1 Capture Summary

**Froze GW3's real FPL data (bootstrap, fixtures, 6 gameweeks of model output, entry 6980093's picks/summary/history, and the full web/data export) into an immutable, offline-verifiable `e2e/fixtures/v1/normal/` set, and wired a `FPL_FIXTURE_DIR` env-var seam into `api/main.py` that makes the real FastAPI app — real ILP solves included — read that set from disk instead of calling `fantasy.premierleague.com` or loading the model artifact, with production (unset env) left byte-for-byte unchanged.**

## Performance
- **Duration:** 55min
- **Started:** 2026-09-03T15:51:54Z (approx., per STATE.md session start)
- **Completed:** 2026-09-03T16:47:00Z (approx.)
- **Tasks:** 3 (1 checkpoint:decision + 2 auto)
- **Files modified:** 28 (25 fixture files + capture script in commit 1; api/main.py, frontend/package.json, tests/test_fixture_mode.py in commit 2)

## Accomplishments
- Captured a real, coherent GW3 fixture set: trimmed `bootstrap-static.json`/`fixtures.json`, 6 frozen per-gameweek prediction pools (gw3–gw8), a verbatim `intervals.json` copy, entry 6980093's picks/summary/history (summary scrubbed per the Task 1 decision), and the full `web-data/*.json` export regenerated by `predict/export.py`'s real builders against that same capture — `/api` and `/data` describe one gameweek universe.
- Built `e2e/scripts/capture_fixtures.py --verify`, an offline (no network, no model artifact) coherence check that confirms the committed set's internal consistency and will guard any future v2 cut.
- Extended `api/main.py` with the `FPL_FIXTURE_DIR`/`FPL_FIXTURE_DATA_DIR` seam across every outbound-data call site — `_load_live`, the single `_gw_pool` model-inference leaf (rebound on both `api.main` and `predict.live`, since `build_pool`/`build_horizon_pool` resolve it from `predict.live`'s own module globals), the intervals artifact, the cold-start artifact sentinel, and the three entry-endpoint `requests.get` sites (extracted into `_fetch_entry_history`/`_fetch_entry_picks`/`_fetch_entry_summary`) — plus a dual static mount (`/data` before the catch-all `/`) that serves the built React app and the frozen `/data` set in fixture mode.
- Added a `postbuild` hook to `frontend/package.json` that copies `dist/index.html` to `dist/404.html`, making Starlette's existing `StaticFiles(html=True)` fallback resolve client-side routes (e.g. `/team`) instead of 404ing.
- Wrote `tests/test_fixture_mode.py`: 9 in-process tests proving the seam is genuinely network-free and artifact-free (both `requests.get` and `joblib.load` monkeypatched to raise) across `/api/health`, `/api/meta`, `/api/team/{entry}` (200 and 404 paths), `/api/solve`, `/api/rate`, `/api/plan`, `/data/xp_table.json`, the SPA fallback, and the unset-env single-mount production default.

## Task Commits
1. **Task 1: Decide the capture policy for entry 6980093's manager fields** — checkpoint:decision, no commit (decision recorded in STATE.md and this SUMMARY; user answered "scrub-names")
2. **Task 2: Capture and commit the immutable v1 "normal" fixture set** - `f7360ae` (feat)
3. **Task 3: Add the FPL_FIXTURE_DIR seam and the SPA build hook to the running stack** - `d89c5da` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `e2e/scripts/capture_fixtures.py` - capture/verify CLI; trims bootstrap/fixtures, freezes 6 gw pools via `predict.live._gw_pool`, fetches entry 6980093 live once, regenerates `web-data/` via `predict/export.py`'s real builders
- `e2e/fixtures/v1/MANIFEST.md` - provenance, trim keep-lists, immutability rule, recorded Task 1 answer, Synthesis-rules placeholder for a later plan
- `e2e/fixtures/v1/normal/**` (23 files) - the committed fixture set itself
- `api/main.py` - `_FIXTURE_ROOT`/`_FIXTURE_API`/`_FIXTURE_DATA`/`_fixture_json`, `_load_live_fixture`, `_gw_pool_fixture` (rebinds both `api.main._gw_pool` and `predict.live._gw_pool`), `_intervals_artifact`, `_refresh`'s artifact-sentinel branch, three extracted entry-fetch helpers, dual static mount
- `frontend/package.json` - `postbuild` script (`cp dist/index.html dist/404.html`)
- `tests/test_fixture_mode.py` - 9 tests proving the seam
- `.gitignore` - ignores Playwright run output (`e2e/test-results/`, etc.); documents `e2e/fixtures/` as deliberately committed

## Decisions Made
See `key-decisions` in frontmatter above — the Task 1 checkpoint:decision answer ("scrub-names") is the load-bearing one for this plan; it determined exactly which two fields of `entries/6980093/summary.json` are blanked versus captured verbatim.

## Deviations from Plan

None — plan executed exactly as written, including the exact trimming keep-lists, the Task 1 decision applied to summary.json only, and the dual-mount/404.html mechanism per RESEARCH.md's verified Starlette behavior.

**Total deviations:** 0.
**Impact:** none.

## Issues Encountered

None. Two implementation details required iteration during the acceptance-criteria verification loop (both resolved before commit, not deviations from the plan's design):
- `tests/test_fixture_mode.py`'s health/meta ordering: `/api/health` reads `_state["gw"]` without calling `_refresh()`, so the test calls `/api/meta` first (which does refresh) to observe the loaded gameweek via shared module state — matching `tests/test_api.py`'s own existing health/meta test ordering.
- The unset-env single-mount assertion needed to check for a `starlette.routing.Mount` instance rather than a route's `.path` attribute (`Mount.path` is `""`, not `"/"`, in the installed Starlette version).

## User Setup Required

None.

## Next Phase Readiness

The fixture set and the `FPL_FIXTURE_DIR` seam are the foundation every later plan in this phase depends on: plan 04-02 (or whichever plan builds the Playwright harness) can now point `webServer.command`'s `env.FPL_FIXTURE_DIR` at `e2e/fixtures/v1/normal` and get a fully offline, network-free, artifact-free FastAPI+React stack. `e2e/fixtures/v1/MANIFEST.md`'s "Synthesis rules" section is intentionally left empty for the plan that derives the `blank`/`dgw` variants from this `normal` capture. No blockers.

## Self-Check: PASSED

- `e2e/scripts/capture_fixtures.py` — FOUND
- `e2e/fixtures/v1/MANIFEST.md` — FOUND
- `e2e/fixtures/v1/normal/api/capture.json` — FOUND
- `e2e/fixtures/v1/normal/api/pools/gw3.json` through `gw8.json` (6 files) — FOUND
- `e2e/fixtures/v1/normal/api/entries/6980093/{picks_event2.json,summary.json,history.json}` — FOUND
- `e2e/fixtures/v1/normal/web-data/*.json` (9 files, no scoreboard.json) — FOUND
- `tests/test_fixture_mode.py` — FOUND
- `git log --oneline --all --grep="04-01"` — commits `f7360ae` and `d89c5da` both carry a `(04-01)` scope and are present in `git log --oneline -5`
- Re-ran all acceptance criteria for Task 2 and Task 3: all pass (see verification block above)
- Re-ran plan-level `<verification>`: `capture_fixtures.py --verify` exits 0; `pytest -q` is green (76 passed); `bash scripts/verify_frontend_build.sh` prints `BUILD PURITY OK` and `cmp frontend/dist/index.html frontend/dist/404.html` succeeds; `git diff` on `api/main.py` shows the production mount statement text unchanged (only relocated under a new `else:` branch)
