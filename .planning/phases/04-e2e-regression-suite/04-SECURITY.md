---
phase: "04"
slug: "e2e-regression-suite"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-11"
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time across all 8 plans; verified retroactively at L1 (grep-depth) on 2026-09-11.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| process env → API data source | `FPL_FIXTURE_DIR` decides whether real users get live or frozen data | mode switch, no user data |
| filesystem → API responses | committed fixture JSON becomes API response bodies verbatim | public FPL data + manager fields |
| upstream FPL API → committed git history | third-party personal data crosses into a permanent public record | manager name fields (scrubbed) |
| npm registry → repo | Playwright devDependency + Chromium binary enter the build | third-party code |
| Playwright process → host ports | webServer binds local ports (8100+) and spawns uvicorn | local traffic only |
| normal fixture set → variant sets | `synthesize-variants.mjs` derives committed test data from committed test data | derived public data |
| browser form input → `/api/solve` / `/api/rate` / `/api/plan` | user-controlled entry id, transfer counts, horizon, lock/exclude arrays | untrusted user input |
| `api.main` → `predict.live` module globals | fixture-mode rebinding of `_gw_pool` outlives any single request | process state |
| frozen JSON → rendered DOM | fixture/export fields (incl. free-text `news`, manager fields) become page content | untrusted-shaped text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Tampering | `api/main.py` fixture-mode branch | high | mitigate | `[fixture-mode]` startup banner (api/main.py:76); `tests/test_fixture_mode.py::test_unset_env_leaves_a_single_root_mount` asserts production default | closed |
| T-04-02 | Information Disclosure | committed entry summary fixture | high | mitigate | Checkpoint-approved `scrub-names` policy recorded in `e2e/fixtures/v1/MANIFEST.md`; `player_first_name`/`player_last_name` are empty strings in committed `summary.json` (verified) | closed |
| T-04-03 | Tampering | entry-scoped fixture file paths | low | accept | FastAPI-coerced `int` path param; no traversal possible | closed |
| T-04-04 | Spoofing | `dist/404.html` SPA fallback | low | accept | Starlette `html=True` mechanism; Phase 7 follow-up recorded | closed |
| T-04-05 | Information Disclosure | committed frozen pool/export JSON | low | accept | All values already public on the site's own `web/data/*.json` | closed |
| T-04-SC | Tampering | `npm install @playwright/test` | high | mitigate | Human package-legitimacy checkpoint; exact pin `"@playwright/test": "1.62.1"` in `e2e/package.json`; `e2e/package-lock.json` committed | closed |
| T-04-06 | Spoofing | `reuseExistingServer` port adoption | medium | mitigate | `playwright.config.ts` base port 8100 with deliberate not-8000 comment; smoke spec asserts frozen-fixture values | closed |
| T-04-07 | Information Disclosure | Playwright report/traces | low | accept | `e2e/playwright-report/` and `e2e/test-results/` gitignored (.gitignore:46-47, verified via `git check-ignore`); content is committed fixture data only | closed |
| T-04-08 | Denial of Service | real ILP solves in browser tests | low | accept | Per-test timeouts bound every run | closed |
| T-04-09 | Tampering | `synthesize-variants.mjs` write targets | medium | mitigate | Script writes only to `fixtures/v1/{blank,dgw}/web-data/` (verified); normal capture asserted unchanged via `git diff --quiet` gate | closed |
| T-04-10 | Tampering | variant/spec literal drift | medium | mitigate | Determinism gate (re-run leaves porcelain clean); MANIFEST.md records BLANK/DOUBLE club lists (MANIFEST.md:134-141) | closed |
| T-04-11 | Information Disclosure | synthesised fixture content | low | accept | Derived from already-public export data; no new fields | closed |
| T-04-12 | Denial of Service | three uvicorn processes per run | low | accept | `E2E_VARIANTS=0` single-server mode for focused work | closed |
| T-04-13 | Tampering | `news`/`name` fields rendered to DOM | low | accept | React escapes text children; no HTML-injecting API used | closed |
| T-04-14 | Tampering | formatting/ordering regression | medium | mitigate | `xp-table.spec.ts` exact-literal cell assertions + both sort directions, tie stability, null placement (verified) | closed |
| T-04-15 | Information Disclosure | xP table page | low | accept | Renders only already-public export data | closed |
| T-04-16 | Tampering | entry-id input reaching API | medium | mitigate | `team-solver.spec.ts:104` asserts empty/non-numeric input fires no request; server 404 for unknown id asserted (ASVS V5 control) | closed |
| T-04-17 | Denial of Service | horizon/transfer-count knobs → ILP | medium | mitigate | `team-solver.spec.ts:340-341` asserts rendered `min`/`max` attributes match server request-model bounds; server validates independently | closed |
| T-04-18 | Tampering | lock/exclude as names vs codes | medium | mitigate | `team-solver.spec.ts:303` asserts locked players present and excluded player absent in response | closed |
| T-04-19 | Denial of Service | two-gameweek plan solve hanging CI | low | accept | Plan test raises only its own timeout; global stays low (`team-plan.spec.ts` header) | closed |
| T-04-20 | Repudiation | silent solver recommendation change | medium | mitigate | Single pinned golden with named "REPIN POINT" (`team-solver.spec.ts:418-426`) | closed |
| T-04-21 | Tampering | URL entry id → rate endpoint | medium | mitigate | `parseEntry` rejects non-numeric/non-positive pre-fetch; `rate-my-team.spec.ts` asserts no-entry prompt and server-side 404 path | closed |
| T-04-22 | Information Disclosure | manager name/rank in heading | high | mitigate | `rate-my-team.spec.ts` asserts exactly the scrub-names policy output (`manager.manager` is `""`, heading is bare team name); a widened capture fails the assertion | closed |
| T-04-23 | Denial of Service | rating runs two ILP solves | low | accept | Bounded by per-test timeout; frozen single-GW pool completes in seconds | closed |
| T-04-24 | Tampering | swap line vs best-move tile divergence | low | mitigate | Spec asserts both against the same captured response | closed |
| T-04-07-01 | Tampering | `api/main.py` → `predict.live._gw_pool` leak | high | mitigate | `hasattr`-guarded capture of `_gw_pool_production` ahead of fixture branch + explicit else-arm restore (api/main.py:313-330); identity assertion in `tests/test_fixture_mode.py` (CR-01 fix) | closed |
| T-04-07-02 | Spoofing | `FPL_FIXTURE_DIR` in deployed process | medium | accept | Env-var control implies process control already; loud startup banner; env var's power not widened | closed |
| T-04-07-03 | Information Disclosure | `predict.live._gw_pool_production` attribute | low | accept | Holds a reference to an already-public function; no credential/path/user data | closed |
| T-04-07-04 | Denial of Service | 500s on `/api/solve`,`/api/team`,`/api/rate`,`/api/plan` | high | mitigate | Same else-branch restore as T-04-07-01 removes the `TypeError` path; verified by `RESTORE OK` repro + identity test | closed |
| T-04-07-SC | Tampering | package installs | low | accept | Plan installed no packages; no install site to guard | closed |
| T-04-08-01 | Tampering | `resolveRateOverlay` row derivation | medium | mitigate | `VALID_PITCH_ROWS` set validates every non-`"BENCH"` row (`RateDiff.tsx:13,78,80`); falls through to no-ghost with DEV warn; `"BENCH"` reachable only from boolean `starting` | closed |
| T-04-08-02 | Spoofing | `best_move` name matching | low | accept | Exact-string-equal, strict single-match; spoofed name removes overlay, never redirects it | closed |
| T-04-08-03 | Information Disclosure | `GhostCard` rendering not-owned player | low | accept | Renders only fields from publicly fetched `xp_table.json` | closed |
| T-04-08-04 | Denial of Service | bench row layout | low | accept | `rowParts` returns `Math.max(5, count)`; centering asserted by test | closed |
| T-04-08-SC | Tampering | package installs | low | accept | Plan installed no packages; toolchain from 04-02 already human-approved | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-03 | FastAPI int-coerced path param cannot carry traversal sequences | plan 04-01 | 2026-09-11 |
| AR-04-02 | T-04-04 | SPA 404 fallback is Starlette's own mechanism, exposes no data; Phase 7 follow-up recorded | plan 04-01 | 2026-09-11 |
| AR-04-03 | T-04-05 | Frozen pool/export JSON contains only already-public site data | plan 04-01 | 2026-09-11 |
| AR-04-04 | T-04-07 | Playwright reports gitignored; contain only committed fixture data | plan 04-02 | 2026-09-11 |
| AR-04-05 | T-04-08 | Per-test timeouts bound real ILP solves | plan 04-02 | 2026-09-11 |
| AR-04-06 | T-04-11 | Variants derived from public export data, no new fields | plan 04-03 | 2026-09-11 |
| AR-04-07 | T-04-12 | `E2E_VARIANTS=0` single-server mode available; 3-server form CI-only | plan 04-03 | 2026-09-11 |
| AR-04-08 | T-04-13 | React default text-child escaping; no HTML-injecting API on the page | plan 04-04 | 2026-09-11 |
| AR-04-09 | T-04-15 | Page renders only public export data | plan 04-04 | 2026-09-11 |
| AR-04-10 | T-04-19 | Plan test's raised timeout is local; global default still catches hangs | plan 04-05 | 2026-09-11 |
| AR-04-11 | T-04-23 | Rating solves bounded by per-test timeout on a frozen pool | plan 04-06 | 2026-09-11 |
| AR-04-12 | T-04-07-02 | Env-var attacker already controls the process; banner announces fixture mode | plan 04-07 | 2026-09-11 |
| AR-04-13 | T-04-07-03 | Production-ref attribute carries no sensitive data | plan 04-07 | 2026-09-11 |
| AR-04-14 | T-04-07-SC | No packages installed by plan 04-07 | plan 04-07 | 2026-09-11 |
| AR-04-15 | T-04-08-02 | Strict single-match name rule degrades to no-overlay, never misdirects | plan 04-08 | 2026-09-11 |
| AR-04-16 | T-04-08-03 | Ghost renders only public `xp_table.json` fields | plan 04-08 | 2026-09-11 |
| AR-04-17 | T-04-08-04 | Bench flex basis fixed at 5 parts; layout asserted by test | plan 04-08 | 2026-09-11 |
| AR-04-18 | T-04-08-SC | No packages installed by plan 04-08 | plan 04-08 | 2026-09-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-11 | 35 | 35 | 0 | /gsd-secure-phase (State B, L1 grep verification, short-circuit — register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-11
