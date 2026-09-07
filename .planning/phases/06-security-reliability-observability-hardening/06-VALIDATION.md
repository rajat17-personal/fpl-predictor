---
phase: "06"
slug: "security-reliability-observability-hardening"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-07"
---

# Phase 06 — Validation Strategy

> Per-phase validation contract, reconstructed retroactively from 06-01..06-07 SUMMARY coverage blocks (State B audit, 2026-09-07).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config: `pytest.ini`) on conda env `python314` |
| **Config file** | `pytest.ini` |
| **Quick run command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q tests/test_api_hardening.py tests/test_obs.py tests/test_payloads.py` |
| **Full suite command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q` |
| **Estimated runtime** | ~4 seconds (170 passed, 1 skipped as of 2026-09-07) |

Runtime proof beyond pytest: `HARDENING_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python bash scripts/verify_hardening.sh` boots a real uvicorn process against the frozen `e2e/fixtures/v1/normal` set (SEC-01, SEC-03, REL-04, OBS-01, OBS-02), wired into `scripts/preflight.sh` Gate 7/8.

---

## Sampling Rate

- **After every task commit:** Run the quick command above
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | REL-01, REL-04 | — | Corrupt/missing JSON raises actionable PayloadError; atomic writes | unit | `pytest tests/test_payloads.py` | ✅ | ✅ green |
| 06-01-02 | 01 | 1 | REL-03 | — | Malformed FPL bootstrap/fixtures payload rejected by pydantic validation (live + fixture profiles) | unit | `pytest tests/test_payloads.py` | ✅ | ✅ green |
| 06-01-03 | 01 | 1 | OBS-01, OBS-02 | T-06-01-03 | Structured JSON logs with redact(); distinct /api/health vs /api/ready | unit | `pytest tests/test_obs.py` | ✅ | ✅ green |
| 06-02-01 | 02 | 2 | REL-01 | — | data/model-layer call sites through ops.jsonio; atomic watchlist writes | unit | `pytest tests/test_reliability.py` | ✅ | ✅ green |
| 06-02-02 | 02 | 2 | REL-01, REL-04 | — | predict/e2e/tests call sites converted; what= labels on every read_json | unit | `pytest tests/test_reliability.py` | ✅ | ✅ green |
| 06-02-03 | 02 | 2 | REL-01 | — | Self-tested repo-wide bare-file-handle scanner gates leak inventory at zero | unit | `pytest tests/test_reliability.py` | ✅ | ✅ green |
| 06-03-01 | 03 | 2 | REL-02 | — | Bounded retry + backoff + jitter on snapshot fetch; atomic parquet write | unit | `pytest tests/test_cron.py` | ✅ | ✅ green |
| 06-03-02 | 03 | 2 | REL-02, OBS-03 | — | run_step() per-step accounting, zero shell suppression, never-raising ops.notify with redaction | unit | `pytest tests/test_cron.py` | ✅ | ✅ green |
| 06-03-03 | 03 | 2 | SEC-03 | T-06-03 | Mode-600 .env loader, never overwrites set env vars, .env gitignored | unit | `pytest tests/test_cron.py` | ✅ | ✅ green |
| 06-04-01 | 04 | 2 | SEC-01 | T-06-04 | CORS restricted to configured allowlist; wildcard is a boot failure | unit | `pytest tests/test_api_hardening.py` | ✅ | ✅ green |
| 06-04-02 | 04 | 2 | REL-05 | — | Bounded LRU+TTL solve cache with pool-version invalidation | unit | `pytest tests/test_api_hardening.py tests/test_api.py` | ✅ | ✅ green |
| 06-04-03 | 04 | 2 | OBS-01 | — | One secret-free http.request JSON record per request with X-Request-ID | unit | `pytest tests/test_obs.py` | ✅ | ✅ green |
| 06-05-01 | 05 | 3 | SEC-01, SEC-03, REL-04, OBS-01, OBS-02 | — | Real-uvicorn runtime proof of the hardening surface | integration | `bash scripts/verify_hardening.sh` | ✅ | ✅ green |
| 06-05-02 | 05 | 3 | REL-01, REL-02 | — | preflight.sh Gate 7/8 static hardening checks + verify_hardening | integration | `bash scripts/preflight.sh` | ✅ | ✅ green |
| 06-06-01 | 06 | 4 | REL-01 | — | capture_fixtures.py import restored; ruff excludes subtree-scoped | integration | `ruff check --no-cache .` | ✅ | ✅ green |
| 06-06-02 | 06 | 4 | REL-01 | — | Self-tested lint-coverage gate with positive/negative F821 controls | unit | `pytest tests/test_reliability.py` | ✅ | ✅ green |
| 06-06-03 | 06 | 4 | REL-04 | — | Ruff-independent runtime-object gate over the capture path | unit | `pytest tests/test_capture_fixtures.py` | ✅ | ✅ green |
| 06-07-01 | 07 | 5 | REL-05 | — | PoolSnapshot/GwPoolsSnapshot: pool + version read in one critical section | unit | `pytest tests/test_api.py tests/test_api_hardening.py` | ✅ | ✅ green |
| 06-07-02 | 07 | 5 | REL-05 | — | Deterministic stub-free TOCTOU regression test with non-vacuity control | unit | `pytest tests/test_api.py` | ✅ | ✅ green |
| 06-07-03 | 07 | 5 | REL-05 | — | AST structural gate against the two-acquisition shape returning | unit | `pytest tests/test_api.py` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

All 91 coverage-block verification refs across 06-01..06-07 SUMMARYs report `status: pass`; the full suite runs 170 passed / 1 skipped (2026-09-07).

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live-browser CORS on team page solve flow | SEC-01 | Only a real browser enforces CORS preflight semantics end to end; TestClient cannot | Open http://localhost:5173 with API running; exercise solve button; request succeeds under FPL_CORS_ORIGINS policy. **Confirmed pass in 06-UAT.md test 1 (2026-09-07).** |
| Cron install + alert-webhook delivery | REL-02, OBS-03 | crontab and webhook delivery are operator actions on the pipeline host, outside the repo | Install daily/weekly cron lines per 06-USER-SETUP.md; `crontab -l` lists both; broken daily.sh run produces same-day FPL_ALERT_WEBHOOK notification. **Confirmed pass in 06-UAT.md test 2 (2026-09-07).** |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-07

---

## Validation Audit 2026-09-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

State B reconstruction: no VALIDATION.md existed; requirement→test map rebuilt from SUMMARY coverage blocks and confirmed against a green full-suite run. All 10 phase requirements (SEC-01, SEC-03, REL-01..05, OBS-01..03) have automated coverage; the two inherently-manual behaviors are recorded above and passed UAT.
