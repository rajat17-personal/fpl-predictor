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

### Active

- [ ] React (Vite) rebuild of the web UI — full parity with all 8 existing pages (xP table/index, team, fixtures, prices, league, scoreboard, differentials, methodology)
- [ ] FPL-style pitch renderer: squad/XI laid out on a pitch with shirts/team visuals, used by team + solver views
- [ ] FastAPI integration test suite (TestClient): /solve, /rate, /team, auth stub, cache behavior, error responses
- [ ] Playwright E2E regression suite covering: team/pitch + solver flow, xP table + captains, rate-my-team, fixtures & prices pages
- [ ] Hardened CI/CD on GitHub Actions: lint, pytest, API tests, Playwright, Docker image build + publish for the API (deploy step stubbed — no live hosting yet)
- [ ] Security & config hardening: CORS restriction, pinned/locked dependencies, secrets via .env pattern, repo hygiene (remove 134MB Chrome .deb, proper .gitignore)
- [ ] Reliability fixes: file-handle leaks, cron error traps (remove `|| true`, add retries), FPL API schema validation, graceful JSON-load failures, solve-cache invalidation/LRU
- [ ] Observability: structured logging, health/monitoring endpoints, failure visibility/alerting for crons and FPL API outages

### Out of Scope

- Live deployment to Cloudflare Pages / Hetzner — hosting not yet purchased; CI produces a deployable image, deployment automation is the next milestone
- Auth (Supabase JWT) and payment integration — blocked on user's gateway/legal decision; `require_key()` stub stays the swap point
- Model/decision-quality improvements — the model is validated and strong; meta-pattern shows extra sophistication doesn't pay right now (see IMPROVEMENTS.md for the deferred list)
- FBref data integration — abandoned; site no longer serves advanced stat values
- A/B testing / feature-flag infrastructure — needed for model rollout experiments, but post-launch concern

## Context

- Brownfield: complete codebase map in `.planning/codebase/` (2026-08-31). Batch ML pipeline + product layers; Python 3.14 (conda env `python314`), FastAPI, LightGBM, PuLP, pandas/parquet.
- Current web UI is framework-free vanilla HTML/JS consuming the `web/data/*.json` export contract. The rebuild must preserve that contract (it decouples product from pipeline and enables scoreboard replay).
- **API tests do not exist today** — `api/main.py` has zero coverage (auth stub, caching, concurrency untested). The user initially assumed they existed; adding them is an explicit requirement, sequenced before/alongside Playwright.
- Concerns audit (`.planning/codebase/CONCERNS.md`) catalogs the hardening backlog: wide-open CORS, unpinned deps, file-handle leaks, silent cron failures (`|| true`), no schema validation on FPL payloads, unbounded solve cache, no monitoring, Chrome .deb bloat.
- Git repo initialized 2026-08-31 (single commit); `.github/workflows/` (daily/weekly) untracked and dormant until pushed to GitHub.
- **Time-critical, independent of this milestone**: the daily snapshot cron must run every day — price-model history cannot be backfilled (first snapshot 2026-08-31; model unlocks at 14 days).
- User's own FPL team id: 6980093 — use for rate-my-team / solver E2E fixtures instead of entry 1.
- FPL club crests/kits are trademarked assets; the pitch renderer should use FPL's own shirt image CDN (as the official app does) or neutral generated kit graphics — resolve during UI design.
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
| CI ends at build + test + published Docker image (no live deploy) | Hosting not purchased; keeps milestone unblocked by infra decisions | — Pending |
| API test suite added before/alongside Playwright | E2E on an untested API inverts the pyramid; API tests are the missing base layer | — Pending |
| All three hardening areas in scope (security, reliability, observability) | These are the "production ready" bar the user asked for pre-monetization | — Pending |

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
*Last updated: 2026-08-31 after initialization*
