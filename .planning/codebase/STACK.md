# Technology Stack

**Analysis Date:** 2026-09-01

## Languages

**Primary:**
- Python 3.14 - All backend pipelines, models, API, and data processing
- TypeScript 6.0.3 - Frontend UI components, routes, utilities

**Secondary:**
- JavaScript (ES2023) - Frontend React components, transpiled via TypeScript

## Runtime

**Environment:**
- Python: conda environment `python314` at `/home/sraja/miniconda3/envs/python314/bin/python3.14`
- Node.js: version managed by package-lock.json (no `.nvmrc` present)

**Package Manager:**
- Python: pip (managed through conda)
  - Lockfile: `requirements.txt` (at project root)
- Node: npm
  - Lockfile: `frontend/package-lock.json`

## Frameworks

**Backend:**
- FastAPI 0.110+ - REST API for squad optimization, team analysis, predictions (`api/main.py`)
- uvicorn 0.29+ - ASGI server to run FastAPI
- LightGBM 4.3+ - Two-stage hurdle xP (expected points) model per position (`models/train.py`)
- scikit-learn 1.4+ - Isotonic calibration for xP predictions, joblib for model serialization
- PuLP 2.8+ - Integer Linear Programming for squad/transfer optimization (`optimize/squad_ilp.py`, `optimize/transfers.py`)

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
- pytest - Python test runner (config: `pytest.ini`)
- Vitest 4.1.11 - Frontend test runner (config: `frontend/vitest.config.ts`)
- @testing-library/react 16.3.3 - React component testing
- jsdom 30.0.1 - DOM environment for Node.js

## Key Dependencies

**Critical (Backend):**
- requests 2.31+ - HTTP client for FPL API, football-data, odds APIs
- joblib 1.3+ - Model persistence (`xp_model.joblib`), caching
- httpx 0.27+ - HTTP client for FastAPI TestClient
- responses 0.25-0.26 - FPL API HTTP mocking in tests

**Infrastructure (Backend):**
- understatapi 0.5+ - Free xG/xA scraping from Understat

**Development (Frontend):**
- @vitejs/plugin-react 5.2.0 - React support for Vite (dev)
- @types/node 26.4.0 - Node.js type definitions (dev)
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
- Python: `python314` conda environment
- Frontend dev: Vite dev server with proxy to `localhost:8000` for `/api` and `/data` paths
- CI/CD: GitHub Actions with Python 3.12 (see `.github/workflows/daily.yml`, `weekly.yml`)
- Module execution: `PYTHONPATH=.` for `python -m` imports

**Build & Dev:**
- Frontend build: `tsc -b && vite build` (type-check first, then Vite bundle)
- Frontend dev: `vite` (dev server with proxy to FastAPI backend)
- Frontend test: `vitest run` or `vitest` (watch mode)
- Frontend type-check: `tsc --noEmit`
- Backend testing: `pytest` (discovers tests in `tests/` directory)

**TypeScript (`frontend/tsconfig.app.json`):**
- Target: ES2023
- Module resolution: bundler mode
- JSX: react-jsx (automatic transform)
- Strict checks: noUnusedLocals, noUnusedParameters, noFallthroughCasesInSwitch
- No emit: true (type-check only)

**Python Configuration (`config.py`):**
- Paths: `DATA_DIR`, `RAW_DIR`, `PROCESSED_DIR`
- Data sources: `VAASTAV_RAW`, `FPL_API`
- Training splits: `SEASONS`, `TRAIN_SEASONS`, `VAL_SEASON`, `TEST_SEASONS`
- FPL rules: `BUDGET`, `SQUAD_SIZE`, `POSITION_QUOTA`, `MAX_PER_CLUB`, `TRANSFER_HIT`
- Features: `WINDOWS`, `POSITIONS`, `SET_PIECE_COLS`, `ODDS_COLS`, `FBREF_COLS`

## Platform Requirements

**Development:**
- Python 3.14 (conda environment)
- Node.js (for frontend build/dev)
- System utilities: curl/wget (for external data downloads)
- Optional: Chrome/Chromium (for FBref scraping with seleniumbase)

**Production:**
- Python 3.14 (or 3.12+ for GitHub Actions)
- uvicorn ASGI server
- Node.js NOT required (frontend is pre-built to static files)
- Deployment target: Any platform supporting Python + uvicorn
- FastAPI serves:
  - REST API endpoints at `/api/*`
  - Static frontend at `/` (from `frontend/dist/`)
  - JSON data exports at `/data/*` (from `web/data/`)
- Thread-safe caching: In-memory dict with `threading.Lock()`, 1-hour pool TTL

---

*Stack analysis: 2026-09-01*
