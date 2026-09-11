---
last_mapped_commit: 382338e2c164a4433cd73cdbb12ffc9be2621493
---
# Technology Stack

**Analysis Date:** 2026-09-11

## Languages

**Primary:**
- Python 3.14 - All backend pipelines, models, API, and data processing
- TypeScript 6.0.3 - Frontend UI components, routes, utilities, E2E tests

**Secondary:**
- JavaScript (ES2023) - Frontend React components, transpiled via TypeScript

## Runtime

**Environment:**
- Python: conda environment `python314` at `/home/sraja/miniconda3/envs/python314/bin/python3.14`
- Node.js: version managed by package-lock.json (no `.nvmrc` present)

**Package Manager:**
- Python: pip (managed through conda)
  - Lockfile: `requirements.txt` (at project root)
  - Dev lockfile: `requirements-dev.txt` (test-only dependencies)
  - RL experimental lockfile: `requirements-rl.txt` (Phase 09 MaskablePPO training only, never shipped)
- Node: npm
  - Frontend lockfile: `frontend/package-lock.json`
  - E2E lockfile: `e2e/package-lock.json`

## Frameworks

**Backend:**
- FastAPI 0.110+ - REST API for squad optimization, team analysis, predictions (`api/main.py`)
- uvicorn 0.29+ - ASGI server to run FastAPI
- LightGBM 4.3+ - Two-stage hurdle xP (expected points) model per position (`models/train.py`)
- scikit-learn 1.4+ - Isotonic calibration for xP predictions, joblib for model serialization
- PuLP 3.3–<4.0 - Integer Linear Programming for squad/transfer optimization (`optimize/squad_ilp.py`, `optimize/transfers.py`, `optimize/multi_period.py`)

**Frontend:**
- React 19.2.8+ - UI framework with Server Component compatibility (`frontend/src/`)
- React Router 7.18.3 - Client-side routing (`frontend/src/router.tsx`)
- Vite 7.3.6 - Build tool and dev server (config: `frontend/vite.config.ts`)
- Tailwind CSS 4.3.3 - Utility-first CSS framework with @tailwindcss/vite integration
- TanStack Query 5.102.8 - Server state management, caching, data fetching (replaces `react-query`)
- react-markdown 10.1.0 - Markdown content rendering
- lucide-react 1.38.0 - Icon library

**Data & ML:**
- pandas 2.2+ - Data manipulation and aggregation
- numpy 1.26+ - Numeric operations
- pyarrow 15+ - Parquet file I/O (canonical data format)
- scipy 1.12+ - Spearman rank correlation, statistical functions

**Testing:**
- pytest 8+ - Python test runner (config: `pytest.ini`)
- Vitest 4.1.11 - Frontend unit test runner (config: `frontend/vitest.config.ts`)
- @playwright/test 1.62.1 - E2E browser testing (config: `e2e/playwright.config.ts`)
- @testing-library/react 16.3.3 - React component testing utilities
- jsdom 30.0.1 - DOM environment for Node.js testing

**RL Experiments (Phase 09, development-only):**
- torch 2.12.0 - PyTorch (with CUDA 13.0 support, pinned below 2.14.0)
- gymnasium 1.3.0 - Farama Foundation RL environment API (Gym successor)
- stable-baselines3 2.9.0 - RL algorithms library (parent of MaskablePPO)
- sb3-contrib 2.9.0 - MaskablePPO + ActionMasker for masked action space

**Linting:**
- ruff 0.16.6 - Python linter for CI-01 lint step (dev/CI-side only, config: `ruff.toml`)

## Key Dependencies

**Critical (Backend):**
- requests 2.31+ - HTTP client for FPL API, football-data, odds APIs
- joblib 1.3+ - Model persistence (`xp_model.joblib`), caching
- httpx 0.27+ - HTTP client for FastAPI TestClient
- responses 0.25-<0.27 - FPL API HTTP mocking in tests

**Infrastructure (Backend):**
- understatapi 0.7.1 - Free xG/xA scraping from Understat (pinned exact; newer versions add deps)

**Web Scraping:**
- lxml >=6.1,<7 - HTML parsing for pandas.read_html (Transfermarkt, FBref via `pandas.io.html`)
- beautifulsoup4 >=4.13 - HTML parsing library (imported as `bs4`, data/fbref.py, data/transfermarkt.py)
- html5lib >=1.1 - Required alongside bs4 for pandas.read_html's bs4 flavor leg
- certifi >=2025.11.12 - SSL certificate bundle (pinned directly to survive from-lockfile-only rebuilds)

**Development (Frontend):**
- @vitejs/plugin-react 5.2.0 - React support for Vite (dev)
- @types/node 26.4.0–26.4.1 - Node.js type definitions (dev)
- @types/react 19.2.18 - React type definitions (dev)
- @types/react-dom 19.2.4 - ReactDOM type definitions (dev)
- @testing-library/jest-dom 7.0.1 - Custom Jest matchers (dev)
- typescript 6.0.3 - TypeScript compiler (dev)

**Self-Hosted Fonts:**
- @fontsource/archivo 5.3.0 - Archivo font
- @fontsource/ibm-plex-mono 5.3.0 - IBM Plex Mono font
- @fontsource/ibm-plex-sans 5.3.0 - IBM Plex Sans font

## Configuration

**Environment:**
- Python: `python314` conda environment (required for all Python work)
- Frontend dev: Vite dev server with proxy to `localhost:8000` for `/api` and `/data` paths
- E2E testing: Full uvicorn lifecycle control; builds frontend, boots fixture-mode server on separate port, drives Chromium (config: `e2e/playwright.config.ts`)
  - Three parallel servers for variants: normal (`8100`), blank (`8101`), DGW (`8102`)
  - Fixture mode: `FPL_FIXTURE_DIR` env var points to frozen data directory
  - Mandatory locale: en-GB, timezone: UTC (for deadline string determinism)
- CI/CD: GitHub Actions with Python 3.12 for workflow runners (see `.github/workflows/daily.yml`, `weekly.yml`)
- Module execution: `PYTHONPATH=.` for `python -m` imports

**Build & Dev:**
- Python linting: ruff 0.16.6 (config: `ruff.toml`)
  - Target: Python 3.14, line-length 100
  - Exclude: generated/regenerable subtrees (`data/raw`, `data/processed`, `models/artifacts`, `frontend`, `web`, etc.)
  - Rules: E4, E7, E9, F (syntax/undefined name errors only)
- Frontend build: `tsc -b && vite build` (type-check first, then Vite bundle)
  - Post-build: `cp dist/index.html dist/404.html` (SPA fallback for client routing)
- Frontend dev: `vite` (dev server with proxy to FastAPI backend)
- Frontend test: `vitest run` or `vitest` (watch mode)
- Frontend type-check: `tsc --noEmit`
- E2E test: `npm run test` (runs full Playwright suite with fixture servers)
  - Local: `E2E_PYTHON=/path/to/python npm run test` (must specify conda interpreter)
  - CI: `python` already on PATH, no E2E_PYTHON needed
  - Fast local: `E2E_VARIANTS=0 npm run test` (single server, normal fixtures only)
- Backend testing: `pytest` (discovers tests in `tests/` directory)
- Docker build: Multi-stage (builder + runtime)
  - Builder: Installs dependencies with `--require-hashes`, no compiler
  - Runtime: python:3.14-slim + libstdc++6 + libgomp1 (CBC and LightGBM require these)
  - No model artifact, .env, or pipeline data in image
  - Non-root user `appuser` (uid 10001) for container hardening
  - Health check: HTTP GET `/api/health` with 30s interval, 5s timeout, 3 retries

**TypeScript Configuration (`frontend/tsconfig.app.json`):**
- Target: ES2023
- Module resolution: bundler mode
- JSX: react-jsx (automatic transform)
- Strict checks: noUnusedLocals, noUnusedParameters, noFallthroughCasesInSwitch
- No emit: true (type-check only, Vite handles compilation)

**Python Configuration (`config.py`):**
- Paths: `DATA_DIR`, `RAW_DIR`, `PROCESSED_DIR`
- Data sources: `VAASTAV_RAW`, `FPL_API`
- Training splits: `SEASONS`, `TRAIN_SEASONS`, `VAL_SEASON`, `TEST_SEASONS`
- FPL rules: `BUDGET`, `SQUAD_SIZE`, `POSITION_QUOTA`, `MAX_PER_CLUB`, `TRANSFER_HIT`
- Features: `WINDOWS`, `POSITIONS`, `SET_PIECE_COLS`, `ODDS_COLS`, `FBREF_COLS`

## Platform Requirements

**Development:**
- Python 3.14 (conda environment `python314`)
- Node.js (for frontend build/dev/E2E testing)
- System utilities: curl/wget (for external data downloads)
- Optional: Chrome/Chromium (for FBref scraping with seleniumbase; required for E2E tests)

**Production (Docker):**
- Python 3.14-slim base image
- libstdc++6 (for PuLP's bundled CBC solver binary)
- libgomp1 (for LightGBM's libomp dependency)
- Non-root user `appuser` (uid 10001)
- No Node.js, no development tooling
- No model artifact (supplied at deploy time next milestone)

**Deployment:**
- Deployment target: Any platform supporting Python 3.14 + uvicorn
- FastAPI serves:
  - REST API endpoints at `/api/*`
  - Static frontend at `/` (from `frontend/dist/`)
  - JSON data exports at `/data/*` (from `web/data/`)
- Thread-safe caching: In-memory dict with `threading.Lock()`, 1-hour pool TTL
- Health check: `/api/health` endpoint (30s polling, 5s timeout, 3 retries)

---

*Stack analysis: 2026-09-11*
