# External Integrations

**Analysis Date:** 2026-08-31

## APIs & External Services

**Official FPL API (fantasy.premierleague.com/api):**
- Bootstrap data (`/api/bootstrap-static/`) - Player metadata, team info, fixtures, live events
  - SDK/Client: `requests` library
  - Usage: Live player pool for inference (`predict/live.py`), team initialization (`api/main.py`)
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

**football-data.co.uk:**
- Historical bookmaker odds (`https://www.football-data.co.uk/mmz4281/{code}/E0.csv`)
  - SDK/Client: `requests` library
  - Usage: De-overround 1X2 and over/under 2.5 markets into per-fixture team-perspective implied probabilities (`data/odds.py`)
  - Signal value: Win prob predicts clean sheets; over-2.5 prob predicts goal-scoring environment
  - Auth: None (free historical data)
  - Downloaded for seasons: 2016-17 through current season
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
  - Usage: Optional enrichment of defensive-action columns that feed FPL's defensive-contribution scoring (`data/fbref.py`)
  - Execution: Requires Chrome browser; run `python -m data.fbref --scrape` on a local machine
  - Output: `data/processed/fbref.parquet` (matches by normalized player name within season)
  - Pipeline: `data/build_table.py` auto-joins if file exists; pipeline no-ops without it (no failure)
  - Note: soccerdata package was previously tried but Cloudflare defeats its scraper reliably

**Understat (Optional):**
- Free xG/xA data via understatapi package
  - SDK: `understatapi>=0.5`
  - Usage: Alternative source for expected value metrics (not currently integrated in core pipeline)

## Data Storage

**Databases:**
- None (no SQL/NoSQL database)

**File Storage:**
- Local filesystem only
  - Raw: `data/raw/{season}/`, `data/raw/odds/`, `data/raw/live/`
  - Processed: `data/processed/` — canonical parquet tables
  - Artifacts: `models/artifacts/xp_model.joblib` (trained model), interval artifacts

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
  - Future: Supabase JWT + subscriptions table (placeholder in code comment at `api/main.py:15`)
  - Single choke point by design for easy upgrade when payments enabled

## Monitoring & Observability

**Error Tracking:**
- None (integrated)

**Logs:**
- Console output via print statements
- Live API calls log their status (cached, saved, MISS, ERROR)
- No persistent logging

## CI/CD & Deployment

**Hosting:**
- None specified (manual runs or custom deployment)

**CI Pipeline:**
- None (no GitHub Actions, GitLab CI, etc. detected)

**Local Execution:**
- CLI commands via `python -m <module>`
- Example entry points:
  - `python -m data.ingest` — download raw data
  - `python -m data.build_table` — build player_gw.parquet
  - `python -m features.engineer` — add rolling features
  - `python -m models.train` — train xP model
  - `python -m predict.live` — live weekly recommendation
  - `uvicorn api.main:app --host 0.0.0.0 --port 8000` — run solver API

## Environment Configuration

**Required env vars:**
- None (everything defaults to public APIs or has graceful fallback)

**Optional env vars:**
- `ODDS_API_KEY` - the-odds-api.com free tier key (enables live forward odds)
- `FPL_API_KEYS` - Comma-separated API keys for solver endpoint authentication

**Secrets location:**
- `.env` file (not committed) — contains optional ODDS_API_KEY and FPL_API_KEYS

## Webhooks & Callbacks

**Incoming:**
- None (pull-based architecture only)

**Outgoing:**
- None (no external notifications or webhooks)

---

*Integration audit: 2026-08-31*
