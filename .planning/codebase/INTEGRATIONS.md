---
last_mapped_commit: 382338e2c164a4433cd73cdbb12ffc9be2621493
---
# External Integrations

**Analysis Date:** 2026-09-11

## APIs & External Services

**Official FPL API (fantasy.premierleague.com/api):**
- Bootstrap data (`/api/bootstrap-static/`) - Player metadata, team info, fixtures, live events
  - SDK/Client: `requests` library
  - Usage: Live player pool for inference (`predict/live.py`), initial state (`api/main.py`)
  - Auth: None (free public API)

- Team picks and history (`/api/entry/{id}/event/{gw}/picks/`, `/api/entry/{id}/history/`)
  - Usage: Fetch user's current squad and transfer history (API endpoints `/api/team/{entry}`, `/api/solve`, `/api/rate`)
  - Auth: None (free public API)

- Player details (`/api/element-summary/{player_id}/`)
  - Usage: Rolling form features for live predictions (`data/live_history.py`)
  - Auth: None (free public API)

- Fixtures (`/api/fixtures/`)
  - Usage: Upcoming match schedule for next-gameweek planning
  - Auth: None (free public API)

**vaastav/Fantasy-Premier-League GitHub Archive:**
- Historical per-GW player stats (`https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data`)
  - SDK/Client: `requests` library
  - Usage: Training data (10+ seasons) for model development (`data/ingest.py`)
  - Data includes: merged_gw CSVs with expected goals/assists, bonus points, transfers
  - Auth: None (free public repo)
  - Seasons: 2016-17 through 2026-27 configured in `config.SEASONS`

**football-data.co.uk:**
- Historical bookmaker odds (`https://www.football-data.co.uk/mmz4281/{code}/E0.csv`)
  - SDK/Client: `requests` library
  - Usage: De-overround 1X2 and over/under 2.5 markets into per-fixture team-perspective implied probabilities (`data/odds.py`)
  - Signal value: Win prob predicts clean sheets (defenders/GK); over-2.5 prob predicts goal-scoring environment (attackers)
  - Auth: None (free historical data)
  - Cached: `data/raw/odds/{season}.csv`

**the-odds-api.com (Optional):**
- Live forward odds for upcoming fixtures
  - Endpoint: `https://api.the-odds-api.com/v4/sports/soccer_epl/odds?regions=eu&markets=h2h,totals&oddsFormat=decimal&apiKey={key}`
  - SDK/Client: `requests` library
  - Auth: Environment variable `ODDS_API_KEY`
  - Free tier: ~500 requests/month
  - Usage: Fill missing implied probabilities for live predictions when FPL fixtures not yet played (`data/live_odds.py`)
  - Degrades gracefully: If key not set, falls back to NaN (training-time behavior preserved)

**FBref (StatsBomb) - Advanced Defensive Stats (Optional):**
- Per-player-season advanced stats (tackles, blocks, clearances, SCA, GCA)
  - Source: `https://fbref.com/en/comps/9/{season}/{kind}/{season}-Premier-League-Stats`
  - SDK/Client: Direct URL scrape via `pandas.read_html` with `beautifulsoup4` + `html5lib` flavor
  - Usage: Optional enrichment of defensive-action columns (`data/fbref.py`)
  - Execution: No special browser automation needed (beautifulsoup4 handles HTML parsing)
  - Output: `data/processed/fbref.parquet`
  - Pipeline: `data/build_table.py` auto-joins if file exists; graceful no-op without it

**Transfermarkt:**
- Player injury statuses, historical transfers, market values
  - Source: `https://www.transfermarkt.com/`
  - SDK/Client: Direct URL scrape via `pandas.read_html` with `beautifulsoup4` + `html5lib` flavor
  - Usage: Optional enrichment of player availability for seasonal/weekly updates (`data/transfermarkt.py`)
  - Execution: No special browser automation needed (beautifulsoup4 handles HTML parsing)
  - Output: `data/processed/transfermarkt_injuries.parquet`
  - Pipeline: `data/build_table.py` auto-joins if file exists; graceful no-op without it

**Understat (Optional):**
- Free xG/xA data via understatapi package (version 0.7.1 exact)
  - SDK: `understatapi==0.7.1` (pinned exact; newer versions drag in unnecessary deps)
  - Usage: Alternative source for expected value metrics (optional integration)

## Data Storage

**Databases:**
- None (no SQL/NoSQL database)

**File Storage:**
- Local filesystem only
  - Raw: `data/raw/{season}/`, `data/raw/odds/`, `data/raw/live/`
  - Processed: `data/processed/` — canonical parquet tables
  - Snapshots: `data/snapshots/` — daily bootstrap history (irreplaceable, not in Docker image)
  - Artifacts: `models/artifacts/xp_model.joblib`, `models/artifacts/price_model.joblib` (trained models)
  - Frontend data exports: `web/data/` — JSON files consumed by web/API
  - Frontend build: `frontend/dist/` — static assets served by FastAPI
  - E2E fixtures: `e2e/fixtures/v1/{normal,blank,dgw}/` — frozen test data (fixture mode)

**Caching:**
- In-memory (thread-safe): `_state` dict in `api/main.py`
  - Player pools cached for 1 hour (POOL_TTL_S = 3600)
  - Solve results cached by (gw, entry, params-hash) until pool refreshes
  - Clear-on-refresh pattern prevents stale predictions after weekly deadline

## Authentication & Identity

**API Authentication:**
- FPL API: None required (free public API)
- the-odds-api.com: API key via `ODDS_API_KEY` environment variable (optional)
- Transfermarkt, FBref: None required (publicly accessible, no API keys)
- Solver endpoints (`/api/solve`, `/api/rate`): Stub implementation
  - Current: Basic API key check via `FPL_API_KEYS` header (`X-API-Key`)
  - Future: Supabase JWT + subscriptions table (placeholder in `api/main.py:15`)
  - Single choke point by design for easy upgrade when payments enabled

## Monitoring & Observability

**Error Tracking:**
- None (integrated)

**Logs:**
- Console output via print statements with context tags (`[vaastav]`, `[fpl-api]`, `[odds]`, `[fbref]`, `[transfermarkt]`, etc.)
- Live API calls log their status (cached, saved, MISS, ERROR)
- CI/CD: GitHub Actions workflows log to console (`daily.yml`, `weekly.yml`)
- E2E test reports: HTML output to `e2e/playwright-report/` (inspector, video, trace)
- No persistent logging to external service

## CI/CD & Deployment

**Hosting:**
- Local development: `localhost:8000` (FastAPI + Vite proxy)
- Local E2E: `localhost:8100–8102` (three parallel fixture-mode servers via Playwright)
- GitHub Actions: Python 3.12 Ubuntu runner for CI jobs
- Docker image: python:3.14-slim (builder stage for hash-locked install, runtime stage for minimal footprint)
- Final deployment target: Not yet specified (Docker image + static artifacts planned)

**CI Pipeline:**
- GitHub Actions workflows:
  - `daily.yml`: Scheduled daily at 02:30 UTC
    - `python -m data.snapshot` - Bootstrap FPL API data
    - `python -m models.price --train` (or true if already trained)
    - `python -m models.price` - Price model prediction
    - `python -m predict.scoreboard` - Backtest accuracy metrics
    - Commits outputs to git: `data/snapshots`, `web/data`, `models/artifacts/price_model.joblib`

  - `weekly.yml`: Scheduled Fridays at 08:00 UTC
    - `python -m data.live_history` - Fetch rolling form
    - `python -m predict.export` - Generate xP predictions + squad recommendations
    - `python -m models.price` - Price model (live)
    - `python -m predict.digest` - Email digest render
    - Commits outputs to git: `web/data`, `data/raw/live`

**Local Development:**
- Frontend: `npm run dev` (Vite with proxy to backend)
- Backend: `python -m data.ingest`, `python -m features.engineer`, etc.
- API: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- E2E tests: `E2E_PYTHON=/path/to/python npm run test` (fixture mode, full server lifecycle)

**Docker Build:**
- Multi-stage Dockerfile (builder + runtime)
  - Builder stage: Installs all dependencies with `--require-hashes` (hash-locked lockfile required)
  - Runtime stage: python:3.14-slim + libstdc++6 + libgomp1 + non-root user
  - No model artifacts, .env, test suites, or pipeline data in final image
  - Frontend pre-built (`frontend/dist/`) baked into image; no Node.js or Vite in runtime
  - Health check: HTTP GET `/api/health` (30s interval, 5s timeout, 3 retries)

## Environment Configuration

**Required env vars:**
- None (everything defaults to public APIs or has graceful fallback)

**Optional env vars:**
- `ODDS_API_KEY` - the-odds-api.com free tier key (enables live forward odds)
- `FPL_API_KEYS` - Comma-separated API keys for solver endpoint authentication
- `E2E_PYTHON` - Path to Python interpreter for E2E tests (local development only; CI sets `python` on PATH)
- `E2E_PORT` - Base port for E2E servers (defaults to 8100; blank/dgw servers use 8101, 8102)
- `E2E_VARIANTS` - Set to "0" to skip blank/dgw variant servers (fast local testing)
- `FPL_FIXTURE_DIR` - Directory with frozen fixture data (set by Playwright config, not user-facing)
- `FPL_FIXTURE_DATA_DIR` - Override web/data/ JSON with variant fixture set (blank or dgw)
- `CI` - Set by GitHub Actions; disables `reuseExistingServer` in E2E config (forces fresh server per run)

**Secrets location:**
- `.env` file (not committed) — contains optional ODDS_API_KEY and FPL_API_KEYS
- GitHub Actions: Environment variables set in workflow files (no secrets engine configured)
- Docker: No .env file included in image (D-05); secrets injected at deploy time

**Frontend API Contracts:**
- Relative fetch paths only (no absolute URLs, no env var base URL)
- Data paths: `/data/meta.json`, `/data/xp_table.json`, `/data/captains.json`, `/data/fixtures.json`, `/data/watchlist.json`, `/data/standings.json`, `/data/leaders.json`, `/data/scoreboard.json`
- API paths: `/api/health`, `/api/meta`, `/api/team/{entry}`, `/api/solve`, `/api/rate`
- Vite proxy (dev): Routes `/api/*` and `/data/*` to `localhost:8000` (see `frontend/vite.config.ts`)
- E2E fixture mode: Three servers on different ports, each serves different fixture data (normal, blank, dgw)

## Webhooks & Callbacks

**Incoming:**
- None (pull-based architecture only)

**Outgoing:**
- None (no external notifications or webhooks)
- Email digest prepared in `predict/digest.py` but no SMTP integration yet

---

*Integration audit: 2026-09-11*
