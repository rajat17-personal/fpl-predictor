# Project Index: FPL ML (Fantasy Premier League predictor)

Generated: 2026-08-21 · updated 2026-08-31 (product layer) · Python 3.14 (conda env `python314`)

Predicts expected points (xP) per player with LightGBM, then selects the optimal
legal squad/XI/captain/transfers/chips with integer linear programming. Full build
log in [PLAN.md](PLAN.md); usage in [README.md](README.md); productization plan
and status in [ROADMAP.md](ROADMAP.md).

## 📁 Structure

```
config.py            constants, paths, seasons/splits, FPL rules, feature lists
data/                ingest + canonical table build
features/engineer.py leakage-safe rolling features
models/              two-stage xP model + tuning
optimize/            ILP squad/transfers/chips + pricing
backtest/            season sim + multi-season walk-forward
predict/live.py      live weekly recommendation (FPL API)
predict/export.py    weekly JSON for the site (+ frozen history for scoreboard)
predict/scoreboard.py post-GW accuracy scoring (us vs FPL's ep_next vs actual)
predict/digest.py    email digest (text + HTML) from exported JSON
data/snapshot.py     DAILY bootstrap snapshot (price-model training data)
models/intervals.py  empirical p10/p90 bands from held-out residuals
models/price.py      price-change watchlist (heuristic → LightGBM at 14+ days)
api/main.py          FastAPI: serves web/ + /api/solve, /api/rate, /api/team
web/                 static site (Cloudflare Pages-ready) reading web/data/*.json
scripts/             daily.sh + weekly.sh cron entry points (.github/workflows mirror)
data/processed/*.parquet   player_gw, features, id_map, odds, test_predictions
data/snapshots/*.parquet   one per day (do not lose — not backfillable)
```

## 🚀 Entry points (`python -m <module>`)

| Command | Purpose |
|---|---|
| `data.ingest` | download vaastav history + live FPL API |
| `data.id_map` | build stable player_code map |
| `data.odds` | football-data.co.uk → implied probabilities |
| `data.fbref --scrape` | optional FBref advanced stats (needs Chrome) |
| `data.build_table` | → `player_gw.parquet` (canonical) |
| `features.engineer` | → `features.parquet` |
| `models.train` | train xP model → `models/artifacts/xp_model.joblib` |
| `models.tune` | validation-scored hyperparameter search |
| `optimize.squad_ilp` | demo: optimal squad for a gameweek |
| `backtest.season` | simulate one season (transfers + chips + autosubs) |
| `backtest.walk_forward` | multi-season backtest + baselines |
| `predict.live` | this week's transfers/XI/captain/chip |
| `data.snapshot` | daily bootstrap snapshot → `data/snapshots/` |
| `data.live_history` | refresh current-season per-player form cache |
| `models.intervals` | fit p10/p90 interval artifact (re-run after retraining) |
| `predict.export` | weekly site JSON → `web/data/` (auto-refreshes form cache) |
| `predict.scoreboard` | score finished GWs → `web/data/scoreboard.json` |
| `models.price` | watchlist (`--train` once ≥14 snapshot days) |
| `predict.digest` | render email digest |

## 🗓️ Weekly operations (in-season)

| When | What | How |
|---|---|---|
| every day | snapshot + watchlist + scoreboard | `scripts/daily.sh` (cron 02:30 UTC) |
| before each deadline | form refresh + export + digest | `scripts/weekly.sh` (cron Fri 08:00 UTC) |
| after retraining the model | refit intervals | `python -m models.intervals` |
| occasionally (e.g. monthly) | retrain on fresh season data | full pipeline: ingest → build_table → engineer → train |

## 📦 Core modules

- **[config.py](config.py)** — paths, `SEASONS`, `TRAIN/VAL/TEST` split, `WINDOWS`,
  FPL rules (budget/quotas/chips), `SET_PIECE_COLS`, `ODDS_COLS`, `FBREF_COLS`.
- **[data/ingest.py](data/ingest.py)** — `fetch_vaastav_season`, `fetch_fpl_live`.
- **[data/id_map.py](data/id_map.py)** — `load_id_map`, `attach_code` (season-local
  id → stable global `code`).
- **[data/odds.py](data/odds.py)** — `load_odds` (de-overrounded 1X2 + O/U 2.5).
- **[data/fbref.py](data/fbref.py)** — `scrape_to_cache` (direct-URL via seleniumbase
  UC), `load_fbref`, `attach`.
- **[data/build_table.py](data/build_table.py)** — `build` → canonical player-GW
  table (joins FDR/odds/set-piece, backfills position, normalises GK label).
- **[features/engineer.py](features/engineer.py)** — `add_features`: rolling form over
  `[3,5,10,all]` (leakage-safe shift), context, targets `y_points/minutes/played/started/clean_sheets`.
- **[models/train.py](models/train.py)** — `load_features`, `train_predict`,
  `train_position`, `predict_xp`; hurdle model `xP = P(play)·E[pts|played]` per
  position; opt-in `RankCalibrated` (LambdaRank), `ComponentModel` (clean-sheet).
- **[optimize/squad_ilp.py](optimize/squad_ilp.py)** — `build_gw_pool`, `pick_squad`
  (squad+XI+captain ILP, `force`/`force_start` locks), `print_result`.
- **[optimize/transfers.py](optimize/transfers.py)** — `optimize_gw` (weekly transfer
  ILP, TC/BB modes, hits, budget with sell-on fee).
- **[optimize/pricing.py](optimize/pricing.py)** — `selling_price` (50% sell-on fee).
- **[optimize/chips.py](optimize/chips.py)** — `default_schedule` (DGW/BGW + xP fallback).
- **[backtest/season.py](backtest/season.py)** — `run_season` (state machine),
  `_autosub`, `_score` (autosubs + vice-captain).
- **[backtest/walk_forward.py](backtest/walk_forward.py)** — expanding-window backtest;
  `leakage_safe_plan` (multi-GW), `_plan_col`, `_jitter` (CIs).
- **[predict/live.py](predict/live.py)** — `build_pool`, `build_horizon_pool`, `main`
  (flags: `--horizon N`, `--force "Names"`, `--entry ID --free-transfers N`).
- **[predict/export.py](predict/export.py)** — `export` (+`build_table/_captains/
  _squad/_ticker/_chips/_standings/_leaders`): weekly JSON contract in `web/data/`;
  force-refreshes the form cache first (stale form silently skews predictions).
- **[predict/scoreboard.py](predict/scoreboard.py)** — `update`, `score_gw`: MAE +
  Spearman vs FPL's ep_next, captain/top-5 calls, from frozen `web/data/history/`.
- **[data/snapshot.py](data/snapshot.py)** — `take_snapshot`, `load_snapshots`
  (idempotent per UTC day).
- **[models/intervals.py](models/intervals.py)** — `fit_intervals`, `apply_intervals`
  (position × xp-bucket residual quantiles; live coverage ≈0.86 for the 80% band).
- **[models/price.py](models/price.py)** — `build_dataset`, `train`, `emit_watchlist`
  (net-transfers-per-owner heuristic with progress/status until the model unlocks).
- **[api/main.py](api/main.py)** — FastAPI app; `/api/solve` (locks/excludes/horizon/
  chips, cached), `/api/rate/{entry}`, `/api/team/{entry}`; serves `web/` statically;
  `require_key` is the auth stub to replace when payments land.
- **[predict/digest.py](predict/digest.py)** — `build_digest`, `to_text`, `to_html`.

## 🔧 Config / 📚 Docs / 🧪 Tests

- Config: [config.py](config.py), [requirements.txt](requirements.txt),
  [pytest.ini](pytest.ini), [web/config.js](web/config.js) (site → API base).
- Docs: [README.md](README.md) (quick start + product layer), [PLAN.md](PLAN.md)
  (build log + findings), [ROADMAP.md](ROADMAP.md) (productization status).
- Tests: [tests/](tests/) — legality/leakage/autosub invariants +
  [tests/test_product.py](tests/test_product.py) (intervals, snapshot, export,
  price dataset, solver locks, API, digest). Run `python -m pytest`.

## 🔗 Key dependencies

`lightgbm` (xP model) · `pulp` (ILP) · `pandas`/`numpy`/`pyarrow` · `scikit-learn`
(isotonic/joblib) · `requests` · optional `soccerdata`/`seleniumbase` (FBref).

## 📝 Quick start

```bash
conda activate python314 && pip install -r requirements.txt
python -m data.ingest && python -m data.id_map && python -m data.odds
python -m data.build_table && python -m features.engineer && python -m models.train
python -m backtest.walk_forward        # evaluate
python -m predict.live --horizon 6     # this week's team
```
