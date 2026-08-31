# FPL ML — Fantasy Premier League team predictor

An end-to-end system that recommends the best Fantasy Premier League squad, starting
XI, captain, transfers and chips each gameweek. It predicts **expected points (xP)**
for every player with a machine-learning model, then selects the optimal legal team
with a constrained optimizer.

> **Core idea:** "best team" is two problems chained — (1) *predict* xP per player
> (ML), then (2) *select* the best legal 15/11 under FPL's rules (integer linear
> programming). ML alone can't output a legal squad; the selection is a knapsack.

## Results (6-season walk-forward, honest averages)

| Config | Points / season | Note |
|---|---|---|
| **Full system** (model + chips) | **~2260** | above-average FPL season; causal chip timing |
| Model, no chips | ~2135 | the core (calibrated P(play)) |
| Naive form-picker (ML-free) | ~2030 | model edge **+102** |
| Never transfer (hold) | ~1730 | active management **+405** |

- The xP model **beats FPL's own expected-points**: fixture MAE **0.87 vs 1.07**,
  ranking Spearman **0.74 vs 0.30**.
- Biggest levers: the model itself, active transfers, chips (**+30–40**, isolated),
  and multi-GW planning (**+40**, leakage-safe). Extra features (set-piece, odds)
  sharpen predictions but move season points within noise.

See [PLAN.md](PLAN.md) for the full phase-by-phase build log, experiments, and
honest negative results.

## Quick start

Requires the **`python314`** conda env (Python 3.14). Either activate it or call the
interpreter directly (`/home/sraja/miniconda3/envs/python314/bin/python`).

```bash
conda activate python314
pip install -r requirements.txt          # pandas, lightgbm, pulp, scikit-learn, ...

# 1. Ingest data (vaastav history + live FPL API + football-data odds)
python -m data.ingest                    # downloads to data/raw/ (cached)
python -m data.id_map                    # stable player_code map
python -m data.odds                      # bookmaker odds -> implied probabilities

# 2. Build the canonical table + features
python -m data.build_table               # -> data/processed/player_gw.parquet
python -m features.engineer              # -> data/processed/features.parquet

# 3. Train the xP model (two-stage, per position) + evaluate vs baselines
python -m models.train                   # -> models/artifacts/xp_model.joblib

# 4. Multi-season backtest (retrains per season; ~a few minutes)
python -m backtest.walk_forward

# 5. This week's recommendation from the live FPL API
python -m predict.live                          # optimal squad for the next GW
python -m predict.live --horizon 6              # plan over the next 6 gameweeks
python -m predict.live --force "Haaland,Saka"   # lock specific players in
python -m predict.live --entry <team_id> --free-transfers 1   # transfers for YOUR team
```

## Product layer (site, API, jobs)

The weekly run also ships as a product (see [ROADMAP.md](ROADMAP.md)): a static
site over exported JSON, a solver API, and scheduled jobs. The CLI stays the
source of truth — these are wrappers, so the backtest keeps validating the exact
code the product serves.

```bash
python -m data.snapshot        # DAILY: bootstrap snapshot (price-model training data)
python -m models.intervals     # fit p10/p90 bands from held-out residuals (once per retrain)
python -m predict.export       # weekly JSON -> web/data/ (xP table, captains, squad, ticker)
python -m predict.scoreboard   # post-GW: score frozen predictions vs actual + FPL's ep_next
python -m models.price         # nightly watchlist (heuristic until 14 snapshot days, then --train)
python -m predict.digest       # render email digest from the exported JSON

# One process serves BOTH the site and the API — open http://localhost:8000/
uvicorn api.main:app --port 8000

# (optional two-process alternative: `python -m http.server -d web 8000` for the
#  site + `uvicorn api.main:app --port 8001` for the API — the pages probe
#  localhost:8001 automatically. In production set API_BASE in web/config.js.)
```

- `web/` is a framework-free static site (deploy the directory to Cloudflare
  Pages as-is); set `API_BASE` in [web/config.js](web/config.js) to enable Rate My Team.
- `scripts/daily.sh` and `scripts/weekly.sh` are cron-ready; the
  `.github/workflows/` equivalents activate when this repo is pushed to GitHub.
- The API's paid gate is a stub: set `FPL_API_KEYS=key1,key2` to require
  `X-API-Key`; swap `require_key` in [api/main.py](api/main.py) for real auth
  when payments are wired.
- **Start the daily snapshot cron first** — the price model trains itself from
  day-over-day history that cannot be backfilled.

## How it works

```
vaastav history + FPL API + odds
        │  data/ingest, id_map, odds
        ▼
   player_gw.parquet            data/build_table   (clean, join FDR/odds/set-piece)
        │  features/engineer    (leakage-safe rolling form over [3,5,10,all] windows)
        ▼
   features.parquet
        │  models/train         xP = P(play) × E[points | played]   (hurdle model,
        ▼                                                            LightGBM, per pos)
   xP per player
        │  optimize/            ILP: squad + XI + captain, transfers (sell-on fee),
        ▼                       chips (WC/FH/BB/TC)
   optimal team
        │  backtest/            walk-forward w/ autosubs, jitter CIs, isolated chips
        ▼  predict/            live weekly runner (FPL API), multi-GW horizon
   recommendation
```

**Prediction** ([models/train.py](models/train.py)) — a per-position hurdle model:
stage 1 predicts P(the player features), stage 2 predicts conditional points; a
non-playing player scores exactly 0. LightGBM; validated with strict time-based
splits (never random — that leaks the future).

**Optimization** ([optimize/](optimize/)) — PuLP integer programs enforce £100m
budget, 2/5/5/3 squad, ≤3 per club, valid formations, captain (×2)/Triple Captain
(×3), transfers with the 50% sell-on fee and −4 hits, and chip modes.

**Evaluation** ([backtest/walk_forward.py](backtest/walk_forward.py)) — retrains with
an expanding window and backtests six seasons independently, with autosubs, jittered
replicas (confidence bands), and isolated chip-value measurement to beat single-season
noise.

## Data sources (all free)

| Source | What | Used for |
|---|---|---|
| [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) | per-GW history 2016→ | training |
| Official FPL API | live prices, injuries, fixtures, your team | inference |
| football-data.co.uk | bookmaker match odds | clean-sheet / goals priors |
| FBref (StatsBomb) — optional | defensive actions, SCA/GCA | `python -m data.fbref --scrape` (needs Chrome) |

## Project structure

```
config.py                 constants, paths, seasons/splits, FPL rules, feature lists
data/
  ingest.py               download vaastav + FPL API
  id_map.py               stable player_code across seasons + live
  odds.py                 football-data.co.uk -> implied probabilities
  fbref.py                optional FBref scrape (direct URL, browser)
  build_table.py          -> player_gw.parquet (canonical)
features/engineer.py      -> features.parquet (leakage-safe rolling + context)
models/
  train.py                two-stage hurdle xP model, per position
  tune.py                 hyperparameter search (validation-scored)
optimize/
  squad_ilp.py            squad + XI + captain ILP
  transfers.py            weekly transfer ILP (+ TC/BB modes)
  pricing.py              selling price (50% sell-on fee)
  chips.py                chip scheduling
backtest/
  season.py               season state machine (transfers, chips, autosubs)
  walk_forward.py         multi-season evaluation + baselines
predict/live.py           live weekly recommendation from the FPL API
PLAN.md                   full build log, experiments, findings
```

## Notes & limitations (honest)

- **Single-GW transfer lookahead** by default; multi-GW planning is available
  (`--horizon`) and leakage-safe, worth ~+40 pts/season.
- **Cold start**: early season has little form, so predictions lean on price/fixture
  priors — re-run the pipeline as gameweeks are played to sharpen rolling features.
- **Chip timing** is heuristic (fixture-structure + xP fallback); its per-season value
  is noisy but positive on average.
- The model is mature: several architectural refinements (ranking loss, clean-sheet
  sub-model) were tested and **did not beat** the plain LightGBM regressor — kept
  opt-in and revertible.
