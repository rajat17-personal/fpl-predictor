---
phase: 06-security-reliability-observability-hardening
verified: 2026-09-06T11:00:00Z
status: human_needed
score: 5/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "4/5 roadmap success criteria fully verified; 1 partially fails on a confirmed concurrency defect (REL-05)"
  gaps_closed:
    - "A cache entry written against one pool version can never be served after a refresh (roadmap Success Criterion #5, REL-05) — the TOCTOU race between _pool()/_gw_pools_meta()'s pool fetch and a separate pool_version read is closed by making both reads happen inside one critical section (PoolSnapshot/GwPoolsSnapshot returned from _pool()/_gw_pools_meta())"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
human_verification:
  - test: "Open the React dev server (http://localhost:5173) with the API running and exercise the team page's solve button end to end."
    expected: "The solve request succeeds under the FPL_CORS_ORIGINS-restricted CORS policy (default dev origins allow localhost:5173/8000 on both localhost and 127.0.0.1)."
    why_human: "Carried forward unchanged from every prior verification pass — none of 06-06/06-07 touched CORS code (confirmed: `_cors_origins()`/`CORSMiddleware` wiring unchanged; test_api_hardening.py's 8 CORS tests still pass). A restricted CORS list is the one Phase 6 change that can break the real browser path in a way no TestClient/uvicorn-script assertion can reproduce — only an actual browser enforces CORS preflight semantics end to end."
  - test: "Install the daily cron line (30 2 * * * .../scripts/daily.sh) and the weekly cron line (0 8 * * fri .../scripts/weekly.sh) on the host that runs the pipeline, confirm with crontab -l, then deliberately break one step and confirm the FPL_ALERT_WEBHOOK notification lands on a channel actually watched."
    expected: "crontab -l lists both jobs; a deliberately broken scripts/daily.sh run produces a same-day alert on the configured channel."
    why_human: "Carried forward unchanged. 06-USER-SETUP.md (read directly in this session) still lists all three setup items unchecked; `crontab -l` cannot be run from this sandboxed session (denied by the sandbox's permission system on prior sessions, and it is squarely an operator action on the host that runs the pipeline, not a code-verifiable claim). REL-02/OBS-03's 'a failed run is noticed the same day' promise is wiring (verified), not yet live coverage."
---

# Phase 6: Security, Reliability & Observability Hardening Verification Report

**Phase Goal:** The system fails loudly, safely, and visibly instead of silently
**Verified:** 2026-09-06
**Status:** human_needed
**Re-verification:** Yes — after gap-closure plan 06-07 executed to close the REL-05 TOCTOU cache-invalidation race (the sole remaining gap from the prior `gaps_found` verification)

## Goal Achievement

### Gap-Closure Regression Check (item from the prior VERIFICATION.md)

| # | Item | Prior Status | Current Status | Evidence |
|---|------|---------------|-----------------|----------|
| 1 | `api/main.py`'s `/api/solve` and `/api/plan` have a TOCTOU race between fetching a pool and separately re-reading `_state['pool_version']` for the cache key (REL-05) | ⚠ PARTIAL (confirmed defect) | ✓ VERIFIED | `_pool()` and the rewritten `_gw_pools_meta()` each read the pool/pools, gameweek, bootstrap payload and `pool_version` inside ONE locked block and return a `PoolSnapshot`/`GwPoolsSnapshot` `NamedTuple` (`api/main.py:190-217, 360-371, 711-723`, read directly). `team()`, `solve()`, `rate()`, `plan()` consume the snapshot by attribute access and hold no lock and touch no state dict — independently re-derived via an AST walk in this session (see below), not merely re-read from the SUMMARY. |
| 2 | No regression test drove the real `_pool()`/`_refresh()` interleaving; all five pre-existing concurrency tests stubbed `_pool` to a version-independent fixture | Missing | ✓ VERIFIED | Two new tests added: `test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key` (the stub-free gate, asserts `m._pool.__name__ == "_pool"` before driving two real `/api/solve` requests through a deterministic lock-release-triggered refresh) and `test_the_window_hook_opens_a_real_gap_for_a_two_acquisition_reader` (its non-vacuity control). Both re-run in this session and pass (`tests/test_api_hardening.py`, 20 tests total, all pass). |
| 3 | No structural gate stopped the two-acquisition shape from silently returning | Missing | ✓ VERIFIED | `test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict` parses `api/main.py`'s syntax tree and asserts `team`/`solve`/`rate`/`plan` hold no lock and subscript no state dict, plus the critical-section census (`_pool`==1, `_gw_pools_meta`==1, `_gw_pools_locked`==0). Independently re-run in this session as a standalone script (not just via pytest) — see "Independent Re-Derivation" below — with identical results. |

**Independent re-derivation (not trusting the SUMMARY's narration):**

1. **Code read.** `api/main.py:190-217` defines `PoolSnapshot(pool, gw, boot, version)` and `GwPoolsSnapshot(pools, gw, boot, version)` as `NamedTuple`s. `_pool()` (`:360-371`) calls `_refresh()`, then inside one `with _lock:` block builds/fetches the pool and returns `PoolSnapshot(pool, gw, boot, pool_version)` — all four values read together. `_gw_pools_locked()` (`:374-392`, renamed from `_gw_pools`) takes no lock of its own (docstring states the caller must already hold `_lock`) and now runs entirely inside `_gw_pools_meta()`'s (`:711-723`) single `with _lock:` block, which also reads `gw` and `boot` for the first time under lock. `solve()` (`:617-668`) and `plan()`(`:677-708`) each bind one snapshot via `snap.pool/.gw/.boot/.version` or `snap.pools/...` and contain no second lock acquisition — the previously-flagged separate `with _lock: pool_version = _state["pool_version"]` block is gone.
2. **AST re-derivation, run fresh in this session** (not copy-pasted from the plan): parsed `api/main.py`'s syntax tree and confirmed (a) none of `team`, `solve`, `rate`, `plan` contains a `with _lock` block or a `_state[...]` subscript, and (b) the critical-section census is exactly `_pool: 1`, `_gw_pools_meta: 1`, `_gw_pools_locked: 0`. Output: `bad: []`, `census: {'_pool': 1, '_gw_pools_meta': 1, '_gw_pools_locked': 0}`.
3. **Non-vacuity check via a scratch git worktree at the pre-fix commit (21cb2b9)** — copied the *current* `tests/test_api_hardening.py` into that worktree and ran only `test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key` against the pre-fix `api/main.py`. It failed with `AssertionError: STALE PAYLOAD SERVED AFTER A REFRESH: ['G0-1001', 'G0-1002', ...]` — the exact message 06-07-SUMMARY.md claims it observed. Run against the current HEAD, the same test passes. This independently proves the gate is not vacuous: it genuinely distinguishes the fixed code from the defect it was written to close.

### Observable Truths (ROADMAP.md Success Criteria) — Full Re-Verification

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The API accepts requests only from configured origins, and secrets are read from a mode-600 `.env` — never present in code, logs, or workflow files | ✓ VERIFIED (regression) | Unchanged by 06-07. `api/main.py::_cors_origins()` (line 87) reads `FPL_CORS_ORIGINS`, raises on wildcard (re-confirmed by grep in this session). `tests/test_api_hardening.py`'s 8 CORS tests re-run in this session, all pass. |
| 2 | A malformed or changed FPL bootstrap/fixtures payload is rejected by schema validation with an actionable message, and a missing or corrupt export JSON produces a clear error instead of a traceback | ✓ VERIFIED (regression) | Unchanged by 06-07. `tests/test_payloads.py` (24 tests) re-run in this session, all pass. |
| 3 | The daily snapshot and weekly export crons retry on transient failure and surface failures visibly — a failed run is noticed the same day, not discovered weeks later | ✓ VERIFIED (mechanism); ⚠ not yet live | Unchanged by 06-07. `tests/test_cron.py` (22 tests, 1 conditionally skipped) re-run in this session, all pass. `06-USER-SETUP.md` (read directly) confirms cron installation itself remains an outstanding operator action — carried forward as a human-verification item. |
| 4 | The API emits structured JSON request logs and exposes distinct liveness and readiness endpoints | ✓ VERIFIED (regression) | Unchanged by 06-07. `tests/test_obs.py` (15 tests) re-run in this session, all pass. |
| 5 | A long-running API process leaks no file handles, and the solve cache is bounded with correct invalidation under concurrent requests | ✓ VERIFIED | File handles: repo-wide bare-open gate (`tests/test_reliability.py`, 9 tests) re-run, all pass, zero findings. Solve cache bound (`SOLVE_CACHE_MAX=256`, LRU eviction, TTL) verified unchanged. **Cache invalidation is now correct**: the TOCTOU race is closed — `_pool()`/`_gw_pools_meta()` return an atomic `(pool[s], gw, boot, version)` snapshot from one critical section, independently re-derived by direct code reading and AST analysis (above), and proven non-vacuously by reproducing the pre-fix failure in a scratch worktree. |

**Score:** 5/5 roadmap success criteria verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/main.py` | CORS, structured logging, readiness, bounded+correctly-invalidated solve cache | ✓ VERIFIED | All five properties confirmed by direct reading and test re-runs; the previously-partial invalidation guarantee is now fully verified |
| `tests/test_api_hardening.py` | REL-05 bound/eviction/TTL/version-bump tests plus new stub-free race gate, non-vacuity control, multi-gameweek atomicity proof, and AST structural gate | ✓ VERIFIED | 20 tests collected and passing (16 pre-existing + 4 new: `test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key`, `test_the_window_hook_opens_a_real_gap_for_a_two_acquisition_reader`, `test_gw_pools_meta_returns_the_version_its_pools_were_built_under`, `test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict`) |
| `tests/test_api.py`, `tests/test_obs.py`, `tests/test_product.py` | Fourteen `_pool` stub sites updated to return four-field `PoolSnapshot` | ✓ VERIFIED | Full suite passes (170 passed, 1 skipped) — a stale three-value stub would raise a `TypeError` on unpack, so passing is direct evidence the stubs were updated |
| `e2e/scripts/capture_fixtures.py`, `ruff.toml`, `tests/test_reliability.py`, `tests/test_capture_fixtures.py`, `data/ingest.py` | 06-06 gap-closure artifacts (CR-01, lint blind spot) | ✓ VERIFIED (regression) | Unchanged since the prior pass; `ruff check .` still reports `All checks passed!`; `tests/test_reliability.py` and `tests/test_capture_fixtures.py` still pass |
| `ops/jsonio.py`, `ops/jsonlog.py`, `ops/payloads.py`, `ops/notify.py` | Unchanged since prior verification | ✓ VERIFIED (regression) | All associated test files still pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/main.py::_pool()`'s single locked block | `PoolSnapshot.version` → `solve()`'s cache key → `_cache_put` | Atomic snapshot | ✓ WIRED | Confirmed by direct code read: `solve()` destructures `snap.version` and passes it into the same `"pool_version"` JSON key that feeds `hashlib.sha1(...)`; no second lock acquisition exists in `solve()` |
| `api/main.py::_gw_pools_meta()`'s single locked block | `GwPoolsSnapshot.version` → `plan()`'s cache key | Atomic snapshot (multi-gameweek path) | ✓ WIRED | Confirmed by direct code read and by the AST census (`_gw_pools_meta` == 1 lock-held block, `_gw_pools_locked` == 0) |
| the AST gate | `api/main.py`'s four snapshot consumers | Structural regression backstop | ✓ WIRED | Independently re-run in this session as a standalone script outside pytest, output matches `test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict`'s assertions exactly |
| `FPL_CORS_ORIGINS` | `api/main.py::_cors_origins` → `CORSMiddleware` | Browser trust boundary | ✓ WIRED (regression) | `tests/test_api_hardening.py` CORS tests pass |
| `data.snapshot.take_snapshot` | retry loop → `ops.notify.report` | FPL-outage visibility | ✓ WIRED (regression) | `tests/test_cron.py` passes |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `python -m pytest -q` | `170 passed, 1 skipped` | ✓ PASS |
| REL-05 test module in isolation | `pytest -q tests/test_api_hardening.py` | `20 passed` | ✓ PASS |
| REL-05 gate + control by name | `pytest -q tests/test_api_hardening.py -k "never_serves_a_pre_refresh_payload or window_hook_opens_a_real_gap"` | `2 passed` | ✓ PASS |
| Multi-gameweek atomicity + AST gate by name | `pytest -q tests/test_api_hardening.py -k "gw_pools_meta_returns_the_version or snapshot_consumers_hold_no_lock"` | `2 passed` | ✓ PASS |
| Regression bundle (security/reliability/obs/api) | `pytest -q tests/test_api_hardening.py tests/test_payloads.py tests/test_cron.py tests/test_obs.py tests/test_api.py tests/test_reliability.py` | `130 passed, 1 skipped` | ✓ PASS |
| Lint | `ruff check .` | `All checks passed!` | ✓ PASS |
| Preflight | `PREFLIGHT_PYTHON=... bash scripts/preflight.sh` | `PREFLIGHT PASSED` (container gate skipped — no docker/podman on this host, exercised by CI instead) | ✓ PASS |
| Non-vacuity: pre-fix commit reproduces the exact claimed failure | new test copied into a scratch `git worktree` at `21cb2b9` (pre-Task-1), run in isolation | `AssertionError: STALE PAYLOAD SERVED AFTER A REFRESH: ['G0-1001', ...]` | ✓ PASS (confirms gate is non-vacuous, not merely trusting the SUMMARY's quoted message) |
| Debt markers (TBD/FIXME/XXX) in phase-touched files | `grep -rnE "TBD\|FIXME\|XXX" api/main.py tests/test_api_hardening.py tests/test_api.py tests/test_obs.py tests/test_product.py` | no matches | ✓ PASS |
| Dependency/export/fixture/lint-config drift | `git diff --stat 21cb2b9 HEAD -- requirements*.txt requirements*.in web/data e2e/fixtures ruff.toml` | empty | ✓ PASS |
| Commit authenticity | `git log --oneline` shows `aae7503`, `4932b84`, `c0b4f7a` (06-07's three task commits) present in history | matches SUMMARY's claimed hashes | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| SEC-01 | 06-04, 06-05 | CORS restricted to configured origins | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| SEC-03 | 06-03, 06-05 | Secrets via mode-600 `.env`, never in code/logs/workflows | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| REL-01 | 06-01, 06-02, 06-05, 06-06 | All file handles closed via context managers | ✓ SATISFIED | Repo-wide gate empty; unchanged by 06-07 |
| REL-02 | 06-03, 06-05 | Cron retry/backoff, failures visible | ✓ SATISFIED (mechanism); scheduler not yet installed (human item, unchanged) |
| REL-03 | 06-01 | Pydantic schema validation on bootstrap/fixtures | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| REL-04 | 06-01, 06-02, 06-05, 06-06 | Graceful JSON-load failures, actionable messages | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| REL-05 | 06-04, 06-07 | Bounded solve cache, invalidation race fixed | ✓ SATISFIED | TOCTOU race closed; atomic snapshot pattern verified by direct code read, independent AST re-derivation, and non-vacuous worktree reproduction of the pre-fix failure |
| OBS-01 | 06-01, 06-04 | Structured JSON request logging | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| OBS-02 | 06-01 | Liveness/readiness endpoints | ✓ SATISFIED | Regression-checked, unchanged since prior pass |
| OBS-03 | 06-03 | Cron/outage failures surfaced/alertable | ✓ SATISFIED (mechanism); scheduler not yet installed (human item, unchanged) |

Cross-referenced against `.planning/REQUIREMENTS.md`: all 10 IDs assigned to Phase 6 (`SEC-01, SEC-03, REL-01, REL-02, REL-03, REL-04, REL-05, OBS-01, OBS-02, OBS-03`) are claimed by at least one of this phase's seven plans' `requirements:` frontmatter (06-01 through 06-07), and the union of those seven lists is exactly this set — no orphaned requirements. All 10 are now satisfied per the per-requirement table above.

**Note on `.planning/REQUIREMENTS.md` staleness:** its traceability table and checkboxes currently show REL-05 as `[x]`/`Complete` (updated by 06-07's commit) but the other nine Phase 6 requirements still show `[ ]`/`Gaps Found` — a stale blanket marker left over from the original `gaps_found` verification pass that was never individually corrected once those nine were re-verified as SATISFIED (both in the prior `06-VERIFICATION.md` re-verification and again in this session). This is a documentation-hygiene gap in `REQUIREMENTS.md` itself, not a functional gap in the nine requirements — recommend a follow-up doc-only commit to flip those nine checkboxes/table rows to `[x]`/`Complete` before Phase 6 closes out, but it does not block phase completion since this VERIFICATION.md's per-requirement table (independently re-derived, not copied from REQUIREMENTS.md) is authoritative.

### Anti-Patterns Found

Carried forward from `06-REVIEW.md` (2026-09-06), none of which are Phase 6 blocking must-haves, re-confirmed still present/deferred in this session:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `predict/digest.py` | 41 | `r.get("ownership") or 100` treats a genuine `0.0` ownership as falsy | ⚠ Warning | Pre-existing, not a Phase 6 must-have; explicitly deferred by `06-06-PLAN.md` and `06-07-PLAN.md` |
| `ops/jsonio.py` | 47-65 | `write_json` silently narrows every written JSON file to mode 0600 | ⚠ Warning | Pre-existing since 06-01/06-02; explicitly deferred |
| `predict/scoreboard.py` | 39-63 | `score_gw` can raise uncaught `IndexError` on an empty merge | ⚠ Warning | Adjacent to REL-04's theme but outside its literal scope; explicitly deferred |
| `api/main.py` | ~424-428 (line numbers shifted by 06-07's edits; `require_key`) | API-key check is non-constant-time | ℹ️ Info | Pre-existing stub auth; not a SEC-01/SEC-03 must-have; explicitly deferred |
| `predict/scoreboard.py` | 81-82 | bootstrap fetch has none of REL-02's retry/backoff treatment | ⚠ Warning | Not a stated must-have for this phase's plans |
| `predict/digest.py` | 55-56, 86-87 | crashes with `KeyError` on `p10`/`p90` when intervals artifact absent | ⚠ Warning | Cold-start path outside this phase's stated must-haves |
| `ops/jsonlog.py` | 41-54 | `redact()` doesn't recurse into tuples | ⚠ Warning | No current call site logs a tuple-valued field |
| `models/price.py` | 38 | dead `CLASSES` dict | ℹ️ Info | Cosmetic; not a Phase 6 must-have |
| `scripts/daily.sh` / `scripts/weekly.sh` | 34-36, 33-35 | "alerting failed" fallback branch effectively unreachable | ℹ️ Info | Narrower than the message implies, not a Phase 6 must-have |

No new anti-patterns were introduced by 06-07: its diff is two private `NamedTuple` types, one lock-scope refactor, fourteen mechanical stub-return updates, and four new test functions — no bare-open, no empty handler, no hardcoded-empty return, no debt marker.

### Human Verification Required

### 1. Live-browser CORS check

**Test:** Open the React dev server (`http://localhost:5173`) with the API running and exercise the team page's solve button.
**Expected:** The solve request succeeds under the restricted `FPL_CORS_ORIGINS` policy (default dev origins).
**Why human:** Unchanged from every prior verification — a restricted CORS list is the one Phase 6 change that can break the real browser path in a way no `TestClient`/script assertion reproduces.

### 2. Cron install and alert-webhook confirmation

**Test:** Install the daily/weekly cron lines from `06-USER-SETUP.md`, confirm with `crontab -l`, then deliberately break one step and confirm `FPL_ALERT_WEBHOOK` delivers a notification to a channel actually watched.
**Expected:** `crontab -l` lists both jobs; a broken run produces a same-day alert.
**Why human:** `06-USER-SETUP.md` (read directly this session) still lists all three checklist items as unchecked, and this is squarely an operator action on the host that runs the pipeline — no automated gate can install a crontab or confirm a human is watching a notification channel.

### Gaps Summary

No gaps remain. Gap-closure plan 06-07 fully closed the sole outstanding item from the prior `gaps_found` verification: the REL-05 TOCTOU race between `_pool()`/`_gw_pools_meta()`'s pool fetch and a separately-read `pool_version`. This verification independently re-derived the fix rather than trusting 06-07-SUMMARY.md's narrative — by reading `api/main.py` directly, re-running an AST walk over the four handlers and the two snapshot helpers from a fresh Python session, and reproducing the exact pre-fix failure message in a scratch `git worktree` checked out at the pre-fix commit (confirming the new regression test is not vacuous). The full suite (170 passed, 1 skipped), `ruff check .` (`All checks passed!`), and `scripts/preflight.sh` (`PREFLIGHT PASSED`) all re-ran clean in this session.

All 10 of Phase 6's requirements (SEC-01, SEC-03, REL-01 through REL-05, OBS-01 through OBS-03) are now satisfied. `.planning/REQUIREMENTS.md`'s traceability table is stale for nine of them (still shows "Gaps Found" from the original pass) — flagged above as a documentation hygiene item, not a functional gap.

Two items remain correctly deferred to end-of-phase human verification, unchanged from every prior pass: the live-browser CORS check and the cron-scheduler/webhook-confirmation handoff, both outside this repository's reach and both explicitly out of scope for 06-07 (which touched only `api/main.py`'s pool-fetch locking and its test coverage).

---

*Verified: 2026-09-06*
*Verifier: Claude (gsd-verifier)*
