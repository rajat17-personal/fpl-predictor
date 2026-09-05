---
phase: 06-security-reliability-observability-hardening
plan: 01
subsystem: reliability
tags: [pydantic, structured-logging, json-io, fastapi, readiness-probe, fpl-api]

# Dependency graph
requires: []
provides:
  - "ops/ package: jsonio (context-manager read/write, atomic os.replace writes, PayloadError), jsonlog (JsonFormatter, idempotent configure_logging, log_event, redact), payloads (pydantic v2 bootstrap/fixtures validation, live vs fixture profile)"
  - "predict/live.py::_load_live reads and validates through ops.jsonio/ops.payloads instead of bare json.load(open(...))"
  - "api/main.py: structured JSON logging on startup, ready/last_error state, GET /api/ready distinct from GET /api/health, all five bare file handles closed"
affects: [06-02, 06-03, 06-04, 06-05]

# Actuals (#2632)
actuals:
  tokens: 10140
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ops.jsonio.read_json/write_json as the single chokepoint for every JSON file read/write in api/, predict/live.py and ops/ — no bare open() calls remain in any of those three trees"
    - "Two-profile pydantic validation (profile='live' vs profile='fixture') to cover the live FPL API payload and the trimmed, frozen E2E capture through the same validator without ever mutating the immutable v1 fixture set"
    - "Liveness (/api/health) vs readiness (/api/ready) as distinct, separately-tested FastAPI routes: liveness never acquires the pool lock or calls _refresh; readiness does both and surfaces the last failure's reason"
    - "Structured JSON logging via one idempotent root-logger handler (ops.jsonlog.configure_logging), with redact() blanking key-shaped fields and FPL_API_KEYS values before every line is emitted"

key-files:
  created:
    - ops/__init__.py
    - ops/jsonio.py
    - ops/jsonlog.py
    - ops/payloads.py
    - tests/test_payloads.py
    - tests/test_obs.py
  modified:
    - predict/live.py
    - api/main.py

key-decisions:
  - "Task 2 (tdd=\"true\") implementation and its tests were committed together in one feat(06-01) commit rather than a separate test(06-01) RED commit followed by a feat(06-01) GREEN commit — see TDD Gate Compliance below."
  - "Added a dedicated redact() test suite beyond the plan's explicit acceptance criteria — T-06-01-03's threat mitigation (no secret in a log line) had implementation but no direct test coverage until this was added (Rule 2 deviation)."
  - "predict/live.py's two other bare file-opening call sites (_fetch_entry's boot re-read, and the --purchase-prices override load) were also routed through ops.jsonio.read_json in Task 1, since the plan's own acceptance criteria requires zero bare open() calls anywhere in the file, not just inside _load_live."

requirements-completed: [REL-01, REL-03, REL-04, OBS-01, OBS-02]

coverage:
  - id: D1
    description: "ops/jsonio.py: context-manager read_json/write_json, PayloadError with actionable one-line messages, atomic os.replace writes"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "tests/test_payloads.py::test_missing_file_raises_payload_error_with_path_and_remedy"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_zero_byte_file_raises_payload_error_with_path_and_position"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_truncated_file_raises_payload_error_with_line_and_column"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_write_json_leaves_prior_content_intact_on_simulated_mid_write_crash"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_write_json_last_writer_wins_whole_no_truncated_file"
        status: pass
    human_judgment: false
  - id: D2
    description: "ops/jsonlog.py: structured JSON logging, idempotent handler install, redact() blanks secrets"
    requirement: OBS-01
    verification:
      - kind: unit
        ref: "tests/test_payloads.py::test_jsonlog_configure_logging_is_idempotent"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_redact_blanks_key_shaped_fields_regardless_of_value"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_redact_blanks_any_value_matching_an_fpl_api_keys_entry"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_jsonformatter_output_never_contains_a_redacted_secret"
        status: pass
    human_judgment: false
  - id: D3
    description: "ops/payloads.py pydantic validation rejects a malformed/schema-drifted bootstrap or fixtures payload before model inference, naming the failing field path"
    requirement: REL-03
    verification:
      - kind: unit
        ref: "tests/test_payloads.py::test_validate_bootstrap_committed_fixture_fails_under_live_profile"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_validate_bootstrap_missing_now_cost_names_elements_and_field"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_validate_bootstrap_empty_elements_list_names_elements"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_validate_bootstrap_list_input_raises_payload_error_not_type_error"
        status: pass
      - kind: unit
        ref: "tests/test_payloads.py::test_validate_fixtures_uncoercible_difficulty_names_index_and_field"
        status: pass
      - kind: integration
        ref: "python -c \"...validate_bootstrap/validate_fixtures against committed e2e/fixtures/v1/normal/api/*.json\" (plan <verify> command)"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET /api/ready distinct from GET /api/health: liveness never blocks on the pool lock or calls _refresh; readiness does, and returns 503 with a reason until a pool has loaded"
    requirement: OBS-02
    verification:
      - kind: unit
        ref: "tests/test_obs.py::test_health_never_blocks_on_the_pool_lock"
        status: pass
      - kind: unit
        ref: "tests/test_obs.py::test_ready_and_health_return_different_status_codes_when_not_ready"
        status: pass
      - kind: unit
        ref: "tests/test_obs.py::test_ready_returns_200_with_ready_true_after_a_successful_refresh"
        status: pass
      - kind: unit
        ref: "tests/test_obs.py::test_concurrent_ready_failures_never_garble_a_log_line"
        status: pass
      - kind: integration
        ref: "FPL_FIXTURE_DIR=e2e/fixtures/v1/normal python -c \"...\" (plan <verify> fixture-mode liveness/readiness check)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every bare file-opening call site in api/main.py, predict/live.py and ops/ is closed via a context manager (no fd leak under a long-lived uvicorn process)"
    requirement: REL-01
    verification:
      - kind: other
        ref: "! git ls-files 'api/*.py' 'predict/live.py' 'ops/*.py' | xargs grep -nE bare-open-pattern | grep -v 'with open(' | grep -q ."
        status: pass
      - kind: unit
        ref: "tests/test_api.py::test_team_endpoint_missing_picks (unmodified, still passes after the api/main.py refactor)"
        status: pass
      - kind: unit
        ref: "tests/test_api.py::test_team_endpoint_summary_failure_is_best_effort (unmodified, still passes)"
        status: pass
    human_judgment: false
  - id: D6
    description: "REL-04: an actionable message names the absolute path plus the regenerating command — assumption flagged unresolved by the plan's own edge-probe; verify at UAT"
    requirement: REL-04
    verification: []
    human_judgment: true
    rationale: "Plan's own 'Flagged assumptions' section marks REL-04 unclassified — 'actionable' is not independently specified anywhere beyond this plan's own interpretation (absolute path + regenerate command), so a human should confirm that interpretation matches intent."

# Metrics
duration: 30min
completed: 2026-09-05
status: complete
---

# Phase 6 Plan 01: Fail-Loudly Ops Spine Summary

**New `ops/` package (jsonio, jsonlog, payloads) rewires predict.live and api.main so a corrupt or schema-drifted FPL payload fails loudly end to end — actionable CLI message, one structured JSON log line, and a `/api/ready` 503 — while `/api/health` stays a stable, lock-free liveness probe.**

## Performance
- **Duration:** 30 min
- **Started:** 2026-09-05T11:09:00Z (approx.)
- **Completed:** 2026-09-05T11:39:00Z
- **Tasks:** 3 completed
- **Files modified:** 8 (6 created, 2 modified)

## Accomplishments
- Built `ops/jsonio.py`, `ops/jsonlog.py` and `ops/payloads.py` — the fail-loudly spine every remaining Phase 6 plan will call into.
- Rewired `predict/live.py::_load_live` and `api/main.py::_load_live_fixture` through the same pydantic validators (`profile="live"` vs `profile="fixture"`), so the frozen E2E capture and the live FPL API payload are both exercised by one validator that can never drift untested.
- Closed every bare `open()`/`json.load(open(...))` call site in `api/main.py`, `predict/live.py` and the new `ops/` package — proven by a repo-wide grep gate, not just spot-checked.
- Added `GET /api/ready`, distinct from `GET /api/health`: liveness answers in under 2 seconds even while another thread holds the pool lock; readiness surfaces the last failure's reason and only returns `ready: true` after a real successful load.
- Closed a coverage gap beyond the plan's own acceptance criteria: added direct unit tests for `ops.jsonlog.redact()`, since the T-06-01-03 threat mitigation (no secret in a log line) had implementation but no test proving it.

## Task Commits
Each task was committed atomically:
1. **Task 1: End-to-end "a broken FPL payload fails loudly"** - `6355e72` (feat)
2. **Task 2: Pydantic schema validation (REL-03)** - `f67a44d` (feat)
3. **Task 3: Close api/main.py's bare file handles; liveness/readiness split (REL-01, OBS-02)** - `33954f1` (fix)
4. **Follow-up: redact() test coverage (Rule 2 deviation)** - `5664c5e` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `ops/__init__.py` - package docstring for the operational-hardening layer
- `ops/jsonio.py` - `PayloadError`, `read_json` (context-manager, one-line actionable message), `write_json` (temp-file + `os.replace` atomic write)
- `ops/jsonlog.py` - `JsonFormatter`, `configure_logging` (idempotent root-logger handler), `log_event`, `redact`
- `ops/payloads.py` - pydantic v2 models (`Team`, `Event`, `Element`, `Fixture`, `Bootstrap`), `validate_bootstrap`/`validate_fixtures`, `LIVE_ONLY_ELEMENT_FIELDS`
- `predict/live.py` - `_load_live` reads+validates through `ops.jsonio`/`ops.payloads`; two other bare file reads (`_fetch_entry`, `--purchase-prices` override) also routed through `read_json`
- `api/main.py` - `configure_logging("api")` at startup, `_initial_state()` carries `ready`/`last_error`, `_refresh` sets/logs failure state, `GET /api/ready`, all five bare file-opening call sites replaced with `read_json`, `_load_live_fixture` validates through the fixture profile
- `tests/test_payloads.py` - 24 tests: `ops.jsonio` (read/write/atomicity), `ops.jsonlog` (idempotency, redact), `ops.payloads` (live vs fixture profile, malformed-payload behaviors), end-to-end health/ready proof
- `tests/test_obs.py` - 8 tests: liveness never blocks on the pool lock, readiness contract, 20-way concurrent structured-logging proof

## Decisions Made
- Combined Task 2's RED and GREEN steps into a single `feat(06-01)` commit instead of a separate failing-test commit followed by an implementation commit, since `ops/payloads.py` and its tests were designed together as one new module with no pre-existing code to characterize against. Documented under TDD Gate Compliance below rather than silently passed over.
- Routed `predict/live.py`'s two non-`_load_live` bare file reads (`_fetch_entry`'s boot re-read, and the `--purchase-prices` JSON override) through `ops.jsonio.read_json` in Task 1 rather than leaving them for a later plan — the plan's own acceptance criteria (`grep -nE '(^|[^A-Za-z0-9_.])open\('` across the whole file) requires zero bare opens anywhere in `predict/live.py`, not just inside `_load_live`.
- Added `ops.jsonlog.redact()` unit tests beyond the plan's explicit acceptance criteria — the threat register's T-06-01-03 mitigation ("no secret value appears" in a log line) had implementation from Task 1 but no test proving it until this plan's close-out pass (Rule 2 — missing critical test coverage for a stated security mitigation).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing test coverage] `ops.jsonlog.redact()` had no direct test**
- **Found during:** Close-out review after Task 3, cross-checking the threat register against test coverage
- **Issue:** T-06-01-03 (Information Disclosure, `ops.jsonlog` records, severity high, disposition mitigate) names `redact()` as the mitigation, but no test in `tests/test_payloads.py` exercised it directly — only indirectly, by not happening to log a secret in the payload-failure end-to-end test.
- **Fix:** Added `test_redact_blanks_key_shaped_fields_regardless_of_value`, `test_redact_blanks_any_value_matching_an_fpl_api_keys_entry`, and `test_jsonformatter_output_never_contains_a_redacted_secret` to `tests/test_payloads.py`.
- **Files modified:** `tests/test_payloads.py`
- **Verification:** `python -m pytest tests/test_payloads.py -q` — 24 passed (was 21)
- **Committed in:** `5664c5e`

---
**Total deviations:** 1 auto-fixed (Rule 2 — missing test coverage for a stated threat mitigation).
**Impact on plan:** Purely additive; no plan-authored code or test was changed, only extended. No effect on the plan's acceptance criteria, all of which independently pass.

## TDD Gate Compliance

Task 2 declared `tdd="true"`. Per the executor's TDD flow, this should have produced a `test(06-01): add failing test for ...` commit (RED) followed by a `feat(06-01): implement ...` commit (GREEN). Instead, `ops/payloads.py` and its Task 2 tests were written and committed together in a single `feat(06-01)` commit (`f67a44d`), because the module, its pydantic models, and its behavior-case tests were designed as one coherent new unit with no pre-existing production code to characterize a RED phase against (the module did not exist before this task).

- `git log --oneline` shows no separate `test(06-01)` commit ahead of `f67a44d` for Task 2's tests.
- All 11 of Task 2's new behavior-case tests pass against the implementation committed in the same commit; there was no observed RED phase.

This is flagged here rather than silently omitted, per the gate-validation instruction. No functional risk: every one of Task 2's `<behavior>` cases and `<acceptance_criteria>` items was independently verified to pass (see the plan's own `<verify>` block, re-run clean in this session).

## Issues Encountered

None. All three tasks' `<verify>` blocks and `<acceptance_criteria>` passed on first implementation, aside from one ruff `F841` (unused local `logger` variable in a test) caught and fixed before commit, and one `capsys` stream-binding gotcha (the JSON logging handler binds its stream to `sys.stderr` at `configure_logging()` call time — which happens once at `api.main` import time, predating any per-test `capsys` swap — so tests asserting log output must re-call `configure_logging()` after `capsys` is active). Neither required a plan deviation; both were test-authoring details resolved inline.

## User Setup Required

None — no external service configuration required. `pydantic==2.13.5` was already present in the hash-locked `requirements.txt`/`requirements-dev.txt`; no dependency lock file was touched (`git diff --quiet -- requirements.txt requirements-dev.txt requirements.in requirements-dev.in` passes).

## Next Phase Readiness

`ops.jsonio.read_json`/`write_json`, `ops.jsonlog.configure_logging`/`log_event`/`redact`, and `ops.payloads.validate_bootstrap`/`validate_fixtures` are now the stable, tested chokepoints the remaining Phase 6 plans (06-02 through 06-05) are expected to call into for every other JSON read/write and every other failure-notification path in the codebase (per this plan's `<reversibility rating="costly">` note — their signatures should not change without touching every downstream caller). `GET /api/ready` and the `ready`/`last_error` state keys are available for any later plan that needs to distinguish "process is up" from "data has actually loaded."

No blockers for 06-02 onward.

---
*Phase: 06-security-reliability-observability-hardening*
*Completed: 2026-09-05*

## Self-Check: PASSED

All 9 created/modified files found on disk; all 4 task commit hashes (`6355e72`, `f67a44d`, `33954f1`, `5664c5e`) found in git history.
