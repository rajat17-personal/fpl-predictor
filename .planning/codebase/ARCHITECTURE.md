<!-- refreshed: 2026-09-01 -->
# Architecture

**Analysis Date:** 2026-09-01

## System Overview

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│                          Batch ML Pipeline + Product                          │
├──────────────────────┬──────────────────────┬─────────────────────────────────┤
│   Data Ingestion     │   Features & Models  │   Optimization & Eval           │
│ `data/ingest.py`     │ `features/engineer`  │ `optimize/squad_ilp.py`         │
│ `data/build_table.py`│ `models/train.py`    │ `optimize/transfers.py`         │
│ `data/snapshot.py`   │ `models/intervals.py`│ `backtest/season.py`            │
└──────────────┬───────┴──────────────┬───────┴───────────────┬────────────────┘
               │                      │                       │
               ▼                      ▼                       ▼
        ┌─────────────────┐   ┌──────────────────┐    ┌──────────────────┐
        │ data/raw/       │   │ data/processed/  │    │ predict/live.py  │
        │ data/processed/ │   │ features.parquet │    │ predict/export.py│
        │ data/snapshots/ │   │ xp_model.joblib  │    │                  │
        └────────┬────────┘   └────────┬─────────┘    └────────┬─────────┘
                 │                    │                        │
                 └────────────────────┴────────────────────────┘
                                     │
                           ┌─────────▼──────────┐
                           │   web/data/        │
                           │   (JSON contract)  │
                           │ • xp_table.json    │
                           │ • captains.json    │
                           │ • squad.json, etc. │
                           └─────────┬──────────┘
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
                ▼                      ▼                      ▼
         ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │  Static Site    │  │ FastAPI Solver   │  │ React/Vite       │
         │ web/ (HTML/JS)  │  │ api/main.py      │  │ frontend/        │
         │ (Legacy vanilla)│  │ /api/solve       │  │ (React Router +  │
         │                 │  │ /api/rate        │  │  TypeScript)     │
         └─────────────────┘  │ /api/team        │  └──────────────────┘
                               │ GET / (web/)     │
                               └──────────────────┘
                                      ▲
                        ┌─────────────┴─────────────┐
                        │  (dev: Vite proxy)        │
                        │  /api → localhost:8000    │
                        │  /data → localhost:8000   │
                        └───────────────────────────┘

   ┌──────────────────────────────────────┐
   │     Cron Jobs (scripts/)             │
   │  • daily.sh  (snapshot + watchlist)  │
   │  • weekly.sh (export + digest)       │
   └──────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Data Ingest** | Download vaastav history + live FPL API; normalize to canonical schema | `data/ingest.py`, `data/id_map.py`, `data/odds.py` |
| **Data Build** | Join raw history with FDR, odds, set-piece; output canonical player_gw table | `data/build_table.py` |
| **Feature Engineer** | Rolling form (3/5/10/all windows), context features; leakage-safe shifts | `features/engineer.py` |
| **Model Training** | Two-stage hurdle model (P(play), E[pts\|played]) per position; LightGBM | `models/train.py` |
| **Model Intervals** | Fit p10/p90 bands from held-out residuals per position×xp-bucket | `models/intervals.py` |
| **Price Model** | Net-transfer-per-owner heuristic → LightGBM after 14+ snapshot days | `models/price.py` |
| **Squad Selection** | ILP: 15-man squad (2/5/5/3) with captain, budget, club limits, formations | `optimize/squad_ilp.py` |
| **Weekly Transfers** | ILP: sell/buy decisions within budget, hit cost, free-transfer allowance | `optimize/transfers.py` |
| **Chip Scheduling** | DGW/BGW detection; heuristic chip timing (WC/FH/BB/TC) | `optimize/chips.py` |
| **Multi-Period Plan** | Expand single-GW xP to multi-GW horizon for lookahead | `optimize/multi_period.py` |
| **Season Simulation** | State machine: apply transfers, autosubs (GK→DEF, bench→XI), score matches | `backtest/season.py` |
| **Walk-Forward Backtest** | Retrain per season, expanding window; jitter replicas for CIs; isolated chip evals | `backtest/walk_forward.py` |
| **Live Prediction** | Fetch FPL API; predict xP for next GW; optimize squad/transfers; interactive flags | `predict/live.py` |
| **JSON Export** | Emit weekly product contract: xp_table, captains, squad, fixtures, chips to web/data/ | `predict/export.py` |
| **Scoreboard** | Post-GW accuracy: MAE + Spearman rank vs FPL's ep_next + actual | `predict/scoreboard.py` |
| **Email Digest** | Render plain-text + HTML digest from exported JSON for mailing | `predict/digest.py` |
| **Snapshots** | Idempotent daily bootstrap (player metadata, prices) for price-model training | `data/snapshot.py` |
| **Solver API** | FastAPI: /api/solve (ILP with locks), /api/rate (rate-my-team), /api/team (squad fetch) | `api/main.py` |
| **Static Site (Legacy)** | Framework-free HTML/JS consuming web/data/*.json; renders tables, charts, team editor | `web/` |
| **React Frontend** | React + TypeScript rebuild with 8 routes (XpTable, Team, Fixtures, etc.); consumes web/data/ via proxy | `frontend/src/` |

## Pattern Overview

**Overall:** Batch ML pipeline with a daily/weekly product refresh cycle. Product layer includes both a legacy vanilla static site and a new React/TypeScript frontend, both consuming the same JSON export contract.

**Key Characteristics:**
- **Leakage-safe**: All features for a fixture are computed from matches before it (strict temporal validation)
- **Retrainable**: Core components (data, features, models) can re-run without product disruption
- **Cacheable**: Predictions are exported to JSON; API caches pools + solves by (GW, params)
- **Modular entry points**: Each phase (`python -m module`) can run independently; cron orchestrates sequences
- **Two-objective model**: Core squad selection uses median xP (robust); captain picks use mean xP (doubles points, so maximize expectation)
- **Contract-driven UI**: Both web/ and frontend/ consume identical JSON from web/data/; no custom API responses for UI
- **Type-safe frontend**: React + TypeScript with interfaces in `frontend/src/lib/api.ts` mirroring export contract

## Layers

**Data Layer:**
- Purpose: Ingest, canonicalize, enrich player-GW records
- Location: `data/`
- Contains: FPL API fetch, vaastav history aggregation, ID mapping, odds de-overrounding, FBref scraper
- Depends on: External APIs (FPL, football-data.co.uk, GitHub vaastav)
- Used by: Feature engineering, live prediction, snapshots
- Artifacts: `data/raw/` (cached downloads), `data/processed/player_gw.parquet`

**Feature Layer:**
- Purpose: Engineer leakage-safe rolling form + context features
- Location: `features/engineer.py`
- Contains: Multi-window rolling aggregations (3/5/10/all), volatility, congestion, target encoding
- Depends on: `data/processed/player_gw.parquet`
- Used by: Model training
- Artifacts: `data/processed/features.parquet`

**Model Training Layer:**
- Purpose: Train two-stage per-position hurdle model (P(play) × E[pts|played])
- Location: `models/train.py`, `models/tune.py`, `models/calibration.py`
- Contains: LightGBM classifier + regressor per position, isotonic calibration, hyperparameter search
- Depends on: `data/processed/features.parquet`
- Used by: Live prediction, export, API
- Artifacts: `models/artifacts/xp_model.joblib`, intervals artifact (p10/p90 bands)

**Optimization Layer:**
- Purpose: Solve integer linear programs for squad, transfers, chip timing
- Location: `optimize/`
- Contains: Squad selection ILP (squad+XI+captain), weekly transfer ILP (sell/buy decisions), chip scheduler, multi-period horizon expansion
- Depends on: xP predictions, current squad state (for transfers)
- Used by: Live prediction, export, API solver
- No persistent artifacts (solves on-demand)

**Backtest Layer:**
- Purpose: Evaluate predictions via multi-season walk-forward simulation with noise controls
- Location: `backtest/`
- Contains: Season state machine (transfers, autosubs, chip application), walk-forward retraining loop, jitter-based confidence intervals
- Depends on: All ML layers (trains per test season)
- Used by: Validation, reporting (PLAN.md, ROADMAP.md)
- Artifacts: `data/processed/test_predictions.parquet` (saved during walk-forward)

**Prediction Layer:**
- Purpose: Emit weekly xP predictions + recommendations in multiple formats
- Location: `predict/`
- Contains: Live pool builders, export to JSON, scoreboard evaluation, email digest
- Depends on: Trained model, FPL API (live data), optimization layer
- Used by: Product layer (API + site), email distribution
- Artifacts: `web/data/*.json` (xp_table, captains, squad, etc.), digest HTML

**API & Serving Layer:**
- Purpose: Serve predictions via REST API and static site
- Location: `api/main.py`
- Contains: FastAPI app (cached pool builders, solve endpoint, auth stub), mounts StaticFiles from web/ at "/"
- Depends on: `web/data/` JSON exports, trained model (for intervals)
- Used by: Frontend, legacy site, API clients
- Thread safety: Uses `threading.Lock()` for pool refresh + solve cache
- Proxy behavior (development): Both `/api` and `/data` proxy to `localhost:8000` for shared data

**Frontend Layer (React + Vite):**
- Purpose: Modern React/TypeScript rebuild of the UI with type-safe data consumption
- Location: `frontend/` (src/, dist/, build config)
- Contains: 8 routes (XpTable, Team, Fixtures, Prices, League, Scoreboard, Differentials, Methodology), components, utilities
- Build: Vite (development server with /api and /data proxies, production build to dist/)
- Depends on: `web/data/` JSON exports (via /data/* paths)
- Dev proxy: Vite proxies /api and /data to `localhost:8000` (same as web/)
- Testing: Vitest + React Testing Library
- Type-safe: Interfaces in `frontend/src/lib/api.ts` match export contract from `api/main.py`

**Legacy Site Layer:**
- Purpose: Framework-free vanilla HTML/JS site (kept live during transition)
- Location: `web/`
- Contains: Static HTML pages, inline JS, CSS; reads JSON from `/data/` paths
- Depends on: `web/data/` JSON exports
- Deployment: Deploy web/ directory as-is to static host

**Cron/Job Layer:**
- Purpose: Orchestrate daily + weekly pipeline runs
- Location: `scripts/daily.sh`, `scripts/weekly.sh`, `.github/workflows/`
- Contains: Ordered execution of snapshot, price model, export, digest
- Depends on: All prior layers
- Used by: System scheduler (or GitHub Actions)
- Triggers: daily.sh @ 02:30 UTC, weekly.sh @ 08:00 UTC Fridays

## Data Flow

### Primary Request Path (Weekly Prediction Export)

1. **Fetch fresh FPL API data** (`predict/export.py:export()`)
   - Calls `_load_live()` → `data/ingest.py:fetch_fpl_live()` + reads JSON
   - File: `data/raw/live/bootstrap-static.json`, `data/raw/live/fixtures.json`

2. **Build player pool for this GW** (`predict/live.py:build_pool()`)
   - Loads trained model (`models/artifacts/xp_model.joblib`)
   - Applies leakage-safe features from current season
   - Predicts xP per player via `models/train.py:predict_xp()`
   - Returns `pd.DataFrame`: [player_code, name, team, position, xp, price_m, ...]

3. **Attach intervals** (`models/intervals.py:apply_intervals()`)
   - If p10/p90 artifact exists, adds `p10`, `p90` columns per position×xp-bucket

4. **Merge live metadata** (`predict/export.py:_boot_meta()`)
   - Ownership, status, news, ep_next from `bootstrap-static.json`

5. **Optimize squad** (`optimize/squad_ilp.py:pick_squad()`)
   - Solves ILP: maximize XI xp + captain bonus under FPL constraints
   - Returns 15-man squad + 11-man XI + captain pick

6. **Export JSON** (`predict/export.py`)
   - Writes to `web/data/`:
     - `xp_table.json`: all players ranked by xP
     - `captains.json`: top-10 captain picks (by armband metric)
     - `squad.json`: optimal 15-man + XI + captain
     - `meta.json`: gameweek, deadline, model timestamp
     - `fixtures.json`: team difficulty ticker (next 6 GWs)
     - `chips.json`: DGW/BGW structure + chip note

### Frontend Data Consumption (React Routes)

1. **User navigates to `/` (XpTable route)**
   - `frontend/src/routes/XpTable.tsx` mounts
   - useQuery hook calls `fetchJson<XpRow[]>("/data/xp_table.json")`
   - Vite dev server (or FastAPI in prod) serves from `web/data/xp_table.json`

2. **Data fetched and rendered**
   - Component uses `useSortable<SortKey>()` hook for sort state
   - Renders `<BandCell>` for p10/p90 bands (from XpRow.p10, p90)
   - Status flags from `frontend/src/lib/statusFlag.tsx` for injuries/news

3. **Secondary fetch (captain picks)**
   - Query `fetchJson<CaptainRow[]>("/data/captains.json")` with separate error boundary
   - If main table OK but captains fail, shows inline message (graceful degradation)

### Live Prediction Flow (Interactive CLI)

1. **User runs** `python -m predict.live --entry 1234567 --free-transfers 1`

2. **Fetch FPL data & build pool** (same as export)

3. **Fetch user's current squad** (`predict/live.py:_load_entry()`)
   - Calls FPL API to get team ID's squad + bank

4. **Optimize transfers** (`optimize/transfers.py:optimize_gw()`)
   - ILP: which players to sell (with 50% sell-on fee) and buy (within budget)
   - Constraints: bank + sales, transfer hits (−4 pts each over free), squad composition
   - Maximizes: XI xP + captain bonus (with constraints)

5. **Print recommendation** (`optimize/transfers.py` or squad selection)
   - Shows transfers, new XI, captain, estimated points

### API Request Flow (`/api/solve`)

1. **Client POST** `/api/solve` with locks, excludes, horizon, chip mode

2. **Server refreshes pool** (`_refresh()`)
   - Checks TTL (1 hour default); if stale, re-fetches FPL API + rebuilds pools
   - Thread-safe via `threading.Lock()`
   - Caches by horizon (single-GW vs multi-period lookahead)

3. **Solve ILP** (`optimize/squad_ilp.py:pick_squad()` or `optimize/transfers.py:optimize_gw()`)
   - Applies user locks/excludes
   - Returns optimal squad + transfers

4. **Cache solve** by (GW, entry, params-hash)
   - Deadline-hour traffic hits cache (seconds vs minutes for ILP)

5. **Return JSON** with result + solved xP estimates

### Backtest Flow (Walk-Forward Validation)

1. **For each test season T** in TEST_SEASONS = ["2020-21", ..., "2025-26"]:

2. **Split data:**
   - Train on seasons before T-1
   - Validate on T-1 (early stopping)
   - Test on T

3. **Train xP model** (`models/train.py:train_predict()`)
   - Two-stage per-position (P(play), E[pts|played])
   - Save trained model

4. **Generate predictions** for season T (match-level xP)

5. **Simulate season T** (`backtest/season.py:run_season()`)
   - State machine: GW1 → GW38
   - Each GW: apply transfers, optimize XI, apply chips, score matches
   - Autosubs: bench GK/DEF → XI if starter doesn't play
   - Vice-captain: if captain plays 0 mins, vice-captain gets 1x bonus

6. **Measure results:**
   - Realized points (with/without chips)
   - MAE + Spearman rank vs FPL's ep_next (from history)
   - Isolated chip value (on same team with/without chip that GW)

7. **Aggregate across seasons** for final report

**State Management:**
- `api/main.py` maintains thread-safe `_state` dict:
  - `artifact`: Loaded xp_model
  - `boot`, `fixtures`: Current FPL API snapshot
  - `gw`: Next gameweek ID
  - `pools`: Cached player pools by horizon
  - `loaded_at`: Timestamp for TTL check
  - `_solve_cache`: (gw, entry, params-hash) → result

## Key Abstractions

**Hurdle Model:**
- Purpose: Bakes in "non-playing player scores 0" into a single xP value
- Formula: `xP = P(play) × E[points | played]`
- Implementation: Two-stage LightGBM (classifier + regressor, per position) in `models/train.py`
- Why two-stage: Dynamics of "will I play?" differ from "how many points if I play?" — separate models pick better features
- Examples: `models/artifacts/xp_model.joblib`

**Leakage-Safe Rolling Features:**
- Purpose: Ensure no information from a match "leaks" into its own prediction
- Pattern: Every feature is `shift(1)` then rolled (moving avg over prior N matches)
- Implementation: `features/engineer.py:_roll()` uses `.shift(1).rolling().mean()`
- Example: A player's expected points in GW5 cannot include their GW5 performance

**ILP Optimization:**
- Purpose: Solve squad + XI + captain + transfers + chips as a single mathematical program
- Solver: PuLP (Python API over CBC/SCIP)
- Components:
  - Squad ILP (`optimize/squad_ilp.py`): 15-man, 2/5/5/3 positions, ≤3 per club, budget
  - Transfer ILP (`optimize/transfers.py`): sell/buy decisions with hit cost
  - Chip scheduling (`optimize/chips.py`): DGW/BGW detection + heuristic timing
- Multi-period (`optimize/multi_period.py`): Chain single-GW solves over a horizon (lookahead planning)

**JSON Export Contract:**
- Purpose: Decouple product layer (API + site) from CLI (prediction logic); unified data format for all UI surfaces
- Files in `web/data/`:
  - `meta.json`: gameweek, deadline, model timestamp
  - `xp_table.json`: all players + xP + intervals + ownership
  - `captains.json`: top captain picks
  - `squad.json`: optimal 15-man + XI
  - `history/gw{N}.json`: frozen predictions (for scoreboard)
- Consumed by: `api/main.py` (StaticFiles mount), `frontend/src/lib/api.ts` (typed fetch), `web/assets/app.js` (legacy)
- Why: Allows API/site to work offline; enables versioning + replay; both old and new UI can coexist

**Walk-Forward Backtest:**
- Purpose: Reduce single-season noise via multiple retrains + jitter
- Design: Expanding-window retrain per test season (avoid lookahead bias)
- Confidence bands: K jittered replicas (5% noise on xP) → within-season range
- Isolated chips: Measure each chip on the same team with/without it
- Files: `data/processed/test_predictions.parquet` (frozen predictions per test season)

**Type-Safe Frontend Interfaces:**
- Purpose: Mirror the JSON export contract in TypeScript for compile-time safety
- Location: `frontend/src/lib/api.ts`
- Examples: `XpRow`, `CaptainRow`, `FixtureTickerTeam`, `WatchlistRow`, `ScoreboardEntry`
- Auto-sync: Contract changes in `api/main.py` or `predict/export.py` require updating interfaces
- Fetch pattern: `fetchJson<XpRow[]>("/data/xp_table.json")` ensures type coercion

## Entry Points

**CLI (Python Modules):**
- Location: Each phase is `python -m <module>`
- Examples:
  - `python -m data.ingest` — fetch vaastav + FPL API
  - `python -m data.build_table` — canonicalize
  - `python -m features.engineer` — rolling form
  - `python -m models.train` — train xP model
  - `python -m backtest.walk_forward` — multi-season eval
  - `python -m predict.live` — this week's recommendation
  - `python -m predict.export` — export JSON for site
  - `python -m data.snapshot` — daily bootstrap
  - `python -m models.price --train` — train price model (after 14 days)

**API Server:**
- Location: `api/main.py`
- Command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- Endpoints:
  - `GET /api/health` — liveness + pool freshness
  - `GET /api/meta` — gameweek, deadline, model stamp
  - `POST /api/solve` — ILP solve with locks/excludes/horizon/chips
  - `GET /api/rate/{entry}` — rate-my-team: squad xP vs optimum
  - `GET /api/team/{entry}` — fetch manager's current squad
  - `GET /` (static files) — serves `web/` directory

**Frontend (React + Vite):**
- Location: `frontend/`
- Development: `npm run dev` (starts Vite dev server on port 5173 with proxies to localhost:8000)
- Build: `npm run build` (compiles TypeScript + bundles to frontend/dist/)
- Preview: `npm run preview` (serves dist/ locally for testing production build)
- Test: `npm run test` (runs Vitest suite)
- Entry point: `frontend/src/main.tsx` (mounts React app to #root in index.html)
- Router: `frontend/src/router.tsx` (defines 8 routes + error boundaries)

**Cron/Scheduled Jobs:**
- `scripts/daily.sh` (cron 02:30 UTC):
  - `python -m data.snapshot` — idempotent bootstrap
  - `python -m models.price --train` (idempotent, no-op unless ≥14 days)
  - `python -m models.price` — emit watchlist
  - `python -m predict.scoreboard` — score finished GWs

- `scripts/weekly.sh` (cron 08:00 UTC Fridays):
  - `python -m data.live_history` — refresh rolling form for current season
  - `python -m predict.export` — export JSON + refresh form cache
  - `python -m models.price` — watchlist alongside fresh export
  - `python -m predict.digest` — render email

## Architectural Constraints

- **Threading:** API uses `threading.Lock()` for pool refresh (one thread rebuilds all pools; others wait). Solves are computed in parallel (thread-safe ILP).
- **Global state:** `api/main.py` holds `_state` (artifact, FPL snapshot, cached pools) and `_solve_cache`. All access guarded by `_lock`.
- **Circular imports:** Avoided by splitting concerns into phases (data → features → models → optimize → backtest → predict).
- **Time-based splits:** Training NEVER uses random splits. Strictly chronological: train on old seasons, validate on next, test on latest. This prevents future leakage.
- **Leakage-safe features:** Every rolling feature is shifted by one before rolling. Match-level targets (y_points, y_played) are never mixed with pre-match features.
- **Idempotency:** `data/snapshot.py` is idempotent per UTC day (no duplicates from re-runs). `models.price --train` only trains once (checks artifact exists).
- **Cache TTL:** Pool cache expires after 1 hour (`POOL_TTL_S = 3600`). Solve cache clears on refresh.
- **Constraint satisfaction:** All ILP solves enforce FPL rules (budget, quotas, formations, max-per-club). Results validated post-solve (`tests/test_legality.py`).
- **Frontend-backend contract:** Both React frontend and legacy site consume identical JSON from `web/data/` via relative paths (`/data/xp_table.json`). No custom API responses for UI — all UI surfaces are stateless and read-only.
- **Development isolation:** Vite dev server proxies `/api` and `/data` to `localhost:8000`; production FastAPI serves both from same process (no proxy needed).

## Anti-Patterns

### Hard-Coded Thresholds

**What happens:** Magic numbers like "5% jitter" in `backtest/walk_forward.py:JITTER_FRAC = 0.05` are not parameterized.

**Why it's wrong:** Changing noise levels requires editing code; no easy way to run sensitivity analyses.

**Do this instead:** Move configurable thresholds to `config.py` and accept command-line overrides in entry points. Example: `python -m backtest.walk_forward --jitter 0.08`.

### Model Re-training on Live Data

**What happens:** The live prediction (`predict/live.py`) re-uses the last trained model without re-fitting to recent seasons (cold-start).

**Why it's wrong:** Early-season predictions are weak (sparse rolling features); only price/fixture priors are strong.

**Do this instead:** After a few GWs are played, run the full pipeline (`data.ingest → build_table → features → models.train`) to retrain on fresh season data. This is documented but not automated.

### Chip Timing Heuristic

**What happens:** Chip scheduling (`optimize/chips.py:default_schedule()`) uses a fixture-structure heuristic, not an optimal search.

**Why it's wrong:** Some chip timings miss subtle value (e.g., captain pick vs BB in overlapping GWs).

**Do this instead:** Either (a) use a multi-period ILP that solves chip timing jointly with squad selection, or (b) generate k-best chip schedules and evaluate each via simulation.

## Error Handling

**Strategy:** Explicit, fail-fast approach; no silent defaults.

**Patterns:**
- **Missing data:** Raises `FileNotFoundError` or `SystemExit` with a helpful message (e.g., "Missing player_gw.parquet. Run `python -m data.build_table`.")
- **API failures:** `requests.get()` calls raise on HTTP errors (no silent None returns). FPL API timeouts trigger a retry (see `data/ingest.py`).
- **Validation errors:** ILP solves that violate constraints raise `ValueError` with the constraint name.
- **Leakage detection:** `tests/test_leakage.py` asserts no match outcome appears in pre-match features. Run before shipping.
- **Grid search:** `models/tune.py` logs hyperparameter results; failed evals raise exception (no silent NaN weights).
- **Frontend data errors:** React components use error boundaries + suspense. Network failures show `<ErrorState>` with retry button (see `frontend/src/components/ErrorState.tsx`). Missing optional fields (e.g., captains.json) fail gracefully in-place (see `XpTable.tsx:63-67`).

**Logging:** 
- Python: Minimal; mostly `print()` statements in entry points. Cron jobs redirect stdout/stderr to `data/cron.log` for later inspection.
- Frontend: `console.error(error)` on fetch failures; tests log to stdout.

## Cross-Cutting Concerns

**Logging:** 
- No library logger configured. Entry points use `print()` with timestamps.
- Cron jobs save output to `data/cron.log`.
- API has optional request logging (via FastAPI middleware).

**Validation:**
- Feature legality: `tests/test_leakage.py` ensures no match outcome in pre-match features.
- Squad legality: `tests/test_legality.py` checks all ILP solutions obey FPL rules.
- Autosub correctness: `tests/test_autosub.py` simulates matches and validates bench→XI substitutions.
- Frontend routing: `frontend/src/routes/routeIsolation.test.tsx` ensures each route can fail independently (error boundary per route, not shared).

**Authentication:**
- **Stub mode:** If `FPL_API_KEYS` env var is not set, API endpoints are open.
- **Stub mode:** If set, requires `X-API-Key` header (comma-separated keys in env var).
- **Migration path:** Replace `require_key()` in `api/main.py` with real Supabase JWT + subscriptions table when payments are live.
- **Frontend auth:** Not yet implemented; placeholder for future paid tiers.

**Rate limiting:**
- **Not implemented.** Pool cache + solve cache reduce server load; scale up CPU/memory if needed.
- **Future:** Add FastAPI `SlowAPIMiddleware` to rate-limit by IP or API key.

---

*Architecture analysis: 2026-09-01*
