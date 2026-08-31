---
phase: "1"
slug: "test-base-layer-app-skeleton"
status: secured
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-08-31"
---

# Phase 1 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| developer workstation → git history | First-ever mass staging of the source tree; blobs are permanent once committed | source code, potential credentials (none found) |
| public package registries → local node_modules / site-packages | npm/pip installs execute registry-controlled code with developer privileges | 13 [SUS]-flagged packages, human-approved |
| test suite → FPL API | Tests must never reach the real third-party API | mocked HTTP only (`responses`, exact-URL registration) |
| browser → dev server → FastAPI | Vite proxy seam for the React rebuild | pipeline JSON, loopback-only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-SC | Tampering | npm + PyPI installs | high | mitigate | blocking-human package gate; verbatim "Approved" in 01-01-SUMMARY.md | closed |
| T-01-01 | Info Disclosure | initial `git add` | high | mitigate | `.gitignore` first commit; explicit paths; zero credential-shaped tracked files | closed |
| T-01-02 | Tampering | node_modules in index | medium | mitigate | ignore rules landed one wave before first `npm install`; 0 tracked matches | closed |
| T-01-03 | DoS | 134MB .deb / 77MB parquet in history | medium | mitigate | ignored; `git log --all -- '*.deb'` empty | closed |
| T-01-04 | Tampering | data/snapshots swept into ignore | medium | mitigate | `!data/snapshots/**` negation; parquet tracked | closed |
| T-02-01 | Info Disclosure | `_refresh` → `_load_live` | medium | mitigate | every test monkeypatches `_load_live`/`_pool` | closed |
| T-02-02 | Tampering | `_state`/`_solve_cache` bleed | medium | mitigate | autouse `_reset_api_state` pre+post; pristine-state assertion | closed |
| T-02-03 | Tampering | `joblib.load` of untracked pickle | high | mitigate | artifact sentinel in conftest; raising-loader test returns 200 | closed |
| T-02-04 | DoS | unanchored `_resolve` scan | low | accept | bounded input behind require_key; rate limiting owned by PAID-01 | closed |
| T-02-05 | Spoofing | open gate during 01-02 tests | low | accept | deliberate; three-mode coverage delivered in 01-03 (tests/test_api.py:365-400) | closed |
| T-03-SC | Tampering | `pip install responses` | high | mitigate | approved pin `>=0.25,<0.27`; installed 0.26.3 | closed |
| T-03-01 | Spoofing | `require_key` bypass | high | mitigate | 9 parametrized cases over both protected endpoints incl. open-gate modes | closed |
| T-03-02 | Info Disclosure | tests reaching real FPL API | medium | mitigate | `@responses.activate`, literal-URL registration only | closed |
| T-03-03 | Info Disclosure | manager PII in fixtures | medium | mitigate | synthetic entry 12345 / "Test FC" / "Test Manager" | closed |
| T-03-04 | Info Disclosure | non-constant-time key compare | low | accept | documented stub; Supabase JWT swap at PAID-02 | closed |
| T-03-05 | DoS | unbounded `_solve_cache` | medium | accept | observable via concurrency test; fix owned by Phase 6 REL-05 | closed |
| T-03-06 | Tampering | loosened test / drive-by impl change | medium | mitigate | `git diff --quiet -- api/main.py` gates held; commits verified clean | closed |
| T-04-SC | Tampering | npm install of [SUS] set | high | mitigate | exact pins in package.json; package-lock.json committed | closed |
| T-04-01 | Tampering | typescript@latest (7.x) | medium | mitigate | `"typescript": "6.0.3"` exact pin, gate reads it back | closed |
| T-04-02 | Info Disclosure | pipeline JSON in dist | medium | mitigate | verify_frontend_build.sh filename comparison; dist has no JSON | closed |
| T-04-03 | Info Disclosure | dev server beyond loopback | medium | mitigate | literal localhost proxy target; no `--host`; uvicorn 127.0.0.1 | closed |
| T-04-04 | Spoofing | hardcoded absolute API base | low | mitigate | relative-path-only fetch helpers; zero env/URL matches in src | closed |
| T-04-05 | DoS | verify script orphaning ports | low | mitigate | trap on EXIT/INT/TERM + port sweep; no listeners remain | closed |
| T-04-06 | Tampering | prototype pollution in dep tree | low | transfer | ESLint security plugins at Phase 5 CI-01 (ROADMAP confirmed) | closed |
| T-05-01 | DoS | one route unmounting SPA | medium | mitigate | per-route errorElement ×8; routeIsolation.test.tsx | closed |
| T-05-02 | Info Disclosure | raw error detail in DOM | medium | mitigate | ErrorState renders copy-contract text only; detail to console.error | closed |
| T-05-03 | Spoofing | undefined view on arbitrary path | low | mitigate | `*` catch-all → NotFoundPage; ROUTES REGISTERED 9 | closed |
| T-05-04 | Tampering | backstop suite deleted/skipped quietly | low | mitigate | Retry-spy exactly-once present; suite-count gate does NOT encode its ≥3 threshold (`grep -Eic` passes on any count ≥1) | open — below high threshold (non-blocking) |
| T-05-05 | Info Disclosure | XSS via unescaped content | low | transfer | React default escaping; no dangerouslySetInnerHTML; ESLint security at Phase 5 CI-01 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01-01 | T-02-04 | Bounded pydantic input behind require_key; O(pool) scan over ~600 rows; rate limiting is v2 (PAID-01) | plan register (user decision) | 2026-08-31 |
| AR-01-02 | T-02-05 | Gate deliberately open in 01-02 to test handler contract; gate coverage delivered in 01-03 | plan register | 2026-08-31 |
| AR-01-03 | T-03-04 | require_key is a documented stub replaced by Supabase JWT at PAID-02; constant-time compare routed to that swap | plan register | 2026-08-31 |
| AR-01-04 | T-03-05 | Unbounded `_solve_cache` made observable here; bounded cache owned by Phase 6 REL-05 | plan register | 2026-08-31 |

---

## Advisory Findings (unregistered, non-blocking)

1. **`npm run typecheck` is a no-op** — `frontend/tsconfig.json` is a solution file (`"files": []`), so `tsc --noEmit` checks zero files. Every "typecheck exits 0" criterion in plans 01-04/01-05 was vacuous; only `tsc -b` (via `npm run build`) catches type errors. Logged in `deferred-items.md`, owner Phase 5 CI-01/CI-02. Recommend registering as a threat in Phase 5.
2. **`verify_dev_proxy.sh` port sweep kills unowned processes** — the `lsof -ti | kill` fallback on ports 8000/5173 is unscoped to script children. Developer-workstation-only impact.
3. **Four caret-range deps deviate from `--save-exact` discipline** — `react`, `react-dom`, `@types/react`, `@types/react-dom` (clean-verdict scaffold defaults; lockfile pins the tree). Phase 5 CI should not assume a uniformly exact manifest.
4. **No `## Threat Flags` section in any Phase 1 SUMMARY.md** — executors declared no new attack surface; absence is a process gap to watch in later phases.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-31 | 29 | 28 | 1 (low, non-blocking) | gsd-security-auditor (opus), ASVS L1, block_on high |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed (T-05-04 is low < block_on: high — tracked, non-blocking)
