---
milestone: v1
audited: 2026-09-11T00:00:00Z
status: gaps_found
scores:
  requirements: 39/40
  phases: 8/10
  integration: 14/16
  flows: 7/8
gaps:
  requirements:
    - id: "CUT-01"
      status: "unsatisfied"
      phase: "07-parity-validation-cutover"
      claimed_by_plans: ["07-01-PLAN.md", "07-02-PLAN.md", "07-03-PLAN.md", "07-04-PLAN.md", "07-05-PLAN.md", "07-06-PLAN.md"]
      completed_by_plans: ["07-01-SUMMARY.md (partial — serving seam only)"]
      verification_status: "missing"
      evidence: "Phase 7 is 3/6 plans executed. Serving seam (FPL_FRONTEND=react), dual_site.sh, 8-page parity tool, and the pre-deadline validation pass are done; validation passes 2–3 (mid-GW, post-finish) and the human-gated cutover (07-04..07-06) are calendar-gated on the live validation gameweek. Default mount is still vanilla (api/main.py:801) — correct, no premature cutover."
  phases:
    - phase: "07-parity-validation-cutover"
      status: "unverified (in progress)"
      evidence: "No 07-VERIFICATION.md — expected: phase execution is mid-flight, waves 4–6 gated on real calendar time (deadline → live → finished)."
    - phase: "08-self-hosted-gameweek-data-capture"
      status: "unverified (unexecuted)"
      evidence: "0/5 plans executed; no VERIFICATION.md. Wave 5 (cron edit) is gated on CUT-01 lifting the cron freeze, but waves 1–4 are not. Time-sensitive: element-summary only retains the current season, so the backfill window for finished GWs closes at season rollover."
  integration:
    - id: "W1-api-key-unwired"
      severity: "warning"
      requirements: ["APIT-02", "PITCH-03", "PITCH-04"]
      evidence: "/api/solve, /api/plan, /api/rate carry Depends(require_key) and CORS allows X-API-Key (api/main.py:131), but no client — React (SquadTab.tsx:113-115, PlanTransfers.tsx:40-42, RateTab.tsx:19) or vanilla (web/team.html) — ever sends the header. Setting FPL_API_KEYS in production would 401 the team page on both sites. Consistent with the open-stub pre-monetization design; carry to the payments milestone (PAID-02)."
    - id: "W2-react-smoke-data-blindspot"
      severity: "warning"
      requirements: ["CI-03", "CUT-01"]
      evidence: "scripts/smoke_test.sh react branch (:58-104) asserts /api/health and index markers but never fetches /data/*.json — the Starlette mount-order hazard the code itself documents (api/main.py:788-790) is exactly what it wouldn't catch in-container. Mitigated by tests/test_react_seam.py mount-order assertions."
  flows:
    - flow: "Cutover (CUT-01)"
      status: "partial by design"
      breaks_at: "Validation passes 2–3 and retirement (07-04..07-06) pending the live gameweek"
  traceability:
    - id: "phases-8-10-no-req-ids"
      severity: "warning"
      evidence: "Phases 8–10 were inserted with Requirements: TBD. Phase 10 SUMMARYs claim pseudo-IDs (TODO-AVAIL-FLAGS, TODO-BRACKET, PHASE10-*) that do not exist in REQUIREMENTS.md, and Phase 9 SUMMARYs claim none. The 3-source cross-reference cannot cover these phases; their verifications (both passed) are the only evidence trail. Backfill REQ-IDs into REQUIREMENTS.md or record the TBD as accepted before /gsd-complete-milestone."
nyquist:
  compliant_phases: ["01", "02", "04", "06", "10"]
  partial_phases: ["03"]
  not_validated_phases: ["05", "08", "09"]
  missing_phases: ["07"]
  overall: partial
tech_debt:
  - phase: 01-test-base-layer-app-skeleton
    items:
      - "Local `npm --prefix frontend run typecheck` is still a no-op (tsc --noEmit against a solution tsconfig type-checks zero files). CI works around it by running `tsc -b` directly (ci.yml:58-59), but every local 'typecheck exits 0' signal is misleading until the script is changed to `tsc -b --noEmit`."
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
      - "Nyquist VALIDATION.md still status: draft — run /gsd-validate-phase 5 to reconcile."
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
---

# Milestone v1 Audit — FPL Predictor: Production Hardening

**Audited:** 2026-09-11 · **Status:** `gaps_found` · **Verdict in one line:** all 39 buildable requirements are satisfied and verified with cross-phase wiring confirmed end to end; the only open gap is the cutover itself (CUT-01), which is calendar-gated on the live validation gameweek, plus the unexecuted Phase 8 data-capture insert.

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

Note: SEC-04 does not appear in any SUMMARY `requirements-completed` frontmatter field, but 05-04-SUMMARY's body requirement table and 05-VERIFICATION.md line 91 both mark it SATISFIED with concrete evidence (.deb absent from disk/history, .gitignore reconciled, workflows tracked) — treated as satisfied, not partial.

## Phase Verification Status

| Phase | VERIFICATION | Score | Nyquist |
|---|---|---|---|
| 1 Test Base Layer & App Skeleton | passed (re-verified) | 9/10 (1 visual → UAT) | COMPLIANT |
| 2 Data Layer & Non-Pitch Pages | passed (re-verified) | 14/16 | COMPLIANT |
| 3 Pitch Renderer & Squad Views | passed (re-verified) | 12/12 automated | PARTIAL (UI-07 manual-only) |
| 4 E2E Regression Suite | passed (re-verified) | 5/5 | COMPLIANT |
| 5 Container Build & CI | passed + human-verified | 6/8 + 2 human-confirmed | NOT-VALIDATED (draft) |
| 6 Security/Reliability/Observability | passed (re-verified) | 5/5 criteria | COMPLIANT |
| 7 Parity Validation & Cutover | **missing** — in progress 3/6 | — | MISSING |
| 8 Self-Hosted GW Data Capture | **missing** — unexecuted 0/5 | — | NOT-VALIDATED (draft) |
| 9 xP Improvement Experiments | passed | 15/15 | NOT-VALIDATED (draft) |
| 10 xP Experiment Follow-ups | passed | 12/12 | COMPLIANT |

## Cross-Phase Integration (subagent report)

**14/16 checks wired, 7/8 flows complete, 0 blockers.** All five load-bearing seams verified against source, not planning docs:

1. **Frontend→API**: Vite proxy paths match FastAPI routes exactly (incl. `/api/plan`, a real tested route absent from the original route list); response contracts verified field-for-field between `frontend/src/lib/api.ts` and `api/main.py`.
2. **E2E↔CI**: Playwright webServer builds the frontend and boots uvicorn with `FPL_FIXTURE_DIR`, health-gated; CI's `e2e` job runs the full suite in the lint-build → test → e2e → image → publish chain.
3. **Phase 6 vs earlier seams**: CORS default allowlist covers exactly the Phase 1/4 dev origins; the LRU+TTL cache rework preserves the solve response shape (pinned by the E2E REPIN test).
4. **Phase 7 react seam**: fixture > react > vanilla mount precedence tested; CI smoke re-runs the same image with `SMOKE_REACT_MODE=1`.
5. **Weekly pipeline contract**: zero orphans in either direction — every JSON consumed by React (10 files) or vanilla (7 files) is produced by export/scoreboard/price; Phases 9/10 experiments confirmed isolated from the weekly path (default-off, no imports into predict/export.py).

Warnings W1 (API-key header has no client sender) and W2 (react smoke never probes `/data`) are recorded in frontmatter above — pre-monetization/pre-cutover hygiene, not blockers.

## Bottom Line

The buildable milestone is done and holds together: 39/40 requirements verified across three independent sources, integration confirmed at the source level, and the weekly recommendation cycle demonstrably intact. What remains is (a) Phase 7's calendar-gated validation gameweek and human-gated cutover — the milestone's definition of done explicitly ends there — and (b) the Phase 8 insert, whose backfill is time-sensitive (finished-GW data becomes unrecoverable at season rollover). Neither is a planning failure; both are known, sequenced work. Do not run /gsd-complete-milestone until CUT-01 closes and Phase 8's disposition (execute now vs. re-scope) is decided.
