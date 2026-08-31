# Codebase Structure

**Analysis Date:** 2026-08-31

## Directory Layout

```
fpl/
├── config.py                        # Constants, paths, seasons, FPL rules, feature lists
├── requirements.txt                 # Python dependencies (pandas, lightgbm, pulp, etc.)
├── pytest.ini                       # Test runner config
├── README.md                        # Quick start + product layer overview
├── PLAN.md                          # Build log, experiments, findings
├── ROADMAP.md                       # Productization status & roadmap
├── PROJECT_INDEX.md                 # This structure + entry points (auto-generated)
├── IMPROVEMENTS.md                  # Known limitations & ideas
│
├── data/                            # Data ingestion & processing
│   ├── ingest.py                    # Fetch vaastav + FPL API
│   ├── id_map.py                    # Stable player_code across seasons + live
│   ├── odds.py                      # football-data.co.uk → implied probabilities
│   ├── fbref.py                     # FBref scraper (optional, needs Chrome)
│   ├── build_table.py               # → player_gw.parquet (canonical)
│   ├── live_history.py              # Refresh current-season form cache
│   ├── live_odds.py                 # Live odds fetch (for rolling updates)
│   ├── snapshot.py                  # Daily bootstrap → data/snapshots/ (idempotent)
│   ├── raw/                         # Cached downloads (vaastav CSVs, FPL API JSON)
│   │   ├── 2016-17...2026-27/       # Per-season vaastav history (GW→player records)
│   │   ├── live/                    # FPL API snapshots (bootstrap-static.json, fixtures.json)
│   │   ├── odds/                    # football-data.co.uk fixtures + odds
│   │   └── fbref/                   # FBref scraped advanced stats (if enabled)
│   ├── processed/                   # Canonical parquet tables
│   │   ├── player_gw.parquet        # Canonical: [gw, player_id, minutes, points, ...]
│   │   ├── features.parquet         # ML-ready: + rolling form + context
│   │   ├── id_map.parquet           # Season-local id → stable player_code
│   │   ├── odds.parquet             # Fixture-level odds (de-overrounded)
│   │   └── test_predictions.parquet # Frozen predictions from backtest
│   └── snapshots/                   # Daily price/metadata snapshots (do not lose)
│       └── *.parquet                # One per UTC day; used for price model training
│
├── features/                        # Feature engineering
│   └── engineer.py                  # Rolling form (3/5/10/all), context → features.parquet
│
├── models/                          # ML model training & artifacts
│   ├── train.py                     # Two-stage hurdle xP model, per position (LightGBM)
│   ├── tune.py                      # Hyperparameter search (validation-scored)
│   ├── calibration.py               # Isotonic regression calibration
│   ├── intervals.py                 # Fit p10/p90 confidence bands per position×xp-bucket
│   ├── price.py                     # Price change watchlist (heuristic → LightGBM)
│   └── artifacts/                   # Saved model weights + intervals
│       ├── xp_model.joblib          # Trained two-stage model
│       └── *.joblib                 # Intervals, calibration artifacts
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
├── web/                             # Static site (Cloudflare Pages-ready)
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
├── scripts/                         # Cron entry points
│   ├── daily.sh                     # 02:30 UTC: snapshot + price model + watchlist + scoreboard
│   └── weekly.sh                    # 08:00 UTC Fridays: live_history + export + digest
│
├── tests/                           # Pytest suite
│   ├── test_legality.py             # ILP results obey FPL rules
│   ├── test_leakage.py              # No match outcome in pre-match features
│   ├── test_autosub.py              # Autosub + vice-captain logic
│   └── test_product.py              # Intervals, snapshot, export, price, solver, API, digest
│
├── .github/                         # GitHub Actions (mirrors cron scripts)
│   └── workflows/
│       ├── daily.yml                # GitHub Actions version of daily.sh
│       └── weekly.yml               # GitHub Actions version of weekly.sh
│
├── .planning/                       # Codebase mapping (this directory)
│   └── codebase/
│       ├── ARCHITECTURE.md          # System overview, layers, data flow, abstractions
│       └── STRUCTURE.md             # Directory layout & naming conventions (this file)
│
└── __pycache__, .pytest_cache/      # Generated cache directories
```

## Directory Purposes

**config.py:**
- Purpose: Single source of truth for constants, paths, seasons, FPL rules, feature lists
- Key exports: `ROOT`, `SEASONS`, `TRAIN/VAL/TEST`, `BUDGET`, `POSITION_QUOTA`, `WINDOWS`, `SET_PIECE_COLS`, `ODDS_COLS`, `FBREF_COLS`
- Imported by: All modules
- Do not edit during runs: Changing `SEASONS` or `TRAIN_SEASONS` requires re-running the entire pipeline

**data/:**
- Purpose: Ingest raw data, canonicalize, produce parquet tables consumed by ML
- Key outputs:
  - `data/raw/`: Cached downloads (vaastav per-season CSVs, FPL API JSON snapshots)
  - `data/processed/`: Canonical parquet tables (player_gw, features, id_map, odds)
  - `data/snapshots/`: Daily snapshots (price, metadata); not backfillable — do not lose
- Responsibility: Handle external API failures, normalize schema, backfill missing columns

**features/:**
- Purpose: Engineer leakage-safe rolling form + context features
- Key output: `data/processed/features.parquet`
- Constraint: Every rolling feature must be shifted by one (no leakage of a match into its own prediction)
- Single file: `engineer.py` (consolidated into one module for clarity)

**models/:**
- Purpose: Train, tune, calibrate two-stage per-position xP model
- Key outputs:
  - `models/artifacts/xp_model.joblib`: Trained LightGBM models (GK, DEF, MID, FWD)
  - `models/artifacts/*.joblib`: Intervals (p10/p90), calibration, price model
- Splits: `models/train.py` (train + predict), `models/tune.py` (hyperparameter search), `models/calibration.py` (isotonic regression)
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

**web/:**
- Purpose: Framework-free static site + JSON contract
- HTML pages: `index.html` (xp table), `team.html` (rate-my-team), `scoreboard.html`, `fixtures.html`, etc.
- Client app: `assets/app.js` (table rendering, API calls, filters)
- Data: `web/data/` JSON files (xp_table, captains, squad, etc.); refreshed weekly by export.py
- Deployment: Deploy `web/` directory to Cloudflare Pages (or any static host)

**scripts/:**
- Purpose: Cron entry points for daily + weekly jobs
- `daily.sh`: Runs snapshot → price model → watchlist → scoreboard (02:30 UTC)
- `weekly.sh`: Runs live_history → export → digest (08:00 UTC Fridays)
- Both use the Python env: `/home/sraja/miniconda3/envs/python314/bin/python`

**tests/:**
- Purpose: Validate legality, leakage, autosubs, product components
- Key files:
  - `test_legality.py`: ILP results obey FPL constraints
  - `test_leakage.py`: Features don't contain match outcomes
  - `test_autosub.py`: Bench→XI substitution logic
  - `test_product.py`: Intervals, snapshot, export, price, solver, API, digest
- Run: `python -m pytest` (or `pytest tests/test_product.py -v` for specific test)

**.github/workflows/:**
- Purpose: GitHub Actions mirrors of cron scripts (if repo is pushed to GitHub)
- Files: `daily.yml`, `weekly.yml`
- Trigger: Push to main (or scheduled via cron expression)

**.planning/codebase/:**
- Purpose: Auto-generated codebase documentation (this directory)
- Files: `ARCHITECTURE.md`, `STRUCTURE.md` (this file)
- Do not edit by hand; regenerated by `/gsd-map-codebase --arch`

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

**Configuration:**
- `config.py`: Paths, seasons, FPL rules, feature lists
- `requirements.txt`: Python dependencies
- `pytest.ini`: Test runner config (minimal markers)
- `web/config.js`: Client-side API base URL

**Core Logic:**
- `data/build_table.py`: Canonical player_gw table builder
- `features/engineer.py`: Rolling form + context
- `models/train.py`: Two-stage hurdle model
- `optimize/squad_ilp.py`: Squad selection ILP
- `optimize/transfers.py`: Weekly transfer ILP
- `backtest/season.py`: Season state machine

**Testing:**
- `tests/test_legality.py`: Constraint validation
- `tests/test_leakage.py`: Feature leakage detection
- `tests/test_autosub.py`: Autosub simulation
- `tests/test_product.py`: Integration tests (intervals, export, API, digest)

## Naming Conventions

**Files:**
- `*.py`: Python modules (snake_case with `_` prefixes for private functions, no suffix for public ones)
- `config.py`: Master constants file (not config/ directory, single file only)
- `main.py`: Entry point for a package (e.g., `api/main.py` for FastAPI app)
- `train.py`, `ingest.py`, `engineer.py`: Verb names (what the module does)
- `.html`: Static site pages; hyphenated names (index.html, team.html, scoreboard.html)
- `.json`: Data exports (lowercase, underscored: xp_table.json, captains.json, meta.json)

**Directories:**
- `data/`, `features/`, `models/`, `optimize/`, `backtest/`, `predict/`, `api/`, `web/`, `tests/`, `scripts/`: Phase/component names
- `data/raw/`: Cached downloads (do not edit)
- `data/processed/`: Canonical tables (outputs of pipeline)
- `data/snapshots/`: Daily snapshots (critical, not backfillable)
- `models/artifacts/`: Saved model weights + intervals
- `web/data/`: JSON export contract (weekly)
- `web/data/history/`: Frozen predictions per GW (for scoreboard)

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

**Functions:**
- `build_*()`: Construct a data structure (e.g., `build_pool()`, `build_table()`)
- `load_*()`: Read from disk (e.g., `load_features()`, `load_artifact()`)
- `fetch_*()`: Retrieve from external API (e.g., `fetch_fpl_live()`)
- `predict_*()`: Generate predictions (e.g., `predict_xp()`)
- `optimize_*()`: Solve an ILP (e.g., `optimize_gw()`)
- `_*()`: Private/internal function (leading underscore)
- `*_gw()`: Functions operating on a single gameweek (e.g., `optimize_gw()`)

## Where to Add New Code

**New Feature (e.g., additional rolling window):**
- Edit: `features/engineer.py:add_features()` to add new `feat[col] = ...` line
- Rerun: `python -m features.engineer` to regenerate `data/processed/features.parquet`
- Retrain: `python -m models.train` to pick it up in the next model
- Test: `python -m backtest.walk_forward` to measure impact

**New Data Source (e.g., additional external API):**
- Add fetch function: `data/<source>.py` (e.g., `data/fancy_stats.py:fetch_fancy_stats()`)
- Join to player_gw: Edit `data/build_table.py:build()` to merge new data
- Add config: Export columns to `config.FANCY_STATS_COLS` if optional
- Rerun: `python -m data.build_table` → `python -m features.engineer` → retrain

**New API Endpoint (e.g., /api/transfers-advice):**
- Edit: `api/main.py` to add new `@app.get()` or `@app.post()` decorated function
- Logic: Call `optimize/transfers.py:optimize_gw()` or similar
- Cache: Consider `_solve_cache` if expensive; else compute on-demand
- Test: `curl http://localhost:8000/api/transfers-advice?gw=1`

**New Web Page (e.g., player comparison tool):**
- Create: `web/<page>.html` (vanilla HTML/JS, read from `/` config)
- Client: Add fetch calls to `web/assets/app.js` or inline script tags
- API: May need new endpoint in `api/main.py` to expose data
- Deploy: Include in `web/` directory when pushing to Cloudflare Pages

**New Test:**
- File: `tests/test_<component>.py` (e.g., `tests/test_price.py` for price model)
- Framework: pytest (assert statements)
- Run: `python -m pytest tests/test_<component>.py -v`
- Coverage: Existing tests in `tests/test_product.py` cover export, intervals, solver, API

**New CLI Command (e.g., python -m data.live_stats):**
- File: Create new module in appropriate package (e.g., `data/live_stats.py`)
- Entry point: Define `main()` function + `if __name__ == "__main__"` block
- Run: `python -m data.live_stats [args]` (Python finds it via import path)
- Integration: Add to `scripts/daily.sh` or `scripts/weekly.sh` if it's a recurring job

## Special Directories

**data/snapshots/:**
- Purpose: Daily price/metadata bootstrap (inputs to price model)
- Generated: `python -m data.snapshot` (idempotent per UTC day)
- Committed: NO (ignore in .gitignore; cannot be backfilled)
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

**web/data/:**
- Purpose: JSON export contract (site reads from here)
- Generated: `python -m predict.export` (weekly, before gameweek deadline)
- Committed: YES (version control the contract for replay/audit)
- Content: xp_table.json, captains.json, squad.json, meta.json, fixtures.json, chips.json, history/

**web/data/history/:**
- Purpose: Frozen predictions per GW (for post-GW scoreboard comparison)
- Generated: `python -m predict.export` appends gw{N}.json after each GW ends
- Committed: YES (audit trail of predictions vs actuals)
- Format: One JSON file per finished gameweek; immutable once written

---

*Structure analysis: 2026-08-31*
