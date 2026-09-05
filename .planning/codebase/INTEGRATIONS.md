# External Integrations

**Analysis Date:** 2026-09-01

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
  - SDK/Client: Direct URL scrape via `seleniumbase` (Chrome automation to bypass Cloudflare)
  - Usage: Optional enrichment of defensive-action columns (`data/fbref.py`)
  - Execution: Requires Chrome browser; run `python -m data.fbref --scrape` locally
  - Output: `data/processed/fbref.parquet`
  - Pipeline: `data/build_table.py` auto-joins if file exists; graceful no-op without it
  - Note: `soccerdata` package superseded due to Cloudflare blocking

**Understat (Optional):**
- Free xG/xA data via understatapi package
  - SDK: `understatapi>=0.5`
  - Usage: Alternative source for expected value metrics (optional integration)

## Data Storage

**Databases:**
- None (no SQL/NoSQL database)

**File Storage:**
- Local filesystem only
  - Raw: `data/raw/{season}/`, `data/raw/odds/`, `data/raw/live/`
  - Processed: `data/processed/` — canonical parquet tables
  - Artifacts: `models/artifacts/xp_model.joblib` (trained model)
  - Frontend data exports: `web/data/` — JSON files consumed by web/API
  - Frontend build: `frontend/dist/` — static assets served by FastAPI

**Caching:**
- In-memory (thread-safe): `_state` dict in `api/main.py`
  - Player pools cached for 1 hour (POOL_TTL_S = 3600)
  - Solve results cached by (gw, entry, params-hash) until pool refreshes
  - Clear-on-refresh pattern prevents stale predictions after weekly deadline

## Authentication & Identity

**API Authentication:**
- FPL API: None required (free public API)
- the-odds-api.com: API key via `ODDS_API_KEY` environment variable (optional)
- Solver endpoints (`/api/solve`, `/api/rate`): Stub implementation
  - Current: Basic API key check via `FPL_API_KEYS` header (`X-API-Key`)
  - Future: Supabase JWT + subscriptions table (placeholder in `api/main.py:15`)
  - Single choke point by design for easy upgrade when payments enabled

## Monitoring & Observability

**Error Tracking:**
- None (integrated)

**Logs:**
- Console output via print statements with context tags (`[vaastav]`, `[fpl-api]`, `[odds]`, etc.)
- Live API calls log their status (cached, saved, MISS, ERROR)
- CI/CD: GitHub Actions workflows log to console (`daily.yml`, `weekly.yml`)
- No persistent logging to external service

## CI/CD & Deployment

**Hosting:**
- Local development: `localhost:8000` (FastAPI + Vite proxy)
- GitHub Actions: Python 3.12 Ubuntu runner for CI jobs
- Cloudflare Pages implied (from daily.yml commit comment about site redeploy)
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

## Environment Configuration

**Required env vars:**
- None (everything defaults to public APIs or has graceful fallback)

**Optional env vars:**
- `ODDS_API_KEY` - the-odds-api.com free tier key (enables live forward odds)
- `FPL_API_KEYS` - Comma-separated API keys for solver endpoint authentication

**Secrets location:**
- `.env` file (not committed) — contains optional ODDS_API_KEY and FPL_API_KEYS
- GitHub Actions: Environment variables set in workflow files (no secrets engine configured)

**Frontend API Contracts:**
- Relative fetch paths only (no absolute URLs, no env var base URL)
- Paths: `/data/meta.json`, `/data/xp_table.json`, `/data/captains.json`, `/data/fixtures.json`, `/data/watchlist.json`, `/data/standings.json`, `/data/leaders.json`, `/data/scoreboard.json`
- API paths: `/api/health`, `/api/meta`, `/api/team/{entry}`, `/api/solve`, `/api/rate`
- Vite proxy: dev server routes `/api/*` and `/data/*` to `localhost:8000` (see `frontend/vite.config.ts`)

## Webhooks & Callbacks

**Incoming:**
- None (pull-based architecture only)

**Outgoing:**
- None (no external notifications or webhooks)
- Email digest prepared in `predict/digest.py` but no SMTP integration yet

---

*Integration audit: 2026-09-01*
