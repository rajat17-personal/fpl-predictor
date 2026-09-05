---
phase: 06-security-reliability-observability-hardening
verified: 2026-09-05T00:00:00Z
status: gaps_found
score: 5/5 roadmap success criteria verified; 1 unresolved regression blocks a clean pass
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "e2e/scripts/capture_fixtures.py's fixture-capture path runs without crashing"
    status: failed
    reason: "06-02 Task 3 (closing bare file handles in e2e/scripts/capture_fixtures.py) removed the module's `import json` line while adding `from ops.jsonio import read_json, write_json`. Line 133 still calls `json.loads(pool.to_json(orient='records'))` directly (unrelated to the file-handle conversion), so the script's default action — `python e2e/scripts/capture_fixtures.py`, i.e. capturing/refreshing the immutable v1 E2E fixture set — raises `NameError: name 'json' is not defined` on every invocation that isn't `--verify`. Confirmed independently in this verification with `python -m pyflakes e2e/scripts/capture_fixtures.py` (one hit, line 133) and by diffing the import block across 06-02's own commit (f7360ae had `import json`; 08dc692 does not). Already called out as CR-01 (the review's sole critical finding) in 06-REVIEW.md and left unfixed as of the latest commit (69704fc, docs-only). Not caught by any gate because `ruff.toml` excludes `e2e/` from lint and no pytest module covers `capture_fixtures.py`'s capture path (06-02's own plan text explicitly scoped test coverage to the reliability gate, not this script's behavior)."
    artifacts:
      - path: "e2e/scripts/capture_fixtures.py"
        issue: "Missing `import json`; `json.loads(...)` at line 133 raises NameError on the default (non---verify) invocation"
    missing:
      - "Add `import json` back to e2e/scripts/capture_fixtures.py's import block"
      - "Add a regression test (or a project-conventions lint/smoke check that isn't excluded for e2e/) that actually exercises the capture path, since this class of bug currently has zero automated coverage"
deferred: []
human_verification:
  - test: "Open the React dev server (http://localhost:5173) with the API running and exercise the team page's solve button end to end."
    expected: "The solve request succeeds under the new FPL_CORS_ORIGINS-restricted CORS policy (default dev origins allow localhost:5173/8000 on both localhost and 127.0.0.1)."
    why_human: "Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase (06-04-SUMMARY.md's own outstanding item). A restricted CORS list is the one Phase 6 change that can break the real browser path in a way no TestClient/uvicorn-script assertion can reproduce — only an actual browser enforces CORS preflight semantics end to end."
  - test: "Install the daily cron line (30 2 * * * .../scripts/daily.sh) and the weekly cron line (0 8 * * fri .../scripts/weekly.sh) on the host that runs the pipeline, confirm with crontab -l, then deliberately break one step and confirm the FPL_ALERT_WEBHOOK notification lands on a channel actually watched."
    expected: "crontab -l lists both jobs; a deliberately broken scripts/daily.sh run produces a same-day alert on the configured channel."
    why_human: "Per 06-USER-SETUP.md and 06-05-PLAN.md's own <human-check>: crontab -l on this host reports no crontab today, so REL-02/OBS-03's 'a failed run is noticed the same day' promise is wiring, not yet live coverage. Whether an alert is actually noticed is a claim about the operator's attention that no automated gate can verify."
---

# Phase 6: Security, Reliability & Observability Hardening Verification Report

**Phase Goal:** The system fails loudly, safely, and visibly instead of silently
**Verified:** 2026-09-05
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The API accepts requests only from configured origins, and secrets are read from a mode-600 `.env` — never present in code, logs, or workflow files | ✓ VERIFIED | `api/main.py::_cors_origins()` reads `FPL_CORS_ORIGINS`, raises `RuntimeError` naming the variable on a wildcard, defaults to local-dev origins when unset. Live-process proof: `scripts/verify_hardening.sh` (run in this session) shows Gate 1/6 and 2/6 PASS — a denied origin gets no `access-control-allow-origin`; an allowed origin's preflight echoes it exactly. `config.load_dotenv()` never overwrites an already-set env var, warns loudly on any `.env` mode ≠ 0600, `.env` is git-ignored (`git check-ignore -q .env` exits 0) and `.env.example` is tracked with every value empty (verified by direct read). `scripts/preflight.sh` Gate 6 (workflow hygiene, credential-literal scan over 454 tracked files) and Gate 7 (phase 6 hardening) both pass in this session. |
| 2 | A malformed or changed FPL bootstrap/fixtures payload is rejected by schema validation with an actionable message, and a missing or corrupt export JSON produces a clear error instead of a traceback | ✓ VERIFIED | Behaviorally re-proven in this session: mutating the committed fixture bootstrap to remove `elements[0].now_cost` raises `PayloadError: ...elements.0.now_cost: Field required`; setting `elements=[]` raises `PayloadError: ...elements: ... must not be empty`. Separately, calling `predict.digest.build_digest()` against a temp `WEB_DATA` dir with a missing `xp_table.json` raises the existing clean `SystemExit("[digest] run predict.export first")`, and against a syntactically-corrupt `xp_table.json` raises `PayloadError` naming the absolute path, the parse position, and the `python -m predict.export` remedy — no traceback in either case. |
| 3 | The daily snapshot and weekly export crons retry on transient failure and surface failures visibly — a failed run is noticed the same day, not discovered weeks later | ✓ VERIFIED (mechanism); ⚠ not yet live | `data/snapshot.py::take_snapshot` retries on 429/5xx/RequestException with exponential backoff+jitter, does not retry non-retryable 4xx, writes the parquet atomically (`os.replace`), and calls `ops.notify.report` on final failure — all covered by `tests/test_cron.py` (21 tests, all passing in this session). `scripts/daily.sh`/`weekly.sh` use `run_step`/`FAILED`/`NOTIFIED` accounting with zero shell-suppression operators (verified directly: `grep '||'` over both scripts and both workflows returns nothing). The workflows delegate to the shell scripts. The one gap: `crontab -l` reports no crontab on this host, so "noticed the same day" is not yet live — tracked as a human-verification item, per 06-USER-SETUP.md, not a code gap. |
| 4 | The API emits structured JSON request logs and exposes distinct liveness and readiness endpoints | ✓ VERIFIED | `api/main.py` registers an `@app.middleware("http")` handler emitting one `http.request` JSON record per request with `request_id`/`method`/`path` (route template, not concrete path)/`status`/`duration_ms`/`client`, and echoes `X-Request-ID`. Live-process proof: `scripts/verify_hardening.sh` Gate 3/6 (liveness/readiness key-set distinctness) and Gate 4/6 (structured request log) both PASS against a real booted uvicorn. `/api/health` returns exactly `{ok, gw, pool_age_s}` and never blocks on `_lock`; `/api/ready` returns `{ready, reason?, gw, pool_age_s}` and is a genuinely separate code path (`_refresh()`-driven). |
| 5 | A long-running API process leaks no file handles, and the solve cache is bounded with correct invalidation under concurrent requests | ✓ VERIFIED | Repo-wide gate: `! git ls-files '*.py' \| xargs grep -nE bare-open-pattern \| grep -v 'with open('` exits 0 across all tracked Python (re-run directly in this session — empty). `api/main.py` replaces `_solve_cache` with an `OrderedDict`, adds `SOLVE_CACHE_MAX=256`/`SOLVE_CACHE_TTL_S`, `_cache_get`/`_cache_put` as the only two doors (both lock-held), `_state["pool_version"]` incremented under `_refresh`'s lock and folded into both `solve()`'s and `plan()`'s cache keys. `tests/test_api_hardening.py` (16 tests) and the rewritten `tests/test_api.py::test_concurrent_solve_and_refresh` all pass. |

**Score:** 5/5 roadmap success criteria verified as observably true in the codebase.

### Confirmed Regression (blocks a clean pass)

| # | Item | Status | Evidence |
|---|------|--------|----------|
| CR-01 | `e2e/scripts/capture_fixtures.py`'s fixture-capture path runs without crashing | ✗ FAILED | `import json` was removed by 06-02's Task 3 while converting bare `open()` calls to `ops.jsonio`; `json.loads(...)` at line 133 is untouched and still needs it. Confirmed independently in this session with `python -m pyflakes e2e/scripts/capture_fixtures.py` → `undefined name 'json'`, and by diffing the import block between commit `f7360ae` (had `import json`) and `08dc692` (06-02's Task 3 commit, does not). This is the tool that produces/refreshes the immutable v1 E2E fixture set the Playwright suite and `tests/test_fixture_mode.py`/`tests/test_payloads.py` depend on — it currently cannot be re-run to capture a v2 set or repair v1. Already flagged as the sole critical (CR-01) finding in `06-REVIEW.md`; the latest commit since that review (`69704fc`) only adds the review document itself — the bug is unfixed. |

This does not falsify any of the five roadmap success criteria directly (the script's crash is itself a loud, traceback-visible failure, not a silent one — ironically consistent with the phase's own theme), but it is a confirmed, unresolved functional regression in code this phase's own Task 3 modified, with a trivial one-line fix and zero test coverage protecting against its reintroduction. Per the milestone invariant ("every change in this milestone must leave the pipeline... at least as correct... as before") and the review's own unresolved-critical-finding status, it is recorded as a gap rather than waived.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `ops/jsonio.py` | Context-manager read/write, atomic `os.replace` writes, `PayloadError` | ✓ VERIFIED | `read_json`/`write_json`/`PayloadError` present; repo-wide bare-handle gate passes; `tests/test_payloads.py` (24 tests) pass |
| `ops/jsonlog.py` | Structured JSON logging, idempotent handler, `redact()` | ✓ VERIFIED | `JsonFormatter`/`configure_logging`/`log_event`/`redact` present and tested |
| `ops/payloads.py` | Pydantic v2 bootstrap/fixtures validation, live vs fixture profile | ✓ VERIFIED | Behaviorally re-proven in this session (see truth #2 above) |
| `ops/notify.py` | Never-raising `report()`, alert JSONL + optional webhook | ✓ VERIFIED | `tests/test_cron.py` proves swallow-on-raise, redaction, JSONL append |
| `tests/test_reliability.py` | Repo-wide bare-handle regression gate, self-tested | ✓ VERIFIED | 5/5 tests pass in this session (positive control, negative control, sort order, real gate, `what=` label gate) |
| `tests/test_obs.py` | Liveness/readiness, structured request logging | ✓ VERIFIED | 15 tests pass |
| `tests/test_cron.py` | Retry/backoff, atomic writes, `.env`/`load_dotenv`, cron scripts | ✓ VERIFIED | 22 tests pass (1 conditionally skipped — no `.env` on this host) |
| `tests/test_api_hardening.py` | CORS, bounded/versioned cache | ✓ VERIFIED | 16 tests pass |
| `scripts/verify_hardening.sh` | Runtime proof against a real booted process | ✓ VERIFIED | Run directly in this session: all 6 gates PASS, `HARDENING VERIFIED`, no leaked process |
| `.env.example` | Tracked, valueless template | ✓ VERIFIED | Read directly; every line is `KEY=` with no value; git-tracked |
| `e2e/scripts/capture_fixtures.py` | Nine call sites converted to `ops.jsonio`, script still functional | ⚠ STUB-LIKE REGRESSION | I/O conversion done correctly; script itself crashes on its primary (non-`--verify`) action — see CR-01 above |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `predict/live.py::_load_live` | `ops.jsonio.read_json` → `ops.payloads.validate_bootstrap` | Live-path chokepoint | ✓ WIRED | Confirmed by source read and by the digest/scoreboard behavioral tests above |
| `api/main.py::_refresh` | `_state['ready']`/`last_error']` → `GET /api/ready` | Operator-visible failure surface | ✓ WIRED | `/api/ready` and `/api/health` proven distinct via `scripts/verify_hardening.sh` Gate 3/6 against a real process |
| `FPL_CORS_ORIGINS` | `api/main.py::_cors_origins` → `CORSMiddleware` | Browser trust boundary | ✓ WIRED | Verified via real-process Gates 1/6, 2/6 |
| `api/main.py::_refresh` | `_state['pool_version']` → solve cache key | Invalidation-race fix | ✓ WIRED | Code read + `tests/test_api_hardening.py`/`test_api.py::test_concurrent_solve_and_refresh` pass |
| `data.snapshot.take_snapshot` | retry loop → `ops.notify.report` | FPL-outage visibility | ✓ WIRED | `tests/test_cron.py` (9 snapshot/notify tests) pass |
| `scripts/daily.sh run_step` | `ops.notify.report` → `data/alerts.jsonl` + webhook | Cron failure trail | ✓ WIRED | Source read confirms `run_step`/`FAILED`/`NOTIFIED`; no shell suppression in either script or workflow (re-verified directly) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Empty `elements` list rejected | `validate_bootstrap({..., elements: []}, profile='fixture')` | `PayloadError: ...elements: ... must not be empty` | ✓ PASS |
| Missing required field rejected | `validate_bootstrap` with `elements[0].now_cost` deleted | `PayloadError: ...elements.0.now_cost: Field required` | ✓ PASS |
| Missing export file → clean exit | `predict.digest.build_digest()` with `xp_table.json` absent | `SystemExit("[digest] run predict.export first")` | ✓ PASS |
| Corrupt export file → actionable error | `predict.digest.build_digest()` with `xp_table.json` = `"not json{"` | `PayloadError` naming path + parse position + `python -m predict.export` remedy | ✓ PASS |
| `e2e/scripts/capture_fixtures.py` capture path | `python -m pyflakes e2e/scripts/capture_fixtures.py` | `undefined name 'json'` at line 133 | ✗ FAIL (CR-01) |
| Bare file-handle gate, whole tracked tree | `! git ls-files '*.py' \| xargs grep -nE bare-open-pattern \| grep -v 'with open('` | empty (exit 0) | ✓ PASS |
| Full test suite | `python -m pytest -q` | 158 passed, 1 skipped | ✓ PASS |
| Lint | `ruff check .` | All checks passed | ✓ PASS |
| Cron/workflow suppression scan | `grep -vE '^\s*#' scripts/daily.sh scripts/weekly.sh .github/workflows/{daily,weekly}.yml \| grep '\|\|'` | no match | ✓ PASS |
| Fixture/lockfile immutability | `git diff --quiet -- e2e/fixtures`, `git diff --quiet -- requirements*.txt requirements*.in` | both clean | ✓ PASS |

### Probe Execution (`scripts/verify_hardening.sh` — real uvicorn boot on frozen fixtures)

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| `scripts/verify_hardening.sh` (all 6 gates) | `HARDENING_PYTHON=<conda-python> bash scripts/verify_hardening.sh` | 6/6 gates PASS, `HARDENING VERIFIED`, no leaked process | PASS |
| `scripts/preflight.sh` (full 8-gate local CI reproduction, including the above) | `bash scripts/preflight.sh` | `PREFLIGHT PASSED`, 7 gates ran, 2 skipped by name (container runtime absent, no `.env` on this host) | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| SEC-01 | 06-04, 06-05 | CORS restricted to configured origins | ✓ SATISFIED | Real-process gates + tests |
| SEC-03 | 06-03, 06-05 | Secrets via mode-600 `.env`, never in code/logs/workflows | ✓ SATISFIED | `.env.example`, `load_dotenv`, redaction, preflight Gate 6/7 |
| REL-01 | 06-01, 06-02, 06-05 | All file handles closed via context managers | ✓ SATISFIED | Repo-wide gate empty; `tests/test_reliability.py` |
| REL-02 | 06-03, 06-05 | Cron retry/backoff, failures visible | ✓ SATISFIED (mechanism); scheduler not yet installed (human item) |
| REL-03 | 06-01 | Pydantic schema validation on bootstrap/fixtures | ✓ SATISFIED | Behaviorally re-proven in this session |
| REL-04 | 06-01, 06-02, 06-05 | Graceful JSON-load failures, actionable messages | ✓ SATISFIED | Behaviorally re-proven (digest missing/corrupt cases) |
| REL-05 | 06-04 | Bounded solve cache, invalidation race fixed | ✓ SATISFIED | Code + tests |
| OBS-01 | 06-01, 06-04 | Structured JSON request logging | ✓ SATISFIED | Real-process gate |
| OBS-02 | 06-01 | Liveness/readiness endpoints | ✓ SATISFIED | Real-process gate |
| OBS-03 | 06-03 | Cron/outage failures surfaced/alertable | ✓ SATISFIED (mechanism); scheduler not yet installed (human item) |

Cross-referenced against `.planning/REQUIREMENTS.md`: all 10 IDs assigned to Phase 6 (`SEC-01, SEC-03, REL-01, REL-02, REL-03, REL-04, REL-05, OBS-01, OBS-02, OBS-03`) are claimed by at least one of this phase's five plans' `requirements:` frontmatter, and the union of those five lists is exactly this set — no orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `e2e/scripts/capture_fixtures.py` | 133 | Undefined name `json` (missing import, regression from 06-02) | 🛑 Blocker | Breaks the tool's primary (capture) action; unresolved critical finding from `06-REVIEW.md` (CR-01) |
| `predict/digest.py` | 41 | `r.get("ownership") or 100` treats a genuine `0.0` ownership as falsy, excluding the most extreme differential candidate | ⚠ Warning | Pre-existing logic bug, not introduced by Phase 6; noted in `06-REVIEW.md` (WR-01), not gating any Phase 6 success criterion |
| `ops/jsonio.py` | 47-65 | `write_json`'s `tempfile.NamedTemporaryFile` writes mode 0600 regardless of umask; `os.replace` preserves that mode, silently narrowing every `web/data/*.json` and `models/artifacts/*.json` file's permissions | ⚠ Warning | Currently masked because the API and cron run as the same OS user (per README); would break a multi-process/multi-user deployment reading these files directly off disk. Noted in `06-REVIEW.md` (WR-02) |
| `predict/scoreboard.py` | 39-63 | `score_gw` can raise an uncaught `IndexError` (not a `PayloadError`) if the frozen predictions and live actuals share zero rows after an inner merge | ⚠ Warning | Narrower failure mode than "corrupt/missing JSON" (SC #2); noted in `06-REVIEW.md` (WR-03), not independently reproduced in this verification session |
| `api/main.py` | 424-428 | `require_key`'s API-key check is a non-constant-time set-membership test | ℹ️ Info | Pre-existing stub auth, not modified by Phase 6; noted in `06-REVIEW.md` (WR-04) |

### Human Verification Required

### 1. Live-browser CORS check

**Test:** Open the React dev server (`http://localhost:5173`) with the API running and exercise the team page's solve button.
**Expected:** The solve request succeeds under the restricted `FPL_CORS_ORIGINS` policy (default dev origins).
**Why human:** A restricted CORS list is the one Phase 6 change that can break the real browser path in a way no `TestClient`/script assertion reproduces — only a real browser enforces CORS preflight end to end. Deferred to end-of-phase UAT per `workflow.human_verify_mode=end-of-phase` (06-04's own outstanding item).

### 2. Cron install and alert-webhook confirmation

**Test:** Install the daily/weekly cron lines from `06-USER-SETUP.md`, confirm with `crontab -l`, then deliberately break one step and confirm `FPL_ALERT_WEBHOOK` delivers a notification to a channel actually watched.
**Expected:** `crontab -l` lists both jobs; a broken run produces a same-day alert.
**Why human:** `crontab -l` on this host reports no crontab today. "Noticed the same day" is a claim about the operator's attention, not something any automated gate can verify — the plan's own `<human-check>` and threat `T-06-05-05`'s `transfer` disposition say so explicitly.

### Gaps Summary

Every one of the five ROADMAP.md success criteria for Phase 6 is observably true in the codebase, re-proven behaviorally in this session (not merely by re-reading SUMMARY.md's claims): CORS is a boot-refusing configured allowlist, malformed FPL payloads and corrupt export JSON both fail with actionable messages instead of tracebacks, the cron scripts retry/alert/never-suppress, the API emits structured JSON request logs with a genuinely distinct liveness/readiness split, and the solve cache is bounded, LRU-evicted, and pool-version-invalidated under lock. `scripts/verify_hardening.sh` and `scripts/preflight.sh` both pass end to end against a real booted uvicorn process in this session, not just against mocks.

The phase is nonetheless not a clean pass: `06-REVIEW.md`'s sole critical finding (CR-01 — `e2e/scripts/capture_fixtures.py` crashes with `NameError: name 'json' is not defined` on its primary action) is a confirmed, unresolved regression introduced by this phase's own 06-02 Task 3, with a one-line fix and currently zero test coverage protecting against it. It does not falsify any of the five roadmap truths, but it is real, in-scope, phase-introduced breakage that should be closed (add `import json`) before the phase is considered fully done. Two further items are correctly deferred to end-of-phase human verification rather than treated as gaps: the live-browser CORS check and the cron-scheduler/webhook-confirmation handoff, both explicitly out of this repository's reach per the phase's own `<human-check>` blocks.

---

*Verified: 2026-09-05*
*Verifier: Claude (gsd-verifier)*
