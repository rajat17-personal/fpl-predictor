---
milestone: v1
audited: 2026-09-12T00:00:00Z
status: gaps_found
scores:
  requirements: 39/40
  phases: 8/10
  integration: 5/5
  flows: 7/8
gaps:
  requirements:
    - id: "CUT-01"
      status: "unsatisfied"
      phase: "07-parity-validation-cutover"
      claimed_by_plans: ["07-01-PLAN.md", "07-02-PLAN.md", "07-03-PLAN.md", "07-04-PLAN.md", "07-05-PLAN.md", "07-06-PLAN.md"]
      completed_by_plans: ["07-01-SUMMARY.md (partial — serving seam only)"]
      verification_status: "missing"
      evidence: "Phase 7 is 3/6 plans executed. Serving seam (FPL_FRONTEND=react), dual_site.sh, 8-page parity tool, and the pre-deadline validation pass are done (PARITY-REPORT: 8 pages, 34 fields, 11 explained deltas, 0 defects, 5 defects found-and-closed). Validation passes 2–3 (mid-GW, post-finish) and the human-gated cutover (07-04..07-06) remain calendar-gated on the live validation gameweek. Default mount is still vanilla — correct, no premature cutover."
  phases:
    - phase: "07-parity-validation-cutover"
      status: "unverified (in progress)"
      evidence: "No 07-VERIFICATION.md — expected: phase execution is mid-flight, waves 4–6 gated on real calendar time (deadline → live → finished). Note: .planning/milestone.lock still points at a dead PID from a Phase 7 session (stale lock)."
    - phase: "08-self-hosted-gameweek-data-capture"
      status: "unverified (unexecuted)"
      evidence: "0/5 plans executed; no SUMMARYs, VALIDATION.md still draft. Wave 5 (cron edit) is gated on CUT-01 lifting the cron freeze, but waves 1–4 are not. Time-sensitive: element-summary only retains the current season, so the backfill window for finished GWs closes at season rollover."
  integration: []
  flows:
    - flow: "Cutover (CUT-01)"
      status: "partial by design"
      breaks_at: "Validation passes 2–3 and retirement (07-04..07-06) pending the live gameweek"
  traceability:
    - id: "phases-8-10-no-req-ids"
      severity: "warning"
      evidence: "Phases 8–10 were inserted with Requirements: TBD. Phase 10 SUMMARYs claim pseudo-IDs (TODO-AVAIL-FLAGS, TODO-BRACKET, PHASE10-*) that do not exist in REQUIREMENTS.md, and Phase 9 SUMMARYs claim none. The 3-source cross-reference cannot cover these phases; their verifications (both passed) are the only evidence trail. Backfill REQ-IDs into REQUIREMENTS.md or record the TBD as accepted before /gsd-complete-milestone."
  warnings:
    - id: "W1-api-key-unwired"
      severity: "warning"
      requirements: ["APIT-02", "PITCH-03", "PITCH-04"]
      evidence: "Re-confirmed 2026-09-12: /api/solve, /api/plan, /api/rate carry Depends(require_key) and CORS allows X-API-Key, but no client — React (SquadTab.tsx, PlanTransfers.tsx, RateTab.tsx) or vanilla (web/team.html) — ever sends the header. Setting FPL_API_KEYS in production would 401 the team page on both sites. Consistent with the open-stub pre-monetization design; carry to the payments milestone (PAID-02)."
    - id: "W2-react-smoke-data-blindspot"
      severity: "warning"
      requirements: ["CI-03", "CUT-01"]
      evidence: "Re-confirmed 2026-09-12: scripts/smoke_test.sh react branch asserts /api/health and index markers but never fetches /data/*.json. Mitigated by tests/test_react_seam.py mount-order assertions and full Playwright E2E coverage of /data fetches."
nyquist:
  compliant_phases: ["01", "02", "04", "05", "06", "10"]
  partial_phases: ["03"]
  not_validated_phases: ["08", "09"]
  missing_phases: ["07"]
  overall: partial
tech_debt:
  - phase: 01-test-base-layer-app-skeleton
    items:
      - "Local `npm --prefix frontend run typecheck` is still a no-op (tsc --noEmit against a solution tsconfig type-checks zero files). CI works around it by running `tsc -b` directly (ci.yml), but every local 'typecheck exits 0' signal is misleading until the script is changed to `tsc -b --noEmit`."
      - "G-01-3 wide-viewport header containment: automated class-token coverage only; final visual confirmation recorded as end-of-phase UAT."
  - phase: 02-data-layer-non-pitch-pages
    items:
      - "Human UAT pending: dark theme reads neutral-dark (not green) incl. UA chrome paint; fixture chip stacked H/A geometry vs vanilla — both programmatically gated (check-tokens.mjs, 6 geometry tests) but never eyeballed in a browser."
  - phase: 03-pitch-renderer-squad-views
    items:
      - "Human UAT pending: even-cardinality formation-row centering (G-03-1 fix) at desktop + 375px, both themes — jsdom asserts the flex model, not pixels."
      - "UI-07 automated coverage escalated as manual-only (visual/layout not automatable in jsdom) — the Nyquist PARTIAL flag on this phase."
  - phase: 05-container-build-ci-pipeline
    items:
      - "Trivy runs report-only (D-10); the 187-CVE triage backlog was deferred to Phase 6 and remains open."
  - phase: 06-security-reliability-observability-hardening
    items:
      - "06-USER-SETUP.md all three operator items unchecked: install daily cron line, install weekly cron line, confirm FPL_ALERT_WEBHOOK lands on a watched channel. REL-02/OBS-03's 'failures noticed same day' is verified wiring, not yet live coverage."
      - "Human UAT pending: real-browser solve under the restricted CORS policy (dev server against API)."
  - phase: 09-xp-model-optimizer-improvement-experiments
    items:
      - "Nyquist VALIDATION.md still status: draft — run /gsd-validate-phase 9 to reconcile."
  - phase: integration (cross-phase)
    items:
      - "SPA deep links in react/fixture mode serve dist/404.html with HTTP 404 status — app works, but uptime monitors/crawlers will see 404s post-cutover."
      - "/api/ready has no runtime consumer (Dockerfile HEALTHCHECK uses /api/health only) — expected until the deploy milestone wires orchestrator probes."
      - "No Playwright specs for /league, /scoreboard, /differentials, /methodology — not required by E2E-01..05; covered by vitest units and the Phase 7 parity tool's 8-page registry."
      - "Stale .planning/milestone.lock (dead PID from a Phase 7 session) — clear before the next execute-phase run if it blocks."
---

# Milestone v1 Audit — FPL Predictor: Production Hardening

**Audited:** 2026-09-12 (re-audit; supersedes 2026-09-11) · **Status:** `gaps_found` · **Verdict in one line:** all 39 buildable requirements remain satisfied and verified across three independent sources, cross-phase integration re-confirmed at source level with zero blockers; the only open gap is the cutover itself (CUT-01), calendar-gated on the live validation gameweek, plus the unexecuted Phase 8 data-capture insert.

## What changed since the 2026-09-11 audit

Four commits, docs and tests only — no production code:

1. **Phase 5 Nyquist gap closed** — `tests/test_ci_cd_artifacts.py` added (786 lines, 32 tests, all passing: lockfile pinning, Dockerfile non-root/multi-stage, SHA-pinned actions, gitignore/dockerignore rules, smoke-test syntax). `05-VALIDATION.md` reconciled to `status: validated`, `nyquist_compliant: true` (validated 2026-09-12). Phase 5 moves NOT-VALIDATED → **COMPLIANT**; its "VALIDATION still draft" tech-debt item is removed.
2. **Phase 4 re-audited** — validation re-audit (0 gaps, all suites green) and security threat verification updated. Remains COMPLIANT/passed.
3. Everything else unchanged: Phase 7 still 3/6 plans (calendar-gated), Phase 8 still 0/5, Phase 9 VALIDATION still draft.

## Requirements Coverage (3-source cross-reference)

40 v1 requirements in REQUIREMENTS.md traceability; all 40 mapped, 0 orphans (every REQ-ID appears in at least one phase VERIFICATION).

| Group | REQ-IDs | Phase | VERIFICATION | SUMMARY frontmatter | Checkbox | Final |
|---|---|---|---|---|---|---|
| React App | UI-01..UI-07 | 1–3 | passed | listed | [x] | **satisfied** |
| Pitch View | PITCH-01..04 | 3 | passed | listed | [x] | **satisfied** |
| UI Extras | UIX-01..03 | 2–3 | passed | listed | [x] | **satisfied** |
| API Tests | APIT-01..03 | 1 | passed | listed | [x] | **satisfied** |
| Playwright E2E | E2E-01..05 | 4 | passed | listed | [x] | **satisfied** |
| CI/CD | CI-01..05 | 5 | passed | listed | [x] | **satisfied** |
| Security | SEC-01..04 | 5–6 | passed | SEC-04 via body table (05-04) | [x] | **satisfied** |
| Reliability | REL-01..05 | 6 | passed | listed | [x] | **satisfied** |
| Observability | OBS-01..03 | 6 | passed | listed | [x] | **satisfied** |
| Cutover | CUT-01 | 7 | **missing** | listed (07-01, partial) | [ ] | **unsatisfied** |

Note: SEC-04 does not appear in any SUMMARY `requirements-completed` frontmatter field, but 05-04-SUMMARY's body requirement table and 05-VERIFICATION.md both mark it SATISFIED with concrete evidence — treated as satisfied, not partial. It is now additionally regression-pinned by `tests/test_ci_cd_artifacts.py`.

## Phase Verification Status

| Phase | VERIFICATION | Score | Nyquist |
|---|---|---|---|
| 1 Test Base Layer & App Skeleton | passed | 9/10 (1 visual → UAT) | COMPLIANT |
| 2 Data Layer & Non-Pitch Pages | passed | 14/16 | COMPLIANT |
| 3 Pitch Renderer & Squad Views | passed | 12/12 automated | PARTIAL (UI-07 manual-only) |
| 4 E2E Regression Suite | passed (re-audited 09-12, 0 gaps) | 5/5 | COMPLIANT |
| 5 Container Build & CI | passed + human-verified | 6/8 + 2 human-confirmed | **COMPLIANT** (reconciled 09-12) |
| 6 Security/Reliability/Observability | passed | 5/5 criteria | COMPLIANT |
| 7 Parity Validation & Cutover | **missing** — in progress 3/6 | — | MISSING |
| 8 Self-Hosted GW Data Capture | **missing** — unexecuted 0/5 | — | NOT-VALIDATED (draft) |
| 9 xP Improvement Experiments | passed | 15/15 | NOT-VALIDATED (draft) |
| 10 xP Experiment Follow-ups | passed | 12/12 | COMPLIANT |

## Cross-Phase Integration (subagent report, 2026-09-12)

**5/5 load-bearing seams re-verified WIRED against live source; 0 blockers.**

1. **Frontend→API**: Vite proxy paths match FastAPI routes exactly; all four response contracts (`SolveResult`, `RateResponse`, `PlanResponse`, `TeamResponse` in `frontend/src/lib/api.ts`) verified field-for-field against `api/main.py` handlers; all 10 `/data/*.json` fetches map to real pipeline outputs.
2. **E2E↔CI**: linear job chain lint-build → test → e2e → image → publish confirmed in `ci.yml`; frontend dist artifact handoff verified at each stage; both smoke modes (fixture, `SMOKE_REACT_MODE=1`) run before Trivy and publish.
3. **Phase 6 hardening**: CORS allowlist covers exactly the dev origins with `X-API-Key` allowed; solve cache is OrderedDict LRU (max 256) + 1h TTL with the REL-05 TOCTOU fix (`PoolSnapshot` read under one lock).
4. **Phase 7 react seam**: fixture > react > vanilla mount precedence verified in code and pinned by 4 tests in `tests/test_react_seam.py`; default mount remains vanilla (correct pre-cutover).
5. **Weekly pipeline contract**: zero orphans in either direction between producers (export/scoreboard/price) and consumers (React 10 files, vanilla 7 files); Phase 9/10 experiment code confirmed default-off with no imports into `predict/export.py`.

Spot-checked E2E flow (/team load → mark players → solve → pitch re-render) traced link-by-link through `Team.tsx` → `SquadTab.tsx` → `/api/solve` → ILP → response render, covered end-to-end by `e2e/specs/team-solver.spec.ts` running the real CBC solver.

**New since last audit:** `tests/test_ci_cd_artifacts.py` collects and passes cleanly (32/32), references only real repo artifacts, and regression-pins SEC-02/SEC-04/CI-01/CI-03/CI-04/CI-05 contracts.

Warnings W1 (API-key header has no client sender) and W2 (react smoke never probes `/data`) re-confirmed and recorded in frontmatter — pre-monetization/pre-cutover hygiene, not blockers.

## Bottom Line

Unchanged from yesterday in substance, improved in coverage: 39/40 requirements verified across three independent sources, integration re-confirmed at source level with a new 32-test CI/CD artifact suite, and Nyquist compliance now 6 COMPLIANT / 1 PARTIAL / 2 draft / 1 missing. What remains is (a) Phase 7's calendar-gated validation gameweek and human-gated cutover — the milestone's definition of done explicitly ends there — and (b) the Phase 8 insert, whose backfill is time-sensitive (finished-GW data becomes unrecoverable at season rollover). Do not run /gsd-complete-milestone until CUT-01 closes and Phase 8's disposition (execute now vs. re-scope) is decided.
