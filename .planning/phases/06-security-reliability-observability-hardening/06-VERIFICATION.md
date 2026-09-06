---
phase: 06-security-reliability-observability-hardening
verified: 2026-09-06T06:08:23Z
status: gaps_found
score: 4/5 roadmap success criteria fully verified; 1 partially fails on a confirmed concurrency defect
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "5/5 roadmap success criteria verified; 1 unresolved regression (CR-01) blocked a clean pass"
  gaps_closed:
    - "e2e/scripts/capture_fixtures.py's fixture-capture path runs without crashing (CR-01: missing `import json`)"
    - "ruff.toml's blanket data/e2e exclusions hid 10 tracked Python files from the CI lint gate and preflight Gate 2/8"
  gaps_remaining: []
  regressions:
    - "NEW (not in prior verification's gap list): api/main.py's /api/solve and /api/plan have a TOCTOU race between fetching a pool (_pool()/_gw_pools_meta(), which internally calls _refresh()) and separately re-acquiring the lock to read _state['pool_version'] for the cache key. A _refresh() landing in that window tags an old-pool payload with the new pool_version, making it indistinguishable from a genuinely fresh entry for up to SOLVE_CACHE_TTL_S. Independently confirmed by direct code reading in this session (api/main.py:582-589, 643-652, 330-340) and by reading every test that touches this path (tests/test_api.py and tests/test_api_hardening.py's concurrency tests all monkeypatch `_pool` to a version-independent stub, so none exercises the real race). First reported in the fresh 06-REVIEW.md (2026-09-06) as its sole Critical finding; not present in the prior 06-VERIFICATION.md (2026-09-05) because that verification's Truth #5 evidence relied on the same stubbed concurrency tests plus a source read that did not trace this exact interleaving."
gaps:
  - truth: "A cache entry written against one pool version can never be served after a refresh (roadmap Success Criterion #5, REL-05)"
    status: partial
    reason: "The pool-version invalidation mechanism is real and correctly wired for the case its own tests exercise (a version bump between two requests), but a genuine TOCTOU race exists inside a single request: `_pool(req.horizon)` internally calls `_refresh()` and returns a pool without its version; the handler then does a SEPARATE `with _lock: pool_version = _state['pool_version']` read afterward. If another thread's `_refresh()` (a natural POOL_TTL_S=3600s boundary, or a concurrent request's own `_pool()` call) lands in the gap between those two lock acquisitions, the handler computes its output from the OLD pool but tags it in the cache under the NEW pool_version — indistinguishable from a fresh entry to any later reader. This directly contradicts the must-have's own wording (\"a cache entry written against one pool version can never be served after a refresh\") and the phase's core theme (fails loudly/visibly, never silently) — this is a silent staleness bug with no error, no log line, and no way for a caller to detect it. Confirmed by direct code reading, not merely by trusting 06-REVIEW.md's finding: `_pool()` (api/main.py:330-340) and `_gw_pools_meta()`/`_gw_pools()` (api/main.py:343-356, 677-679) release the lock before returning; `solve()` (api/main.py:582-589) and `plan()` (api/main.py:643-652) each re-enter the lock in a separate statement afterward. Both concurrency tests that exercise this area (`tests/test_api.py`'s helpers and `tests/test_api_hardening.py::test_concurrent_solve_overlapping_refresh_stays_within_bound`) monkeypatch `_pool` itself to a fixed, version-independent stub (`fake_pool`/`slow_pool`), so neither drives the actual `_pool()` code path this bug lives in; `test_payload_cached_before_a_refresh_is_unreachable_after_it` manipulates the cache dict directly and never calls `solve()`/`plan()` at all."
    artifacts:
      - path: "api/main.py"
        issue: "solve() (lines ~582-589) and plan() (lines ~643-652) fetch the pool and the pool_version in two separate, non-atomic critical sections; _pool()/_gw_pools_meta() (lines 330-340, 677-679) don't return the version they read under their own lock"
    missing:
      - "Return pool_version from _pool()/_gw_pools_meta() (and _gw_pools()) themselves, read inside the same locked block that reads the pool, so solve()/plan() use one atomic (pool, version) pair instead of two separate lock acquisitions"
      - "A regression test that does NOT stub _pool() — drives the real _pool()/_refresh() interleaving with a timing hook (e.g. a monkeypatched _refresh that sleeps between the pool-cache write and the pool_version bump) to prove the race is closed, not merely that a version bump between two separate requests invalidates correctly"
deferred: []
human_verification:
  - test: "Open the React dev server (http://localhost:5173) with the API running and exercise the team page's solve button end to end."
    expected: "The solve request succeeds under the FPL_CORS_ORIGINS-restricted CORS policy (default dev origins allow localhost:5173/8000 on both localhost and 127.0.0.1)."
    why_human: "Carried forward unchanged from the prior verification (06-06 did not touch CORS code). Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase (06-04-SUMMARY.md's own outstanding item). A restricted CORS list is the one Phase 6 change that can break the real browser path in a way no TestClient/uvicorn-script assertion can reproduce — only an actual browser enforces CORS preflight semantics end to end."
  - test: "Install the daily cron line (30 2 * * * .../scripts/daily.sh) and the weekly cron line (0 8 * * fri .../scripts/weekly.sh) on the host that runs the pipeline, confirm with crontab -l, then deliberately break one step and confirm the FPL_ALERT_WEBHOOK notification lands on a channel actually watched."
    expected: "crontab -l lists both jobs; a deliberately broken scripts/daily.sh run produces a same-day alert on the configured channel."
    why_human: "Carried forward unchanged — `crontab -l` could not be checked in this session (command denied by the sandbox's permission system), and 06-USER-SETUP.md/06-05-PLAN.md's own <human-check> already flag this as unresolved: REL-02/OBS-03's 'a failed run is noticed the same day' promise is wiring, not yet live coverage. Whether an alert is actually noticed is a claim about the operator's attention that no automated gate can verify."
---

# Phase 6: Security, Reliability & Observability Hardening Verification Report

**Phase Goal:** The system fails loudly, safely, and visibly instead of silently
**Verified:** 2026-09-06
**Status:** gaps_found
**Re-verification:** Yes — after gap-closure plan 06-06 executed to close CR-01 (missing `import json`) and the lint blind spot (`ruff.toml` excluding whole directories)

## Goal Achievement

### Gap-Closure Regression Check (items from the prior VERIFICATION.md)

| # | Item | Prior Status | Current Status | Evidence |
|---|------|---------------|-----------------|----------|
| 1 | `e2e/scripts/capture_fixtures.py`'s fixture-capture path runs without crashing (CR-01) | ✗ FAILED | ✓ VERIFIED | `import json` restored at line 20 (read directly). `python -m pyflakes e2e/scripts/capture_fixtures.py` exits 0, no output. |
| 2 | Lint blind spot: `ruff.toml` excluded whole `data`/`e2e` directories, hiding 10 tracked files from CI lint and preflight Gate 2/8 | ✗ FAILED (implicit, part of CR-01's root cause) | ✓ VERIFIED | `ruff.toml`'s `exclude` list is now 13 subtree-scoped entries (`data/raw`, `data/processed`, `data/snapshots`, `e2e/node_modules`, `e2e/fixtures`, `e2e/playwright-report`, `e2e/test-results`, plus originals) — no whole-source-directory entries remain. `ruff check .` reports `All checks passed!` against all 55 tracked Python files. |
| 3 | Regression coverage for both of the above | Missing (0 coverage) | ✓ VERIFIED | `tests/test_reliability.py` gained 4 new tests (`test_ruff_check_covers_every_tracked_python_file`, `test_coverage_gate_notices_a_reinstated_blanket_exclude`, `test_ruff_detects_an_undefined_name`, `test_ruff_reports_nothing_for_a_clean_module`) — all pass. `tests/test_capture_fixtures.py` (new, 4 tests) exercises the capture script's import, its `--verify` CLI path, and a ruff-independent opcode walk proving no undefined global remains on the capture path — all pass. |

**Full suite in this session:** `python -m pytest -q` → `166 passed, 1 skipped` (matches 06-06-SUMMARY.md's claim exactly). `ruff check .` → `All checks passed!`. `bash scripts/preflight.sh` not re-run in full this session (its constituent gates — lint, pytest, hardening — were re-run individually above and all pass); its behavior is unchanged by 06-06 except for the widened ruff scope, which is directly verified.

### Observable Truths (ROADMAP.md Success Criteria) — Full Re-Verification

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The API accepts requests only from configured origins, and secrets are read from a mode-600 `.env` — never present in code, logs, or workflow files | ✓ VERIFIED (regression check) | Unchanged by 06-06. `api/main.py::_cors_origins()` reads `FPL_CORS_ORIGINS`, raises on wildcard. `tests/test_api_hardening.py`'s 8 CORS tests re-run in this session, all pass. |
| 2 | A malformed or changed FPL bootstrap/fixtures payload is rejected by schema validation with an actionable message, and a missing or corrupt export JSON produces a clear error instead of a traceback | ✓ VERIFIED (regression check) | Unchanged by 06-06. `tests/test_payloads.py` (24 tests) re-run in this session, all pass. |
| 3 | The daily snapshot and weekly export crons retry on transient failure and surface failures visibly — a failed run is noticed the same day, not discovered weeks later | ✓ VERIFIED (mechanism); ⚠ not yet live | Unchanged by 06-06. `tests/test_cron.py` (22 tests, 1 conditionally skipped — no `.env` on this host) re-run in this session, all pass. Cron installation itself remains unverified — carried forward as a human-verification item (crontab check was denied by the sandbox in this session). |
| 4 | The API emits structured JSON request logs and exposes distinct liveness and readiness endpoints | ✓ VERIFIED (regression check) | Unchanged by 06-06. `tests/test_obs.py` (15 tests) re-run in this session, all pass. |
| 5 | A long-running API process leaks no file handles, and the solve cache is bounded with correct invalidation under concurrent requests | ⚠ PARTIAL — file-handle half verified; cache-invalidation half has a confirmed defect | File handles: repo-wide bare-open gate (`tests/test_reliability.py`) still empty; re-verified directly, `! git ls-files '*.py' \| xargs grep -nE <bare-open-pattern> \| grep -v 'with open('` returns nothing. Solve cache bound (`SOLVE_CACHE_MAX=256`, LRU eviction, TTL) verified — `tests/test_api_hardening.py::test_cache_bounded_at_max_entries` and `::test_cache_eviction_is_least_recently_used_not_least_recently_inserted` pass. **Cache invalidation is NOT fully correct**: a confirmed TOCTOU race in `api/main.py`'s `solve()`/`plan()` handlers can tag a stale (pre-refresh) payload with the post-refresh `pool_version`, defeating the exact guarantee this success criterion states. See Gaps below. |

**Score:** 4/5 roadmap success criteria fully verified; success criterion #5 is half-verified (file handles clean) and half-failed (cache invalidation has a confirmed, unresolved race).

### New Finding: Confirmed Cache-Invalidation Race (REL-05)

`06-REVIEW.md` (fresh code review, 2026-09-06) reports one Critical finding: a TOCTOU race in `/api/solve` and `/api/plan` between fetching a pool (which internally calls `_refresh()`) and separately re-reading `_state["pool_version"]` for the cache key. This verification independently confirmed the finding by direct code reading rather than trusting the review's narrative:

- `api/main.py::_pool()` (lines 330-340) calls `_refresh()`, then briefly re-acquires `_lock` to read the cached pool, and **returns without the version** it read it under.
- `api/main.py::_gw_pools_meta()`/`_gw_pools()` (lines 343-356, 677-679) have the identical shape.
- `api/main.py::solve()` (lines 582-589) calls `_pool(req.horizon)`, THEN does a second, separate `with _lock: pool_version = _state["pool_version"]` read — a distinct critical section from the one inside `_pool()`.
- `api/main.py::plan()` (lines 643-652) has the identical shape against `_gw_pools_meta()`.
- If a `_refresh()` (natural `POOL_TTL_S=3600` boundary, or another thread's `_pool()` call) lands between `_pool()`'s return and the handler's own `pool_version` read, the handler computes its payload from the OLD pool but stores it in the cache tagged with the NEW `pool_version` — a stale payload that is indistinguishable from a genuinely fresh one to any subsequent request that hashes to the same key, for up to `SOLVE_CACHE_TTL_S`.
- Verified that no existing test exercises this real interleaving: `tests/test_api.py`'s `fake_pool`/monkeypatched-`_pool` helper (used by every test in that file) and `tests/test_api_hardening.py::test_concurrent_solve_overlapping_refresh_stays_within_bound`'s `slow_pool` stub both replace `_pool` with a version-independent function, and `tests/test_api_hardening.py::test_payload_cached_before_a_refresh_is_unreachable_after_it` manipulates the cache dict directly without ever calling `solve()`/`plan()`.

**Decision:** This is treated as a genuine gap against roadmap Success Criterion #5 and requirement REL-05, not an acceptable residual risk, for three reasons: (1) the must-have text itself ("a cache entry written against one pool version can never be served after a refresh... is what makes that unreachable") is unconditional, and the implementation does not make it unreachable — only rare; (2) it is a silent failure mode with zero error surface, which is precisely the class of bug this entire phase exists to eliminate ("fails loudly, safely, and visibly instead of silently"); (3) the fix is a small, well-scoped, single-file change (return the version from inside `_pool`'s/`_gw_pools_meta`'s own locked block) with a clear test strategy, not an open-ended redesign — deferring it would leave a known, documented, silently-triggerable staleness bug in the exact subsystem this phase's own 06-04 plan was written to close.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `e2e/scripts/capture_fixtures.py` | Capture path runs without NameError | ✓ VERIFIED | `import json` present; `pyflakes` clean |
| `ruff.toml` | Subtree-scoped exclusions, no whole-directory hides | ✓ VERIFIED | 13 subtree entries; header comment documents the CR-01 rationale |
| `tests/test_reliability.py` | Self-tested lint-coverage gate + bare-handle gate | ✓ VERIFIED | 9 tests pass (5 pre-existing + 4 new) |
| `tests/test_capture_fixtures.py` | Ruff-independent runtime-object gate over the capture script | ✓ VERIFIED | 4 tests pass, new file |
| `data/ingest.py` | Dead `import json` removed (precondition for clean narrowed-exclusion lint) | ✓ VERIFIED | Confirmed via commit `5a093d7` diff and current lint-clean state |
| `ops/jsonio.py`, `ops/jsonlog.py`, `ops/payloads.py`, `ops/notify.py` | Unchanged since prior verification | ✓ VERIFIED (regression) | All associated test files still pass |
| `api/main.py` | CORS, structured logging, readiness, bounded solve cache | ⚠ PARTIAL | CORS/logging/readiness/bound all verified; invalidation has the confirmed race above |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `e2e/scripts/capture_fixtures.py` | `json.loads(...)` at (was) line 133 | stdlib import | ✓ WIRED | `import json` present; verified by pyflakes and direct read |
| `ruff.toml` exclude list | `git ls-files '*.py'` | subtree-scoped, not directory-scoped | ✓ WIRED | `tests/test_reliability.py::test_ruff_check_covers_every_tracked_python_file` passes |
| `api/main.py::_refresh` | `_state['pool_version']` → solve cache key | Invalidation guarantee | ⚠ PARTIAL | Wired for the inter-request case (version bump between two requests correctly invalidates); NOT wired atomically for the intra-request case (`_pool()` return → handler's separate lock re-acquisition) — see gap above |
| `FPL_CORS_ORIGINS` | `api/main.py::_cors_origins` → `CORSMiddleware` | Browser trust boundary | ✓ WIRED (regression) | `tests/test_api_hardening.py` CORS tests pass |
| `data.snapshot.take_snapshot` | retry loop → `ops.notify.report` | FPL-outage visibility | ✓ WIRED (regression) | `tests/test_cron.py` passes |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `e2e/scripts/capture_fixtures.py` no longer raises NameError | `python -m pyflakes e2e/scripts/capture_fixtures.py` | exit 0, no output | ✓ PASS |
| `ruff.toml` exclusions no longer hide tracked source | `ruff check .` | `All checks passed!` | ✓ PASS |
| Full suite | `python -m pytest -q` | `166 passed, 1 skipped` | ✓ PASS |
| Gap-closure tests in isolation | `pytest -q tests/test_reliability.py tests/test_capture_fixtures.py` | `13 passed` | ✓ PASS |
| Security/reliability/obs/api regression bundle | `pytest -q tests/test_api_hardening.py tests/test_payloads.py tests/test_cron.py tests/test_obs.py tests/test_api.py` | `117 passed, 1 skipped` | ✓ PASS |
| Cache-invalidation race, real `_pool()` path | (no test exists) | N/A — confirmed absent by reading every concurrency test's fixtures | ✗ GAP (no coverage; bug confirmed by code reading, not by a failing test) |
| Debt markers (TBD/FIXME/XXX) in phase-touched files | `grep -rnE "TBD\|FIXME\|XXX" ops/ api/main.py e2e/scripts/capture_fixtures.py tests/test_reliability.py tests/test_capture_fixtures.py ruff.toml data/ingest.py` | no matches | ✓ PASS |
| Commit authenticity | `git show --stat 5a093d7 b67904c 4f5da63` | all three commits exist, match claimed file changes and descriptions | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| SEC-01 | 06-04, 06-05 | CORS restricted to configured origins | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| SEC-03 | 06-03, 06-05 | Secrets via mode-600 `.env`, never in code/logs/workflows | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| REL-01 | 06-01, 06-02, 06-05, 06-06 | All file handles closed via context managers | ✓ SATISFIED | Repo-wide gate empty; 06-06 additionally widened the lint gate that protects this guarantee |
| REL-02 | 06-03, 06-05 | Cron retry/backoff, failures visible | ✓ SATISFIED (mechanism); scheduler not yet installed (human item, unchanged) |
| REL-03 | 06-01 | Pydantic schema validation on bootstrap/fixtures | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| REL-04 | 06-01, 06-02, 06-05, 06-06 | Graceful JSON-load failures, actionable messages | ✓ SATISFIED | Regression-checked; 06-06 added `tests/test_capture_fixtures.py` behavioral coverage |
| REL-05 | 06-04 | Bounded solve cache, invalidation race fixed | ✗ NOT FULLY SATISFIED | Bound is real and tested; invalidation has a confirmed, unresolved TOCTOU race — see gap above |
| OBS-01 | 06-01, 06-04 | Structured JSON request logging | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| OBS-02 | 06-01 | Liveness/readiness endpoints | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| OBS-03 | 06-03 | Cron/outage failures surfaced/alertable | ✓ SATISFIED (mechanism); scheduler not yet installed (human item, unchanged) |

Cross-referenced against `.planning/REQUIREMENTS.md`: all 10 IDs assigned to Phase 6 (`SEC-01, SEC-03, REL-01, REL-02, REL-03, REL-04, REL-05, OBS-01, OBS-02, OBS-03`) are claimed by at least one of this phase's six plans' `requirements:` frontmatter (06-01 through 06-06), and the union of those six lists is exactly this set — no orphaned requirements. `.planning/REQUIREMENTS.md`'s traceability table currently shows all ten as "Gaps Found" (a phase-level blanket marker from the prior `gaps_found` verification, not updated per-requirement); this verification's per-requirement table above is the authoritative status as of this session — nine of ten are satisfied, REL-05 remains gapped for the reason above.

### Anti-Patterns Found

Carried forward from `06-REVIEW.md` (2026-09-06), none of which are Phase 6 blocking must-haves but are recorded for completeness:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/main.py` | 582-589, 647-652, 330-340 | TOCTOU race between pool fetch and pool_version read (see gap above) | 🛑 Blocker (for REL-05 specifically) | Silent stale-cache serving; violates the phase's core "fail loudly, not silently" theme |
| `predict/digest.py` | 41 | `r.get("ownership") or 100` treats a genuine `0.0` ownership as falsy | ⚠ Warning | Pre-existing, not a Phase 6 must-have; noted in `06-REVIEW.md` (WR-01), explicitly deferred by `06-06-PLAN.md` |
| `ops/jsonio.py` | 47-65 | `write_json` silently narrows every written JSON file to mode 0600 | ⚠ Warning | Pre-existing since 06-01/06-02; noted in `06-REVIEW.md` (WR-02), explicitly deferred by `06-06-PLAN.md`; not a stated must-have |
| `predict/scoreboard.py` | 39-63 | `score_gw` can raise uncaught `IndexError` on an empty merge | ⚠ Warning | Adjacent to REL-04's theme but outside its literal scope (valid-JSON schema-drift case, not a load failure); noted in `06-REVIEW.md` (WR-03), explicitly deferred |
| `api/main.py` | 424-428 | `require_key`'s API-key check is non-constant-time | ℹ️ Info | Pre-existing stub auth; not a SEC-01/SEC-03 must-have; noted in `06-REVIEW.md` (WR-04), explicitly deferred |
| `predict/scoreboard.py` | 81-82 | bootstrap fetch has none of REL-02's retry/backoff treatment | ⚠ Warning | New finding in fresh review (WR-05); not a stated must-have for this phase's plans |
| `predict/digest.py` | 55-56, 86-87 | crashes with `KeyError` on `p10`/`p90` when intervals artifact absent | ⚠ Warning | New finding in fresh review (WR-06); a cold-start path outside the specific must-haves this phase's plans stated |
| `ops/jsonlog.py` | 41-54 | `redact()` doesn't recurse into tuples, understating its docstring guarantee | ⚠ Warning | New finding in fresh review (WR-07); no current call site logs a tuple-valued field |
| `models/price.py` | 38 | dead `CLASSES` dict | ℹ️ Info | Cosmetic; not a Phase 6 must-have |
| `scripts/daily.sh` / `scripts/weekly.sh` | 34-36, 33-35 | "alerting failed" fallback branch effectively unreachable | ℹ️ Info | `ops.notify.report`'s CLI wrapper always returns 0; narrower than the message implies, not a Phase 6 must-have |

### Human Verification Required

### 1. Live-browser CORS check

**Test:** Open the React dev server (`http://localhost:5173`) with the API running and exercise the team page's solve button.
**Expected:** The solve request succeeds under the restricted `FPL_CORS_ORIGINS` policy (default dev origins).
**Why human:** Unchanged from prior verification — a restricted CORS list is the one Phase 6 change that can break the real browser path in a way no `TestClient`/script assertion reproduces.

### 2. Cron install and alert-webhook confirmation

**Test:** Install the daily/weekly cron lines from `06-USER-SETUP.md`, confirm with `crontab -l`, then deliberately break one step and confirm `FPL_ALERT_WEBHOOK` delivers a notification to a channel actually watched.
**Expected:** `crontab -l` lists both jobs; a broken run produces a same-day alert.
**Why human:** `crontab -l` could not even be run in this verification session (denied by the sandbox's permission system) — this is squarely an operator-side action no automated gate can perform or verify.

### Gaps Summary

Gap-closure plan 06-06 fully closed the prior verification's blocking finding: `e2e/scripts/capture_fixtures.py` no longer raises `NameError` on its default action (`import json` restored), and the `ruff.toml` blind spot that let that regression ship unnoticed is closed (subtree-scoped exclusions, all 55 tracked Python files now covered by `ruff check .`), with two new regression gates (`tests/test_reliability.py`'s lint-coverage test, `tests/test_capture_fixtures.py`'s ruff-independent opcode check) protecting against recurrence. The full suite (166 passed, 1 skipped) and lint (`All checks passed!`) confirm this directly, not merely by re-reading 06-06-SUMMARY.md's claims.

However, a fresh code review conducted the same day (`06-REVIEW.md`) surfaced a new, previously-undetected Critical finding — a TOCTOU race in `api/main.py`'s `/api/solve` and `/api/plan` handlers between fetching a pool and separately reading `_state['pool_version']` for the cache key — and this verification independently confirmed it by direct code reading (not by trusting the review) and by reading every test that touches the affected code path (all of them stub `_pool` to a version-independent fixture, so none exercises the real race). This bug directly contradicts roadmap Success Criterion #5's "correct invalidation" clause and requirement REL-05's must-have text, and it is exactly the kind of silent failure mode this phase exists to eliminate: a stale cached payload can be served under a cache key that claims to be current, with zero error, zero log signal, and no way for a caller to detect it. The fix is small and well-scoped (return `pool_version` from inside `_pool()`'s/`_gw_pools_meta()`'s own locked block rather than re-reading it in a second, separate critical section), so this is recorded as a gap requiring closure rather than an accepted residual risk — consistent with the milestone's own invariant that every change must leave the system "at least as correct... as before," and this bug lives in code this phase's own 06-04 plan introduced specifically to fix invalidation.

Two items remain correctly deferred to end-of-phase human verification, unchanged from the prior pass: the live-browser CORS check and the cron-scheduler/webhook-confirmation handoff, both outside this repository's reach.

---

*Verified: 2026-09-06*
*Verifier: Claude (gsd-verifier)*
