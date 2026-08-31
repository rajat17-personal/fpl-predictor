# FPL ML Team Predictor — Build Plan

Goal: each gameweek (GW), recommend the optimal FPL squad, starting XI, **captain/vice**,
transfers, and chip usage — by (1) predicting expected points (xP) per player with ML,
then (2) selecting the best legal team via constrained optimization.

Core principle: **ML predicts xP for every player; a Linear Program picks the team.**
Don't ask a model to output a legal squad directly — selection is a constrained
optimization (knapsack variant) solved exactly and cheaply.

---

## Data sources (all free)

| Data | Source | Access | Use |
|---|---|---|---|
| Historical per-GW player stats/points (2016/17→) | vaastav/Fantasy-Premier-League (GitHub) | CSV / git | Training set |
| Live prices, ownership, injuries, fixtures, FDR, chips state | Official FPL API (`fantasy.premierleague.com/api/`) | REST, no key | Live inference |
| xG / xA / shot data (2014/15→) | understat.com via `understatapi` (pip) | scrape | Feature engineering |
| Team strength / Elo | FPL API `strength_*` fields, or FPL Core Insights | CSV / REST | Fixture signal |

Current prices, budget, injuries, fixtures = **always live from FPL API**.
Historical/xG = vaastav + Understat.

---

## Build order (phased)

### Phase 0 — Project setup  ✅ DONE
- Interpreter: conda env `python314` (`/home/sraja/miniconda3/envs/python314/bin/python`).
- `config.py` holds constants, paths, `SEASONS`, `WINDOWS = [3, 5, 10, "all"]`, rules.
- `requirements.txt`; pandas/numpy/pyarrow/requests already installed.

### Phase 1 — Data ingestion → clean per-player-per-GW table  ✅ DONE
- `data/ingest.py`: downloads vaastav `merged_gw.csv` + `fixtures.csv` per season
  and live FPL API (`bootstrap-static`, `fixtures`) to `data/raw/` (cached).
- `data/build_table.py`: standardises columns, joins fixture difficulty
  (`fdr_self`/`fdr_opp`), flags double GWs (`is_dgw`, `matches_in_gw`), adds
  `price_m`, drops AM (Assistant Manager chip) rows + exact duplicates.
- Output: **`data/processed/player_gw.parquet`** — 113,260 rows, seasons
  2022-23→2025-26, 47 cols, key feature coverage 100%. **This is the backbone.**
- Verified: every 0-minute row scores exactly 0; no duplicate (season,player_id,fixture_id).
- Still TODO for later: Understat xG/xA join by player+date (name/ID map — Phase 2),
  and 2026-27 will populate once the season starts (currently 404 → skipped).

### Phase 2 — Feature engineering  ✅ DONE
- `features/engineer.py`: fixture-level matrix, **113,260 rows × 99 cols**
  (86 features + 4 targets + ids) → `data/processed/features.parquet`.
- Rolling form for 19 stats over `[3, 5, 10, all]`, **leakage-safe** (shift(1)
  then roll/expand per season+player). Plus `points_std_r5`, `apps_prior`,
  `days_rest`, and context (`was_home`, `fdr_self/opp`, `is_dgw`, `price_m`, ...).
- Targets: `y_points`, `y_minutes`, `y_played`, `y_started` (for the two-stage model).
- Verified: 0 first-appearance rows carry rolling data; `minutes_r5` matches an
  independent recompute. (Runtime ~90s — batch job, fine.)
- Deferred: Understat shot-level join; cross-season carry-over of prior form.

<!-- original Phase 2 detail retained below -->
- **Rolling features over MULTIPLE windows** (`last_3`, `last_5`, `last_10`,
  `season_to_date`, plus exponentially-weighted). Configurable list — covers your
  "3 / 30 / all previous games" request. Let the model pick which horizon matters.
  - Rolling: minutes, points, xG, xA, xGI, ICT index, bonus, BPS, shots, key passes,
    clean sheets, goals conceded, saves (GK), defensive contributions.
- **Fixture features**: opponent FDR / Elo, home/away, days rest, congestion,
  double/blank GW flag, opponent rolling xG-against.
- **Availability features**: `chance_of_playing_next_round`, flag status, price,
  transfers in/out momentum, ownership%.
- **Static**: position, team, set-piece/penalty taker, is-promoted-team (cold start).
- Note: **ICT index is empirically the strongest single predictor** — keep it prominent.

### Phase 3 — Prediction model (xP)  ✅ DONE (v1)
- `models/train.py`: hurdle model `xP = P(play) · E[pts | played]`, LightGBM,
  separate GK/DEF/MID/FWD. Strict time split (train 22-23/23-24, val 24-25,
  test 25-26). Artifacts in `models/artifacts/`; test preds saved for Phase 4.
- **Test results (2025-26, fixture level):** our MAE **0.884**, Spearman **0.729**
  — beats FPL's own xP (MAE 1.070, Spearman 0.303) and points_r5 (MAE 1.047).
  GW-level MAE 0.893.
- Importances validate design: availability driven by transfers/selected/minutes;
  points driven by minutes, ICT/influence, FDR. No leakage (features all pre-match).
- **Known refinements:** (a) low MAE partly reflects that ~60% of rows are 0-point
  non-plays; (b) predictions are biased low in absolute terms (L1 == median);
  for absolute xP / transfer-hit decisions switch stage-2 to a MEAN objective
  (L2 / Poisson / Tweedie) or calibrate. Ranking (what the optimizer needs) is fine.

<!-- original detail retained below -->
- **Two-stage, per position** (GK/DEF/MID/FWD have different scoring):
  1. **Minutes model**: predict `P(no play)`, `P(cameo <60)`, `P(start ≥60)`.
     A non-playing player scores **exactly 0** — this stage dominates accuracy.
  2. **Conditional points model**: expected points given the player plays.
  - Combine: `xP = P(≥60)·pts_start + P(cameo)·pts_cameo + P(no play)·0`.
- Model: **LightGBM** (baseline: Random Forest). Try component models
  (goals, assists, clean-sheet prob, saves, bonus) then compose → more interpretable.
- **Validation: time-based splits only** (train past GWs → test future GWs).
  Never random splits (leaks future info). Walk-forward across a season.
- Metric: **MAE on points (target ≈1.2–1.5)** as the ML proxy; the REAL metric is
  season points of the picked team vs. a template/average baseline (Phase 6).

### Phase 4 — Optimization (team selection)  ✅ DONE (single-GW core)
- `optimize/squad_ilp.py`: PuLP ILP picks 15-man squad + legal XI + captain,
  maximising XI xP + captain bonus + discounted bench. Handles DGW (xP summed
  per player-GW). Provably optimal (CBC).
- Validated across GW1/10/20/30/38: all legal (2/5/5/3, ≤3 per club, ≤£100m,
  valid formation, 1 captain). From-scratch picks average ~66 actual pts/GW.
- Still Phase 5: multi-GW horizon, transfers/hits, dynamic prices, chips.

<!-- original detail retained below -->
### Phase 4 — Optimization (team selection) — ILP with PuLP/OR-Tools
- **Single-GW squad problem**: maximize Σ xP subject to:
  - Budget ≤ team value (dynamic, see prices below); 2 GK / 5 DEF / 5 MID / 3 FWD;
    max 3 players per club; valid starting formation (min 1 GK, 3 DEF, 1 FWD).
  - Split starting XI vs bench; **bench order** matters for autosubs.
  - **Captain (×2) + vice-captain** chosen in the objective.
- Extend to **multi-GW horizon** (look-ahead N GWs) so transfers/chips see future fixtures.

### Phase 5 — Transfers, prices, chips  ✅ DONE (v1)
- `optimize/pricing.py`: selling price with 50% sell-on fee (rounded to £0.1).
- `optimize/transfers.py`: myopic (1-GW) transfer ILP — sells/buys to maximise
  XI xP + captain − 4/extra-transfer, honours bank/selling prices; modes for
  Triple Captain (×3) and Bench Boost (all 15 score).
- `optimize/chips.py`: chip schedule from fixture structure only (no points peeking)
  — BB on biggest DGW, TC on next, FH on biggest BGW, WC fixed slot; 2 halves.
- `backtest/season.py`: season state-machine (carries squad/bank/FT/purchase prices,
  applies chips, WC/FH via re-pick). Handles blank-GW holdings via tracked meta.
- **Result (2025-26 test): core (median-obj xP, no chips) ≈ 2105 pts (55/GW).**
  Findings: (1) median objective beats mean for selection (mean model is
  transfer-happy: ~10 hits/season); (2) chips are conditional now (BB->biggest
  DGW, TC->DGW-or-best-captain fallback, FH->biggest BGW, WC->fixed slot); TC
  times well (103/84 pts) but WC fixed-slot timing is weak.
- **Key methodological finding: ONE test season is too noisy to evaluate chips
  or small model deltas — season totals swing +/-50-100 on path-dependence.**
  Phase 6 must be MULTI-SEASON walk-forward (test 22-23..25-26 separately, average).
- Training widened to 8 seasons (2016-17..2023-24); position backfilled from
  id_map for pre-2020 seasons (else they'd be dropped from per-position models).
- Known gaps: single-GW lookahead; autosubs not simulated (conservative);
  multi-GW planning / smarter WC timing left as refinements.

<!-- original detail retained below -->
### Phase 5 — Transfers, prices, chips (the sequential layer)
- **Transfers**: start-of-week state = squad + bank + free transfers (roll up to **5**).
  Each extra transfer = **−4 pts**. Optimizer decides transfers by comparing
  multi-GW xP gain vs. hit cost.
- **Prices dynamic**: selling price applies FPL's **50% sell-on fee on profit**;
  track purchase price per holding; team value + bank evolve weekly.
- **Chips** (2026/27: 2× each, must use first set before GW19 deadline):
  - **Triple Captain** (×3 best captain) — target a Double GW premium.
  - **Bench Boost** (all 15 score) — target a Double GW with strong bench.
  - **Free Hit** (one-week temp team) — target Blank GWs / big Double GWs.
  - **Wildcard** (free unlimited transfers, no hit) — reset around fixture swings.
  - Chip timing is a **sequential decision** → v1: heuristics + look-ahead scoring
    (e.g. "Bench Boost = GW that maximizes sum of all 15 xP on a DGW").
    v2: simulate/optimize chip schedule over the season.

### Phase 6 — Backtest & evaluation  ✅ DONE
- `backtest/walk_forward.py`: expanding-window retrain + backtest across 4 test
  seasons (2022-23..2025-26), averaged. Beats single-season noise.
- **6-season walk-forward (2020-21..2025-26), 3 noise controls:**
  - Core model = **2105 pts/season** (±75 season-to-season, SE 31); model+chips 2256;
    form baseline 2036; hold 1693 (active mgmt +412).
  - Multiple teams (5 jittered replicas) -> within-season spread ~±51 pts.
  - **Isolated chip value (same team, w/ vs w/o): FH +19.9±11.8, BB +12.4±7.6,
    TC +10.0±8.3 (n=9-12) — all cleanly positive.** This resolves the earlier
    "chips hurt" as pure whole-season path-dependence noise.
- Autosubs simulated (`_autosub`/`_score`): bench-order subs + vice-captain fallback.
- Data fix: normalised 'GKP'->'GK' (vaastav 2021-22 quirk broke GK constraints).
- Hyperparameters: random search showed the model is robust (best Spearman +0.0009,
  i.e. noise) -> kept defaults + fixed the `subsample_freq` no-op. `models/tune.py`.
- `train.py` refactored: `load_features()` + `train_predict(...)` reusable.

<!-- original detail retained below -->
### Phase 6 — Backtest & evaluation
- Walk-forward over a full past season: for each GW, freeze known-at-the-time data,
  predict xP, run optimizer, apply transfers/chips, tally realized points.
- Baselines to beat: template team, "pick by last-3-avg points", commercial (FPL Review).
- Report: total season points, rank estimate, per-GW MAE, captaincy hit-rate.

### Refinements (post-Phase-7)
- **Set-piece/penalty features** (config.SET_PIECE_COLS via id_map/players_raw,
  2022-23+): KEPT. Marginal (core ~2105->2128, within noise; low importance) —
  signal largely redundant with price/ICT/form. Helps live cold-start; free.
- **Ranking-loss stage-2 variant** (`objectives={"rank":"rank"}`, LGBMRanker +
  isotonic calibration to points): TESTED, REJECTED. ~-55 pts/season vs L1 core —
  L1 already ranks well and rank->points calibration is lossy. Opt-in only; default
  xp_med unchanged (fully revertible).
- **Multi-GW transfer planning** (`xp_plan` = decayed forward-sum of xP): picks players
  good over a fixture RUN, not one week.
  - Optimistic backtest (peeks future GW preds) = +337/season — 88% leakage.
  - **LEAKAGE-SAFE backtest (`walk_forward.leakage_safe_plan`): +40/season honest**
    (form frozen at g, only future FIXTURE context grafted). Positive but noisy
    (helps 4/6 seasons, -82..+124). Largest single refinement, but modest.
  - Live: `predict.live --horizon N` (same frozen-form + known-fixtures construction).
- Still TODO: external odds (football-data.co.uk match odds -> clean-sheet/goals
  priors); FBref/Understat advanced stats (needs name->FPL map).

### External data source assessment (FBref / WhoScored / TheAnalyst)
- **FBref (StatsBomb/Opta) — RECOMMENDED, supersedes standalone Understat.** Free via
  `soccerdata` (which also yields Understat + football-data odds with matching IDs,
  easing name->FPL mapping). Uniquely gives per-match DEFENSIVE actions
  (tackles/interceptions/blocks/clearances) — direct inputs to FPL's newer
  defensive-contribution points (we only capture these implicitly today) — plus
  SCA/GCA and progressive passes. Richer than Understat (shots-only).
- **WhoScored — AVOID.** ToS prohibits scraping and fantasy use without a licence;
  its unique value (composite rating) is barred and derivable from FBref events.
- **TheAnalyst / Opta — NOT worth it.** Raw Opta feed is commercial; we already get
  Opta xG free via the FPL API. Their free output is a competitor model (benchmark
  only, not a data source).
- Plan: adopt `soccerdata` as the single dependency unlocking FBref + odds + Understat.

### External data — IMPLEMENTED / attempted
- **Odds (football-data.co.uk) — DONE & KEPT.** `data/odds.py` de-overrounds 1X2 +
  over/under 2.5 into per-fixture team-perspective probs (`config.ODDS_COLS`), joined
  on (season, date, team, was_home). 100% coverage on all 6 test seasons (2016-19
  lack `team` so NaN there — training only). Result: **strong for defenders/GK** —
  `odds_plose`/`odds_pwin` are TOP-3 features for DEF cond.points (above FDR); best
  fixture MAE yet (0.871). Season-points effect within noise (core 2128->2119) — real
  prediction gain, but the noisy season backtest can't resolve it. Clean-sheet signal.
- **Clean-sheet sub-model for DEF/GK** (`objectives={"cs":"cs"}`, `ComponentModel`:
  P(CS)*4 + residual-points regressor, CS classifier consumes odds): TESTED, REJECTED.
  Fixture-level GK slightly WORSE (MAE 0.522->0.547), DEF flat; season -50/season
  (2111->2061). The generic L1 regressor already models clean sheets from odds well;
  decomposition compounds error. Opt-in only; default xp_med unchanged.
- **FBref — BLOCKED here, seam shipped for later.** FBref needs a real browser
  (Cloudflare); `soccerdata` requires Chrome (absent) and direct fetch = 403.
  `data/fbref.py`: run `scrape_to_cache()` on a Chrome machine -> `fbref.parquet`;
  `build_table` joins it automatically if present (guarded, no-op otherwise).

### Phase 7 — Live weekly runner  ✅ DONE
- `predict/live.py`: pulls live FPL API (prices, availability, fixtures), predicts
  next-GW xP with the trained model (x live injury/suspension availability), then:
  no `--entry` -> optimal squad from scratch; `--entry ID` -> transfers/XI/captain
  from your real squad + bank. Chip note computed from current fixtures.
- Verified on 2026-27 preseason: builds a valid £100.0m GW1 squad, captain by xP.
- Fixture changes handled automatically (API re-fetched each run). Cold-start early
  season leans on price/fixture priors; re-run the pipeline once GWs are played to
  populate rolling form. Transfer mode activates once the season is underway.

<!-- original detail retained below -->
### Phase 7 — Live weekly runner
- Pull live FPL API (prices, injuries, fixtures, your current squad + bank + chips),
  run predict → optimize → output: transfers, XI, **captain/vice**, chip recommendation.

---

## Edge cases & rules to handle (checklist)

- **Non-playing = 0 points** (drives the minutes model).
- **Autosubs**: bench players sub in if a starter plays 0 min → bench order matters.
- **Double GWs (DGW) / Blank GWs (BGW)**: a player may play 0 or 2 matches in a GW —
  critical for xP aggregation and chip timing.
- **Injuries/suspensions/flags**: `chance_of_playing` (0/25/50/75/100%).
- **Captain doesn't play** → vice-captain takes the armband; model this.
- **Price changes**: selling price with 50% sell-on fee on profit; bank/team value drift.
- **Free transfers**: bank up to 5; −4 per extra hit.
- **Formation legality** + min GK/DEF/FWD on pitch.
- **Cold start**: promoted teams / new signings with no history → priors by position/price.
- **2026/27 tweaks**: BPS changes (GK/full-back/attacker friendly), projected bonus
  after 20 mins, later GW lockdown — affects bonus-point features/labels.

## Rules constants (2026/27)
- Budget £100.0m initial; 15-man squad (2/5/5/3); max 3 per club.
- Chips: 2× Wildcard, Free Hit, Triple Captain, Bench Boost — one set each half,
  first set expires at GW19 deadline.
- Free transfers roll up to 5; extra transfer = −4.

---

## Recommended stack
`Python` · `pandas`/`polars` · `LightGBM` · `PuLP` or `OR-Tools` · FPL API + `understatapi`.

## Suggested repo layout
```
fpl/
  config.py            # constants, windows, paths
  data/
    ingest.py          # vaastav + FPL API + Understat loaders
    build_table.py     # canonical player_gw parquet
  features/
    engineer.py        # rolling/fixture/availability features
  models/
    minutes.py         # stage-1 P(play)
    points.py          # stage-2 conditional xP, per position
    train.py           # time-split training + eval (MAE)
  optimize/
    squad_ilp.py       # PuLP squad + captain + formation
    transfers.py       # transfers, prices, hits, multi-GW
    chips.py           # chip timing heuristics
  backtest/
    walk_forward.py    # full-season simulation + baselines
  run_week.py          # live weekly recommendation
```
