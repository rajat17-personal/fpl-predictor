# Codebase Structure

**Analysis Date:** 2026-09-11

**last_mapped_commit:** 382338e2c164a4433cd73cdbb12ffc9be2621493

## Directory Layout

```
fpl/
├── config.py                        # Constants, paths, seasons, FPL rules, feature lists
├── requirements.txt                 # Python dependencies (pandas, lightgbm, pulp, etc.)
├── requirements.in                  # Pinned + commented version of requirements.txt
├── requirements-dev.txt             # Dev-only: pytest, responses, ruff
├── requirements-dev.in              # -r requirements.in + dev tools
├── requirements-rl.txt              # (Future) RL experimentation deps
├── requirements-rl.in               # (Future) RL source file
├── pytest.ini                       # Test runner config (Python)
├── ruff.toml                        # Python linting (CI-01 lint step, D-07)
├── Dockerfile                       # Multi-stage Docker image (builder + runtime, D-04/D-05)
├── .dockerignore                    # Build-context exclusions (no model, no test code, bake frontend/dist)
├── .env.example                     # Secret configuration template (do not commit .env)
├── .gitignore                       # VCS exclusions (data/raw, data/processed, models/artifacts)
├── README.md                        # Quick start + product overview
├── PLAN.md                          # Build log, experiments, findings (phases 0–13)
├── ROADMAP.md                       # Productization status & roadmap (phases A–E)
├── PROJECT_INDEX.md                 # Module index + entry points
├── PROJECT_INDEX.json               # Same in JSON format (for tools)
├── IMPROVEMENTS.md                  # Known limitations & ideas
│
├── data/                            # Data ingestion & processing
│   ├── ingest.py                    # Fetch vaastav + FPL API (core)
│   ├── build_table.py               # → player_gw.parquet (canonical)
│   ├── id_map.py                    # Stable player_code across seasons + live
│   ├── odds.py                      # football-data.co.uk → implied probabilities
│   ├── snapshot.py                  # Daily bootstrap → data/snapshots/ (idempotent)
│   ├── live_history.py              # Refresh current-season form cache
│   ├── live_odds.py                 # Live odds fetch (for rolling updates)
│   │
│   ├── fbref.py                     # FBref scraper (optional, needs Chrome, kill-switch)
│   ├── transfermarkt.py             # Transfermarkt injury backfill (10-07, kill-switch)
│   ├── understat.py                 # Understat xG/xA scraping (optional, kill-switch)
│   ├── fotmob.py                    # FotMob team stats (optional, kill-switch)
│   ├── fplreview.py                 # FPLReview data (optional, kill-switch)
│   ├── fpl_standings.py             # FPL standings/projections (optional, kill-switch)
│   ├── team_strength.py             # Team strength ratings (optional, kill-switch)
│   ├── availability.py              # Player availability (optional, kill-switch)
│   ├── id_crosswalk.py              # ID mapping across sources (optional, kill-switch)
│   │
│   ├── raw/                         # Cached downloads (do not edit)
│   │   ├── 2016-17...2026-27/       # Per-season vaastav history (GW→player records)
│   │   ├── live/                    # FPL API snapshots (bootstrap-static.json, fixtures.json)
│   │   ├── odds/                    # football-data.co.uk fixtures + odds
│   │   ├── fbref/                   # FBref scraped advanced stats (if enabled)
│   │   └── [other-scrapers]/        # Per-scraper cached data (transfermarkt, understat, etc.)
│   ├── processed/                   # Canonical parquet tables
│   │   ├── player_gw.parquet        # Canonical: [gw, player_id, minutes, points, ...]
│   │   ├── features.parquet         # ML-ready: + rolling form + context
│   │   ├── id_map.parquet           # Season-local id → stable player_code
│   │   ├── odds.parquet             # Fixture-level odds (de-overrounded)
│   │   └── test_predictions.parquet # Frozen predictions from backtest
│   ├── snapshots/                   # Daily price/metadata snapshots (do not lose)
│   │   └── *.parquet                # One per UTC day; used for price-model training
│   └── cron.log                     # Persistent log from scripts/daily.sh + scripts/weekly.sh
│
├── features/                        # Feature engineering
│   └── engineer.py                  # Rolling form (3/5/10/all), context → features.parquet
│
├── models/                          # ML model training & artifacts
│   ├── train.py                     # Two-stage hurdle xP model, per position (LightGBM)
│   ├── tune.py                      # Hyperparameter search (validation-scored)
│   ├── calibration.py               # Isotonic regression calibration
│   ├── intervals.py                 # Fit p10/p90 confidence bands per position×xp-bucket
│   ├── price.py                     # Price change watchlist (heuristic → LightGBM at 14+ days)
│   └── artifacts/                   # Saved model weights + intervals (not committed)
│       ├── xp_model.joblib          # Trained two-stage model
│       ├── *.joblib                 # Intervals, calibration, price model artifacts
│       └── .gitignore               # (artifacts/ explicitly ignored)
│
├── optimize/                        # Integer linear programming (ILP) solvers
│   ├── squad_ilp.py                 # Squad + XI + captain selection (from scratch)
│   ├── transfers.py                 # Weekly transfer ILP (sell/buy decisions)
│   ├── chips.py                     # Chip scheduling (DGW/BGW + heuristic timing)
│   ├── pricing.py                   # 50% sell-on fee calculation
│   ├── multi_period.py              # Multi-GW horizon expansion (lookahead)
│   └── __init__.py
│
├── backtest/                        # Multi-season validation & simulation
│   ├── season.py                    # Season state machine (transfers, chips, autosubs, scoring)
│   ├── walk_forward.py              # Expanding-window backtest + jitter CIs
│   ├── horizons.py                  # Multi-period scenario helpers
│   ├── multi_period_season.py       # Season sim with multi-period constraints
│   └── __init__.py
│
├── predict/                         # Live prediction & product export
│   ├── live.py                      # This week's recommendation (FPL API → ILP)
│   ├── export.py                    # Export xp_table/captains/squad/chips → web/data/
│   ├── scoreboard.py                # Post-GW accuracy (MAE + Spearman vs ep_next)
│   ├── digest.py                    # Email digest (plain-text + HTML)
│   └── __init__.py
│
├── api/                             # Solver API (FastAPI)
│   ├── main.py                      # Endpoints: /api/solve, /api/rate, /api/team; serves web/
│   └── __init__.py
│
├── web/                             # Static site (vanilla HTML/JS, legacy)
│   ├── index.html                   # Main page (xp table, squad, captains)
│   ├── team.html                    # Team editor (rate-my-team)
│   ├── scoreboard.html              # Post-GW accuracy feed
│   ├── fixtures.html                # Fixture difficulty ticker
│   ├── league.html                  # League standings (projected)
│   ├── prices.html                  # Price change watchlist
│   ├── methodology.html             # How it works (documentation)
│   ├── differentials.html           # Differential picks (vs league average)
│   ├── config.js                    # API_BASE env var for custom API endpoint
│   ├── assets/                      # CSS, fonts, images
│   │   └── app.js                   # Client-side app (table rendering, filters, API calls)
│   └── data/                        # JSON export contract (refreshed weekly)
│       ├── meta.json                # Gameweek, deadline, model timestamp
│       ├── xp_table.json            # All players: xP, p10/p90, price, ownership, status
│       ├── captains.json            # Top-10 captain picks
│       ├── squad.json               # Optimal 15-man + 11-man + captain
│       ├── fixtures.json            # Team difficulty ticker (next 6 GWs)
│       ├── chips.json               # DGW/BGW structure + chip note
│       ├── watchlist.json           # Price movers + model-based recommendations
│       ├── standings.json           # League projections
│       ├── leaders.json             # Top performers (xP, owned)
│       ├── digest.html              # Email digest HTML (if digest.py runs)
│       └── history/                 # Frozen predictions (for scoreboard replay)
│           └── gw{N}.json           # Per-GW: frozen xP + FPL's ep_next + actual (after GW ends)
│
├── frontend/                        # React + TypeScript rebuild (new, Phase B)
│   ├── package.json                 # Node.js dependencies (React, Vite, TailwindCSS, TypeScript)
│   ├── package-lock.json            # Lockfile
│   ├── vite.config.ts               # Vite build config + dev proxy (/api, /data → localhost:8000)
│   ├── vitest.config.ts             # Vitest config (unit/component tests)
│   ├── tsconfig.json                # TypeScript config
│   ├── index.html                   # Entry HTML (mounts React at #root)
│   ├── src/
│   │   ├── main.tsx                 # React app entry point (creates root, renders router)
│   │   ├── router.tsx               # React Router config (8 routes + error boundaries)
│   │   ├── index.css                # Global Tailwind CSS
│   │   ├── components/              # Reusable React components
│   │   │   ├── PageShell.tsx        # Layout wrapper (header, nav, footer)
│   │   │   ├── GwBanner.tsx         # Gameweek + deadline display
│   │   │   ├── ErrorState.tsx       # Error boundary for graceful failures
│   │   │   ├── Spinner.tsx          # Loading indicator
│   │   │   ├── ThemeToggle.tsx      # Light/dark mode switch
│   │   │   ├── BandCell.tsx         # p10/p90 interval cell renderer
│   │   │   ├── FdrCell.tsx          # Fixture difficulty cell
│   │   │   ├── EmptyState.tsx       # Empty state placeholder
│   │   │   ├── NotFoundPage.tsx     # 404 page
│   │   │   └── *.test.tsx           # Component unit tests (Vitest)
│   │   ├── routes/                  # Page-level route components (React Router)
│   │   │   ├── XpTable.tsx          # Main xP table (D-06, sortable, filterable)
│   │   │   ├── Team.tsx             # Rate-my-team (current squad + improvements)
│   │   │   ├── Fixtures.tsx         # Team fixture ticker
│   │   │   ├── Prices.tsx           # Price movers (watchlist)
│   │   │   ├── League.tsx           # League standings + projections
│   │   │   ├── Scoreboard.tsx       # Post-GW accuracy + historical
│   │   │   ├── Differentials.tsx    # Differential picks vs average ownership
│   │   │   ├── Methodology.tsx      # Documentation page (markdown)
│   │   │   └── *.test.tsx           # Route integration tests
│   │   ├── lib/                     # Utility functions & hooks (no JSX)
│   │   │   ├── api.ts               # Typed interfaces for JSON contract (MetaResponse, XpRow, etc.)
│   │   │   ├── format.ts            # Number formatting (fixed1, fixed2, orDash)
│   │   │   ├── sortable.ts          # Sortable table logic (useSortable hook, sortRows)
│   │   │   ├── theme.ts             # Light/dark theme logic (useTheme hook)
│   │   │   ├── deadline.ts          # Gameweek deadline calculation
│   │   │   ├── bandCell.ts          # p10/p90 band rendering helper
│   │   │   ├── statusFlag.tsx       # Injury/news status renderer
│   │   │   ├── usePageMeta.ts       # <title> + <meta> tag updater (per route)
│   │   │   └── *.test.ts            # Utility function tests
│   │   ├── test/                    # Test fixtures + setup
│   │   │   ├── setup.ts             # Vitest + React Testing Library config
│   │   │   ├── harness.test.tsx     # Integration test harness (memoryRouter, full flow)
│   │   │   ├── routeIsolation.test.tsx # Each route can fail independently (error boundaries)
│   │   │   └── fixtures/            # Mock JSON data for tests
│   │   │       ├── xp_table.json
│   │   │       ├── captains.json
│   │   │       ├── meta.json
│   │   │       ├── fixtures.json
│   │   │       ├── watchlist_*.json
│   │   │       ├── standings.json
│   │   │       ├── leaders.json
│   │   │       └── scoreboard.json
│   │   ├── content/                 # Markdown files (Methodology page)
│   │   │   └── methodology.md
│   │   └── vite-env.d.ts            # Vite type definitions
│   ├── dist/                        # Production build output (generated by `npm run build`)
│   │   ├── index.html               # Built entry HTML
│   │   ├── assets/                  # Bundled JS + CSS + fonts
│   │   └── favicon.svg
│   └── public/                      # Static assets (copied to dist/ as-is)
│       └── favicon.svg
│
├── e2e/                             # End-to-end testing (Playwright, Phase E)
│   ├── package.json                 # Node.js deps (playwright, @playwright/test)
│   ├── package-lock.json            # Lockfile
│   ├── playwright.config.ts         # Playwright test config (base URL, browsers, reporters)
│   ├── tsconfig.json                # TypeScript config for E2E
│   │
│   ├── specs/                       # Test spec files (Playwright)
│   │   ├── smoke.spec.ts            # Smoke test: site loads, no console errors
│   │   ├── xp-table.spec.ts         # XP table: sort, filter, search, intervals render
│   │   ├── team-solver.spec.ts      # API /api/solve: lock/exclude players, multi-period
│   │   ├── team-plan.spec.ts        # Multi-GW planning: chip selection, lookahead
│   │   ├── rate-my-team.spec.ts     # /api/rate/{entry}: fetch + compare to optimum
│   │   ├── fixtures-prices.spec.ts  # Fixtures and prices routes render correctly
│   │   └── shell-geometry.spec.ts   # Responsive design: mobile/tablet/desktop viewports
│   │
│   ├── helpers/                     # Shared test utilities
│   │   └── page.ts                  # Page object model (loginPage(), goToXpTable(), etc.)
│   │
│   ├── parity/                      # Contract compliance checking
│   │   ├── ledger.mjs               # Record per-test export hash + frontend version (append-only)
│   │   ├── extract.mjs              # Pull export contract metadata from web/data/
│   │   └── parity-diff.mjs          # Diff ledger entries to detect regressions
│   │
│   ├── scripts/                     # Helper scripts
│   │   ├── synthesize-variants.mjs  # Generate test variant URLs + payloads
│   │   └── capture_fixtures.py      # Python helper: prep fixture data for E2E tests
│   │
│   ├── fixtures/                    # Test data (generated by capture_fixtures.py)
│   │   └── [gw-specific-payloads]   # Precomputed API responses for isolated tests
│   │
│   ├── test-results/                # Test run output (not committed)
│   │   └── .last-run.json           # Last run metadata
│   │
│   ├── playwright-report/           # HTML report (generated, not committed)
│   │   └── index.html
│   │
│   └── node_modules/                # Dependencies (not committed)
│
├── scripts/                         # Cron entry points
│   ├── daily.sh                     # 02:30 UTC: snapshot + price model + watchlist + scoreboard
│   └── weekly.sh                    # 08:00 UTC Fridays: live_history + export + digest
│
├── .github/                         # GitHub Actions (mirrors cron scripts)
│   └── workflows/
│       ├── daily.yml                # GitHub Actions version of daily.sh (scheduled cron)
│       ├── weekly.yml               # GitHub Actions version of weekly.sh (scheduled cron)
│       └── [other workflows]        # CI gates (lint, test, E2E, Docker build, publish)
│
├── tests/                           # Pytest suite (Python, comprehensive hardening)
│   ├── conftest.py                  # Pytest fixtures + shared setup
│   │
│   ├── test_api.py                  # API endpoint tests (/api/solve, /api/rate, /api/team, /api/health)
│   ├── test_api_hardening.py        # (NEW) API hardening: error responses, auth, caching, timeouts
│   ├── test_product.py              # Integration tests (intervals, snapshot, export, price, solver, API, digest)
│   ├── test_legality.py             # ILP results obey FPL rules (budget, positions, formations, max-per-club)
│   ├── test_leakage.py              # No match outcome in pre-match features (temporal validation)
│   ├── test_autosub.py              # Autosub + vice-captain logic (bench→XI, captain fallback)
│   │
│   ├── test_transfermarkt.py        # (NEW) Transfermarkt scraper: probe, build, attach
│   ├── test_availability.py         # (NEW) Player availability data source
│   ├── test_crosswalk.py            # (NEW) ID mapping across sources
│   ├── test_chips.py                # (NEW) Chip scheduling + validity
│   ├── test_cron.py                 # (NEW) Cron script validation (daily.sh, weekly.sh)
│   │
│   ├── test_reliability.py          # (NEW) Resilience: retries, timeouts, missing data
│   ├── test_fixture_mode.py         # (NEW) API in fixture mode (no model, precomputed results)
│   ├── test_react_seam.py           # (NEW) Export contract ↔ React interfaces parity
│   ├── test_scoreboard.py           # (NEW) Scoreboard: accuracy, ranking, frozen history
│   │
│   ├── test_experiments.py          # (NEW) Experimental features + ablations
│   ├── test_bracket.py              # (NEW) Bracket/tournament mode (if implemented)
│   ├── test_obs.py                  # (NEW) Observation space for RL (if implemented)
│   ├── test_rl_env.py               # (NEW) RL environment integration (if implemented)
│   ├── test_capture_fixtures.py     # (NEW) E2E fixture capture tool validation
│   ├── test_payloads.py             # (NEW) Request/response payload validation
│   │
│   └── [other test modules]         # Per-component hardening tests
│
├── docs/                            # Documentation
│   └── decisions/                   # Architecture decision records (ADRs)
│       └── [ADR files]              # Decisions made during development
│
├── .planning/                       # GSD codebase mapping & planning artifacts
│   ├── codebase/
│   │   ├── ARCHITECTURE.md          # System overview, layers, data flow, abstractions (this document)
│   │   └── STRUCTURE.md             # Directory layout & naming conventions (this file)
│   ├── phases/                      # Phase-specific planning docs (generated by /gsd-phase)
│   ├── milestone.lock               # Lock file (orchestrator state)
│   └── state.json                   # GSD state (current phase, progress)
│
├── .claude/                         # Project configuration
│   └── CLAUDE.md                    # Project instructions (tech stack, conventions, constraints)
│
├── .gitignore                       # VCS exclusions
├── .dockerignore                    # Docker build-context exclusions (no model, no tests)
└── __pycache__, .pytest_cache/      # Generated cache directories
```

## Directory Purposes

**config.py:**
- Purpose: Single source of truth for constants, paths, seasons, FPL rules, feature lists
- Key exports: `ROOT`, `SEASONS`, `TRAIN/VAL/TEST`, `BUDGET`, `POSITION_QUOTA`, `WINDOWS`, `SET_PIECE_COLS`, `ODDS_COLS`, `FBREF_COLS`
- Imported by: All Python modules
- Do not edit during runs: Changing `SEASONS` or `TRAIN_SEASONS` requires re-running the entire pipeline

**data/:**
- Purpose: Ingest raw data from multiple sources, canonicalize, produce parquet tables consumed by ML
- Key outputs:
  - `data/raw/`: Cached downloads (vaastav per-season CSVs, FPL API JSON snapshots, scraper outputs)
  - `data/processed/`: Canonical parquet tables (player_gw, features, id_map, odds, test_predictions)
  - `data/snapshots/`: Daily snapshots (price, metadata); not backfillable — do not lose
- Scraping strategy: Each scraper (transfermarkt, understat, etc.) has module-level kill-switch; probe-first for access validation
- Responsibility: Handle external API failures, normalize schema, backfill missing columns, attach to canonical table

**features/:**
- Purpose: Engineer leakage-safe rolling form + context features
- Key output: `data/processed/features.parquet`
- Constraint: Every rolling feature must be shifted by one (no leakage of a match into its own prediction)
- Single file: `engineer.py` (consolidated into one module for clarity)

**models/:**
- Purpose: Train, tune, calibrate two-stage per-position xP model + auxiliary models (price, intervals)
- Key outputs:
  - `models/artifacts/xp_model.joblib`: Trained LightGBM models (GK, DEF, MID, FWD)
  - `models/artifacts/*.joblib`: Intervals (p10/p90), calibration, price model
- Splits: `models/train.py` (train + predict), `models/tune.py` (hyperparameter search), `models/calibration.py` (isotonic regression), `models/intervals.py` (confidence bands), `models/price.py` (watchlist)
- Constraint: All training must use time-based splits (train < val < test seasons, no random splits)

**optimize/:**
- Purpose: Solve ILP for squad, transfers, chips
- Key modules:
  - `squad_ilp.py`: Squad + XI + captain (from-scratch or current squad)
  - `transfers.py`: Weekly sell/buy ILP (with hit cost, sell-on fee)
  - `chips.py`: Chip scheduling + timing heuristics
  - `multi_period.py`: Multi-GW lookahead (chain single-GW solves)
- No persistent state: All solves are computed on-demand from input xP + squad state

**backtest/:**
- Purpose: Multi-season walk-forward validation with noise controls
- Key modules:
  - `season.py`: Season state machine (GW-by-GW simulation with transfers, autosubs, scoring)
  - `walk_forward.py`: For each test season, retrain on prior seasons, test on current
  - Outputs: Per-season results (points, MAE vs ep_next, isolated chip value) + confidence bands
- Constraint: Each test season must retrain on its prior seasons (expanding window, never fixed training set)

**predict/:**
- Purpose: Generate live recommendations + product exports
- Key modules:
  - `live.py`: FPL API → pool → ILP → recommendation (interactive CLI)
  - `export.py`: Pool → JSON contract (xp_table, captains, squad, chips) for web/data/
  - `scoreboard.py`: Post-GW accuracy measurement (vs FPL's ep_next + actual)
  - `digest.py`: Render email (plain-text + HTML)
- Output contract: `web/data/*.json` (frozen snapshots; site reads from here)

**api/:**
- Purpose: FastAPI app; solver API + static site serving
- Single file: `main.py` (consolidated for simplicity)
- Endpoints: `/api/solve`, `/api/rate/{entry}`, `/api/team/{entry}`, `GET /` (static files)
- State: Thread-safe `_state` dict (FPL snapshot, cached pools, artifact) + `_solve_cache`
- Auth stub: `require_key()` (replace when payments land)
- StaticFiles mount: Serves `web/` directory at "/" (enables both API + static HTML)
- Fixture mode: If `FPL_FIXTURE_DIR` env set, runs without model (precomputed results)

**web/:**
- Purpose: Framework-free static site + JSON contract (legacy, kept live during transition)
- HTML pages: `index.html` (xp table), `team.html` (rate-my-team), `scoreboard.html`, `fixtures.html`, etc.
- Client app: `assets/app.js` (table rendering, API calls, filters)
- Data: `web/data/` JSON files (xp_table, captains, squad, etc.); refreshed weekly by export.py
- Deployment: Deploy `web/` directory to Cloudflare Pages (or any static host)
- Lifetime: Coexists with React frontend; can be removed once migration is complete

**frontend/:**
- Purpose: Modern React + TypeScript rebuild of the UI (new layer, Phase B)
- Structure:
  - `src/main.tsx`: React app entry point (mounts to #root)
  - `src/router.tsx`: Route definitions (8 routes + error boundaries per route)
  - `src/components/`: Reusable UI components (PageShell, Spinner, ErrorState, BandCell, FdrCell, etc.)
  - `src/routes/`: Page-level components (XpTable, Team, Fixtures, Prices, League, Scoreboard, Differentials, Methodology)
  - `src/lib/`: Utilities (api.ts with typed interfaces, format.ts, sortable.ts, theme.ts, usePageMeta.ts, etc.)
  - `src/test/`: Test setup + fixtures (mock JSON data mirroring web/data/ schema)
- Build:
  - Dev: `npm run dev` (Vite dev server on port 5173, proxies /api and /data to localhost:8000)
  - Prod: `npm run build` (TypeScript compilation + Vite bundling → dist/)
  - Preview: `npm run preview` (serves dist/ locally)
- Testing: Vitest + React Testing Library (unit tests in components/ and lib/, integration in routes/)
- Data contract: Consumes identical JSON from `/data/*` as legacy site; type-safe via api.ts interfaces
- Dependency: @tanstack/react-query (data fetching + caching), react-router (routing), tailwindcss (styling)

**e2e/:**
- Purpose: Browser-based validation of frontend + API parity (new layer, Phase E)
- Structure:
  - `specs/`: 7 test files (smoke, xp-table, team-solver, team-plan, rate-my-team, fixtures-prices, shell-geometry)
  - `helpers/`: Shared page utilities (page object model)
  - `parity/`: Contract compliance ledger (append-only, per-test export hash + version)
  - `scripts/`: Test utilities (synthesize variants, capture fixtures)
  - `fixtures/`: Precomputed API responses for isolated tests
- Run: `cd e2e && npm test` or specific `npx playwright test specs/xp-table.spec.ts`
- Environments: Dev (localhost:5173 for Vite), staging (Docker), prod (deployed site)
- Parity: `ledger.mjs` records per-test result; `parity-diff.mjs` detects regressions

**scripts/:**
- Purpose: Cron entry points for daily + weekly jobs
- `daily.sh`: Runs snapshot → price model → watchlist → scoreboard (02:30 UTC)
- `weekly.sh`: Runs live_history → export → digest (08:00 UTC Fridays)
- Both use the Python env: `/home/sraja/miniconda3/envs/python314/bin/python`
- Logs to `data/cron.log` (append-only)

**tests/:**
- Purpose: Comprehensive testing suite for correctness, legality, hardening (22 Python test modules)
- Key files:
  - Core: `test_api.py`, `test_product.py`, `test_legality.py`, `test_leakage.py`, `test_autosub.py`
  - Hardening: `test_api_hardening.py`, `test_reliability.py`, `test_fixture_mode.py`
  - Data: `test_transfermarkt.py`, `test_availability.py`, `test_crosswalk.py`
  - Frontend seam: `test_react_seam.py` (export contract parity)
  - Integration: `test_cron.py`, `test_chips.py`, `test_scoreboard.py`
  - Future: `test_rl_env.py`, `test_obs.py`, `test_bracket.py` (for upcoming features)
- Run: `python -m pytest` (all) or `pytest tests/test_legality.py -v` (specific)

**.github/workflows/:**
- Purpose: GitHub Actions mirrors of cron scripts + CI gates (if repo is pushed to GitHub)
- Files: `daily.yml`, `weekly.yml` (schedule), plus lint/test/build/publish gates
- Trigger: Push to main (or scheduled via cron expression in workflow file)

**.planning/codebase/:**
- Purpose: Auto-generated codebase documentation (this directory)
- Files: `ARCHITECTURE.md`, `STRUCTURE.md` (this file)
- Do not edit by hand; regenerated by `/gsd-map-codebase --arch`

**Dockerfile & .dockerignore:**
- Purpose: Production-hardened, reproducible runtime image (Phase D hardening)
- Strategy: Multi-stage build
  - Builder: `pip install --require-hashes` from `requirements.txt` (D-04)
  - Runtime: `python:3.14-slim` + `libstdc++6` (CBC) + `libgomp1` (LightGBM)
  - Non-root: `appuser` UID 10001
  - No model artifact: Supplied at deploy time (D-05)
  - Both frontends baked in: web/ + frontend/dist/ (D-06)
- Exclusions in `.dockerignore`: No .env, model artifacts, test code, pipeline data (D-05/D-06)
- Deployment: Push to GHCR; mount secrets + model at runtime

## Key File Locations

**Entry Points:**
- `config.py`: Master constants + imports (import first in any new module)
- `data/ingest.py`: `fetch_fpl_live()`, `fetch_vaastav_season()` (data ingestion)
- `features/engineer.py`: `add_features(df)` → features.parquet
- `models/train.py`: `train_predict()`, `predict_xp()` (model training + inference)
- `backtest/walk_forward.py`: `main()` (multi-season backtest)
- `predict/live.py`: `main()` (interactive recommendation)
- `predict/export.py`: `export()` (weekly JSON export)
- `api/main.py`: FastAPI `app` (solver API + static site)
- `frontend/src/main.tsx`: React app entry (mounts to #root)
- `frontend/src/router.tsx`: Route definitions
- `e2e/playwright.config.ts`: E2E test configuration
- `e2e/specs/`: Individual test specs (7 files)

**Configuration:**
- `config.py`: Paths, seasons, FPL rules, feature lists (Python)
- `requirements.txt`: Python dependencies (hash-locked)
- `requirements-dev.txt`: Dev-only tools (pytest, ruff, responses)
- `pytest.ini`: Test runner config (Python)
- `ruff.toml`: Linting config (CI-01 lint step)
- `frontend/package.json`: Node.js dependencies (React, Vite, TailwindCSS)
- `frontend/vite.config.ts`: Vite build config + dev proxy
- `frontend/vitest.config.ts`: Vitest test config
- `e2e/package.json`: Playwright + E2E tools
- `e2e/playwright.config.ts`: Playwright test config
- `web/config.js`: Client-side API base URL (legacy site)
- `Dockerfile`: Container image build (multi-stage)
- `.dockerignore`: Build-context exclusions

**Core Logic:**
- `data/build_table.py`: Canonical player_gw table builder
- `data/transfermarkt.py`: Injury history scraper (optional, kill-switched)
- `features/engineer.py`: Rolling form + context
- `models/train.py`: Two-stage hurdle model
- `optimize/squad_ilp.py`: Squad selection ILP
- `optimize/transfers.py`: Weekly transfer ILP
- `backtest/season.py`: Season state machine
- `predict/export.py`: JSON export orchestrator
- `api/main.py`: FastAPI app + solver
- `frontend/src/routes/XpTable.tsx`: Main xP table (React)
- `frontend/src/routes/Team.tsx`: Rate-my-team (React)
- `e2e/specs/xp-table.spec.ts`: XP table E2E tests

**Testing:**
- `tests/test_api.py`: API endpoint tests
- `tests/test_legality.py`: Constraint validation
- `tests/test_leakage.py`: Feature leakage detection
- `tests/test_autosub.py`: Autosub simulation
- `tests/test_api_hardening.py`: API hardening tests
- `tests/test_transfermarkt.py`: Scraper validation
- `tests/test_react_seam.py`: Export contract parity
- `tests/test_cron.py`: Cron script validation
- `frontend/src/components/*.test.tsx`: Component unit tests
- `frontend/src/routes/*.test.tsx`: Route integration tests
- `frontend/src/lib/*.test.ts`: Utility function tests
- `frontend/src/test/harness.test.tsx`: Full app integration harness
- `e2e/specs/*.spec.ts`: Playwright E2E tests
- `e2e/parity/ledger.mjs`: Contract compliance ledger

## Naming Conventions

**Files:**
- `*.py`: Python modules (snake_case with `_` prefixes for private functions, no suffix for public ones)
- `config.py`: Master constants file (not config/ directory, single file only)
- `main.py`: Entry point for a package (e.g., `api/main.py` for FastAPI app, `frontend/src/main.tsx` for React)
- `train.py`, `ingest.py`, `engineer.py`: Verb names (what the module does)
- `.html`: Static site pages; hyphenated names (index.html, team.html, scoreboard.html)
- `.json`: Data exports (lowercase, underscored: xp_table.json, captains.json, meta.json)
- `.tsx`: React components (PascalCase: XpTable.tsx, PageShell.tsx)
- `.ts`: TypeScript utilities (camelCase: api.ts, format.ts)
- `.spec.ts`: Playwright E2E tests (PascalCase module name + `.spec.ts`)

**Directories:**
- `data/`, `features/`, `models/`, `optimize/`, `backtest/`, `predict/`, `api/`, `web/`, `frontend/`, `e2e/`, `tests/`, `scripts/`: Phase/component names
- `data/raw/`: Cached downloads (do not edit)
- `data/processed/`: Canonical tables (outputs of pipeline)
- `data/snapshots/`: Daily snapshots (critical, not backfillable)
- `models/artifacts/`: Saved model weights + intervals
- `web/data/`: JSON export contract (weekly)
- `web/data/history/`: Frozen predictions per GW (for scoreboard)
- `frontend/src/components/`: Reusable React components
- `frontend/src/routes/`: Page-level route components (one per route)
- `frontend/src/lib/`: Utility functions + hooks (no JSX)
- `frontend/src/test/`: Test setup + fixtures
- `e2e/specs/`: Playwright test specs (one per major feature)
- `e2e/helpers/`: Shared page utilities
- `e2e/parity/`: Contract compliance tracking

**Columns (Dataframes):**
- `player_code`: Stable player ID across seasons (int, primary key in production)
- `player_id`: Season-local FPL player ID (int, changes between seasons)
- `gw`: Gameweek (int, 1-38)
- `xp`, `xp_capt`: Expected points + captain value (float)
- `y_points`, `y_minutes`, `y_played`: Targets (float / int / binary)
- `*_r3`, `*_r5`, `*_r10`, `*_rall`: Rolling stats (3/5/10/all-game windows)
- `p10`, `p90`: Confidence interval bounds (float, from intervals.py)
- `price_m`: Player price in £ millions (float)
- `fdr_self`, `fdr_opp`: Fixture difficulty rating (int, 1-5)
- `is_dgw`: Double gameweek flag (bool)
- `injury_status_as_of`: Injury status from Transfermarkt (string, date-joined for pre-match context)

**Functions (Python):**
- `build_*()`: Construct a data structure (e.g., `build_pool()`, `build_table()`)
- `load_*()`: Read from disk (e.g., `load_features()`, `load_artifact()`)
- `fetch_*()`: Retrieve from external API (e.g., `fetch_fpl_live()`)
- `predict_*()`: Generate predictions (e.g., `predict_xp()`)
- `optimize_*()`: Solve an ILP (e.g., `optimize_gw()`)
- `_*()`: Private/internal function (leading underscore)
- `*_gw()`: Functions operating on a single gameweek (e.g., `optimize_gw()`)

**Functions (TypeScript/React):**
- `use*()`: React hooks (e.g., `useSortable`, `usePageMeta`, `useTheme`)
- `*Cell()`: Component that renders a table cell (e.g., `BandCell`, `FdrCell`)
- `*State()`: Component for state display (e.g., `ErrorState`, `EmptyState`)
- `*Flag()`: Component for status indicators (e.g., `StatusFlag`)
- `fetch*()`: Data fetching functions (e.g., `fetchJson`, `fetchApi`)
- `*Row`: TypeScript interface for a JSON row (e.g., `XpRow`, `CaptainRow`)

## Where to Add New Code

**New Feature (Python, e.g., additional rolling window):**
- Edit: `features/engineer.py:add_features()` to add new `feat[col] = ...` line
- Rerun: `python -m features.engineer` to regenerate `data/processed/features.parquet`
- Retrain: `python -m models.train` to pick it up in the next model
- Test: `python -m backtest.walk_forward` to measure impact

**New Data Source (Python, e.g., additional external API):**
- Add fetch function: `data/<source>.py` (e.g., `data/fancy_stats.py:fetch_fancy_stats()`)
- Add kill-switch: Module-level `*_ENABLED = True` (follow transfermarkt.py pattern)
- Attach to canonical: Edit `data/build_table.py:build()` to call `fancy_stats.attach()` if enabled
- Add config: Export columns to `config.FANCY_STATS_COLS` if optional
- Rerun: `python -m data.build_table` → `python -m features.engineer` → retrain

**New API Endpoint (Python, e.g., /api/transfers-advice):**
- Edit: `api/main.py` to add new `@app.get()` or `@app.post()` decorated function
- Logic: Call `optimize/transfers.py:optimize_gw()` or similar
- Cache: Consider `_solve_cache` if expensive; else compute on-demand
- Auth: Wrap with `@require_key()` if API_KEYS env set
- Test: `curl http://localhost:8000/api/transfers-advice?gw=1`

**New React Route (e.g., player comparison tool):**
- Create: `frontend/src/routes/<PageName>.tsx` (React component with useQuery to fetch data)
- Router: Add entry to `frontend/src/router.tsx` routes array
- Component: Implement error boundary via `<RouteErrorBoundary resource="..."/>`
- Type-safe: Add interfaces to `frontend/src/lib/api.ts` if new JSON is needed
- Test: Add `frontend/src/routes/<PageName>.test.tsx`
- API/export: If new data source, export from `predict/export.py` to `web/data/`

**New Component (React, e.g., player comparison cell):**
- File: `frontend/src/components/<ComponentName>.tsx` (PascalCase)
- Type-safe: Add TypeScript props interface
- Test: Add `frontend/src/components/<ComponentName>.test.tsx`
- Reuse: Import and use in routes or other components

**New Utility (React/TypeScript, e.g., price formatter):**
- File: `frontend/src/lib/<utilName>.ts` (camelCase, no JSX)
- Test: Add `frontend/src/lib/<utilName>.test.ts`
- Import: Use in components/routes via `import { funcName } from "../lib/<utilName>"`

**New E2E Test (Playwright):**
- File: `e2e/specs/<FeatureName>.spec.ts` (camelCase feature name)
- Use helpers: Import from `e2e/helpers/page.ts`
- Run: `npx playwright test specs/<FeatureName>.spec.ts`
- Parity: Update `e2e/parity/ledger.mjs` if testing export contract

**New Python Test:**
- File: `tests/test_<component>.py` (e.g., `tests/test_price.py` for price model)
- Framework: pytest (assert statements)
- Run: `python -m pytest tests/test_<component>.py -v`

**New CLI Command (Python, e.g., python -m data.live_stats):**
- File: Create new module in appropriate package (e.g., `data/live_stats.py`)
- Entry point: Define `main()` function + `if __name__ == "__main__"` block
- Run: `python -m data.live_stats [args]` (Python finds it via import path)
- Integration: Add to `scripts/daily.sh` or `scripts/weekly.sh` if it's a recurring job

## Special Directories

**data/snapshots/:**
- Purpose: Daily price/metadata bootstrap (inputs to price model)
- Generated: `python -m data.snapshot` (idempotent per UTC day)
- Committed: NO (ignored in .gitignore; cannot be backfilled)
- Criticality: HIGH — losing snapshots requires restarting price model training

**data/processed/:**
- Purpose: Canonical tables consumed by ML (player_gw.parquet, features.parquet)
- Generated: `python -m data.build_table`, `python -m features.engineer`
- Committed: NO (regenerated from raw + code)
- Reproducibility: Fully deterministic; re-run pipeline to rebuild

**models/artifacts/:**
- Purpose: Trained model weights + intervals
- Generated: `python -m models.train`, `python -m models.intervals`
- Committed: NO (large binary files; rebuild from training pipeline)
- Reproducibility: Deterministic (time-based splits, fixed seed)
- Deployment: Mounted at runtime into Docker container (not baked into image)

**web/data/:**
- Purpose: JSON export contract (site reads from here); shared by legacy site and React frontend
- Generated: `python -m predict.export` (weekly, before gameweek deadline)
- Committed: YES (version control the contract for replay/audit)
- Content: xp_table.json, captains.json, squad.json, meta.json, fixtures.json, chips.json, watchlist.json, history/
- Consumed by: `api/main.py` (StaticFiles mount), `frontend/src/lib/api.ts` (React fetch), `web/assets/app.js` (legacy)

**web/data/history/:**
- Purpose: Frozen predictions per GW (for post-GW scoreboard comparison)
- Generated: `python -m predict.export` appends gw{N}.json after each GW ends
- Committed: YES (audit trail of predictions vs actuals)
- Format: One JSON file per finished gameweek; immutable once written

**frontend/dist/:**
- Purpose: Production-ready build output (generated by `npm run build`)
- Generated: `cd frontend && npm run build`
- Committed: NO (regenerated from src/ on every build)
- Deployment: Baked into Docker image (D-06); uploaded to CDN or served by FastAPI

**frontend/src/test/fixtures/:**
- Purpose: Mock JSON data for component/route tests (mirrors web/data/ schema)
- Committed: YES (test dependencies, not generated)
- Usage: Imported by test files to avoid real API calls during testing

**e2e/fixtures/:**
- Purpose: Precomputed API responses for E2E test isolation (generated by capture_fixtures.py)
- Generated: `cd e2e && python scripts/capture_fixtures.py --gw <N>`
- Committed: NO (regenerated from live API or current predictions)
- Usage: Playwright specs can run in isolation mode (--use-fixtures) against precomputed data

**e2e/playwright-report/:**
- Purpose: HTML test report (generated after test run)
- Generated: `npx playwright test` (auto-generated if configured)
- Committed: NO (CI artifact)
- View: Open `index.html` in browser

---

*Structure analysis: 2026-09-11*
