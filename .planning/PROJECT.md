# FPL Predictor — Production Hardening

## What This Is

A Fantasy Premier League prediction and squad-optimization system: a LightGBM two-stage hurdle model predicts expected points (xP), ILP solvers pick squads/transfers/captains, and a FastAPI service plus a static site deliver weekly recommendations. This milestone hardens the system for production ahead of monetization: a React rebuild of the web UI with an FPL-style pitch renderer, CI/CD with Docker, real test coverage (API + Playwright E2E), and closure of the production-readiness gaps in the concerns audit.

## Core Value

The weekly recommendations (xP table, squad, captains, transfers) must keep flowing reliably — every change in this milestone must leave the pipeline, API, and site at least as correct and more trustworthy than before.

## Business Context

- **Customer**: FPL managers; freemium visitors → season-pass subscribers (~₹499/$19)
- **Revenue model**: Freemium + season pass; Razorpay (UPI Autopay) + merchant-of-record for international — gateway choice still pending (user reviewing)
- **Success metric**: Paid launch ready pre-season July 2027; this milestone gates it on production-grade code, tests, and CI
- **Strategy notes**: Monetization playbook + build roadmap artifacts (see memory / claude.ai artifacts); auth (Supabase JWT) and payment webhooks deliberately deferred — `require_key()` in `api/main.py` is the single swap point

## Requirements

### Validated

- ✓ Data pipeline: vaastav history + live FPL API ingest, canonical player_gw table, leakage-safe rolling features — existing
- ✓ xP model: two-stage per-position hurdle (LightGBM), isotonic P(play) calibration, p10/p90 intervals; 6-season walk-forward core 2134 ±36 — existing
- ✓ Optimization: squad ILP (15-man, XI, captain-by-mean), transfer ILP with hits/sell-on fee/grandfathered club cap, chip heuristics — existing
- ✓ Backtest: multi-season walk-forward with jitter CIs and isolated chip evaluation — existing
- ✓ Product surface: weekly JSON export contract (`web/data/*.json`), FastAPI solver API (/solve, /rate, /team), 8-page static site, email digest — existing
- ✓ Ops: daily snapshot + weekly export cron scripts; pytest suite for optimizer legality, leakage, autosubs, export builders (~18 tests) — existing
- ✓ FastAPI integration test suite (TestClient): /solve, /rate, /team, /health, /meta against a `responses`-mocked FPL API; three-mode auth stub coverage; concurrent solve + pool-refresh race test — Phase 1
- ✓ React/Vite app skeleton with proven dev-proxy runtime seam: all 8 routes resolve, per-route error boundaries, loading/error/empty/404 states, Vitest harness, no pipeline data bundled — Phase 1
- ✓ Seven non-pitch pages (xP table, fixtures, prices, league, scoreboard, differentials, methodology) rebuilt at verified vanilla parity from the unchanged JSON contract, with GW deadline banner, persistent dark mode, self-hosted fonts, and a PARITY-DEVIATIONS.md ledger of every intentional delta — Phase 2
- ✓ FPL-style pitch renderer + team page: green-gradient pitch with neutral generated SVG kits, formation rows with continuous flex centering (any row size incl. 6-card ghost rows), Squad/Rate/Plan tabs, solver flow with numeric-code locks/excludes and stale-response guard — all 8 pages now rebuilt; UAT 4/4, 21 threats closed — Phase 3
- ✓ Trademark posture for pitch visuals: neutral generated kits (no crests/sponsors/CDN imagery), sitewide disclaimer, committed decision doc (docs/decisions/pitch-kit-sourcing.md) signed off in UAT — Phase 3
- ✓ Playwright E2E regression suite on frozen versioned fixtures (normal/blank/DGW) with a fixture-mode API server: team/pitch + solver flow, xP table + captains (exact cell values and sort order), rate-my-team incl. pitch visual diff, fixtures & prices pages — 42 specs, calendar-independent — Phase 4
- ✓ CI/CD on GitHub Actions: hash-locked deps (uv --generate-hashes), ruff lint, 5-job chained ci.yml (lint-build → test → e2e → image → publish) with SHA-pinned actions, multi-stage Docker image + CBC smoke test, report-only Trivy scan, GHCR publish proven live (ghcr.io/rajat17-personal/fpl-predictor), branch protection on main, local preflight.sh mirror — Phase 5
- ✓ Repo push hygiene: 140MB Chrome .deb removed, dispatch-only schedulers on py3.14 with hashed installs and bot identity, personal email redacted from tracked files, .gitignore reconciled — Phase 5
- ✓ Security & config hardening: CORS restricted to a configured allowlist (wildcard = boot failure, live-browser verified), mode-600 `.env` secrets pattern with loud-warning loader, secret redaction on every log/alert egress — Phase 6
- ✓ Reliability fixes: all bare file handles routed through ops.jsonio (self-tested repo-wide gate), atomic writes everywhere, cron per-step accounting with zero shell suppression, snapshot retry/backoff, pydantic validation of FPL payloads, bounded LRU+TTL solve cache with pool-version invalidation and the TOCTOU race closed via atomic snapshots — Phase 6
- ✓ Observability: structured JSON logging with X-Request-ID correlation, distinct liveness/readiness endpoints, never-raising ops.notify alerting spine — cron + webhook confirmed live in UAT — Phase 6
- ✓ Experiment framework + honest measurement of the xP/optimizer frontier: flag registry (`config.EXPERIMENTS`), leakage-tested enrichment joins (Understat, FotMob, Dixon-Coles team strength), external benchmark vs theFPLkiwi, Wildcard's isolated value measured (+14.2±9.0), RL-for-strategy time-boxed and beaten by the solver — all 8 experiments REJECTED on the pre-declared ≥2,280 bar (final combined 2262 = baseline); code merged default-off, IMPROVEMENTS.md Phase F ledger complete, product surface untouched — Phase 9

### Active

- [ ] Parity validation & cutover (Phase 7, CUT-01): React and vanilla sites side by side through a full gameweek cycle; retire vanilla only after zero unexplained deltas

### Out of Scope

- Live deployment to Cloudflare Pages / Hetzner — hosting not yet purchased; CI produces a deployable image, deployment automation is the next milestone
- Auth (Supabase JWT) and payment integration — blocked on user's gateway/legal decision; `require_key()` stub stays the swap point
- Model/decision-quality improvements — meta-pattern now measured, not assumed: Phase 9 ran the six recommended experiments honestly and every one was rejected on its pre-declared bar (IMPROVEMENTS.md Phase F); further xP gains need better signal, not more machinery
- FBref data integration — confirmed not acquirable (Phase 9: Cloudflare challenge survives real-Chrome UC-mode spikes); no new scraping infrastructure
- A/B testing / feature-flag infrastructure — needed for model rollout experiments, but post-launch concern

## Context

- Brownfield: complete codebase map in `.planning/codebase/` (2026-08-31). Batch ML pipeline + product layers; Python 3.14 (conda env `python314`), FastAPI, LightGBM, PuLP, pandas/parquet.
- Current web UI is framework-free vanilla HTML/JS consuming the `web/data/*.json` export contract. The rebuild must preserve that contract (it decouples product from pipeline and enables scoreboard replay).
- **API tests do not exist today** — `api/main.py` has zero coverage (auth stub, caching, concurrency untested). The user initially assumed they existed; adding them is an explicit requirement, sequenced before/alongside Playwright.
- Concerns audit (`.planning/codebase/CONCERNS.md`) catalogs the hardening backlog: wide-open CORS, unpinned deps, file-handle leaks, silent cron failures (`|| true`), no schema validation on FPL payloads, unbounded solve cache, no monitoring, Chrome .deb bloat.
- Git repo initialized 2026-08-31 (single commit); `.github/workflows/` (daily/weekly) untracked and dormant until pushed to GitHub.
- **Time-critical, independent of this milestone**: the daily snapshot cron must run every day — price-model history cannot be backfilled (first snapshot 2026-08-31; model unlocks at 14 days).
- User's own FPL team id: 6980093 — use for rate-my-team / solver E2E fixtures instead of entry 1.
- FPL club crests/kits are trademarked assets — **resolved Phase 3**: neutral generated kit graphics (inline SVG, no CDN/crest/sponsor imagery), documented in docs/decisions/pitch-kit-sourcing.md; feeds the eventual payment-gateway legal review.
- pytest note: run with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` or keep `pytest.ini` plugin disables (`-p no:playwright -p no:seleniumbase` collide on `--browser`) — Playwright's pytest plugin will need config care if Python-based, or use the Node Playwright runner.

## Constraints

- **Tech stack**: Python 3.14 backend stays as-is; frontend rebuild is React + Vite — user's explicit choice
- **Contract**: `web/data/*.json` export schema is the API between pipeline and site — rebuild consumes it unchanged
- **Hosting**: No live infrastructure yet — CI must end at a published Docker image + static build artifact, not a deploy
- **Budget**: Solo developer, pre-revenue — prefer free tiers (GitHub Actions, GHCR) and boring, maintainable choices
- **Timeline**: Paid launch target pre-season July 2027; hardening must not disrupt the weekly recommendation cycle during the current season
- **Environment**: conda env `python314` at `/home/sraja/miniconda3/envs/python314/bin/python` for all Python work

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full React (Vite) rebuild, not incremental vanilla enhancement | Cleanest long-term base for a paid product; pitch UI wants componentization | — Pending |
| React chosen directly (no framework research phase) | User preference; largest ecosystem for component/pitch libraries | — Pending |
| Full parity: all 8 pages rebuilt this milestone | Avoid maintaining two frontends into launch | — Pending |
| CI ends at build + test + published Docker image (no live deploy) | Hosting not purchased; keeps milestone unblocked by infra decisions | ✓ Good — Phase 5: main-branch run green through GHCR publish, deploy step stubbed |
| Trivy scan report-only this milestone (D-10) | Gating on 187 base-image/dep CVEs would block launch prep on upstream fixes | — Pending: triage backlog for Phase 6 |
| uv as lockfile compiler, kept out of runtime lockfiles (D-01) | Only tool producing hash-verified locks; pip freeze forbidden (D-02) | ✓ Good — Phase 5: clean-venv --require-hashes install proven |
| Every push to GitHub is a human action (D-14); dispatch-only schedulers (D-12) | Pre-revenue repo safety; local WSL cron stays sole production scheduler | ✓ Good — Phase 5: first push caught 2 real CI bugs at the gate |
| API test suite added before/alongside Playwright | E2E on an untested API inverts the pyramid; API tests are the missing base layer | ✓ Good — Phase 1 shipped the suite (contract, auth, concurrency) green |
| Package-legitimacy gate: exact-pin installs against a human-approved list | Supply-chain hygiene for a pre-revenue solo project | ✓ Good — Phase 1: zero registry drift at install time |
| TypeScript 6.x (not 7.x) + Vite 7.3.6/plugin-react 5.2.0 pins | ESLint support for TS 7.0 unstable; deliberate downgrade pins | ✓ Good — Phase 1 scaffold stable |
| All three hardening areas in scope (security, reliability, observability) | These are the "production ready" bar the user asked for pre-monetization | ✓ Good — Phase 6: all 10 requirements shipped, 49 threats closed, UAT 2/2 |
| ops.jsonio as the single JSON I/O chokepoint, gated by a self-tested repo-wide scanner | A sweep without a regression gate decays; scanner has positive/negative controls so it can never silently stop detecting | ✓ Good — Phase 6: leak inventory gated at zero in CI |
| Runtime proof as a real-uvicorn script (verify_hardening.sh), not more TestClient tests | CORS enforcement and log redaction are properties of a genuinely running process TestClient cannot exercise | ✓ Good — Phase 6: wired into preflight Gate 7/8 |
| Atomic snapshot types (PoolSnapshot/GwPoolsSnapshot) + AST structural gate for cache concurrency | The REL-05 TOCTOU race survived four verification passes because tests stubbed the accessor; the guarantee is now structural, not observational | ✓ Good — Phase 6 wave 5 gap closure |
| PARITY-DEVIATIONS.md ledger records every intentional vanilla→React delta | Phase 7 cutover must distinguish approved changes from regressions without relying on memory | ✓ Good — Phase 2 seeded all 8 known deviations |
| Lockstep palette edits (React + vanilla in one commit) until CUT-01; fonts self-hosted via @fontsource, CDN removed | Vanilla stays authoritative pre-cutover; no third-party font requests leaking visitor IPs | ✓ Good — Phase 2, guarded by check-tokens.mjs on every test run |
| Neutral generated SVG kits, not FPL CDN shirt imagery | Trademark/passing-off exposure; no third-party origin dependency; posture documented in a committed decision doc | ✓ Good — Phase 3, UAT-signed-off; revisit at payment-gateway legal review |
| Continuous flex centering for pitch rows (fixed basis over max(5, n) parts) | Integer grid-column placement is exact only when row size and track count share parity — 2/4-card rows drifted half a column (G-03-1) | ✓ Good — Phase 3, symmetry-tested n∈{1..6}, visually confirmed |
| Client sends numeric player_code locks/excludes, never free-text names | Server's substring name-resolver never exercised by the rebuilt client; request-body test asserts no display names | ✓ Good — Phase 3 |
| E2E runs against a fixture-mode API server (`FPL_FIXTURE_DIR`), never the live FPL API | Suite must pass or fail on code, not the calendar; frozen v1 fixtures (normal/blank/DGW) with a manifest | ✓ Good — Phase 4: 42 specs deterministic |
| Fixture-mode seam uses capture-once + explicit restore of `predict.live._gw_pool` | Module reload alone left production bindings permanently monkeypatched after teardown (CR-01) | ✓ Good — Phase 4 gap closure, identity-asserted in tests |
| Rate-diff ghost card keyed off the sell target's actual pitch row (bench included) | Deriving row from the buy position rendered phantom rows and distorted the visual diff | ✓ Good — Phase 4 gap closure, adjacency-asserted in E2E |
| Pre-declared mechanical adoption bar (≥2,280 pts, D-05/D-07) with all experiment code merged behind default-off flags (D-08) | Experiments must be judged by the honest harness before any product change; rejected work stays inspectable, never silently dropped | ✓ Good — Phase 9: 8/8 experiments rejected on the bar, zero product wiring needed, export contract locked by regression test |
| RL dependency stack dev-only and hash-locked (`requirements-rl.txt`), never in Dockerfile/CI (D-09) | torch + gymnasium + SB3 are heavyweight experiment-only deps; production image must not carry them | ✓ Good — Phase 9: isolation proven by grep+parser assertion and byte-identical Dockerfile/workflows |
| Captain by mean xP retained over ceiling-EV quantile blend | Ceiling-EV capture gain (+1.5pt) fell below the pre-declared ≥+2pt bar; mechanical rule decided | ✓ Good — Phase 9: verdict recorded with numbers in IMPROVEMENTS.md |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-08 after Phase 9*
