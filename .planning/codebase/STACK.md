# Technology Stack

**Analysis Date:** 2026-08-31

## Languages

**Primary:**
- Python 3.14 - All backend pipelines, models, and API

## Runtime

**Environment:**
- Conda environment `python314` at `/home/sraja/miniconda3/envs/python314/bin/python3.14`
- Python 3.14+ required

**Package Manager:**
- pip (managed through conda)
- Lockfile: `requirements.txt` (at project root)

## Frameworks

**Core:**
- FastAPI 0.110+ - REST API for squad optimization, team analysis, predictions (`api/main.py`)
- uvicorn 0.29+ - ASGI server to run FastAPI

**ML Model:**
- LightGBM 4.3+ - Two-stage hurdle xP (expected points) model per position (`models/train.py`)
- scikit-learn 1.4+ - Isotonic calibration for xP predictions, joblib for model serialization

**Optimization:**
- PuLP 2.8+ - Integer Linear Programming for squad/transfer optimization (`optimize/squad_ilp.py`, `optimize/transfers.py`)

**Data Processing:**
- pandas 2.2+ - Data manipulation and aggregation
- numpy 1.26+ - Numeric operations
- pyarrow 15+ - Parquet file I/O (canonical data format)

**Testing:**
- pytest - Test runner (config: `pytest.ini`)

## Key Dependencies

**Critical:**
- requests 2.31+ - HTTP client for FPL API, football-data, odds APIs, and data ingestion
- scipy 1.12+ - Spearman rank correlation for scoreboard, general statistical functions
- joblib 1.3+ - Model persistence (`xp_model.joblib`), caching of fixtures/pools
- httpx 0.27+ - HTTP client for FastAPI TestClient

**Data Source Integration:**
- understatapi 0.5+ - Free xG/xA expected value scraping from Understat

**Optional (Feature-dependent):**
- seleniumbase - FBref browser automation (optional, for scraping advanced defensive stats) — requires Chrome/Chromium
- soccerdata - Mentioned in PROJECT_INDEX but superseded by direct FBref URL scraping due to Cloudflare reliability issues

## Configuration

**Environment:**
- Config file: `config.py` (project root)
  - Paths: `DATA_DIR`, `RAW_DIR`, `PROCESSED_DIR`
  - Data sources: `VAASTAV_RAW`, `FPL_API`
  - Training/validation/test splits: `SEASONS`, `TRAIN_SEASONS`, `VAL_SEASON`, `TEST_SEASONS`
  - FPL rules: `BUDGET`, `SQUAD_SIZE`, `POSITION_QUOTA`, `MAX_PER_CLUB`, `TRANSFER_HIT`, `SELL_ON_FEE`
  - Features: `WINDOWS`, `POSITIONS`, `SET_PIECE_COLS`, `ODDS_COLS`, `FBREF_COLS`

**API Environment Variables:**
- `FPL_API_KEYS` - Comma-separated API keys for `/api/solve` and `/api/rate` endpoint authentication (stub implementation, upgradeable to Supabase JWT)
- `ODDS_API_KEY` - Optional API key for live bookmaker odds (free tier ~500 req/month)

**Build:**
- No build step; Python runs modules directly via `-m` flag (e.g., `python -m data.ingest`)
- Parquet files are pre-built into `data/processed/` during pipeline execution

## Platform Requirements

**Development:**
- Python 3.14 (conda environment `python314`)
- For FBref optional scraping: Chrome/Chromium browser + seleniumbase

**Production:**
- Python 3.14
- Deployment target: Any platform supporting Python + uvicorn (cloud functions, containers, VPS)
- FastAPI serves both REST API and static site (`web/` directory) from the same process
- Caching layer: in-memory (thread-safe dict) with 1-hour TTL for player pools

---

*Stack analysis: 2026-08-31*
