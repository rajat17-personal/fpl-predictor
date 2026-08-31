# Requirements: FPL Predictor — Production Hardening

**Defined:** 2026-08-31
**Core Value:** The weekly recommendations (xP table, squad, captains, transfers) must keep flowing reliably — every change must leave the pipeline, API, and site at least as correct and more trustworthy than before.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### React App

- [x] **UI-01**: React (Vite, TypeScript 6.x) app with routes for all 8 pages, dev-server proxy to the API, and runtime-fetched `web/data/*.json` (never bundled at build time)
- [ ] **UI-02**: xP table page at parity — sortable/filterable by position, team, price, xP, ownership, form, with exact sort/format semantics matching the vanilla site
- [ ] **UI-03**: Fixtures page with FDR ticker in the standard 1–5 green→red convention
- [ ] **UI-04**: Prices page with watchlist rise/fall indicators
- [ ] **UI-05**: League, scoreboard, differentials, and methodology pages at parity
- [ ] **UI-06**: Persistent gameweek meta banner with deadline countdown
- [ ] **UI-07**: Mobile-responsive pitch and tables

### Pitch View

- [ ] **PITCH-01**: Shirt/kit asset sourcing decision documented before component build (verify FPL CDN URLs via devtools, or neutral generated kits) with non-affiliation disclaimer
- [ ] **PITCH-02**: Pitch renderer — formation-driven rows (GK/DEF/MID/FWD + bench), player cards with shirt, name, price, xP, and C/VC badges
- [ ] **PITCH-03**: Team page — load a squad (default entry 6980093), render on pitch, lock/exclude players, request solve, see transfers/XI update
- [ ] **PITCH-04**: Rate-my-team view — visual diff of user squad vs optimal with suggested swaps

### UI Extras

- [ ] **UIX-01**: p10/p90 prediction intervals rendered on player/captain cards
- [ ] **UIX-02**: Dark mode toggle
- [ ] **UIX-03**: Chip-timing "why this GW" UI with DGW/BGW callouts

### API Tests

- [x] **APIT-01**: FastAPI TestClient integration tests for /solve, /rate, /team, /health, /meta with mocked FPL API
- [x] **APIT-02**: Auth stub (`require_key`) tests — open mode, valid key, invalid key
- [x] **APIT-03**: Concurrency test for pool refresh + solve-cache race, with autouse state-reset fixture (adds DI seam as needed)

### Playwright E2E

- [ ] **E2E-01**: Fixture strategy — frozen versioned JSON snapshots (normal, blank, double GW) and mocked FPL API; no live-data dependence
- [ ] **E2E-02**: Team/pitch + solver flow regression test
- [ ] **E2E-03**: xP table + captains rendering/sorting regression test
- [ ] **E2E-04**: Rate-my-team flow regression test
- [ ] **E2E-05**: Fixtures and prices pages regression tests

### CI/CD

- [ ] **CI-01**: GitHub Actions workflow — lint, typecheck, pytest + API tests on every push/PR
- [ ] **CI-02**: Frontend build + Playwright E2E job with cached browsers, run against uvicorn serving the built frontend + fixture data
- [ ] **CI-03**: Multi-stage Dockerfile on `python:3.14-slim` with locked deps, CBC solver installed, and a container smoke test (solver available + health check passes)
- [ ] **CI-04**: Image published to GHCR with SHA-pinned actions and scoped `GITHUB_TOKEN`; deploy step stubbed
- [ ] **CI-05**: Trivy image vulnerability scan job

### Security & Config

- [ ] **SEC-01**: CORS restricted from `["*"]` to configured origins
- [ ] **SEC-02**: Dependencies pinned/locked (uv lock or equivalent), verified installable in a fresh environment with cp314 wheels
- [ ] **SEC-03**: Secrets via `.env` pattern (mode 600), never in code, logs, or workflows
- [ ] **SEC-04**: Repo hygiene — Chrome .deb removed, proper `.gitignore`, workflows tracked in git

### Reliability

- [ ] **REL-01**: All file handles closed via context managers (fixes the leak inventory in CONCERNS.md)
- [ ] **REL-02**: Cron error traps — remove `|| true`, add retry/backoff to snapshot, failures visible
- [ ] **REL-03**: Pydantic schema validation on FPL bootstrap/fixtures payloads
- [ ] **REL-04**: Graceful JSON-load failures in predict/* with actionable error messages
- [ ] **REL-05**: Solve cache bounded (LRU/TTL) with the invalidation race fixed

### Observability

- [ ] **OBS-01**: Structured (JSON) request logging in the API
- [ ] **OBS-02**: Health/readiness endpoints with liveness vs readiness semantics
- [ ] **OBS-03**: Cron and FPL-API-outage failures surfaced/alertable (not buried in cron.log)

### Cutover

- [ ] **CUT-01**: Vanilla site stays live until the React site completes a full gameweek cycle (deadline → live → finished) side-by-side with verified parity; only then is it retired

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Product & Monetization

- **PAID-01**: Rate limiting (slowapi, per-IP/per-key) — user decision: implement when the paid feature is added
- **PAID-02**: Supabase JWT auth + subscriptions table replacing `require_key()` stub
- **PAID-03**: Payment webhooks (Razorpay + merchant-of-record)

### Deployment

- **DEPLOY-01**: Live deploy automation — Cloudflare Pages (frontend) + API host with crons

### UI Polish

- **UIX-04**: Price-watchlist polish (predicted tonight/tomorrow/later granularity)
- **UIX-05**: Historical multi-season stats explorer UI

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time in-match live tracking | High infra complexity; batch pipeline architecture doesn't support it; revisit only with demonstrated demand |
| Social/community features | Scope creep for solo dev; link out to existing communities instead |
| Custom-drawn club crests/kits | Trademark risk for a paid product; use FPL's officially-served imagery or neutral kits only |
| Model/decision-quality improvements | Model is validated (6-season walk-forward); extra sophistication doesn't pay (see IMPROVEMENTS.md) |
| FBref data integration | Abandoned — site no longer serves advanced stat values |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 1 | Complete |
| APIT-01 | Phase 1 | Complete |
| APIT-02 | Phase 1 | Complete |
| APIT-03 | Phase 1 | Complete |
| UI-02 | Phase 2 | Pending |
| UI-03 | Phase 2 | Pending |
| UI-04 | Phase 2 | Pending |
| UI-05 | Phase 2 | Pending |
| UI-06 | Phase 2 | Pending |
| UIX-02 | Phase 2 | Pending |
| PITCH-01 | Phase 3 | Pending |
| PITCH-02 | Phase 3 | Pending |
| PITCH-03 | Phase 3 | Pending |
| PITCH-04 | Phase 3 | Pending |
| UI-07 | Phase 3 | Pending |
| UIX-01 | Phase 3 | Pending |
| UIX-03 | Phase 3 | Pending |
| E2E-01 | Phase 4 | Pending |
| E2E-02 | Phase 4 | Pending |
| E2E-03 | Phase 4 | Pending |
| E2E-04 | Phase 4 | Pending |
| E2E-05 | Phase 4 | Pending |
| CI-01 | Phase 5 | Pending |
| CI-02 | Phase 5 | Pending |
| CI-03 | Phase 5 | Pending |
| CI-04 | Phase 5 | Pending |
| CI-05 | Phase 5 | Pending |
| SEC-02 | Phase 5 | Pending |
| SEC-04 | Phase 5 | Pending |
| SEC-01 | Phase 6 | Pending |
| SEC-03 | Phase 6 | Pending |
| REL-01 | Phase 6 | Pending |
| REL-02 | Phase 6 | Pending |
| REL-03 | Phase 6 | Pending |
| REL-04 | Phase 6 | Pending |
| REL-05 | Phase 6 | Pending |
| OBS-01 | Phase 6 | Pending |
| OBS-02 | Phase 6 | Pending |
| OBS-03 | Phase 6 | Pending |
| CUT-01 | Phase 7 | Pending |

**Coverage:**

- v1 requirements: 40 total
- Mapped to phases: 40 ✓
- Unmapped: 0

---
*Requirements defined: 2026-08-31*
*Last updated: 2026-08-31 after roadmap creation (traceability populated)*
