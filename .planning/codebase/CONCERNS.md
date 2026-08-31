# Codebase Concerns

**Analysis Date:** 2026-08-31

## Tech Debt

**Auth and API security (blocking product launch):**
- Issue: Payment gate is a stub — `FPL_API_KEYS` env var → `X-API-Key` header only
- Files: `api/main.py::require_key()` (lines 159-163), comments (lines 14-15)
- Impact: No real user entitlements, no payments collection, no JWT validation
- Fix approach: Replace `require_key()` stub with Supabase JWT + subscriptions table validation; this is the single choke point by design, but must happen before serving real users

**CORS wide open:**
- Issue: API allows `["*"]` origins, methods, headers — no domain restriction
- Files: `api/main.py::app.add_middleware()` (lines 48-49)
- Impact: Any website can call /solve and /rate endpoints; no origin validation
- Fix approach: Restrict to deployed frontend domain(s) once hosting is known; e.g. `allow_origins=["https://yourdomain.com"]`

**Daily snapshot cron not scheduled:**
- Issue: `scripts/daily.sh` is cron-ready but not wired into the system scheduler
- Files: `scripts/daily.sh` (entire file), `README.md` line 91-92
- Impact: Price model training data is lost daily; cannot backfill history; price-change predictions remain disabled indefinitely
- Fix approach: Install cron job as: `30 2 * * * /home/sraja/fpl/scripts/daily.sh >> /home/sraja/fpl/data/cron.log 2>&1` (or use systemd timer on modern systems)

**Snapshots cannot be backfilled:**
- Issue: `data/snapshot.py::take_snapshot()` silently skips if `out.exists()`; no historical API archive
- Files: `data/snapshot.py::take_snapshot()` (lines 88-91)
- Impact: If cron misses a day, that day's training data is permanently lost; price model training quality degrades
- Fix approach: Document this limitation; implement a data-recovery endpoint (FPL may not support historical snapshots, so this may be irreversible)

**FPL API is undocumented and subject to change:**
- Issue: Relying on unofficial FPL API (`https://fantasy.premierleague.com/api/*`) which has no SLA or breaking-change notice
- Files: `config.py` (line 17), all files under `data/` and `predict/` that call FPL endpoints
- Impact: If FPL changes schema (player fields, fixture structure, pricing rules), live predictions break with no warning
- Fix approach: Pin tested API schema versions; add schema validation on bootstrap + fixtures payloads; monitor for API errors and alert early; consider building against a mock API for regression testing

**Chrome deb file in repo:**
- Issue: 134M Google Chrome binary (`google-chrome-stable_current_amd64.deb`) committed to repo
- Files: `/home/sraja/fpl/google-chrome-stable_current_amd64.deb`
- Impact: Massive repo bloat; slows clone/pull; unused after FBref scrape was abandoned
- Fix approach: Delete file; if browser automation needed again, document installation in README or CI config, never commit binary

## Known Bugs

**File handles not closed (resource leak):**
- Symptom: Many `open()` calls without context managers; can exhaust system file descriptors on long-running services
- Files: `data/live_history.py::47`, `data/id_map.py::53`, `models/intervals.py::85,95`, `predict/export.py::290,296`, `predict/live.py::44-45,196,274`, `predict/scoreboard.py::84,90,100`, `models/price.py::182,206`, `predict/digest.py::26`
- Trigger: Run a long-lived process (e.g. uvicorn API) and call live endpoints repeatedly; eventually `FileNotFoundError: [Errno 24] Too many open files`
- Workaround: Restart the API process periodically
- Fix approach: Replace all `json.load(open(...))` with `with open(...) as f: json.load(f)`, and `json.dump(..., open(..., "w"))` with `with open(..., "w") as f: json.dump(..., f)`

**Snapshot API failures silently fail in cron:**
- Symptom: If FPL API returns 5xx or times out during `scripts/daily.sh` cron run, error is printed to log but cron exits cleanly
- Files: `data/snapshot.py::92-93`, `scripts/daily.sh::14` (no error trap)
- Trigger: FPL API downtime during 02:30 UTC scheduled cron window
- Workaround: Manual re-run with `python -m data.snapshot` after API recovers
- Fix approach: Make cron errors visible: pipe stdout/stderr to a monitoring service; add a `--retry` mode to snapshot.py with exponential backoff; mark the snapshot failed if API errors occur

**Daily.sh `|| true` swallows price model training errors:**
- Symptom: Line 15 `$PY -m models.price --train || true` masks failures; if training breaks, the error is silently ignored
- Files: `scripts/daily.sh::15`
- Trigger: Price model training fails (e.g., insufficient data, dtype mismatch) — cron continues anyway
- Workaround: Check cron.log manually for warnings
- Fix approach: Remove `|| true`; let failures propagate; add log-level configuration to distinguish "no-op (not enough data)" from "error (crashed)"

**Missing or invalid JSON files cause uncaught exceptions:**
- Symptom: `predict/live.py::_load_live()` opens bootstrap and fixtures with no error handling; if files missing or corrupt, uncaught exception crashes the CLI
- Files: `predict/live.py::44-45`, similar patterns in `predict/scoreboard.py`, `predict/export.py`
- Trigger: Delete or corrupt `data/raw/live/bootstrap-static.json`; run `python -m predict.live`
- Workaround: Re-run `python -m data.ingest`
- Fix approach: Wrap JSON loads with try-except; log file path and error; exit cleanly with a helpful message; add a `--fetch-live` flag to explicitly refresh before proceeding

## Security Considerations

**API key exposed in cron logs:**
- Risk: If cron jobs set `FPL_API_KEYS` in environment or command line, keys may appear in cron error output or log files
- Files: `scripts/daily.sh`, `api/main.py::require_key()`
- Current mitigation: Keys stored in environment variables (best practice); not logged by default
- Recommendations: Use `.env` file with restricted permissions (mode 600) and load via `export $(cat .env | xargs)` (not version-controlled); add audit logging to API key validation; rotate keys periodically once payments are live

**CORS allows any origin to call /solve and /rate:**
- Risk: Any malicious website can call the solver API without restriction; could enable scraping or denial-of-service attacks
- Files: `api/main.py::48-49`
- Current mitigation: `require_key` stub gates paid endpoints, but if keys are compromised or stub is disabled, CORS does nothing
- Recommendations: Restrict origins to known frontend domain; add rate limiting per IP; add request signing (HMAC) for /solve and /rate

**Dependency versions not pinned (supply-chain risk):**
- Risk: `requirements.txt` uses `>=` constraints; a future release of lightgbm, pulp, or pandas could introduce breaking changes or security issues
- Files: `requirements.txt` (all lines)
- Current mitigation: None; dev environment uses conda-managed python314 which pins transitive deps
- Recommendations: Use `==` versions in production lockfile (e.g. `pip freeze > requirements.lock`); test major version upgrades before deploying

## Performance Bottlenecks

**Solve endpoint cache not invalidated on pool refresh:**
- Problem: `_solve_cache` dict persists across `_refresh()` calls; if model or pool becomes stale, cached results are still returned
- Files: `api/main.py::68,320,357` (cache cleared on refresh, but only if lock is held)
- Cause: Thread-safety mechanism has a race condition; cache is cleared inside `_lock`, but reads happen outside
- Improvement path: Attach cache TTL or pool version to cache key; invalidate if `time.time() - _state["loaded_at"] > POOL_TTL_S`

**Large parquet files loaded into memory on every predict.live call:**
- Problem: `data/processed/features.parquet` (16M) and `models/artifacts/xp_model.joblib` (7.1M) loaded via `joblib.load()` on every CLI run and API request
- Files: `api/main.py::62-64`, `predict/live.py::248`
- Cause: No persistent caching; model artifact reloaded even if nothing changed
- Improvement path: Cache model in process memory (already done in API `_state`); CLI should load once and reuse or use a background worker; consider quantization to reduce artifact size

**Backtests rebuild model for every season (no caching):**
- Problem: `backtest/walk_forward.py` retrains model from scratch for each test season; even with expanding-window validation, earlier folds recompute
- Files: `backtest/walk_forward.py` (entire module)
- Cause: Design choice for data leakage safety (strict time-based splits), but no cross-validation caching
- Improvement path: Implement incremental training or checkpoint cache; validate cache staleness against training data timestamps

## Fragile Areas

**Live predictions depend on consistent FPL API schema:**
- Files: `predict/live.py::_gw_pool()` (lines 103-162), `api/main.py::_fetch_team()`, `data/snapshot.py::snapshot_frame()`
- Why fragile: Hardcoded field names (`element_type`, `now_cost`, `web_name`, `status`, `chance_of_playing_next_round`, `price_change_percent`, etc.) with no schema validation
- Safe modification: Before accessing bootstrap or fixtures, validate structure with pydantic models or JSONSchema; add assertions on critical fields (e.g., `assert "elements" in bootstrap`); log schema changes detected
- Test coverage: No tests validate live API payload parsing; a breaking change goes unnoticed until CLI crashes mid-run

**FBref scrape abandoned but data seam still present:**
- Files: `data/fbref.py` (198 lines), config.py::FBREF_COLS, features/engineer.py (merges fbref if present)
- Why fragile: FBref returns empty cells since StatsBomb→Opta provider switch (2026-08); code still attempts merge; historical FBref cache is partial and inconsistent
- Safe modification: Document that FBref data is blocked at source; remove the seam or make it fully optional with graceful NaN handling; add a warning log when FBREF_COLS are requested but file is missing
- Test coverage: No tests verify fbref merge correctness or handle missing data edge cases

**Multi-period optimizer not integrated (sits unused):**
- Files: `optimize/multi_period.py` (151 lines), `backtest/multi_period_season.py` (unused in main backtest)
- Why fragile: Code is untested in live inference; small logic bugs (e.g., chip constraints, credit constraints) would only surface in production
- Safe modification: If re-enabling, add regression tests to `tests/` and validate against known good outputs; integrate into live `/api/plan` endpoint with A/B testing
- Test coverage: Exists in isolated backtest, but not in unit tests or API integration tests

## Scaling Limits

**Solve cache grows unbounded:**
- Current capacity: Dictionary grows with `len(_solve_cache)` over time; no eviction
- Limit: If API runs for weeks without restart, memory consumption grows linearly; eventually hits OOM or swaps to disk
- Scaling path: Implement LRU cache with max size (e.g., `functools.lru_cache(maxsize=1000)`) or use `cachetools.TTLCache`; clear cache on model reload; monitor cache hit/miss ratio

**Snapshot parquet directory has no quota:**
- Current capacity: `data/snapshots/` stores one parquet per day; at 53KB per file, ~19MB/year
- Limit: After 10+ years continuous operation, directory size becomes unwieldy; no cleanup policy
- Scaling path: Implement retention policy (e.g., keep 1 year of snapshots, archive older data); use a time-series database (InfluxDB, TimescaleDB) instead of parquets for long-term snapshots

**API pool computation is single-threaded:**
- Current capacity: `_pool()` builds the player pool synchronously; horizon > 1 computes multiple weeks sequentially
- Limit: Busy hour during deadline (last few hours before GW deadline) can see request queue backs up
- Scaling path: Pre-compute pools on a schedule; parallelize horizon pools with ThreadPoolExecutor; use a background job queue (Celery, RQ)

## Dependencies at Risk

**LightGBM model serialization (joblib + pickle):**
- Risk: `xp_model.joblib` contains pickled Python objects; upgrades to LightGBM, scikit-learn, or pandas can break deserialization
- Impact: API fails to start if artifact is incompatible; live predictions unavailable until model is retrained
- Migration plan: Before major version upgrades, retrain model and test deserialization; keep a version-locked environment for production; consider ONNX export as an escape hatch

**PuLP solver integration:**
- Risk: PuLP >= 2.8 can switch solvers (CBC default, others via add-ons); CBC binary must be installed separately
- Impact: If CBC is missing, solve requests 500; ILP constraints become infeasible if solver changes behavior
- Migration plan: Document solver installation in README; add solver health check to API startup; test with both CBC and ortools (alternative)

**Undocumented vaastav data schema:**
- Risk: `vaastav/Fantasy-Premier-League` repo on GitHub is community-maintained; schema can change or data can be retracted
- Impact: Data ingestion fails silently if column names change; historical training data becomes unavailable
- Migration plan: Version-pin the vaastav commit in data ingestion; snapshot raw CSVs locally once downloaded; maintain a secondary data source (e.g., FBref, Understat) as fallback

## Missing Critical Features

**No A/B testing or feature flag infrastructure:**
- Problem: Can't safely deploy model upgrades (e.g., captain-by-mean) to a subset of users for validation
- Blocks: Multi-variant experiment rollout; risk is high for any change

**No audit logging for API calls:**
- Problem: No trace of who called /solve, when, with what parameters, or what squad was returned
- Blocks: Debugging user issues; security incident investigation; SLA validation

**No monitoring or alerting:**
- Problem: If FPL API goes down, price model stops collecting data, or model predictions drift, no alert fires
- Blocks: Proactive incident response; knowing when the system is degraded

**No graceful degradation for API outages:**
- Problem: If FPL bootstrap is stale or unavailable, entire solver fails; no fallback to cached pool or baseline model
- Blocks: High availability during FPL infrastructure hiccups

## Test Coverage Gaps

**Live prediction integration not tested:**
- What's not tested: `predict/live.py` end-to-end; no tests verify that FPL API parsing, model inference, and optimization produce legal squads
- Files: `tests/` has `test_product.py` (export/scoreboard) and optimizer tests, but no `test_live.py`
- Risk: Changes to `_gw_pool()` or `build_pool()` break live inference silently; caught only when manual `python -m predict.live` fails
- Priority: High — this is the user-facing entrypoint

**API authentication not tested:**
- What's not tested: `require_key()` stub, cache invalidation, concurrent solve requests, error responses
- Files: `api/main.py` has no unit or integration tests
- Risk: Auth bypass, cache coherency bugs, or race conditions go unnoticed until production
- Priority: High — authentication and correctness are critical for product

**FPL API schema validation missing:**
- What's not tested: What happens if FPL API returns unexpected payload (missing fields, type changes, null values)
- Files: No schema validation in bootstrap or fixtures parsing
- Risk: Obscure `KeyError` or `TypeError` crashes during live inference
- Priority: Medium — adds robustness but low probability in practice

**Cron job execution not tested:**
- What's not tested: `scripts/daily.sh` and `scripts/weekly.sh` in isolation; no mock FPL API or filesystem
- Files: `scripts/` directory has no tests
- Risk: Cron jobs fail silently; no alerting; price model training stops without notice
- Priority: Medium — affects data quality but only discovered when model performance degrades

---

*Concerns audit: 2026-08-31*
