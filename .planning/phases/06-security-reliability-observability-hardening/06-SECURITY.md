---
phase: "06"
slug: "security-reliability-observability-hardening"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-09-07"
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time across 06-01..06-07 `<threat_model>` blocks; verified at ASVS L1 grep depth against the implementation plus the green test suite (170 passed / 1 skipped, 2026-09-07).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| FPL API → pipeline | Untrusted third-party JSON drives every prediction | Public player/fixture data |
| Filesystem → process | Cached/exported JSON may be absent, truncated, or mid-write | Pipeline artifacts, product contract |
| Any browser origin → API | Cross-origin requests reach /api/solve, /api/plan, /api/rate | Solve requests, entry ids |
| Concurrent threads → shared state | `_state` + solve cache mutated by overlapping requests and refresh | Pools, pool_version, cached solves |
| Process → log/webhook sinks | First place a secret can escape a hardened process | Log records, alert records |
| `.env` → process environment | File mode is the whole access control for credentials | FPL_API_KEYS, ODDS_API_KEY, webhook URL |
| Repository → GitHub Actions | Workflow files are public-by-default; an inline secret is permanent | CI configuration |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01-01 | Tampering | predict.live._load_live | high | mitigate | ops.payloads pydantic validation (live+fixture profiles); tests/test_payloads.py | closed |
| T-06-01-02 | DoS | file descriptors, long-lived uvicorn | high | mitigate | with-block reads via ops.jsonio; repo-wide bare-handle gate (tests/test_reliability.py) | closed |
| T-06-01-03 | Info Disclosure | ops.jsonlog records | high | mitigate | redact() blanks key-shaped fields + FPL_API_KEYS values; dedicated redact test suite | closed |
| T-06-01-04 | DoS | /api/health as liveness probe | medium | mitigate | Liveness never acquires pool lock (tests/test_obs.py asserts answer while _lock held) | closed |
| T-06-01-05 | Tampering | write_json interrupted mid-write | medium | mitigate | temp-file + os.replace (ops/jsonio.py:59) | closed |
| T-06-01-06 | Info Disclosure | PayloadError absolute paths | low | accept | Single-tenant; actionable message outweighs disclosure at L1 | closed |
| T-06-01-07 | Spoofing | planted bootstrap-static.json in live cache | low | accept | Requires local FS write = host already compromised | closed |
| T-06-02-01 | DoS | leaked descriptors (24 remaining sites) | high | mitigate | All sites converted; tests/test_reliability.py gates at zero | closed |
| T-06-02-02 | Tampering | web/data/*.json observed mid-write | high | mitigate | Atomic write_json for the product contract | closed |
| T-06-02-03 | Tampering | scoreboard silently replacing corrupt board | medium | mitigate | Corrupt board raises PayloadError; only absent yields fresh board | closed |
| T-06-02-04 | Info Disclosure | --purchase-prices path echoed | low | accept | Operator's own CLI path on single-tenant host | closed |
| T-06-02-05 | Tampering | capture_fixtures.py rewriting v1 capture | medium | mitigate | Script edited, never re-run; git-diff gate on e2e/fixtures | closed |
| T-06-02-06 | Repudiation | silent handler swallowing converted error | medium | mitigate | Corrupt-board raise reaches caller (gated); no default-substitution allowed | closed |
| T-06-03-01 | Info Disclosure | .env on host | high | mitigate | load_dotenv warns on mode != 600 (config.py:42); .env gitignored; .env.example valueless; tested | closed |
| T-06-03-02 | Info Disclosure | alert record POSTed to webhook | high | mitigate | report() passes record through redact() before write/POST; tested | closed |
| T-06-03-03 | Repudiation | cron step failing with no durable record | high | mitigate | run_step() accounting, data/alerts.jsonl append, non-zero exit; live delivery confirmed in 06-UAT.md test 2 | closed |
| T-06-03-04 | DoS | retry loop hammering FPL API | medium | mitigate | Bounded attempts (3), exp backoff + jitter, no retry on non-retryable 4xx | closed |
| T-06-03-05 | Tampering | interrupted snapshot write truncating archive | high | mitigate | temp + os.replace (data/snapshot.py:140); suite-never-writes-snapshots gate | closed |
| T-06-03-06 | DoS | alerting failure aborting the pipeline | medium | mitigate | report() never raises; inner guard on webhook POST (ops/notify.py) | closed |
| T-06-03-07 | Info Disclosure | secret inlined into a workflow file | high | mitigate | Secret-assignment ratio test + preflight Gate 6 credential scan | closed |
| T-06-03-08 | Spoofing | attacker-supplied .env planted on host | low | accept | Requires repo-root write access = host compromise | closed |
| T-06-04-01 | Spoofing | CORS allowing any origin | high | mitigate | _cors_origins() allowlist, wildcard = boot failure (api/main.py:87-113); 8 CORS tests; live-browser pass in 06-UAT.md test 1 | closed |
| T-06-04-02 | DoS | unbounded _solve_cache | high | mitigate | SOLVE_CACHE_MAX=256 LRU + TTL expiry (api/main.py:56) | closed |
| T-06-04-03 | Tampering | stale solve served after refresh | high | mitigate | pool_version in cache key, incremented under _lock; hardened further by 06-07 | closed |
| T-06-04-04 | Info Disclosure | request logs leaking keys/bodies/queries | high | mitigate | Fixed field set, route template not concrete path, redact() on every field | closed |
| T-06-04-05 | Repudiation | no solver call trail | medium | mitigate | One http.request record per request, X-Request-ID echoed | closed |
| T-06-04-06 | DoS | allowed-origin caller exhausting solver CPU | medium | transfer | Rate limiting = PAID-01, deferred to v2 in REQUIREMENTS.md; bounded cache + require_key interim | closed |
| T-06-04-07 | EoP | require_key stub open when key list empty | medium | transfer | Real auth = PAID-02 (v2); Phase 1 three-mode tests pin current behavior | closed |
| T-06-04-08 | Info Disclosure | cors.configured startup record prints origins | low | accept | Origins public by construction; operator debugging value | closed |
| T-06-05-01 | Repudiation | preflight gate passing vacuously | high | mitigate | Scanned-file count printed; skips recorded by name; SKIPPED count asserted ≤2 | closed |
| T-06-05-02 | Info Disclosure | verify_hardening capture holding real key | medium | mitigate | Sentinel FPL_API_KEYS owned by script; EXIT trap removes capture | closed |
| T-06-05-03 | DoS | leaked uvicorn holding verification port | medium | mitigate | EXIT trap kills by PID; post-run listen assertion | closed |
| T-06-05-04 | Spoofing | verification reaching live FPL API | medium | mitigate | FPL_FIXTURE_DIR set unconditionally + source grep assertion | closed |
| T-06-05-05 | Tampering | alerting "complete" with no scheduler | high | transfer | Carried as 06-USER-SETUP.md user_setup; cron install + webhook delivery now confirmed live in 06-UAT.md test 2 (2026-09-07) | closed |
| T-06-06-01 | Repudiation | ruff exclude silently shrinking lint scope | high | mitigate | Set-equality coverage gate vs git ls-files + blanket-exclude control test | closed |
| T-06-06-02 | Repudiation | vacuous gate (empty scan set) | high | mitigate | Non-empty assertions + F821 positive control | closed |
| T-06-06-03 | Tampering | test writing into immutable e2e/fixtures/v1 | high | mitigate | No _capture() call (source grep); git-status-clean assertion after suite | closed |
| T-06-06-04 | Tampering | suppression comment instead of source fix | medium | mitigate | Bare-noqa gate re-run; select list unchanged; preflight forbids ignore-list suppressions | closed |
| T-06-06-05 | Spoofing | gate resolving a different ruff | medium | mitigate | sys.executable -m ruff with --config at repo ruff.toml | closed |
| T-06-06-06 | Info Disclosure | narrowed exclusion exposing untracked path | low | mitigate | Set equality fails both directions; zero leakage measured pre-plan | closed |
| T-06-06-07 | DoS | test reaching live API / model artifact in CI | medium | mitigate | Only --verify invoked; lazy imports never reached (source grep) | closed |
| T-06-07-01 | Spoofing | pre-refresh payload under post-refresh version | high | mitigate | PoolSnapshot/GwPoolsSnapshot from one critical section (api/main.py:190,206); end-to-end gate via /api/solve | closed |
| T-06-07-02 | Repudiation | silent staleness, no runtime trace | high | mitigate | Structural AST gate fails any handler re-acquiring lock or touching state dict | closed |
| T-06-07-03 | Tampering | two-acquisition read re-introduced later | high | mitigate | Syntax-tree gate names offender; four-field snapshot type forces version through | closed |
| T-06-07-04 | Repudiation | regression test passing vacuously | high | mitigate | Control performs old two-acquisition read, asserts version skew observed | closed |
| T-06-07-05 | Repudiation | race proof depending on scheduler luck | medium | mitigate | Single-threaded, sleep-free _WindowLock injection; sleep-timing prohibited | closed |
| T-06-07-06 | DoS | refactor deadlocking every request | high | mitigate | _gw_pools_locked takes no lock (census assertion); concurrency tests + full suite green | closed |
| T-06-07-07 | Tampering | REL-05 test weakened to fit new signature | medium | mitigate | Prohibition + stub-diff restriction; 5 pre-existing REL-05 tests re-run by name | closed |
| T-06-07-08 | Info Disclosure | gates leaking env state / hanging on network | medium | mitigate | From-scratch solve branch only; _load_live substituted; artifact sentinel seeded | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-01-06 | PayloadError paths are local single-tenant locations; actionable messages outweigh disclosure at ASVS L1 | plan 06-01 threat model (plan-time) | 2026-09-07 |
| AR-06-02 | T-06-01-07 | Planted live-cache JSON requires local FS write access, which already implies full host compromise | plan 06-01 threat model (plan-time) | 2026-09-07 |
| AR-06-03 | T-06-02-04 | --purchase-prices path came from the operator's own command line on a single-tenant CLI | plan 06-02 threat model (plan-time) | 2026-09-07 |
| AR-06-04 | T-06-03-08 | Attacker-supplied .env requires repo-root write access = host compromise | plan 06-03 threat model (plan-time) | 2026-09-07 |
| AR-06-05 | T-06-04-08 | CORS origins are public by construction; startup record aids operator debugging | plan 06-04 threat model (plan-time) | 2026-09-07 |

Transfers: T-06-04-06 (rate limiting → PAID-01, v2), T-06-04-07 (real auth → PAID-02, v2) are documented deferrals in REQUIREMENTS.md; T-06-05-05 (scheduler) transferred to operator via 06-USER-SETUP.md and since confirmed live (06-UAT.md test 2).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-07 | 49 | 49 | 0 | gsd-secure-phase (L1 short-circuit: plan-time register, all dispositions verified at grep depth + green suite) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-07
