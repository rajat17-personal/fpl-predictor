---
phase: 01-test-base-layer-app-skeleton
plan: 03
subsystem: testing
tags: [pytest, fastapi, testclient, responses, monkeypatch, concurrency, auth, api]

# Dependency graph
requires:
  - phase: 01-02
    provides: "_initial_state() DI seam, tests/conftest.py autouse reset fixture, tests/test_api.py base file with TEAMS/fake_boot/fake_pool builders and /api/health, /api/meta, /api/solve contract tests"
provides:
  - "tests/test_api.py extended with /api/team and /api/rate contract tests against a URL-mocked FPL API (responses library)"
  - "require_key three-mode coverage (open/valid-key/invalid-key) across both protected endpoints, including empty/whitespace FPL_API_KEYS edge cases"
  - "A real-OS-thread concurrency test proving the unlocked _solve_cache race does not crash or corrupt state, green on 5 consecutive runs"
  - "requirements.txt pin: responses>=0.25,<0.27 (test-only HTTP mocking dependency)"
affects: [01-05, 05-ci-docker]

# Actuals (#2632)
actuals:
  tokens: 3277
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: ["responses>=0.25,<0.27 (PyPI, HTTP mocking for requests.get)"]
  patterns:
    - "@responses.activate + responses.add(url, json=..., status=...) to intercept requests.get calls made directly against config.FPL_API — no importable seam existed for _fetch_team/_free_transfers, so interception happens at the HTTP layer instead"
    - "pytest.mark.parametrize((env_value, header, expected_status)) to drive require_key's mode matrix as named, individually-failing cases rather than one monolithic assertion block"
    - "ThreadPoolExecutor(max_workers=8) sharing one TestClient across 20 submitted requests, with a monkeypatched slow_pool() sleep to deterministically widen the race window — real OS-thread overlap on module globals, not a sequential loop"
    - "Synthetic-only fixture identities (entry 12345, 'Test FC', 'Test Manager', keys k1/k2/nope) documented in a fixture-block comment so a future contributor cannot mistake them for live data"

key-files:
  created: []
  modified:
    - tests/test_api.py
    - requirements.txt

key-decisions:
  - "Task 1's plan-authored <verify> command called responses.__version__, which does not exist on the installed responses==0.26.3 (still within the approved >=0.25,<0.27 pin — verified via `pip show`/importlib.metadata). Substituted importlib.metadata.version('responses') to prove the same fact (module imports, pin recorded); documented as a Rule 3 deviation in the verification command, not a change to the plan's intent or the pinned range."
  - "/api/rate's 200 path is covered once (test_rate_endpoint_contract, full FPL mocking); its 401 paths are covered separately in test_rate_endpoint_require_key_modes without FPL mocking, per the plan's explicit escape hatch — a wrong/missing key raises inside require_key before the handler body runs, so no FPL URL is ever reached for those cases."
  - "did not add locking, an LRU, or a TTL to _solve_cache while writing the concurrency test that observes the race — that remediation is explicitly Phase 6 REL-05's scope (STRIDE T-03-05, disposition: accept in this plan)."

patterns-established:
  - "HTTP-layer test doubles for endpoints that call requests.get() directly (no DI seam): register exact URLs with responses.add, never a catch-all, so an unregistered call raises loudly rather than reaching the real FPL API."

requirements-completed: [APIT-01, APIT-02, APIT-03]

coverage:
  - id: D1
    description: "/api/team/{entry} and /api/rate/{entry} full response contracts, 404/best-effort-failure branches, against a URL-mocked FPL API"
    requirement: "APIT-01"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_team_endpoint_contract"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_team_endpoint_missing_picks"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_team_endpoint_summary_failure_is_best_effort"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_rate_endpoint_contract"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_rate_endpoint_missing_history_leaves_free_transfers_null"
        status: pass
    human_judgment: false
  - id: D2
    description: "require_key covered in all three modes (open/valid-key/invalid-key) across /api/solve and /api/rate, including empty/comma/whitespace-only FPL_API_KEYS staying open, plus /api/health and /api/meta proven open in every mode"
    requirement: "APIT-02"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_require_key_three_modes (9 parametrized cases)"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_rate_endpoint_require_key_modes"
        status: pass
      - kind: unit
        ref: "tests/test_api.py#test_unauthenticated_endpoints_stay_open (6 parametrized cases)"
        status: pass
    human_judgment: false
  - id: D3
    description: "20 concurrent POST /api/solve requests across 8 real OS threads run green with no exceptions and well-formed bodies, stable on 5 consecutive runs"
    requirement: "APIT-03"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_concurrent_solve_and_refresh (5 consecutive invocations, all green)"
        status: pass
    human_judgment: false
  - id: D4
    description: "No real FPL manager's personal name, team name, rank, or entry id leaked into a committed fixture, assertion, or recorded HTTP body"
    requirement: "APIT-01"
    verification: []
    human_judgment: true
    rationale: "Plan-level <human-check> requires a human to skim the three responses.add fixture bodies and confirm no field carries real third-party PII, since /team and /rate return third-party personal data and a fixture is a permanent git record. Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase, matching 01-02's precedent for its own human-check item."

# Metrics
duration: 12min
completed: 2026-08-31
status: complete
---

# Phase 1 Plan 3: Test Base Layer & App Skeleton — API Safety Net (FPL Contract, Auth, Concurrency) Summary

**`/api/team` and `/api/rate` covered against a `responses`-mocked FPL API, `require_key` pinned in open/valid/invalid mode across both protected endpoints including its empty-value open-by-default edge cases, and the unlocked `_solve_cache` race made observable via 20 concurrent requests across 8 real OS threads — green on 5 consecutive runs, `api/main.py` untouched throughout.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-31 (Plan 01-03 start)
- **Completed:** 2026-08-31
- **Tasks:** 3
- **Files modified:** 2 (`tests/test_api.py`, `requirements.txt`)

## Accomplishments

- Installed and pinned `responses>=0.25,<0.27` (from plan 01-01's approved package
  set) and added `fake_picks(boot)`, an FPL-shaped 15-man picks body builder
  matching `config.POSITION_QUOTA` (2 GK / 5 DEF / 5 MID / 3 FWD).
- `/api/team/{entry}`: full response contract (`entry`/`bank`/`value`/`picks`/
  `manager`), the 404-from-FPL branch (detail names the gameweek), and the
  best-effort manager-summary branch (a 500 there still returns 200 with
  `manager: {}`) — all against `@responses.activate`-registered exact URLs, no
  catch-all.
- `/api/rate/{entry}`: full response contract with `score` asserted as an
  `int` in `0..100`, plus the `/history/` 404 branch leaving `free_transfers`
  null.
- `require_key` walked through a 9-case parametrized matrix against
  `/api/solve` (unset, both keys in a two-key list, wrong key, missing header,
  whitespace-stripped key, and the three empty-ish `FPL_API_KEYS` values that
  the `if keys` guard treats as open), plus a dedicated `/api/rate` test for
  its wrong-key/missing-header 401s, plus a 6-case matrix proving
  `/api/health`/`/api/meta` stay open in every mode. `api/main.py` untouched —
  confirmed by `git diff --quiet`.
- `test_concurrent_solve_and_refresh`: 20 `POST /api/solve` calls dispatched
  across 8 real threads via `ThreadPoolExecutor`, sharing one `TestClient` so
  Starlette's `anyio` worker-thread dispatch produces genuine overlap on
  `_solve_cache`. Payloads vary `horizon`/`free_transfers` so cache-hit and
  cache-miss paths run concurrently; a `time.sleep(0.05)` in the mocked pool
  widens the window deterministically. Assertions are limited to "no
  exception, all 200s, well-formed bodies, `_state["pools"]` still a dict" —
  exactly the guarantee the code makes today, no more. Green on 5 consecutive
  runs.
- Ran the exact `pytest` invocation Phase 5's CI job inherits:
  `/home/sraja/miniconda3/envs/python314/bin/python -m pytest` → **67 passed**
  (66 pre-existing + this plan's net addition after the 5-into-67 count from
  01-02's 45 → 67; full suite green throughout all three task commits).

## Task Commits

Each task was committed atomically:

1. **Task 1: Install responses and cover /api/team and /api/rate against a mocked FPL API** — `714310f` (test)
2. **Task 2: Cover require_key in all three modes across both protected endpoints** — `ef0725b` (test)
3. **Task 3: Make the pool-refresh / solve-cache race observable in a repeatable test** — `969979b` (test)

**Plan metadata:** committed alongside this SUMMARY (see below).

## Files Created/Modified

- `tests/test_api.py` (extended, 508 lines) — `fake_picks()` builder;
  `test_team_endpoint_contract`, `test_team_endpoint_missing_picks`,
  `test_team_endpoint_summary_failure_is_best_effort`,
  `test_rate_endpoint_contract`,
  `test_rate_endpoint_missing_history_leaves_free_transfers_null`,
  `test_require_key_three_modes` (9 parametrized cases),
  `test_rate_endpoint_require_key_modes`,
  `test_unauthenticated_endpoints_stay_open` (6 parametrized cases),
  `test_concurrent_solve_and_refresh`.
- `requirements.txt` — new `# Test-only` comment group with
  `responses>=0.25,<0.27`.

## Decisions Made

- Substituted `importlib.metadata.version('responses')` for the plan's
  `responses.__version__` in Task 1's verification (the attribute doesn't
  exist on the installed 0.26.3) — same fact proven, different mechanism. See
  Deviations below.
- Covered `/api/rate`'s 401 paths without FPL mocking (the dependency raises
  before the handler body runs) and its 200 path once, in the dedicated
  contract test — avoiding duplicated FPL-mocking boilerplate across three
  test functions, per the plan's own stated escape hatch.
- Left `_solve_cache` completely unmodified while writing the test that
  observes its race, per the plan's explicit prohibition (Phase 6 REL-05
  owns the fix).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1's `<verify>` command used a non-existent `responses.__version__` attribute**
- **Found during:** Task 1 (installing and verifying the `responses` pin)
- **Issue:** The plan's second automated `<verify>` command was
  `python -c "import responses; print('RESPONSES', responses.__version__)"`.
  The installed `responses==0.26.3` (within the approved `>=0.25,<0.27` range)
  does not define a module-level `__version__` attribute; the command raised
  `AttributeError`.
- **Fix:** Ran `python -c "import importlib.metadata as m; print('RESPONSES', m.version('responses'))"`
  instead, which proves the identical fact the plan's check was after — the
  package is importable and its installed version satisfies the pin — via
  `importlib.metadata` rather than a module attribute the library doesn't
  expose.
- **Files modified:** None — this is a verification-command substitution, not
  an implementation or `requirements.txt` change; the pin text itself
  (`responses>=0.25,<0.27`) is exactly what the plan specified.
- **Verification:** `import responses` exits 0; `importlib.metadata.version('responses')`
  returns `0.26.3`; `grep -q '^responses' requirements.txt` finds the pin.
- **Committed in:** `714310f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — a verification-command defect unrelated to the implementation)
**Impact on plan:** No implementation or dependency-pin changes; the substitution proves the exact same acceptance fact the plan's original command intended. No scope creep.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All five phase endpoints (`/api/health`, `/api/meta`, `/api/team/{entry}`,
  `/api/solve`, `/api/rate/{entry}`) now have contract assertions in
  `tests/test_api.py`.
- `require_key` is pinned in all three modes on both protected endpoints, and
  `/api/health`/`/api/meta` are proven open in every mode — this is the
  explicit baseline the Phase 6 / `PAID-02` auth swap will be diffed against.
- The pool-refresh/solve-cache race is observable and stable (green x5); its
  fix is deliberately deferred to Phase 6 `REL-05` and not attempted here.
- Full `pytest` command for CI (Phase 5) confirmed:
  `/home/sraja/miniconda3/envs/python314/bin/python -m pytest` — **67 passed,
  0 failed.**
- **Human verification pending (deferred to end-of-phase per
  `workflow.human_verify_mode: end-of-phase`):** skim the `responses.add`
  fixture bodies in `tests/test_api.py` (entry `12345`, `"Test FC"`,
  `"Test Manager"`) and confirm none carries a real FPL manager's identity —
  same as this plan's own review during authoring, now surfaced for
  independent confirmation alongside 01-02's pending `_initial_state()`
  refactor-diff check.
- APIT-01, APIT-02, APIT-03 all marked complete in `REQUIREMENTS.md`.
- No blockers. Ready for 01-05 (or Phase 1 close-out, per `ROADMAP.md`).

---
*Phase: 01-test-base-layer-app-skeleton*
*Completed: 2026-08-31*

## Self-Check: PASSED

- FOUND: tests/test_api.py
- FOUND: requirements.txt (contains `responses>=0.25,<0.27`)
- FOUND commit: 714310f
- FOUND commit: ef0725b
- FOUND commit: 969979b
- Re-ran full `pytest` suite: 67 passed, 0 failed
- Re-ran `pytest tests/test_api.py -k concurrent` x5: all green
- Re-verified `git diff --quiet HEAD -- api/main.py`: unchanged since plan 01-02
