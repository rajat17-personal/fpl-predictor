---
milestone: v1
audited: 2026-09-12T04:30:00Z
status: gaps_found
scores:
  requirements: 39/40
  phases: 8/10
  integration: 6/6
  flows: 6/7
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
      evidence: "No 07-VERIFICATION.md — expected: phase execution is mid-flight, waves 4–6 gated on real calendar time (deadline → live → finished). No new Phase 7 progress since the previous audit. Note: .planning/milestone.lock still points at a dead PID from a Phase 7 session (stale lock, re-confirmed dead this pass)."
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
      evidence: "Re-confirmed 2026-09-12 (this pass, by the integration checker): /api/solve, /api/plan, /api/rate carry Depends(require_key) and CORS allows X-API-Key, but no client — React (SquadTab.tsx, PlanTransfers.tsx, RateTab.tsx) or vanilla (web/team.html) — ever sends the header (grep of frontend/src returns nothing). Setting FPL_API_KEYS in production would 401 the team page on both sites. Consistent with the open-stub pre-monetization design; carry to the payments milestone (PAID-02)."
    - id: "W2-react-smoke-data-blindspot"
      severity: "warning"
      requirements: ["CI-03", "CUT-01"]
      evidence: "Re-confirmed 2026-09-12 (this pass): scripts/smoke_test.sh react branch asserts /api/health and index markers (<div id=\"root\"> present, assets/style.css absent) but never fetches /data/*.json. Mitigated by frontend route tests, tests/test_react_seam.py mount-order assertions, and full Playwright E2E coverage of /data fetches."
nyquist:
  compliant_phases: ["01", "02", "04", "05", "06", "09", "10"]
  partial_phases: ["03"]
  not_validated_phases: ["08"]
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
  - phase: integration (cross-phase)
    items:
      - "SPA deep links in react/fixture mode serve dist/404.html with HTTP 404 status — app works, but uptime monitors/crawlers will see 404s post-cutover."
      - "/api/ready has no runtime consumer (Dockerfile HEALTHCHECK uses /api/health only; re-confirmed no HEALTHCHECK present) — expected until the deploy milestone wires orchestrator probes."
      - "No Playwright specs for /league, /scoreboard, /differentials, /methodology — not required by E2E-01..05; covered by vitest units and the Phase 7 parity tool's 8-page registry."
      - "Stale .planning/milestone.lock (dead PID from a Phase 7 session, re-confirmed dead 2026-09-12) — clear before the next execute-phase run if it blocks."
---

# Milestone v1 Audit — FPL Predictor: Production Hardening

**Audited:** 2026-09-12 (second re-audit; supersedes the 2026-09-12 morning audit) · **Status:** `gaps_found` · **Verdict in one line:** all 39 buildable requirements remain satisfied and verified across three independent sources, cross-phase integration re-verified end-to-end with zero blockers and zero new findings; the only open gap is the cutover itself (CUT-01), calendar-gated on the live validation gameweek, plus the unexecuted Phase 8 data-capture insert.

## What changed since the 2026-09-12 morning audit

Two commits, docs and tests only — no production code:

1. **Phase 9 Nyquist gap closed** — Nyquist validation tests added (c3e0d88) and `09-VALIDATION.md` reconciled to `status: validated`, `nyquist_compliant: true`, `wave_0_complete: true` (f66a3ef). Phase 9 moves NOT-VALIDATED → **COMPLIANT**; its "VALIDATION still draft" tech-debt item is removed. Nyquist tally is now 7 COMPLIANT / 1 PARTIAL / 1 NOT-VALIDATED / 1 MISSING.
2. Everything else unchanged: Phase 7 still 3/6 plans (calendar-gated, no 07-04 SUMMARY), Phase 8 still 0/5, requirements checkboxes unchanged (39×`[x]`, CUT-01 `[ ]`).

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

Note: SEC-04 does not appear in any SUMMARY `requirements-completed` frontmatter field, but 05-04-PLAN's `requirements:` frontmatter claims it and 05-VERIFICATION.md marks it ✓ SATISFIED with concrete evidence (`.deb` absent from disk/history, `.gitignore` reconciled, workflows tracked) — treated as satisfied, not partial. Additionally regression-pinned by `tests/test_ci_cd_artifacts.py`.

## Phase Verification Status

| Phase | VERIFICATION | Score | Nyquist |
|---|---|---|---|
| 1 Test Base Layer & App Skeleton | passed | 9/10 (1 visual → UAT) | COMPLIANT |
| 2 Data Layer & Non-Pitch Pages | passed | 14/16 | COMPLIANT |
| 3 Pitch Renderer & Squad Views | passed | 12/12 automated | PARTIAL (UI-07 manual-only) |
| 4 E2E Regression Suite | passed (re-audited 09-12, 0 gaps) | 5/5 | COMPLIANT |
| 5 Container Build & CI | passed + human-verified | 6/8 + 2 human-confirmed | COMPLIANT |
| 6 Security/Reliability/Observability | passed | 5/5 criteria | COMPLIANT |
| 7 Parity Validation & Cutover | **missing** — in progress 3/6 | — | MISSING |
| 8 Self-Hosted GW Data Capture | **missing** — unexecuted 0/5 | — | NOT-VALIDATED (draft) |
| 9 xP Improvement Experiments | passed | 15/15 | **COMPLIANT** (reconciled 09-12) |
| 10 xP Experiment Follow-ups | passed | 12/12 | COMPLIANT |

## Cross-Phase Integration (subagent report, 2026-09-12 afternoon pass)

**6/6 load-bearing seams verified WIRED end-to-end against live source; 6/6 checkable E2E flows complete; 0 blockers, 0 new findings.**

1. **Phase 1→2/3 (React ↔ data/API)**: Vite proxy (`/api`, `/data` → :8000) matches FastAPI routes exactly; all 13 TypeScript interfaces in `frontend/src/lib/api.ts` verified against `api/main.py` handlers; every route fetches its `/data/*.json` at runtime — nothing bundled.
2. **Phase 3→6 (pitch ↔ hardened API)**: solve/plan/rate/team calls verified against the restricted CORS allowlist (wildcard is a boot failure), the bounded LRU solve cache (max 256, 1h TTL) with the REL-05 atomic pool-snapshot fix.
3. **Phase 4→5 (E2E ↔ CI)**: chained lint-build → test → e2e → image → publish confirmed in `ci.yml`; frontend dist artifact handoff verified; all three fixture variants (normal/blank/dgw) run; `FPL_FIXTURE_DIR` else-branch leaves production untouched.
4. **Phase 5→7 (container ↔ react seam)**: the same image is smoke-tested twice — fixture mode, then `SMOKE_REACT_MODE=1` asserting the React root marker and the absence of the vanilla stylesheet; mount precedence fixture > react > vanilla pinned by `tests/test_react_seam.py`; default mount remains vanilla (correct pre-cutover).
5. **Phase 6→7 (hardening ↔ parity tooling)**: fixture-mode branches never touch the live FPL API or joblib artifacts; dual-site and parity tooling run against the hardened serving path.
6. **Phase 9/10→product (experiment isolation)**: `config.resolve_experiments()` has exactly one callsite — `backtest/walk_forward.py` — and `models/train.py:main()` / `predict/export.py` never pass experiment or `stage2` parameters; `test_experiments_registry_default_off` passes. The weekly product output is provably unaffected by both experiment phases.

E2E flows traced link-by-link and covered by real Playwright specs against the real CBC solver: weekly export → JSON → React render; team load → lock → solve → pitch update; rate-my-team; multi-week plan; CI push → verify → publish; default model-squad view. The seventh flow — cutover itself — is partial by design (waves 4–6 calendar-gated).

Prior accepted items re-verified as still holding: W1 (no client sends `X-API-Key`), W2 (react smoke never probes `/data`, mitigated), SPA deep-link 404 status, `/api/ready` unconsumed by any HEALTHCHECK.

## Bottom Line

Unchanged from this morning in substance, improved in coverage: 39/40 requirements verified across three independent sources, integration re-confirmed end-to-end by a fresh subagent pass with zero blockers, and Nyquist compliance now 7 COMPLIANT / 1 PARTIAL (Phase 3, manual-only UI-07) / 1 draft (Phase 8, unexecuted) / 1 missing (Phase 7, in progress). What remains is (a) Phase 7's calendar-gated validation gameweek and human-gated cutover — the milestone's definition of done explicitly ends there — and (b) the Phase 8 insert, whose backfill is time-sensitive (finished-GW data becomes unrecoverable at season rollover). Do not run /gsd-complete-milestone until CUT-01 closes and Phase 8's disposition (execute now vs. re-scope) is decided.
