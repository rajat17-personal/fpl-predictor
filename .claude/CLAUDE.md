<!-- GSD:project-start source:PROJECT.md -->

## Project

**FPL Predictor — Production Hardening**

A Fantasy Premier League prediction and squad-optimization system: a LightGBM two-stage hurdle model predicts expected points (xP), ILP solvers pick squads/transfers/captains, and a FastAPI service plus a static site deliver weekly recommendations. This milestone hardens the system for production ahead of monetization: a React rebuild of the web UI with an FPL-style pitch renderer, CI/CD with Docker, real test coverage (API + Playwright E2E), and closure of the production-readiness gaps in the concerns audit.

**Core Value:** The weekly recommendations (xP table, squad, captains, transfers) must keep flowing reliably — every change in this milestone must leave the pipeline, API, and site at least as correct and more trustworthy than before.

### Constraints

- **Tech stack**: Python 3.14 backend stays as-is; frontend rebuild is React + Vite — user's explicit choice
- **Contract**: `web/data/*.json` export schema is the API between pipeline and site — rebuild consumes it unchanged
- **Hosting**: No live infrastructure yet — CI must end at a published Docker image + static build artifact, not a deploy
- **Budget**: Solo developer, pre-revenue — prefer free tiers (GitHub Actions, GHCR) and boring, maintainable choices
- **Timeline**: Paid launch target pre-season July 2027; hardening must not disrupt the weekly recommendation cycle during the current season
- **Environment**: conda env `python314` at `/home/sraja/miniconda3/envs/python314/bin/python` for all Python work

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.14 - All backend pipelines, models, and API

## Runtime

- Conda environment `python314` at `/home/sraja/miniconda3/envs/python314/bin/python3.14`
- Python 3.14+ required
- pip (managed through conda)
- Lockfile: `requirements.txt` (at project root)

## Frameworks

- FastAPI 0.110+ - REST API for squad optimization, team analysis, predictions (`api/main.py`)
- uvicorn 0.29+ - ASGI server to run FastAPI
- LightGBM 4.3+ - Two-stage hurdle xP (expected points) model per position (`models/train.py`)
- scikit-learn 1.4+ - Isotonic calibration for xP predictions, joblib for model serialization
- PuLP 2.8+ - Integer Linear Programming for squad/transfer optimization (`optimize/squad_ilp.py`, `optimize/transfers.py`)
- pandas 2.2+ - Data manipulation and aggregation
- numpy 1.26+ - Numeric operations
- pyarrow 15+ - Parquet file I/O (canonical data format)
- pytest - Test runner (config: `pytest.ini`)

## Key Dependencies

- requests 2.31+ - HTTP client for FPL API, football-data, odds APIs, and data ingestion
- scipy 1.12+ - Spearman rank correlation for scoreboard, general statistical functions
- joblib 1.3+ - Model persistence (`xp_model.joblib`), caching of fixtures/pools
- httpx 0.27+ - HTTP client for FastAPI TestClient
- understatapi 0.5+ - Free xG/xA expected value scraping from Understat
- seleniumbase - FBref browser automation (optional, for scraping advanced defensive stats) — requires Chrome/Chromium
- soccerdata - Mentioned in PROJECT_INDEX but superseded by direct FBref URL scraping due to Cloudflare reliability issues

## Configuration

- Config file: `config.py` (project root)
- `FPL_API_KEYS` - Comma-separated API keys for `/api/solve` and `/api/rate` endpoint authentication (stub implementation, upgradeable to Supabase JWT)
- `ODDS_API_KEY` - Optional API key for live bookmaker odds (free tier ~500 req/month)
- No build step; Python runs modules directly via `-m` flag (e.g., `python -m data.ingest`)
- Parquet files are pre-built into `data/processed/` during pipeline execution

## Platform Requirements

- Python 3.14 (conda environment `python314`)
- For FBref optional scraping: Chrome/Chromium browser + seleniumbase
- Python 3.14
- Deployment target: Any platform supporting Python + uvicorn (cloud functions, containers, VPS)
- FastAPI serves both REST API and static site (`web/` directory) from the same process
- Caching layer: in-memory (thread-safe dict) with 1-hour TTL for player pools

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- `snake_case.py` for modules (e.g., `data/ingest.py`, `models/train.py`, `optimize/squad_ilp.py`)
- Test files: `test_*.py` (e.g., `tests/test_legality.py`, `tests/test_leakage.py`)
- No file suffixes beyond `.py` for Python modules
- `camelCase` for public functions in JavaScript modules (`detectApiBase()`, `loadJSON()`, `makeSortable()`)
- `snake_case` for Python functions: `add_features()`, `train_predict()`, `fetch_vaastav_season()`
- Private/internal functions: prefix with underscore (`_download()`, `_roll()`, `_pool()`, `_assert_legal_squad()`)
- `snake_case` for all Python variables: `horizon_sum`, `sell_values`, `xp_med`, `total_points`
- `camelCase` for JavaScript variables: `apiBase`, `numLeaves`, `stateKey`
- Constants in ALL_CAPS in Python: `BUDGET = 100.0`, `SQUAD_SIZE = 15`, `MAX_PER_CLUB = 3`, `SEASONS = [...]`
- Local constants in ALL_CAPS: `HEADERS`, `TIMEOUT`, `ARTIFACTS`, `_EXCLUDE`
- Python: Use `from __future__ import annotations` for forward-compatible type hints (see `data/ingest.py:11`, `models/train.py:20`)
- Type hints on function signatures: `def add_features(df: pd.DataFrame) -> pd.DataFrame:`
- Union types use pipe syntax: `dict | None`, `list[str]`
- No type hints in JS (vanilla ES6 modules)

## Code Style

- Python: 4-space indentation (standard Python)
- JS: 2-space indentation (see `web/assets/app.js`)
- Line length: appears to be ~90-100 characters in Python
- No explicit linter/formatter config detected (no `.flake8`, `.pylintrc`, `pyproject.toml` config)
- Not configured (no `.eslintrc`, `.flake8`, or linting config files present)
- Code follows implicit conventions: clean imports, type hints, docstrings

## Import Organization

- `export` statements for public API at module level
- Helper functions and state below
- No path aliases configured; imports use relative paths within the project
- Implicit: `import config` works because `config.py` is at project root
- Submodules imported as: `from data.ingest import fetch_vaastav_season`, `from optimize.transfers import optimize_gw`

## Error Handling

- **HTTP errors:** `resp.raise_for_status()` to throw on non-2xx, then catch `requests.HTTPError` and `requests.RequestException` (see `data/ingest.py:28-44`)
- **Optional enrichment:** `try/except Exception` when a data source is optional (see `data/build_table.py` for odds/fbref)
- **Solver failures:** `raise RuntimeError(f"multi-period solve: {pulp.LpStatus[m.status]}")` (see `optimize/multi_period.py`)
- **Parameter validation:** `raise ValueError(f"objective '{objective}' unsupported...")` (see `models/train.py`)
- **User-facing CLI errors:** `raise SystemExit("Missing player_gw.parquet. Run `python -m data.build_table`.")` (see `features/engineer.py:110`)
- **Test assertions:** Direct `pytest.raises(ValueError)` for expected exceptions (see `tests/test_legality.py:92`)

## Logging

- Print status/progress with context tags: `print(f"  saved    {dest.relative_to(config.ROOT)}")` (see `data/ingest.py:48`)
- Module-tagged info: `print(f"[price] {message}")`, `print(f"[odds] live fetch failed...")` (see `data/live_odds.py`, `models/price.py`)
- Structured reporting: `print("\n=== features summary ===")` followed by organized output (see `features/engineer.py:89-104`)
- Indented status for hierarchical info: `print(f"  cached   {dest.relative_to(config.ROOT)}")` (nested under parent operation)
- When to print: status messages, progress counters, warnings about optional data, final artifact paths

## Comments

- Module-level docstring: Always. Explains purpose, design decisions, and usage (see every file)
- Function/class docstrings: Always. Single-line summary + details if complex (see `data/ingest.py:53-74`)
- Inline comments: Explain *why*, not what. Used sparingly (see `models/train.py:39` — "FPL's own prediction")
- Design notes: Multi-line at module top inside docstring (see `api/main.py:10-16`)
- Not used. JavaScript uses inline comments only (see `web/assets/app.js:1-7`)
- Python docstrings explain algorithm/constraints inline (see `backtest/season.py`, `features/engineer.py:5-16`)

## Function Design

- Functions range 10-50 lines typically
- Longer functions (50-100+) are algorithmic (e.g., optimizer MILP setup in `optimize/multi_period.py`)
- Private helpers extracted for reusability and clarity
- Named, typed: `def train_predict(df: pd.DataFrame, train_seasons, val_season, test_seasons, params: dict | None = None, objectives: dict | None = None, minutes_model: str = "binary", calibrate: bool = False):`
- Keyword-only args after `*` where they denote options: `def fetch_vaastav_season(season: str, *, force: bool = False)`
- Defaults for optional enrichment/behavior
- Single values for simple operations
- Dicts for complex results: `return {"squad": ..., "bank": ..., "transfers": ...}` (optimizer output)
- Dicts with optional fields: `{"p10": ..., "p90": ...}` (intervals)
- None for side-effect operations (e.g., `summarise()`)
- Tuple for multi-value return when order matters (rare)

## Module Design

- Python: No explicit `__all__` found; public API inferred from function/class names (those not prefixed with `_`)
- JavaScript: `export` keyword for public API (see `web/assets/app.js:3,9,24,30,44,57,81,91`)
- Used minimally; most `__init__.py` are empty (e.g., `data/__init__.py`, `features/__init__.py`, `api/__init__.py`)
- No re-exports; submodules imported directly: `from data.ingest import ...`

## CLI Entry Points

- Modules are executable via `python -m module_name`
- Main function at module bottom: `def main() -> int:` (see `features/engineer.py:107-122`)
- Exit via `sys.exit(main())` or `if __name__ == "__main__": sys.exit(main())`
- Docstring at module top documents usage: `python -m data.ingest`, `python -m models.train` (see every module's docstring)
- argparse for CLI args: `ap = argparse.ArgumentParser()`, `ap.add_argument(...)` (see `predict/live.py`)

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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
| **Static Site** | Framework-free HTML/JS consuming web/data/*.json; renders tables, charts, team editor | `web/` |

## Pattern Overview

- **Leakage-safe**: All features for a fixture are computed from matches before it (strict temporal validation)
- **Retrainable**: Core components (data, features, models) can re-run without product disruption
- **Cacheable**: Predictions are exported to JSON; API caches pools + solves by (GW, params)
- **Modular entry points**: Each phase (`python -m module`) can run independently; cron orchestrates sequences
- **Two-objective model**: Core squad selection uses median xP (robust); captain picks use mean xP (doubles points, so maximize expectation)

## Layers

- Purpose: Ingest, canonicalize, enrich player-GW records
- Location: `data/`
- Contains: FPL API fetch, vaastav history aggregation, ID mapping, odds de-overrounding, FBref scraper
- Depends on: External APIs (FPL, football-data.co.uk, GitHub vaastav)
- Used by: Feature engineering, live prediction, snapshots
- Artifacts: `data/raw/` (cached downloads), `data/processed/player_gw.parquet`
- Purpose: Engineer leakage-safe rolling form + context features
- Location: `features/engineer.py`
- Contains: Multi-window rolling aggregations (3/5/10/all), volatility, congestion, target encoding
- Depends on: `data/processed/player_gw.parquet`
- Used by: Model training
- Artifacts: `data/processed/features.parquet`
- Purpose: Train two-stage per-position hurdle model (P(play) × E[pts|played])
- Location: `models/train.py`, `models/tune.py`, `models/calibration.py`
- Contains: LightGBM classifier + regressor per position, isotonic calibration, hyperparameter search
- Depends on: `data/processed/features.parquet`
- Used by: Live prediction, export, API
- Artifacts: `models/artifacts/xp_model.joblib`, intervals artifact (p10/p90 bands)
- Purpose: Solve integer linear programs for squad, transfers, chip timing
- Location: `optimize/`
- Contains: Squad selection ILP (squad+XI+captain), weekly transfer ILP (sell/buy decisions), chip scheduler, multi-period horizon expansion
- Depends on: xP predictions, current squad state (for transfers)
- Used by: Live prediction, export, API solver
- No persistent artifacts (solves on-demand)
- Purpose: Evaluate predictions via multi-season walk-forward simulation with noise controls
- Location: `backtest/`
- Contains: Season state machine (transfers, autosubs, chip application), walk-forward retraining loop, jitter-based confidence intervals
- Depends on: All ML layers (trains per test season)
- Used by: Validation, reporting (PLAN.md, ROADMAP.md)
- Artifacts: `data/processed/test_predictions.parquet` (saved during walk-forward)
- Purpose: Emit weekly xP predictions + recommendations in multiple formats
- Location: `predict/`
- Contains: Live pool builders, export to JSON, scoreboard evaluation, email digest
- Depends on: Trained model, FPL API (live data), optimization layer
- Used by: Product layer (API + site), email distribution
- Artifacts: `web/data/*.json` (xp_table, captains, squad, etc.), digest HTML
- Purpose: Serve predictions via API and static site
- Location: `api/main.py`, `web/`
- Contains: FastAPI app (cached pool builders, solve endpoint, auth stub), static HTML consuming JSON
- Depends on: `web/data/` JSON exports, trained model (for intervals)
- Used by: End users (web browser, API clients)
- Thread safety: `api/main.py` uses `threading.Lock()` for pool refresh + solve cache
- Purpose: Orchestrate daily + weekly pipeline runs
- Location: `scripts/daily.sh`, `scripts/weekly.sh`, `.github/workflows/`
- Contains: Ordered execution of snapshot, price model, export, digest
- Depends on: All prior layers
- Used by: System scheduler (or GitHub Actions)
- Triggers: daily.sh @ 02:30 UTC, weekly.sh @ 08:00 UTC Fridays

## Data Flow

### Primary Request Path (Weekly Prediction Export)

### Live Prediction Flow (Interactive CLI)

### API Request Flow (`/api/solve`)

### Backtest Flow (Walk-Forward Validation)

- `api/main.py` maintains thread-safe `_state` dict:

## Key Abstractions

- Purpose: Bakes in "non-playing player scores 0" into a single xP value
- Formula: `xP = P(play) × E[points | played]`
- Implementation: Two-stage LightGBM (classifier + regressor, per position) in `models/train.py`
- Why two-stage: Dynamics of "will I play?" differ from "how many points if I play?" — separate models pick better features
- Examples: `models/artifacts/xp_model.joblib`
- Purpose: Ensure no information from a match "leaks" into its own prediction
- Pattern: Every feature is `shift(1)` then rolled (moving avg over prior N matches)
- Implementation: `features/engineer.py:_roll()` uses `.shift(1).rolling().mean()`
- Example: A player's expected points in GW5 cannot include their GW5 performance
- Purpose: Solve squad + XI + captain + transfers + chips as a single mathematical program
- Solver: PuLP (Python API over CBC/SCIP)
- Components:
- Multi-period (`optimize/multi_period.py`): Chain single-GW solves over a horizon (lookahead planning)
- Purpose: Decouple product layer (API + site) from CLI (prediction logic)
- Files in `web/data/`:
- Why: Allows API/site to work offline; enables versioning + replay
- Purpose: Reduce single-season noise via multiple retrains + jitter
- Design: Expanding-window retrain per test season (avoid lookahead bias)
- Confidence bands: K jittered replicas (5% noise on xP) → within-season range
- Isolated chips: Measure each chip on the same team with/without it
- Files: `data/processed/test_predictions.parquet` (frozen predictions per test season)

## Entry Points

- Location: Each phase is `python -m <module>`
- Examples:
- Location: `api/main.py`
- Command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- Endpoints:
- `scripts/daily.sh` (cron 02:30 UTC):
- `scripts/weekly.sh` (cron 08:00 UTC Fridays):

## Architectural Constraints

- **Threading:** API uses `threading.Lock()` for pool refresh (one thread rebuilds all pools; others wait). Solves are computed in parallel (thread-safe ILP).
- **Global state:** `api/main.py` holds `_state` (artifact, FPL snapshot, cached pools) and `_solve_cache`. All access guarded by `_lock`.
- **Circular imports:** Avoided by splitting concerns into phases (data → features → models → optimize → backtest → predict).
- **Time-based splits:** Training NEVER uses random splits. Strictly chronological: train on old seasons, validate on next, test on latest. This prevents future leakage.
- **Leakage-safe features:** Every rolling feature is shifted by one before rolling. Match-level targets (y_points, y_played) are never mixed with pre-match features.
- **Idempotency:** `data/snapshot.py` is idempotent per UTC day (no duplicates from re-runs). `models.price --train` only trains once (checks artifact exists).
- **Cache TTL:** Pool cache expires after 1 hour (`POOL_TTL_S = 3600`). Solve cache clears on refresh.
- **Constraint satisfaction:** All ILP solves enforce FPL rules (budget, quotas, formations, max-per-club). Results validated post-solve (`tests/test_legality.py`).

## Anti-Patterns

### Hard-Coded Thresholds

### Model Re-training on Live Data

### Chip Timing Heuristic

## Error Handling

- **Missing data:** Raises `FileNotFoundError` or `SystemExit` with a helpful message (e.g., "Missing player_gw.parquet. Run `python -m data.build_table`.")
- **API failures:** `requests.get()` calls raise on HTTP errors (no silent None returns). FPL API timeouts trigger a retry (see `data/ingest.py`).
- **Validation errors:** ILP solves that violate constraints raise `ValueError` with the constraint name.
- **Leakage detection:** `tests/test_leakage.py` asserts no match outcome appears in pre-match features. Run before shipping.
- **Grid search:** `models/tune.py` logs hyperparameter results; failed evals raise exception (no silent NaN weights).

## Cross-Cutting Concerns

- No library logger configured. Entry points use `print()` with timestamps.
- Cron jobs save output to `data/cron.log`.
- API has optional request logging (via FastAPI middleware).
- Feature legality: `tests/test_leakage.py` ensures no match outcome in pre-match features.
- Squad legality: `tests/test_legality.py` checks all ILP solutions obey FPL rules.
- Autosub correctness: `tests/test_autosub.py` simulates matches and validates bench→XI substitutions.
- **Stub mode:** If `FPL_API_KEYS` env var is not set, API endpoints are open.
- **Stub mode:** If set, requires `X-API-Key` header (comma-separated keys in env var).
- **Migration path:** Replace `require_key()` in `api/main.py` with real Supabase JWT + subscriptions table when payments are live.
- **Not implemented.** Pool cache + solve cache reduce server load; scale up CPU/memory if needed.
- **Future:** Add FastAPI `SlowAPIMiddleware` to rate-limit by IP or API key.

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
